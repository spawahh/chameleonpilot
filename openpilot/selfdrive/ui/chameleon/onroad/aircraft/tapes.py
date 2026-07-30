"""
Aircraft tapes: speed (left), GPS altitude (right), GPS heading (bottom).

Real HUD tapes are moving scales read against a fixed index: the ticks slide,
the current value sits in a boxed readout at the index line. Same here. The
speed tape also carries two bugs, like an airspeed tape's: a filled caret at
the cruise setpoint and a hollow one at the posted speed limit (offline map
data), each pinned to the tape end when it is off-scale.

Data honesty, per element:
- Speed comes from carState with upstream's own vEgoCluster latch, so the tape
  reads exactly what the dash and the stock speedometer read.
- Altitude is GPS (1 Hz on the 3X, smoothed here with a short filter so it
  glides instead of stepping), and it is height above the WGS-84 ellipsoid —
  around 20 m off sea-level maps in the Pacific Northwest. The tape appears
  after the first fix and holds the last value between fixes.
- Heading is GPS course over ground, not a compass: there is no magnetometer,
  and below walking pace the bearing is noise, so the heading tape hides below
  MIN_HEADING_SPEED instead of spinning.
"""
import numpy as np
import pyray as rl

from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

COLOR = rl.Color(0, 255, 70, 230)  # aircraft green, same as the FPV
DIM = rl.Color(0, 255, 70, 140)
BOX_BG = rl.Color(0, 0, 0, 140)

TAPE_HEIGHT = 560.0  # vertical tapes
TAPE_WIDTH = 130.0
EDGE_MARGIN = 50.0  # clear of the accel bar (28 px) and blind spot icons
HEADING_WIDTH = 1000.0
HEADING_BOTTOM_MARGIN = 100.0  # baseline this far above the rect bottom; the readout box hangs below it
TICK = 18.0
THICKNESS = 3.0
CARET = 22.0  # px: the speed bugs' triangle size
LABEL_SIZE = 34
VALUE_SIZE = 52
BOX_PAD = 10.0

MIN_HEADING_SPEED = 3.0  # m/s; below this GPS course is noise
ALT_SMOOTHING_S = 1.0  # glides the 1 Hz GPS steps
CARDINALS = {0: "N", 90: "E", 180: "S", 270: "W"}


