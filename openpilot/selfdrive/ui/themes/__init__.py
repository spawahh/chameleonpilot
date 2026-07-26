"""HUD theme registry.

Renderers read colors through the proxies exported here instead of module-level
constants, so adding or switching a theme never touches a renderer. The UI is a single
process, so a switch from settings takes effect on the next frame with no restart.
"""
import time

import pyray as rl

from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.ui.themes.base import Theme
from openpilot.selfdrive.ui.themes.cascade import CASCADE
from openpilot.selfdrive.ui.themes.stock import STOCK

THEME_PARAM = "HudTheme"
NIGHT_PARAM = "HudNightMode"  # "auto" | "on" | "off"
DEFAULT_THEME = STOCK

# Ambient trigger (auto mode). light_sensor is 0..100, derived from camera
# auto-exposure in ui_state (-1 when the camera is not alive). Hysteresis plus
# dwell so headlight glare or an underpass can't flap the palette. Tunables.
NIGHT_ENTER_BELOW = 30.0
NIGHT_EXIT_ABOVE = 45.0
NIGHT_DWELL_S = 15.0

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
  set_night_mode(p.get(NIGHT_PARAM, return_default=True))
  return set_active(p.get(THEME_PARAM, return_default=True))


class _NightResolver:
  """Decides whether the night palette is in effect. Not a bare boolean: manual
  modes override, auto follows ambient light with hysteresis and dwell."""

  def __init__(self):
    self.mode: str = "auto"
    self.is_night: bool = False
    self._pending: bool | None = None  # candidate state waiting out the dwell
    self._pending_since: float = 0.0

  def set_mode(self, mode: str) -> None:
    if mode not in ("auto", "on", "off"):
      cloudlog.warning(f"unknown {NIGHT_PARAM} {mode!r}, falling back to auto")
      mode = "auto"
    self.mode = mode
    self._pending = None
    if mode == "on":
      self.is_night = True
    elif mode == "off":
      self.is_night = False

  def tick(self, light_sensor: float, now: float | None = None) -> bool:
    if self.mode != "auto":
      return self.is_night
    if light_sensor < 0:  # camera not alive: hold the current state
      self._pending = None
      return self.is_night

    if self.is_night:
      candidate = not (light_sensor > NIGHT_EXIT_ABOVE)
    else:
      candidate = light_sensor < NIGHT_ENTER_BELOW

    if candidate == self.is_night:
      self._pending = None
      return self.is_night

    t = time.monotonic() if now is None else now
    if self._pending != candidate:
      self._pending = candidate
      self._pending_since = t
    elif t - self._pending_since >= NIGHT_DWELL_S:
      self.is_night = candidate
      self._pending = None
    return self.is_night


night = _NightResolver()


def set_night_mode(mode: str, params: Params | None = None) -> None:
  night.set_mode(mode)
  if params is not None:
    params.put(NIGHT_PARAM, night.mode, block=True)


def night_tick(light_sensor: float) -> None:
  """Call once per frame from the UI loop (auto mode's ambient trigger)."""
  night.tick(light_sensor)


class _ColorProxy:
  def __init__(self, group: str):
    self._group = group

  def __getattr__(self, name: str) -> rl.Color:
    palette = getattr(_active, self._group)
    if night.is_night:
      palette = getattr(_active, f"night_{self._group}") or palette
    return getattr(palette, name)


HUD_COLORS = _ColorProxy("hud")
ROAD_COLORS = _ColorProxy("road")
OFFROAD_COLORS = _ColorProxy("offroad")


def with_alpha(color: rl.Color, alpha: int) -> rl.Color:
  """Themed RGB with a per-frame alpha (model confidence, distance fade)."""
  return rl.Color(color.r, color.g, color.b, alpha)
