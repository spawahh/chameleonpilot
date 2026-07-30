"""
Driver-monitoring annunciator, aircraft master-caution style.

openpilot tracks awareness, a three-step alert level and a lockout state in
driverMonitoringState — and the stock UI displays none of it (the face icon
shows head pose only). This widget puts that state where a pilot would look
for a caution light: top-centre, under the header.

States, escalating:
- monitoring normally: small "MON 94%" readout in aircraft green, awareness
  from whichever policy is active (vision vs wheeltouch — the percent lives on
  different sub-structs).
- alertLevel one: amber "ATTENTION"; two and three: red, boxed.
- lockout (including always-on lockout): red boxed "LOCKOUT", with minutes
  remaining when the message carries them.

The amber/red match the theme-pinned WARNING/DANGER values as literals, the
same approach as the target designator's urgency ramp: escalation colors are
not themeable. Hidden while a full-screen alert is up, mirroring the DM face
icon's own gate, so it never fights the alert renderer.
"""
import pyray as rl

from openpilot.cereal import log
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

GREEN = rl.Color(0, 255, 70, 230)  # aircraft green, same as the FPV
AMBER = rl.Color(218, 202, 37, 255)  # the pinned WARNING value
RED = rl.Color(201, 34, 49, 255)  # the pinned DANGER value

TEXT_SIZE = 44
TOP_MARGIN = 160.0  # px below the rect top: under the heading tape's readout, above the ladder
PAD_X, PAD_Y = 24.0, 10.0
BOX_THICKNESS = 4.0

AlertLevel = log.DriverMonitoringState.AlertLevel
MonitoringPolicy = log.DriverMonitoringState.MonitoringPolicy


class DmAnnunciator:
  def __init__(self):
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if not ui_state.dm_annunciator:
      return

    if sm.recv_frame['driverMonitoringState'] < ui_state.started_frame:
      return

    # a full-screen alert owns the display; mirror the DM face icon's gate
    if sm['selfdriveState'].alertSize != log.SelfdriveState.AlertSize.none:
      return

    dm = sm['driverMonitoringState']
    text, color, boxed = self._state(dm)

    measure = measure_text_cached(self._font, text, TEXT_SIZE, 0)
    x = rect.x + rect.width / 2 - measure.x / 2
    y = rect.y + TOP_MARGIN
    rl.draw_text_ex(self._font, text, rl.Vector2(x, y), TEXT_SIZE, 0, color)

    if boxed:
      box = rl.Rectangle(x - PAD_X, y - PAD_Y, measure.x + 2 * PAD_X, measure.y + 2 * PAD_Y)
      rl.draw_rectangle_lines_ex(box, BOX_THICKNESS, color)

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

    # the live awareness percent lives on whichever policy is active
    if dm.activePolicy == MonitoringPolicy.vision:
      percent = int(dm.visionPolicyState.awarenessPercent)
    else:
      percent = int(dm.wheeltouchPolicyState.awarenessPercent)
    return f"MON {percent}%", GREEN, False
