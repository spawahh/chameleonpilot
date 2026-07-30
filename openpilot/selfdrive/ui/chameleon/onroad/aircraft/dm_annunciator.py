"""
Driver-monitoring annunciator, aircraft master-caution style.

openpilot tracks awareness, a three-step alert level and a lockout state in
driverMonitoringState — and the stock UI displays none of it (the face icon
shows head pose only). This widget puts that state where a pilot would look
for a caution light: top-centre, under the header.

States, escalating:
- monitoring normally: small "MON 94%" readout, awareness from whichever policy
  is active (vision vs wheeltouch — the percent lives on different sub-structs).
  Green above AMBER_PERCENT, amber as the score drains, red below RED_PERCENT.
  Two cues jump the queue because they move instantly: "NO FACE" in amber when
  the camera loses the face, and amber the moment the model calls you
  distracted, before the score has moved at all.
- alertLevel one: amber "ATTENTION"; two and three: red.
- lockout (including always-on lockout): red "LOCKOUT", with minutes remaining
  when the message carries them.

Going amber also fires one soft chime — a caution ahead of openpilot's own
warning, which does not sound until much lower. It is one-shot per excursion
and goes quiet entirely once openpilot has an alert of its own up, so the two
never talk over each other.

Every state is outlined in its own colour, matching the driver-alert legends
that share this row; the escalated states (level two and up, lockout) add a
dark fill behind the text so they read as lit annunciators. The amber/red match
the theme-pinned WARNING/DANGER values as literals, the same approach as the
target designator's urgency ramp: escalation colors are not themeable. Hidden
while a full-screen alert is up, mirroring the DM face icon's own gate, so it
never fights the alert renderer.
"""
import pyray as rl

from openpilot.cereal import log
from openpilot.chameleon import chime
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

GREEN = rl.Color(0, 255, 70, 230)  # aircraft green, same as the FPV
AMBER = rl.Color(218, 202, 37, 255)  # the pinned WARNING value
RED = rl.Color(201, 34, 49, 255)  # the pinned DANGER value

TEXT_SIZE = 44
TOP_MARGIN = 160.0  # px below the rect top: the annunciator row; driver alert legends share this line
PAD_X, PAD_Y = 24.0, 10.0
BOX_THICKNESS = 4.0
BOX_BG = rl.Color(0, 0, 0, 140)  # dark fill behind escalated states, same as the alert legends

# The readout colours off the awareness percent itself, at the values Marcus
# reads on the road, rather than waiting for openpilot's own alert levels
# (those land far lower — level one at ~62%, level two at ~38% — so the
# readout would sit green through the whole visible part of the drain).
AMBER_PERCENT = 90
RED_PERCENT = 75

# One soft chime as the readout first goes amber — a caution ahead of the
# warning, well before openpilot's own alert has anything to say. Re-arms only
# after the score climbs back past REARM_PERCENT, so hovering at the boundary
# cannot make it chatter.
PREWARN_CHIME = "prompt"
REARM_PERCENT = 95

AlertLevel = log.DriverMonitoringState.AlertLevel
MonitoringPolicy = log.DriverMonitoringState.MonitoringPolicy


class DmAnnunciator:
  def __init__(self):
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)
    self._prewarned = False

  def render(self, rect: rl.Rectangle, sm) -> None:
    if not ui_state.dm_annunciator:
      return

    if sm.recv_frame['driverMonitoringState'] < ui_state.started_frame:
      return

    # a full-screen alert owns the display; mirror the DM face icon's gate
    if sm['selfdriveState'].alertSize != log.SelfdriveState.AlertSize.none:
      return

    dm = sm['driverMonitoringState']
    text, color, filled = self._state(dm)
    self._maybe_prewarn(dm)

    measure = measure_text_cached(self._font, text, TEXT_SIZE, 0)
    x = rect.x + rect.width / 2 - measure.x / 2
    y = rect.y + TOP_MARGIN

    # boxed like the driver-alert legends, so the row reads as one panel;
    # escalated states also get the dark fill
    box = rl.Rectangle(x - PAD_X, y - PAD_Y, measure.x + 2 * PAD_X, measure.y + 2 * PAD_Y)
    if filled:
      rl.draw_rectangle_rec(box, BOX_BG)
    rl.draw_rectangle_lines_ex(box, BOX_THICKNESS, color)
    rl.draw_text_ex(self._font, text, rl.Vector2(x, y), TEXT_SIZE, 0, color)

  def _maybe_prewarn(self, dm) -> None:
    """Chime once as the score first goes amber, then stay quiet."""
    if dm.lockout or dm.alwaysOnLockout or dm.alertLevel != AlertLevel.none:
      self._prewarned = True  # openpilot owns the audio from here down
      return

    percent = self._awareness_percent(dm)
    if percent < AMBER_PERCENT:
      if not self._prewarned:
        chime.request(PREWARN_CHIME)
        self._prewarned = True
    elif percent >= REARM_PERCENT:
      self._prewarned = False

  @staticmethod
  def _awareness_percent(dm) -> int:
    if dm.activePolicy == MonitoringPolicy.vision:
      return int(dm.visionPolicyState.awarenessPercent)
    return int(dm.wheeltouchPolicyState.awarenessPercent)

  @staticmethod
  def _state(dm) -> tuple[str, rl.Color, bool]:
    if dm.lockout or dm.alwaysOnLockout:
      minutes = int(dm.lockoutMinutesRemaining)
      text = f"LOCKOUT {minutes} MIN" if minutes > 0 else "LOCKOUT"
      return text, RED, True

    if dm.alertLevel in (AlertLevel.two, AlertLevel.three):
      return "ATTENTION", RED, True
    if dm.alertLevel == AlertLevel.one:
      return "ATTENTION", AMBER, False

    distracted = False
    if dm.activePolicy == MonitoringPolicy.vision:
      if not dm.visionPolicyState.faceDetected:
        return "NO FACE", AMBER, False
      distracted = dm.visionPolicyState.isDistracted

    percent = DmAnnunciator._awareness_percent(dm)
    text = f"MON {percent}%"
    if percent < RED_PERCENT:
      return text, RED, True
    if percent < AMBER_PERCENT or distracted:
      return text, AMBER, False
    return text, GREEN, False
