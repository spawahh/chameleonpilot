"""
Target designator (TD), aircraft HUD symbology for the lead vehicle.

Four corner brackets around the lead car with a range and closing-rate
readout, replacing the stock chevron while the toggle is on
(ChameleonModelRenderer suppresses the chevron for exactly this flag).

Two gates are deliberately different from the chevron's:
- NOT gated on openpilot longitudinal control. The chevron is, which is why a
  stock-ACC car never sees a lead marker at all. The designator is
  information, not a control cue, so it draws wherever a lead is tracked.
- Keyed on `lead.present`, never `lead.status` — on radarless cars radarState
  is vision-fused and only sets present/modelProb.

The urgency ramp is the chevron's exact formula (40 m buffer, 10 m/s closing
buffer), mapped to a color lerp toward the chevron red — which the theme
safety test pins identical across themes — and thicker brackets. A theme
cannot dim the warning.
"""
import numpy as np
import pyray as rl

from openpilot.common.constants import CV
from openpilot.selfdrive.locationd.calibrationd import HEIGHT_INIT
from openpilot.selfdrive.ui.themes import ROAD_COLORS
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

LEAD_BUFF = 40.0  # m, the chevron's distance ramp
SPEED_BUFF = 10.0  # m/s, the chevron's closing-speed ramp
CAR_HALF_WIDTH = 1.1  # m each side; the box hugs a ~2.2 m vehicle
MIN_WIDTH, MAX_WIDTH = 60.0, 240.0  # px
HEIGHT_RATIO = 0.75
ARM = 0.3  # bracket arm length, fraction of the box side
MIN_THICKNESS, MAX_THICKNESS = 4.0, 8.0
COLOR = rl.Color(0, 255, 70, 230)  # aircraft green, same as the FPV
SECOND_LEAD_ALPHA = 90
MIN_LEAD_GAP = 3.0  # m; closer than this the two vision-fused leads shadow each other
READOUT_SIZE = 36
READOUT_GAP = 14.0  # px between box and text
MIN_CLOSING_RATE = 0.5  # m/s before the closing readout appears


class TargetDesignator:
  def __init__(self):
    self._car_space_transform = np.zeros((3, 3), dtype=np.float32)
    self._height = HEIGHT_INIT[0]
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)

  def set_transform(self, transform: np.ndarray) -> None:
    self._car_space_transform = transform.astype(np.float32)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if not ui_state.target_designator:
      return

    if sm.recv_frame['radarState'] < ui_state.started_frame or not sm.valid['radarState']:
      return

    calib_height = sm['liveCalibration'].height
    if len(calib_height):
      self._height = calib_height[0]

    position = sm['modelV2'].position
    lead_one, lead_two = sm['radarState'].leadOne, sm['radarState'].leadTwo

    if lead_one.present:
      self._draw_lead(lead_one, position, rect, primary=True)

      if lead_two.present and abs(lead_two.dRel - lead_one.dRel) > MIN_LEAD_GAP:
        self._draw_lead(lead_two, position, rect, primary=False)

  def _draw_lead(self, lead, position, rect: rl.Rectangle, primary: bool) -> None:
    z = float(np.interp(lead.dRel, position.x, position.z)) if len(position.x) else 0.0

    center = self._project(lead.dRel, -lead.yRel, z + self._height)
    edge = self._project(lead.dRel, -lead.yRel + CAR_HALF_WIDTH, z + self._height)
    if center is None or edge is None:
      return

    width = float(np.clip(2 * abs(edge[0] - center[0]), MIN_WIDTH, MAX_WIDTH))
    height = width * HEIGHT_RATIO

    # a very close lead pins at the screen edge instead of vanishing, like the chevron
    x = float(np.clip(center[0], rect.x + width / 2, rect.x + rect.width - width / 2))
    y = float(np.clip(center[1], rect.y + height / 2, rect.y + rect.height - height / 2))

    urgency = self._urgency(lead.dRel, lead.vRel)
    if primary:
      color = self._blend(COLOR, ROAD_COLORS.LEAD_CHEVRON, urgency / 255.0)
      thickness = MIN_THICKNESS + (MAX_THICKNESS - MIN_THICKNESS) * (urgency / 255.0)
    else:
      color = rl.Color(COLOR.r, COLOR.g, COLOR.b, SECOND_LEAD_ALPHA)
      thickness = MIN_THICKNESS

    self._draw_brackets(x, y, width, height, thickness, color)
    if primary:
      self._draw_readout(lead, x, y + height / 2 + READOUT_GAP, color)

  @staticmethod
  def _urgency(d_rel: float, v_rel: float) -> float:
    """The chevron's fill-alpha formula, verbatim semantics."""
    if d_rel >= LEAD_BUFF:
      return 0.0
    urgency = 255 * (1.0 - (d_rel / LEAD_BUFF))
    if v_rel < 0:
      urgency += 255 * (-1 * (v_rel / SPEED_BUFF))
    return min(urgency, 255.0)

  @staticmethod
  def _blend(a: rl.Color, b: rl.Color, t: float) -> rl.Color:
    return rl.Color(int(a.r + (b.r - a.r) * t), int(a.g + (b.g - a.g) * t),
                    int(a.b + (b.b - a.b) * t), a.a)

  @staticmethod
  def _draw_brackets(x: float, y: float, width: float, height: float, thickness: float, color: rl.Color) -> None:
    half_w, half_h = width / 2, height / 2
    arm_x, arm_y = width * ARM, height * ARM

    for sx in (-1, 1):
      for sy in (-1, 1):
        corner_x, corner_y = x + sx * half_w, y + sy * half_h
        rl.draw_line_ex(rl.Vector2(corner_x, corner_y), rl.Vector2(corner_x - sx * arm_x, corner_y), thickness, color)
        rl.draw_line_ex(rl.Vector2(corner_x, corner_y), rl.Vector2(corner_x, corner_y - sy * arm_y), thickness, color)

  def _draw_readout(self, lead, x: float, top_y: float, color: rl.Color) -> None:
    if ui_state.is_metric:
      text = f"{lead.dRel:.0f} m"
      closing = lead.vRel * CV.MS_TO_KPH
      unit = "km/h"
    else:
      text = f"{lead.dRel * 3.281:.0f} ft"
      closing = lead.vRel * CV.MS_TO_MPH
      unit = "mph"

    if abs(lead.vRel) > MIN_CLOSING_RATE:
      text += f"  {closing:+.0f} {unit}"

    measure = measure_text_cached(self._font, text, READOUT_SIZE, 0)
    rl.draw_text_ex(self._font, text, rl.Vector2(x - measure.x / 2, top_y), READOUT_SIZE, 0, color)

  def _project(self, x: float, y: float, z: float) -> tuple[float, float] | None:
    pt = self._car_space_transform @ np.array([x, y, z])
    if abs(pt[2]) < 1e-6:
      return None

    return (pt[0] / pt[2], pt[1] / pt[2])
