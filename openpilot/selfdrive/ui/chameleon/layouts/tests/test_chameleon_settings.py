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
from openpilot.selfdrive.ui.chameleon import brightness
from openpilot.selfdrive.ui.chameleon import toggles as toggle_defs_mod
from openpilot.selfdrive.ui.chameleon.layouts import nav
from openpilot.selfdrive.ui.chameleon.layouts import settings as cs
from openpilot.selfdrive.ui.chameleon.toggles import TOGGLE_DEFS
from openpilot.system.ui.widgets import DialogResult
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
    self.param_refreshes = 0

  def update_params(self):
    self.param_refreshes += 1


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
    panel = cs.ChameleonStockHudLayout()
    rows = [panel._toggles[p] for p in cs.STOCK_HUD_PARAMS]

    self.assertEqual(panel._scroller._items, rows)

  def test_driver_alerts_sits_with_the_aircraft_symbology(self):
    """Its default look is a legend in the aircraft annunciator row, so that is
    where someone goes looking for it — it used to be filed under Stock HUD."""
    self.assertIn("DriverAlerts", cs.AIRCRAFT_PARAMS)
    self.assertNotIn("DriverAlerts", cs.STOCK_HUD_PARAMS)

  def test_the_alert_style_row_follows_the_toggle_it_qualifies(self):
    panel = cs.ChameleonAircraftLayout()
    items = panel._scroller._items

    self.assertEqual(items[items.index(panel._toggles["DriverAlerts"]) + 1], panel._alert_style)

  def test_themes_leads_with_the_pickers(self):
    panel = cs.ChameleonThemesLayout()
    items = panel._scroller._items

    self.assertEqual(items[:3], [panel._theme_btn, panel._night_btn, panel._brightness_btn])

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


class TestBrightnessRow(PanelTestCase):
  """The manual brightness picker. Auto is the default and must stay a real
  option, because it is the only value that leaves upstream's backlight alone."""

  def _open_dialog(self, panel):
    dialog_cls = self._patch(mock.patch.object(cs, 'MultiOptionDialog'))
    self._patch(mock.patch.object(cs.gui_app, 'push_widget'))
    panel._show_brightness_dialog()
    _, options, _ = dialog_cls.call_args.args
    return options, dialog_cls.call_args.kwargs['callback'], panel._brightness_dialog

  def test_label_reads_auto_by_default(self):
    self.assertEqual(cs.ChameleonThemesLayout()._current_brightness_label(), "Auto")

  def test_label_reads_the_chosen_level(self):
    self.params.values["ChameleonBrightness"] = 40

    self.assertEqual(cs.ChameleonThemesLayout()._current_brightness_label(), "40%")

  def test_dialog_offers_auto_then_every_level(self):
    options, _, _ = self._open_dialog(cs.ChameleonThemesLayout())

    self.assertEqual(list(options.values()), [brightness.AUTO, *brightness.LEVELS])

  def test_confirming_writes_an_int(self):
    """Params.put is type-checked on an INT key — a string raises on the car."""
    panel = cs.ChameleonThemesLayout()
    options, callback, dialog = self._open_dialog(panel)
    dialog.selection = "40%"

    callback(DialogResult.CONFIRM)

    self.assertEqual(self.params.values["ChameleonBrightness"], 40)
    self.assertIsInstance(self.params.values["ChameleonBrightness"], int)

  def test_confirming_refreshes_params_so_the_screen_moves_now(self):
    panel = cs.ChameleonThemesLayout()
    _, callback, dialog = self._open_dialog(panel)
    dialog.selection = "Auto"

    callback(DialogResult.CONFIRM)

    self.assertEqual(self.ui_state.param_refreshes, 1)

  def test_cancelling_writes_nothing(self):
    panel = cs.ChameleonThemesLayout()
    _, callback, dialog = self._open_dialog(panel)
    dialog.selection = "40%"

    callback(DialogResult.CANCEL)

    self.assertEqual(self.params.puts, [])


