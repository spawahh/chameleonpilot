"""
The fork's toggle params, as one list read in one place.

UIState reads params twice — once in `_initialize` and again in `update_params`
— and a toggle added to only the first takes effect on restart instead of
immediately. That is a real bug this fork has shipped before, and duplicating
seven reads makes it likely again. One mapping and one loop removes the
possibility rather than warning about it, and keeps the upstream diff at three
lines.

Deliberately imports nothing: `ui_state` imports this, and pulling in anything
from the widget or params layers here risks an import cycle.
"""

# attribute on ui_state -> params key
TOGGLES = {
  "blindspot": "BlindSpot",
  "dm_annunciator": "DmAnnunciator",
  "driver_alerts": "DriverAlerts",
  "flight_path_vector": "FlightPathVector",
  "hide_driving_path": "HideDrivingPath",
  "hide_lane_lines": "HideLaneLines",
  "hide_speed_cluster": "HideSpeedCluster",
  "hide_wheel_button": "HideWheelButton",
  "pitch_ladder": "PitchLadder",
  "rainbow_path": "RainbowMode",
  "rocket_fuel": "RocketFuel",
  "target_designator": "TargetDesignator",
  "turn_signals": "ShowTurnSignals",
}


def refresh(state, params) -> None:
  """Read every fork toggle onto `state`. Call from both UIState param sites."""
  for attr, key in TOGGLES.items():
    setattr(state, attr, params.get_bool(key))
