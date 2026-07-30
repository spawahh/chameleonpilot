"""The fork's settings surface — six panels and the sidebar that hosts them — without a window.

What these pin, in order of how quietly it would break:
- every fork toggle lands in exactly one panel (the panel lists are explicit, so a
  new toggle would otherwise just not appear anywhere)
- rows behave like upstream's: tapping the row expands the description and only
  the switch writes a param
- the sidebar keeps upstream's own panels reachable below the divider, and a
  scroll drag that ends over a row does not select it
- upstream's `settings.py` and `toggles.py` carry no fork lines
"""
import unittest
from unittest import mock

import pyray as rl

import openpilot.selfdrive.ui.layouts.settings.settings as st
from openpilot.selfdrive.ui.chameleon import toggles as toggle_defs_mod
from openpilot.selfdrive.ui.chameleon.layouts import nav
from openpilot.selfdrive.ui.chameleon.layouts import settings as cs
from openpilot.selfdrive.ui.chameleon.toggles import TOGGLE_DEFS
from openpilot.system.ui.widgets.scroller_tici import LineSeparator


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


# panel class -> the param tuple it is supposed to render
PANEL_CONTENTS = (
  (cs.ChameleonThemesLayout, cs.THEMES_PARAMS),
  (cs.ChameleonAircraftLayout, cs.AIRCRAFT_PARAMS),
  (cs.ChameleonStockHudLayout, cs.STOCK_HUD_PARAMS),
  (cs.ChameleonHideLayout, cs.HIDE_PARAMS),
  (cs.ChameleonDrivingLayout, cs.DRIVING_PARAMS),
  (cs.ChameleonMapDataLayout, ()),
)


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


class TestPanelSplit(PanelTestCase):
  def test_all_panels_construct_windowless(self):
    for panel_cls, _ in PANEL_CONTENTS:
      with self.subTest(panel=panel_cls.__name__):
        panel_cls()

  def test_every_toggle_lands_in_exactly_one_panel(self):
    """The panel lists are explicit, so a new toggle is orphaned until it is named."""
    groups = [cs.THEMES_PARAMS, cs.AIRCRAFT_PARAMS, cs.STOCK_HUD_PARAMS, cs.HIDE_PARAMS, cs.DRIVING_PARAMS]

    self.assertEqual(set(cs.PANEL_PARAMS), set(TOGGLE_DEFS))
    self.assertEqual(sum(len(g) for g in groups), len(set(cs.PANEL_PARAMS)))

  def test_panels_build_the_rows_they_claim(self):
    for panel_cls, params in PANEL_CONTENTS:
      with self.subTest(panel=panel_cls.__name__):
        self.assertEqual(set(panel_cls()._toggles), set(params))

  def test_row_order_follows_the_param_tuple(self):
    panel = cs.ChameleonAircraftLayout()
    rows = [panel._toggles[p] for p in cs.AIRCRAFT_PARAMS]

    self.assertEqual(panel._scroller._items, rows)

  def test_themes_leads_with_the_pickers(self):
    panel = cs.ChameleonThemesLayout()
    items = panel._scroller._items

    self.assertEqual(items[:2], [panel._theme_btn, panel._night_btn])

  def test_upstream_toggles_panel_is_stock(self):
    """The whole point of the fork panels: upstream's TogglesLayout owes the fork nothing."""
    import openpilot.selfdrive.ui.layouts.settings.toggles as upstream_toggles

    with open(upstream_toggles.__file__, encoding="utf-8") as f:
      self.assertNotIn("chameleon", f.read().lower())

  def test_upstream_settings_layout_is_stock(self):
    """The sidebar host is a fork subclass, so this file names no fork panel either."""
    with open(st.__file__, encoding="utf-8") as f:
      self.assertNotIn("chameleon", f.read().lower())


class TestRowBehaviour(PanelTestCase):
  def _row(self, param="PitchLadder"):
    panel = cs.ChameleonAircraftLayout()
    row = panel._toggles[param]
    row.set_rect(rl.Rectangle(0, 0, 1000, 170))
    return panel, row

  def test_descriptions_start_collapsed(self):
    _, row = self._row()

    self.assertFalse(row.description_visible)

  def test_tap_on_the_row_expands_instead_of_toggling(self):
    _, row = self._row()

    row._handle_mouse_release(rl.Vector2(100, 85))

    self.assertTrue(row.description_visible)
    self.assertEqual(self.params.puts, [])
    self.assertFalse(row.action_item.get_state())

  def test_tapping_again_collapses(self):
    _, row = self._row()

    row._handle_mouse_release(rl.Vector2(100, 85))
    row._handle_mouse_release(rl.Vector2(100, 85))

    self.assertFalse(row.description_visible)

  def test_tap_on_the_switch_leaves_the_description_alone(self):
    _, row = self._row()
    switch = row.get_right_item_rect(row.rect)

    row._handle_mouse_release(rl.Vector2(switch.x + switch.width / 2, switch.y + switch.height / 2))

    self.assertFalse(row.description_visible)


