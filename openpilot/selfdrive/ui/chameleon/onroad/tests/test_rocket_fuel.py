import unittest
from unittest import mock

import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad import rocket_fuel as rf
from openpilot.selfdrive.ui.chameleon.onroad.rocket_fuel import ACCEL_COLOR, BAR_WIDTH, DECEL_COLOR, MAX_HEIGHT_FRACTION, SMOOTHING, RocketFuel

SCREEN = rl.Rectangle(0, 0, 2160, 1080)


class FakeSubMaster(dict):
  def __init__(self, a_ego=0.0):
    super().__init__(carState=mock.Mock(aEgo=a_ego))


class FakeUIState:
  def __init__(self, rocket_fuel=True):
    self.rocket_fuel = rocket_fuel


class TestRocketFuel(unittest.TestCase):
  def setUp(self):
    draw_patcher = mock.patch.object(rf.rl, 'draw_rectangle')
    self.draw = draw_patcher.start()
    self.addCleanup(draw_patcher.stop)

    self._patch_ui_state(FakeUIState())

  def _patch_ui_state(self, ui_state):
    patcher = mock.patch.object(rf, 'ui_state', ui_state)
    patcher.start()
    self.addCleanup(patcher.stop)
    return ui_state

  def _render(self, a_ego, frames=1):
    bar = RocketFuel()
    for _ in range(frames):
      bar.render(SCREEN, FakeSubMaster(a_ego))
    return bar

  def test_no_draw_when_disabled(self):
    self._patch_ui_state(FakeUIState(rocket_fuel=False))
    self._render(5.0, frames=50)

    self.draw.assert_not_called()

  def test_no_draw_when_coasting(self):
    self._render(0.0, frames=50)

    self.draw.assert_not_called()

  def test_no_draw_below_the_deadband(self):
    """The 0.1/accel term means gentle acceleration produces no bar at all."""
    self._render(0.1, frames=50)

    self.draw.assert_not_called()

  def test_acceleration_is_green(self):
    self._render(2.0, frames=50)

    self.draw.assert_called()
    self.assertEqual(self.draw.call_args.args[4], ACCEL_COLOR)

  def test_braking_is_red(self):
    self._render(-2.0, frames=50)

    self.draw.assert_called()
    self.assertEqual(self.draw.call_args.args[4], DECEL_COLOR)

  def test_smoothing_lags_the_first_frame(self):
    """One frame moves the displayed value 1/SMOOTHING of the way, so the bar eases in."""
    bar = self._render(5.0, frames=1)

    self.assertAlmostEqual(bar.vc_accel, 5.0 / SMOOTHING)
    self.assertLess(bar.vc_accel, 5.0)

  def test_smoothing_converges(self):
    bar = self._render(2.0, frames=200)

    self.assertAlmostEqual(bar.vc_accel, 2.0, places=4)

  def test_bar_width_and_left_edge(self):
    self._render(2.0, frames=50)

    x, _, width, _, _ = self.draw.call_args.args
    self.assertEqual(x, int(SCREEN.x))
    self.assertEqual(width, int(BAR_WIDTH))

  def test_acceleration_bar_is_centred(self):
    """Accelerating grows the bar symmetrically about the vertical centre."""
    self._render(2.0, frames=200)

    _, y, _, height, _ = self.draw.call_args.args
    centre = SCREEN.y + SCREEN.height / 2
    self.assertLess(y, centre)
    self.assertAlmostEqual(y + height, centre, delta=2)

  def test_braking_bar_starts_at_the_centre(self):
    self._render(-2.0, frames=200)

    _, y, _, height, _ = self.draw.call_args.args
    self.assertEqual(y, int(SCREEN.y + SCREEN.height / 2))
    self.assertGreater(height, 0)

  def test_height_is_capped(self):
    """Even at absurd acceleration the bar cannot exceed the 85% cap (half-filled)."""
    self._render(1000.0, frames=200)

    height = self.draw.call_args.args[3]
    self.assertLessEqual(height, int(MAX_HEIGHT_FRACTION * SCREEN.height / 2.0))
    self.assertGreater(height, 0)

  def test_bar_grows_with_acceleration(self):
    self._render(1.0, frames=200)
    small = self.draw.call_args.args[3]
    self.draw.reset_mock()

    self._render(4.0, frames=200)
    large = self.draw.call_args.args[3]

    self.assertGreater(large, small)


if __name__ == '__main__':
  unittest.main()
