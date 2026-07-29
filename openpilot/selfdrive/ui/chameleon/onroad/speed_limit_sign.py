"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's selfdrive/ui/sunnypilot/onroad/speed_limit.py,
simplified: the number comes straight from liveMapData (this fork has no speed
limit *control* stack, so there is no resolver, no offset badge, no overspeed
warning coloring). US MUTCD rectangle or Vienna circle by the metric setting,
grey when the map has no answer, and an AHEAD box when a different limit is
coming up.
"""
import pyray as rl

from openpilot.common.constants import CV
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

WIDTH_MUTCD = 172.0
WIDTH_VIENNA = 200.0
HEIGHT = 216.0
MARGIN_X, MARGIN_Y = 60.0, 45.0
RED = rl.Color(235, 32, 32, 255)
GREY = rl.Color(145, 155, 149, 255)
WHITE = rl.Color(255, 255, 255, 255)
BLACK = rl.Color(0, 0, 0, 255)
AHEAD_BG = rl.Color(0, 0, 0, 180)


class SpeedLimitSign:
  def __init__(self):
    self._font_bold: rl.Font = gui_app.font(FontWeight.BOLD)
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if not ui_state.speed_limit_display:
      return

    if sm.recv_frame['liveMapData'] < ui_state.started_frame:
      return

    live = sm['liveMapData']
    conversion = CV.MS_TO_KPH if ui_state.is_metric else CV.MS_TO_MPH
    limit = round(live.speedLimit * conversion) if live.speedLimitValid else 0
    limit_str = str(limit) if limit > 0 else "--"

    x = rect.x + MARGIN_X
    y = rect.y + MARGIN_Y
    color = BLACK if live.speedLimitValid else GREY

    if ui_state.is_metric:
      self._draw_vienna(x, y, limit_str, color)
      width = WIDTH_VIENNA
    else:
      self._draw_mutcd(x, y, limit_str, color)
      width = WIDTH_MUTCD

    ahead = round(live.speedLimitAhead * conversion) if live.speedLimitAheadValid else 0
    if ahead > 0 and ahead != limit:
      self._draw_ahead(x, y + HEIGHT + 12, width, ahead, live.speedLimitAheadDistance)

  def _draw_mutcd(self, x: float, y: float, limit_str: str, color: rl.Color) -> None:
    sign = rl.Rectangle(x, y, WIDTH_MUTCD, HEIGHT)
    rl.draw_rectangle_rounded(sign, 0.3, 10, WHITE)
    inner = rl.Rectangle(x + 10, y + 10, WIDTH_MUTCD - 20, HEIGHT - 20)
    rl.draw_rectangle_rounded_lines_ex(inner, 0.25, 10, 4, BLACK)

    for i, word in enumerate(("SPEED", "LIMIT")):
      measure = measure_text_cached(self._font, word, 34, 0)
      rl.draw_text_ex(self._font, word, rl.Vector2(x + WIDTH_MUTCD / 2 - measure.x / 2, y + 26 + i * 36), 34, 0, BLACK)

    measure = measure_text_cached(self._font_bold, limit_str, 88, 0)
    rl.draw_text_ex(self._font_bold, limit_str, rl.Vector2(x + WIDTH_MUTCD / 2 - measure.x / 2, y + 108), 88, 0, color)

  def _draw_vienna(self, x: float, y: float, limit_str: str, color: rl.Color) -> None:
    radius = WIDTH_VIENNA / 2
    center = rl.Vector2(x + radius, y + radius)
    rl.draw_circle_v(center, radius, WHITE)
    rl.draw_ring(center, radius * 0.75, radius, 0, 360, 36, RED)

    size = 85 if len(limit_str) < 3 else 70
    measure = measure_text_cached(self._font_bold, limit_str, size, 0)
    rl.draw_text_ex(self._font_bold, limit_str, rl.Vector2(center.x - measure.x / 2, center.y - measure.y / 2), size, 0, color)

  def _draw_ahead(self, x: float, y: float, width: float, ahead: int, distance_m: float) -> None:
    box = rl.Rectangle(x, y, width, 150)
    rl.draw_rectangle_rounded(box, 0.25, 10, AHEAD_BG)

    if ui_state.is_metric:
      distance = f"{distance_m / 1000:.1f} km" if distance_m >= 1000 else f"{round(distance_m / 10) * 10} m"
    else:
      feet = distance_m * 3.281
      distance = f"{feet / 5280:.1f} mi" if feet >= 900 else f"{round(feet / 50) * 50} ft"

    for i, (text, size) in enumerate((("AHEAD", 30), (str(ahead), 56), (distance, 30))):
      measure = measure_text_cached(self._font, text, size, 0)
      rl.draw_text_ex(self._font, text, rl.Vector2(x + width / 2 - measure.x / 2, y + 10 + i * 46), size, 0, WHITE)
