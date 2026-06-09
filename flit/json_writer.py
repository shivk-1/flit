"""Domain-split JSON I/O. Mirrors vit's json_writer: one file per role so git
merges them without conflicts. Always indent=2, sort_keys=True for clean diffs."""

import json
import os
from typing import List

from .models import (
    Arrangement,
    Asset,
    AutomationClip,
    Channel,
    Metadata,
    MixerTrack,
    Pattern,
    Project,
)

# project-relative paths
PATTERNS = ("timeline", "patterns.json")
CHANNELS = ("timeline", "channels.json")
ARRANGEMENT = ("timeline", "arrangement.json")
MIXER = ("timeline", "mixer.json")
AUTOMATION = ("timeline", "automation.json")
METADATA = ("timeline", "metadata.json")
MANIFEST = ("assets", "manifest.json")

# files git stages on commit (plugins/ added separately as binary sidecars)
TRACKED_DIRS = ["timeline", "assets", "plugins"]


def _write(project_dir: str, parts: tuple, data: dict) -> None:
    path = os.path.join(project_dir, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def _read(project_dir: str, parts: tuple) -> dict:
    path = os.path.join(project_dir, *parts)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def write_project(project_dir: str, proj: Project) -> None:
    _write(project_dir, METADATA, proj.metadata.to_dict())
    _write(project_dir, CHANNELS, {"channels": [c.to_dict() for c in proj.channels]})
    _write(project_dir, PATTERNS, {"patterns": [p.to_dict() for p in proj.patterns]})
    _write(project_dir, ARRANGEMENT,
           {"arrangements": [a.to_dict() for a in proj.arrangements]})
    _write(project_dir, MIXER, {"tracks": [t.to_dict() for t in proj.mixer]})
    _write(project_dir, AUTOMATION,
           {"automation_clips": [a.to_dict() for a in proj.automation]})
    _write(project_dir, MANIFEST,
           {"assets": {k: v.to_dict() for k, v in proj.assets.items()}})


def read_project(project_dir: str) -> Project:
    meta = _read(project_dir, METADATA)
    channels = _read(project_dir, CHANNELS).get("channels", [])
    patterns = _read(project_dir, PATTERNS).get("patterns", [])
    arrangements = _read(project_dir, ARRANGEMENT).get("arrangements", [])
    mixer = _read(project_dir, MIXER).get("tracks", [])
    automation = _read(project_dir, AUTOMATION).get("automation_clips", [])
    assets = _read(project_dir, MANIFEST).get("assets", {})
    return Project(
        metadata=Metadata.from_dict(meta),
        channels=[Channel.from_dict(c) for c in channels],
        patterns=[Pattern.from_dict(p) for p in patterns],
        arrangements=[Arrangement.from_dict(a) for a in arrangements],
        mixer=[MixerTrack.from_dict(t) for t in mixer],
        automation=[AutomationClip.from_dict(a) for a in automation],
        assets={k: Asset.from_dict(k, v) for k, v in assets.items()},
    )


def read_all_domain_files(project_dir: str) -> dict:
    """Raw dicts keyed by domain — for the validator and AI merge."""
    return {
        "metadata": _read(project_dir, METADATA),
        "channels": _read(project_dir, CHANNELS),
        "patterns": _read(project_dir, PATTERNS),
        "arrangement": _read(project_dir, ARRANGEMENT),
        "mixer": _read(project_dir, MIXER),
        "automation": _read(project_dir, AUTOMATION),
        "manifest": _read(project_dir, MANIFEST),
    }
