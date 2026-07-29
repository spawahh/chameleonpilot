import unittest
from unittest import mock

import numpy as np
import pyray as rl

from openpilot.selfdrive.locationd.calibrationd import HEIGHT_INIT
from openpilot.selfdrive.ui.chameleon.onroad.aircraft import flight_path_vector as fpv
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.flight_path_vector import (
  GHOST_COLOR, GHOST_SEPARATION, LOOKAHEAD, MIN_SPEED, RADIUS, WING, FlightPathVector,
)

SCREEN = rl.Rectangle(0, 0, 2160, 1080)
CX, CY, FOCAL = 1080.0, 540.0, 900.0

# Projects car space onto the screen the way the real transform does: depth is
# the forward axis, +lateral goes right, +vertical goes down.
TRANSFORM = np.array([
  [CX, FOCAL, 0.0],
  [CY, 0.0, FOCAL],
  [1.0, 0.0, 0.0],
])

# The straight-ahead symbol still sits below the centre line: the path is drawn
# at camera height, so HEIGHT_INIT[0] is added to every point.
BORESIGHT_X = CX
BORESIGHT_Y = CY + FOCAL * HEIGHT_INIT[0] / LOOKAHEAD


class FakeModel:
  def __init__(self, vx, vy, vz, plan_y=None, plan_x=None):
    self.velocity = mock.Mock(x=[vx], y=[vy], z=[vz])
    # straight plan out past the lookahead unless a test shapes it
    xs = list(np.arange(0.0, 65.0, 1.0)) if plan_x is None else plan_x
    ys = [0.0] * len(xs) if plan_y is None else [plan_y(x) for x in xs]
    self.position = mock.Mock(x=xs, y=ys, z=[0.0] * len(xs))


class FakeSubMaster(dict):
  def __init__(self, vx=25.0, vy=0.0, vz=0.0, recv_frame=10, plan_y=None, plan_x=None):
    super().__init__(modelV2=FakeModel(vx, vy, vz, plan_y, plan_x))
    self.recv_frame = {'modelV2': recv_frame}


class FakeUIState:
  def __init__(self, enabled=True, started_frame=1):
    self.flight_path_vector = enabled
    self.started_frame = started_frame