class TestParamsRoundTrip(PanelTestCase):
  def test_toggle_callback_writes_its_param(self):
    panel = cs.ChameleonAircraftLayout()

    panel._toggles["PitchLadder"].action_item.toggle._callback(True)

    self.assertIn(("PitchLadder", True), self.params.puts)

  def test_alc_timer_writes_int_index(self):
    panel = cs.ChameleonDrivingLayout()

    panel._set_alc_timer(2)

    self.assertIn(("AutoLaneChangeTimer", 2), self.params.puts)

  def test_restart_toggle_requests_an_onroad_cycle(self):
    """Params read at process construction only take effect after a cycle."""
    panel = cs.ChameleonDrivingLayout()

    panel._toggles["NeuralNetworkLateralControl"].action_item.toggle._callback(True)

    self.assertIn(("NeuralNetworkLateralControl", True), self.params.puts)
    self.assertIn(("OnroadCycleRequested", True), self.params.puts)

  def test_live_toggle_does_not_cycle_onroad(self):
    panel = cs.ChameleonAircraftLayout()

    panel._toggles["PitchLadder"].action_item.toggle._callback(True)

    self.assertNotIn(("OnroadCycleRequested", True), self.params.puts)

  def test_show_event_mirrors_external_changes(self):
    """Panels re-read params on show, so a change made elsewhere lands."""
    themes_panel, driving = cs.ChameleonThemesLayout(), cs.ChameleonDrivingLayout()
    self.params.values["RainbowMode"] = True
    self.params.values["AutoLaneChangeTimer"] = 3

    themes_panel.show_event()
    driving.show_event()

    self.assertTrue(themes_panel._toggles["RainbowMode"].action_item.get_state())
    self.assertEqual(driving._alc_timer.action_item.get_selected_button(), 3)


class TestBsmGating(PanelTestCase):
  def test_rows_disabled_without_bsm(self):
    self.ui_state.CP = FakeCP(enable_bsm=False)
    panel = cs.ChameleonDrivingLayout()

    self.assertFalse(panel._alc_timer.action_item.enabled)
    self.assertFalse(panel._toggles["AutoLaneChangeBsmDelay"].action_item.enabled)

  def test_rows_enabled_with_bsm(self):
    self.ui_state.CP = FakeCP(enable_bsm=True)
    panel = cs.ChameleonDrivingLayout()

    self.assertTrue(panel._alc_timer.action_item.enabled)
    self.assertTrue(panel._toggles["AutoLaneChangeBsmDelay"].action_item.enabled)

  def test_gate_is_live_not_snapshotted(self):
    """CarParams arrives after construction; the rows must follow it."""
    self.ui_state.CP = None
    panel = cs.ChameleonDrivingLayout()
    self.assertFalse(panel._alc_timer.action_item.enabled)

    self.ui_state.CP = FakeCP(enable_bsm=True)
    self.assertTrue(panel._alc_timer.action_item.enabled)

  def test_nnlc_is_never_gated_on_bsm(self):
    """The gate is for auto lane change only; NNLC has nothing to do with blind spot."""
    self.ui_state.CP = FakeCP(enable_bsm=False)
    panel = cs.ChameleonDrivingLayout()

    self.assertTrue(panel._toggles["NeuralNetworkLateralControl"].action_item.enabled)


class NavTestCase(PanelTestCase):
  """Upstream's own panels are heavy (wifi threads, textures), so they are mocked.

  What is under test is the sidebar, not them — the fork's six panels stay real.
  """

  UPSTREAM_PANELS = ("DeviceLayout", "NetworkUI", "TogglesLayout", "SoftwareLayout",
                     "FirehoseLayout", "DeveloperLayout", "WifiManager")

  def setUp(self):
    super().setUp()
    for name in self.UPSTREAM_PANELS:
      self._patch(mock.patch.object(st, name, return_value=mock.Mock()))
    self._patch(mock.patch.object(st.gui_app, 'font', return_value=FakeFont()))
    self._patch(mock.patch.object(st.gui_app, 'texture', return_value=mock.Mock(width=70, height=70)))

  def _host(self):
    host = nav.ChameleonSettingsLayout()
    # upstream sets this while drawing the sidebar; the tests never draw
    host._close_btn_rect = rl.Rectangle(0, 0, 0, 0)
    return host


