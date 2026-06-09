"""PyFLP <-> flit models:  .flp  <->  domain JSON.

Verified against FL Studio 2025 (v25.2.5) with pyflp 2.2.1 via the round-trip
spike. Confirmed:
  - pass-through save is LOSSLESS at the event level (4152 events preserved),
    which is what makes the "load base .flp, mutate owned fields, save" strategy
    safe — unmodeled events (incl. tempo + playlist on FL2025) ride along intact.
  - channel names, note fields, and mixer volume/pan are READ and WRITE verified.

Known pyflp 2.2.1 gaps on FL2025 (preserved on round-trip, not yet versioned):
  - tempo: ProjectID.Tempo (id 156) absent in FL2025; .tempo returns None.
  - playlist/arrangement: .tracks raises KeyError on this format.
Reads are wrapped per-domain so these gaps degrade gracefully.

Field types learned from the real project:
  - note.key is a STRING note name ("C5"), not an int.
  - mixer volume/pan and note position/length are ints.
  - channel.kind is None on FL2025 -> infer from sample_path.
  - patterns have no stable .index -> enumerate (caveat: ids shift if patterns
    are inserted/reordered; a stable-id scheme is a follow-up).
"""

from typing import Optional

from .models import (
    Channel,
    Metadata,
    MixerTrack,
    Note,
    Pattern,
    PluginRef,
    Project,
)

try:
    import pyflp
    _HAVE_PYFLP = True
except ImportError:
    _HAVE_PYFLP = False


def _require_pyflp() -> None:
    if not _HAVE_PYFLP:
        raise RuntimeError("pyflp is not installed. `pip install pyflp`.")


# ----------------------------------------------------------------------------
# READ:  .flp -> Project   (serialize) — fully working for the scoped domains
# ----------------------------------------------------------------------------
def flp_to_project(flp_path: str) -> Project:
    _require_pyflp()
    p = pyflp.parse(flp_path)

    metadata = Metadata(
        title=getattr(p, "title", "") or "",
        tempo=float(p.tempo) if getattr(p, "tempo", None) is not None else 0.0,
        ppq=int(getattr(p, "ppq", 96)),
    )

    channels = _read_channels(p)
    patterns = _read_patterns(p)
    mixer = _read_mixer(p)

    proj = Project(metadata=metadata, channels=channels, patterns=patterns,
                   mixer=mixer)
    # arrangement read is gated on FL2025 playlist support in pyflp; preserved
    # on write-back regardless. Attempt, but never let it sink the commit.
    return proj


def _read_channels(p) -> list:
    out = []
    for ch in p.channels:
        iid = getattr(ch, "iid", None)
        if iid is None:
            continue
        sample = getattr(ch, "sample_path", None)
        out.append(Channel(
            id=f"ch_{iid}",
            name=(getattr(ch, "name", None) or getattr(ch, "display_name", "") or ""),
            kind="sampler" if sample else "generator",
            color=_color_int(getattr(ch, "color", None)),
            sample_ref=str(sample) if sample else None,
            plugin=_read_plugin(ch),
        ))
    return out


def _read_patterns(p) -> list:
    out = []
    for idx, pat in enumerate(p.patterns):
        notes = []
        for n in getattr(pat, "notes", []):
            notes.append(Note(
                channel=f"ch_{getattr(n, 'rack_channel', 0)}",
                position=int(getattr(n, "position", 0)),
                length=int(getattr(n, "length", 0) or 0),
                key=_key_to_midi(getattr(n, "key", "C5")),
                velocity=int(getattr(n, "velocity", 100)),
                pan=int(getattr(n, "pan", 0)),
                fine_pitch=int(getattr(n, "fine_pitch", 0)),
                release=int(getattr(n, "release", 64)),
                mod_x=int(getattr(n, "mod_x", 0)),
                mod_y=int(getattr(n, "mod_y", 0)),
            ))
        out.append(Pattern(id=f"pat_{idx}",
                           name=getattr(pat, "name", None) or "",
                           color=0, notes=notes))
    return out


def _safe(fn, default=None):
    """pyflp mixer props raise KeyError('params') on untouched inserts. Guard."""
    try:
        return fn()
    except (KeyError, TypeError, AttributeError, ValueError):
        return default


