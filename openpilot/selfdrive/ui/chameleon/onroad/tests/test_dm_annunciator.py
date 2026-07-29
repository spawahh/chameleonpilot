import unittest
from types import SimpleNamespace
from unittest import mock

import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad.aircraft import dm_annunciator as da
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.dm_annunciator import AMBER, GREEN, RED, DmAnnunciator

SCREEN = rl.Rectangle(0, 0, 2160, 1080)


class FakeFont:
  pass


def fake_dm(lockout=False, always_on_lockout=False, minutes=0, alert_level=None, policy=None,
            vision_percent=94, wheel_percent=61):
  return SimpleNamespace(
    lockout=lockout,
    alwaysOnLockout=always_on_lockout,
    lockoutMinutesRemaining=minutes,
    alertLevel=alert_level if alert_level is not None else da.AlertLevel.none,
    activePolicy=policy if policy is not None else da.MonitoringPolicy.vision,
    visionPolicyState=SimpleNamespace(awarenessPercent=vision_percent),
    wheeltouchPolicyState=SimpleNamespace(awarenessPercent=wheel_percent),
  )


class FakeSubMaster(dict):
  def __init__(self, dm=None, recv_frame=10, alert_size=None):
    from openpilot.cereal import log
    super().__init__(
      driverMonitoringState=dm or fake_dm(),
      selfdriveState=SimpleNamespace(alertSize=alert_size if alert_size is not None else log.SelfdriveState.AlertSize.none),
    )
    self.recv_frame = {'driverMonitoringState': recv_frame}


class FakeUIState:
  def __init__(self, enabled=True, started_frame=1):
    self.dm_annunciator = enabled
    self.started_frame = started_frame


class TestDmAnnunciator(unittest.TestCase):
  def setUp(self):
    self._patch(mock.patch.object(da.gui_app, 'font', return_value=FakeFont()))
    self.text = self._patch(mock.patch.object(da.rl, 'draw_text_ex'))
    self.box = self._patch(mock.patch.object(da.rl, 'draw_rectangle_lines_ex'))
    self._patch(mock.patch.object(da, 'measure_text_cached', return_value=rl.Vector2(160, 44)))
    self.ui_state = FakeUIState()
    self._patch(mock.patch.object(da, 'ui_state', self.ui_state))

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def _render(self, sm=None):
    DmAnnunciator().render(SCREEN, sm if sm is not None else FakeSubMaster())

  def _drawn(self):
    self.assertTrue(self.text.called, "nothing drawn")
    call = self.text.call_args
    return call[0][1], call[0][5]  # text, color

  def test_no_draw_when_disabled(self):
    self.ui_state.dm_annunciator = False
    self._render()

    self.text.assert_not_called()

  def test_no_draw_before_started(self):
    self.ui_state.started_frame = 100
    self._render(FakeSubMaster(recv_frame=5))

    self.text.assert_not_called()

  def test_no_draw_during_a_fullscreen_alert(self):
    """The alert renderer owns the screen; same gate as the DM face icon."""
    from openpilot.cereal import log
    self._render(FakeSubMaster(alert_size=log.SelfdriveState.AlertSize.full))

    self.text.assert_not_called()

  def test_normal_shows_awareness_in_green(self):
    self._render(FakeSubMaster(fake_dm(vision_percent=94)))

    text, color = self._drawn()
    self.assertEqual(text, "MON 94%")
    self.assertEqual((color.r, color.g, color.b), (GREEN.r, GREEN.g, GREEN.b))
    self.box.assert_not_called()

  def test_awareness_follows_the_active_policy(self):
    """The live percent lives on different sub-structs per policy."""
    self._render(FakeSubMaster(fake_dm(policy=da.MonitoringPolicy.wheeltouch, wheel_percent=61)))

    text, _ = self._drawn()
    self.assertEqual(text, "MON 61%")

  def test_level_one_is_amber_unboxed(self):
    self._render(FakeSubMaster(fake_dm(alert_level=da.AlertLevel.one)))

    text, color = self._drawn()
    self.assertEqual(text, "ATTENTION")
    self.assertEqual((color.r, color.g, color.b), (AMBER.r, AMBER.g, AMBER.b))
    self.box.assert_not_called()

  def test_level_two_is_red_boxed(self):
    self._render(FakeSubMaster(fake_dm(alert_level=da.AlertLevel.two)))

    text, color = self._drawn()
    self.assertEqual(text, "ATTENTION")
    self.assertEqual((color.r, color.g, color.b), (RED.r, RED.g, RED.b))
    self.box.assert_called_once()

  def test_lockout_beats_everything(self):
    self._render(FakeSubMaster(fake_dm(lockout=True, minutes=4, alert_level=da.AlertLevel.three)))

    text, color = self._drawn()
    self.assertEqual(text, "LOCKOUT 4 MIN")
    self.assertEqual((color.r, color.g, color.b), (RED.r, RED.g, RED.b))
    self.box.assert_called_once()

  def test_always_on_lockout_counts(self):
    self._render(FakeSubMaster(fake_dm(always_on_lockout=True)))

    text, _ = self._drawn()
    self.assertEqual(text, "LOCKOUT")

  def test_text_is_centred(self):
    self._render()

    x = self.text.call_args[0][2].x
    self.assertAlmostEqual(x, SCREEN.width / 2 - 160 / 2, places=3)


if __name__ == '__main__':
  unittest.main()
