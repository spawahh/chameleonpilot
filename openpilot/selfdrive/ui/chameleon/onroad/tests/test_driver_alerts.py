import unittest
from unittest import mock

import pyray as rl

from openpilot.cereal import log
from openpilot.selfdrive.ui.chameleon.onroad import driver_alerts as da
from openpilot.selfdrive.ui.chameleon.onroad.aircraft import dm_annunciator as dma
from openpilot.selfdrive.ui.chameleon.onroad.driver_alerts import (
  TOP_MARGIN, DriverAlerts, DriverAlertsHelper, E2EStates,
)

DT = 0.05  # deterministic tick for tests, matches DT_MDL
SCREEN = rl.Rectangle(0, 0, 2160, 1080)

AlertSize = log.SelfdriveState.AlertSize


class FakeCarState:
  def __init__(self):
    self.standstill = True
    self.vEgo = 0.0
    self.gasPressed = False


class FakeCarControl:
  def __init__(self):
    self.enabled = False


class FakePosition:
  def __init__(self, path_length):
    self.x = [0.0, path_length]


class FakeModelV2:
  def __init__(self, path_length=5.0):
    self.position = FakePosition(path_length)


class FakeLead:
  def __init__(self, present=False, d_rel=0.0):
    self.present = present
    self.dRel = d_rel


class FakeRadarState:
  def __init__(self):
    self.leadOne = FakeLead()


class FakeSelfdriveState:
  def __init__(self):
    self.alertSize = AlertSize.none


class FakeSM:
  def __init__(self):
    self._services = {
      'carState': FakeCarState(),
      'carControl': FakeCarControl(),
      'modelV2': FakeModelV2(),
      'radarState': FakeRadarState(),
      'selfdriveState': FakeSelfdriveState(),
    }
    self.recv_frame = {'driverStateV2': 10}

  def __getitem__(self, service):
    return self._services[service]


class FakeUIState:
  def __init__(self):
    self.driver_alerts = True
    self.driver_alert_style = da.AlertStyle.LEGEND
    self.started_frame = 0
    self.sm = FakeSM()


class FakeFont:
  pass


class DriverAlertsTestCase(unittest.TestCase):
  def setUp(self):
    self.ui_state = FakeUIState()
    self._patch(mock.patch.object(da, 'ui_state', self.ui_state))
    self._patch(mock.patch.object(da.gui_app, 'font', return_value=FakeFont()))

  def _patch(self, patcher):
    started = patcher.start()
    self.addCleanup(patcher.stop)
    return started

  def _ticks(self, seconds):
    return int(seconds / DT) + 2

  def _make_helper(self):
    helper = DriverAlertsHelper()
    helper._dt = DT
    return helper

  def _run(self, helper, seconds):
    """Run the helper, reporting whether either alert pulsed during the window."""
    green = lead = False
    for _ in range(self._ticks(seconds)):
      helper.update()
      green = green or helper.green_light_alert
      lead = lead or helper.lead_depart_alert
    return green, lead

  def _drive_then_stop(self, helper, cooldown=2.5):
    """Alerts never arm before the car has moved once (last_moving_frame == -1
    counts as recently moving), so tests roll the car forward and stop it."""
    cs = self.ui_state.sm['carState']
    cs.standstill = False
    cs.vEgo = 5.0
    self._run(helper, 0.5)
    cs.standstill = True
    cs.vEgo = 0.0
    return self._run(helper, cooldown)


