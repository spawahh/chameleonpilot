"""
The fork's settings panels: Themes, Aircraft HUD, Stock HUD, Hide, Driving, Map Data.

Everything the fork adds lives here rather than in upstream's Toggles panel,
which is what lets that file stay byte-stock. Six narrow panels rather than one
long scroll — the sidebar scrolls now (`nav.py`), so panel count is cheap and
the panel name does the job a section header used to.

Rows are plain upstream `toggle_item`s. An earlier version subclassed them so
the whole row toggled, which meant descriptions had to be permanently open —
twenty rows of always-on prose in one panel. Tapping a row now expands its
description and only the switch toggles, matching upstream and sunnypilot.

Rows that need the car's blind spot monitoring grey out through a live
`enabled` callable instead of event plumbing.
"""
from collections.abc import Sequence

import requests

from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.ui import themes
from openpilot.selfdrive.ui.chameleon import brightness
from openpilot.selfdrive.ui.chameleon.toggles import DESCRIPTIONS, TOGGLE_DEFS
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.list_view import ListItem, button_item, multiple_button_item, toggle_item
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.system.ui.widgets.scroller_tici import Scroller

THEME_DESCRIPTIONS = {
  'hud_theme': tr_noop("Color scheme for the onroad display. Stock matches upstream openpilot exactly."),
  'night_mode': tr_noop("Switch to the theme's night palette in the dark. Auto follows ambient light."),
  'brightness': tr_noop(
    "Screen brightness. Auto is openpilot's own behaviour: the road camera's exposure drives the backlight, " +
    "between 30 and 100 percent while driving. A fixed level overrides that everywhere, which is how to get a " +
    "dimmer screen at night than Auto will give you. Changes ease in over about ten seconds, and the screen " +
    "still goes dark on the usual timeout."
  ),
}

BRIGHTNESS_AUTO_LABEL = tr_noop("Auto")

ALERT_STYLE_DESCRIPTION = tr_noop(
  "How a green light or a departing lead is shown. Legend brightens GRN LIGHT or LEAD DEPT in the annunciator row " +
  "at the top of the screen. Pop-up is the original look: a large ringed circle on the right of the road view, " +
  "shown only while the alert fires. Both draws the two together. The chime is the same either way."
)

NIGHT_MODE_LABELS = {
  "auto": tr_noop("Auto"),
  "on": tr_noop("On"),
  "off": tr_noop("Off"),
}

MAP_DATA_DESCRIPTION = tr_noop(
  "Download offline map data (OpenStreetMap) for one US state, used by the speed limit sign and road name display. " +
  "Downloading happens on the device over WiFi and can take a while; the whole US is about 6 GB, single states much less."
)

# Which panel each toggle belongs to. Named explicitly rather than "everything not
# claimed above", so a toggle can never quietly drift into the wrong panel. The cost
# is that a new toggle must be named here, and a test fails if one is missed.
THEMES_PARAMS = ("NightVideo", "RainbowMode")
# DriverAlerts lives here, not under Stock HUD: its default look is a legend in
# the aircraft annunciator row, so that is where someone goes looking for it.
AIRCRAFT_PARAMS = ("AircraftTapes", "PitchLadder", "FlightPathVector", "TargetDesignator",
                   "DmAnnunciator", "DriverAlerts", "RocketFuel")
STOCK_HUD_PARAMS = ("ShowTurnSignals", "BlindSpot", "RoadNameDisplay", "SpeedLimitDisplay")
HIDE_PARAMS = ("HideDriverFace", "HideDrivingPath", "HideLaneLines", "HideSpeedCluster", "HideWheelButton")
DRIVING_PARAMS = ("AutoLaneChangeBsmDelay", "NeuralNetworkLateralControl")

PANEL_PARAMS = THEMES_PARAMS + AIRCRAFT_PARAMS + STOCK_HUD_PARAMS + HIDE_PARAMS + DRIVING_PARAMS


class ChameleonPanelBase(Widget):
  """Row construction, the params round-trip and the scroller, shared by every panel.

  Subclasses assemble their own item list and hand it to `_build`. Everything
  that writes a param lives here, so there is one code path for it.
  """

  def __init__(self):
    super().__init__()
    self._params = Params()
    self._toggles: dict[str, ListItem] = {}
    self._scroller: Scroller | None = None

  def _rows(self, params: Sequence[str]) -> list[Widget]:
    rows: list[Widget] = []
    for param in params:
      title, description, icon, needs_restart = TOGGLE_DEFS[param]
      row = toggle_item(title, description, self._params.get_bool(param),
                        callback=self._make_toggle_callback(param, needs_restart), icon=icon)
      self._toggles[param] = row
      rows.append(row)
    return rows

  def _build(self, items: list[Widget]) -> None:
    self._scroller = Scroller(items, line_separator=True, spacing=0)

  def _make_toggle_callback(self, param: str, needs_restart: bool):
    def callback(state: bool) -> None:
      self._params.put_bool(param, state, block=True)
      if needs_restart:
        # mirror upstream's restart plumbing: the manager cycles onroad, which
        # is what re-reads params that are only read at process construction
        self._params.put_bool("OnroadCycleRequested", True, block=True)
    return callback

  def show_event(self):
    super().show_event()
    # mirror external changes (another panel, ssh, a reset) into the rows
    for param, item in self._toggles.items():
      item.action_item.set_state(self._params.get_bool(param))
    if self._scroller is not None:
      self._scroller.show_event()

  def _render(self, rect):
    if self._scroller is not None:
      self._scroller.render(rect)


