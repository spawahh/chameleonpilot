"""
The fork's setting definitions, consumed by the Chameleon settings panel.

These rows used to be merged into upstream's Toggles panel, which meant
upstream's `layouts/settings/toggles.py` carried fork lines — rebase surface
the fork exists to avoid. The Chameleon panel (`ui/chameleon/layouts/settings.py`)
renders these directly, so that upstream file is now byte-stock.

Row shape matches upstream's `_toggle_defs`: (title, description, icon,
needs_restart). Dict order is display order within the panel's sections.
"""
from openpilot.system.ui.lib.multilang import tr, tr_noop

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
  "HideDrivingPath": tr_noop(
    "Hide the colored driving path that openpilot draws on the road. " +
    "The flight path vector's ghost already rides the same planned path, so the two show the same information."
  ),
  "HideLaneLines": tr_noop(
    "Hide the white lane lines and the red road-edge lines. " +
    "The road edges are a warning cue in stock openpilot; hiding them is a clean-screen trade you are choosing to make."
  ),
  "HideSpeedCluster": tr_noop(
    "Hide the MAX set-speed box and the large speed number at the top of the onroad screen. " +
    "Your car's own dashboard still shows both."
  ),
  "HideWheelButton": tr_noop(
    "Hide the round steering wheel button at the top right of the onroad screen. " +
    "That button is also the tap target for Experimental Mode, which stays available in the Toggles panel."
  ),
  "PitchLadder": tr_noop(
    "Draw an aircraft-style pitch ladder on the road: bars marking every 5 degrees of climb and dive, " +
    "with a long bar on the horizon. It needs the device to be calibrated, and hides itself until then."
  ),
  "RainbowMode": tr_noop("Draw the predicted driving path as a moving rainbow instead of the normal path colours."),
  "TargetDesignator": tr_noop(
    "Draw aircraft-style corner brackets around the car ahead, with its distance and closing speed. " +
    "Replaces the stock red lead triangle, and turns red with the same urgency as the car ahead gets close. " +
    "Works even when your car's own cruise control does the speed keeping."
  ),
  "RocketFuel": tr_noop(
    "Show a bar on the left of the onroad screen for the acceleration the car is actually producing. " +
    "Green is speeding up, red is slowing down. This is what the car is doing, not what openpilot asked for."
  ),
  "ShowTurnSignals": tr_noop("Show a blinking arrow on the onroad screen while a turn signal is on."),
}

# param -> (title, description, icon, needs_restart), upstream's row shape
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
  "HideDrivingPath": (
    lambda: tr("Hide Driving Path"),
    DESCRIPTIONS["HideDrivingPath"],
    "road.png",
    False,
  ),
  "HideLaneLines": (
    lambda: tr("Hide Lane Lines and Road Edges"),
    DESCRIPTIONS["HideLaneLines"],
    "road.png",
    False,
  ),
  "HideSpeedCluster": (
    lambda: tr("Hide MAX and Speed Display"),
    DESCRIPTIONS["HideSpeedCluster"],
    "metric.png",
    False,
  ),
  "HideWheelButton": (
    lambda: tr("Hide Steering Wheel Button"),
    DESCRIPTIONS["HideWheelButton"],
    "chffr_wheel.png",
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
  "TargetDesignator": (
    lambda: tr("Lead Target Designator"),
    DESCRIPTIONS["TargetDesignator"],
    "road.png",
    False,
  ),
  "ShowTurnSignals": (
    lambda: tr("Display Turn Signals"),
    DESCRIPTIONS["ShowTurnSignals"],
    "arrow-right.png",
    False,
  ),
}
