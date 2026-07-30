import unittest
from types import SimpleNamespace
from unittest import mock

import pyray as rl

from openpilot.cereal import log
from openpilot.selfdrive.ui.chameleon.onroad.aircraft import dm_annunciator as dma
from openpilot.selfdrive.ui.chameleon.onroad.aircraft import status_legends as sl
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.status_legends import TempLegend, TurnLegend

SCREEN = rl.Rectangle(0, 0, 2160, 1080)

ThermalStatus = log.DeviceState.ThermalStatus
AlertSize = log.SelfdriveState.AlertSize


class FakeFont:
  pass


class FakeSubMaster(dict):
  def __init__(self, left=False, right=False, thermal=None, alert_size=None, car_frame=10):
    super().__init__(
      carState=SimpleNamespace(leftBlinker=left, rightBlinker=right),
      deviceState=SimpleNamespace(thermalStatus=thermal if thermal is not None else ThermalStatus.ok),
      selfdriveState=SimpleNamespace(alertSize=alert_size if alert_size is not None else AlertSize.none),
    )
    self.recv_frame = {'carState': car_frame}


class FakeUIState:
  def __init__(self):
    self.dm_annunciator = True
    self.started_frame = 1


class StatusLegendsTestCase(unittest.TestCase):
  def setUp(self):
    self._patch(mock.patch.object(sl.gui_app, 'font', return_value=FakeFont()))
    self.text = self._patch(mock.patch.object(dma.rl, 'draw_text_ex'))
    self.box = self._patch(mock.patch.object(dma.rl, 'draw_rectangle_lines_ex'))
    self.fill = self._patch(mock.patch.object(dma.rl, 'draw_rectangle_rec'))
    self._patch(mock.patch.object(dma, 'measure_text_cached', return_value=rl.Vector2(120, 44)))
    self.ui_state = FakeUIState()
    self._patch(mock.patch.object(sl, 'ui_state', self.ui_state))

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def _drawn(self):
    self.assertTrue(self.text.called, "nothing drawn")
    call = self.text.call_args
    return call[0][1], call[0][5]  # text, color


class TestTurnLegend(StatusLegendsTestCase):
  def test_dim_with_no_signal(self):
    TurnLegend().render(SCREEN, FakeSubMaster())

    text, color = self._drawn()
    self.assertEqual(text, "TURN")
    self.assertEqual(color.a, sl.DIM.a)

  def test_left_blinker_points_left(self):
    with mock.patch.object(sl.time, 'monotonic', return_value=0.0):  # on-phase
      TurnLegend().render(SCREEN, FakeSubMaster(left=True))

    text, color = self._drawn()
    self.assertEqual(text, "< TURN")
    self.assertEqual((color.r, color.g, color.b, color.a),
                     (sl.GREEN.r, sl.GREEN.g, sl.GREEN.b, sl.GREEN.a))

  def test_right_blinker_points_right(self):
    with mock.patch.object(sl.time, 'monotonic', return_value=0.0):
      TurnLegend().render(SCREEN, FakeSubMaster(right=True))

    text, _ = self._drawn()
    self.assertEqual(text, "TURN >")

  def test_blinks_at_the_shared_period(self):
    with mock.patch.object(sl.time, 'monotonic', return_value=sl.TURN_SIGNAL_BLINK_PERIOD * 1.5):
      TurnLegend().render(SCREEN, FakeSubMaster(left=True))

    _, color = self._drawn()
    self.assertEqual(color.a, sl.DIM.a)  # off-phase: back to the unlit look

  def test_sits_in_its_slot(self):
    TurnLegend().render(SCREEN, FakeSubMaster())

    pos = self.text.call_args[0][2]
    self.assertEqual(pos.x + 60, dma.slot_x(SCREEN, dma.SLOT_TURN))  # fake measure.x = 120
    self.assertEqual(pos.y, SCREEN.y + dma.TOP_MARGIN)

  def test_hidden_before_the_car_reports(self):
    self.ui_state.started_frame = 100
    TurnLegend().render(SCREEN, FakeSubMaster(car_frame=5))

    self.text.assert_not_called()


class TestTempLegend(StatusLegendsTestCase):
  def test_three_colors_and_the_critical_fill(self):
    for thermal, expected, filled in ((ThermalStatus.ok, sl.GREEN, False),
                                      (ThermalStatus.overheated, sl.AMBER, False),
                                      (ThermalStatus.critical, sl.RED, True)):
      with self.subTest(thermal=thermal):
        self.text.reset_mock()
        self.fill.reset_mock()
        TempLegend().render(SCREEN, FakeSubMaster(thermal=thermal))

        text, color = self._drawn()
        self.assertEqual(text, "TEMP")
        self.assertEqual((color.r, color.g, color.b), (expected.r, expected.g, expected.b))
        self.assertEqual(self.fill.called, filled)

  def test_sits_in_its_slot(self):
    TempLegend().render(SCREEN, FakeSubMaster())

    pos = self.text.call_args[0][2]
    self.assertEqual(pos.x + 60, dma.slot_x(SCREEN, dma.SLOT_TEMP))


class TestRowGates(StatusLegendsTestCase):
  def test_nothing_when_the_annunciator_toggle_is_off(self):
    self.ui_state.dm_annunciator = False
    TurnLegend().render(SCREEN, FakeSubMaster())
    TempLegend().render(SCREEN, FakeSubMaster())

    self.text.assert_not_called()

  def test_nothing_during_a_fullscreen_alert(self):
    sm = FakeSubMaster(alert_size=AlertSize.full)
    TurnLegend().render(SCREEN, sm)
    TempLegend().render(SCREEN, sm)

    self.text.assert_not_called()


if __name__ == '__main__':
  unittest.main()
