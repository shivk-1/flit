# flit Domain JSON Schemas

All files live in `timeline/` of a flit project, except `assets/manifest.json`
and the binary plugin sidecars in `plugins/`. Written with
`json.dump(indent=2, sort_keys=True)` for clean diffs.

**Stable IDs are critical for merges.** IDs derive from FL Studio's internal
identifiers (channel IID, pattern index) so they stay stable across edits:
`ch_<iid>`, `pat_<index>`, etc.

## Ownership map (who edits what → conflict-free merges)

| File | Contents | Typical owner |
|------|----------|---------------|
| `patterns.json` | piano-roll notes per pattern | melody / topline writer |
| `channels.json` | channel rack: instruments, samples, step seqs | beatmaker |
| `arrangement.json` | playlist: patterns/audio on tracks | arranger |
| `mixer.json` | mixer volume/pan/routing/effect chain | mix engineer |
| `automation.json` | automation clips (param curves) | anyone |
| `plugins/*.fst` | plugin/preset state (binary sidecar) | sound designer |
| `metadata.json` | tempo, time sig, ppq, sample rate | rarely |

## metadata.json
```json
{
  "flit_version": "0.1.0",
  "title": "My Track",
  "tempo": 140.0,
  "time_signature": { "num": 4, "denom": 4 },
  "ppq": 96,
  "sample_rate": 44100
}
```

## channels.json
```json
{
  "channels": [
    {
      "id": "ch_5",
      "name": "Kick",
      "kind": "sampler",
      "color": 5066239,
      "sample_ref": "sha256:abcd...",
      "plugin": { "name": "Fruity Sampler", "wrapper": "native",
                  "state_ref": "plugins/ch_5.fst" },
      "steps": [true, false, false, false, true, false, false, false]
    }
  ]
}
```
`kind`: `sampler` | `generator`. `sample_ref` null for synths; `state_ref` null
if no preset state. `steps` present only for step-sequenced channels.

## patterns.json
Positions/lengths in ticks (relative to `ppq`). `key` = MIDI note (60 = C5 in FL).
```json
{
  "patterns": [
    {
      "id": "pat_0",
      "name": "Verse Chords",
      "color": 8454143,
      "notes": [
        { "channel": "ch_3", "position": 0, "length": 96, "key": 60,
          "velocity": 100, "pan": 0, "fine_pitch": 0, "release": 64,
          "mod_x": 0, "mod_y": 0 }
      ]
    }
  ]
}
```

## arrangement.json
```json
{
  "arrangements": [
    {
      "id": "arr_0",
      "name": "Arrangement",
      "tracks": [
        {
          "index": 1,
          "name": "Drums",
          "items": [
            { "id": "pi_0", "kind": "pattern", "ref": "pat_0",
              "start": 0, "length": 768, "muted": false },
            { "id": "pi_1", "kind": "audio", "ref": "sha256:ef01...",
              "start": 768, "length": 1536, "start_offset": 0, "muted": false }
          ]
        }
      ]
    }
  ]
}
```
`kind`: `pattern` (ref → patterns.json id) | `audio` (ref → manifest sha).

## mixer.json
```json
{
  "tracks": [
    {
      "index": 0, "name": "Master", "volume": 0.8, "pan": 0.0,
      "muted": false, "solo": false, "routes": [1, 2],
      "effects": [
        { "slot": 0, "name": "Fruity Reeverb 2", "wrapper": "native",
          "enabled": true, "state_ref": "plugins/mix0_slot0.fst" }
      ]
    }
  ]
}
```
`routes`: list of mixer track indices this track sends to.

## automation.json
```json
{
  "automation_clips": [
    {
      "id": "auto_0", "name": "Filter Cutoff",
      "target": { "mixer_track": 1, "plugin_slot": 0, "param": "cutoff" },
      "points": [
        { "position": 0, "value": 0.2, "tension": 0.0 },
        { "position": 768, "value": 0.9, "tension": 0.0 }
      ]
    }
  ]
}
```

## plugins/  (binary sidecars)
`.fst`-style state blobs, one per channel/effect slot, keyed by `state_ref`
(`plugins/ch_5.fst`, `plugins/mix0_slot0.fst`). Opaque binary — git stores them;
a binary conflict here means "pick one branch's version, or fork the channel."
This is flit's analogue of vit's baked `.cube` color sidecars.

## assets/manifest.json
```json
{
  "assets": {
    "sha256:abcd...": { "kind": "sample", "filename": "kick_03.wav",
                        "original_path": "/Users/x/Samples/kick_03.wav" },
    "plugin:Serum:1.3.6": { "kind": "vst3", "name": "Serum", "version": "1.3.6" }
  }
}
```
On checkout, flit warns about missing samples/plugins before the project opens
broken.
