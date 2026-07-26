import unittest

from openpilot.selfdrive.ui import themes
from openpilot.selfdrive.ui.themes.base import HudColors
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

  def test_upstream_reference_covers_whole_schema(self):
    # a color added to the schema without a recorded upstream value would go unchecked above
    self.assertEqual(set(UPSTREAM_HUD), set(HudColors.__dataclass_fields__))

  def test_every_theme_is_complete(self):
    for name, theme in themes.THEMES.items():
      with self.subTest(theme=name):
        self.assertEqual(theme.name, name, "registry key must match the theme's own name")
        self.assertTrue(theme.label, "no picker label")
        for color in HudColors.__dataclass_fields__:
          self.assertIsNotNone(rgba(getattr(theme.hud, color)), f"missing {color}")

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

  def test_proxy_rejects_unknown_color(self):
    with self.assertRaises(AttributeError):
      _ = themes.HUD_COLORS.NOT_A_COLOR


if __name__ == "__main__":
  unittest.main()
