"""The Chameleon settings panel, tested without a window.

The panel is the fork's whole settings surface, so these tests pin the three
things that would break silently: the row set and section order, the params
round-trip, and the full-row tap contract (flip everywhere except the switch,
never when disabled).
"""
import unittest
from unittest import mock

import pyray as rl

from openpilot.selfdrive.ui.chameleon import toggles as toggle_defs_mod
from openpilot.selfdrive.ui.chameleon.layouts import settings as cs
from openpilot.selfdrive.ui.chameleon.toggles import TOGGLE_DEFS


class FakeFont:
  """gui_app has no font atlas without a window.

  wrap_text and measure_text_cached hash `font.texture.id`, so the fake needs
  one; the actual measuring call (rl.measure_text_ex) is patched at the pyray
  module, which is the single chokepoint every text helper funnels through.
  """
  texture = mock.Mock(id=1)


class FakeParams:
  def __init__(self, values=None):
    self.values = dict(values or {})
    self.puts = []

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def get(self, key, return_default=False):
    return self.values.get(key, 0)

  def put_bool(self, key, value, block=False):
    self.values[key] = value
    self.puts.append((key, value))

  def put(self, key, value, block=False):
    self.values[key] = value
    self.puts.append((key, value))


class FakeCP:
  def __init__(self, enable_bsm):
    self.enableBsm = enable_bsm


class FakeUIState:
  def __init__(self, CP=None):
    self.CP = CP


class PanelTestCase(unittest.TestCase):
  def setUp(self):
    self._patch(mock.patch.object(cs.gui_app, 'font', return_value=FakeFont()))
    self._patch(mock.patch('pyray.measure_text_ex', return_value=rl.Vector2(100, 40)))
    # ListItem and the icon path both come from upstream list_view, which loads
    # fonts and textures at import/construct time
    import openpilot.system.ui.widgets.list_view as lv
    self._patch(mock.patch.object(lv.gui_app, 'font', return_value=FakeFont()))
    self._patch(mock.patch.object(lv.gui_app, 'texture', return_value=mock.Mock(width=80, height=80)))

    self.params = FakeParams()
    self._patch(mock.patch.object(cs, 'Params', return_value=self.params))
    self.ui_state = FakeUIState()
    self._patch(mock.patch.object(cs, 'ui_state', self.ui_state))

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def _panel(self):
    return cs.ChameleonSettingsLayout()


class TestPanelStructure(PanelTestCase):
  def test_constructs_windowless(self):
    self._panel()

  def test_every_fork_toggle_has_a_row(self):
    panel = self._panel()

    self.assertEqual(set(panel._toggles.keys()), set(TOGGLE_DEFS.keys()))

  def test_section_order(self):
    """Theme first, then driving, then the HUD widgets; hide rows last when present."""
    panel = self._panel()
    items = panel._scroller._items

    headers = [i for i in items if isinstance(i, cs.SectionHeader)]
    self.assertGreaterEqual(len(headers), 3)

    # the theme rows come before the ALC control, which comes before the widget toggles
    self.assertLess(items.index(panel._theme_btn), items.index(panel._alc_timer))
    self.assertLess(items.index(panel._alc_timer), items.index(panel._toggles["BlindSpot"]))

  def test_upstream_toggles_panel_is_stock(self):
    """The whole point of the panel: upstream's TogglesLayout owes the fork nothing."""
    import openpilot.selfdrive.ui.layouts.settings.toggles as upstream_toggles

    source = open(upstream_toggles.__file__, encoding="utf-8").read()
    self.assertNotIn("chameleon", source.lower())


