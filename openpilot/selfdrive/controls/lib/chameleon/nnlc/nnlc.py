"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's
sunnypilot/selfdrive/controls/lib/nnlc/nnlc.py + latcontrol_torque_ext.py,
rewritten against upstream's CURRENT LatControlTorque (v1) — sunnypilot's
adapter targets their own modified controller, whose update() takes
calibrated_pose; upstream's does not, so controlsd pushes model/pose/lag state
into this extension between frames instead (see update_calibrated_pose).

Structural differences from sunnypilot, all deliberate:
- The model path is resolved HERE, at construction, from CP. sunnypilot routes
  it card -> CarParamsSP param -> custom.capnp -> controlsd, which exists for
  their process architecture and costs a capnp struct, an opendbc structs
  change and a card.py hook. In-process resolution costs none of that.
- No LatControlTorqueV0: sunnypilot currently routes torque cars through a
  vendored copy of an older upstream controller ("FIXME-SP" for v1 tuning
  issues). Carrying a vendored upstream file contradicts this fork's
  rebaseability thesis, so this port hooks v1 only.
- No EnforceTorqueControl / manual torque override — a separate sunnypilot
  feature, not ported. NNLC also does not force torque tuning onto non-torque
  cars here (sunnypilot's configure_torque_tune); the extension only exists
  where upstream already chose LatControlTorque. Stock tune cars are simply
  out of scope until that is wanted.

The gate is fail-safe three ways, mirroring sunnypilot: the param (read once
at construction — toggling requires a restart), a resolved non-MOCK model, and
a valid modelV2. When any is false, update() returns upstream's own
pid_log/output_torque untouched, bit-for-bit stock behavior.
"""
from collections import deque
import math
import numpy as np

from opendbc.car.lateral import FRICTION_THRESHOLD, get_friction
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.params import Params
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.selfdrive.controls.lib.chameleon.nnlc.ext_base import LatControlTorqueExtBase, sign
from openpilot.selfdrive.controls.lib.chameleon.nnlc.helpers import MOCK_MODEL_PATH, get_nn_model_path
from openpilot.selfdrive.controls.lib.chameleon.nnlc.model import NNTorqueModel
from openpilot.selfdrive.controls.lib.chameleon.nnlc.torque_space import LatControlInputs, get_friction_in_torque_space

LOW_SPEED_X = [0, 10, 20, 30]
LOW_SPEED_Y = [12, 3, 1, 0]


# At a given roll, if pitch magnitude increases, the
# gravitational acceleration component starts pointing
# in the longitudinal direction, decreasing the lateral
# acceleration component. Here we do the same thing
# to the roll value itself, then passed to nnff.
def roll_pitch_adjust(roll, pitch):
  return roll * math.cos(pitch)


class NeuralNetworkLateralControl(LatControlTorqueExtBase):
  def __init__(self, lac_torque, CP):
    super().__init__(lac_torque, CP)
    self.enabled = Params().get_bool("NeuralNetworkLateralControl")

    model_path, self.model_name, exact_match = get_nn_model_path(CP)
    self.fuzzy_fingerprint = not exact_match
    self.has_nn_model = model_path != MOCK_MODEL_PATH

    # NN model takes current v_ego, lateral_accel, lat accel/jerk error, roll, and past/future/planned data
    # of lat accel and roll
    # Past value is computed using previous desired lat accel and observed roll
    self.model = NNTorqueModel(model_path)
    self.calibrated_pose = None

    self.pitch = FirstOrderFilter(0.0, 0.5, 0.01)
    self.pitch_last = 0.0

    # setup future time offsets
    self.future_times = [0.3, 0.6, 1.0, 1.5]  # seconds in the future
    self.nn_future_times = [i + self.desired_lat_jerk_time for i in self.future_times]

    # setup past time offsets
    self.past_times = [-0.3, -0.2, -0.1]
    history_check_frames = [int(abs(i)*100) for i in self.past_times]
    self.history_frame_offsets = [history_check_frames[0] - i for i in history_check_frames]
    self.lateral_accel_desired_deque = deque(maxlen=history_check_frames[0])
    self.roll_deque = deque(maxlen=history_check_frames[0])
    self.past_future_len = len(self.past_times) + len(self.nn_future_times)

    self.update_limits()

  @property
  def _nnlc_enabled(self):
    return self.enabled and self.model_valid and self.has_nn_model

  def update_limits(self):
    # NNLC's PID works in torque space, so its limits are +/-steer_max —
    # upstream's PID limits are in lateral-accel space and would clip wrongly
    self._pid.set_limits(self.lac_torque.steer_max, -self.lac_torque.steer_max)

  def update_calibrated_pose(self, calibrated_pose):
    self.calibrated_pose = calibrated_pose

  def update_lateral_lag(self, lag):
    super().update_lateral_lag(lag)
    self.nn_future_times = [t + self.desired_lat_jerk_time for t in self.future_times]

  def update_feedforward_torque_space(self, CS):
    torque_from_setpoint = self.torque_from_lateral_accel_in_torque_space(LatControlInputs(self._setpoint, self._roll_compensation, CS.vEgo, CS.aEgo),
                                                                          self.torque_params, gravity_adjusted=False)
    torque_from_measurement = self.torque_from_lateral_accel_in_torque_space(LatControlInputs(self._measurement, self._roll_compensation, CS.vEgo, CS.aEgo),
                                                                             self.torque_params, gravity_adjusted=False)
    self._pid_log.error = float(torque_from_setpoint - torque_from_measurement)
    self._ff = self.torque_from_lateral_accel_in_torque_space(LatControlInputs(self._gravity_adjusted_lateral_accel, self._roll_compensation,
                                                                               CS.vEgo, CS.aEgo), self.torque_params, gravity_adjusted=True)
    self._ff += get_friction_in_torque_space(self._desired_lateral_accel - self._actual_lateral_accel, self._lateral_accel_deadzone,
                                             FRICTION_THRESHOLD, self.torque_params)

  def update_output_torque(self, CS):
    freeze_integrator = self._steer_limited_by_safety or CS.steeringPressed or CS.vEgo < 5
    self._output_torque = self._pid.update(self._pid_log.error,
                                           feedforward=self._ff,
                                           speed=CS.vEgo,
                                           freeze_integrator=freeze_integrator)

  def update_neural_network_feedforward(self, CS, params) -> None:
    self.update_feedforward_torque_space(CS)

    low_speed_factor = float(np.interp(CS.vEgo, LOW_SPEED_X, LOW_SPEED_Y)) ** 2
    self._setpoint = self._desired_lateral_accel + low_speed_factor * self._desired_curvature
    self._measurement = self._actual_lateral_accel + low_speed_factor * self._actual_curvature

    # update past data
    roll = params.roll
    if self.calibrated_pose is not None:
      pitch = self.pitch.update(self.calibrated_pose.orientation.pitch)
      roll = roll_pitch_adjust(roll, pitch)
      self.pitch_last = pitch
    self.roll_deque.append(roll)
    self.lateral_accel_desired_deque.append(self._desired_lateral_accel)

    # prepare past and future values
    # adjust future times to account for longitudinal acceleration
    adjusted_future_times = [t + 0.5 * CS.aEgo * (t / max(CS.vEgo, 1.0)) for t in self.nn_future_times]
    past_rolls = [self.roll_deque[min(len(self.roll_deque) - 1, i)] for i in self.history_frame_offsets]
    future_rolls = [roll_pitch_adjust(np.interp(t, ModelConstants.T_IDXS, self.model_v2.orientation.x) + roll,
                                      np.interp(t, ModelConstants.T_IDXS, self.model_v2.orientation.y) + self.pitch_last) for t in
                    adjusted_future_times]
    past_lateral_accels_desired = [self.lateral_accel_desired_deque[min(len(self.lateral_accel_desired_deque) - 1, i)]
                                   for i in self.history_frame_offsets]
    future_planned_lateral_accels = [np.interp(t, ModelConstants.T_IDXS, self.model_v2.acceleration.y) for t in
                                     adjusted_future_times]

    # compute NNFF error response
    nnff_setpoint_input = [CS.vEgo, self._setpoint, self.lateral_jerk_setpoint, roll] \
                          + [self._setpoint] * self.past_future_len \
                          + past_rolls + future_rolls
    # past lateral accel error shouldn't count, so use past desired like the setpoint input
    nnff_measurement_input = [CS.vEgo, self._measurement, self.lateral_jerk_measurement, roll] \
                             + [self._measurement] * self.past_future_len \
                             + past_rolls + future_rolls
    torque_from_setpoint = self.model.evaluate(nnff_setpoint_input)
    torque_from_measurement = self.model.evaluate(nnff_measurement_input)
    self._pid_log.error = torque_from_setpoint - torque_from_measurement

    # The "pure" NNLC error response can be too weak for cars whose models were trained
    # with a lack of high-magnitude lateral acceleration data, for which the NNLC model
    # torque response flattens out at high lateral accelerations.
    # This workaround blends in a guaranteed stronger error response only when the
    # desired lateral acceleration is high enough to warrant it, by using the lateral acceleration
    # error as the input to the NNLC model. This is not ideal, and potentially degrades the NNLC
    # accuracy for cars that don't have this issue, but it's necessary until a better NNLC model
    # structure is used that doesn't create this issue when high-magnitude data is missing.
    error_blend_factor = float(np.interp(abs(self._desired_lateral_accel), [1.0, 2.0], [0.0, 1.0]))
    if error_blend_factor > 0.0:  # blend in stronger error response when in high lat accel
      # NNFF inputs 5+ are optional, and if left out are replaced with 0.0 inside the NNFF class
      nnff_error_input = [CS.vEgo, self._setpoint - self._measurement, self.lateral_jerk_setpoint - self.lateral_jerk_measurement, 0.0]
      torque_from_error = self.model.evaluate(nnff_error_input)
      if sign(self._pid_log.error) == sign(torque_from_error) and abs(self._pid_log.error) < abs(torque_from_error):
        self._pid_log.error = self._pid_log.error * (1.0 - error_blend_factor) + torque_from_error * error_blend_factor

    # compute feedforward (same as nn setpoint output)
    friction_input = self.update_friction_input(self._setpoint, self._measurement)
    nn_input = [CS.vEgo, self._desired_lateral_accel, friction_input, roll] \
               + past_lateral_accels_desired + future_planned_lateral_accels \
               + past_rolls + future_rolls
    self._ff = self.model.evaluate(nn_input)

    # apply friction override for cars with low NN friction response
    if self.model.friction_override:
      self._pid_log.error += get_friction(friction_input, self._lateral_accel_deadzone, FRICTION_THRESHOLD, self.torque_params)

    self.update_output_torque(CS)


class LatControlTorqueExt(NeuralNetworkLateralControl):
  """The adapter upstream's LatControlTorque calls, shaped to v1's locals.

  update() is invoked after upstream computes its own output_torque; when NNLC
  is off (or has no model, or the model plan is stale) the inputs come straight
  back and upstream behavior is bit-for-bit stock.
  """

  def update(self, CS, VM, params, pid_log, setpoint, measurement, roll_compensation, lateral_accel_deadzone,
             desired_lateral_accel, actual_lateral_accel, desired_curvature, actual_curvature,
             gravity_adjusted_lateral_accel, steer_limited_by_safety, output_torque):
    if not self._nnlc_enabled:
      return pid_log, output_torque

    self._pid_log = pid_log
    self._setpoint = setpoint
    self._measurement = measurement
    self._roll_compensation = roll_compensation
    self._lateral_accel_deadzone = lateral_accel_deadzone
    self._desired_lateral_accel = desired_lateral_accel
    self._actual_lateral_accel = actual_lateral_accel
    self._desired_curvature = desired_curvature
    self._actual_curvature = actual_curvature
    self._gravity_adjusted_lateral_accel = gravity_adjusted_lateral_accel
    self._steer_limited_by_safety = steer_limited_by_safety
    self._output_torque = output_torque

    self.update_calculations(CS, VM, desired_lateral_accel)
    self.update_neural_network_feedforward(CS, params)

    return self._pid_log, self._output_torque