class VerticalTape:
  """A moving vertical scale with a boxed readout at its centre index."""

  def __init__(self, font, ticks_on_right: bool, minor_step: float, major_step: float, px_per_unit: float):
    self._font = font
    self._ticks_on_right = ticks_on_right
    self._minor = minor_step
    self._major = major_step
    self._px = px_per_unit

  def draw(self, x: float, cy: float, value: float) -> None:
    half_span = (TAPE_HEIGHT / 2) / self._px
    edge = x + (TAPE_WIDTH if self._ticks_on_right else 0.0)
    direction = -1.0 if self._ticks_on_right else 1.0

    rl.draw_line_ex(rl.Vector2(edge, cy - TAPE_HEIGHT / 2), rl.Vector2(edge, cy + TAPE_HEIGHT / 2), THICKNESS, DIM)

    first = math_floor_to(value - half_span, self._minor)
    tick = first
    while tick <= value + half_span:
      if tick >= 0:
        y = cy - (tick - value) * self._px
        is_major = abs(tick % self._major) < 1e-6
        length = TICK * (1.6 if is_major else 1.0)
        rl.draw_line_ex(rl.Vector2(edge, y), rl.Vector2(edge - direction * length, y), THICKNESS, DIM)
        if is_major:
          label = str(int(tick))
          measure = measure_text_cached(self._font, label, LABEL_SIZE, 0)
          # the label goes beyond the far end of the tick, never back across it:
          # right-side ticks grow rightward so the text starts there, left-side
          # ticks grow leftward so the text has to end there instead
          label_x = edge - direction * (length + 8) - (0.0 if self._ticks_on_right else measure.x)
          rl.draw_text_ex(self._font, label, rl.Vector2(label_x, y - measure.y / 2), LABEL_SIZE, 0, DIM)
      tick += self._minor

    # the boxed readout sits on the index line and covers the ticks under it
    text = str(int(round(value)))
    measure = measure_text_cached(self._font, text, VALUE_SIZE, 0)
    box_w = measure.x + 2 * BOX_PAD
    box_x = edge - box_w if self._ticks_on_right else edge
    box = rl.Rectangle(box_x, cy - measure.y / 2 - BOX_PAD, box_w, measure.y + 2 * BOX_PAD)
    rl.draw_rectangle_rec(box, BOX_BG)
    rl.draw_rectangle_lines_ex(box, 2.0, COLOR)
    rl.draw_text_ex(self._font, text, rl.Vector2(box_x + BOX_PAD, cy - measure.y / 2), VALUE_SIZE, 0, COLOR)

  def draw_bug(self, x: float, cy: float, tape_value: float, bug_value: float, filled: bool) -> None:
    """A caret marking bug_value on the scale, pinned to the tape end when
    off-scale so an out-of-view target still shows which way it is. Sits on
    the tick side, clear of the boxed readout on the other side.
    Filled = the cruise setpoint, hollow = the posted speed limit."""
    half_span = (TAPE_HEIGHT / 2) / self._px
    edge = x + (TAPE_WIDTH if self._ticks_on_right else 0.0)
    direction = -1.0 if self._ticks_on_right else 1.0

    offset = float(np.clip(bug_value - tape_value, -half_span, half_span))
    y = cy - offset * self._px
    apex = rl.Vector2(edge, y)
    base_x = edge - direction * CARET
    v_up = rl.Vector2(base_x, y - CARET / 2)
    v_dn = rl.Vector2(base_x, y + CARET / 2)

    if filled:
      # raylib culls clockwise triangles; the winding flips with the tape side
      verts = (apex, v_up, v_dn) if base_x > edge else (apex, v_dn, v_up)
      rl.draw_triangle(*verts, COLOR)
    else:
      rl.draw_triangle_lines(apex, v_up, v_dn, COLOR)


def math_floor_to(value: float, step: float) -> float:
  return step * np.floor(value / step)


def angle_diff(a: float, b: float) -> float:
  """Signed shortest arc from b to a, degrees in [-180, 180)."""
  return float((a - b + 180.0) % 360.0 - 180.0)


