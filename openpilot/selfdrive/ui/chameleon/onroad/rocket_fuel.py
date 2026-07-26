"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's selfdrive/ui/sunnypilot/onroad/rocket_fuel.py.
The bar geometry is sunnypilot's, quirks included: the 0.1/accel term means nothing draws
below about 0.12 m/s^2, and only half the computed height is filled.
"""
import pyray as rl

from openpilot.selfdrive.ui.ui_state import ui_state

BAR_WIDTH = 28.0
MAX_HEIGHT_FRACTION = 0.85  # only extend up to 85% of the screen
SMOOTHING = 5.0  # frames of lag on the displayed value
ACCEL_COLOR = rl.Color(0, 245, 0, 200)
DECEL_COLOR = rl.Color(245, 0, 0, 200)


class RocketFuel:
  def __init__(self):
    self.vc_accel = 0.0

  def render(self, rect: rl.Rectangle, sm) -> None:
    if not ui_state.rocket_fuel:
      return

    vc_accel0 = sm['carState'].aEgo

    # Smooth the acceleration
    self.vc_accel = self.vc_accel + (vc_accel0 - self.vc_accel) / SMOOTHING

    hha = 0.0
    color = rl.Color(0, 0, 0, 0)  # Transparent by default

    if self.vc_accel > 0:
      hha = MAX_HEIGHT_FRACTION - 0.1 / self.vc_accel
      color = ACCEL_COLOR
    elif self.vc_accel < 0:
      hha = MAX_HEIGHT_FRACTION + 0.1 / self.vc_accel
      color = DECEL_COLOR

    if hha < 0:
      hha = 0.0

    hha = hha * rect.height

    # Accelerating grows the bar out from the centre; braking grows it downward
    if self.vc_accel > 0:
      ra_y = rect.height / 2.0 - hha / 2.0
    else:
      ra_y = rect.height / 2.0

    if hha > 0:
      rl.draw_rectangle(int(rect.x), int(rect.y + ra_y), int(BAR_WIDTH), int(hha / 2.0), color)