class TestDriverAlertsHelper(DriverAlertsTestCase):
  def test_green_light_alert_fires(self):
    """Stopped, disengaged, no lead: arming then a long model path fires the alert once."""
    helper = self._make_helper()
    green, _ = self._drive_then_stop(helper)
    self.assertFalse(green)
    self.assertEqual(helper.green_light_state, E2EStates.ARMED)

    self.ui_state.sm['modelV2'].position.x = [0.0, 60.0]  # light turns green, path opens
    green, lead = self._run(helper, 1.0)

    self.assertTrue(green)
    self.assertFalse(lead)
    self.assertEqual(helper.green_light_state, E2EStates.CONSUMED)

  def test_green_light_needs_sustained_trigger(self):
    """A single long-path frame (model noise) does not fire."""
    helper = self._make_helper()
    self._drive_then_stop(helper)

    self.ui_state.sm['modelV2'].position.x = [0.0, 60.0]
    helper.update()
    self.assertFalse(helper.green_light_alert)

    self.ui_state.sm['modelV2'].position.x = [0.0, 5.0]
    green, _ = self._run(helper, 1.0)
    self.assertFalse(green)

  def test_alert_fires_only_once(self):
    """After firing, the state machine stays consumed instead of re-alerting."""
    helper = self._make_helper()
    self._drive_then_stop(helper)
    self.ui_state.sm['modelV2'].position.x = [0.0, 60.0]
    green, _ = self._run(helper, 1.0)
    self.assertTrue(green)

    green, _ = self._run(helper, 3.0)
    self.assertFalse(green)
    self.assertEqual(helper.green_light_state, E2EStates.CONSUMED)

  def test_no_alert_when_disabled(self):
    self.ui_state.driver_alerts = False
    helper = self._make_helper()
    self._drive_then_stop(helper)
    self.assertEqual(helper.green_light_state, E2EStates.INACTIVE)

    self.ui_state.sm['modelV2'].position.x = [0.0, 60.0]
    green, lead = self._run(helper, 1.0)
    self.assertFalse(green)
    self.assertFalse(lead)

  def test_no_alert_when_engaged(self):
    """openpilot handles the launch itself when engaged, so no nag."""
    self.ui_state.sm['carControl'].enabled = True
    helper = self._make_helper()
    self._drive_then_stop(helper)
    self.assertEqual(helper.green_light_state, E2EStates.INACTIVE)

  def test_no_alert_when_gas_pressed(self):
    helper = self._make_helper()
    self.ui_state.sm['carState'].gasPressed = True
    self._drive_then_stop(helper)
    self.assertEqual(helper.green_light_state, E2EStates.INACTIVE)

  def test_no_arm_right_after_stopping(self):
    """The 2 s cooldown after moving keeps ordinary stop-and-go from arming instantly."""
    helper = self._make_helper()
    self._drive_then_stop(helper, cooldown=1.0)  # 1.0 s stopped is inside the cooldown
    self.assertEqual(helper.green_light_state, E2EStates.INACTIVE)

    self._run(helper, 2.0)
    self.assertEqual(helper.green_light_state, E2EStates.ARMED)

  def test_green_light_not_armed_with_lead(self):
    """With a lead present the green light alert stays inactive - the lead owns the cue."""
    self.ui_state.sm['radarState'].leadOne = FakeLead(present=True, d_rel=5.0)
    helper = self._make_helper()
    self._drive_then_stop(helper)
    self.assertEqual(helper.green_light_state, E2EStates.INACTIVE)

    self.ui_state.sm['modelV2'].position.x = [0.0, 60.0]
    green, _ = self._run(helper, 1.0)
    self.assertFalse(green)

  def test_lead_departure_alert_fires(self):
    """A close lead held for 1 s arms; the lead pulling >1 m away fires."""
    lead = FakeLead(present=True, d_rel=5.0)
    self.ui_state.sm['radarState'].leadOne = lead
    helper = self._make_helper()
    self._drive_then_stop(helper, cooldown=4.0)
    self.assertEqual(helper.lead_depart_state, E2EStates.ARMED)

    lead.dRel = 7.5
    green, depart = self._run(helper, 1.0)
    self.assertTrue(depart)
    self.assertFalse(green)

  def test_lead_departure_needs_confirmed_lead(self):
    """A lead that shows up after we are already stopped and settled does not arm."""
    helper = self._make_helper()
    self._drive_then_stop(helper)

    self.ui_state.sm['radarState'].leadOne = FakeLead(present=True, d_rel=5.0)
    self._run(helper, 2.0)
    self.assertEqual(helper.lead_depart_state, E2EStates.INACTIVE)

  def test_empty_model_position_is_safe(self):
    """modelV2 can be empty before the model publishes; must not crash."""
    self.ui_state.sm['modelV2'].position.x = []
    helper = self._make_helper()
    green, lead = self._drive_then_stop(helper)
    self.assertFalse(green)
    self.assertFalse(lead)


