"""
The fork's Toggles rows, kept out of upstream's settings layout.

Every chameleonpilot setting used to be written straight into upstream's
`layouts/settings/toggles.py`, which grew it by 103 lines — half the fork's
entire upstream diff, in a file upstream edits whenever it adds a setting.
That is the rebase surface the fork exists to avoid, so the rows live here and
upstream keeps five call lines.

Display order is dict order. The fork's toggles were already the last eight in
upstream's dict, so merging with `|=` puts them exactly where they were.
"""
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets.list_view import multiple_button_item

DESCRIPTIONS = {
  "AutoLaneChangeTimer": tr_noop(
    "Start the lane change this long after the turn signal, without waiting for a nudge on the steering wheel. Default is Nudge. " +
    "Requires a car that sends blind spot monitoring (BSM) over CAN. On cars without BSM, every setting behaves like Nudge: " +
    "the steering nudge is always required. " +
    "Use caution: only signal when traffic and road conditions permit."
  ),
  "AutoLaneChangeBsmDelay": tr_noop(
    "Delay the auto lane change by one second when blind spot monitoring detects a vehicle. " +
    "Requires a car that sends blind spot monitoring over CAN, and an auto lane change timer other than Nudge."
  ),
  "BlindSpot": tr_noop(
    "Show an icon at the left or right edge of the onroad screen when your car reports a vehicle in that blind spot. " +
    "Requires a car that sends blind spot monitoring over CAN."
  ),
  "DriverAlerts": tr_noop(
    "Show a pop-up while stopped and disengaged when the traffic light ahead turns green (no lead car and the driving model sees an open road) " +
    "or when the car in front starts to drive away. Visual only, no sound."
  ),
  "FlightPathVector": tr_noop(
    "Draw an aircraft-style flight path vector on the road: a small winged circle marking where the car is actually travelling. " +
    "It centres itself at low speed, where the direction of travel means nothing."
  ),
  "PitchLadder": tr_noop(
    "Draw an aircraft-style pitch ladder on the road: bars marking every 5 degrees of climb and dive, " +
    "with a long bar on the horizon. It needs the device to be calibrated, and hides itself until then."
  ),
  "RainbowMode": tr_noop("Draw the predicted driving path as a moving rainbow instead of the normal path colours."),
  "RocketFuel": tr_noop(
    "Show a bar on the left of the onroad screen for the acceleration the car is actually producing. " +
    "Green is speeding up, red is slowing down. This is what the car is doing, not what openpilot asked for."
  ),
  "ShowTurnSignals": tr_noop("Show a blinking arrow on the onroad screen while a turn signal is on."),
}

# param, title, desc, icon, needs_restart — same shape as upstream's _toggle_defs
TOGGLE_DEFS = {
  "AutoLaneChangeBsmDelay": (
    lambda: tr("Auto Lane Change: Delay with Blind Spot"),
    DESCRIPTIONS["AutoLaneChangeBsmDelay"],
    "warning.png",
    False,
  ),
  "BlindSpot": (
    lambda: tr("Blind Spot Indicators"),
    DESCRIPTIONS["BlindSpot"],
    "warning.png",
    False,
  ),
  "DriverAlerts": (
    lambda: tr("Green Light and Lead Departure Alerts"),
    DESCRIPTIONS["DriverAlerts"],
    "warning.png",
    False,
  ),
  "FlightPathVector": (
    lambda: tr("Flight Path Vector"),
    DESCRIPTIONS["FlightPathVector"],
    "road.png",
    False,
  ),
  "PitchLadder": (
    lambda: tr("Pitch Ladder"),
    DESCRIPTIONS["PitchLadder"],
    "road.png",
    False,
  ),
  "RainbowMode": (
    lambda: tr("Rainbow Path"),
    DESCRIPTIONS["RainbowMode"],
    "road.png",
    False,
  ),
  "RocketFuel": (
    lambda: tr("Real-time Acceleration Bar"),
    DESCRIPTIONS["RocketFuel"],
    "speed_limit.png",
    False,
  ),
  "ShowTurnSignals": (
    lambda: tr("Display Turn Signals"),
    DESCRIPTIONS["ShowTurnSignals"],
    "arrow-right.png",
    False,
  ),
}

# The fork's non-toggle controls are keyed by the upstream toggle they follow,
# because upstream builds its rows in a loop and this is the only ordering hook.
_ALC_TIMER_FOLLOWS = "IsMetric"


class ChameleonToggles:
  """The fork's multi-button controls and the state they own."""

  def __init__(self, params):
    self._params = params
    self.alc_timer = multiple_button_item(
      lambda: tr("Auto Lane Change by Blinker"),
      lambda: tr(DESCRIPTIONS["AutoLaneChangeTimer"]),
      buttons=[lambda: tr("Nudge"), lambda: tr("Nudgeless"), "0.5s", "1s", "2s", "3s"],
      button_width=160,
      callback=self._set_alc_timer,
      selected_index=max(self._params.get("AutoLaneChangeTimer", return_default=True), 0),
      icon="chffr_wheel.png",
    )

  def insert_after(self, toggles: dict, param: str) -> None:
    """Place the fork's controls in display order, called per row as upstream builds them."""
    if param == _ALC_TIMER_FOLLOWS:
      toggles["AutoLaneChangeTimer"] = self.alc_timer

  def update(self, toggles: dict, CP) -> None:
    """Nudgeless auto lane change needs the car's blind spot monitoring (BSM)."""
    has_bsm = CP.enableBsm
    self.alc_timer.action_item.set_enabled(has_bsm)
    toggles["AutoLaneChangeBsmDelay"].action_item.set_enabled(has_bsm)

  def _set_alc_timer(self, button_index: int) -> None:
    # button order matches AutoLaneChangeMode values (NUDGE=0 .. THREE_SECONDS=5)
    self._params.put("AutoLaneChangeTimer", button_index, block=True)
