"""Stock openpilot colours, verbatim from selfdrive/ui/onroad/hud_renderer.py,
model_renderer.py and augmented_road_view.py @ 27122bbd2.

Do not tune these. This is the fallback when a theme fails to load, and the baseline
test_themes.py asserts against to prove a theme change altered nothing upstream.
"""
import pyray as rl

from openpilot.selfdrive.ui.themes.base import HudColors, RoadColors, Theme

STOCK = Theme(
  name="stock",
  label="Stock",
  hud=HudColors(
    WHITE=rl.WHITE,
    DISENGAGED=rl.Color(145, 155, 149, 255),
    OVERRIDE=rl.Color(145, 155, 149, 255),
    ENGAGED=rl.Color(128, 216, 166, 255),
    DISENGAGED_BG=rl.Color(0, 0, 0, 153),
    OVERRIDE_BG=rl.Color(145, 155, 149, 204),
    ENGAGED_BG=rl.Color(128, 216, 166, 204),
    GREY=rl.Color(166, 166, 166, 255),
    DARK_GREY=rl.Color(114, 114, 114, 255),
    BLACK_TRANSLUCENT=rl.Color(0, 0, 0, 166),
    WHITE_TRANSLUCENT=rl.Color(255, 255, 255, 200),
    BORDER_TRANSLUCENT=rl.Color(255, 255, 255, 75),
    HEADER_GRADIENT_START=rl.Color(0, 0, 0, 114),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  road=RoadColors(
    BORDER_DISENGAGED=rl.Color(0x12, 0x28, 0x39, 0xFF),
    BORDER_OVERRIDE=rl.Color(0x89, 0x92, 0x8D, 0xFF),
    BORDER_ENGAGED=rl.Color(0x16, 0x7F, 0x40, 0xFF),
    PATH_THROTTLE_NEAR=rl.Color(13, 248, 122, 102),
    PATH_THROTTLE_MID=rl.Color(114, 255, 92, 89),
    PATH_THROTTLE_FAR=rl.Color(114, 255, 92, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(242, 242, 242, 102),
    PATH_NO_THROTTLE_MID=rl.Color(242, 242, 242, 89),
    PATH_NO_THROTTLE_FAR=rl.Color(242, 242, 242, 0),
    LANE_LINE=rl.Color(255, 255, 255, 255),
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
  ),
)
