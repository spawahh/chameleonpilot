import unittest
from types import SimpleNamespace
from unittest import mock

import pyray as rl

from openpilot.cereal import log
from openpilot.selfdrive.ui.chameleon.onroad.aircraft import dm_annunciator as dma
from openpilot.selfdrive.ui.chameleon.onroad.aircraft import status_legends as sl
import openpilot.cereal.messaging as messaging
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.status_legends import (
  EngageLegend, GpsLegend, TempLegend, TurnLegend,
)

SCREEN = rl.Rectangle(0, 0, 2160, 1080)

ThermalStatus = log.DeviceState.ThermalStatus
AlertSize = log.SelfdriveState.AlertSize


class FakeFont:
  pass


def real_thermal(status):
  """A genuine capnp _DynamicEnum, not the module-level int.

  This matters: the two types compare equal but hash differently, so a fake
  using ThermalStatus.ok directly made a broken dict lookup pass in tests while
  TEMP sat red for a whole trip on the car. The fake has to be the real type.
  """
  msg = messaging.new_message('deviceState')
  msg.deviceState.thermalStatus = status
  return msg.deviceState.thermalStatus


class FakeSubMaster(dict):
  def __init__(self, left=False, right=False, thermal=None, alert_size=None, car_frame=10,
               has_fix=True, accuracy=3.0, enabled=False, engageable=False):
    super().__init__(
      carState=SimpleNamespace(leftBlinker=left, rightBlinker=right),
      deviceState=SimpleNamespace(thermalStatus=real_thermal(thermal or 'ok')),
      gpsLocation=SimpleNamespace(hasFix=has_fix, horizontalAccuracy=accuracy),
      selfdriveState=SimpleNamespace(alertSize=alert_size if alert_size is not None else AlertSize.none,
                                     enabled=enabled, engageable=engageable),
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
    # fake measure.x = 120; rl.Vector2 is float32 so compare approximately
    self.assertAlmostEqual(pos.x + 60, dma.slot_x(SCREEN, dma.SLOT_TURN), places=2)
    self.assertEqual(pos.y, SCREEN.y + dma.TOP_MARGIN)

  def test_hidden_before_the_car_reports(self):
    self.ui_state.started_frame = 100
    TurnLegend().render(SCREEN, FakeSubMaster(car_frame=5))

    self.text.assert_not_called()


class TestTempLegend(StatusLegendsTestCase):
  def test_three_colors_and_the_critical_fill(self):
    for thermal, expected, filled in (('ok', sl.GREEN, False),
                                      ('overheated', sl.AMBER, False),
                                      ('critical', sl.RED, True)):
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
    self.assertAlmostEqual(pos.x + 60, dma.slot_x(SCREEN, dma.SLOT_TEMP), places=2)


class TestTempRegression(StatusLegendsTestCase):
  """TEMP sat red for a whole trip while the device was a comfortable 52 C.

  A capnp enum field reads back as a _DynamicEnum: it compares equal to the
  module-level int but hashes differently, so the dict lookup it was written
  with missed every frame and fell through to a red default. These pin both the
  live type and the rule that an unknown state must never read as danger.
  """

  def test_the_live_enum_type_is_not_dict_hashable_against_the_int(self):
    live = real_thermal('ok')
    self.assertEqual(live, ThermalStatus.ok)  # equality holds...
    self.assertNotIn(live, {ThermalStatus.ok: 1})  # ...hashing does not

  def test_a_healthy_device_reads_green(self):
    TempLegend().render(SCREEN, FakeSubMaster(thermal='ok'))

    _, color = self._drawn()
    self.assertEqual((color.r, color.g, color.b), (sl.GREEN.r, sl.GREEN.g, sl.GREEN.b))
    self.fill.assert_not_called()

  def test_an_unknown_state_is_a_caution_not_a_danger(self):
    color, filled = sl.temp_style(real_thermal('warmDEPRECATED'))

    self.assertEqual((color.r, color.g, color.b), (sl.AMBER.r, sl.AMBER.g, sl.AMBER.b))
    self.assertFalse(filled)


class TestGpsLegend(StatusLegendsTestCase):
  def test_good_fix_is_green(self):
    GpsLegend().render(SCREEN, FakeSubMaster(has_fix=True, accuracy=3.0))

    text, color = self._drawn()
    self.assertEqual(text, "GPS")
    self.assertEqual((color.r, color.g, color.b), (sl.GREEN.r, sl.GREEN.g, sl.GREEN.b))

  def test_degraded_fix_is_amber(self):
    GpsLegend().render(SCREEN, FakeSubMaster(has_fix=True, accuracy=sl.GPS_GOOD_ACCURACY + 1))

    _, color = self._drawn()
    self.assertEqual((color.r, color.g, color.b), (sl.AMBER.r, sl.AMBER.g, sl.AMBER.b))

  def test_unreported_accuracy_is_amber_not_green(self):
    """0.0 means the module said nothing, which is not the same as perfect."""
    GpsLegend().render(SCREEN, FakeSubMaster(has_fix=True, accuracy=0.0))

    _, color = self._drawn()
    self.assertEqual((color.r, color.g, color.b), (sl.AMBER.r, sl.AMBER.g, sl.AMBER.b))

  def test_no_fix_is_dim(self):
    GpsLegend().render(SCREEN, FakeSubMaster(has_fix=False))

    _, color = self._drawn()
    self.assertEqual(color.a, sl.DIM.a)


class TestEngageLegend(StatusLegendsTestCase):
  def test_engaged_is_green(self):
    EngageLegend().render(SCREEN, FakeSubMaster(enabled=True))

    text, color = self._drawn()
    self.assertEqual(text, "ENGAGE")
    self.assertEqual((color.r, color.g, color.b), (sl.GREEN.r, sl.GREEN.g, sl.GREEN.b))

  def test_engageable_is_amber(self):
    EngageLegend().render(SCREEN, FakeSubMaster(engageable=True))

    _, color = self._drawn()
    self.assertEqual((color.r, color.g, color.b), (sl.AMBER.r, sl.AMBER.g, sl.AMBER.b))

  def test_not_engageable_is_dim(self):
    EngageLegend().render(SCREEN, FakeSubMaster())

    _, color = self._drawn()
    self.assertEqual(color.a, sl.DIM.a)


class TestRowGates(StatusLegendsTestCase):
  ALL = (TurnLegend, TempLegend, GpsLegend, EngageLegend)

  def test_nothing_when_the_annunciator_toggle_is_off(self):
    self.ui_state.dm_annunciator = False
    for legend in self.ALL:
      legend().render(SCREEN, FakeSubMaster())

    self.text.assert_not_called()

  def test_nothing_during_a_fullscreen_alert(self):
    sm = FakeSubMaster(alert_size=AlertSize.full)
    for legend in self.ALL:
      legend().render(SCREEN, sm)

    self.text.assert_not_called()

  def test_every_legend_lands_in_a_distinct_slot(self):
    """Seven slots, no two legends sharing one."""
    xs = set()
    for slot in range(dma.SLOTS):
      xs.add(dma.slot_x(SCREEN, slot))

    self.assertEqual(len(xs), dma.SLOTS)
    self.assertGreater(min(xs), SCREEN.x)
    self.assertLess(max(xs), SCREEN.x + SCREEN.width)


if __name__ == '__main__':
  unittest.main()
