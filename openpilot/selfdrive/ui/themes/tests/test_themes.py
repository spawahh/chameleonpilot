import unittest

from openpilot.selfdrive.ui import themes
from openpilot.selfdrive.ui.themes.base import HudColors, OffroadColors, RoadColors
from openpilot.selfdrive.ui.themes.stock import STOCK

# Upstream values, transcribed from selfdrive/ui/onroad/hud_renderer.py @ 27122bbd2.
# If a rebase changes upstream's colors this test must fail: it is the only thing proving
# the stock path still renders exactly like comma's.
UPSTREAM_HUD = {
  "WHITE": (255, 255, 255, 255),
  "DISENGAGED": (145, 155, 149, 255),
  "OVERRIDE": (145, 155, 149, 255),
  "ENGAGED": (128, 216, 166, 255),
  "DISENGAGED_BG": (0, 0, 0, 153),
  "OVERRIDE_BG": (145, 155, 149, 204),
  "ENGAGED_BG": (128, 216, 166, 204),
  "GREY": (166, 166, 166, 255),
  "DARK_GREY": (114, 114, 114, 255),
  "BLACK_TRANSLUCENT": (0, 0, 0, 166),
  "WHITE_TRANSLUCENT": (255, 255, 255, 200),
  "BORDER_TRANSLUCENT": (255, 255, 255, 75),
  "HEADER_GRADIENT_START": (0, 0, 0, 114),
  "HEADER_GRADIENT_END": (0, 0, 0, 0),
}

# Same idea, transcribed from augmented_road_view.py (BORDER_COLORS) and
# model_renderer.py (THROTTLE/NO_THROTTLE_COLORS + inline literals) @ 27122bbd2.
UPSTREAM_ROAD = {
  "BORDER_DISENGAGED": (0x12, 0x28, 0x39, 0xFF),
  "BORDER_OVERRIDE": (0x89, 0x92, 0x8D, 0xFF),
  "BORDER_ENGAGED": (0x16, 0x7F, 0x40, 0xFF),
  "PATH_THROTTLE_NEAR": (13, 248, 122, 102),
  "PATH_THROTTLE_MID": (114, 255, 92, 89),
  "PATH_THROTTLE_FAR": (114, 255, 92, 0),
  "PATH_NO_THROTTLE_NEAR": (242, 242, 242, 102),
  "PATH_NO_THROTTLE_MID": (242, 242, 242, 89),
  "PATH_NO_THROTTLE_FAR": (242, 242, 242, 0),
  "LANE_LINE": (255, 255, 255, 255),
  "ROAD_EDGE": (255, 0, 0, 255),
  "LEAD_GLOW": (218, 202, 37, 255),
  "LEAD_CHEVRON": (201, 34, 49, 255),
  "DM_ENGAGED": (26, 242, 66, 255),
  "DM_DISENGAGED": (139, 139, 139, 255),
  "ALERT_NORMAL_BG": (0x15, 0x15, 0x15, 0xF1),
  "ALERT_PROMPT_BG": (0xDA, 0x6F, 0x25, 0xF1),
  "ALERT_CRITICAL_BG": (0xC9, 0x22, 0x31, 0xF1),
}

# Upstream values, transcribed from selfdrive/ui/layouts/sidebar.py (Colors) and
# layouts/settings/settings.py (module constants) @ 27122bbd2.
UPSTREAM_OFFROAD = {
  "WHITE": (255, 255, 255, 255),
  "WHITE_DIM": (255, 255, 255, 85),
  "GRAY": (84, 84, 84, 255),
  "GOOD": (255, 255, 255, 255),
  "WARNING": (218, 202, 37, 255),
  "DANGER": (201, 34, 49, 255),
  "METRIC_BORDER": (255, 255, 255, 85),
  "BUTTON_NORMAL": (255, 255, 255, 255),
  "BUTTON_PRESSED": (255, 255, 255, 166),
  "PANEL_BG": (41, 41, 41, 255),
  "CLOSE_BTN_BG": (41, 41, 41, 255),
  "CLOSE_BTN_PRESSED": (59, 59, 59, 255),
  "TEXT_DIM": (128, 128, 128, 255),
}

# Colors that must be identical in every theme: they are safety cues, not styling.
SAFETY_ROAD_COLORS = ("ROAD_EDGE", "LEAD_GLOW", "LEAD_CHEVRON", "ALERT_PROMPT_BG", "ALERT_CRITICAL_BG")

# Sidebar metric status semantics: white/amber/red mean good/warning/danger. Themable
# chrome around them is fine, but repainting these would change what they communicate.
STATUS_OFFROAD_COLORS = ("GOOD", "WARNING", "DANGER")


