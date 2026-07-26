"""Stock openpilot colours, verbatim from selfdrive/ui/onroad/hud_renderer.py @ 27122bbd2.

Do not tune these. This is the fallback when a theme fails to load, and the baseline
test_themes.py asserts against to prove a theme change altered nothing upstream.
"""
import pyray as rl

from openpilot.selfdrive.ui.themes.base import HudColors, Theme

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
)
