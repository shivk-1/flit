# flit Architecture

## Core insight (inherited from vit)

Version-control the **decisions**, not the media. Patterns, arrangement, mixer,
automation, and plugin presets become domain-split JSON; real `git` is the
backend. Samples and renders stay out of git (a manifest records references).

## The FL Studio constraint

| Surface | Draw UI? | Read project? | Run git / write files? |
|---|---|---|---|
| MIDI Controller Script (in-app Python 3.9) | hint bar + overlays only | yes (live API) | **NO — sandboxed** |
| Native plugin (FL SDK / JUCE VST3) | full window | limited | yes (native code) |

Because the in-app interpreter is sandboxed, the engine **must** be external.
Every design is therefore: in-app surface + external `flit-engine` + a bridge.

## Source of truth: the `.flp` file, not the live API

Do **not** reconstruct the project by streaming live state over MIDI (7-bit, slow,
lossy). Instead:

1. Trigger a save (Ctrl+S, or user saves and the engine file-watches).
2. Read the saved `.flp` with PyFLP → domain JSON. (commit)
3. To restore: JSON → PyFLP → write `.flp` → reopen in FL. (checkout)

The `.flp` binary is **gitignored**, like vit ignores `.drp`/media. Only the JSON
+ plugin sidecars are tracked, so diffs stay clean and merges work per-domain.

## Engine modules

```
flit/
  core.py        git wrapper (subprocess) — ported from vit, ~unchanged
  models.py      music dataclasses (Note, Pattern, Channel, MixerTrack, ...)
  json_writer.py domain-split read/write
  flpio.py       PyFLP  .flp ⇄ models   <-- THE HARD PART, currently stubbed
  validator.py   cross-domain merge rules (orphans, overlaps, tempo drift)
  differ.py      human-readable / audible diff
  ai_merge.py    optional LLM musical merge (degrades gracefully)
  cli.py         init/add/commit/branch/checkout/merge/diff/log/status
```

`flpio.py` is bigger and harder than the rest combined (deserialize > serialize),
exactly as in vit. It is the one module that depends on round-trip fidelity.

## In-app surfaces (build in tiers)

- **Tier 0** — `fl_controller/` MIDI controller script + file-watch engine.
  Pure Python, no C++. Commit/prev/next via pads; feedback in the hint bar;
  changed regions highlighted via playlist overlays. Fastest path to "in-app".
- **Tier 1** — JUCE VST3 effect on the Master with a WebView panel: branch list,
  version graph, buttons, audible diff. The true vit-panel equivalent.
- **Tier 2** — Tier 1 + controller-script overlays/hint-bar + audible diff.

The bridge between in-app surface and engine is a local socket; the data channel
is always the `.flp` file, never MIDI.

## The #1 risk: round-trip fidelity

PyFLP write-back must be lossless. Before building anything else, run
`spikes/roundtrip_spike.py` on several real `.flp` files:
`load → save (untouched) → open in FL, identical?` then `edit one field → only
that changes?`. The whole project is gated on this. The sandbox claim ("no file
I/O in the in-app interpreter") is also load-bearing — confirm it during the spike.
