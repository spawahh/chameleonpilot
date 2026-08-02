"""
Manual screen brightness.

Upstream drives the backlight off the wide road camera's auto-exposure: onroad
it puts that through a CIE 1931 curve into 30-100%, offroad it holds a fixed
BACKLIGHT_OFFROAD. There is no user control anywhere, and no way to ask for a
screen dimmer than the curve wants — which is the complaint at night, where the
automatic floor is 30%.

This is one number: 0 leaves upstream's automatic value exactly as it is,
anything else is the percentage to hold. Deliberately not a second light
policy — night mode already owns "is it dark outside", and stacking two
automatic brightness behaviours on one backlight is how the night modes Marcus
tried ended up flickering.

The level is applied *into* upstream's existing filter, so a change eases in
over its 10 s time constant instead of stepping, and the wakefulness logic
still wins: a manual level never keeps the screen lit past the timeout.

Zero imports, like `ui_params`: `ui_state` imports this at module load and a
dependency on the widget or params layers here risks an import cycle.
"""

AUTO = 0
# 10, not 0: a fixed level is meant to be readable. Turning the screen off is
# what the interaction timeout is for, and a user who picks 0 on the road has no
# way to see the menu that would undo it.
MIN_PERCENT = 10
MAX_PERCENT = 100
LEVELS = tuple(range(MIN_PERCENT, MAX_PERCENT + 1, 10))  # the picker's fixed choices


def resolve(percent: int, auto_brightness: float) -> float:
  """The brightness to use, given the setting and upstream's automatic value."""
  if percent == AUTO:
    return auto_brightness
  return float(min(max(percent, MIN_PERCENT), MAX_PERCENT))
