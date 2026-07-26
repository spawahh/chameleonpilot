"""Cascade — cool glacier palette, chameleonpilot's own theme.

Differs from stock in three ways that are obvious at a glance on the device: teal
instead of green for engaged, a cool white, and a tinted border that reads against
a bright windshield. Override gets its own amber rather than reusing the disengaged
grey, so the three engagement states are distinguishable without reading text.
"""
import pyray as rl

from openpilot.selfdrive.ui.themes.base import HudColors, RoadColors, Theme

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
  road=RoadColors(
    BORDER_DISENGAGED=rl.Color(14, 32, 46, 255),   # deeper blue-grey than stock
    BORDER_OVERRIDE=rl.Color(168, 143, 102, 255),  # muted echo of the amber OVERRIDE
    BORDER_ENGAGED=rl.Color(16, 105, 110, 255),    # deep teal, pairs with ENGAGED
    PATH_THROTTLE_NEAR=rl.Color(13, 220, 205, 102),
    PATH_THROTTLE_MID=rl.Color(90, 235, 215, 89),
    PATH_THROTTLE_FAR=rl.Color(90, 235, 215, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(235, 242, 245, 102),
    PATH_NO_THROTTLE_MID=rl.Color(235, 242, 245, 89),
    PATH_NO_THROTTLE_FAR=rl.Color(235, 242, 245, 0),
    LANE_LINE=rl.Color(240, 246, 250, 255),
    # Safety cues stay stock in every theme: red road edge, amber glow, red chevron.
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
  ),
)
