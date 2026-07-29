"""NNLC port tests.

Three things pinned: the fuzzy fingerprint matcher (sunnypilot's
test_fingerprint cases are the spec), real-weights model loading, and — the
one that matters most — the extension returning upstream's values UNTOUCHED
whenever NNLC is not armed. That passthrough is the whole safety story of
this port: off, no model, or stale plan must all mean bit-for-bit stock
steering.
"""
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from openpilot.selfdrive.controls.lib.chameleon.nnlc.helpers import MOCK_MODEL_PATH, TORQUE_NN_MODEL_PATH, get_nn_model_path
from openpilot.selfdrive.controls.lib.chameleon.nnlc.model import NNTorqueModel
from openpilot.selfdrive.controls.lib.chameleon.nnlc.nnlc import LatControlTorqueExt
from openpilot.selfdrive.modeld.constants import ModelConstants

TORQUE = 0  # structs.CarParams.SteerControlType.torque
ANGLE = 1  # structs.CarParams.SteerControlType.angle


def fake_cp(fingerprint, steer_control_type=TORQUE, eps_fw=""):
  fw = [SimpleNamespace(ecu="eps", fwVersion=eps_fw)] if eps_fw else []
  return SimpleNamespace(carFingerprint=fingerprint, carFw=fw,
                         steerControlType=steer_control_type, steerActuatorDelay=0.2)


class TestFingerprintMatching(unittest.TestCase):
  """sunnypilot's test_fingerprint cases, driven through the ported matcher."""

  def test_exact_matches(self):
    for platform in ("HONDA_CIVIC_BOSCH", "TOYOTA_RAV4_TSS2_2022", "HYUNDAI_IONIQ_5", "SUBARU_IMPREZA_2020"):
      path, name, exact = get_nn_model_path(fake_cp(platform))
      self.assertNotEqual(name, "MOCK", platform)
      self.assertTrue(exact, platform)
      self.assertIn(platform, path, platform)

  def test_fuzzy_matches(self):
    for platform in ("HONDA_CIVIC_BOSCH_DIESEL", "GENESIS_G70_2020", "HYUNDAI_IONIQ_6"):
      path, name, exact = get_nn_model_path(fake_cp(platform))
      self.assertNotEqual(name, "MOCK", platform)
      self.assertFalse(exact, platform)

  def test_angle_cars_get_mock(self):
    """Angle-steering cars are forced to MOCK whatever the name similarity."""
    path, name, _ = get_nn_model_path(fake_cp("TESLA_MODEL_3", steer_control_type=ANGLE))
    self.assertEqual(name, "MOCK")
    self.assertEqual(path, MOCK_MODEL_PATH)

  def test_empty_weights_dir_resolves_to_mock(self):
    """The port's divergence from sunnypilot: no weights means MOCK, not a crash."""
    with mock.patch("openpilot.selfdrive.controls.lib.chameleon.nnlc.helpers.os.listdir", return_value=[]):
      path, name, exact = get_nn_model_path(fake_cp("SUBARU_IMPREZA_2020"))

    self.assertEqual(name, "MOCK")
    self.assertFalse(exact)


class TestModelLoading(unittest.TestCase):
  def test_crosstrek_model_loads_and_evaluates(self):
    model = NNTorqueModel(f"{TORQUE_NN_MODEL_PATH}/SUBARU_IMPREZA_2020.json")

    self.assertEqual(model.input_size, 18)
    out = model.evaluate([10.0, 1.0, 0.1, 0.0] + [0.0] * 14)
    self.assertIsInstance(out, float)
    self.assertTrue(np.isfinite(out))

  def test_short_input_padding(self):
    model = NNTorqueModel(f"{TORQUE_NN_MODEL_PATH}/SUBARU_IMPREZA_2020.json")

    self.assertTrue(np.isfinite(model.evaluate([10.0, 0.0, 0.2])))
    with self.assertRaises(ValueError):
      model.evaluate([10.0])

  def test_every_vendored_model_parses(self):
    """All 114 weights files load, validate their activations, and evaluate."""
    import os
    files = [f for f in os.listdir(TORQUE_NN_MODEL_PATH) if f.endswith(".json")]
    self.assertGreaterEqual(len(files), 100)
    for f in files:
      model = NNTorqueModel(f"{TORQUE_NN_MODEL_PATH}/{f}")
      self.assertTrue(np.isfinite(model.evaluate([10.0, 0.0, 0.2])), f)


