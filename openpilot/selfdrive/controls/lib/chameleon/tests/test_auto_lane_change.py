"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's
sunnypilot/selfdrive/controls/lib/tests/test_auto_lane_change.py, converted
from pytest/parameterized to unittest/subTest. The DesireHelper tests at the
bottom are new: they pin the hook in desire_helper.py, which the controller
tests alone do not touch.
"""
import types
import unittest

from openpilot.cereal import log
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.controls.lib.desire_helper import DesireHelper, LaneChangeState, LaneChangeDirection
from openpilot.selfdrive.controls.lib.chameleon.auto_lane_change import (
  AUTO_LANE_CHANGE_TIMER, ONE_SECOND_DELAY, AutoLaneChangeController, AutoLaneChangeMode,
)

AUTO_MODES = [
  AutoLaneChangeMode.NUDGELESS,
  AutoLaneChangeMode.HALF_SECOND,
  AutoLaneChangeMode.ONE_SECOND,
  AutoLaneChangeMode.TWO_SECONDS,
  AutoLaneChangeMode.THREE_SECONDS,
]

LANE_CHANGE_SPEED = 30.0  # m/s, comfortably above LANE_CHANGE_SPEED_MIN


class FakeCarState:
  def __init__(self):
    self.vEgo = LANE_CHANGE_SPEED
    self.leftBlinker = False
    self.rightBlinker = False
    self.steeringPressed = False
    self.steeringTorque = 0.0
    self.leftBlindspot = False
    self.rightBlindspot = False
    self.brakePressed = False


def make_helper(mode, bsm_delay=False, enable_bsm=True):
  # enable_bsm=True by default so the auto-mode tests exercise the modes;
  # the BSM gate itself is pinned separately in TestBsmGate
  DH = DesireHelper(types.SimpleNamespace(enableBsm=enable_bsm))
  DH.alc.read_params = lambda: None  # pin the mode; update_params re-reads every 50 frames
  DH.alc.lane_change_set_timer = mode
  DH.alc.lane_change_bsm_delay = bsm_delay
  return DH


class TestAutoLaneChangeController(unittest.TestCase):
  def _controller(self, mode, bsm_delay=False):
    return make_helper(mode, bsm_delay).alc

  def _updates_for(self, delay):
    return int(delay / DT_MDL) + 1  # one extra update to make sure the threshold is crossed

  def test_reset(self):
    """Reset puts the timers back to default when the parent state machine is off."""
    alc = self._controller(AutoLaneChangeMode.NUDGE)
    alc.lane_change_wait_timer = 2.0
    alc.prev_brake_pressed = True

    alc.DH.lane_change_state = LaneChangeState.off
    alc.DH.lane_change_direction = LaneChangeDirection.none
    alc.reset()

    self.assertEqual(alc.lane_change_wait_timer, 0.0)
    self.assertFalse(alc.prev_brake_pressed)

  def test_off_and_nudge_mode(self):
    """OFF and NUDGE never allow an automatic lane change, however long we wait."""
    for mode in (AutoLaneChangeMode.OFF, AutoLaneChangeMode.NUDGE):
      with self.subTest(mode=mode):
        alc = self._controller(mode)
        for _ in range(int(10.0 / DT_MDL)):
          alc.update_lane_change(blindspot_detected=False, brake_pressed=False)
        self.assertFalse(alc.auto_lane_change_allowed)

  def test_timers(self):
    """Each delay mode allows the lane change only after its own delay."""
    for mode in AUTO_MODES:
      delay = AUTO_LANE_CHANGE_TIMER[mode]
      with self.subTest(mode=mode, delay=delay):
        alc = self._controller(mode)

        alc.update_lane_change(blindspot_detected=False, brake_pressed=False)
        self.assertFalse(alc.auto_lane_change_allowed)

        for _ in range(self._updates_for(delay)):
          alc.update_lane_change(blindspot_detected=False, brake_pressed=False)

        self.assertGreater(alc.lane_change_wait_timer, alc.lane_change_delay)
        self.assertTrue(alc.auto_lane_change_allowed)

  def test_brake_pressed_disables_auto_lane_change(self):
    """Braking while waiting cancels the auto lane change, even after release."""
    for mode in AUTO_MODES:
      with self.subTest(mode=mode):
        alc = self._controller(mode)
        num_updates = self._updates_for(AUTO_LANE_CHANGE_TIMER[mode])

        for _ in range(num_updates):
          alc.update_lane_change(blindspot_detected=False, brake_pressed=True)
        self.assertFalse(alc.auto_lane_change_allowed)
        self.assertTrue(alc.prev_brake_pressed)

        for _ in range(num_updates):
          alc.update_lane_change(blindspot_detected=False, brake_pressed=False)
        self.assertFalse(alc.auto_lane_change_allowed)

  def test_blindspot_detected_with_bsm_delay(self):
    """An occupied blind spot holds off the auto lane change while it persists."""
    for mode in AUTO_MODES:
      with self.subTest(mode=mode):
        alc = self._controller(mode, bsm_delay=True)

        alc.update_lane_change(blindspot_detected=True, brake_pressed=False)
        self.assertFalse(alc.auto_lane_change_allowed)

        for _ in range(self._updates_for(AUTO_LANE_CHANGE_TIMER[mode])):
          alc.update_lane_change(blindspot_detected=True, brake_pressed=False)
        self.assertFalse(alc.auto_lane_change_allowed)

  def test_blindspot_detected_then_undetected_with_bsm_delay(self):
    """Once the blind spot clears, the change is allowed after the extra delay."""
    for mode in AUTO_MODES:
      with self.subTest(mode=mode):
        alc = self._controller(mode, bsm_delay=True)

        alc.update_lane_change(blindspot_detected=True, brake_pressed=False)
        self.assertFalse(alc.auto_lane_change_allowed)

        num_updates = int((AUTO_LANE_CHANGE_TIMER[mode] + abs(ONE_SECOND_DELAY)) / DT_MDL) + 1
        for _ in range(num_updates):
          alc.update_lane_change(blindspot_detected=False, brake_pressed=False)
        self.assertTrue(alc.auto_lane_change_allowed)

  def test_disallow_continuous_auto_lane_change(self):
    """One blinker pull gets one auto lane change, not a chain of them."""
    for mode in AUTO_MODES:
      with self.subTest(mode=mode):
        alc = self._controller(mode)
        num_updates = self._updates_for(AUTO_LANE_CHANGE_TIMER[mode])

        for _ in range(num_updates):
          alc.update_lane_change(blindspot_detected=False, brake_pressed=False)
        self.assertTrue(alc.auto_lane_change_allowed)

        alc.DH.lane_change_state = LaneChangeState.laneChangeStarting
        alc.update_state()
        alc.DH.lane_change_state = LaneChangeState.preLaneChange  # done, blinker still on
        alc.update_state()

        for _ in range(num_updates):
          alc.update_lane_change(blindspot_detected=False, brake_pressed=False)
        self.assertFalse(alc.auto_lane_change_allowed)

  def test_controller_is_wired_into_desire_helper(self):
    dh = DesireHelper()
    self.assertIsInstance(dh.alc, AutoLaneChangeController)


class TestBsmGate(unittest.TestCase):
  """Without blind spot monitoring (BSM) the nudge is always required: the
  blindspot_detected gate in desire_helper.py is permanently False on those
  cars, so nudgeless would mean no cross-traffic check at all."""

  def test_default_is_no_bsm(self):
    """No CP (or a CP without enableBsm=True) means the gate stays closed."""
    self.assertFalse(DesireHelper().alc.enable_bsm)
    self.assertFalse(DesireHelper(types.SimpleNamespace(enableBsm=False)).alc.enable_bsm)
    self.assertTrue(DesireHelper(types.SimpleNamespace(enableBsm=True)).alc.enable_bsm)

  def test_no_bsm_never_allows_auto_lane_change(self):
    """Every auto mode stays disallowed without BSM, however long we wait."""
    for mode in AUTO_MODES:
      with self.subTest(mode=mode):
        alc = make_helper(mode, enable_bsm=False).alc
        for _ in range(int(10.0 / DT_MDL)):
          alc.update_lane_change(blindspot_detected=False, brake_pressed=False)
        self.assertFalse(alc.auto_lane_change_allowed)

  def test_no_bsm_nudgeless_still_requires_torque(self):
    """End to end: nudgeless set on a car without BSM behaves exactly like NUDGE."""
    DH = make_helper(AutoLaneChangeMode.NUDGELESS, enable_bsm=False)
    cs = FakeCarState()
    cs.leftBlinker = True

    for _ in range(int(5.0 / DT_MDL)):
      DH.update(cs, lateral_active=True, lane_change_prob=0.0)
    self.assertEqual(DH.lane_change_state, LaneChangeState.preLaneChange)

    cs.steeringPressed = True
    cs.steeringTorque = 1.0
    DH.update(cs, lateral_active=True, lane_change_prob=0.0)
    DH.update(cs, lateral_active=True, lane_change_prob=0.0)
    self.assertEqual(DH.lane_change_state, LaneChangeState.laneChangeStarting)
    self.assertEqual(DH.desire, log.Desire.laneChangeLeft)


class TestDesireHelperAutoLaneChange(unittest.TestCase):
  """End-to-end through DesireHelper.update: the ported hook itself."""

  def _run(self, DH, carstate, updates):
    for _ in range(updates):
      DH.update(carstate, lateral_active=True, lane_change_prob=0.0)

  def test_nudgeless_lane_change_without_torque(self):
    """In nudgeless mode the blinker alone starts the lane change."""
    DH = make_helper(AutoLaneChangeMode.NUDGELESS)
    cs = FakeCarState()
    cs.leftBlinker = True

    DH.update(cs, lateral_active=True, lane_change_prob=0.0)
    self.assertEqual(DH.lane_change_state, LaneChangeState.preLaneChange)

    # lane_change_prob stays 0 (no model), so laneChangeStarting bounces back to
    # preLaneChange after 0.5 s - watch for the transition instead of the end state
    seen_states = set()
    desires = set()
    for _ in range(int(1.0 / DT_MDL)):
      DH.update(cs, lateral_active=True, lane_change_prob=0.0)
      seen_states.add(DH.lane_change_state)
      desires.add(DH.desire)

    self.assertIn(LaneChangeState.laneChangeStarting, seen_states)
    self.assertIn(log.Desire.laneChangeLeft, desires)
    self.assertFalse(cs.steeringPressed)  # and no nudge was ever given
    # one blinker pull, one auto lane change: it must not have restarted
    self.assertTrue(DH.alc.prev_lane_change)
    self.assertEqual(DH.lane_change_state, LaneChangeState.preLaneChange)

  def test_nudge_mode_still_requires_torque(self):
    """Stock behavior is untouched in NUDGE mode: no torque, no lane change."""
    DH = make_helper(AutoLaneChangeMode.NUDGE)
    cs = FakeCarState()
    cs.rightBlinker = True

    self._run(DH, cs, int(5.0 / DT_MDL))
    self.assertEqual(DH.lane_change_state, LaneChangeState.preLaneChange)

    cs.steeringPressed = True
    cs.steeringTorque = -1.0
    self._run(DH, cs, 2)
    self.assertEqual(DH.lane_change_state, LaneChangeState.laneChangeStarting)
    self.assertEqual(DH.desire, log.Desire.laneChangeRight)

  def test_nudgeless_blocked_by_blindspot(self):
    """A car in the blind spot blocks the nudgeless change (bsm delay off)."""
    DH = make_helper(AutoLaneChangeMode.NUDGELESS)
    cs = FakeCarState()
    cs.leftBlinker = True
    cs.leftBlindspot = True

    self._run(DH, cs, int(3.0 / DT_MDL))
    self.assertEqual(DH.lane_change_state, LaneChangeState.preLaneChange)

  def test_nudgeless_blocked_after_braking(self):
    """Braking while the blinker is on cancels the nudgeless change."""
    DH = make_helper(AutoLaneChangeMode.NUDGELESS)
    cs = FakeCarState()
    cs.leftBlinker = True
    cs.brakePressed = True

    DH.update(cs, lateral_active=True, lane_change_prob=0.0)  # off -> preLaneChange
    DH.update(cs, lateral_active=True, lane_change_prob=0.0)  # brake sampled while waiting
    cs.brakePressed = False
    self._run(DH, cs, int(3.0 / DT_MDL))
    self.assertEqual(DH.lane_change_state, LaneChangeState.preLaneChange)

  def test_blinker_off_resets(self):
    """Cancelling the blinker before the delay expires ends the maneuver."""
    DH = make_helper(AutoLaneChangeMode.THREE_SECONDS)
    cs = FakeCarState()
    cs.leftBlinker = True

    self._run(DH, cs, int(1.0 / DT_MDL))
    self.assertEqual(DH.lane_change_state, LaneChangeState.preLaneChange)

    cs.leftBlinker = False
    DH.update(cs, lateral_active=True, lane_change_prob=0.0)
    self.assertEqual(DH.lane_change_state, LaneChangeState.off)
    self.assertEqual(DH.desire, log.Desire.none)


if __name__ == '__main__':
  unittest.main()