class ChameleonThemesLayout(ChameleonPanelBase):
  """How the screen looks: the palette, when it goes dark, how bright it is."""

  def __init__(self):
    super().__init__()
    self._theme_dialog: MultiOptionDialog | None = None
    self._night_dialog: MultiOptionDialog | None = None
    self._brightness_dialog: MultiOptionDialog | None = None

    self._theme_btn = button_item(lambda: tr("HUD Theme"), self._current_theme_label,
                                  lambda: tr(THEME_DESCRIPTIONS['hud_theme']), callback=self._show_theme_dialog)
    self._night_btn = button_item(lambda: tr("Night Mode"), self._current_night_label,
                                  lambda: tr(THEME_DESCRIPTIONS['night_mode']), callback=self._show_night_dialog)
    self._brightness_btn = button_item(lambda: tr("Screen Brightness"), self._current_brightness_label,
                                       lambda: tr(THEME_DESCRIPTIONS['brightness']), callback=self._show_brightness_dialog)

    self._build([self._theme_btn, self._night_btn, self._brightness_btn, *self._rows(THEMES_PARAMS)])

  def _current_theme_label(self) -> str:
    return tr(themes.active().label)

  def _current_night_label(self) -> str:
    return tr(NIGHT_MODE_LABELS.get(themes.night.mode, NIGHT_MODE_LABELS["auto"]))

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

  def _brightness_percent(self) -> int:
    # INT-typed param: get returns an int already, never a string to parse
    return self._params.get("ChameleonBrightness", return_default=True) or brightness.AUTO

  def _current_brightness_label(self) -> str:
    percent = self._brightness_percent()
    return tr(BRIGHTNESS_AUTO_LABEL) if percent == brightness.AUTO else f"{percent}%"

  def _show_brightness_dialog(self) -> None:
    options: dict[str, int] = {tr(BRIGHTNESS_AUTO_LABEL): brightness.AUTO}
    options.update({f"{percent}%": percent for percent in brightness.LEVELS})

    def handle_brightness_selection(result: DialogResult):
      if result == DialogResult.CONFIRM and self._brightness_dialog:
        # an int, not a string: Params.put is type-checked on this INT key
        self._params.put("ChameleonBrightness", options[self._brightness_dialog.selection], block=True)
        # same as upstream's toggle rows: refresh now so the backlight starts
        # moving with the dialog, rather than at the next background param tick
        ui_state.update_params()
      self._brightness_dialog = None

    self._brightness_dialog = MultiOptionDialog(tr("Screen Brightness"), options, self._current_brightness_label(),
                                                callback=handle_brightness_selection)
    gui_app.push_widget(self._brightness_dialog)


class ChameleonAircraftLayout(ChameleonPanelBase):
  """The flight-display symbology the fork draws over the road."""

  def __init__(self):
    super().__init__()

    self._alert_style = multiple_button_item(
      lambda: tr("Green Light / Lead Alert Style"),
      lambda: tr(ALERT_STYLE_DESCRIPTION),
      buttons=[lambda: tr("Legend"), lambda: tr("Pop-up"), lambda: tr("Both")],
      button_width=220,
      callback=self._set_alert_style,
      selected_index=self._alert_style_index(),
      icon="warning.png",
    )

    rows = self._rows(AIRCRAFT_PARAMS)
    # The style row sits immediately under the toggle it qualifies, rather than at
    # the end of the panel where it would read as unrelated. If that toggle ever
    # moves to another panel the row goes last instead of raising: an unguarded
    # .index() here is a ValueError inside a panel constructor, i.e. a dead
    # settings screen on the car, and the row's position is a nicety while
    # reaching the settings at all is not.
    split = len(rows)
    if "DriverAlerts" in AIRCRAFT_PARAMS:
      split = AIRCRAFT_PARAMS.index("DriverAlerts") + 1
    self._build([*rows[:split], self._alert_style, *rows[split:]])

  def _alert_style_index(self) -> int:
    # INT-typed param: get returns an int. Clamp so a stale or hand-edited value
    # cannot index past the three buttons.
    value = self._params.get("DriverAlertStyle", return_default=True) or 0
    return min(max(value, 0), 2)

  def show_event(self):
    super().show_event()
    self._alert_style.action_item.set_selected_button(self._alert_style_index())

  def _set_alert_style(self, button_index: int) -> None:
    # button order matches AlertStyle: LEGEND=0, POPUP=1, BOTH=2
    self._params.put("DriverAlertStyle", button_index, block=True)
    ui_state.update_params()  # single UI process, so the next frame draws the new look


