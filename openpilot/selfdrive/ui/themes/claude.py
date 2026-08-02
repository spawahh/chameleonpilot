"""claudePilot — warm paper and clay: cream whites over a warm ink cabin.

The one theme here not named after a Cascade volcano, and the only warm-neutral
one: cream instead of a cool white, and warm ink instead of blue-grey for every
background and panel.

Role assignment is deliberate. Clay is the accent, but it lands on OVERRIDE, not
ENGAGED: the pinned ALERT_PROMPT_BG is (218, 111, 37), close enough in hue to
clay that clay-coloured engaged chrome would read like a prompt alert. Override
is an attention state, so the accent belongs there instead. ENGAGED is a warm
jade — still unmistakably "go", but warmed to sit with the clay rather than
fight it. Disengaged is a warm stone grey, so the three engagement states are
distinguishable without reading text.

Safety cues stay stock in every theme (pinned by test).
"""
import pyray as rl

from openpilot.selfdrive.ui.themes.base import HudColors, OffroadColors, RoadColors, Theme

CLAUDE = Theme(
  name="claude",
  label="claudePilot",
  hud=HudColors(
    WHITE=rl.Color(245, 243, 236, 255),
    DISENGAGED=rl.Color(150, 145, 133, 255),
    OVERRIDE=rl.Color(217, 119, 87, 255),
    ENGAGED=rl.Color(94, 178, 138, 255),
    DISENGAGED_BG=rl.Color(24, 23, 21, 153),
    OVERRIDE_BG=rl.Color(217, 119, 87, 204),
    ENGAGED_BG=rl.Color(94, 178, 138, 204),
    GREY=rl.Color(163, 157, 145, 255),
    DARK_GREY=rl.Color(110, 105, 96, 255),
    BLACK_TRANSLUCENT=rl.Color(24, 23, 21, 178),
    WHITE_TRANSLUCENT=rl.Color(240, 238, 230, 200),
    BORDER_TRANSLUCENT=rl.Color(217, 160, 130, 85),  # clay-tinted, reads against a bright windshield
    HEADER_GRADIENT_START=rl.Color(20, 20, 19, 130),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  road=RoadColors(
    BORDER_DISENGAGED=rl.Color(38, 33, 29, 255),   # warm ink instead of stock's blue-grey
    BORDER_OVERRIDE=rl.Color(168, 104, 78, 255),   # muted echo of the clay OVERRIDE
    BORDER_ENGAGED=rl.Color(28, 110, 84, 255),     # deep jade, pairs with ENGAGED
    PATH_THROTTLE_NEAR=rl.Color(46, 200, 148, 102),
    PATH_THROTTLE_MID=rl.Color(110, 220, 170, 89),
    PATH_THROTTLE_FAR=rl.Color(110, 220, 170, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(240, 238, 230, 102),
    PATH_NO_THROTTLE_MID=rl.Color(240, 238, 230, 89),
    PATH_NO_THROTTLE_FAR=rl.Color(240, 238, 230, 0),
    LANE_LINE=rl.Color(245, 243, 236, 255),
    # Safety cues stay stock in every theme: red road edge, amber glow, red chevron,
    # and the prompt/critical alert backgrounds.
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(94, 178, 138, 255),     # jade, pairs with ENGAGED
    DM_DISENGAGED=rl.Color(150, 145, 133, 255),
    ALERT_NORMAL_BG=rl.Color(26, 25, 23, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
  offroad=OffroadColors(
    WHITE=rl.Color(245, 243, 236, 255),
    WHITE_DIM=rl.Color(240, 238, 230, 85),
    GRAY=rl.Color(88, 83, 76, 255),
    # Status semantics stay stock in every theme (pinned by test).
    GOOD=rl.WHITE,
    WARNING=rl.Color(218, 202, 37, 255),
    DANGER=rl.Color(201, 34, 49, 255),
    METRIC_BORDER=rl.Color(217, 160, 130, 85),  # matches the HUD's tinted border
    BUTTON_NORMAL=rl.Color(245, 243, 236, 255),
    BUTTON_PRESSED=rl.Color(217, 160, 130, 166),
    PANEL_BG=rl.Color(34, 32, 29, 255),          # warm charcoal instead of neutral 41s
    CLOSE_BTN_BG=rl.Color(34, 32, 29, 255),
    CLOSE_BTN_PRESSED=rl.Color(50, 47, 43, 255),
    TEXT_DIM=rl.Color(140, 133, 122, 255),
  ),
  # Night: same hues, lower luminance and saturation, so nothing glares in a dark
  # cabin but every state stays recognizable. Safety cues remain stock (tested).
  night_hud=HudColors(
    WHITE=rl.Color(198, 193, 182, 255),
    DISENGAGED=rl.Color(112, 107, 98, 255),
    OVERRIDE=rl.Color(176, 96, 70, 255),
    ENGAGED=rl.Color(70, 140, 110, 255),
    DISENGAGED_BG=rl.Color(14, 13, 12, 153),
    OVERRIDE_BG=rl.Color(176, 96, 70, 204),
    ENGAGED_BG=rl.Color(70, 140, 110, 204),
    GREY=rl.Color(128, 122, 112, 255),
    DARK_GREY=rl.Color(84, 80, 73, 255),
    BLACK_TRANSLUCENT=rl.Color(14, 13, 12, 200),
    WHITE_TRANSLUCENT=rl.Color(186, 181, 170, 170),
    BORDER_TRANSLUCENT=rl.Color(160, 116, 94, 70),
    HEADER_GRADIENT_START=rl.Color(10, 10, 9, 160),
    HEADER_GRADIENT_END=rl.BLANK,
  ),
  night_road=RoadColors(
    BORDER_DISENGAGED=rl.Color(24, 21, 18, 255),
    BORDER_OVERRIDE=rl.Color(122, 74, 56, 255),
    BORDER_ENGAGED=rl.Color(20, 78, 60, 255),
    PATH_THROTTLE_NEAR=rl.Color(34, 146, 110, 95),
    PATH_THROTTLE_MID=rl.Color(80, 160, 126, 80),
    PATH_THROTTLE_FAR=rl.Color(80, 160, 126, 0),
    PATH_NO_THROTTLE_NEAR=rl.Color(186, 182, 172, 95),
    PATH_NO_THROTTLE_MID=rl.Color(186, 182, 172, 80),
    PATH_NO_THROTTLE_FAR=rl.Color(186, 182, 172, 0),
    LANE_LINE=rl.Color(206, 201, 190, 255),
    ROAD_EDGE=rl.Color(255, 0, 0, 255),
    LEAD_GLOW=rl.Color(218, 202, 37, 255),
    LEAD_CHEVRON=rl.Color(201, 34, 49, 255),
    DM_ENGAGED=rl.Color(70, 140, 110, 255),
    DM_DISENGAGED=rl.Color(104, 99, 91, 255),
    ALERT_NORMAL_BG=rl.Color(16, 15, 14, 0xF1),
    ALERT_PROMPT_BG=rl.Color(0xDA, 0x6F, 0x25, 0xF1),
    ALERT_CRITICAL_BG=rl.Color(0xC9, 0x22, 0x31, 0xF1),
  ),
  night_offroad=OffroadColors(
    WHITE=rl.Color(198, 193, 182, 255),
    WHITE_DIM=rl.Color(180, 175, 165, 70),
    GRAY=rl.Color(66, 62, 57, 255),
    GOOD=rl.WHITE,
    WARNING=rl.Color(218, 202, 37, 255),
    DANGER=rl.Color(201, 34, 49, 255),
    METRIC_BORDER=rl.Color(160, 116, 94, 70),
    BUTTON_NORMAL=rl.Color(198, 193, 182, 255),
    BUTTON_PRESSED=rl.Color(160, 116, 94, 140),
    PANEL_BG=rl.Color(20, 19, 17, 255),
    CLOSE_BTN_BG=rl.Color(20, 19, 17, 255),
    CLOSE_BTN_PRESSED=rl.Color(32, 30, 27, 255),
    TEXT_DIM=rl.Color(112, 106, 97, 255),
  ),
)
