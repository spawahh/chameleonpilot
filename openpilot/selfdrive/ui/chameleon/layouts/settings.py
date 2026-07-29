"""
The Chameleon settings panel: every fork setting in one place.

The settings sidebar is full at seven panels (buttons start 300 px down, 110 px
each, 1080 px screen), so this panel replaces the Themes panel rather than
sitting beside it — the theme picker and night mode are its first section.
Hosting the fork's toggles here is also what lets upstream's Toggles panel go
back to byte-stock.

Usability differences from upstream rows, both deliberate:
- The whole row is the touch target, not just the switch. Upstream uses the
  row tap to expand the description instead, so here descriptions are simply
  always shown — nothing becomes unreachable, the rows are just taller.
- Rows that need the car's blind spot monitoring grey out through a live
  `enabled` callable instead of event plumbing.
"""
import pyray as rl

from openpilot.common.params import Params
from openpilot.selfdrive.ui import themes
from openpilot.selfdrive.ui.chameleon.toggles import DESCRIPTIONS, TOGGLE_DEFS
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.list_view import ListItem, ToggleAction, button_item, multiple_button_item
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.system.ui.widgets.scroller_tici import Scroller

THEME_DESCRIPTIONS = {
  'hud_theme': tr_noop("Color scheme for the onroad display. Stock matches upstream openpilot exactly."),
  'night_mode': tr_noop("Switch to the theme's night palette in the dark. Auto follows ambient light."),
}

NIGHT_MODE_LABELS = {
  "auto": tr_noop("Auto"),
  "on": tr_noop("On"),
  "off": tr_noop("Off"),
}

# panel sections; every TOGGLE_DEFS key not claimed here lands in "HUD Widgets"
DRIVING_PARAMS = ("AutoLaneChangeBsmDelay", "NeuralNetworkLateralControl")
HIDE_PREFIX = "Hide"

SECTION_HEIGHT = 110
SECTION_FONT_SIZE = 44
SECTION_COLOR = rl.Color(160, 160, 160, 255)
SECTION_PADDING = 40


class SectionHeader(Widget):
  """A non-interactive label between groups of rows."""

  def __init__(self, title):
    super().__init__()
    self._title = title
    self._font = gui_app.font(FontWeight.MEDIUM)
    self._rect = rl.Rectangle(0, 0, 0, SECTION_HEIGHT)

  def set_parent_rect(self, parent_rect: rl.Rectangle) -> None:
    super().set_parent_rect(parent_rect)
    self._rect.width = parent_rect.width

  def _render(self, rect: rl.Rectangle) -> None:
    text = self._title() if callable(self._title) else self._title
    position = rl.Vector2(rect.x + SECTION_PADDING, rect.y + rect.height - SECTION_FONT_SIZE - 8)
    rl.draw_text_ex(self._font, text, position, SECTION_FONT_SIZE, 0, SECTION_COLOR)


class ChameleonToggleItem(ListItem):
  """A toggle row where the whole row is the touch target.

  Upstream rows only respond on the switch itself and use the row tap to
  expand the description, so the description here is permanently visible
  instead. A tap on the switch is left to the switch (returning early avoids
  the flip firing twice), and a disabled row ignores taps entirely.
  """

  def __init__(self, title, description, initial_state: bool, callback, icon=None):
    super().__init__(title=title, description=description, description_visible=True,
                     icon=icon, action_item=ToggleAction(initial_state=initial_state, callback=callback))
    self._on_change = callback

  def show_event(self):
    super().show_event()  # collapses the description...
    self._set_description_visible(True)  # ...so re-open it; always-visible is this row's contract

  def _handle_mouse_release(self, mouse_pos) -> None:
    if not self.is_visible:
      return

    action_rect = self.get_right_item_rect(self._rect)
    if rl.check_collision_point_rec(mouse_pos, action_rect):
      return  # the switch handles its own taps

    if not self.action_item.enabled:
      return

    new_state = not self.action_item.get_state()
    self.action_item.set_state(new_state)
    if self._on_change is not None:
      self._on_change(new_state)