class ChameleonStockHudLayout(ChameleonPanelBase):
  """Additions to openpilot's own HUD, rather than replacements for it."""

  def __init__(self):
    super().__init__()
    self._build(self._rows(STOCK_HUD_PARAMS))


class ChameleonHideLayout(ChameleonPanelBase):
  """Turning off parts of the stock HUD, to make room for the fork's own."""

  def __init__(self):
    super().__init__()
    self._build(self._rows(HIDE_PARAMS))


class ChameleonDrivingLayout(ChameleonPanelBase):
  """The only fork settings that change what the car does rather than what it shows."""

  def __init__(self):
    super().__init__()

    # nudgeless auto lane change needs the car's blind spot monitoring (BSM);
    # a live callable greys the rows the moment CarParams arrives
    has_bsm = self._has_bsm
    self._alc_timer = multiple_button_item(
      # Two lines on purpose. This row carries six buttons (960 px of them), and
      # upstream sizes the button block with `content_width - title_width`, so a
      # long single-line title squeezes the buttons rather than wrapping itself.
      # Breaking the title drops the measured width to its longest line, which
      # hands the buttons their full width back. raylib's draw_text_ex and
      # measure_text_ex both understand "\n", and two 50 px lines (~135 px drawn)
      # fit inside the 170 px row.
      lambda: tr("Auto Lane Change\nby Blinker"),
      lambda: tr(DESCRIPTIONS["AutoLaneChangeTimer"]),
      buttons=[lambda: tr("Nudge"), lambda: tr("Nudgeless"), "0.5s", "1s", "2s", "3s"],
      button_width=160,
      callback=self._set_alc_timer,
      selected_index=max(self._params.get("AutoLaneChangeTimer", return_default=True), 0),
      icon="chffr_wheel.png",
    )
    self._alc_timer.action_item.set_enabled(has_bsm)

    rows = self._rows(DRIVING_PARAMS)
    # the BSM gate applies to the auto-lane-change rows only, not everything here
    self._toggles["AutoLaneChangeBsmDelay"].action_item.set_enabled(has_bsm)

    self._build([self._alc_timer, *rows])

  @staticmethod
  def _has_bsm() -> bool:
    return ui_state.CP is not None and bool(ui_state.CP.enableBsm)

  def show_event(self):
    super().show_event()
    self._alc_timer.action_item.set_selected_button(max(self._params.get("AutoLaneChangeTimer", return_default=True), 0))

  def _set_alc_timer(self, button_index: int) -> None:
    # button order matches AutoLaneChangeMode values (NUDGE=0 .. THREE_SECONDS=5)
    self._params.put("AutoLaneChangeTimer", button_index, block=True)


class ChameleonMapDataLayout(ChameleonPanelBase):
  """The offline map download the speed limit sign and road name depend on."""

  def __init__(self):
    super().__init__()
    self._region_dialog: MultiOptionDialog | None = None
    self._region_btn = button_item(lambda: tr("Map Data Region"), self._current_region_label,
                                   lambda: tr(MAP_DATA_DESCRIPTION), callback=self._show_region_dialog)
    self._build([self._region_btn])

  def _current_region_label(self) -> str:
    """The button's value: the chosen region, with download progress while one runs."""
    state = self._params.get("OsmStateName", return_default=True) or ""
    label = state if state else tr("None")

    try:
      # OSMDownloadProgress is JSON-typed: Params.get returns the parsed dict directly
      progress = self._params.get("OSMDownloadProgress") or {}
      total, done = int(progress.get("total_files", 0)), int(progress.get("downloaded_files", 0))
      if total > 0 and done < total:
        label += f"  ({100 * done // total}%)"
    except (AttributeError, ValueError, TypeError):
      pass
    return label

  def _show_region_dialog(self) -> None:
    # the state list lives beside the map extracts, fetched live like sunnypilot does;
    # offline just means an empty dialog, never a crash
    try:
      url = "https://raw.githubusercontent.com/pfeiferj/openpilot-mapd/main/us_states_bounding_boxes.json"
      states = sorted(requests.get(url, timeout=10).json().keys())
    except Exception:
      cloudlog.warning("chameleon mapd: could not fetch the region list (offline?)")
      states = []
    options = {name: name for name in states}

    def handle_selection(result: DialogResult):
      if result == DialogResult.CONFIRM and self._region_dialog:
        self._params.put("OsmLocationName", "US", block=True)
        self._params.put("OsmStateName", options[self._region_dialog.selection], block=True)
        self._params.put_bool("OsmDbUpdatesCheck", True, block=True)
      self._region_dialog = None

    self._region_dialog = MultiOptionDialog(tr("Map Data Region (US states)"), options,
                                            self._params.get("OsmStateName", return_default=True) or "", callback=handle_selection)
    gui_app.push_widget(self._region_dialog)
