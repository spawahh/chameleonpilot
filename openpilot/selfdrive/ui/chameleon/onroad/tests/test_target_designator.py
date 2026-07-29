import unittest
from unittest import mock

import numpy as np
import pyray as rl

from openpilot.selfdrive.locationd.calibrationd import HEIGHT_INIT
from openpilot.selfdrive.ui.chameleon.onroad.aircraft import target_designator as td
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.target_designator import (
  COLOR, LEAD_BUFF, MAX_THICKNESS, MIN_THICKNESS, TargetDesignator,
)

SCREEN = rl.Rectangle(0, 0, 2160, 1080)
CX, CY, FOCAL = 1080.0, 540.0, 900.0

# Same fake camera as the FPV and pitch ladder tests: depth forward,
# +lateral right, +vertical down.
TRANSFORM = np.array([
  [CX, FOCAL, 0.0],
  [CY, 0.0, FOCAL],
  [1.0, 0.0, 0.0],
])


class FakeLead:
  def __init__(self, present=True, d_rel=30.0, y_rel=0.0, v_rel=0.0, status=False):
    self.present = present
    self.dRel = d_rel
    self.yRel = y_rel
    self.vRel = v_rel
    self.status = status  # vision-fused radarState never sets this


class FakeModel:
  def __init__(self):
    xs = list(np.arange(0.0, 120.0, 2.0))
    self.position = mock.Mock(x=xs, y=[0.0] * len(xs), z=[0.0] * len(xs))


class FakeCalibration:
  def __init__(self, height=None):
    self.height = height if height is not None else []


class FakeSubMaster(dict):
  def __init__(self, lead_one=None, lead_two=None, recv_frame=10, radar_valid=True):
    super().__init__(
      radarState=mock.Mock(leadOne=lead_one or FakeLead(), leadTwo=lead_two or FakeLead(present=False)),
      liveCalibration=FakeCalibration(),
      modelV2=FakeModel(),
    )
    self.recv_frame = {'radarState': recv_frame}
    self.valid = {'radarState': radar_valid}


class FakeUIState:
  def __init__(self, enabled=True, started_frame=1, is_metric=True):
    self.target_designator = enabled
    self.started_frame = started_frame
    self.is_metric = is_metric


class FakeFont:
  pass


