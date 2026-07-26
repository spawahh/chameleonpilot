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
class Theme:
  name: str  # param value: stable, lowercase, never translated
  label: str  # shown in the picker, translated at display time
  hud: HudColors