class TestParamsRoundTrip(PanelTestCase):
  def test_toggle_callback_writes_its_param(self):
    panel = self._panel()

    panel._toggles["BlindSpot"]._on_change(True)

    self.assertIn(("BlindSpot", True), self.params.puts)

  def test_alc_timer_writes_int_index(self):
    panel = self._panel()

    panel._set_alc_timer(2)

    self.assertIn(("AutoLaneChangeTimer", 2), self.params.puts)

  def test_restart_toggle_requests_an_onroad_cycle(self):
    """Params read at process construction only take effect after a cycle."""
    panel = self._panel()

    panel._toggles["NeuralNetworkLateralControl"]._on_change(True)

    self.assertIn(("NeuralNetworkLateralControl", True), self.params.puts)
    self.assertIn(("OnroadCycleRequested", True), self.params.puts)

  def test_live_toggle_does_not_cycle_onroad(self):
    panel = self._panel()

    panel._toggles["BlindSpot"]._on_change(True)

    self.assertNotIn(("OnroadCycleRequested", True), self.params.puts)

  def test_show_event_mirrors_external_changes(self):
    panel = self._panel()
    self.params.values["RainbowMode"] = True
    self.params.values["AutoLaneChangeTimer"] = 3

    panel.show_event()

    self.assertTrue(panel._toggles["RainbowMode"].action_item.get_state())
    self.assertEqual(panel._alc_timer.action_item.get_selected_button(), 3)


class TestBsmGating(PanelTestCase):
  def test_rows_disabled_without_bsm(self):
    self.ui_state.CP = FakeCP(enable_bsm=False)
    panel = self._panel()

    self.assertFalse(panel._alc_timer.action_item.enabled)
    self.assertFalse(panel._toggles["AutoLaneChangeBsmDelay"].action_item.enabled)

  def test_rows_enabled_with_bsm(self):
    self.ui_state.CP = FakeCP(enable_bsm=True)
    panel = self._panel()

    self.assertTrue(panel._alc_timer.action_item.enabled)
    self.assertTrue(panel._toggles["AutoLaneChangeBsmDelay"].action_item.enabled)

  def test_gate_is_live_not_snapshotted(self):
    """CarParams arrives after construction; the rows must follow it."""
    self.ui_state.CP = None
    panel = self._panel()
    self.assertFalse(panel._alc_timer.action_item.enabled)

    self.ui_state.CP = FakeCP(enable_bsm=True)
    self.assertTrue(panel._alc_timer.action_item.enabled)


class TestFullRowTap(PanelTestCase):
  def _row(self, enabled=True, state=False):
    writes = []
    row = cs.ChameleonToggleItem("t", "d", state, callback=lambda s: writes.append(s))
    row.set_rect(rl.Rectangle(0, 0, 1000, 170))
    row.action_item.set_enabled(enabled)
    return row, writes

  def test_tap_on_row_body_flips(self):
    row, writes = self._row(state=False)

    row._handle_mouse_release(rl.Vector2(100, 85))

    self.assertEqual(writes, [True])
    self.assertTrue(row.action_item.get_state())

  def test_tap_on_the_switch_is_left_to_the_switch(self):
    """The switch fires its own callback; the row firing too would double-toggle."""
    row, writes = self._row(state=False)
    switch_rect = row.get_right_item_rect(row.rect)
    inside_switch = rl.Vector2(switch_rect.x + switch_rect.width / 2, switch_rect.y + switch_rect.height / 2)

    row._handle_mouse_release(inside_switch)

    self.assertEqual(writes, [])
    self.assertFalse(row.action_item.get_state())

  def test_disabled_row_ignores_taps(self):
    row, writes = self._row(enabled=False)

    row._handle_mouse_release(rl.Vector2(100, 85))

    self.assertEqual(writes, [])

  def test_description_stays_visible_through_show_event(self):
    row, _ = self._row()
    row.show_event()

    self.assertTrue(row.description_visible)


class TestToggleDefsShape(unittest.TestCase):
  def test_defs_are_uniform_4_tuples(self):
    for param, row in TOGGLE_DEFS.items():
      self.assertEqual(len(row), 4, param)
      title, desc, icon, needs_restart = row
      self.assertTrue(callable(title), param)
      self.assertIsInstance(desc, str, param)
      self.assertIn(param, toggle_defs_mod.DESCRIPTIONS, param)
      self.assertIsInstance(needs_restart, bool, param)


if __name__ == '__main__':
  unittest.main()
