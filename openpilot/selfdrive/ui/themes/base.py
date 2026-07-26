from dataclasses import dataclass

import pyray as rl


@dataclass(frozen=True)
class HudColors:
  # Field names match the upstream Colors dataclass so renderer call sites stay untouched.
  # No defaults: a theme missing a color fails at construction instead of drawing black.
  WHITE: rl.Color
  DISENGAGED: rl.Color
  OVERRIDE: rl.Color
  ENGAGED: rl.Color
  DISENGAGED_BG: rl.Color
  OVERRIDE_BG: rl.Color
  ENGAGED_BG: rl.Color
  GREY: rl.Color
  DARK_GREY: rl.Color
  BLACK_TRANSLUCENT: rl.Color
  WHITE_TRANSLUCENT: rl.Color
  BORDER_TRANSLUCENT: rl.Color
  HEADER_GRADIENT_START: rl.Color
  HEADER_GRADIENT_END: rl.Color


@dataclass(frozen=True)
class RoadColors:
  # Colors for the road view: screen border, driving path, lane lines, lead markers.
  # Same rules as HudColors: names are stable, no defaults.
  BORDER_DISENGAGED: rl.Color
  BORDER_OVERRIDE: rl.Color
  BORDER_ENGAGED: rl.Color
  # 3-stop path gradient, bottom of path -> top
  PATH_THROTTLE_NEAR: rl.Color
  PATH_THROTTLE_MID: rl.Color
  PATH_THROTTLE_FAR: rl.Color
  PATH_NO_THROTTLE_NEAR: rl.Color
  PATH_NO_THROTTLE_MID: rl.Color
  PATH_NO_THROTTLE_FAR: rl.Color
  # alpha of these two is replaced per frame (model confidence); only RGB is themed
  LANE_LINE: rl.Color
  ROAD_EDGE: rl.Color
  LEAD_GLOW: rl.Color
  LEAD_CHEVRON: rl.Color  # alpha replaced per frame with the distance-based fill


@dataclass(frozen=True)
class Theme:
  name: str  # param value: stable, lowercase, never translated
  label: str  # shown in the picker, translated at display time
  hud: HudColors
  road: RoadColors
