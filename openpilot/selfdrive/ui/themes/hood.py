"""Hood — high-desert dusk: warm gold over violet shadow.

Engaged is a warm gold (more orange than the pinned WARNING yellow, and drawn
on much larger elements, so the two read differently), override a dusk violet,
disengaged a warm stone grey. Whites lean sand. Safety cues stay stock in
every theme (pinned by test).
"""
import pyray as rl

from openpilot.selfdrive.ui.themes.base import HudColors, OffroadColors, RoadColors, Theme

HOOD = Theme(
  name="hood",
  label="Hood",
  hud=HudColors(
    WHITE=rl.Color(250, 246, 238, 255),
    DISENGAGED=rl.Color(142, 134, 126, 255),
    OVERRIDE=rl.Color(164, 134, 196, 255),
    ENGAGED=rl.Color(234, 168, 66, 255),
    DISENGAGED_BG=rl.Color(18, 13, 10, 153),
    OVERRIDE_BG=rl.Color(164, 134, 196, 204),
    ENGAGED_BG=rl.Color(234, 168, 66, 204),
    GREY=rl.Color(168, 158, 148, 255),
    DARK_GREY=rl.Color(112, 104, 96, 255),
    BLACK_TRANSLUCENT=rl.Color(18, 13, 10, 178),
    WHITE_TRANSLUCENT=rl.Color(242, 234, 222, 200),
    BORDER_TRANSLUCENT=rl.Color(216, 178, 128, 90),
    HEADER_GRADIENT_START=rl.Color(14, 10, 8, 140),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  road=RoadColors(
    BORDER_DISENGAGED=rl.Color(34, 26, 20, 255),   # basalt shadow
    BORDER_OVERRIDE=rl.Color(112, 92, 134, 255),   # muted dusk violet
    BORDER_ENGAGED=rl.Color(140, 96, 30, 255),     # deep amber
    PATH_THROTTLE_NEAR=rl.Color(236, 172, 70, 102),
    PATH_THROTTLE_MID=rl.Color(244, 196, 110, 89),
    PATH_THROTTLE_FAR=rl.Color(244, 196, 110, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(246, 240, 230, 102),
    PATH_NO_THROTTLE_MID=rl.Color(246, 240, 230, 89),
    PATH_NO_THROTTLE_FAR=rl.Color(246, 240, 230, 0),
    LANE_LINE=rl.Color(250, 246, 238, 255),
    # Safety cues stay stock in every theme.
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(234, 168, 66, 255),
    DM_DISENGAGED=rl.Color(142, 134, 126, 255),
    ALERT_NORMAL_BG=rl.Color(20, 15, 11, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
  offroad=OffroadColors(
    WHITE=rl.Color(250, 246, 238, 255),
    WHITE_DIM=rl.Color(232, 222, 206, 85),
    GRAY=rl.Color(92, 84, 76, 255),
    # Status semantics stay stock in every theme (pinned by test).
    GOOD=rl.WHITE,
    WARNING=rl.Color(218, 202, 37, 255),
    DANGER=rl.Color(201, 34, 49, 255),
    METRIC_BORDER=rl.Color(216, 178, 128, 90),
    BUTTON_NORMAL=rl.Color(250, 246, 238, 255),
    BUTTON_PRESSED=rl.Color(216, 178, 128, 166),
    PANEL_BG=rl.Color(36, 28, 22, 255),
    CLOSE_BTN_BG=rl.Color(36, 28, 22, 255),
    CLOSE_BTN_PRESSED=rl.Color(52, 42, 33, 255),
    TEXT_DIM=rl.Color(150, 138, 124, 255),
  ),
  night_hud=HudColors(
    WHITE=rl.Color(212, 204, 190, 255),
    DISENGAGED=rl.Color(108, 100, 92, 255),
    OVERRIDE=rl.Color(128, 104, 154, 255),
    ENGAGED=rl.Color(186, 130, 48, 255),
    DISENGAGED_BG=rl.Color(9, 7, 5, 153),
    OVERRIDE_BG=rl.Color(128, 104, 154, 204),
    ENGAGED_BG=rl.Color(186, 130, 48, 204),
    GREY=rl.Color(134, 126, 116, 255),
    DARK_GREY=rl.Color(90, 84, 76, 255),
    BLACK_TRANSLUCENT=rl.Color(9, 7, 5, 200),
    WHITE_TRANSLUCENT=rl.Color(200, 190, 176, 170),
    BORDER_TRANSLUCENT=rl.Color(168, 138, 96, 70),
    HEADER_GRADIENT_START=rl.Color(6, 4, 3, 160),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  night_road=RoadColors(
    BORDER_DISENGAGED=rl.Color(22, 17, 13, 255),
    BORDER_OVERRIDE=rl.Color(82, 68, 100, 255),
    BORDER_ENGAGED=rl.Color(104, 70, 22, 255),
    PATH_THROTTLE_NEAR=rl.Color(178, 128, 50, 95),
    PATH_THROTTLE_MID=rl.Color(192, 148, 82, 80),
    PATH_THROTTLE_FAR=rl.Color(192, 148, 82, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(196, 188, 176, 95),
    PATH_NO_THROTTLE_MID=rl.Color(196, 188, 176, 80),
    PATH_NO_THROTTLE_FAR=rl.Color(196, 188, 176, 0),
    LANE_LINE=rl.Color(216, 208, 194, 255),
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(186, 130, 48, 255),
    DM_DISENGAGED=rl.Color(112, 104, 96, 255),
    ALERT_NORMAL_BG=rl.Color(12, 9, 7, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
  night_offroad=OffroadColors(
    WHITE=rl.Color(212, 204, 190, 255),
    WHITE_DIM=rl.Color(192, 182, 166, 70),
    GRAY=rl.Color(70, 64, 56, 255),
    GOOD=rl.WHITE,
    WARNING=rl.Color(218, 202, 37, 255),
    DANGER=rl.Color(201, 34, 49, 255),
    METRIC_BORDER=rl.Color(168, 138, 96, 70),
    BUTTON_NORMAL=rl.Color(212, 204, 190, 255),
    BUTTON_PRESSED=rl.Color(168, 138, 96, 140),
    PANEL_BG=rl.Color(24, 18, 14, 255),
    CLOSE_BTN_BG=rl.Color(24, 18, 14, 255),
    CLOSE_BTN_PRESSED=rl.Color(36, 28, 22, 255),
    TEXT_DIM=rl.Color(130, 120, 108, 255),
  ),
)
