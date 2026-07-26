import unittest
from unittest import mock

import numpy as np
import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad import rainbow_path as rp
from openpilot.selfdrive.ui.chameleon.onroad.rainbow_path import RainbowPath


class FakePath:
  projected_points = np.zeros((4, 2), dtype=np.float32)


class TestRainbowPath(unittest.TestCase):
  def test_gradient_has_one_colour_per_segment(self):
    path = RainbowPath(num_segments=5)
    gradient = path.get_gradient()

    self.assertEqual(len(gradient.colors), 5)
    self.assertEqual(len(gradient.stops), 5)

  def test_stops_span_zero_to_one_in_order(self):
    """draw_polygon needs ascending stops covering the whole path."""
    gradient = RainbowPath().get_gradient()

    self.assertEqual(gradient.stops[0], 0.0)
    self.assertEqual(gradient.stops[-1], 1.0)
    self.assertEqual(gradient.stops, sorted(gradient.stops))

  def test_gradient_runs_bottom_to_top(self):
    gradient = RainbowPath().get_gradient()

    self.assertEqual(gradient.start, (0.0, 1.0))
    self.assertEqual(gradient.end, (0.0, 0.0))

  def test_alpha_fades_toward_the_horizon(self):
    """Bottom of the path is the most opaque; the far end fades by ALPHA_FADE."""
    path = RainbowPath()
    gradient = path.get_gradient()

    self.assertEqual(gradient.colors[0].a, int(path.BASE_ALPHA * 255))
    self.assertEqual(gradient.colors[-1].a, int(path.BASE_ALPHA * (1.0 - path.ALPHA_FADE) * 255))
    self.assertLess(gradient.colors[-1].a, gradient.colors[0].a)

  def test_hue_rotates_with_time(self):
    """The rainbow animates off the monotonic clock, not off frame count."""
    path = RainbowPath()
    with mock.patch('time.monotonic', return_value=0.0):
      first = [(c.r, c.g, c.b) for c in path.get_gradient().colors]
    with mock.patch('time.monotonic', return_value=1.0):
      later = [(c.r, c.g, c.b) for c in path.get_gradient().colors]

    self.assertNotEqual(first, later)

  def test_speed_zero_freezes_the_rainbow(self):
    path = RainbowPath(speed=0.0)
    with mock.patch('time.monotonic', return_value=0.0):
      first = [(c.r, c.g, c.b) for c in path.get_gradient().colors]
    with mock.patch('time.monotonic', return_value=10.0):
      later = [(c.r, c.g, c.b) for c in path.get_gradient().colors]

    self.assertEqual(first, later)

  def test_all_colours_are_in_range(self):
    """rl.Color takes uint8; an out-of-range channel would wrap and show a wrong colour."""
    for colour in RainbowPath().get_gradient().colors:
      for channel in (colour.r, colour.g, colour.b, colour.a):
        self.assertGreaterEqual(channel, 0)
        self.assertLessEqual(channel, 255)

  def test_setters_clamp_to_valid_range(self):
    path = RainbowPath()

    path.set_saturation(5.0)
    self.assertEqual(path.saturation, 1.0)
    path.set_saturation(-5.0)
    self.assertEqual(path.saturation, 0.0)
    path.set_lightness(5.0)
    self.assertEqual(path.lightness, 1.0)
    path.set_lightness(-5.0)
    self.assertEqual(path.lightness, 0.0)

  def test_zero_saturation_is_greyscale(self):
    path = RainbowPath(saturation=0.0)

    for colour in path.get_gradient().colors:
      self.assertEqual(colour.r, colour.g)
      self.assertEqual(colour.g, colour.b)

  def test_draw_passes_gradient_and_points(self):
    path = RainbowPath()
    fake_path = FakePath()
    rect = rl.Rectangle(0, 0, 100, 100)

    with mock.patch.object(rp, 'draw_polygon') as draw_polygon:
      path.draw_rainbow_path(rect, fake_path)

    draw_polygon.assert_called_once()
    self.assertIs(draw_polygon.call_args.args[0], rect)
    np.testing.assert_array_equal(draw_polygon.call_args.args[1], fake_path.projected_points)
    self.assertEqual(len(draw_polygon.call_args.kwargs['gradient'].colors), path.num_segments)


if __name__ == '__main__':
  unittest.main()
