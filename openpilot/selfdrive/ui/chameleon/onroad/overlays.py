"""
The chameleonpilot onroad overlay widgets, as one set.

These used to be constructed and drawn inside upstream's HudRenderer. They live
here instead so the widget set does not belong to any one HUD layout: swapping
HudRenderer for an alternative layout must not take the blind spot, turn signal,
acceleration bar and driver alert widgets with it.

AugmentedRoadView draws this in the same z-position HudRenderer used to, so the
result on screen is unchanged.
"""
import numpy as np
import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad.aircraft.dm_annunciator import DmAnnunciator
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.flight_path_vector import FlightPathVector
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.pitch_ladder import PitchLadder
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.tapes import AircraftTapes
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.target_designator import TargetDesignator
from openpilot.selfdrive.ui.chameleon.onroad.blind_spot_indicators import BlindSpotIndicators
from openpilot.selfdrive.ui.chameleon.onroad.driver_alerts import DriverAlerts
from openpilot.selfdrive.ui.chameleon.onroad.road_name import RoadName
from openpilot.selfdrive.ui.chameleon.onroad.speed_limit_sign import SpeedLimitSign
from openpilot.selfdrive.ui.chameleon.onroad.rocket_fuel import RocketFuel
from openpilot.selfdrive.ui.chameleon.onroad.turn_signal import TurnSignalController
from openpilot.selfdrive.ui.ui_state import ui_state


class ChameleonOverlays:
  def __init__(self):
    self._aircraft_tapes = AircraftTapes()
    self._blind_spot_indicators = BlindSpotIndicators()
    self._dm_annunciator = DmAnnunciator()
    self._driver_alerts = DriverAlerts()
    self._flight_path_vector = FlightPathVector()
    self._pitch_ladder = PitchLadder()
    self._road_name = RoadName()
    self._rocket_fuel = RocketFuel()
    self._speed_limit_sign = SpeedLimitSign()
    self._target_designator = TargetDesignator()
    self._turn_signal_controller = TurnSignalController()

  def set_transform(self, transform: np.ndarray) -> None:
    """Car space to screen, shared with the model renderer."""
    self._flight_path_vector.set_transform(transform)
    self._pitch_ladder.set_transform(transform)
    self._target_designator.set_transform(transform)

  def update(self) -> None:
    self._blind_spot_indicators.update()
    self._turn_signal_controller.update()
    self._driver_alerts.update()

  def render(self, rect: rl.Rectangle) -> None:
    self.update()

    # road-space symbology first, so the screen-space widgets sit on top of it.
    # Ladder at the back; the designator brackets a car on the road; the vector
    # is the thing you read and stays on top, sitting in the ladder's centre gap.
    self._pitch_ladder.render(rect, ui_state.sm)
    self._target_designator.render(rect, ui_state.sm)
    self._flight_path_vector.render(rect, ui_state.sm)
    self._dm_annunciator.render(rect, ui_state.sm)
    self._aircraft_tapes.render(rect, ui_state.sm)
    self._speed_limit_sign.render(rect, ui_state.sm)
    self._road_name.render(rect, ui_state.sm)

    self._blind_spot_indicators.render(rect)
    self._turn_signal_controller.render(rect)
    self._rocket_fuel.render(rect, ui_state.sm)
    # annunciator legend on the DM row, draws on top of the other widgets
    self._driver_alerts.render(rect)
