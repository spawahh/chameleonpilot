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
            vision_percent=94, wheel_percent=61, face_detected=True, distracted=False):
  return SimpleNamespace(
    lockout=lockout,
    alwaysOnLockout=always_on_lockout,
    lockoutMinutesRemaining=minutes,
    alertLevel=alert_level if alert_level is not None else da.AlertLevel.none,
    activePolicy=policy if policy is not None else da.MonitoringPolicy.vision,
    visionPolicyState=SimpleNamespace(awarenessPercent=vision_percent, faceDetected=face_detected, isDistracted=distracted),
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


class DmAnnunciatorTestCase(unittest.TestCase):
  """Shared fixture only — no tests, so subclasses don't re-run them."""

  def setUp(self):
    self._patch(mock.patch.object(da.gui_app, 'font', return_value=FakeFont()))
    self.text = self._patch(mock.patch.object(da.rl, 'draw_text_ex'))
    self.box = self._patch(mock.patch.object(da.rl, 'draw_rectangle_lines_ex'))
    self.fill = self._patch(mock.patch.object(da.rl, 'draw_rectangle_rec'))
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


class TestDmAnnunciator(DmAnnunciatorTestCase):
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
    self.box.assert_called_once()  # outlined like the alert legends
    self.fill.assert_not_called()  # the dark fill is for escalations only

  def test_awareness_colours_at_the_road_thresholds(self):
    """Colour off the score itself: openpilot's own alert levels land far
    lower (~62%/~38%), so the readout would stay green through the drain."""
    for percent, expected, filled in ((100, GREEN, False), (da.AMBER_PERCENT, GREEN, False),
                                      (da.AMBER_PERCENT - 1, AMBER, False), (da.RED_PERCENT, AMBER, False),
                                      (da.RED_PERCENT - 1, RED, True), (0, RED, True)):
      with self.subTest(percent=percent):
        self.box.reset_mock()
        self.fill.reset_mock()
        self.text.reset_mock()
        self._render(FakeSubMaster(fake_dm(vision_percent=percent)))

        text, color = self._drawn()
        self.assertEqual(text, f"MON {percent}%")
        self.assertEqual((color.r, color.g, color.b), (expected.r, expected.g, expected.b))
        self.assertEqual(self.fill.called, filled)

  def test_wheeltouch_awareness_uses_the_same_thresholds(self):
    self._render(FakeSubMaster(fake_dm(policy=da.MonitoringPolicy.wheeltouch,
                                       wheel_percent=da.RED_PERCENT - 1)))

    text, color = self._drawn()
    self.assertEqual(text, f"MON {da.RED_PERCENT - 1}%")
    self.assertEqual((color.r, color.g, color.b), (RED.r, RED.g, RED.b))

  def test_awareness_follows_the_active_policy(self):
    """The live percent lives on different sub-structs per policy."""
    self._render(FakeSubMaster(fake_dm(policy=da.MonitoringPolicy.wheeltouch, wheel_percent=61)))

    text, _ = self._drawn()
    self.assertEqual(text, "MON 61%")

  def test_no_face_shows_in_amber(self):
    """The camera losing the face is the state a driver can actually watch move."""
    self._render(FakeSubMaster(fake_dm(face_detected=False)))

    text, color = self._drawn()
    self.assertEqual(text, "NO FACE")
    self.assertEqual((color.r, color.g, color.b), (AMBER.r, AMBER.g, AMBER.b))

  # the distracted -> amber behaviour lives in TestDistractedDwell: it needs
  # sustained frames now, because the raw flag flashing single frames of amber
  # was itself a distraction on the road

  def test_wheeltouch_policy_ignores_the_face(self):
    """No camera in the loop: face state must not leak into the wheeltouch readout."""
    self._render(FakeSubMaster(fake_dm(policy=da.MonitoringPolicy.wheeltouch, face_detected=False, wheel_percent=100)))

    text, color = self._drawn()
    self.assertEqual(text, "MON 100%")
    self.assertEqual((color.r, color.g, color.b), (GREEN.r, GREEN.g, GREEN.b))

  def test_level_one_is_amber_outlined_not_filled(self):
    self._render(FakeSubMaster(fake_dm(alert_level=da.AlertLevel.one)))

    text, color = self._drawn()
    self.assertEqual(text, "ATTENTION")
    self.assertEqual((color.r, color.g, color.b), (AMBER.r, AMBER.g, AMBER.b))
    self.box.assert_called_once()
    self.fill.assert_not_called()

  def test_level_two_is_red_filled(self):
    self._render(FakeSubMaster(fake_dm(alert_level=da.AlertLevel.two)))

    text, color = self._drawn()
    self.assertEqual(text, "ATTENTION")
    self.assertEqual((color.r, color.g, color.b), (RED.r, RED.g, RED.b))
    self.box.assert_called_once()
    self.fill.assert_called_once()

  def test_lockout_beats_everything(self):
    self._render(FakeSubMaster(fake_dm(lockout=True, minutes=4, alert_level=da.AlertLevel.three)))

    text, color = self._drawn()
    self.assertEqual(text, "LOCK 4M")  # short form: the long one overflowed a row slot
    self.assertEqual((color.r, color.g, color.b), (RED.r, RED.g, RED.b))
    self.fill.assert_called_once()

  def test_always_on_lockout_counts(self):
    self._render(FakeSubMaster(fake_dm(always_on_lockout=True)))

    text, _ = self._drawn()
    self.assertEqual(text, "LOCKOUT")

  def test_text_is_centred_in_its_row_slot(self):
    self._render()

    x = self.text.call_args[0][2].x
    # fake measure.x = 160; the readout owns slot SLOT_MON, not the screen centre
    self.assertAlmostEqual(x + 80, da.slot_x(SCREEN, da.SLOT_MON), places=2)


class TestDistractedDwell(DmAnnunciatorTestCase):
  """The distracted cue must not flash: amber only after the raw flag holds
  for the dwell, then held so single-frame excursions never strobe the row."""

  def setUp(self):
    super().setUp()
    self.widget = DmAnnunciator()
    self.fps = da.gui_app.target_fps
    self.dwell = int(da.DISTRACTED_DWELL_S * self.fps)
    self.hold = int(da.DISTRACTED_HOLD_S * self.fps)

  def _frames(self, n, distracted):
    for _ in range(n):
      self.text.reset_mock()
      self.widget.render(SCREEN, FakeSubMaster(fake_dm(distracted=distracted, vision_percent=100)))
    return self.text.call_args[0][5]  # the last frame's colour

  def test_a_brief_excursion_never_goes_amber(self):
    color = self._frames(self.dwell - 1, distracted=True)
    self.assertEqual((color.r, color.g, color.b), (GREEN.r, GREEN.g, GREEN.b))

  def test_sustained_distraction_goes_amber(self):
    color = self._frames(self.dwell, distracted=True)
    self.assertEqual((color.r, color.g, color.b), (AMBER.r, AMBER.g, AMBER.b))

  def test_amber_holds_instead_of_strobing(self):
    self._frames(self.dwell, distracted=True)

    color = self._frames(self.hold - 1, distracted=False)
    self.assertEqual((color.r, color.g, color.b), (AMBER.r, AMBER.g, AMBER.b))

    color = self._frames(1, distracted=False)
    self.assertEqual((color.r, color.g, color.b), (GREEN.r, GREEN.g, GREEN.b))


class TestAnnunciatorIsSilent(DmAnnunciatorTestCase):
  """The readout is display-only: openpilot owns every driver-monitoring sound.

  A pre-warning chime was added here once and was not wanted — this pins the
  widget as silent so it does not come back by accident.
  """

  def test_no_chime_at_any_awareness_level(self):
    widget = DmAnnunciator()
    with mock.patch("openpilot.chameleon.chime.request") as request:
      for percent in (100, 95, da.AMBER_PERCENT, da.AMBER_PERCENT - 1, da.RED_PERCENT - 1, 0):
        widget.render(SCREEN, FakeSubMaster(fake_dm(vision_percent=percent)))

      request.assert_not_called()

  def test_module_does_not_import_the_chime_bus(self):
    self.assertFalse(hasattr(da, "chime"))


if __name__ == '__main__':
  unittest.main()
