"""
A one-shot chime request bus between the UI and soundd.

soundd owns the audio output exclusively (one portaudio stream), so a fork
widget that wants a sound cannot play it itself. Instead it writes a chime
name into the ChameleonChime param and soundd's loop pops it here, mapping to
one of upstream's own play-once alert sounds. A real openpilot alert always
wins: soundd only polls this while no alert sound is active, and the request
is consumed on read so it can never loop or replay.
"""
from openpilot.cereal import log
from openpilot.common.params import Params

AudibleAlert = log.SelfdriveState.AudibleAlert

# chime name -> upstream sound (all play-once entries in soundd's sound_list)
CHIMES = {
  "complete": AudibleAlert.complete,
  "prompt": AudibleAlert.prompt,
}


class ChimePoller:
  def __init__(self, params: Params | None = None):
    self.params = params if params is not None else Params()

  def pop(self) -> int:
    """The pending chime as an AudibleAlert, consuming it; none when idle."""
    name = self.params.get("ChameleonChime")
    if not name:
      return AudibleAlert.none
    self.params.remove("ChameleonChime")
    return CHIMES.get(name, AudibleAlert.none)


def request(name: str, params: Params | None = None) -> None:
  """UI side: ask soundd to play a chime. Unknown names are silently ignored."""
  p = params if params is not None else Params()
  p.put("ChameleonChime", name)
