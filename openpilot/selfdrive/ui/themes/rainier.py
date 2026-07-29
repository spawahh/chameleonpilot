"""Rainier — alpine dawn: glacier blues with an alpenglow rose.

Engaged is a clear glacier blue, override the rose a sunrise puts on the
mountain, disengaged a cold shadow grey. Whites lean icy. Safety cues stay
stock in every theme (pinned by test).
"""
import pyray as rl

from openpilot.selfdrive.ui.themes.base import HudColors, OffroadColors, RoadColors, Theme

RAINIER = Theme(
  name="rainier",
  label="Rainier",
  hud=HudColors(
    WHITE=rl.Color(243, 247, 253, 255),
    DISENGAGED=rl.Color(122, 134, 150, 255),
    OVERRIDE=rl.Color(224, 138, 128, 255),
    ENGAGED=rl.Color(96, 168, 228, 255),
    DISENGAGED_BG=rl.Color(10, 14, 22, 153),
    OVERRIDE_BG=rl.Color(224, 138, 128, 204),
    ENGAGED_BG=rl.Color(96, 168, 228, 204),
    GREY=rl.Color(152, 162, 176, 255),
    DARK_GREY=rl.Color(98, 108, 122, 255),
    BLACK_TRANSLUCENT=rl.Color(10, 14, 22, 178),
    WHITE_TRANSLUCENT=rl.Color(226, 234, 246, 200),
    BORDER_TRANSLUCENT=rl.Color(150, 186, 220, 90),
    HEADER_GRADIENT_START=rl.Color(8, 12, 24, 140),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  road=RoadColors(
    BORDER_DISENGAGED=rl.Color(16, 24, 42, 255),   # night-sky indigo
    BORDER_OVERRIDE=rl.Color(172, 118, 110, 255),  # muted alpenglow
    BORDER_ENGAGED=rl.Color(24, 84, 132, 255),     # deep glacier blue
    PATH_THROTTLE_NEAR=rl.Color(70, 170, 235, 102),
    PATH_THROTTLE_MID=rl.Color(120, 195, 245, 89),
    PATH_THROTTLE_FAR=rl.Color(120, 195, 245, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(238, 244, 250, 102),
    PATH_NO_THROTTLE_MID=rl.Color(238, 244, 250, 89),
    PATH_NO_THROTTLE_FAR=rl.Color(238, 244, 250, 0),
    LANE_LINE=rl.Color(243, 247, 253, 255),
    # Safety cues stay stock in every theme.
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(96, 168, 228, 255),
    DM_DISENGAGED=rl.Color(122, 134, 150, 255),
    ALERT_NORMAL_BG=rl.Color(11, 16, 26, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
  offroad=OffroadColors(
    WHITE=rl.Color(243, 247, 253, 255),
    WHITE_DIM=rl.Color(214, 226, 242, 85),
    GRAY=rl.Color(76, 86, 102, 255),
    # Status semantics stay stock in every theme (pinned by test).
    GOOD=rl.WHITE,
    WARNING=rl.Color(218, 202, 37, 255),
    DANGER=rl.Color(201, 34, 49, 255),
    METRIC_BORDER=rl.Color(150, 186, 220, 90),
    BUTTON_NORMAL=rl.Color(243, 247, 253, 255),
    BUTTON_PRESSED=rl.Color(150, 186, 220, 166),
    PANEL_BG=rl.Color(20, 28, 44, 255),
    CLOSE_BTN_BG=rl.Color(20, 28, 44, 255),
    CLOSE_BTN_PRESSED=rl.Color(32, 42, 62, 255),
    TEXT_DIM=rl.Color(124, 138, 158, 255),
  ),
  night_hud=HudColors(
    WHITE=rl.Color(192, 202, 216, 255),
    DISENGAGED=rl.Color(94, 104, 118, 255),
    OVERRIDE=rl.Color(184, 110, 102, 255),
    ENGAGED=rl.Color(70, 128, 178, 255),
    DISENGAGED_BG=rl.Color(5, 8, 14, 153),
    OVERRIDE_BG=rl.Color(184, 110, 102, 204),
    ENGAGED_BG=rl.Color(70, 128, 178, 204),
    GREY=rl.Color(122, 130, 142, 255),
    DARK_GREY=rl.Color(80, 88, 100, 255),
    BLACK_TRANSLUCENT=rl.Color(5, 8, 14, 200),
    WHITE_TRANSLUCENT=rl.Color(182, 194, 210, 170),
    BORDER_TRANSLUCENT=rl.Color(108, 138, 166, 70),
    HEADER_GRADIENT_START=rl.Color(3, 6, 12, 160),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  night_road=RoadColors(
    BORDER_DISENGAGED=rl.Color(10, 16, 28, 255),
    BORDER_OVERRIDE=rl.Color(124, 88, 82, 255),
    BORDER_ENGAGED=rl.Color(16, 58, 92, 255),
    PATH_THROTTLE_NEAR=rl.Color(52, 126, 176, 95),
    PATH_THROTTLE_MID=rl.Color(90, 148, 188, 80),
    PATH_THROTTLE_FAR=rl.Color(90, 148, 188, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(182, 192, 204, 95),
    PATH_NO_THROTTLE_MID=rl.Color(182, 192, 204, 80),
    PATH_NO_THROTTLE_FAR=rl.Color(182, 192, 204, 0),
    LANE_LINE=rl.Color(202, 212, 226, 255),
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(70, 128, 178, 255),
    DM_DISENGAGED=rl.Color(100, 110, 124, 255),
    ALERT_NORMAL_BG=rl.Color(7, 10, 16, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
  night_offroad=OffroadColors(
    WHITE=rl.Color(192, 202, 216, 255),
    WHITE_DIM=rl.Color(172, 186, 204, 70),
    GRAY=rl.Color(58, 68, 82, 255),
    GOOD=rl.WHITE,
    WARNING=rl.Color(218, 202, 37, 255),
    DANGER=rl.Color(201, 34, 49, 255),
    METRIC_BORDER=rl.Color(108, 138, 166, 70),
    BUTTON_NORMAL=rl.Color(192, 202, 216, 255),
    BUTTON_PRESSED=rl.Color(108, 138, 166, 140),
    PANEL_BG=rl.Color(12, 18, 30, 255),
    CLOSE_BTN_BG=rl.Color(12, 18, 30, 255),
    CLOSE_BTN_PRESSED=rl.Color(22, 30, 46, 255),
    TEXT_DIM=rl.Color(100, 114, 132, 255),
  ),
)
