"""Cross-domain merge validation.

Git merges cleanly per-file, but can't see cross-domain breakage: a note whose
channel was deleted, a playlist item pointing at a removed pattern, automation
targeting a missing track. This runs after every merge; issues feed the optional
AI resolution pass. Rule-based and dependency-free — works with no API key.

See docs/MERGE_RULES.md.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Issue:
    rule: str          # short id, e.g. "orphan_note"
    severity: str      # "error" | "warning"
    message: str
    domain: str = ""   # which file the problem lives in

    def __str__(self) -> str:
        tag = "✗" if self.severity == "error" else "⚠"
        return f"{tag} [{self.rule}] {self.message}"


def validate(domains: dict) -> List[Issue]:
    """Validate the merged domain dicts (as from read_all_domain_files)."""
    issues: List[Issue] = []

    channels = domains.get("channels", {}).get("channels", [])
    patterns = domains.get("patterns", {}).get("patterns", [])
    arrangements = domains.get("arrangement", {}).get("arrangements", [])
    mixer = domains.get("mixer", {}).get("tracks", [])
    automation = domains.get("automation", {}).get("automation_clips", [])
    manifest = domains.get("manifest", {}).get("assets", {})
    metadata = domains.get("metadata", {})

    channel_ids = {c.get("id") for c in channels}
    pattern_ids = {p.get("id") for p in patterns}
    mixer_indices = {t.get("index") for t in mixer}

    # 1. orphan notes — note.channel no longer exists
    for p in patterns:
        for n in p.get("notes", []):
            if n.get("channel") not in channel_ids:
                issues.append(Issue(
                    "orphan_note", "error",
                    f"pattern '{p.get('id')}' has a note on missing channel "
                    f"'{n.get('channel')}'", "patterns"))

    # 2 & 3. orphan playlist items
    for arr in arrangements:
        for tr in arr.get("tracks", []):
            for it in tr.get("items", []):
                if it.get("kind") == "pattern" and it.get("ref") not in pattern_ids:
                    issues.append(Issue(
                        "orphan_playlist_pattern", "error",
                        f"playlist item '{it.get('id')}' references missing pattern "
                        f"'{it.get('ref')}'", "arrangement"))
                elif it.get("kind") == "audio" and it.get("ref") not in manifest:
                    issues.append(Issue(
                        "orphan_playlist_audio", "warning",
                        f"playlist item '{it.get('id')}' references audio not in "
                        f"manifest '{it.get('ref')}'", "arrangement"))

    # 4. orphan channel route (mixer routing target gone)
    for t in mixer:
        for r in t.get("routes", []):
            if r not in mixer_indices:
                issues.append(Issue(
                    "orphan_channel_route", "error",
                    f"mixer track {t.get('index')} routes to missing track {r}",
                    "mixer"))

    # 5. orphan automation target
    for a in automation:
        tgt = a.get("target", {})
        mt = tgt.get("mixer_track")
        if mt is not None and mt not in mixer_indices:
            issues.append(Issue(
                "orphan_automation_target", "error",
                f"automation '{a.get('id')}' targets missing mixer track {mt}",
                "automation"))

    # 6. overlapping items on the same playlist track
    for arr in arrangements:
        for tr in arr.get("tracks", []):
            items = sorted(tr.get("items", []), key=lambda i: i.get("start", 0))
            for prev, cur in zip(items, items[1:]):
                prev_end = prev.get("start", 0) + prev.get("length", 0)
                if cur.get("start", 0) < prev_end:
                    issues.append(Issue(
                        "overlapping_items", "warning",
                        f"items '{prev.get('id')}' and '{cur.get('id')}' overlap on "
                        f"track {tr.get('index')}", "arrangement"))

    # 7. duplicate ids
    issues += _dupes([c.get("id") for c in channels], "channel", "channels")
    issues += _dupes([p.get("id") for p in patterns], "pattern", "patterns")

    # 9. tempo drift — automation exists but tempo changed (best-effort warning)
    if automation and metadata.get("tempo") and metadata.get("_base_tempo") not in (
        None, metadata.get("tempo")
    ):
        issues.append(Issue(
            "tempo_drift", "warning",
            "tempo changed while automation exists — timing may have shifted",
            "metadata"))

    return issues


def _dupes(ids: List, label: str, domain: str) -> List[Issue]:
    seen, out = set(), []
    for i in ids:
        if i in seen:
            out.append(Issue("duplicate_ids", "error",
                             f"duplicate {label} id '{i}'", domain))
        seen.add(i)
    return out


def summarize(issues: List[Issue]) -> str:
    if not issues:
        return "✓ no cross-domain issues"
    errors = sum(1 for i in issues if i.severity == "error")
    warns = len(issues) - errors
    lines = [f"{errors} error(s), {warns} warning(s):"]
    lines += [f"  {i}" for i in issues]
    return "\n".join(lines)
