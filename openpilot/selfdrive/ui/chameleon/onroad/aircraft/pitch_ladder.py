"""
Pitch ladder, the attitude reference of the aircraft HUD layout.

Horizontal bars every LADDER_STEP degrees of elevation, climb bars solid and
dive bars dashed, with the horizon drawn long and unbroken. The ladder slides
down the screen as the car noses up a hill and rotates with body roll, so it
reads as a real attitude reference rather than a fixed grid.

chameleonpilot original. Bars are placed by projecting car-space points through
the same transform the model renderer and the flight path vector use, so the
ladder shares their frame: a point at unit distance and height tan(a) sits a
degrees below the boresight, whatever the camera intrinsics and zoom are. That
means no focal length is extracted here and none needs to be kept in sync.

Attitude comes from livePose via PoseCalibrator, which removes the device mount
angle — the raw device orientation is tilted by however the comma sits on the
windscreen. orientationNED pitch is positive nose-up: longitudinal_planner's
get_coast_accel multiplies sin(pitch) by a negative constant to get the coast
deceleration, which is only correct uphill if up is positive.
"""
import numpy as np
import pyray as rl

from openpilot.selfdrive.locationd.helpers import Pose, PoseCalibrator
from openpilot.selfdrive.ui.chameleon.onroad.aircraft import dm_annunciator as dma
from openpilot.selfdrive.ui.chameleon.onroad.aircraft import tapes
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

LADDER_STEP = 5.0  # deg between bars
LADDER_RANGE = 15.0  # deg, highest and lowest bar drawn
HALF_WIDTH = 7.0  # deg of azimuth, half a climb/dive bar
HORIZON_HALF_WIDTH = 12.0  # deg, the horizon bar is drawn longer
CENTER_GAP = 2.5  # deg of azimuth left clear in the middle for the boresight
TICK = 1.2  # deg of elevation, the end ticks that point at the horizon
DASHES = 5  # segments a dive bar is broken into

# Roll direction. A car rolls a few degrees at most, so this is a small effect
# and the sign has not been confirmed against a banked road yet — flip this one
# constant if the ladder tilts the wrong way.
ROLL_SIGN = -1.0

MARGIN = 80.0  # px of slack outside the rect before a bar is dropped
THICKNESS = 3.0
HORIZON_THICKNESS = 4.0
COLOR = rl.Color(0, 255, 70, 190)
HORIZON_COLOR = rl.Color(0, 255, 70, 230)
LABEL_SIZE = 34
LABEL_GAP = 12.0  # px between a bar end and its number

# The ladder sweeps up and down the screen with pitch, so its bars cross whatever
# else is drawn there — on the road that was the annunciator row and the heading
# tape, with the text sitting on top of a green bar. Bars fade out as they
# approach those bands instead of being clipped, so nothing blinks on and off at
# a boundary. The edges are derived from those widgets' own constants rather than
# copied, so moving a row moves the fade with it, and a band only exists while
# the thing that occupies it is switched on.
FADE_MARGIN = 90.0  # px over which a bar fades to nothing as it nears a band


def band_edges(rect: rl.Rectangle) -> tuple[float, float]:
  """Screen y of the bottom of the top band and the top of the bottom band.

  A band that nothing occupies is pushed a full margin outside the rect, so the
  ladder is never faded by an element that is switched off.
  """
  if ui_state.dm_annunciator:
    # the legend box: TOP_MARGIN down to one line plus its two paddings
    top = rect.y + dma.TOP_MARGIN + dma.TEXT_SIZE + 2 * dma.PAD_Y
  else:
    top = rect.y - FADE_MARGIN

  if ui_state.aircraft_tapes:
    # the heading tape's ticks and labels rise above its baseline
    top_of_heading = tapes.HEADING_BOTTOM_MARGIN + tapes.TICK * 1.6 + tapes.LABEL_SIZE
    bottom = rect.y + rect.height - top_of_heading
  else:
    bottom = rect.y + rect.height + FADE_MARGIN

  return top, bottom


def fade_scale(y: float, rect: rl.Rectangle) -> float:
  """1.0 in the clear, 0.0 inside a reserved band, linear in between."""
  top, bottom = band_edges(rect)
  return float(np.clip(min(y - top, bottom - y) / FADE_MARGIN, 0.0, 1.0))


def faded(color: rl.Color, scale: float) -> rl.Color:
  """The colour, dimmed. Returns the original object untouched at full scale —
  which is the common case, so the ladder allocates nothing per frame while it is
  in the clear, and a caller comparing against the module colour still matches."""
  if scale >= 1.0:
    return color
  return rl.Color(color.r, color.g, color.b, int(color.a * scale))


