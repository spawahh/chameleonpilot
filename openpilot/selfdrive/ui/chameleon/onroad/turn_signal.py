"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's selfdrive/ui/sunnypilot/onroad/turn_signal.py.
Blind spot display is deliberately left out here — port/blind-spot owns that, and drawing
it in both places would put two blind spot icons on the screen at once.
"""
import pyray as rl
import time
from dataclasses import dataclass

from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.mici.onroad.alert_renderer import IconSide, TURN_SIGNAL_BLINK_PERIOD
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import Widget
from openpilot.common.filter_simple import FirstOrderFilter

MAX_ALPHA = 255


@dataclass(frozen=True)
class TurnSignalConfig:
  left_x: int = 80
  left_y: int = 190
  right_x: int = 80
  right_y: int = 190
  size: int = 150


class TurnSignalWidget(Widget):
  def __init__(self, direction: IconSide):
    super().__init__()
    self._direction = direction
    self._active = False

    self._turn_signal_timer = 0.0
    self._turn_signal_alpha_filter = FirstOrderFilter(0.0, 0.3, 1 / gui_app.target_fps)

    self._texture = gui_app.texture('icons_mici/onroad/turn_signal_left.png', 120, 109, flip_x=(direction == IconSide.right))

  @property
  def active(self) -> bool:
    return self._active

  def _render(self, _):
    if not self._active:
      return

    # Snap to full brightness at the start of each blink, then decay toward dim
    if time.monotonic() - self._turn_signal_timer > TURN_SIGNAL_BLINK_PERIOD:
      self._turn_signal_timer = time.monotonic()
      self._turn_signal_alpha_filter.x = MAX_ALPHA * 2
    else:
      self._turn_signal_alpha_filter.update(MAX_ALPHA * 0.2)
    icon_alpha = int(min(self._turn_signal_alpha_filter.x, MAX_ALPHA))

    if self._texture:
      pos_x = self._rect.x + (self._rect.width - self._texture.width) / 2
      pos_y = self._rect.y + (self._rect.height - self._texture.height) / 2
      rl.draw_texture_ex(self._texture, rl.Vector2(pos_x, pos_y), 0.0, 1.0, rl.Color(255, 255, 255, icon_alpha))

  def activate(self):
    if not self._active:
      self._turn_signal_timer = 0.0
    self._active = True

  def deactivate(self):
    self._active = False
    self._turn_signal_timer = 0.0


class TurnSignalController:
  def __init__(self):
    self._config = TurnSignalConfig()
    self._left_signal = TurnSignalWidget(direction=IconSide.left)
    self._right_signal = TurnSignalWidget(direction=IconSide.right)

  @staticmethod
  def _update_signal(signal: TurnSignalWidget, blinker: bool) -> None:
    if ui_state.turn_signals and blinker:
      signal.activate()
    else:
      signal.deactivate()

  def update(self) -> None:
    CS = ui_state.sm['carState']

    self._update_signal(self._left_signal, CS.leftBlinker)
    self._update_signal(self._right_signal, CS.rightBlinker)

  def render(self, rect: rl.Rectangle) -> None:
    if not ui_state.turn_signals:
      return

    x = rect.x + rect.width / 2

    left_x = x - self._config.left_x - self._config.size
    left_y = rect.y + self._config.left_y

    right_x = x + self._config.right_x
    right_y = rect.y + self._config.right_y

    if self._left_signal.active:
      self._left_signal.render(rl.Rectangle(left_x, left_y, self._config.size, self._config.size))

    if self._right_signal.active:
      self._right_signal.render(rl.Rectangle(right_x, right_y, self._config.size, self._config.size))

  @property
  def config(self) -> TurnSignalConfig:
    return self._config

  @config.setter
  def config(self, new_config: TurnSignalConfig) -> None:
    self._config = new_config
