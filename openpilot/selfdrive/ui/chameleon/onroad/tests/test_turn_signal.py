import unittest
from unittest import mock

import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad import turn_signal as ts
from openpilot.selfdrive.ui.chameleon.onroad.turn_signal import MAX_ALPHA, IconSide, TurnSignalConfig, TurnSignalController, TurnSignalWidget
from openpilot.selfdrive.ui.mici.onroad.alert_renderer import TURN_SIGNAL_BLINK_PERIOD

TEXTURE_WIDTH = 120
TEXTURE_HEIGHT = 109
SCREEN = rl.Rectangle(0, 0, 2160, 1080)


class FakeTexture:
  # gui_app.texture() needs a GL context, so stand in for it.
  width = TEXTURE_WIDTH
  height = TEXTURE_HEIGHT


class FakeCarState:
  def __init__(self, left=False, right=False):
    self.leftBlinker = left
    self.rightBlinker = right


class FakeUIState:
  def __init__(self, turn_signals=True, left=False, right=False):
    self.turn_signals = turn_signals
    self.sm = {'carState': FakeCarState(left, right)}


class TurnSignalTestCase(unittest.TestCase):
  def setUp(self):
    patcher = mock.patch.object(ts.gui_app, 'texture', return_value=FakeTexture())
    patcher.start()
    self.addCleanup(patcher.stop)

    draw_patcher = mock.patch.object(ts.rl, 'draw_texture_ex')
    self.draw = draw_patcher.start()
    self.addCleanup(draw_patcher.stop)

  def _patch_ui_state(self, ui_state):
    patcher = mock.patch.object(ts, 'ui_state', ui_state)
    patcher.start()
    self.addCleanup(patcher.stop)
    return ui_state


class TestTurnSignalController(TurnSignalTestCase):
  def test_blinker_activates_matching_side(self):
    self._patch_ui_state(FakeUIState(left=True))
    controller = TurnSignalController()
    controller.update()

    self.assertTrue(controller._left_signal.active)
    self.assertFalse(controller._right_signal.active)

  def test_blinker_off_deactivates(self):
    ui_state = self._patch_ui_state(FakeUIState(left=True))
    controller = TurnSignalController()
    controller.update()
    self.assertTrue(controller._left_signal.active)

    ui_state.sm['carState'].leftBlinker = False
    controller.update()

    self.assertFalse(controller._left_signal.active)

  def test_param_gates_activation(self):
    """With the toggle off, a blinker must not activate the widget."""
    self._patch_ui_state(FakeUIState(turn_signals=False, left=True, right=True))
    controller = TurnSignalController()
    controller.update()

    self.assertFalse(controller._left_signal.active)
    self.assertFalse(controller._right_signal.active)

  def test_no_draw_when_disabled(self):
    ui_state = self._patch_ui_state(FakeUIState(left=True))
    controller = TurnSignalController()
    controller.update()

    ui_state.turn_signals = False
    controller.render(SCREEN)

    self.draw.assert_not_called()

  def test_positions_straddle_the_centre(self):
    """Icons sit either side of screen centre, offset by the config gap."""
    self._patch_ui_state(FakeUIState(left=True, right=True))
    controller = TurnSignalController()
    controller.update()
    controller.render(SCREEN)

    self.assertEqual(self.draw.call_count, 2)
    left_pos, right_pos = (call.args[1] for call in self.draw.call_args_list)

    config = TurnSignalConfig()
    centre = SCREEN.x + SCREEN.width / 2
    icon_inset = (config.size - TEXTURE_WIDTH) / 2

    self.assertEqual(left_pos.x, centre - config.left_x - config.size + icon_inset)
    self.assertEqual(right_pos.x, centre + config.right_x + icon_inset)
    self.assertLess(left_pos.x, centre)
    self.assertGreater(right_pos.x, centre)

  def test_config_is_replaceable(self):
    controller = TurnSignalController()
    replacement = TurnSignalConfig(left_x=10, left_y=20, right_x=30, right_y=40, size=50)

    controller.config = replacement

    self.assertEqual(controller.config, replacement)


class TestTurnSignalWidget(TurnSignalTestCase):
  def test_first_frame_is_full_brightness(self):
    """The timer starts at 0, so the first rendered frame snaps to full alpha."""
    self._patch_ui_state(FakeUIState())
    widget = TurnSignalWidget(IconSide.left)
    widget.activate()
    widget.render(SCREEN)

    self.assertEqual(self.draw.call_args.args[4].a, MAX_ALPHA)

  def test_alpha_decays_within_a_blink(self):
    """Held inside one blink period, alpha falls away from full — that is the blink."""
    self._patch_ui_state(FakeUIState())
    with mock.patch('time.monotonic', return_value=100.0):
      widget = TurnSignalWidget(IconSide.left)
      widget.activate()
      widget.render(SCREEN)
      self.assertEqual(self.draw.call_args.args[4].a, MAX_ALPHA)

      for _ in range(200):
        widget.render(SCREEN)

    self.assertLess(self.draw.call_args.args[4].a, MAX_ALPHA)

  def test_new_blink_period_restores_full_alpha(self):
    self._patch_ui_state(FakeUIState())
    with mock.patch('time.monotonic', return_value=100.0) as monotonic:
      widget = TurnSignalWidget(IconSide.left)
      widget.activate()
      widget.render(SCREEN)
      for _ in range(200):
        widget.render(SCREEN)
      dimmed = self.draw.call_args.args[4].a

      monotonic.return_value = 100.0 + TURN_SIGNAL_BLINK_PERIOD + 0.01
      widget.render(SCREEN)

    self.assertLess(dimmed, MAX_ALPHA)
    self.assertEqual(self.draw.call_args.args[4].a, MAX_ALPHA)

  def test_inactive_widget_does_not_draw(self):
    self._patch_ui_state(FakeUIState())
    widget = TurnSignalWidget(IconSide.left)
    widget.render(SCREEN)

    self.draw.assert_not_called()

  def test_deactivate_resets_blink_timer(self):
    """Resetting the timer means the next activation starts bright, not mid-fade."""
    self._patch_ui_state(FakeUIState())
    widget = TurnSignalWidget(IconSide.left)
    widget.activate()
    widget.render(SCREEN)
    self.assertNotEqual(widget._turn_signal_timer, 0.0)

    widget.deactivate()

    self.assertFalse(widget.active)
    self.assertEqual(widget._turn_signal_timer, 0.0)

  def test_right_side_flips_the_icon(self):
    with mock.patch.object(ts.gui_app, 'texture', return_value=FakeTexture()) as texture:
      TurnSignalWidget(IconSide.right)

    self.assertTrue(texture.call_args.kwargs['flip_x'])


if __name__ == '__main__':
  unittest.main()
