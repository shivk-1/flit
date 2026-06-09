"""Dataclasses for FL Studio project entities (domain model).

These are DAW-shaped, not FLP-shaped: flpio.py maps PyFLP objects onto these and
back. IDs derive from FL Studio internal identifiers (channel IID, pattern index)
so they stay stable across edits — which is what makes merges work. See
docs/SCHEMAS.md.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Metadata:
    title: str = ""
    tempo: float = 140.0
    ts_num: int = 4
    ts_denom: int = 4
    ppq: int = 96
    sample_rate: int = 44100
    flit_version: str = "0.1.0"

    def to_dict(self) -> dict:
        return {
            "flit_version": self.flit_version,
            "title": self.title,
            "tempo": self.tempo,
            "time_signature": {"num": self.ts_num, "denom": self.ts_denom},
            "ppq": self.ppq,
            "sample_rate": self.sample_rate,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Metadata":
        ts = d.get("time_signature", {})
        return cls(
            title=d.get("title", ""),
            tempo=d.get("tempo", 140.0),
            ts_num=ts.get("num", 4),
            ts_denom=ts.get("denom", 4),
            ppq=d.get("ppq", 96),
            sample_rate=d.get("sample_rate", 44100),
            flit_version=d.get("flit_version", "0.1.0"),
        )


@dataclass
class PluginRef:
    name: str = ""
    wrapper: str = "native"          # native | vst2 | vst3
    enabled: bool = True
    state_ref: Optional[str] = None  # path to binary sidecar in plugins/

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "wrapper": self.wrapper,
            "enabled": self.enabled,
            "state_ref": self.state_ref,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PluginRef":
        return cls(
            name=d.get("name", ""),
            wrapper=d.get("wrapper", "native"),
            enabled=d.get("enabled", True),
            state_ref=d.get("state_ref"),
        )


@dataclass
class Channel:
    id: str
    name: str = ""
    kind: str = "sampler"            # sampler | generator
    color: int = 0
    sample_ref: Optional[str] = None
    plugin: Optional[PluginRef] = None
    steps: Optional[List[bool]] = None

    def to_dict(self) -> dict:
        d = {"id": self.id, "name": self.name, "kind": self.kind, "color": self.color,
             "sample_ref": self.sample_ref,
             "plugin": self.plugin.to_dict() if self.plugin else None}
        if self.steps is not None:
            d["steps"] = self.steps
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Channel":
        plug = d.get("plugin")
        return cls(
            id=d["id"], name=d.get("name", ""), kind=d.get("kind", "sampler"),
            color=d.get("color", 0), sample_ref=d.get("sample_ref"),
            plugin=PluginRef.from_dict(plug) if plug else None,
            steps=d.get("steps"),
        )


@dataclass
class Note:
    channel: str
    position: int          # ticks
    length: int            # ticks
    key: int = 60          # MIDI note
    velocity: int = 100
    pan: int = 0
    fine_pitch: int = 0
    release: int = 64
    mod_x: int = 0
    mod_y: int = 0

    def to_dict(self) -> dict:
        return {
            "channel": self.channel, "position": self.position, "length": self.length,
            "key": self.key, "velocity": self.velocity, "pan": self.pan,
            "fine_pitch": self.fine_pitch, "release": self.release,
            "mod_x": self.mod_x, "mod_y": self.mod_y,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Note":
        return cls(
            channel=d["channel"], position=d["position"], length=d["length"],
            key=d.get("key", 60), velocity=d.get("velocity", 100), pan=d.get("pan", 0),
            fine_pitch=d.get("fine_pitch", 0), release=d.get("release", 64),
            mod_x=d.get("mod_x", 0), mod_y=d.get("mod_y", 0),
        )


@dataclass
class Pattern:
    id: str
    name: str = ""
    color: int = 0
    notes: List[Note] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color,
                "notes": [n.to_dict() for n in self.notes]}

    @classmethod
    def from_dict(cls, d: dict) -> "Pattern":
        return cls(id=d["id"], name=d.get("name", ""), color=d.get("color", 0),
                   notes=[Note.from_dict(n) for n in d.get("notes", [])])


@dataclass
class PlaylistItem:
    id: str
    kind: str              # pattern | audio
    ref: str               # pattern id, or asset sha for audio
    start: int             # ticks
    length: int            # ticks
    start_offset: int = 0
    muted: bool = False

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "ref": self.ref,
                "start": self.start, "length": self.length,
                "start_offset": self.start_offset, "muted": self.muted}

    @classmethod
    def from_dict(cls, d: dict) -> "PlaylistItem":
        return cls(id=d["id"], kind=d["kind"], ref=d["ref"], start=d["start"],
                   length=d["length"], start_offset=d.get("start_offset", 0),
                   muted=d.get("muted", False))


@dataclass
class PlaylistTrack:
    index: int
    name: str = ""
    items: List[PlaylistItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"index": self.index, "name": self.name,
                "items": [i.to_dict() for i in self.items]}

    @classmethod
    def from_dict(cls, d: dict) -> "PlaylistTrack":
        return cls(index=d["index"], name=d.get("name", ""),
                   items=[PlaylistItem.from_dict(i) for i in d.get("items", [])])


@dataclass
class Arrangement:
    id: str
    name: str = ""
    tracks: List[PlaylistTrack] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name,
                "tracks": [t.to_dict() for t in self.tracks]}

    @classmethod
    def from_dict(cls, d: dict) -> "Arrangement":
        return cls(id=d["id"], name=d.get("name", ""),
                   tracks=[PlaylistTrack.from_dict(t) for t in d.get("tracks", [])])


@dataclass
class MixerTrack:
    index: int
    name: str = ""
    volume: float = 0.8
    pan: float = 0.0
    muted: bool = False
    solo: bool = False
    routes: List[int] = field(default_factory=list)
    effects: List[PluginRef] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "index": self.index, "name": self.name, "volume": self.volume,
            "pan": self.pan, "muted": self.muted, "solo": self.solo,
            "routes": self.routes,
            "effects": [{"slot": i, **e.to_dict()} for i, e in enumerate(self.effects)],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MixerTrack":
        fx = sorted(d.get("effects", []), key=lambda e: e.get("slot", 0))
        return cls(
            index=d["index"], name=d.get("name", ""), volume=d.get("volume", 0.8),
            pan=d.get("pan", 0.0), muted=d.get("muted", False), solo=d.get("solo", False),
            routes=d.get("routes", []), effects=[PluginRef.from_dict(e) for e in fx],
        )


@dataclass
class AutomationPoint:
    position: int
    value: float
    tension: float = 0.0

    def to_dict(self) -> dict:
        return {"position": self.position, "value": self.value, "tension": self.tension}

    @classmethod
    def from_dict(cls, d: dict) -> "AutomationPoint":
        return cls(position=d["position"], value=d["value"], tension=d.get("tension", 0.0))


@dataclass
class AutomationClip:
    id: str
    name: str = ""
    target: dict = field(default_factory=dict)  # {mixer_track, plugin_slot, param}
    points: List[AutomationPoint] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "target": self.target,
                "points": [p.to_dict() for p in self.points]}

    @classmethod
    def from_dict(cls, d: dict) -> "AutomationClip":
        return cls(id=d["id"], name=d.get("name", ""), target=d.get("target", {}),
                   points=[AutomationPoint.from_dict(p) for p in d.get("points", [])])


@dataclass
class Asset:
    ref: str
    kind: str = "sample"   # sample | vst2 | vst3
    filename: str = ""
    original_path: str = ""
    name: str = ""
    version: str = ""

    def to_dict(self) -> dict:
        d = {"kind": self.kind}
        if self.kind == "sample":
            d.update({"filename": self.filename, "original_path": self.original_path})
        else:
            d.update({"name": self.name, "version": self.version})
        return d

    @classmethod
    def from_dict(cls, ref: str, d: dict) -> "Asset":
        return cls(ref=ref, kind=d.get("kind", "sample"), filename=d.get("filename", ""),
                   original_path=d.get("original_path", ""), name=d.get("name", ""),
                   version=d.get("version", ""))


@dataclass
class Project:
    """Complete in-memory project state — the boundary flpio.py maps to/from."""
    metadata: Metadata = field(default_factory=Metadata)
    channels: List[Channel] = field(default_factory=list)
    patterns: List[Pattern] = field(default_factory=list)
    arrangements: List[Arrangement] = field(default_factory=list)
    mixer: List[MixerTrack] = field(default_factory=list)
    automation: List[AutomationClip] = field(default_factory=list)
    assets: Dict[str, Asset] = field(default_factory=dict)
