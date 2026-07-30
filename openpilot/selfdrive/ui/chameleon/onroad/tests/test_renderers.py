"""The hide-stock-HUD renderer subclasses.

Two things worth pinning here. The seam test: every method these subclasses
override must still exist on the upstream parent, because an upstream rename
makes an override silently dead (stock drawing returns — fail-safe, but the
hide stops working and nothing says so). And the gates themselves: each flag
must suppress exactly its own upstream call, in both directions.
"""
import unittest
from unittest import mock

from openpilot.selfdrive.ui.chameleon.onroad import renderers
from openpilot.selfdrive.ui.chameleon.onroad.renderers import ChameleonHudRenderer, ChameleonModelRenderer
from openpilot.selfdrive.ui.onroad.hud_renderer import HudRenderer
from openpilot.selfdrive.ui.onroad.model_renderer import ModelRenderer

MODEL_OVERRIDES = ("_draw_lane_lines", "_draw_path", "_draw_lead_indicator")
HUD_OVERRIDES = ("_draw_set_speed", "_draw_current_speed")


class FakeUIState:
  def __init__(self):
    self.hide_driving_path = False
    self.hide_lane_lines = False
    self.hide_speed_cluster = False
    self.hide_wheel_button = False
    self.target_designator = False


class TestSeam(unittest.TestCase):
  def test_every_override_still_exists_upstream(self):
    """An upstream rename must fail here, not silently un-hide an element."""
    for name in MODEL_OVERRIDES:
      self.assertTrue(callable(getattr(ModelRenderer, name, None)), f"ModelRenderer.{name} is gone upstream")
    for name in HUD_OVERRIDES:
      self.assertTrue(callable(getattr(HudRenderer, name, None)), f"HudRenderer.{name} is gone upstream")

  def test_augmented_road_view_constructs_the_subclasses(self):
    import openpilot.selfdrive.ui.onroad.augmented_road_view as arv

    with open(arv.__file__, encoding="utf-8") as f:
      source = f.read()
    self.assertIn("ChameleonModelRenderer()", source)
    self.assertIn("ChameleonHudRenderer()", source)


class TestModelRendererGates(unittest.TestCase):
  def setUp(self):
    self.ui_state = FakeUIState()
    patcher = mock.patch.object(renderers, 'ui_state', self.ui_state)
    patcher.start()
    self.addCleanup(patcher.stop)

    # the subclass adds no __init__, so bypass the parent's (it builds filters
    # and textures) — the gates are the only behavior under test
    self.renderer = ChameleonModelRenderer.__new__(ChameleonModelRenderer)

  def _parent(self, name):
    patcher = mock.patch.object(ModelRenderer, name)
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def test_lane_lines_gate(self):
    parent = self._parent("_draw_lane_lines")

    self.renderer._draw_lane_lines()
    parent.assert_called_once()

    self.ui_state.hide_lane_lines = True
    self.renderer._draw_lane_lines()
    parent.assert_called_once()  # still once: the hidden call was suppressed

  def test_path_gate(self):
    parent = self._parent("_draw_path")

    self.renderer._draw_path({})
    parent.assert_called_once()

    self.ui_state.hide_driving_path = True
    self.renderer._draw_path({})
    parent.assert_called_once()

  def test_lead_indicator_yields_to_the_target_designator(self):
    parent = self._parent("_draw_lead_indicator")

    self.renderer._draw_lead_indicator()
    parent.assert_called_once()

    self.ui_state.target_designator = True
    self.renderer._draw_lead_indicator()
    parent.assert_called_once()

  def test_gates_are_independent(self):
    """Hiding one element must not touch its neighbours."""
    lanes = self._parent("_draw_lane_lines")
    path = self._parent("_draw_path")

    self.ui_state.hide_lane_lines = True
    self.renderer._draw_lane_lines()
    self.renderer._draw_path(sm={})

    lanes.assert_not_called()
    path.assert_called_once()


class TestHudRendererGates(unittest.TestCase):
  def setUp(self):
    self.ui_state = FakeUIState()
    patcher = mock.patch.object(renderers, 'ui_state', self.ui_state)
    patcher.start()
    self.addCleanup(patcher.stop)

    self.renderer = ChameleonHudRenderer.__new__(ChameleonHudRenderer)

  def test_speed_cluster_gate_covers_both_draws(self):
    set_speed = mock.patch.object(HudRenderer, "_draw_set_speed").start()
    current = mock.patch.object(HudRenderer, "_draw_current_speed").start()
    self.addCleanup(mock.patch.stopall)

    self.renderer._draw_set_speed(None)
    self.renderer._draw_current_speed(None)
    set_speed.assert_called_once()
    current.assert_called_once()

    self.ui_state.hide_speed_cluster = True
    self.renderer._draw_set_speed(None)
    self.renderer._draw_current_speed(None)
    set_speed.assert_called_once()
    current.assert_called_once()

  def test_wheel_button_visibility_follows_the_flag(self):
    """set_visible gets a live callable, so the button follows the toggle
    with no polling — and an invisible Widget takes no taps either, which is
    what keeps user_interacting() quiet."""
    button = mock.Mock()
    with mock.patch.object(HudRenderer, "__init__", lambda self: setattr(self, "_exp_button", button)):
      ChameleonHudRenderer()

    button.set_visible.assert_called_once()
    visible = button.set_visible.call_args[0][0]
    self.assertTrue(callable(visible))

    self.ui_state.hide_wheel_button = False
    self.assertTrue(visible())
    self.ui_state.hide_wheel_button = True
    self.assertFalse(visible())


if __name__ == '__main__':
  unittest.main()