class PitchLadder:
  def __init__(self):
    self._car_space_transform = np.zeros((3, 3), dtype=np.float32)
    self._calibrator = PoseCalibrator()
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)

  def set_transform(self, transform: np.ndarray) -> None:
    self._car_space_transform = transform.astype(np.float32)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if not ui_state.pitch_ladder:
      return

    if sm.recv_frame['livePose'] < ui_state.started_frame:
      return

    if sm.recv_frame['liveCalibration'] >= ui_state.started_frame:
      self._calibrator.feed_live_calib(sm['liveCalibration'])

    # Without calibration the mount angle is unknown, so the horizon would sit
    # at an arbitrary height. Better to draw nothing than to draw a wrong one.
    if not self._calibrator.calib_valid:
      return

    live_pose = sm['livePose']
    if not live_pose.orientationNED.valid:
      return

    pose = self._calibrator.build_calibrated_pose(Pose.from_live_pose(live_pose))
    pitch, roll = float(pose.orientation.pitch), float(pose.orientation.roll)
    if not (np.isfinite(pitch) and np.isfinite(roll)):
      return

    for angle in np.arange(-LADDER_RANGE, LADDER_RANGE + LADDER_STEP / 2, LADDER_STEP):
      self._draw_bar(round(float(angle)), pitch, roll, rect)

  def _draw_bar(self, angle: int, pitch: float, roll: float, rect: rl.Rectangle) -> None:
    """One rung: the bar itself, its end ticks pointing at the horizon, and its number."""
    # Depression below the boresight. Nose up moves the whole ladder down.
    depression = np.tan(pitch - np.radians(angle))
    is_horizon = angle == 0
    half_width = np.tan(np.radians(HORIZON_HALF_WIDTH if is_horizon else HALF_WIDTH))
    color = HORIZON_COLOR if is_horizon else COLOR
    thickness = HORIZON_THICKNESS if is_horizon else THICKNESS

    # Ticks hang toward the horizon, so they point down above it and up below.
    tick = np.tan(np.radians(TICK)) * (-1.0 if angle > 0 else 1.0)

    inner = 0.0 if is_horizon else np.tan(np.radians(CENTER_GAP))
    spans = [(-half_width, -inner), (inner, half_width)] if inner else [(-half_width, half_width)]

    for start, end in spans:
      if is_horizon or angle > 0:
        segments = [(start, end)]
      else:
        segments = self._dashes(start, end)

      for seg_start, seg_end in segments:
        self._line(seg_start, depression, seg_end, depression, roll, thickness, color, rect)

      if not is_horizon:
        outer = start if start < 0 else end
        self._line(outer, depression, outer, depression + tick, roll, thickness, color, rect)

    if not is_horizon:
      self._label(angle, half_width, depression, roll, color, rect)

  @staticmethod
  def _dashes(start: float, end: float) -> list[tuple[float, float]]:
    """Break a dive bar into DASHES segments with equal gaps between them."""
    edges = np.linspace(start, end, DASHES * 2 + 1)
    return [(float(edges[i]), float(edges[i + 1])) for i in range(0, len(edges) - 1, 2)]

  def _label(self, angle: int, half_width: float, depression: float, roll: float,
             color: rl.Color, rect: rl.Rectangle) -> None:
    """The bar's number, off its right end. Upright: a car's roll is too small to be worth rotating text for."""
    point = self._project(half_width, depression, roll, rect)
    if point is None:
      return

    scale = fade_scale(point[1], rect)
    if scale <= 0.0:
      return

    text = str(abs(angle))
    measure = measure_text_cached(self._font, text, LABEL_SIZE, 0)
    position = rl.Vector2(point[0] + LABEL_GAP, point[1] - measure.y / 2)
    rl.draw_text_ex(self._font, text, position, LABEL_SIZE, 0, faded(color, scale))

  def _line(self, y1: float, z1: float, y2: float, z2: float, roll: float,
            thickness: float, color: rl.Color, rect: rl.Rectangle) -> None:
    start = self._project(y1, z1, roll, rect)
    end = self._project(y2, z2, roll, rect)
    if start is None or end is None:
      return

    # one alpha for the whole segment, taken from whichever end is deeper into a
    # band: a bar is near enough to horizontal that splitting it would show a
    # gradient along a line the eye reads as one object
    scale = min(fade_scale(start[1], rect), fade_scale(end[1], rect))
    if scale <= 0.0:
      return

    rl.draw_line_ex(rl.Vector2(*start), rl.Vector2(*end), thickness, faded(color, scale))

  def _project(self, y: float, z: float, roll: float, rect: rl.Rectangle) -> tuple[float, float] | None:
    """Car space at unit distance to screen, rotated about the boresight by roll."""
    angle = ROLL_SIGN * roll
    cos_r, sin_r = np.cos(angle), np.sin(angle)
    pt = self._car_space_transform @ np.array([1.0, y * cos_r - z * sin_r, y * sin_r + z * cos_r])
    if abs(pt[2]) < 1e-6:
      return None

    screen_x, screen_y = pt[0] / pt[2], pt[1] / pt[2]
    # Generous bounds: raylib clips a partly visible bar, but a bar way off
    # screen is wasted work and a wildly wrong one should not be drawn at all.
    if not (rect.x - MARGIN <= screen_x <= rect.x + rect.width + MARGIN):
      return None
    if not (rect.y - MARGIN <= screen_y <= rect.y + rect.height + MARGIN):
      return None

    return (screen_x, screen_y)