class TestDriverAlertsRenderer(DriverAlertsTestCase):
  def setUp(self):
    super().setUp()
    self.draw_box = self._patch(mock.patch.object(da.rl, 'draw_rectangle_rec'))
    self.draw_outline = self._patch(mock.patch.object(da.rl, 'draw_rectangle_lines_ex'))
    self.draw_text = self._patch(mock.patch.object(da.rl, 'draw_text_ex'))
    # draw_legend lives in dm_annunciator; patch the measure it actually calls
    self._patch(mock.patch.object(dma, 'measure_text_cached', return_value=rl.Vector2(100, 48)))
    self.chime = self._patch(mock.patch.object(da, 'chime'))

  def _fired_alerts(self):
    """A DriverAlerts widget whose helper just pulsed the green light alert."""
    alerts = DriverAlerts()
    with mock.patch.object(alerts._helper, 'update') as helper_update:
      helper_update.side_effect = lambda: setattr(alerts._helper, 'green_light_alert', True)
      alerts.update()
    alerts._helper.green_light_alert = False
    return alerts

  def test_alert_latches_display_timer_and_chimes_once(self):
    alerts = self._fired_alerts()
    self.assertEqual(alerts._display_timer, int(3.0 * da.gui_app.target_fps) - 1)
    self.assertEqual(alerts._alert_kind, da.GREEN_LIGHT)
    self.chime.request.assert_called_once_with(da.CHIME)

  def test_active_legend_is_boxed_both_stay_visible(self):
    alerts = self._fired_alerts()
    alerts.render(SCREEN)

    self.draw_box.assert_called_once()  # background fill only behind the active legend
    self.assertEqual(self.draw_outline.call_count, 2)
    self.assertEqual(self.draw_text.call_count, 2)

  def test_legends_sit_in_their_row_slots(self):
    """Centred in the annunciator row's first two slots, one line."""
    alerts = self._fired_alerts()
    alerts.render(SCREEN)

    first = self.draw_text.call_args_list[0].args[2]
    second = self.draw_text.call_args_list[1].args[2]
    self.assertEqual(first.y, SCREEN.y + TOP_MARGIN)
    self.assertEqual(second.y, SCREEN.y + TOP_MARGIN)  # one line, not stacked

    # fake measure.x = 100, so each text starts 50 left of its slot centre
    # rl.Vector2 is float32, so the round-trip cannot match a float64 exactly
    self.assertAlmostEqual(first.x + 50, dma.slot_x(SCREEN, dma.SLOT_GREEN_LIGHT), places=2)
    self.assertAlmostEqual(second.x + 50, dma.slot_x(SCREEN, dma.SLOT_LEAD_DEPART), places=2)

  def test_idle_legends_draw_dim_with_no_fill(self):
    alerts = DriverAlerts()
    with mock.patch.object(alerts._helper, 'update'):
      alerts.update()
    alerts.render(SCREEN)

    self.draw_box.assert_not_called()
    self.assertEqual(self.draw_text.call_count, 2)
    for call in self.draw_text.call_args_list:
      self.assertEqual(call.args[5], da.DIM)
    self.chime.request.assert_not_called()

  def test_no_draw_when_disabled(self):
    alerts = self._fired_alerts()
    self.ui_state.driver_alerts = False
    alerts.render(SCREEN)

    self.draw_text.assert_not_called()

  def test_no_draw_over_real_alert(self):
    """A real selfdrive alert on screen suppresses the legends entirely."""
    self.ui_state.sm['selfdriveState'].alertSize = AlertSize.small
    alerts = self._fired_alerts()
    alerts.render(SCREEN)

    self.draw_text.assert_not_called()

  def test_no_draw_before_driver_monitoring(self):
    self.ui_state.started_frame = 100  # driverStateV2 recv_frame (10) predates onroad
    alerts = self._fired_alerts()
    alerts.render(SCREEN)

    self.draw_text.assert_not_called()

  def test_display_expires_back_to_dim(self):
    alerts = self._fired_alerts()
    with mock.patch.object(alerts._helper, 'update'):
      for _ in range(int(3.0 * da.gui_app.target_fps) + 1):
        alerts.update()
    alerts.render(SCREEN)

    self.draw_box.assert_not_called()  # no fill: nothing active any more
    self.assertEqual(self.draw_text.call_count, 2)  # but the dim legends remain
    self.chime.request.assert_called_once()  # and the chime never replayed


