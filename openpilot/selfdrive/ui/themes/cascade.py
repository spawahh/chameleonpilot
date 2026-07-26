"""Cascade — cool glacier palette, chameleonpilot's own theme.

Differs from stock in three ways that are obvious at a glance on the device: teal
instead of green for engaged, a cool white, and a tinted border that reads against
a bright windshield. Override gets its own amber rather than reusing the disengaged
grey, so the three engagement states are distinguishable without reading text.
"""
import pyray as rl

from openpilot.selfdrive.ui.themes.base import HudColors, Theme

CASCADE = Theme(
  name="cascade",
  label="Cascade",
  hud=HudColors(
    WHITE=rl.Color(240, 246, 250, 255),
    DISENGAGED=rl.Color(120, 138, 150, 255),
    OVERRIDE=rl.Color(214, 158, 76, 255),
    ENGAGED=rl.Color(86, 199, 190, 255),
    DISENGAGED_BG=rl.Color(8, 14, 20, 153),
    OVERRIDE_BG=rl.Color(214, 158, 76, 204),
    ENGAGED_BG=rl.Color(86, 199, 190, 204),
    GREY=rl.Color(150, 162, 170, 255),
    DARK_GREY=rl.Color(96, 108, 116, 255),
    BLACK_TRANSLUCENT=rl.Color(8, 14, 20, 178),
    WHITE_TRANSLUCENT=rl.Color(222, 235, 242, 200),
    BORDER_TRANSLUCENT=rl.Color(140, 190, 205, 90),
    HEADER_GRADIENT_START=rl.Color(6, 14, 22, 140),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
)
