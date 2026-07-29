"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's opendbc extensions
(opendbc/sunnypilot/car/interfaces.py LatControlInputs +
torque_from_lateral_accel_linear_in_torque_space, and
opendbc/sunnypilot/car/lateral_ext.py get_friction). Lives here as a fork
module because chameleonpilot pins commaai's opendbc unmodified.

Only the linear (generic) torque-space conversion is ported. sunnypilot also
carries a GM-specific override; on a GM car this port's NNLC will be slightly
off in the same way every non-GM car is exact — noted, not implemented.
"""
from typing import NamedTuple

import numpy as np

from opendbc.car.lateral import apply_center_deadzone


class LatControlInputs(NamedTuple):
  lateral_acceleration: float
  roll_compensation: float
  vego: float
  aego: float


def torque_from_lateral_accel_in_torque_space(latcontrol_inputs: LatControlInputs, torque_params, gravity_adjusted: bool) -> float:
  # The default is a linear relationship between torque and lateral acceleration (accounting for road roll and steering friction)
  return latcontrol_inputs.lateral_acceleration / float(torque_params.latAccelFactor)


def get_friction_in_torque_space(lateral_accel_error: float, lateral_accel_deadzone: float, friction_threshold: float, torque_params) -> float:
  friction_interp = np.interp(
    apply_center_deadzone(lateral_accel_error, lateral_accel_deadzone),
    [-friction_threshold, friction_threshold],
    [-torque_params.friction, torque_params.friction]
  )
  return float(friction_interp)
