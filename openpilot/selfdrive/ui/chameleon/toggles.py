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
  "AircraftTapes": tr_noop(
    "Draw aircraft-style tapes: speed on the left, GPS altitude on the right, and GPS heading along the top. " +
    "Altitude and heading appear after the first GPS fix; the heading hides below walking pace, where GPS course means nothing. " +
    "Altitude is height above the GPS ellipsoid, which can read a little different from map elevation. " +
    "Pairs well with Hide MAX and Speed Display."
  ),
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
  "DmAnnunciator": tr_noop(
    "Show an aircraft-style caution readout at the top of the onroad screen for driver monitoring: " +
    "your attention score, amber below 90 percent (or the moment you look away, or NO FACE if the camera lost you) and red below 75. " +
    "Escalates to an amber then red ATTENTION with openpilot, and a red LOCKOUT box when driver monitoring has locked you out. " +
    "Display only — openpilot's own alerts make the sounds."
  ),
  "DriverAlerts": tr_noop(
    "Show GREEN LIGHT and LEAD DEPARTING annunciator legends next to the driver monitoring readout. " +
    "They stay dim while armed, then brighten with a chime while stopped and disengaged when the light ahead turns green " +
    "(no lead car and the driving model sees an open road) or when the car in front starts to drive away."
  ),
  "FlightPathVector": tr_noop(
    "Draw an aircraft-style flight path vector on the road: a small winged circle marking where the car is actually travelling. " +
    "It centres itself at low speed, where the direction of travel means nothing."
  ),
  "HideDriverFace": tr_noop(
    "Hide the driver monitoring face icon at the bottom left of the onroad screen. " +
    "Driver monitoring itself stays fully active and still alerts you. With this on and the Driver Monitoring Annunciator off, " +
    "nothing on screen shows your attention state until openpilot raises an alert."
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
  "NeuralNetworkLateralControl": tr_noop(
    "Steer using a neural network model trained on this car platform's real driving data (sunnypilot's NNLC), instead of the standard controller. " +
    "Only takes effect on cars that use torque steering control and that have a trained model; otherwise steering stays completely stock. " +
    "Changing this restarts openpilot if the car is powered on."
  ),
  "NightVideo": tr_noop(
    "Show the road camera in black and white at night, like an aircraft's night vision display. " +
    "Only active while the theme's night palette is in effect, so it follows Night Mode."
  ),
  "PitchLadder": tr_noop(
    "Draw an aircraft-style pitch ladder on the road: bars marking every 5 degrees of climb and dive, " +
    "with a long bar on the horizon. It needs the device to be calibrated, and hides itself until then."
  ),
  "RainbowMode": tr_noop("Draw the predicted driving path as a moving rainbow instead of the normal path colours."),
  "RoadNameDisplay": tr_noop(
    "Show the name of the road you are on at the top of the onroad screen. " +
    "Needs downloaded map data (Chameleon settings, Map Data section)."
  ),
  "SpeedLimitDisplay": tr_noop(
    "Show the posted speed limit from offline map data as a road sign on the onroad screen, " +
    "with the upcoming limit when it is about to change. Display only: it never controls your speed. " +
    "Needs downloaded map data (Chameleon settings, Map Data section)."
  ),
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
  "AircraftTapes": (
    lambda: tr("Aircraft Tapes (Speed, Altitude, Heading)"),
    DESCRIPTIONS["AircraftTapes"],
    "road.png",
    False,
  ),
  "AutoLaneChangeBsmDelay": (
    lambda: tr("Auto Lane Change: Delay with Blind Spot"),
    DESCRIPTIONS["AutoLaneChangeBsmDelay"],
    "warning.png",
    False,
  ),
  "NeuralNetworkLateralControl": (
    lambda: tr("Neural Network Lateral Control (NNLC)"),
    DESCRIPTIONS["NeuralNetworkLateralControl"],
    "chffr_wheel.png",
    True,
  ),
  "BlindSpot": (
    lambda: tr("Blind Spot Indicators"),
    DESCRIPTIONS["BlindSpot"],
    "warning.png",
    False,
  ),
  "DmAnnunciator": (
    lambda: tr("Driver Monitoring Annunciator"),
    DESCRIPTIONS["DmAnnunciator"],
    "monitoring.png",
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
  "NightVideo": (
    lambda: tr("Night Vision Video"),
    DESCRIPTIONS["NightVideo"],
    "road.png",
    False,
  ),
  "PitchLadder": (
    lambda: tr("Pitch Ladder"),
    DESCRIPTIONS["PitchLadder"],
    "road.png",
    False,
  ),
  "HideDriverFace": (
    lambda: tr("Hide Driver Monitoring Face"),
    DESCRIPTIONS["HideDriverFace"],
    "monitoring.png",
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
  "RoadNameDisplay": (
    lambda: tr("Show Road Name"),
    DESCRIPTIONS["RoadNameDisplay"],
    "road.png",
    False,
  ),
  "SpeedLimitDisplay": (
    lambda: tr("Show Speed Limit Sign"),
    DESCRIPTIONS["SpeedLimitDisplay"],
    "speed_limit.png",
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
