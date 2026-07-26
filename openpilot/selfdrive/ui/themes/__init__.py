"""HUD theme registry.

Renderers read colors through the proxies exported here instead of module-level
constants, so adding or switching a theme never touches a renderer. The UI is a single
process, so a switch from settings takes effect on the next frame with no restart.
"""
import pyray as rl

from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.ui.themes.base import Theme
from openpilot.selfdrive.ui.themes.cascade import CASCADE
from openpilot.selfdrive.ui.themes.stock import STOCK

THEME_PARAM = "HudTheme"
DEFAULT_THEME = STOCK

THEMES: dict[str, Theme] = {t.name: t for t in (STOCK, CASCADE)}

_active: Theme = DEFAULT_THEME


def active() -> Theme:
  return _active


def set_active(name: str) -> Theme:
  global _active
  theme = THEMES.get(name)
  if theme is None:
    # a bad param must never stop the UI from drawing
    cloudlog.warning(f"unknown {THEME_PARAM} {name!r}, falling back to {DEFAULT_THEME.name}")
    theme = DEFAULT_THEME
  _active = theme
  return _active


def load_from_params(params: Params | None = None) -> Theme:
  p = params if params is not None else Params()
  return set_active(p.get(THEME_PARAM, return_default=True))


class _ColorProxy:
  def __init__(self, group: str):
    self._group = group

  def __getattr__(self, name: str) -> rl.Color:
    return getattr(getattr(_active, self._group), name)


HUD_COLORS = _ColorProxy("hud")
ROAD_COLORS = _ColorProxy("road")


def with_alpha(color: rl.Color, alpha: int) -> rl.Color:
  """Themed RGB with a per-frame alpha (model confidence, distance fade)."""
  return rl.Color(color.r, color.g, color.b, alpha)
