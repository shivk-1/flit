# flit Merge Rules

Git merges cleanly **per file** — a topline writer (patterns.json) and a mix
engineer (mixer.json) never collide. The danger is **cross-domain** breakage that
git can't see. `validator.py` runs after every merge; if it finds issues, they
feed an optional LLM resolution pass (`ai_merge.py`). Everything works without AI.

## Structural rules (rule-based, always on)

| # | Rule | Example | Resolution |
|---|------|---------|------------|
| 1 | **Orphan note** | note.channel deleted in channels.json | drop note / flag |
| 2 | **Orphan playlist pattern** | arrangement refs a pattern id no longer in patterns.json | drop item / flag |
| 3 | **Orphan playlist audio** | audio item ref not in manifest | flag (relink) |
| 4 | **Orphan channel route** | channel routed to a deleted mixer track | reroute to Master / flag |
| 5 | **Orphan automation target** | automation targets missing track/plugin/param | drop clip / flag |
| 6 | **Overlapping items** | two items overlap on one playlist track | flag (git merged both) |
| 7 | **Duplicate IDs** | same id appears twice after merge | flag (id collision) |
| 8 | **Plugin state conflict** | same `state_ref` blob differs on both branches | true binary conflict → pick one or fork |
| 9 | **Tempo drift** | tempo changed in metadata; automation/clips assume old tempo | warn |

## Musical rules (AI-assisted, optional — flit's edge over vit)

Because notes carry pitch + timing, the merge can reason *musically*, which a
video diff cannot:

- **Key clash** — two patterns stacked in the playlist sit in clashing keys.
- **Off-grid notes** introduced by a merge.
- **Mixer clipping** — summed levels after merge exceed 0 dB.
- **Density collision** — both branches added busy parts in the same range.

These are surfaced as warnings and, with `GEMINI_API_KEY` set, sent to the LLM
with BASE/OURS/THEIRS for a musically-aware suggestion. The user always confirms
before anything is written.

## Audible diff (the killer feature)

A text diff of notes is useless to a musician. flit renders each branch/commit's
patterns to a short MIDI/audio preview so `flit diff` and the merge UI let you
**hear** before-vs-after — something video metadata can't easily do.
