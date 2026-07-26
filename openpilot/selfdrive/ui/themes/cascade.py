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
    # Safety cues stay stock in every theme: red road edge, amber glow, red chevron,
    # and the prompt/critical alert backgrounds.
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(86, 199, 190, 255),     # teal, pairs with ENGAGED
    DM_DISENGAGED=rl.Color(120, 138, 150, 255),
    ALERT_NORMAL_BG=rl.Color(10, 16, 21, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
  # Night: same hues, lower luminance and saturation, so nothing glares in a dark
  # cabin but every state stays recognisable. Safety cues remain stock (tested).
  night_hud=HudColors(
    WHITE=rl.Color(190, 202, 212, 255),
    DISENGAGED=rl.Color(92, 106, 116, 255),
    OVERRIDE=rl.Color(178, 130, 64, 255),
    ENGAGED=rl.Color(64, 156, 150, 255),
    DISENGAGED_BG=rl.Color(4, 8, 12, 153),
    OVERRIDE_BG=rl.Color(178, 130, 64, 204),
    ENGAGED_BG=rl.Color(64, 156, 150, 204),
    GREY=rl.Color(120, 130, 138, 255),
    DARK_GREY=rl.Color(78, 88, 96, 255),
    BLACK_TRANSLUCENT=rl.Color(4, 8, 12, 200),
    WHITE_TRANSLUCENT=rl.Color(180, 195, 205, 170),
    BORDER_TRANSLUCENT=rl.Color(100, 140, 155, 70),
    HEADER_GRADIENT_START=rl.Color(2, 6, 10, 160),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  night_road=RoadColors(
    BORDER_DISENGAGED=rl.Color(8, 20, 30, 255),
    BORDER_OVERRIDE=rl.Color(120, 102, 72, 255),
    BORDER_ENGAGED=rl.Color(10, 72, 76, 255),
    PATH_THROTTLE_NEAR=rl.Color(10, 160, 150, 95),
    PATH_THROTTLE_MID=rl.Color(66, 172, 158, 80),
    PATH_THROTTLE_FAR=rl.Color(66, 172, 158, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(180, 190, 196, 95),
    PATH_NO_THROTTLE_MID=rl.Color(180, 190, 196, 80),
    PATH_NO_THROTTLE_FAR=rl.Color(180, 190, 196, 0),
    LANE_LINE=rl.Color(200, 212, 220, 255),
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(64, 156, 150, 255),
    DM_DISENGAGED=rl.Color(100, 112, 122, 255),
    ALERT_NORMAL_BG=rl.Color(6, 10, 14, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
)