class TestSidebar(NavTestCase):
  def test_constructs_windowless(self):
    self._host()

  def test_fork_panels_lead_and_upstream_follows(self):
    order = list(self._host()._panels)

    self.assertEqual(order[:len(nav.ChameleonPanel)], list(nav.ChameleonPanel))
    self.assertEqual(order[len(nav.ChameleonPanel):], list(st.PanelType))

  def test_all_upstream_panels_survive(self):
    panels = self._host()._panels

    for panel_type in st.PanelType:
      self.assertIn(panel_type, panels, panel_type)
    self.assertEqual(len(panels), len(st.PanelType) + len(nav.ChameleonPanel))

  def test_upstream_enum_has_no_fork_member(self):
    """The fork used to add CHAMELEON = 6 here; the subclass is what replaced that."""
    self.assertNotIn("CHAMELEON", st.PanelType.__members__)

  def test_upstream_enum_keys_still_resolve(self):
    """main.py opens panels by upstream's enum, and the dict now has mixed key types."""
    host = self._host()

    host.set_current_panel(st.PanelType.FIREHOSE)

    self.assertEqual(host.current_panel, st.PanelType.FIREHOSE)

  def test_one_nav_button_per_panel_plus_one_divider(self):
    items = self._host()._nav_scroller._items

    self.assertEqual(len([i for i in items if isinstance(i, nav.NavButton)]), len(nav.ChameleonPanel) + len(st.PanelType))
    self.assertEqual(len([i for i in items if isinstance(i, LineSeparator)]), 1)

  def test_the_divider_sits_between_the_two_groups(self):
    items = self._host()._nav_scroller._items
    divider = next(i for i in items if isinstance(i, LineSeparator))

    self.assertEqual(items.index(divider), len(nav.ChameleonPanel))

  def test_only_fork_panels_carry_an_icon(self):
    panels = self._host()._panels

    for panel_type in nav.ChameleonPanel:
      self.assertTrue(getattr(panels[panel_type], "icon", ""), panel_type)
    for panel_type in st.PanelType:
      self.assertFalse(getattr(panels[panel_type], "icon", ""), panel_type)

  def test_every_panel_icon_asset_exists(self):
    """A missing texture is a silent no-draw at runtime, so resolve the paths here."""
    from openpilot.system.ui.lib.application import ASSETS_DIR
    panels = self._host()._panels

    for panel_type in nav.ChameleonPanel:
      path = ASSETS_DIR.joinpath("icons", panels[panel_type].icon)
      self.assertTrue(path.is_file(), str(path))

  def test_the_panel_list_no_longer_fits_unscrolled(self):
    """If it ever fits again, the scroller stopped being the reason this works."""
    host = self._host()
    stacked = len(host._panels) * nav.NAV_BTN_HEIGHT + nav.GROUP_DIVIDER_HEIGHT

    self.assertGreater(stacked + 300, 1080)


class TestSidebarTaps(NavTestCase):
  def _host_with_row(self, panel_type, valid_touch=True):
    host = self._host()
    host._panels[panel_type].button_rect = rl.Rectangle(0, 400, 400, nav.NAV_BTN_HEIGHT)
    self._patch(mock.patch.object(host._nav_scroller.scroll_panel, 'is_touch_valid', return_value=valid_touch))
    return host

  def test_tap_selects_the_panel_under_it(self):
    host = self._host_with_row(nav.ChameleonPanel.AIRCRAFT)

    host._handle_mouse_release(rl.Vector2(200, 450))

    self.assertEqual(host.current_panel, nav.ChameleonPanel.AIRCRAFT)

  def test_a_scroll_drag_selects_nothing(self):
    """A release that scrolled the list is a drag, not a tap on whatever ended up under it."""
    host = self._host_with_row(nav.ChameleonPanel.AIRCRAFT, valid_touch=False)
    before = host.current_panel

    host._handle_mouse_release(rl.Vector2(200, 450))

    self.assertEqual(host.current_panel, before)

  def test_close_button_still_closes(self):
    host = self._host_with_row(nav.ChameleonPanel.AIRCRAFT)
    closed = []
    host.set_callbacks(on_close=lambda: closed.append(True))
    host._close_btn_rect = rl.Rectangle(0, 0, 200, 200)

    host._handle_mouse_release(rl.Vector2(100, 100))

    self.assertEqual(closed, [True])
    self.assertNotEqual(host.current_panel, nav.ChameleonPanel.AIRCRAFT)


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
