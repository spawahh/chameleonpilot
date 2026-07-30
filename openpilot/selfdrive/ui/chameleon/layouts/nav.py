"""
The fork's settings sidebar: a scrollable, icon-labelled panel list.

Upstream lays the nav buttons out from a fixed `y + 300` at `NAV_BTN_HEIGHT`
each, which fits exactly seven on a 1080 px screen — full before the fork adds
anything, which is why the fork's settings used to displace the Themes panel.
Ported from sunnypilot's `SettingsLayoutSP`, which runs fifteen panels through
a `Scroller`. The fork's six sit at the top with icons, then a divider, then
upstream's own six plain ones: twelve rows, 1320 px, so the scroller is doing
real work rather than future-proofing.

Subclassing is the point, not just the extra room: the sidebar geometry and the
panel list move into fork code, so upstream's `settings.py` carries no fork
lines at all and the only upstream edit left is which class `layouts/main.py`
instantiates.

Fork panels get their own IntEnum, with values clear of upstream's 0-5. Rebuilding
upstream's `PanelType` (sunnypilot's approach) also works — a member with the same
name and value is both equal and equally hashed, so dict lookups still land — but
two enums interoperating by coincidence is exactly the shape of the capnp
`_DynamicEnum` bug that ate a drive, so the fork keeps its keys distinct instead.
"""
from dataclasses import dataclass
from enum import IntEnum
from typing import cast

import pyray as rl

from openpilot.selfdrive.ui.chameleon.layouts.settings import (
  ChameleonAircraftLayout,
  ChameleonDrivingLayout,
  ChameleonHideLayout,
  ChameleonMapDataLayout,
  ChameleonStockHudLayout,
  ChameleonThemesLayout,
)
from openpilot.selfdrive.ui.layouts.settings.settings import (
  CLOSE_BTN_SIZE,
  NAV_BTN_HEIGHT,
  PanelInfo,
  PanelType,
  SettingsLayout,
  SIDEBAR_COLOR,
  SIDEBAR_WIDTH,
  TEXT_SELECTED,
)
from openpilot.selfdrive.ui.themes import OFFROAD_COLORS
from openpilot.system.ui.lib.application import gui_app, MousePos
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.scroller_tici import LineSeparator, Scroller

# Matches upstream's own sidebar metrics so the rows land where they always did:
# buttons inset 50 px, 100 px of clear space on the right, label right-aligned.
NAV_LEFT_PAD = 50
NAV_RIGHT_PAD = 150
NAV_LABEL_SIZE = 65
NAV_ICON_SIZE = 70
CLOSE_BTN_TOP = 60
NAV_TOP_GAP = 40  # 60 + 200 + 40 puts the first row at y + 300, where upstream starts it
GROUP_DIVIDER_HEIGHT = 48  # LineSeparator draws at its top edge, so the rest is breathing room


class ChameleonPanel(IntEnum):
  THEMES = 100
  AIRCRAFT = 101
  STOCK_HUD = 102
  HIDE = 103
  DRIVING = 104
  MAP_DATA = 105


@dataclass
class ChameleonPanelInfo(PanelInfo):
  """Upstream's PanelInfo plus an icon. Only the fork's rows carry one."""
  icon: str = ""


class NavButton(Widget):
  """One sidebar row.

  The scroller repositions these every frame, so the row publishes where it
  landed onto the shared `PanelInfo` and the host hit-tests against that —
  the same contract as upstream's layout loop, which stores the rect it just
  computed. Taps are not handled here: the host needs to reject the ones that
  were really a scroll drag, and it owns the scroll panel.
  """

  def __init__(self, host: "ChameleonSettingsLayout", panel_type: IntEnum, panel_info: PanelInfo):
    super().__init__()
    self._host = host
    self._panel_type = panel_type
    self._panel_info = panel_info
    self._icon = getattr(panel_info, "icon", "")

  def _render(self, rect: rl.Rectangle) -> None:
    selected = self._panel_type == self._host.current_panel
    color = TEXT_SELECTED if selected else OFFROAD_COLORS.TEXT_DIM

    if self._icon:
      texture = gui_app.texture(f"icons/{self._icon}", NAV_ICON_SIZE, NAV_ICON_SIZE)
      position = rl.Vector2(rect.x, rect.y + (rect.height - texture.height) / 2)
      rl.draw_texture_v(texture, position, color)

    name = tr(self._panel_info.name)
    measure = measure_text_cached(self._host.nav_font, name, NAV_LABEL_SIZE)
    position = rl.Vector2(rect.x + rect.width - measure.x, rect.y + (rect.height - measure.y) / 2)
    rl.draw_text_ex(self._host.nav_font, name, position, NAV_LABEL_SIZE, 0, color)

    self._panel_info.button_rect = rect


