"""
Flight path vector (FPV), the first element of the aircraft HUD layout.

An aircraft HUD draws a small winged circle where the aircraft is actually
going, which is not where it is pointing. Same idea here: the symbol sits on
the spot down the road the car is currently travelling towards.

chameleonpilot original. The car-space to screen projection is the same
transform upstream's ModelRenderer uses, so the symbol lands in the same frame
as the path and the lead markers. modelV2.velocity shares modelV2.position's
frame, so no sign flip is needed (unlike radar's yRel, which ModelRenderer
negates).
"""
import numpy as np
import pyray as rl

from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.selfdrive.locationd.calibrationd import HEIGHT_INIT
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app

LOOKAHEAD = 32.0  # m down the road, where the symbol is drawn
MIN_SPEED = 2.0  # m/s; below walking pace the travel direction is noise
SMOOTHING = 0.35  # s, time constant on the direction

RADIUS = 26.0
WING = 30.0  # length of each horizontal wing, outside the circle
FIN = 18.0  # length of the vertical fin, above the circle
THICKNESS = 5.0
COLOR = rl.Color(0, 255, 70, 230)


class FlightPathVector:
  def __init__(self):
    self._car_space_transform = np.zeros((3, 3), dtype=np.float32)
    dt = 1 / gui_app.target_fps
    self._y_ratio = FirstOrderFilter(0.0, SMOOTHING, dt)
    self._z_ratio = FirstOrderFilter(0.0, SMOOTHING, dt)

  def set_transform(self, transform: np.ndarray) -> None:
    self._car_space_transform = transform.astype(np.float32)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if not ui_state.flight_path_vector:
      return

    if sm.recv_frame['modelV2'] < ui_state.started_frame:
      return

    velocity = sm['modelV2'].velocity
    if len(velocity.x) == 0:
      return

    v_forward, v_lateral, v_vertical = velocity.x[0], velocity.y[0], velocity.z[0]

    # Real HUDs cage the FPV to straight ahead at low speed, where the
    # direction is undefined and the symbol would otherwise thrash
    if v_forward < MIN_SPEED:
      y_ratio = self._y_ratio.update(0.0)
      z_ratio = self._z_ratio.update(0.0)
    else:
      y_ratio = self._y_ratio.update(v_lateral / v_forward)
      z_ratio = self._z_ratio.update(v_vertical / v_forward)

    point = self._project(LOOKAHEAD, y_ratio * LOOKAHEAD, z_ratio * LOOKAHEAD + HEIGHT_INIT[0], rect)
    if point is None:
      return

    self._draw(*point)

  def _project(self, x: float, y: float, z: float, rect: rl.Rectangle) -> tuple[float, float] | None:
    pt = self._car_space_transform @ np.array([x, y, z])
    if abs(pt[2]) < 1e-6:
      return None

    screen_x, screen_y = pt[0] / pt[2], pt[1] / pt[2]
    if not (rect.x <= screen_x <= rect.x + rect.width and rect.y <= screen_y <= rect.y + rect.height):
      return None

    return (screen_x, screen_y)

  @staticmethod
  def _draw(x: float, y: float) -> None:
    rl.draw_ring(rl.Vector2(x, y), RADIUS - THICKNESS / 2, RADIUS + THICKNESS / 2, 0, 360, 36, COLOR)
    rl.draw_line_ex(rl.Vector2(x - RADIUS - WING, y), rl.Vector2(x - RADIUS, y), THICKNESS, COLOR)
    rl.draw_line_ex(rl.Vector2(x + RADIUS, y), rl.Vector2(x + RADIUS + WING, y), THICKNESS, COLOR)
    rl.draw_line_ex(rl.Vector2(x, y - RADIUS - FIN), rl.Vector2(x, y - RADIUS), THICKNESS, COLOR)