class TestTargetDesignator(unittest.TestCase):
  def setUp(self):
    self._patch(mock.patch.object(td.gui_app, 'font', return_value=FakeFont()))
    self.line = self._patch(mock.patch.object(td.rl, 'draw_line_ex'))
    self.text = self._patch(mock.patch.object(td.rl, 'draw_text_ex'))
    self._patch(mock.patch.object(td, 'measure_text_cached', return_value=rl.Vector2(120, 36)))
    self.ui_state = FakeUIState()
    self._patch(mock.patch.object(td, 'ui_state', self.ui_state))

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def _render(self, sm=None, rect=SCREEN):
    widget = TargetDesignator()
    widget.set_transform(TRANSFORM)
    widget.render(rect, sm if sm is not None else FakeSubMaster())
    return widget

  def _bracket_center(self):
    """Mean of all bracket line endpoints — the box is symmetric about its centre."""
    self.assertTrue(self.line.called, "no brackets drawn")
    xs, ys = [], []
    for call in self.line.call_args_list:
      for pt in (call[0][0], call[0][1]):
        xs.append(pt.x)
        ys.append(pt.y)
    return float(np.mean(xs)), float(np.mean(ys))

  def _box_width(self):
    xs = [pt.x for call in self.line.call_args_list for pt in (call[0][0], call[0][1])]
    return max(xs) - min(xs)

  def test_no_draw_when_disabled(self):
    self.ui_state.target_designator = False
    self._render()

    self.line.assert_not_called()

  def test_no_draw_when_radar_invalid(self):
    self._render(FakeSubMaster(radar_valid=False))

    self.line.assert_not_called()

  def test_no_draw_before_started(self):
    self.ui_state.started_frame = 100
    self._render(FakeSubMaster(recv_frame=5))

    self.line.assert_not_called()

  def test_no_draw_without_a_lead(self):
    self._render(FakeSubMaster(lead_one=FakeLead(present=False)))

    self.line.assert_not_called()

  def test_draws_on_present_even_when_status_is_falsy(self):
    """The Crosstrek pin: vision-fused radarState sets present/modelProb, never
    status. A status gate would blank the designator on every radarless car."""
    self._render(FakeSubMaster(lead_one=FakeLead(present=True, status=False)))

    self.assertTrue(self.line.called)
    self.assertEqual(self.line.call_count, 8)  # 4 corners x 2 arms, one lead

  def test_box_centres_on_the_projected_lead(self):
    d_rel = 30.0
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=d_rel, y_rel=0.0)))

    x, y = self._bracket_center()
    self.assertAlmostEqual(x, CX, delta=1.0)
    self.assertAlmostEqual(y, CY + FOCAL * HEIGHT_INIT[0] / d_rel, delta=1.0)

  def test_lateral_lead_moves_the_box(self):
    """radarState yRel is positive-left; on screen the box must go left too."""
    self._render(FakeSubMaster(lead_one=FakeLead(y_rel=3.0)))
    left_x = self._bracket_center()[0]

    self.line.reset_mock()
    self._render(FakeSubMaster(lead_one=FakeLead(y_rel=-3.0)))
    right_x = self._bracket_center()[0]

    self.assertLess(left_x, CX)
    self.assertGreater(right_x, CX)

  def test_box_shrinks_with_distance(self):
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=15.0)))
    near = self._box_width()

    self.line.reset_mock()
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=60.0)))
    far = self._box_width()

    self.assertGreater(near, far)

  def test_urgency_matches_the_chevron_formula(self):
    """Far and steady is calm; close and closing saturates, like the chevron."""
    self.assertEqual(TargetDesignator._urgency(LEAD_BUFF + 10, 0.0), 0.0)
    self.assertEqual(TargetDesignator._urgency(10.0, -8.0), 255.0)
    self.assertAlmostEqual(TargetDesignator._urgency(20.0, 0.0), 255 * 0.5, places=3)

  def test_calm_lead_is_green_and_thin(self):
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=60.0, v_rel=0.0)))

    color = self.line.call_args_list[0][0][3]
    thickness = self.line.call_args_list[0][0][2]
    self.assertEqual((color.r, color.g, color.b), (COLOR.r, COLOR.g, COLOR.b))
    self.assertEqual(thickness, MIN_THICKNESS)

  def test_close_closing_lead_is_red_and_thick(self):
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=8.0, v_rel=-9.0)))

    color = self.line.call_args_list[0][0][3]
    thickness = self.line.call_args_list[0][0][2]
    self.assertGreater(color.r, color.g)  # lerped to the chevron red
    self.assertEqual(thickness, MAX_THICKNESS)

  def test_second_lead_needs_separation(self):
    """Vision-fused leadTwo often shadows leadOne; a near-duplicate is not drawn."""
    shadow = FakeLead(d_rel=31.0)
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=30.0), lead_two=shadow))
    self.assertEqual(self.line.call_count, 8)

    self.line.reset_mock()
    distinct = FakeLead(d_rel=60.0)
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=30.0), lead_two=distinct))
    self.assertEqual(self.line.call_count, 16)

  def test_close_lead_pins_at_the_screen_edge(self):
    """A lead nearly under the bumper projects below the rect; it clamps in."""
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=2.0)))

    _, y = self._bracket_center()
    self.assertLessEqual(y, SCREEN.height)
    self.assertTrue(self.line.called)

  def test_readout_units_follow_is_metric(self):
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=30.0, v_rel=-3.0)))
    metric_text = self.text.call_args[0][1]
    self.assertIn("m", metric_text)
    self.assertIn("km/h", metric_text)

    self.text.reset_mock()
    self.ui_state.is_metric = False
    self._render(FakeSubMaster(lead_one=FakeLead(d_rel=30.0, v_rel=-3.0)))
    imperial_text = self.text.call_args[0][1]
    self.assertIn("ft", imperial_text)
    self.assertIn("mph", imperial_text)

  def test_steady_lead_shows_no_closing_rate(self):
    self._render(FakeSubMaster(lead_one=FakeLead(v_rel=0.1)))

    self.assertNotIn("km/h", self.text.call_args[0][1])


if __name__ == '__main__':
  unittest.main()
