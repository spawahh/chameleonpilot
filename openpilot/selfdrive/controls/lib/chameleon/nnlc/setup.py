"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from the NNLC half of sunnypilot's
sunnypilot/selfdrive/car/interfaces.py (_initialize_torque_lateral_control).

Why this exists: controlsd only constructs LatControlTorque — the controller
NNLC extends — when `CP.lateralTuning.which() == 'torque'`. Plenty of
platforms with trained models ship a PID tune upstream (the 2022 Crosstrek,
SUBARU_IMPREZA_2020, is one), so without this hook the NNLC toggle would
silently do nothing on exactly the cars it was ported for. When NNLC will
genuinely arm, the car is moved onto upstream's own torque tune for its
platform; in every other case CP leaves this function untouched.

card calls this while CP is still a builder, before it is serialized.
"""
from opendbc.car import structs
from opendbc.car.interfaces import CarInterfaceBase
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.controls.lib.chameleon.nnlc.helpers import get_nn_model_path


def setup_nnlc(CP, params) -> None:
  if not params.get_bool("NeuralNetworkLateralControl"):
    return

  if CP.steerControlType == structs.CarParams.SteerControlType.angle:
    cloudlog.warning("chameleon nnlc: angle-steering car, staying stock")
    return

  _, model_name, exact_match = get_nn_model_path(CP)
  if model_name == "MOCK":
    cloudlog.error({"chameleon nnlc": "car doesn't match any Neural Network model, staying stock"})
    return

  if CP.lateralTuning.which() != 'torque':
    cloudlog.warning(f"chameleon nnlc: switching {CP.carFingerprint} from {CP.lateralTuning.which()} to torque tune (model {model_name}, exact={exact_match})")
    CarInterfaceBase.configure_torque_tune(CP.carFingerprint, CP.lateralTuning)
