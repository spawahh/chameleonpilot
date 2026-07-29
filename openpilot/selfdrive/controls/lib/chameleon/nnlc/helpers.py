"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's
sunnypilot/selfdrive/controls/lib/nnlc/helpers.py. Differences from the
original, all deliberate:
- The weights live in this package's ./data directory (vendored, not a
  submodule — submodule contents don't travel in this fork's git-bundle
  workflow), so the path constants point there.
- An empty/missing weights directory resolves to MOCK instead of raising
  TypeError on `car_fingerprint not in None`.
- The matcher's behavior is otherwise verbatim, quirks included — sunnypilot's
  test_fingerprint is the spec. That includes the substitute loop whose first
  iteration is dead work (both candidates are checked but only the last
  result survives).
"""
import os
import tomllib
from difflib import SequenceMatcher

from opendbc.car import structs
from openpilot.common.basedir import BASEDIR

TORQUE_NN_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TORQUE_NN_MODEL_SUBSTITUTE_PATH = os.path.join(BASEDIR, "opendbc_repo", "opendbc", "car", "torque_data/substitute.toml")
MOCK_MODEL_PATH = os.path.join(TORQUE_NN_MODEL_PATH, "MOCK.json")


def similarity(s1: str, s2: str) -> float:
  return SequenceMatcher(None, s1, s2).ratio()


def get_nn_model_path(CP) -> tuple[str, str, bool]:
  car_fingerprint = CP.carFingerprint
  eps_fw = str(next((fw.fwVersion for fw in CP.carFw if fw.ecu == "eps"), ""))

  def check_nn_path(_nn_candidate):
    _model_path = None
    _max_similarity = -1.0
    for f in os.listdir(TORQUE_NN_MODEL_PATH):
      if f.endswith(".json"):
        model = os.path.splitext(f)[0]
        similarity_score = similarity(model, _nn_candidate)
        if similarity_score > _max_similarity:
          _max_similarity = similarity_score
          _model_path = os.path.join(TORQUE_NN_MODEL_PATH, f)
    return _model_path, _max_similarity

  if len(eps_fw) > 3:
    eps_fw = eps_fw.replace("\\", "")
    nn_candidate = f"{car_fingerprint} {eps_fw}"
  else:
    nn_candidate = car_fingerprint

  model_path, max_similarity = check_nn_path(nn_candidate)
  if model_path is None:
    return MOCK_MODEL_PATH, "MOCK", False
  exact_match = max_similarity >= 0.99

  if car_fingerprint not in model_path or 0.0 <= max_similarity < 0.9:
    nn_candidate = car_fingerprint
    model_path, max_similarity = check_nn_path(nn_candidate)
    exact_match = max_similarity >= 0.99

    if 0.0 <= max_similarity < 0.9:
      with open(TORQUE_NN_MODEL_SUBSTITUTE_PATH, 'rb') as f:
        sub = tomllib.load(f)
      sub_candidate = sub.get(car_fingerprint, car_fingerprint)

      for candidate in [car_fingerprint, sub_candidate]:
        model_path, max_similarity = check_nn_path(candidate)

      exact_match = False

  if CP.steerControlType == structs.CarParams.SteerControlType.angle:
    model_path = MOCK_MODEL_PATH

  model_name = os.path.splitext(os.path.basename(model_path))[0]

  return model_path, model_name, exact_match
