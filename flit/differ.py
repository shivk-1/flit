"""Human-readable diff between two project states (raw domain dicts).

vit's differ turns git's line noise into editor language ("Trimmed clip..."). This
does the same in producer language ("+ 4 notes in 'Verse Chords'", "Kick volume
0.8 -> 0.6"). An audible diff (rendering patterns to preview audio) is the planned
companion — see docs/MERGE_RULES.md — and belongs here too.
"""

from typing import List


def diff_projects(base: dict, head: dict) -> str:
    lines: List[str] = []
    lines += _diff_patterns(base, head)
    lines += _diff_channels(base, head)
    lines += _diff_mixer(base, head)
    lines += _diff_arrangement(base, head)
    return "\n".join(lines) if lines else "no changes"


def _by_id(domain: dict, top: str, key: str) -> dict:
    return {x.get("id"): x for x in domain.get(top, {}).get(key, [])}


def _diff_patterns(base: dict, head: dict) -> List[str]:
    b = _by_id(base, "patterns", "patterns")
    h = _by_id(head, "patterns", "patterns")
    out = []
    for pid in h.keys() - b.keys():
        out.append(f"PATTERNS: + Added pattern '{h[pid].get('name', pid)}'")
    for pid in b.keys() - h.keys():
        out.append(f"PATTERNS: - Removed pattern '{b[pid].get('name', pid)}'")
    for pid in b.keys() & h.keys():
        name = h[pid].get("name") or pid
        bn, hn = b[pid].get("notes", []), h[pid].get("notes", [])
        if len(bn) != len(hn):
            delta = f"+{len(hn) - len(bn)}" if len(hn) > len(bn) else str(len(hn) - len(bn))
            out.append(f"PATTERNS: ~ '{name}' notes {len(bn)} -> {len(hn)} ({delta})")
        else:
            # same count: report per-note property changes (velocity, position, ...)
            changed = sum(1 for x, y in zip(bn, hn) if x != y)
            if changed:
                fields = sorted({k for x, y in zip(bn, hn) for k in x
                                 if x.get(k) != y.get(k)})
                out.append(f"PATTERNS: ~ '{name}' edited {changed} note(s) "
                           f"({', '.join(fields)})")
    return out


def _diff_channels(base: dict, head: dict) -> List[str]:
    b = _by_id(base, "channels", "channels")
    h = _by_id(head, "channels", "channels")
    out = []
    for cid in h.keys() - b.keys():
        out.append(f"CHANNELS: + Added channel '{h[cid].get('name', cid)}'")
    for cid in b.keys() - h.keys():
        out.append(f"CHANNELS: - Removed channel '{b[cid].get('name', cid)}'")
    return out


def _diff_mixer(base: dict, head: dict) -> List[str]:
    b = {t.get("index"): t for t in base.get("mixer", {}).get("tracks", [])}
    h = {t.get("index"): t for t in head.get("mixer", {}).get("tracks", [])}
    out = []
    for idx in b.keys() & h.keys():
        bt, ht = b[idx], h[idx]
        label = ht.get("name") or f"track {idx}"
        if bt.get("volume") != ht.get("volume"):
            out.append(f"MIXER: ~ '{label}' volume "
                       f"{bt.get('volume')} -> {ht.get('volume')}")
        if bt.get("pan") != ht.get("pan"):
            out.append(f"MIXER: ~ '{label}' pan {bt.get('pan')} -> {ht.get('pan')}")
        if len(bt.get("effects", [])) != len(ht.get("effects", [])):
            out.append(f"MIXER: ~ '{label}' effect count "
                       f"{len(bt.get('effects', []))} -> {len(ht.get('effects', []))}")
    return out


def _diff_arrangement(base: dict, head: dict) -> List[str]:
    def count(d):
        return sum(len(t.get("items", []))
                   for a in d.get("arrangement", {}).get("arrangements", [])
                   for t in a.get("tracks", []))
    cb, ch = count(base), count(head)
    if cb != ch:
        return [f"ARRANGEMENT: ~ playlist items {cb} -> {ch}"]
    return []