class ChameleonSettingsLayout(Widget):
  def __init__(self):
    super().__init__()
    self._params = Params()
    self._theme_dialog: MultiOptionDialog | None = None
    self._night_dialog: MultiOptionDialog | None = None

    self._theme_btn = button_item(lambda: tr("HUD Theme"), self._current_theme_label,
                                  lambda: tr(THEME_DESCRIPTIONS['hud_theme']), callback=self._show_theme_dialog)
    self._night_btn = button_item(lambda: tr("Night Mode"), self._current_night_label,
                                  lambda: tr(THEME_DESCRIPTIONS['night_mode']), callback=self._show_night_dialog)

    # nudgeless auto lane change needs the car's blind spot monitoring (BSM);
    # a live callable greys the rows the moment CarParams arrives
    has_bsm = self._has_bsm
    self._alc_timer = multiple_button_item(
      lambda: tr("Auto Lane Change by Blinker"),
      lambda: tr(DESCRIPTIONS["AutoLaneChangeTimer"]),
      buttons=[lambda: tr("Nudge"), lambda: tr("Nudgeless"), "0.5s", "1s", "2s", "3s"],
      button_width=160,
      callback=self._set_alc_timer,
      selected_index=max(self._params.get("AutoLaneChangeTimer", return_default=True), 0),
      icon="chffr_wheel.png",
    )
    self._alc_timer.action_item.set_enabled(has_bsm)

    self._toggles: dict[str, ChameleonToggleItem] = {}
    for param, (title, desc, icon, needs_restart) in TOGGLE_DEFS.items():
      self._toggles[param] = ChameleonToggleItem(
        title, desc, self._params.get_bool(param),
        callback=self._make_toggle_callback(param, needs_restart),
        icon=icon,
      )
    # the BSM gate applies to the auto-lane-change rows only, not everything in the section
    self._toggles["AutoLaneChangeBsmDelay"].action_item.set_enabled(has_bsm)

    hud_params = [p for p in TOGGLE_DEFS if p not in DRIVING_PARAMS and not p.startswith(HIDE_PREFIX)]
    hide_params = [p for p in TOGGLE_DEFS if p.startswith(HIDE_PREFIX)]

    items: list[Widget] = [
      SectionHeader(lambda: tr("Theme")),
      self._theme_btn,
      self._night_btn,
      SectionHeader(lambda: tr("Driving")),
      self._alc_timer,
      *[self._toggles[p] for p in DRIVING_PARAMS],
      SectionHeader(lambda: tr("HUD Widgets")),
      *[self._toggles[p] for p in hud_params],
    ]
    if hide_params:
      items.append(SectionHeader(lambda: tr("Hide Stock HUD")))
      items.extend(self._toggles[p] for p in hide_params)

    self._scroller = Scroller(items, line_separator=True, spacing=0)

  def _make_toggle_callback(self, param: str, needs_restart: bool):
    def callback(state: bool) -> None:
      self._params.put_bool(param, state, block=True)
      if needs_restart:
        # mirror upstream's restart plumbing: the manager cycles onroad, which
        # is what re-reads params that are only read at process construction
        self._params.put_bool("OnroadCycleRequested", True, block=True)
    return callback

  @staticmethod
  def _has_bsm() -> bool:
    return ui_state.CP is not None and bool(ui_state.CP.enableBsm)

  def _current_theme_label(self) -> str:
    return tr(themes.active().label)

  def _current_night_label(self) -> str:
    return tr(NIGHT_MODE_LABELS.get(themes.night.mode, NIGHT_MODE_LABELS["auto"]))

  def show_event(self):
    super().show_event()
    # mirror external changes (another panel, ssh, a reset) into the rows
    for param, item in self._toggles.items():
      item.action_item.set_state(self._params.get_bool(param))
    self._alc_timer.action_item.set_selected_button(max(self._params.get("AutoLaneChangeTimer", return_default=True), 0))
    self._scroller.show_event()

  def _render(self, rect: rl.Rectangle) -> None:
    self._scroller.render(rect)

  def _set_alc_timer(self, button_index: int) -> None:
    # button order matches AutoLaneChangeMode values (NUDGE=0 .. THREE_SECONDS=5)
    self._params.put("AutoLaneChangeTimer", button_index, block=True)

  def _show_theme_dialog(self) -> None:
    # translated label -> stable param value, so the picker localises without changing what we persist
    options = {tr(t.label): t.name for t in themes.THEMES.values()}

    def handle_theme_selection(result: DialogResult):
      if result == DialogResult.CONFIRM and self._theme_dialog:
        name = options[self._theme_dialog.selection]
        themes.set_active(name)  # single UI process, so this lands on the next frame
        self._params.put(themes.THEME_PARAM, name, block=True)
      self._theme_dialog = None

    self._theme_dialog = MultiOptionDialog(tr("HUD Theme"), options, self._current_theme_label(), callback=handle_theme_selection)
    gui_app.push_widget(self._theme_dialog)

  def _show_night_dialog(self) -> None:
    options = {tr(label): mode for mode, label in NIGHT_MODE_LABELS.items()}

    def handle_night_selection(result: DialogResult):
      if result == DialogResult.CONFIRM and self._night_dialog:
        themes.set_night_mode(options[self._night_dialog.selection], params=self._params)
      self._night_dialog = None

    self._night_dialog = MultiOptionDialog(tr("Night Mode"), options, self._current_night_label(), callback=handle_night_selection)
    gui_app.push_widget(self._night_dialog)