class TestFlightPathVector(unittest.TestCase):
  def setUp(self):
    ring_patcher = mock.patch.object(fpv.rl, 'draw_ring')
    self.ring = ring_patcher.start()
    self.addCleanup(ring_patcher.stop)

    line_patcher = mock.patch.object(fpv.rl, 'draw_line_ex')
    self.line = line_patcher.start()
    self.addCleanup(line_patcher.stop)

    self._patch_ui_state(FakeUIState())

  def _patch_ui_state(self, ui_state):
    patcher = mock.patch.object(fpv, 'ui_state', ui_state)
    patcher.start()
    self.addCleanup(patcher.stop)
    return ui_state

  def _render(self, sm=None, frames=1, transform=TRANSFORM, rect=SCREEN):
    symbol = FlightPathVector()
    symbol.set_transform(transform)
    for _ in range(frames):
      symbol.render(rect, sm if sm is not None else FakeSubMaster())
    return symbol

  def _center(self):
    """Centre of the last drawn symbol, from the ring call."""
    self.assertTrue(self.ring.called, "nothing was drawn")
    center = self.ring.call_args[0][0]
    return center.x, center.y

  def test_no_draw_when_disabled(self):
    self._patch_ui_state(FakeUIState(enabled=False))
    self._render(FakeSubMaster(vy=5.0), frames=50)

    self.ring.assert_not_called()
    self.line.assert_not_called()

  def test_no_draw_before_the_model_starts(self):
    """recv_frame older than started_frame means the data is from a previous drive."""
    self._patch_ui_state(FakeUIState(started_frame=100))
    self._render(FakeSubMaster(recv_frame=5), frames=50)

    self.ring.assert_not_called()

  def test_no_draw_without_velocity_data(self):
    sm = FakeSubMaster()
    sm['modelV2'].velocity = mock.Mock(x=[], y=[], z=[])
    self._render(sm, frames=50)

    self.ring.assert_not_called()

  def test_no_draw_when_projected_off_screen(self):
    """A symbol outside the camera rect is dropped, not clamped to the edge."""
    self._render(FakeSubMaster(), frames=50, rect=rl.Rectangle(0, 0, 10, 10))

    self.ring.assert_not_called()

  def test_straight_ahead_is_centred(self):
    self._render(FakeSubMaster(vx=25.0), frames=300)

    x, y = self._center()
    self.assertAlmostEqual(x, BORESIGHT_X, places=3)
    self.assertAlmostEqual(y, BORESIGHT_Y, places=3)

  def test_lateral_travel_moves_the_symbol(self):
    """Drifting right puts the symbol right of centre, and the other way round."""
    self._render(FakeSubMaster(vx=25.0, vy=2.5), frames=300)
    right_x, _ = self._center()

    self.ring.reset_mock()
    self._render(FakeSubMaster(vx=25.0, vy=-2.5), frames=300)
    left_x, _ = self._center()

    self.assertGreater(right_x, BORESIGHT_X)
    self.assertLess(left_x, BORESIGHT_X)
    # symmetric about the boresight
    self.assertAlmostEqual(right_x - BORESIGHT_X, BORESIGHT_X - left_x, places=3)

  def test_vertical_travel_moves_the_symbol(self):
    self._render(FakeSubMaster(vx=25.0, vz=1.0), frames=300)
    down_y = self._center()[1]

    self.assertGreater(down_y, BORESIGHT_Y)

  def test_caged_below_min_speed(self):
    """Crawling with a big lateral component must not throw the symbol sideways."""
    self._render(FakeSubMaster(vx=MIN_SPEED - 0.1, vy=5.0), frames=300)

    x, y = self._center()
    self.assertAlmostEqual(x, BORESIGHT_X, places=3)
    self.assertAlmostEqual(y, BORESIGHT_Y, places=3)

  def test_direction_is_smoothed(self):
    """One frame of a new direction moves the symbol only part of the way."""
    self._render(FakeSubMaster(vx=25.0, vy=2.5), frames=1)
    after_one_frame = self._center()[0]

    self.ring.reset_mock()
    self._render(FakeSubMaster(vx=25.0, vy=2.5), frames=300)
    settled = self._center()[0]

    self.assertGreater(settled, BORESIGHT_X)
    self.assertLess(after_one_frame - BORESIGHT_X, (settled - BORESIGHT_X) / 2)

  def test_no_ghost_when_plan_matches_travel(self):
    """Plan and travel agree: a single clean symbol, no ghost underneath it."""
    self._render(FakeSubMaster(), frames=300)

    self.assertEqual(self.ring.call_count, 300)

  def test_ghost_rides_the_planned_path(self):
    """A plan curving away from the travel direction gets the ghost drawn on it."""
    self._render(FakeSubMaster(plan_y=lambda x: 0.2 * x), frames=300)

    ghost, primary = self.ring.call_args_list[-2], self.ring.call_args_list[-1]
    self.assertAlmostEqual(primary[0][0].x, BORESIGHT_X, places=3)
    self.assertGreater(ghost[0][0].x, BORESIGHT_X + GHOST_SEPARATION)
    # the dimmer twin, not a second solid symbol
    self.assertEqual(ghost[0][6].a, GHOST_COLOR.a)

  def test_ghost_hidden_inside_the_separation_threshold(self):
    """Small in-lane disagreement (~1 m at the lookahead) stays a single symbol."""
    self._render(FakeSubMaster(plan_y=lambda x: x / LOOKAHEAD), frames=300)

    self.assertEqual(self.ring.call_count, 300)

  def test_no_ghost_when_plan_is_short(self):
    """A plan that ends before the lookahead cannot place the ghost."""
    xs = list(np.arange(0.0, 20.0, 1.0))
    self._render(FakeSubMaster(plan_y=lambda x: 0.5 * x, plan_x=xs), frames=300)

    self.assertEqual(self.ring.call_count, 300)

  def test_symbol_has_wings_and_a_fin(self):
    # one frame: with no lateral or vertical travel the symbol is already settled
    self._render(FakeSubMaster(), frames=1)
    x, y = self._center()

    self.assertEqual(self.line.call_count, 3)
    starts = [call[0][0] for call in self.line.call_args_list]
    ends = [call[0][1] for call in self.line.call_args_list]

    # left wing, right wing, vertical fin - all clear of the ring
    self.assertAlmostEqual(starts[0].x, x - RADIUS - WING, places=3)
    self.assertAlmostEqual(ends[0].x, x - RADIUS, places=3)
    self.assertAlmostEqual(starts[1].x, x + RADIUS, places=3)
    self.assertAlmostEqual(ends[1].x, x + RADIUS + WING, places=3)
    self.assertLess(starts[2].y, y - RADIUS)
    self.assertAlmostEqual(starts[2].x, x, places=3)


if __name__ == '__main__':
  unittest.main()