def rgba(color) -> tuple[int, int, int, int]:
  # raylib's named colors (rl.WHITE, rl.BLANK) are plain tuples; rl.Color(...) is a struct
  if isinstance(color, tuple):
    return tuple(color)
  return (color.r, color.g, color.b, color.a)


class TestThemes(unittest.TestCase):
  def tearDown(self):
    themes.set_active(themes.DEFAULT_THEME.name)
    themes.set_night_mode("auto")
    themes.night.is_night = False

  def test_stock_matches_upstream(self):
    for name, expected in UPSTREAM_HUD.items():
      with self.subTest(color=name):
        self.assertEqual(rgba(getattr(STOCK.hud, name)), expected, "stock drifted from upstream")
    for name, expected in UPSTREAM_ROAD.items():
      with self.subTest(color=name):
        self.assertEqual(rgba(getattr(STOCK.road, name)), expected, "stock drifted from upstream")
    for name, expected in UPSTREAM_OFFROAD.items():
      with self.subTest(color=name):
        self.assertEqual(rgba(getattr(STOCK.offroad, name)), expected, "stock drifted from upstream")

  def test_upstream_reference_covers_whole_schema(self):
    # a color added to the schema without a recorded upstream value would go unchecked above
    self.assertEqual(set(UPSTREAM_HUD), set(HudColors.__dataclass_fields__))
    self.assertEqual(set(UPSTREAM_ROAD), set(RoadColors.__dataclass_fields__))
    self.assertEqual(set(UPSTREAM_OFFROAD), set(OffroadColors.__dataclass_fields__))

  def test_every_theme_is_complete(self):
    for name, theme in themes.THEMES.items():
      with self.subTest(theme=name):
        self.assertEqual(theme.name, name, "registry key must match the theme's own name")
        self.assertTrue(theme.label, "no picker label")
        for color in HudColors.__dataclass_fields__:
          self.assertIsNotNone(rgba(getattr(theme.hud, color)), f"missing {color}")
        for color in RoadColors.__dataclass_fields__:
          self.assertIsNotNone(rgba(getattr(theme.road, color)), f"missing {color}")
        for color in OffroadColors.__dataclass_fields__:
          self.assertIsNotNone(rgba(getattr(theme.offroad, color)), f"missing {color}")

  def test_safety_colors_identical_in_every_theme(self):
    for name, theme in themes.THEMES.items():
      palettes = [("road", theme.road)] + ([("night_road", theme.night_road)] if theme.night_road else [])
      for palette_name, palette in palettes:
        for color in SAFETY_ROAD_COLORS:
          with self.subTest(theme=name, palette=palette_name, color=color):
            self.assertEqual(rgba(getattr(palette, color)), UPSTREAM_ROAD[color],
                             "safety cues (road edge, lead markers, alert prompt/critical) must not be themed")

  def test_status_colors_identical_in_every_theme(self):
    for name, theme in themes.THEMES.items():
      palettes = [("offroad", theme.offroad)] + ([("night_offroad", theme.night_offroad)] if theme.night_offroad else [])
      for palette_name, palette in palettes:
        for color in STATUS_OFFROAD_COLORS:
          with self.subTest(theme=name, palette=palette_name, color=color):
            self.assertEqual(rgba(getattr(palette, color)), UPSTREAM_OFFROAD[color],
                             "sidebar status colors (good/warning/danger) must not be themed")

  def test_offroad_proxy_follows_active_theme(self):
    themes.set_active("stock")
    self.assertEqual(rgba(themes.OFFROAD_COLORS.PANEL_BG), UPSTREAM_OFFROAD["PANEL_BG"])

    themes.set_active("cascade")
    self.assertNotEqual(rgba(themes.OFFROAD_COLORS.PANEL_BG), UPSTREAM_OFFROAD["PANEL_BG"])

    themes.set_active("stock")
    self.assertEqual(rgba(themes.OFFROAD_COLORS.PANEL_BG), UPSTREAM_OFFROAD["PANEL_BG"])

  def test_night_palettes_are_all_or_nothing(self):
    # half a night variant would render a mixed day/night screen
    for name, theme in themes.THEMES.items():
      with self.subTest(theme=name):
        self.assertEqual(theme.night_hud is None, theme.night_road is None,
                         "a theme must define both night palettes or neither")
        self.assertEqual(theme.night_hud is None, theme.night_offroad is None,
                         "a theme must define all three night palettes or none")

  def test_night_proxy_switches_palette(self):
    themes.set_active("cascade")
    day = rgba(themes.HUD_COLORS.ENGAGED)
    themes.set_night_mode("on")
    self.assertNotEqual(rgba(themes.HUD_COLORS.ENGAGED), day)
    self.assertNotEqual(rgba(themes.ROAD_COLORS.BORDER_ENGAGED), UPSTREAM_ROAD["BORDER_ENGAGED"])
    themes.set_night_mode("off")
    self.assertEqual(rgba(themes.HUD_COLORS.ENGAGED), day)

  def test_stock_is_unaffected_by_night(self):
    # stock has no night palette: it must render bit-identical to upstream around the clock
    themes.set_active("stock")
    themes.set_night_mode("on")
    self.assertEqual(rgba(themes.HUD_COLORS.ENGAGED), UPSTREAM_HUD["ENGAGED"])
    self.assertEqual(rgba(themes.ROAD_COLORS.BORDER_ENGAGED), UPSTREAM_ROAD["BORDER_ENGAGED"])

  def test_auto_mode_needs_dwell_and_hysteresis(self):
    r = themes._NightResolver()
    r.set_mode("auto")
    # dark reading alone must not flip it: dwell first
    self.assertFalse(r.tick(10.0, now=0.0))
    self.assertFalse(r.tick(10.0, now=themes.NIGHT_DWELL_S - 0.1))
    self.assertTrue(r.tick(10.0, now=themes.NIGHT_DWELL_S))
    # readings inside the hysteresis band (enter < 30 < 40 < 45 exit) hold night
    self.assertTrue(r.tick(40.0, now=100.0))
    self.assertTrue(r.tick(40.0, now=200.0))
    # a brief bright flash (oncoming headlights) resets, but doesn't flip
    self.assertTrue(r.tick(90.0, now=300.0))
    self.assertTrue(r.tick(10.0, now=301.0))  # dark again: pending day cancelled
    self.assertTrue(r.tick(90.0, now=400.0))
    self.assertFalse(r.tick(90.0, now=400.0 + themes.NIGHT_DWELL_S))

  def test_auto_mode_holds_state_without_camera(self):
    r = themes._NightResolver()
    r.set_mode("auto")
    r.is_night = True
    self.assertTrue(r.tick(-1, now=0.0))
    self.assertTrue(r.tick(-1, now=1000.0))

  def test_manual_mode_ignores_ambient(self):
    r = themes._NightResolver()
    r.set_mode("off")
    self.assertFalse(r.tick(0.0, now=0.0))
    self.assertFalse(r.tick(0.0, now=1000.0))
    r.set_mode("on")
    self.assertTrue(r.tick(100.0, now=2000.0))

  def test_unknown_night_mode_falls_back_to_auto(self):
    r = themes._NightResolver()
    r.set_mode("dusk-ish")
    self.assertEqual(r.mode, "auto")

  def test_unknown_theme_falls_back_to_stock(self):
    themes.set_active("cascade")
    self.assertIs(themes.set_active("does-not-exist"), STOCK)
    self.assertIs(themes.active(), STOCK)

  def test_proxy_follows_active_theme(self):
    themes.set_active("stock")
    self.assertEqual(rgba(themes.HUD_COLORS.ENGAGED), UPSTREAM_HUD["ENGAGED"])

    themes.set_active("cascade")
    self.assertNotEqual(rgba(themes.HUD_COLORS.ENGAGED), UPSTREAM_HUD["ENGAGED"])

    themes.set_active("stock")
    self.assertEqual(rgba(themes.HUD_COLORS.ENGAGED), UPSTREAM_HUD["ENGAGED"])

  def test_road_proxy_follows_active_theme(self):
    themes.set_active("stock")
    self.assertEqual(rgba(themes.ROAD_COLORS.BORDER_ENGAGED), UPSTREAM_ROAD["BORDER_ENGAGED"])

    themes.set_active("cascade")
    self.assertNotEqual(rgba(themes.ROAD_COLORS.BORDER_ENGAGED), UPSTREAM_ROAD["BORDER_ENGAGED"])

    themes.set_active("stock")
    self.assertEqual(rgba(themes.ROAD_COLORS.BORDER_ENGAGED), UPSTREAM_ROAD["BORDER_ENGAGED"])

  def test_with_alpha_keeps_themed_rgb(self):
    themes.set_active("stock")
    c = themes.with_alpha(themes.ROAD_COLORS.LANE_LINE, 77)
    self.assertEqual(rgba(c), (255, 255, 255, 77))

  def test_proxy_rejects_unknown_color(self):
    with self.assertRaises(AttributeError):
      _ = themes.HUD_COLORS.NOT_A_COLOR
    with self.assertRaises(AttributeError):
      _ = themes.ROAD_COLORS.NOT_A_COLOR
    with self.assertRaises(AttributeError):
      _ = themes.OFFROAD_COLORS.NOT_A_COLOR


if __name__ == "__main__":
  unittest.main()
