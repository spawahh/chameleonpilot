from openpilot.common.params import Params
from openpilot.selfdrive.ui import themes
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.list_view import button_item
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.system.ui.widgets.scroller_tici import Scroller

# Description constants
DESCRIPTIONS = {
  'hud_theme': tr_noop("Color scheme for the onroad display. Stock matches upstream openpilot exactly."),
  'night_mode': tr_noop("Switch to the theme's night palette in the dark. Auto follows ambient light."),
}

NIGHT_MODE_LABELS = {
  "auto": tr_noop("Auto"),
  "on": tr_noop("On"),
  "off": tr_noop("Off"),
}


class ThemesLayout(Widget):
  def __init__(self):
    super().__init__()

    self._params = Params()
    self._theme_dialog: MultiOptionDialog | None = None
    self._night_dialog: MultiOptionDialog | None = None

    self._theme_btn = button_item(lambda: tr("HUD Theme"), self._current_label,
                                  lambda: tr(DESCRIPTIONS['hud_theme']), callback=self._show_theme_dialog)
    self._night_btn = button_item(lambda: tr("Night Mode"), self._current_night_label,
                                  lambda: tr(DESCRIPTIONS['night_mode']), callback=self._show_night_dialog)
    self._scroller = Scroller([self._theme_btn, self._night_btn], line_separator=True, spacing=0)

  def _current_label(self) -> str:
    return tr(themes.active().label)

  def _current_night_label(self) -> str:
    return tr(NIGHT_MODE_LABELS.get(themes.night.mode, NIGHT_MODE_LABELS["auto"]))

  def show_event(self):
    super().show_event()
    self._scroller.show_event()

  def _render(self, rect):
    self._scroller.render(rect)

  def _show_theme_dialog(self):
    # translated label -> stable param value, so the picker localises without changing what we persist
    options = {tr(t.label): t.name for t in themes.THEMES.values()}

    def handle_theme_selection(result: DialogResult):
      if result == DialogResult.CONFIRM and self._theme_dialog:
        name = options[self._theme_dialog.selection]
        themes.set_active(name)  # single UI process, so this lands on the next frame
        self._params.put(themes.THEME_PARAM, name, block=True)
      self._theme_dialog = None

    self._theme_dialog = MultiOptionDialog(tr("HUD Theme"), options, self._current_label(), callback=handle_theme_selection)
    gui_app.push_widget(self._theme_dialog)

  def _show_night_dialog(self):
    options = {tr(label): mode for mode, label in NIGHT_MODE_LABELS.items()}

    def handle_night_selection(result: DialogResult):
      if result == DialogResult.CONFIRM and self._night_dialog:
        themes.set_night_mode(options[self._night_dialog.selection], params=self._params)
      self._night_dialog = None

    self._night_dialog = MultiOptionDialog(tr("Night Mode"), options, self._current_night_label(), callback=handle_night_selection)
    gui_app.push_widget(self._night_dialog)