def fake_lac_torque(steer_max=1.0):
  torque_params = SimpleNamespace(latAccelFactor=2.5, latAccelOffset=0.0, friction=0.1)
  return SimpleNamespace(torque_params=torque_params, steer_max=steer_max)


def fake_model_v2(n=33):
  zeros = [0.0] * n
  return SimpleNamespace(orientation=SimpleNamespace(x=zeros, y=zeros),
                         acceleration=SimpleNamespace(y=[0.5] * n))


def fake_cs(v_ego=25.0):
  return SimpleNamespace(vEgo=v_ego, aEgo=0.0, steeringRateDeg=0.0, steeringPressed=False)


class TestStockPassthrough(unittest.TestCase):
  """The safety pin: an unarmed extension must hand back exactly what it got."""

  def _ext(self, enabled=False, fingerprint="SUBARU_IMPREZA_2020"):
    with mock.patch("openpilot.selfdrive.controls.lib.chameleon.nnlc.nnlc.Params") as params:
      params.return_value.get_bool.return_value = enabled
      return LatControlTorqueExt(fake_lac_torque(), fake_cp(fingerprint))

  def _update(self, ext, pid_log, output_torque=0.42):
    return ext.update(fake_cs(), mock.Mock(), SimpleNamespace(roll=0.0), pid_log,
                      setpoint=1.0, measurement=0.9, roll_compensation=0.0, lateral_accel_deadzone=0.01,
                      desired_lateral_accel=1.0, actual_lateral_accel=0.9, desired_curvature=0.002,
                      actual_curvature=0.0018, gravity_adjusted_lateral_accel=1.0,
                      steer_limited_by_safety=False, output_torque=output_torque)

  def test_disabled_is_identity(self):
    ext = self._ext(enabled=False)
    ext.update_model_v2(fake_model_v2())
    pid_log = SimpleNamespace(error=0.123)

    out_log, out_torque = self._update(ext, pid_log, output_torque=0.42)

    self.assertIs(out_log, pid_log)
    self.assertEqual(out_log.error, 0.123)
    self.assertEqual(out_torque, 0.42)

  def test_enabled_without_model_plan_is_identity(self):
    """modelV2 missing or too short means not armed, even with the toggle on."""
    ext = self._ext(enabled=True)
    ext.update_model_v2(None)
    pid_log = SimpleNamespace(error=0.123)

    _, out_torque = self._update(ext, pid_log, output_torque=0.42)

    self.assertEqual(out_torque, 0.42)
    self.assertFalse(ext._nnlc_enabled)

  def test_mock_model_is_identity(self):
    """A car with no trained model never arms, whatever the toggle says."""
    ext = self._ext(enabled=True, fingerprint="TESLA_MODEL_3")
    # Tesla resolves through the fuzzy matcher to *something*, so force the
    # no-model condition the way an angle car would hit it
    ext.has_nn_model = False
    ext.update_model_v2(fake_model_v2())

    _, out_torque = self._update(ext, SimpleNamespace(error=0.0), output_torque=0.42)

    self.assertEqual(out_torque, 0.42)


