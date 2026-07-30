"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's selfdrive/ui/sunnypilot/onroad/road_name.py:
a translucent pill at the top of the onroad screen with the current road's
name from liveMapData.
"""
import pyray as rl

from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

PILL_HEIGHT = 60.0
TEXT_SIZE = 42
BG = rl.Color(0, 0, 0, 120)
TEXT = rl.Color(255, 255, 255, 200)


class RoadName:
  def __init__(self):
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if not ui_state.road_name_display:
      return

    if sm.recv_frame['liveMapData'] < ui_state.started_frame:
      return

    name = sm['liveMapData'].roadName
    if not name:
      return

    measure = measure_text_cached(self._font, name, TEXT_SIZE, 0)
    width = max(200.0, min(measure.x + 40.0, rect.width - 40.0))
    pill = rl.Rectangle(rect.x + rect.width / 2 - width / 2, rect.y + 4.0, width, PILL_HEIGHT)
    rl.draw_rectangle_rounded(pill, 0.5, 10, BG)
    rl.draw_text_ex(self._font, name, rl.Vector2(pill.x + width / 2 - measure.x / 2, pill.y + (PILL_HEIGHT - measure.y) / 2), TEXT_SIZE, 0, TEXT)