class AircraftTapes:
  def __init__(self):
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)
    dt = 1 / gui_app.target_fps
    self._altitude = FirstOrderFilter(0.0, ALT_SMOOTHING_S, dt)
    self._raw_altitude_m = 0.0
    self._have_fix = False
    self._heading = 0.0
    self._v_ego_cluster_seen = False

  def render(self, rect: rl.Rectangle, sm) -> None:
    if not ui_state.aircraft_tapes:
      return

    if sm.recv_frame['carState'] >= ui_state.started_frame:
      self._draw_speed(rect, sm)

    self._update_gps(sm)
    if self._have_fix:
      self._draw_altitude(rect)
      self._draw_heading(rect, sm)

  # --- speed (left) ---

  def _draw_speed(self, rect: rl.Rectangle, sm) -> None:
    car_state = sm['carState']
    # upstream's own latch, so the tape reads what the dash reads
    self._v_ego_cluster_seen = self._v_ego_cluster_seen or car_state.vEgoCluster != 0.0
    v_ego = car_state.vEgoCluster if self._v_ego_cluster_seen else car_state.vEgo
    conversion = CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH
    speed = max(0.0, v_ego * conversion)

    tape = VerticalTape(self._font, ticks_on_right=True, minor_step=5.0, major_step=10.0,
                        px_per_unit=TAPE_HEIGHT / 20.0)  # 20 units in view, like a real airspeed tape
    x, cy = rect.x + EDGE_MARGIN, rect.y + rect.height / 2
    tape.draw(x, cy, speed)

    # cruise setpoint bug (filled): upstream's own set-speed semantics —
    # km/h with 0/255 sentinels, deprecated vCruise when the cluster is silent
    set_speed = sm['controlsState'].deprecated.vCruise if car_state.vCruiseCluster == 0.0 else car_state.vCruiseCluster
    if 0 < set_speed < 255:
      set_shown = set_speed if ui_state.is_metric else set_speed * CV.KPH_TO_MPH
      tape.draw_bug(x, cy, speed, set_shown, filled=True)

    # posted speed limit bug (hollow), from the offline map data
    live = sm['liveMapData']
    if sm.recv_frame['liveMapData'] >= ui_state.started_frame and live.speedLimitValid:
      tape.draw_bug(x, cy, speed, live.speedLimit * conversion, filled=False)

  # --- altitude (right) ---

  def _update_gps(self, sm) -> None:
    if not sm.updated['gpsLocation']:
      return
    gps = sm['gpsLocation']
    if not gps.hasFix:
      return

    self._raw_altitude_m = gps.altitude  # meters, converted at draw so a unit flip never mixes scales
    if not self._have_fix:
      self._altitude.x = self._raw_altitude_m  # first fix snaps, no glide up from zero
      self._have_fix = True
    self._heading = gps.bearingDeg % 360.0

  def _draw_altitude(self, rect: rl.Rectangle) -> None:
    # per-frame filter pulls toward the held 1 Hz value, so the tape glides
    altitude_m = self._altitude.update(self._raw_altitude_m)
    altitude = altitude_m if ui_state.is_metric else altitude_m * 3.281
    steps = (10.0, 50.0) if ui_state.is_metric else (25.0, 100.0)
    span = 150.0 if ui_state.is_metric else 500.0

    tape = VerticalTape(self._font, ticks_on_right=False, minor_step=steps[0], major_step=steps[1],
                        px_per_unit=TAPE_HEIGHT / span)
    tape.draw(rect.x + rect.width - EDGE_MARGIN - TAPE_WIDTH, rect.y + rect.height / 2, max(0.0, altitude))

  # --- heading (bottom) ---

  def _draw_heading(self, rect: rl.Rectangle, sm) -> None:
    if sm['carState'].vEgo < MIN_HEADING_SPEED:
      return

    cx = rect.x + rect.width / 2
    px_per_deg = HEADING_WIDTH / 120.0  # +/-60 degrees in view
    # bottom-centre: ticks and labels rise above the baseline, the readout box
    # hangs below it, ending clear of the screen edge (DM face is bottom-left)
    baseline = rect.y + rect.height - HEADING_BOTTOM_MARGIN

    rl.draw_line_ex(rl.Vector2(cx - HEADING_WIDTH / 2, baseline), rl.Vector2(cx + HEADING_WIDTH / 2, baseline), THICKNESS, DIM)

    tick = math_floor_to(self._heading - 60.0, 5.0)
    while tick <= self._heading + 60.0:
      x = cx + angle_diff(tick, self._heading) * px_per_deg
      bearing = int(tick % 360.0)
      is_major = bearing % 30 == 0
      length = TICK * (1.6 if is_major else 1.0)
      rl.draw_line_ex(rl.Vector2(x, baseline), rl.Vector2(x, baseline - length), THICKNESS, DIM)
      if is_major:
        label = CARDINALS.get(bearing, f"{bearing:03d}")
        measure = measure_text_cached(self._font, label, LABEL_SIZE, 0)
        rl.draw_text_ex(self._font, label, rl.Vector2(x - measure.x / 2, baseline - length - measure.y - 2), LABEL_SIZE, 0, DIM)
      tick += 5.0

    text = f"{int(round(self._heading)) % 360:03d}"
    measure = measure_text_cached(self._font, text, VALUE_SIZE, 0)
    box = rl.Rectangle(cx - measure.x / 2 - BOX_PAD, baseline + 4.0, measure.x + 2 * BOX_PAD, measure.y + 2 * BOX_PAD)
    rl.draw_rectangle_rec(box, BOX_BG)
    rl.draw_rectangle_lines_ex(box, 2.0, COLOR)
    rl.draw_text_ex(self._font, text, rl.Vector2(cx - measure.x / 2, box.y + BOX_PAD), VALUE_SIZE, 0, COLOR)
