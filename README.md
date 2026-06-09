# flit — Git for FL Studio

`flit` brings git-style version control to music production in FL Studio.

Like [`vit`](https://github.com/LucasHJin/vit) does for video editing, `flit`
versions the **decisions** in your project — patterns, arrangement, mixer,
automation, plugin presets — as lightweight JSON, using real `git` as the
backend. It does **not** version raw audio or render output.

Collaborators (topline writer, beatmaker, sound designer, mix engineer) work in
parallel on branches and merge cleanly, just like developers with code.

## Why this is different from vit

DaVinci Resolve has a live, unsandboxed scripting API — vit talks to the running
app. **FL Studio does not.** Its only in-app Python surface (MIDI Controller
Scripting) is *sandboxed* (no file I/O, no `git`, no `subprocess`). So flit is a
**two-part system**:

```
In-app surface (triggers + feedback)   ─bridge─   flit-engine (the real work)
  • controller script (hint bar/pads)              • PyFLP: .flp ⇄ domain JSON
  • JUCE VST3 WebView panel (later)                • git wrapper (ported from vit)
                                                   • validator + optional AI
```

The **`.flp` file on disk is the source of truth.** flit triggers a save, then
reads the `.flp` with [PyFLP](https://github.com/demberto/PyFLP). The live API is
used only to trigger save, show feedback, and reload on checkout.

## Status

Early scaffold. The git wrapper, domain models, validator, and diff work today.
The PyFLP serialize/deserialize (`flit/flpio.py`) is **stubbed** and gated on the
round-trip fidelity spike (`spikes/roundtrip_spike.py`) — run that against a real
`.flp` first; nothing else matters until it passes. See `docs/ARCHITECTURE.md`.

## Layout

```
flit/            engine: core.py (git), models.py, json_writer.py,
                 flpio.py (PyFLP I/O — stub), validator.py, differ.py, cli.py
fl_controller/   in-app MIDI controller script (Tier 0 surface)
spikes/          roundtrip_spike.py — PyFLP fidelity test (run this first)
docs/            ARCHITECTURE.md, SCHEMAS.md, MERGE_RULES.md
tests/
```
