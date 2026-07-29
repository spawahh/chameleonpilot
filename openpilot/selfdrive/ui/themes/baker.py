"""Baker — evergreen: deep forest greens under fresh snow.

Engaged is a forest green (deeper and less minty than stock's), override a
warm cedar amber, disengaged a lichen grey. Whites lean snow-neutral with a
hint of green. Safety cues stay stock in every theme (pinned by test).
"""
import pyray as rl

from openpilot.selfdrive.ui.themes.base import HudColors, OffroadColors, RoadColors, Theme

BAKER = Theme(
  name="baker",
  label="Baker",
  hud=HudColors(
    WHITE=rl.Color(244, 250, 245, 255),
    DISENGAGED=rl.Color(124, 136, 128, 255),
    OVERRIDE=rl.Color(206, 150, 92, 255),
    ENGAGED=rl.Color(74, 178, 110, 255),
    DISENGAGED_BG=rl.Color(9, 16, 12, 153),
    OVERRIDE_BG=rl.Color(206, 150, 92, 204),
    ENGAGED_BG=rl.Color(74, 178, 110, 204),
    GREY=rl.Color(150, 164, 154, 255),
    DARK_GREY=rl.Color(96, 110, 100, 255),
    BLACK_TRANSLUCENT=rl.Color(9, 16, 12, 178),
    WHITE_TRANSLUCENT=rl.Color(228, 240, 230, 200),
    BORDER_TRANSLUCENT=rl.Color(150, 200, 165, 90),
    HEADER_GRADIENT_START=rl.Color(7, 14, 10, 140),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  road=RoadColors(
    BORDER_DISENGAGED=rl.Color(16, 30, 22, 255),   # forest-floor shadow
    BORDER_OVERRIDE=rl.Color(158, 122, 82, 255),   # muted cedar
    BORDER_ENGAGED=rl.Color(22, 98, 56, 255),      # deep evergreen
    PATH_THROTTLE_NEAR=rl.Color(56, 190, 108, 102),
    PATH_THROTTLE_MID=rl.Color(110, 210, 140, 89),
    PATH_THROTTLE_FAR=rl.Color(110, 210, 140, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(238, 246, 240, 102),
    PATH_NO_THROTTLE_MID=rl.Color(238, 246, 240, 89),
    PATH_NO_THROTTLE_FAR=rl.Color(238, 246, 240, 0),
    LANE_LINE=rl.Color(244, 250, 245, 255),
    # Safety cues stay stock in every theme.
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(74, 178, 110, 255),
    DM_DISENGAGED=rl.Color(124, 136, 128, 255),
    ALERT_NORMAL_BG=rl.Color(10, 18, 13, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
  offroad=OffroadColors(
    WHITE=rl.Color(244, 250, 245, 255),
    WHITE_DIM=rl.Color(216, 232, 220, 85),
    GRAY=rl.Color(74, 90, 80, 255),
    # Status semantics stay stock in every theme (pinned by test).
    GOOD=rl.WHITE,
    WARNING=rl.Color(218, 202, 37, 255),
    DANGER=rl.Color(201, 34, 49, 255),
    METRIC_BORDER=rl.Color(150, 200, 165, 90),
    BUTTON_NORMAL=rl.Color(244, 250, 245, 255),
    BUTTON_PRESSED=rl.Color(150, 200, 165, 166),
    PANEL_BG=rl.Color(19, 31, 24, 255),
    CLOSE_BTN_BG=rl.Color(19, 31, 24, 255),
    CLOSE_BTN_PRESSED=rl.Color(30, 46, 36, 255),
    TEXT_DIM=rl.Color(120, 140, 128, 255),
  ),
  night_hud=HudColors(
    WHITE=rl.Color(194, 208, 198, 255),
    DISENGAGED=rl.Color(94, 106, 98, 255),
    OVERRIDE=rl.Color(170, 122, 70, 255),
    ENGAGED=rl.Color(56, 138, 86, 255),
    DISENGAGED_BG=rl.Color(4, 9, 6, 153),
    OVERRIDE_BG=rl.Color(170, 122, 70, 204),
    ENGAGED_BG=rl.Color(56, 138, 86, 204),
    GREY=rl.Color(120, 132, 124, 255),
    DARK_GREY=rl.Color(78, 90, 82, 255),
    BLACK_TRANSLUCENT=rl.Color(4, 9, 6, 200),
    WHITE_TRANSLUCENT=rl.Color(184, 200, 188, 170),
    BORDER_TRANSLUCENT=rl.Color(108, 148, 120, 70),
    HEADER_GRADIENT_START=rl.Color(2, 7, 4, 160),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  night_road=RoadColors(
    BORDER_DISENGAGED=rl.Color(9, 18, 13, 255),
    BORDER_OVERRIDE=rl.Color(116, 90, 60, 255),
    BORDER_ENGAGED=rl.Color(14, 68, 38, 255),
    PATH_THROTTLE_NEAR=rl.Color(42, 140, 80, 95),
    PATH_THROTTLE_MID=rl.Color(80, 156, 104, 80),
    PATH_THROTTLE_FAR=rl.Color(80, 156, 104, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(184, 196, 188, 95),
    PATH_NO_THROTTLE_MID=rl.Color(184, 196, 188, 80),
    PATH_NO_THROTTLE_FAR=rl.Color(184, 196, 188, 0),
    LANE_LINE=rl.Color(202, 216, 206, 255),
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(56, 138, 86, 255),
    DM_DISENGAGED=rl.Color(100, 112, 104, 255),
    ALERT_NORMAL_BG=rl.Color(6, 11, 8, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
  night_offroad=OffroadColors(
    WHITE=rl.Color(194, 208, 198, 255),
    WHITE_DIM=rl.Color(174, 192, 180, 70),
    GRAY=rl.Color(56, 70, 62, 255),
    GOOD=rl.WHITE,
    WARNING=rl.Color(218, 202, 37, 255),
    DANGER=rl.Color(201, 34, 49, 255),
    METRIC_BORDER=rl.Color(108, 148, 120, 70),
    BUTTON_NORMAL=rl.Color(194, 208, 198, 255),
    BUTTON_PRESSED=rl.Color(108, 148, 120, 140),
    PANEL_BG=rl.Color(11, 19, 14, 255),
    CLOSE_BTN_BG=rl.Color(11, 19, 14, 255),
    CLOSE_BTN_PRESSED=rl.Color(20, 32, 25, 255),
    TEXT_DIM=rl.Color(98, 118, 106, 255),
  ),
)
