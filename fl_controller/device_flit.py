# name=flit
"""flit — Tier 0 in-app surface (FL Studio MIDI Controller Script).

Install: copy this folder to
  Documents/Image-Line/FL Studio/Settings/Hardware/flit/
then pick "flit" as the controller type for a (real or virtual) MIDI device.

WHAT THIS CAN AND CANNOT DO
---------------------------
FL Studio's scripting interpreter is SANDBOXED: no file I/O, no subprocess, no
git, no pyflp. So this script CANNOT do version control itself. It is only the
in-app *trigger + feedback* layer. The real work happens in the external
flit-engine; this script signals it and reports back.

  pad/shortcut here ──MIDI──► flit-engine (watches MIDI + the .flp) ──► git/pyflp
        ▲                                                                    │
        └────────────── hint-bar text / playlist overlay ◄──────────────────┘

Bridge options for talking to the engine:
  • The engine listens on a virtual MIDI port (loopMIDI / IAC) and reads our
    sysex/CC pings (Flapi-style). Keep it to lightweight triggers — never stream
    project data over MIDI; the engine reads the saved .flp directly.
  • Or: the engine just file-watches the .flp; this script's "commit" simply
    triggers a save and the engine auto-commits.

This is a STUB wiring the FL API hooks. Fill in the engine handshake once the
engine's MIDI listener exists.
"""

import midi          # noqa: F401  (FL Studio built-ins, available in-app only)
import ui
import transport     # noqa: F401
import general       # noqa: F401

# --- pad/CC map (adjust to your controller) ---
CC_COMMIT = 0x10
CC_PREV_VERSION = 0x11
CC_NEXT_VERSION = 0x12

ENGINE_PORT_HINT = "flit-engine"  # the virtual MIDI port the engine listens on


def OnInit():
    ui.setHintMsg("flit ready")


def OnDeInit():
    pass


def OnMidiMsg(event):
    """Map controller buttons to flit actions."""
    if event.midiId == midi.MIDI_CONTROLCHANGE:
        if event.data1 == CC_COMMIT and event.data2 > 0:
            _commit()
            event.handled = True
        elif event.data1 == CC_PREV_VERSION and event.data2 > 0:
            _send_engine("prev")
            event.handled = True
        elif event.data1 == CC_NEXT_VERSION and event.data2 > 0:
            _send_engine("next")
            event.handled = True


def _commit():
    # Save the project so the engine has a fresh .flp to serialize, then ping it.
    # transport / general expose save via FL's command set; wire the exact call
    # for your FL version here. The engine does the git commit.
    ui.setHintMsg("flit: saving + committing...")
    _send_engine("commit")


def _send_engine(action: str):
    """Send a lightweight trigger to the external flit-engine.

    TODO: emit a sysex/CC on the engine's virtual MIDI port. Feedback (e.g.
    'committed v13') comes back as an incoming MIDI msg handled in OnMidiMsg and
    shown via ui.setHintMsg(...). Playlist overlays (ui.* overlay calls) can
    highlight changed regions after a checkout/diff.
    """
    ui.setHintMsg(f"flit: {action} -> engine")
