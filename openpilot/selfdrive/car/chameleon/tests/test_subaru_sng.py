"""The param -> CarParams plumbing for Subaru stop-and-go.

The thing worth pinning here is that the two fields move together. CP.flags alone
arms the car-layer code while panda still blocks the messages; safetyParam alone
opens the allowlist for a feature that never transmits. Either half on its own is
a silent failure, so every test asserts both.
"""
import unittest
from unittest import mock

from opendbc.car import structs
from opendbc.car.subaru.values import SubaruFlags, SubaruSafetyFlags
from openpilot.selfdrive.car.chameleon.subaru_sng import setup_subaru_stop_and_go

SNG_FLAG = SubaruFlags.STOP_AND_GO_MANUAL_PARKING_BRAKE.value
SNG_SAFETY = SubaruSafetyFlags.STOP_AND_GO.value


def car_params(brand="subaru", flags=0, op_long=False):
  CP = structs.CarParams()
  CP.brand = brand
  CP.carFingerprint = "SUBARU_IMPREZA_2020"
  CP.flags = flags
  CP.openpilotLongitudinalControl = op_long
  CP.safetyConfigs = [structs.CarParams.SafetyConfig()]
  CP.safetyConfigs[0].safetyModel = structs.CarParams.SafetyModel.subaru
  return CP


def params(enabled):
  p = mock.Mock()
  p.get_bool.return_value = enabled
  return p


class TestSetupSubaruStopAndGo(unittest.TestCase):
  def assertArmed(self, CP):
    self.assertTrue(CP.flags & SNG_FLAG, "car-layer flag not set")
    self.assertTrue(CP.safetyConfigs[0].safetyParam & SNG_SAFETY, "safety param not set")

  def assertStock(self, CP):
    self.assertFalse(CP.flags & SNG_FLAG, "car-layer flag set when it should not be")
    self.assertFalse(CP.safetyConfigs[0].safetyParam & SNG_SAFETY, "safety param set when it should not be")

  def test_arms_on_an_eligible_subaru(self):
    CP = car_params()
    setup_subaru_stop_and_go(CP, params(True))
    self.assertArmed(CP)

  def test_toggle_off_stays_stock(self):
    CP = car_params()
    setup_subaru_stop_and_go(CP, params(False))
    self.assertStock(CP)

  def test_other_brands_are_untouched(self):
    # the flag value is Subaru's; setting it on a Toyota would mean something else
    for brand in ("toyota", "honda", "hyundai"):
      with self.subTest(brand=brand):
        CP = car_params(brand=brand)
        setup_subaru_stop_and_go(CP, params(True))
        self.assertStock(CP)

  def test_gen2_is_refused(self):
    # the panda allowlist was only widened on the non-GEN2 path
    CP = car_params(flags=SubaruFlags.GLOBAL_GEN2.value)
    setup_subaru_stop_and_go(CP, params(True))
    self.assertStock(CP)

  def test_hybrid_is_refused(self):
    # hybrids have no Throttle on the powertrain bus for the car layer to copy
    CP = car_params(flags=SubaruFlags.HYBRID.value)
    setup_subaru_stop_and_go(CP, params(True))
    self.assertStock(CP)

  def test_openpilot_longitudinal_is_refused(self):
    # this feature drives the CAR's ACC; with openpilot long there is none to nudge
    CP = car_params(op_long=True)
    setup_subaru_stop_and_go(CP, params(True))
    self.assertStock(CP)

  def test_existing_flags_and_safety_params_survive(self):
    CP = car_params(flags=SubaruFlags.SEND_INFOTAINMENT.value)
    CP.safetyConfigs[0].safetyParam = SubaruSafetyFlags.GEN2.value

    setup_subaru_stop_and_go(CP, params(True))

    self.assertArmed(CP)
    self.assertTrue(CP.flags & SubaruFlags.SEND_INFOTAINMENT.value)
    self.assertTrue(CP.safetyConfigs[0].safetyParam & SubaruSafetyFlags.GEN2.value)

  def test_it_reads_the_expected_param(self):
    CP = car_params()
    p = params(True)
    setup_subaru_stop_and_go(CP, p)
    p.get_bool.assert_called_once_with("SubaruStopAndGo")

  def test_the_flag_fits_the_capnp_field(self):
    """CarParams.flags is a UInt32, and the fork's bit sits at the very top of it."""
    self.assertEqual(SNG_FLAG, 1 << 31)
    self.assertLess(SNG_FLAG, 1 << 32)

    CP = car_params()
    setup_subaru_stop_and_go(CP, params(True))
    # survives the round-trip card does before panda ever sees it
    self.assertTrue(structs.CarParams.from_bytes(CP.to_bytes()).flags & SNG_FLAG)


if __name__ == '__main__':
  unittest.main()
