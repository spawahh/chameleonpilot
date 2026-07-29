"""Guards the refactor that moved these widgets out of upstream's HudRenderer:
every widget must still be updated, drawn, and drawn in the old order."""
import unittest
from unittest import mock

import numpy as np
import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad import overlays as ov

SCREEN = rl.Rectangle(0, 0, 2160, 1080)

WIDGETS = (
  '_blind_spot_indicators',
  '_driver_alerts',
  '_flight_path_vector',
  '_pitch_ladder',
  '_rocket_fuel',
  '_turn_signal_controller',
)

ROAD_SPACE_WIDGETS = ('_flight_path_vector', '_pitch_ladder')


class TestChameleonOverlays(unittest.TestCase):
  def setUp(self):
    for name in ('BlindSpotIndicators', 'DriverAlerts', 'FlightPathVector', 'PitchLadder',
                 'RocketFuel', 'TurnSignalController'):
      patcher = mock.patch.object(ov, name)
      patcher.start()
      self.addCleanup(patcher.stop)

    ui_state_patcher = mock.patch.object(ov, 'ui_state', mock.Mock(sm={}))
    ui_state_patcher.start()
    self.addCleanup(ui_state_patcher.stop)

    self.overlays = ov.ChameleonOverlays()

  def test_every_widget_is_rendered(self):
    self.overlays.render(SCREEN)

    for name in WIDGETS:
      self.assertTrue(getattr(self.overlays, name).render.called, f"{name} was not rendered")

  def test_stateful_widgets_are_updated_before_drawing(self):
    self.overlays.render(SCREEN)

    for name in ('_blind_spot_indicators', '_driver_alerts', '_turn_signal_controller'):
      widget = getattr(self.overlays, name)
      self.assertTrue(widget.update.called, f"{name} was not updated")

  def test_driver_alerts_draws_last(self):
    """It is a centred pop-up, so it has to sit on top of the other widgets."""
    calls = []
    for name in WIDGETS:
      getattr(self.overlays, name).render.side_effect = lambda *_, n=name: calls.append(n)

    self.overlays.render(SCREEN)

    self.assertEqual(calls[-1], '_driver_alerts')
    # the ladder is a backdrop; the vector reads on top of it, in its centre gap
    self.assertEqual(calls[:2], ['_pitch_ladder', '_flight_path_vector'])

  def test_transform_reaches_every_road_space_widget(self):
    transform = np.eye(3)
    self.overlays.set_transform(transform)

    for name in ROAD_SPACE_WIDGETS:
      getattr(self.overlays, name).set_transform.assert_called_once_with(transform)


if __name__ == '__main__':
  unittest.main()
