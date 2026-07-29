import unittest
from types import SimpleNamespace
from unittest import mock

import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad import road_name as rn
from openpilot.selfdrive.ui.chameleon.onroad import speed_limit_sign as sl
from openpilot.selfdrive.ui.chameleon.onroad.road_name import RoadName
from openpilot.selfdrive.ui.chameleon.onroad.speed_limit_sign import GREY, SpeedLimitSign

SCREEN = rl.Rectangle(0, 0, 2160, 1080)


class FakeFont:
  pass


def fake_live(valid=True, limit_ms=13.4, ahead_valid=False, ahead_ms=0.0, ahead_dist=0.0, road=""):
  return SimpleNamespace(speedLimitValid=valid, speedLimit=limit_ms,
                         speedLimitAheadValid=ahead_valid, speedLimitAhead=ahead_ms,
                         speedLimitAheadDistance=ahead_dist, roadName=road)


class FakeSubMaster(dict):
  def __init__(self, live=None, recv_frame=10):
    super().__init__(liveMapData=live or fake_live())
    self.recv_frame = {'liveMapData': recv_frame}


class FakeUIState:
  def __init__(self, sign=True, road=True, metric=False):
    self.speed_limit_display = sign
    self.road_name_display = road
    self.is_metric = metric
    self.started_frame = 1


class SignTestCase(unittest.TestCase):
  def setUp(self):
    self._patch(mock.patch.object(sl.gui_app, 'font', return_value=FakeFont()))
    self.text = self._patch(mock.patch.object(sl.rl, 'draw_text_ex'))
    self.rect = self._patch(mock.patch.object(sl.rl, 'draw_rectangle_rounded'))
    self.rect_lines = self._patch(mock.patch.object(sl.rl, 'draw_rectangle_rounded_lines_ex'))
    self.circle = self._patch(mock.patch.object(sl.rl, 'draw_circle_v'))
    self.ring = self._patch(mock.patch.object(sl.rl, 'draw_ring'))
    self._patch(mock.patch.object(sl, 'measure_text_cached', return_value=rl.Vector2(80, 40)))
    self.ui_state = FakeUIState()
    self._patch(mock.patch.object(sl, 'ui_state', self.ui_state))

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def _render(self, sm=None):
    SpeedLimitSign().render(SCREEN, sm if sm is not None else FakeSubMaster())

  def _texts(self):
    return [c[0][1] for c in self.text.call_args_list]

  def test_no_draw_when_disabled(self):
    self.ui_state.speed_limit_display = False
    self._render()

    self.text.assert_not_called()

  def test_mutcd_shows_mph(self):
    """13.4 m/s is 30 mph on the US rectangle sign."""
    self._render(FakeSubMaster(fake_live(limit_ms=13.4)))

    self.assertIn("30", self._texts())
    self.assertIn("SPEED", self._texts())
    self.rect.assert_called()
    self.circle.assert_not_called()

  def test_vienna_shows_kph(self):
    self.ui_state.is_metric = True
    self._render(FakeSubMaster(fake_live(limit_ms=13.4)))

    self.assertIn("48", self._texts())  # 13.4 m/s = 48 km/h
    self.circle.assert_called_once()
    self.ring.assert_called_once()

  def test_invalid_limit_is_grey_dashes(self):
    self._render(FakeSubMaster(fake_live(valid=False, limit_ms=0.0)))

    value_calls = [c for c in self.text.call_args_list if c[0][1] == "--"]
    self.assertEqual(len(value_calls), 1)
    color = value_calls[0][0][5]
    self.assertEqual((color.r, color.g, color.b), (GREY.r, GREY.g, GREY.b))

  def test_ahead_box_only_when_different(self):
    self._render(FakeSubMaster(fake_live(limit_ms=13.4, ahead_valid=True, ahead_ms=13.4)))
    self.assertNotIn("AHEAD", self._texts())

    self.text.reset_mock()
    self._render(FakeSubMaster(fake_live(limit_ms=13.4, ahead_valid=True, ahead_ms=20.1, ahead_dist=150.0)))
    texts = self._texts()
    self.assertIn("AHEAD", texts)
    self.assertIn("45", texts)  # 20.1 m/s = 45 mph
    self.assertTrue(any("ft" in t for t in texts))  # 150 m = 492 ft, under the miles threshold


class RoadNameTestCase(unittest.TestCase):
  def setUp(self):
    self._patch(mock.patch.object(rn.gui_app, 'font', return_value=FakeFont()))
    self.text = self._patch(mock.patch.object(rn.rl, 'draw_text_ex'))
    self.pill = self._patch(mock.patch.object(rn.rl, 'draw_rectangle_rounded'))
    self._patch(mock.patch.object(rn, 'measure_text_cached', return_value=rl.Vector2(300, 42)))
    self.ui_state = FakeUIState()
    self._patch(mock.patch.object(rn, 'ui_state', self.ui_state))

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def test_draws_the_name(self):
    RoadName().render(SCREEN, FakeSubMaster(fake_live(road="NE 45th St")))

    self.assertEqual(self.text.call_args[0][1], "NE 45th St")
    self.pill.assert_called_once()

  def test_empty_name_draws_nothing(self):
    RoadName().render(SCREEN, FakeSubMaster(fake_live(road="")))

    self.text.assert_not_called()

  def test_toggle_off_draws_nothing(self):
    self.ui_state.road_name_display = False
    RoadName().render(SCREEN, FakeSubMaster(fake_live(road="NE 45th St")))

    self.text.assert_not_called()


if __name__ == '__main__':
  unittest.main()