class TestTorqueTuneSetup(unittest.TestCase):
  """The arming chain: platforms with a trained model but a stock PID tune
  (the 2022 Crosstrek among them) must be moved onto torque tuning when the
  toggle is on — otherwise controlsd never constructs LatControlTorque and
  the toggle silently does nothing. Found on the real car's CarParams."""

  def _cp(self, which='pid'):
    from opendbc.car import structs
    CP = structs.CarParams()
    CP.carFingerprint = "SUBARU_IMPREZA_2020"
    CP.steerControlType = structs.CarParams.SteerControlType.torque
    getattr(CP.lateralTuning, 'init', lambda *_: None)
    if which == 'pid':
      CP.lateralTuning.pid = structs.CarParams.LateralPIDTuning()
    else:
      CP.lateralTuning.torque = structs.CarParams.LateralTorqueTuning()
    return CP

  def _params(self, enabled):
    p = mock.Mock()
    p.get_bool.return_value = enabled
    return p

  def test_toggle_off_leaves_stock_tune(self):
    from openpilot.selfdrive.controls.lib.chameleon.nnlc.setup import setup_nnlc
    CP = self._cp('pid')

    setup_nnlc(CP, self._params(False))

    self.assertEqual(CP.lateralTuning.which(), 'pid')

  def test_toggle_on_switches_pid_car_to_torque(self):
    from openpilot.selfdrive.controls.lib.chameleon.nnlc.setup import setup_nnlc
    CP = self._cp('pid')

    setup_nnlc(CP, self._params(True))

    self.assertEqual(CP.lateralTuning.which(), 'torque')
    self.assertGreater(CP.lateralTuning.torque.latAccelFactor, 0.0)

  def test_mock_car_stays_stock_even_when_on(self):
    from openpilot.selfdrive.controls.lib.chameleon.nnlc import setup as setup_mod
    CP = self._cp('pid')

    with mock.patch.object(setup_mod, 'get_nn_model_path', return_value=("x", "MOCK", False)):
      setup_mod.setup_nnlc(CP, self._params(True))

    self.assertEqual(CP.lateralTuning.which(), 'pid')


class TestArmedBehavior(unittest.TestCase):
  def _armed_ext(self):
    with mock.patch("openpilot.selfdrive.controls.lib.chameleon.nnlc.nnlc.Params") as params:
      params.return_value.get_bool.return_value = True
      ext = LatControlTorqueExt(fake_lac_torque(steer_max=1.0), fake_cp("SUBARU_IMPREZA_2020"))
    ext.update_model_v2(fake_model_v2())
    self_check = ext._nnlc_enabled
    assert self_check, "fixture must arm"
    return ext

  def _update(self, ext, desired=1.0, actual=0.0):
    vm = mock.Mock()
    vm.calc_curvature.return_value = 0.0
    return ext.update(fake_cs(), vm, SimpleNamespace(roll=0.0), SimpleNamespace(error=0.0),
                      setpoint=desired, measurement=actual, roll_compensation=0.0, lateral_accel_deadzone=0.01,
                      desired_lateral_accel=desired, actual_lateral_accel=actual, desired_curvature=desired / 625.0,
                      actual_curvature=actual / 625.0, gravity_adjusted_lateral_accel=desired,
                      steer_limited_by_safety=False, output_torque=0.0)

  def test_armed_overrides_torque(self):
    ext = self._armed_ext()

    for _ in range(5):
      pid_log, torque = self._update(ext, desired=1.5, actual=0.0)

    self.assertNotEqual(torque, 0.0)
    self.assertTrue(np.isfinite(torque))
    self.assertTrue(np.isfinite(pid_log.error))

  def test_output_respects_torque_space_limits(self):
    """The NNLC PID clamps at +/-steer_max in torque space."""
    ext = self._armed_ext()

    for _ in range(200):
      _, torque = self._update(ext, desired=4.0, actual=-4.0)

    self.assertLessEqual(abs(torque), ext.lac_torque.steer_max + 1e-6)

  def test_steering_toward_the_error(self):
    ext = self._armed_ext()

    for _ in range(5):
      _, torque_right = self._update(ext, desired=1.5, actual=0.0)
    ext2 = self._armed_ext()
    for _ in range(5):
      _, torque_left = self._update(ext2, desired=-1.5, actual=0.0)

    self.assertGreater(torque_right, 0.0)
    self.assertLess(torque_left, 0.0)

  def test_model_plan_horizon_matches_t_idxs(self):
    """The lookahead interpolates over ModelConstants.T_IDXS; a fixture shorter
    than CONTROL_N must disarm rather than extrapolate."""
    ext = self._armed_ext()
    ext.update_model_v2(fake_model_v2(n=5))

    self.assertFalse(ext._nnlc_enabled)
    self.assertEqual(len(ModelConstants.T_IDXS), 33)


if __name__ == '__main__':
  unittest.main()