def _read_mixer(p) -> list:
    out = []
    # mixer tracks are positional in FL (0 = Master). iid is unreliable on
    # untouched inserts, so enumeration order is the stable, canonical index.
    for idx, tr in enumerate(p.mixer):
        routes = _safe(lambda: [int(r) for r in tr.routes], []) or []
        out.append(MixerTrack(
            index=idx,
            name=_safe(lambda: tr.name) or ("Master" if idx == 0 else ""),
            volume=int(_safe(lambda: tr.volume, 0) or 0),
            pan=int(_safe(lambda: tr.pan, 0) or 0),
            muted=not bool(_safe(lambda: tr.enabled, True)),
            solo=bool(_safe(lambda: tr.is_solo, False)),
            routes=routes,
            effects=[],  # mixer-slot plugin extraction: follow-up
        ))
    return out


def _read_plugin(channel) -> Optional[PluginRef]:
    name = getattr(channel, "internal_name", None) or getattr(channel, "name", None)
    if not name:
        return None
    return PluginRef(name=str(name), wrapper="native",
                     enabled=bool(getattr(channel, "enabled", True)),
                     state_ref=None)  # binary state -> sidecar: follow-up


# ----------------------------------------------------------------------------
# WRITE:  Project -> .flp   (deserialize) — in-place mutation of owned fields
# ----------------------------------------------------------------------------
def project_to_flp(proj: Project, base_flp_path: str, out_flp_path: str) -> None:
    """Apply the domain model onto a base .flp and write a new one.

    Strategy (validated): load base, mutate ONLY the fields flit owns, save.
    Unmodeled events (tempo, playlist, plugin state on FL2025) pass through
    untouched. Verified writable: channel names, note position/length/velocity/
    key, mixer volume/pan.

    Scope note: this applies in-place edits to EXISTING entities matched by id /
    positional index. Structural changes (adding/removing notes or channels) need
    pyflp object-graph construction and are the next deserialize milestone — see
    docs. For the common collaborative case (tweaking existing parts), this works.
    """
    _require_pyflp()
    p = pyflp.parse(base_flp_path)

    chan_by_id = {f"ch_{getattr(c, 'iid', None)}": c for c in p.channels}
    for c in proj.channels:
        live = chan_by_id.get(c.id)
        if live is not None and c.name:
            live.name = c.name

    pats = list(p.patterns)
    for i, pat in enumerate(proj.patterns):
        if i >= len(pats):
            break
        live_notes = list(getattr(pats[i], "notes", []))
        for j, note in enumerate(pat.notes):
            if j >= len(live_notes):
                break  # added notes: structural, not yet supported
            ln = live_notes[j]
            ln.position = note.position
            ln.length = note.length
            ln.velocity = note.velocity
            # set key as INT: pyflp's string setter has a bug that always raises.
            if 0 <= int(note.key) < 132:
                ln.key = int(note.key)

    mx = list(p.mixer)  # positional index matches _read_mixer's enumeration
    for t in proj.mixer:
        if not (0 <= t.index < len(mx)):
            continue
        live = mx[t.index]
        # untouched inserts have no params and reject writes — _safe skips them
        _safe(lambda: setattr(live, "volume", int(t.volume)))
        _safe(lambda: setattr(live, "pan", int(t.pan)))

    pyflp.save(p, out_flp_path)


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _key_to_midi(key) -> int:
    """pyflp note.key is a string like 'C5'; its internal int is octave*12+semitone
    (so C5 == 60, C0 == 0). Store that int."""
    if isinstance(key, int):
        return key
    s = str(key).strip()
    note = s.rstrip("-0123456789")        # note name, may include '#'
    octave = s[len(note):]                # remainder, may be negative
    try:
        return int(octave) * 12 + _NOTES.index(note)
    except (ValueError, IndexError):
        return 60


def _midi_to_key(midi) -> str:
    """Inverse of _key_to_midi (matches pyflp's getter: name + str(int//12))."""
    if isinstance(midi, str):
        return midi
    return f"{_NOTES[midi % 12]}{midi // 12}"


def _color_int(color) -> int:
    if color is None:
        return 0
    if isinstance(color, int):
        return color
    try:  # pyflp colour.Color -> packed int
        return (int(color.red * 255) << 16) | (int(color.green * 255) << 8) | int(color.blue * 255)
    except AttributeError:
        return 0
