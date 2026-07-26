import unittest
from unittest import mock

import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad import blind_spot_indicators as bsi
from openpilot.selfdrive.ui.chameleon.onroad.blind_spot_indicators import ALPHA_EPSILON, BLIND_SPOT_MARGIN_X, BLIND_SPOT_Y_OFFSET, BlindSpotIndicators

TEXTURE_WIDTH = 108
SCREEN = rl.Rectangle(0, 0, 2160, 1080)


class FakeTexture:
  # gui_app.texture() needs a GL context, so stand in for it. Only .width is read.
  width = TEXTURE_WIDTH


class FakeCarState:
  def __init__(self, left=False, right=False):
    self.leftBlindspot = left
    self.rightBlindspot = right


class FakeUIState:
  def __init__(self, blindspot=True, left=False, right=False):
    self.blindspot = blindspot
    self.sm = {'carState': FakeCarState(left, right)}


class TestBlindSpotIndicators(unittest.TestCase):
  def setUp(self):
    patcher = mock.patch.object(bsi.gui_app, 'texture', return_value=FakeTexture())
    patcher.start()
    self.addCleanup(patcher.stop)

    draw_patcher = mock.patch.object(bsi.rl, 'draw_texture_ex')
    self.draw = draw_patcher.start()
    self.addCleanup(draw_patcher.stop)

  def _indicators(self, ui_state):
    indicators = BlindSpotIndicators()
    patcher = mock.patch.object(bsi, 'ui_state', ui_state)
    patcher.start()
    self.addCleanup(patcher.stop)
    return indicators

  def test_alpha_rises_on_detection(self):
    """A blind spot report drives the alpha filter above the draw threshold."""
    indicators = self._indicators(FakeUIState(left=True))
    self.assertEqual(indicators._blind_spot_left_alpha_filter.x, 0)

    indicators.update()

    self.assertGreater(indicators._blind_spot_left_alpha_filter.x, ALPHA_EPSILON)
    self.assertEqual(indicators._blind_spot_right_alpha_filter.x, 0)
    self.assertTrue(indicators.detected)

  def test_alpha_decays_when_clear(self):
    """Once the car stops reporting, alpha falls back toward zero."""
    indicators = self._indicators(ui_state := FakeUIState(left=True))
    for _ in range(60):
      indicators.update()
    peak = indicators._blind_spot_left_alpha_filter.x

    ui_state.sm['carState'].leftBlindspot = False
    for _ in range(60):
      indicators.update()

    self.assertLess(indicators._blind_spot_left_alpha_filter.x, peak)

  def test_detected_false_when_disabled(self):
    """The param gates `detected` even while the filter is still high."""
    indicators = self._indicators(ui_state := FakeUIState(left=True))
    indicators.update()
    self.assertTrue(indicators.detected)

    ui_state.blindspot = False

    self.assertFalse(indicators.detected)

  def test_no_draw_when_disabled(self):
    indicators = self._indicators(FakeUIState(blindspot=False, left=True, right=True))
    indicators.update()
    indicators.render(SCREEN)

    self.draw.assert_not_called()

  def test_no_draw_below_threshold(self):
    """A clear road never draws, so the icons cannot linger at alpha 0."""
    indicators = self._indicators(FakeUIState())
    indicators.update()
    indicators.render(SCREEN)

    self.draw.assert_not_called()

  def test_left_and_right_positions(self):
    """Left hugs the left edge; right is inset by its own width so it stays on screen."""
    indicators = self._indicators(FakeUIState(left=True, right=True))
    indicators.update()
    indicators.render(SCREEN)

    self.assertEqual(self.draw.call_count, 2)
    left_pos, right_pos = (call.args[1] for call in self.draw.call_args_list)

    self.assertEqual(left_pos.x, SCREEN.x + BLIND_SPOT_MARGIN_X)
    self.assertEqual(right_pos.x, SCREEN.x + SCREEN.width - BLIND_SPOT_MARGIN_X - TEXTURE_WIDTH)
    self.assertEqual(left_pos.y, SCREEN.y + BLIND_SPOT_Y_OFFSET)
    self.assertEqual(right_pos.y, SCREEN.y + BLIND_SPOT_Y_OFFSET)

  def test_alpha_tracks_filter(self):
    """Draw alpha is the filter value scaled to 0-255, so the icon fades in rather than popping."""
    indicators = self._indicators(FakeUIState(left=True))
    indicators.update()
    indicators.render(SCREEN)

    expected = int(255 * indicators._blind_spot_left_alpha_filter.x)
    self.assertEqual(self.draw.call_args.args[4].a, expected)
    self.assertGreater(expected, 0)
    self.assertLess(expected, 255)


if __name__ == '__main__':
  unittest.main()