class TestAlertStyleRow(PanelTestCase):
  def test_writes_an_int_for_each_button(self):
    """Params.put is type-checked on this INT key, and the button order is the
    AlertStyle values — LEGEND=0, POPUP=1, BOTH=2."""
    panel = cs.ChameleonAircraftLayout()

    for index in (0, 1, 2):
      panel._set_alert_style(index)
      self.assertEqual(self.params.values["DriverAlertStyle"], index)
      self.assertIsInstance(self.params.values["DriverAlertStyle"], int)

  def test_selection_refreshes_params_so_the_next_frame_draws_it(self):
    cs.ChameleonAircraftLayout()._set_alert_style(1)

    self.assertEqual(self.ui_state.param_refreshes, 1)

  def test_a_stale_value_cannot_index_past_the_buttons(self):
    self.params.values["DriverAlertStyle"] = 99

    self.assertEqual(cs.ChameleonAircraftLayout()._alert_style_index(), 2)

  def test_three_buttons_in_alert_style_order(self):
    panel = cs.ChameleonAircraftLayout()

    self.assertEqual(len(panel._alert_style.action_item.buttons), 3)


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


class TestNavLabelFit(NavTestCase):
  """Two sidebar rows drew their label on top of their own icon.

  Panel names are right-aligned, so a label wider than its row grows leftward
  across the icon at the row's left edge — which is what "Aircraft HUD" and
  "Stock HUD", the two longest names in the list, did. Real font metrics only
  exist on the device, so the widths here are faked *proportionally* (length x
  size): what is pinned is that the layout responds to the measurement, not a
  hand-tuned number that was wrong once already.
  """
  ROW = rl.Rectangle(0, 0, nav.SIDEBAR_WIDTH - nav.NAV_RIGHT_PAD, nav.NAV_BTN_HEIGHT)

  def _fake_measure(self, per_char=0.6):
    def measure(_font, text, size, *_args):
      return rl.Vector2(len(text) * size * per_char, float(size))
    return self._patch(mock.patch.object(nav, 'measure_text_cached', side_effect=measure))

  def test_every_label_fits_beside_its_icon_at_the_fitted_size(self):
    self._fake_measure()
    host = self._host()

    size = host._fit_nav_label_size()

    for button in host._nav_buttons:
      width = len(button.label_text) * size * 0.6
      self.assertLessEqual(width, button.label_width_available,
                           f"{button.label_text!r} still crosses its icon at size {size}")

  def test_the_fitted_size_is_the_largest_that_fits(self):
    """Shrink only as far as needed: this is a type size the user reads."""
    self._fake_measure()
    host = self._host()

    size = host._fit_nav_label_size()
    if size > nav.NAV_MIN_LABEL_SIZE:
      too_big = size + 1
      self.assertTrue(any(len(b.label_text) * too_big * 0.6 > b.label_width_available for b in host._nav_buttons))

  def test_one_size_for_the_whole_list(self):
    """Mixed type sizes on evenly spaced rows read as a mistake."""
    self._fake_measure()
    host = self._host()
    host._nav_label_size = host._fit_nav_label_size()
    sizes = set()
    self._patch(mock.patch.object(nav.rl, 'draw_texture_v'))
    text = self._patch(mock.patch.object(nav.rl, 'draw_text_ex'))

    for button in host._nav_buttons:
      button._render(self.ROW)
    for call in text.call_args_list:
      sizes.add(call.args[3])

    self.assertEqual(len(sizes), 1, sizes)

  def test_a_label_can_never_be_drawn_over_its_icon(self):
    """The clamp, tested where the fit cannot help: absurdly wide text."""
    self._fake_measure(per_char=4.0)  # no size in range makes these fit
    host = self._host()
    host._nav_label_size = host._fit_nav_label_size()
    self._patch(mock.patch.object(nav.rl, 'draw_texture_v'))
    text = self._patch(mock.patch.object(nav.rl, 'draw_text_ex'))

    for button in host._nav_buttons:
      if button._icon:
        text.reset_mock()
        button._render(self.ROW)
        self.assertGreaterEqual(text.call_args.args[2].x, self.ROW.x + nav.NAV_ICON_SIZE + nav.NAV_ICON_GAP,
                                f"{button.label_text!r} drawn over its icon")

  def test_the_fit_never_goes_below_the_floor(self):
    self._fake_measure(per_char=4.0)
    host = self._host()

    self.assertEqual(host._fit_nav_label_size(), nav.NAV_MIN_LABEL_SIZE)

  def test_the_aircraft_panel_name_is_the_short_one(self):
    """It was "Aircraft HUD": the widest name in the sidebar by a clear margin,
    and the "HUD" said nothing the panel's own contents do not."""
    host = self._host()

    self.assertEqual(host._panels[nav.ChameleonPanel.AIRCRAFT].name, "Aircraft")


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
