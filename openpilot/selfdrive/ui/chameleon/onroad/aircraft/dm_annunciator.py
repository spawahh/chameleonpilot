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
  Two cues jump the queue: "NO FACE" in amber when the camera loses the face,
  and amber when the model calls you distracted — the latter behind a short
  dwell-and-hold, because the raw flag flickers on brief pose excursions and a
  flashing readout is itself a distraction.
- alertLevel one: amber "ATTENTION"; two and three: red.
- lockout (including always-on lockout): red "LOCKOUT", with minutes remaining
  when the message carries them.

This widget is silent: openpilot owns every sound driver monitoring makes.

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
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

GREEN = rl.Color(0, 255, 70, 230)  # aircraft green, same as the FPV
AMBER = rl.Color(218, 202, 37, 255)  # the pinned WARNING value
RED = rl.Color(201, 34, 49, 255)  # the pinned DANGER value

# 38, not 44: seven uniform boxes at 44 need 2035 px of the 2100 px content
# width and end up nearly touching. At 38 they are 258 px in 300 px slots,
# which leaves a readable gap. Measured on the device with the real font.
TEXT_SIZE = 38
# high enough to clear the pitch ladder's upper bars (the legends used to sit
# right on the +10 bar), low enough to stay under the road-name pill (y 4..64)
TOP_MARGIN = 88.0
PAD_X, PAD_Y = 24.0, 10.0
BOX_THICKNESS = 4.0
BOX_BG = rl.Color(0, 0, 0, 140)  # dark fill behind escalated states, same as the alert legends

# The readout colours off the awareness percent itself, at the values Marcus
# reads on the road, rather than waiting for openpilot's own alert levels
# (those land far lower — level one at ~62%, level two at ~38% — so the
# readout would sit green through the whole visible part of the drain).
AMBER_PERCENT = 90
RED_PERCENT = 75

# The distracted cue needs a dwell: isDistracted is instantaneous and a brief
# pose excursion made the readout flash amber for single frames — a distraction
# itself. Amber only after the flag holds DISTRACTED_DWELL_S, then stays at
# least DISTRACTED_HOLD_S so it never strobes.
DISTRACTED_DWELL_S = 0.5
DISTRACTED_HOLD_S = 1.0

# The annunciator row: seven evenly spaced slots across the top. Driver-alert
# legends first, then the DM readout, then turn, then the system group.
SLOTS = 7
(SLOT_GREEN_LIGHT, SLOT_LEAD_DEPART, SLOT_MON, SLOT_TURN,
 SLOT_TEMP, SLOT_GPS, SLOT_ENGAGE) = range(SLOTS)

# Every legend reserves this width, so the boxes are identical and the gaps
# read as even — unequal box widths were what made evenly-spaced slot centres
# look irregular. It is the widest ordinary legend; an exceptional text (the
# lockout readout) is allowed to outgrow it.
UNIFORM_RESERVE = "ATTENTION"

AlertLevel = log.DriverMonitoringState.AlertLevel
MonitoringPolicy = log.DriverMonitoringState.MonitoringPolicy


def slot_x(rect: rl.Rectangle, slot: int) -> float:
  """Centre x of an annunciator slot; every legend in the row uses this."""
  return rect.x + rect.width * (slot + 0.5) / SLOTS


def draw_legend(font: rl.Font, text: str, cx: float, y: float, color: rl.Color,
                filled: bool = False, reserve: str = UNIFORM_RESERVE) -> None:
  """One boxed legend, centred on cx — the row's single drawing primitive.

  The box is held at `reserve`'s width rather than the text's, which does two
  jobs: every legend in the row comes out the same size, and a legend whose
  text changes (TURN gaining a direction arrow, MON counting down) never
  resizes mid-drive — that movement is more distracting than the text is
  useful. Text wider than the reserve still gets a box that fits it.
  """
  measure = measure_text_cached(font, text, TEXT_SIZE, 0)
  inner = max(measure.x, measure_text_cached(font, reserve, TEXT_SIZE, 0).x)

  box = rl.Rectangle(cx - inner / 2 - PAD_X, y - PAD_Y, inner + 2 * PAD_X, measure.y + 2 * PAD_Y)
  if filled:
    rl.draw_rectangle_rec(box, BOX_BG)
  rl.draw_rectangle_lines_ex(box, BOX_THICKNESS, color)
  rl.draw_text_ex(font, text, rl.Vector2(cx - measure.x / 2, y), TEXT_SIZE, 0, color)


class DmAnnunciator:
  def __init__(self):
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)
    self._distracted_frames = 0
    self._amber_hold_frames = 0

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
    draw_legend(self._font, text, slot_x(rect, SLOT_MON), rect.y + TOP_MARGIN, color, filled)

  def _distracted_steady(self, distracted: bool) -> bool:
    """The dwell: amber only after the flag holds, then held so it cannot strobe."""
    fps = gui_app.target_fps
    self._distracted_frames = self._distracted_frames + 1 if distracted else 0

    if self._distracted_frames >= int(DISTRACTED_DWELL_S * fps):
      self._amber_hold_frames = int(DISTRACTED_HOLD_S * fps)
    elif self._amber_hold_frames > 0:
      self._amber_hold_frames -= 1

    return self._amber_hold_frames > 0

  @staticmethod
  def _awareness_percent(dm) -> int:
    if dm.activePolicy == MonitoringPolicy.vision:
      return int(dm.visionPolicyState.awarenessPercent)
    return int(dm.wheeltouchPolicyState.awarenessPercent)

  def _state(self, dm) -> tuple[str, rl.Color, bool]:
    if dm.lockout or dm.alwaysOnLockout:
      # short form so it still fits a row slot; "LOCKOUT 30 MIN" overflowed
      minutes = int(dm.lockoutMinutesRemaining)
      text = f"LOCK {minutes}M" if minutes > 0 else "LOCKOUT"
      return text, RED, True

    if dm.alertLevel in (AlertLevel.two, AlertLevel.three):
      return "ATTENTION", RED, True
    if dm.alertLevel == AlertLevel.one:
      return "ATTENTION", AMBER, False

    raw_distracted = False
    if dm.activePolicy == MonitoringPolicy.vision:
      if not dm.visionPolicyState.faceDetected:
        return "NO FACE", AMBER, False
      raw_distracted = dm.visionPolicyState.isDistracted
    distracted = self._distracted_steady(raw_distracted)

    percent = DmAnnunciator._awareness_percent(dm)
    text = f"MON {percent}%"
    if percent < RED_PERCENT:
      return text, RED, True
    if percent < AMBER_PERCENT or distracted:
      return text, AMBER, False
    return text, GREEN, False