class ChameleonSettingsLayout(SettingsLayout):
  """Upstream's settings screen with a scrollable sidebar and the fork's panels."""

  def __init__(self):
    super().__init__()

    fork_panels: dict[IntEnum, PanelInfo] = {
      ChameleonPanel.THEMES: ChameleonPanelInfo(tr_noop("Themes"), ChameleonThemesLayout(), icon="settings.png"),
      ChameleonPanel.AIRCRAFT: ChameleonPanelInfo(tr_noop("Aircraft HUD"), ChameleonAircraftLayout(), icon="calibration.png"),
      ChameleonPanel.STOCK_HUD: ChameleonPanelInfo(tr_noop("Stock HUD"), ChameleonStockHudLayout(), icon="road.png"),
      ChameleonPanel.HIDE: ChameleonPanelInfo(tr_noop("Hide"), ChameleonHideLayout(), icon="eye_closed.png"),
      ChameleonPanel.DRIVING: ChameleonPanelInfo(tr_noop("Driving"), ChameleonDrivingLayout(), icon="chffr_wheel.png"),
      ChameleonPanel.MAP_DATA: ChameleonPanelInfo(tr_noop("Map Data"), ChameleonMapDataLayout(), icon="speed_limit.png"),
    }

    # the fork's panels lead; upstream's keep their own order below the divider
    panels: dict[IntEnum, PanelInfo] = {}
    for panel_type, panel_info in fork_panels.items():
      panels[panel_type] = panel_info
    for panel_type, panel_info in self._panels.items():
      panels[panel_type] = panel_info
    self._panels = panels

    self._nav_scroller = Scroller([], spacing=0, line_separator=False, pad_end=False)
    for panel_type, panel_info in self._panels.items():
      if panel_type == PanelType.DEVICE:
        self._nav_scroller.add_widget(LineSeparator(height=GROUP_DIVIDER_HEIGHT))
      button = NavButton(self, panel_type, panel_info)
      button.rect.width = SIDEBAR_WIDTH - NAV_RIGHT_PAD
      button.rect.height = NAV_BTN_HEIGHT
      self._nav_scroller.add_widget(button)

  @property
  def current_panel(self) -> IntEnum:
    return self._current_panel

  @property
  def nav_font(self):
    return self._font_medium

  def _draw_sidebar(self, rect: rl.Rectangle) -> None:
    rl.draw_rectangle_rec(rect, SIDEBAR_COLOR)
    self._draw_close_button(rect)

    nav_top = self._close_btn_rect.y + self._close_btn_rect.height + NAV_TOP_GAP
    nav_rect = rl.Rectangle(rect.x + NAV_LEFT_PAD, nav_top, rect.width - NAV_LEFT_PAD, rect.y + rect.height - nav_top)
    self._nav_scroller.render(nav_rect)

  def _draw_close_button(self, rect: rl.Rectangle) -> None:
    """Upstream draws this inline in `_draw_sidebar`; overriding that means redrawing it here."""
    close_btn_rect = rl.Rectangle(rect.x + (rect.width - CLOSE_BTN_SIZE) / 2, rect.y + CLOSE_BTN_TOP,
                                  CLOSE_BTN_SIZE, CLOSE_BTN_SIZE)

    pressed = (rl.is_mouse_button_down(rl.MouseButton.MOUSE_BUTTON_LEFT) and
               rl.check_collision_point_rec(rl.get_mouse_position(), close_btn_rect))
    close_color = OFFROAD_COLORS.CLOSE_BTN_PRESSED if pressed else OFFROAD_COLORS.CLOSE_BTN_BG
    rl.draw_rectangle_rounded(close_btn_rect, 1.0, 20, close_color)

    icon_color = rl.Color(255, 255, 255, 255) if not pressed else rl.Color(220, 220, 220, 255)
    icon_dest = rl.Rectangle(
      close_btn_rect.x + (close_btn_rect.width - self._close_icon.width) / 2,
      close_btn_rect.y + (close_btn_rect.height - self._close_icon.height) / 2,
      self._close_icon.width,
      self._close_icon.height,
    )
    rl.draw_texture_pro(self._close_icon, rl.Rectangle(0, 0, self._close_icon.width, self._close_icon.height),
                        icon_dest, rl.Vector2(0, 0), 0, icon_color)

    self._close_btn_rect = close_btn_rect

  def _handle_mouse_release(self, mouse_pos: MousePos) -> None:
    if rl.check_collision_point_rec(mouse_pos, self._close_btn_rect):
      if self._close_callback:
        self._close_callback()
      return

    # a release that scrolled the list is a drag, not a tap on whatever ended up
    # under the finger
    if not self._nav_scroller.scroll_panel.is_touch_valid():
      return

    for panel_type, panel_info in self._panels.items():
      if rl.check_collision_point_rec(mouse_pos, panel_info.button_rect):
        # upstream annotates this PanelType; the fork's own panels are a separate
        # IntEnum on purpose (see the module docstring) and the method only ever
        # uses the value as a dict key
        self.set_current_panel(cast(PanelType, panel_type))
        return

  def show_event(self):
    super().show_event()
    self._nav_scroller.show_event()
