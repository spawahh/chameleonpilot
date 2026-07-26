import unittest

from openpilot.selfdrive.ui import themes
from openpilot.selfdrive.ui.themes.base import HudColors, RoadColors
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
}

# Colors that must be identical in every theme: they are safety cues, not styling.
SAFETY_ROAD_COLORS = ("ROAD_EDGE", "LEAD_GLOW", "LEAD_CHEVRON")


def rgba(color) -> tuple[int, int, int, int]:
  # raylib's named colors (rl.WHITE, rl.BLANK) are plain tuples; rl.Color(...) is a struct
  if isinstance(color, tuple):
    return tuple(color)
  return (color.r, color.g, color.b, color.a)


class TestThemes(unittest.TestCase):
  def tearDown(self):
    themes.set_active(themes.DEFAULT_THEME.name)

  def test_stock_matches_upstream(self):
    for name, expected in UPSTREAM_HUD.items():
      with self.subTest(color=name):
        self.assertEqual(rgba(getattr(STOCK.hud, name)), expected, "stock drifted from upstream")
    for name, expected in UPSTREAM_ROAD.items():
      with self.subTest(color=name):
        self.assertEqual(rgba(getattr(STOCK.road, name)), expected, "stock drifted from upstream")

  def test_upstream_reference_covers_whole_schema(self):
    # a color added to the schema without a recorded upstream value would go unchecked above
    self.assertEqual(set(UPSTREAM_HUD), set(HudColors.__dataclass_fields__))
    self.assertEqual(set(UPSTREAM_ROAD), set(RoadColors.__dataclass_fields__))

  def test_every_theme_is_complete(self):
    for name, theme in themes.THEMES.items():
      with self.subTest(theme=name):
        self.assertEqual(theme.name, name, "registry key must match the theme's own name")
        self.assertTrue(theme.label, "no picker label")
        for color in HudColors.__dataclass_fields__:
          self.assertIsNotNone(rgba(getattr(theme.hud, color)), f"missing {color}")
        for color in RoadColors.__dataclass_fields__:
          self.assertIsNotNone(rgba(getattr(theme.road, color)), f"missing {color}")

  def test_safety_colors_identical_in_every_theme(self):
    for name, theme in themes.THEMES.items():
      for color in SAFETY_ROAD_COLORS:
        with self.subTest(theme=name, color=color):
          self.assertEqual(rgba(getattr(theme.road, color)), UPSTREAM_ROAD[color],
                           "safety cues (road edge, lead markers) must not be themed")

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


if __name__ == "__main__":
  unittest.main()