class TestAlertStyle(DriverAlertsTestCase):
  """Legend, pop-up, or both.

  The pop-up was the original ported look and the legend replaced it outright,
  which removed the choice rather than adding one — so what matters here is that
  each style draws its own thing and nothing else, and that the default is still
  the legend the car has been running.
  """

  def setUp(self):
    super().setUp()
    self.legend = self._patch(mock.patch.object(da, 'draw_legend'))
    self.circle = self._patch(mock.patch.object(da.rl, 'draw_circle_v'))
    self.ring = self._patch(mock.patch.object(da.rl, 'draw_ring'))
    self.draw_text = self._patch(mock.patch.object(da.rl, 'draw_text_ex'))
    self._patch(mock.patch.object(da, 'measure_text_cached', return_value=rl.Vector2(100, 48)))
    self._patch(mock.patch.object(da, 'chime'))

  def _firing(self, style):
    self.ui_state.driver_alert_style = style
    alerts = DriverAlerts()
    with mock.patch.object(alerts._helper, 'update') as helper_update:
      helper_update.side_effect = lambda: setattr(alerts._helper, 'green_light_alert', True)
      alerts.update()
    alerts._helper.green_light_alert = False
    return alerts

  def test_default_style_is_the_legend(self):
    self.assertEqual(da.AlertStyle.LEGEND, 0, "0 is the params default, so it must mean LEGEND")

  def test_legend_style_draws_no_circle(self):
    self._firing(da.AlertStyle.LEGEND).render(SCREEN)

    self.assertEqual(self.legend.call_count, 2)  # both legends, one of them lit
    self.circle.assert_not_called()

  def test_popup_style_draws_no_legend(self):
    self._firing(da.AlertStyle.POPUP).render(SCREEN)

    self.legend.assert_not_called()
    self.circle.assert_called_once()
    self.ring.assert_called_once()

  def test_both_draws_both(self):
    self._firing(da.AlertStyle.BOTH).render(SCREEN)

    self.assertEqual(self.legend.call_count, 2)
    self.circle.assert_called_once()

  def test_popup_uses_the_original_two_line_wording(self):
    self._firing(da.AlertStyle.POPUP).render(SCREEN)

    lines = [c.args[1] for c in self.draw_text.call_args_list]
    self.assertEqual(lines, ["GREEN", "LIGHT"])

  def test_popup_draws_nothing_while_idle(self):
    """A pop-up has no unlit state: an idle one would be a black disc on the road."""
    self.ui_state.driver_alert_style = da.AlertStyle.POPUP
    alerts = DriverAlerts()
    with mock.patch.object(alerts._helper, 'update'):
      alerts.update()

    alerts.render(SCREEN)

    self.circle.assert_not_called()
    self.ring.assert_not_called()

  def test_legends_stay_visible_while_idle(self):
    """The legend style is an annunciator panel: dim when armed, bright when lit."""
    self.ui_state.driver_alert_style = da.AlertStyle.LEGEND
    alerts = DriverAlerts()
    with mock.patch.object(alerts._helper, 'update'):
      alerts.update()

    alerts.render(SCREEN)

    self.assertEqual(self.legend.call_count, 2)

  def test_the_toggle_still_switches_everything_off(self):
    for style in (da.AlertStyle.LEGEND, da.AlertStyle.POPUP, da.AlertStyle.BOTH):
      with self.subTest(style=style):
        self.legend.reset_mock()
        self.circle.reset_mock()
        alerts = self._firing(style)
        self.ui_state.driver_alerts = False

        alerts.render(SCREEN)

        self.legend.assert_not_called()
        self.circle.assert_not_called()
      self.ui_state.driver_alerts = True


if __name__ == '__main__':
  unittest.main()
