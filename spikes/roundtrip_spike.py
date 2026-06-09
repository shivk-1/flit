#!/usr/bin/env python3
"""ROUND-TRIP FIDELITY SPIKE — run this before building anything else.

The entire flit project is gated on one question: can PyFLP load a .flp and write
it back losslessly? If not, restore/checkout can corrupt projects and the product
isn't viable as designed.

Three escalating tests:
  1. IDENTITY   load -> save untouched -> bytes (or re-parse) identical?
  2. ONE FIELD  change tempo only -> only tempo differs, file still opens?
  3. ONE NOTE   move/add a single note -> only that note differs?

After each, OPEN THE RESULT IN FL STUDIO and confirm it's not corrupt — byte
equality is necessary but FL actually opening it is the real test.

Usage:
    pip install pyflp
    python spikes/roundtrip_spike.py /path/to/song.flp
"""

import shutil
import sys
import tempfile
from pathlib import Path

try:
    import pyflp
except ImportError:
    sys.exit("pip install pyflp first")


def _save(proj, path):
    # pyflp 2.x: module-level save(project, file)
    pyflp.save(proj, str(path))


def test_identity(src: Path, work: Path) -> bool:
    out = work / "identity.flp"
    _save(pyflp.parse(src), out)
    same = src.read_bytes() == out.read_bytes()
    print(f"[1] IDENTITY     bytes identical: {same}")
    if not same:
        a, b = src.read_bytes(), out.read_bytes()
        print(f"    sizes: original={len(a)} resaved={len(b)} "
              f"first diff at byte {_first_diff(a, b)}")
        print("    -> NOT byte-identical. Open in FL anyway; if it loads clean,")
        print("       byte-diff may just be event reordering (often fine).")
    print(f"    >> open in FL Studio and confirm: {out}")
    return same


def test_tempo(src: Path, work: Path) -> None:
    out = work / "tempo.flp"
    proj = pyflp.parse(src)
    old = proj.tempo
    proj.tempo = round(float(old) + 1.0, 3)
    _save(proj, out)
    re = pyflp.parse(out)
    print(f"[2] ONE FIELD    tempo {old} -> {proj.tempo}; re-read {re.tempo} "
          f"(match: {abs(float(re.tempo) - float(proj.tempo)) < 1e-6})")
    print(f"    >> open in FL Studio and confirm only tempo changed: {out}")


def test_note(src: Path, work: Path) -> None:
    out = work / "note.flp"
    proj = pyflp.parse(src)
    moved = False
    for pat in proj.patterns:
        notes = list(getattr(pat, "notes", []))
        if notes:
            notes[0].position = int(getattr(notes[0], "position", 0)) + 24
            moved = True
            break
    if not moved:
        print("[3] ONE NOTE     no notes found to move — add a MIDI pattern and retry")
        return
    _save(proj, out)
    print(f"[3] ONE NOTE     moved first note +24 ticks")
    print(f"    >> open in FL Studio and confirm only that note moved: {out}")


def _first_diff(a: bytes, b: bytes) -> int:
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i
    return min(len(a), len(b))


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).expanduser().resolve()
    if not src.exists():
        sys.exit(f"no such file: {src}")
    work = Path(tempfile.mkdtemp(prefix="flit_spike_"))
    print(f"pyflp {getattr(pyflp, '__version__', '?')}  |  source {src}")
    print(f"outputs in {work}\n")
    test_identity(src, work)
    print()
    test_tempo(src, work)
    print()
    test_note(src, work)
    print("\nVerdict: if all three open cleanly in FL Studio with only the intended")
    print("change, write-back is viable — pin this pyflp version and build flpio.")


if __name__ == "__main__":
    main()
