import math
import unittest
from unittest import mock

import numpy as np
import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad.aircraft import pitch_ladder as pl
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.pitch_ladder import (
  COLOR, DASHES, HORIZON_COLOR, LADDER_RANGE, LADDER_STEP, PitchLadder,
)

SCREEN = rl.Rectangle(0, 0, 2160, 1080)
CX, CY, FOCAL = 1080.0, 540.0, 900.0

# Same shape as test_flight_path_vector's: depth forward, +lateral right,
# +vertical down. At unit distance a point at height z lands FOCAL*z below CY.
TRANSFORM = np.array([
  [CX, FOCAL, 0.0],
  [CY, 0.0, FOCAL],
  [1.0, 0.0, 0.0],
])

BARS = int(2 * LADDER_RANGE / LADDER_STEP) + 1  # -15..+15 by 5 = 7


class FakeOrientation:
  def __init__(self, pitch, roll, valid=True):
    self.x, self.y, self.z = roll, pitch, 0.0
    self.xStd = self.yStd = self.zStd = 0.0
    self.valid = valid


class FakeLivePose:
  def __init__(self, pitch=0.0, roll=0.0, valid=True):
    self.orientationNED = FakeOrientation(pitch, roll, valid)
    zero = FakeOrientation(0.0, 0.0)
    self.velocityDevice = self.accelerationDevice = self.angularVelocityDevice = zero


class FakeCalibration:
  """rpyCalib all-zero means the calib frame equals the device frame, so the
  transform in these tests is the whole story."""
  def __init__(self, calibrated=True):
    self.rpyCalib = [0.0, 0.0, 0.0]
    self.calStatus = 1 if calibrated else 0


class FakeSubMaster(dict):
  def __init__(self, pitch=0.0, roll=0.0, valid=True, calibrated=True, recv_frame=10, calib_frame=10):
    super().__init__(
      livePose=FakeLivePose(pitch, roll, valid),
      liveCalibration=FakeCalibration(calibrated),
    )
    self.recv_frame = {'livePose': recv_frame, 'liveCalibration': calib_frame}


class FakeUIState:
  def __init__(self, enabled=True, started_frame=1, dm_annunciator=False, aircraft_tapes=False):
    self.pitch_ladder = enabled
    self.started_frame = started_frame
    # The ladder fades near whatever occupies the top row and the bottom tape, so
    # it reads both of those toggles. Off by default here: the geometry tests are
    # about where bars land, and a fade would change the colours they match on.
    # TestLadderFade turns them on.
    self.dm_annunciator = dm_annunciator
    self.aircraft_tapes = aircraft_tapes


class FakeFont:
  """gui_app has no font atlas without a window, and these tests never open one."""


class TestPitchLadder(unittest.TestCase):
  def setUp(self):
    # calStatus is compared against a capnp enum inside PoseCalibrator; the fake
    # uses plain ints, so map "calibrated" onto 1 for the duration of the test.
    status_patcher = mock.patch(
      'openpilot.selfdrive.locationd.helpers.log.LiveCalibrationData.Status.calibrated', 1
    )
    status_patcher.start()
    self.addCleanup(status_patcher.stop)

    font_patcher = mock.patch.object(pl.gui_app, 'font', return_value=FakeFont())
    font_patcher.start()
    self.addCleanup(font_patcher.stop)

    line_patcher = mock.patch.object(pl.rl, 'draw_line_ex')
    self.line = line_patcher.start()
    self.addCleanup(line_patcher.stop)

    text_patcher = mock.patch.object(pl.rl, 'draw_text_ex')
    self.text = text_patcher.start()
    self.addCleanup(text_patcher.stop)

    measure_patcher = mock.patch.object(pl, 'measure_text_cached', return_value=rl.Vector2(20, 34))
    measure_patcher.start()
    self.addCleanup(measure_patcher.stop)

    self._patch_ui_state(FakeUIState())

  def _patch_ui_state(self, ui_state):
    patcher = mock.patch.object(pl, 'ui_state', ui_state)
    patcher.start()
    self.addCleanup(patcher.stop)
    return ui_state

  def _render(self, sm=None, rect=SCREEN):
    ladder = PitchLadder()
    ladder.set_transform(TRANSFORM)
    ladder.render(rect, sm if sm is not None else FakeSubMaster())
    return ladder

  def _horizon_y(self):
    """Screen y of the horizon bar, found by its distinct colour."""
    ys = [c[0][0].y for c in self.line.call_args_list if c[0][3] is HORIZON_COLOR]
    self.assertTrue(ys, "horizon bar was not drawn")
    return ys[0]

  def _bar_ys(self):
    """Distinct y values of horizontal segments, top to bottom."""
    ys = {round(c[0][0].y, 3) for c in self.line.call_args_list
          if abs(c[0][0].y - c[0][1].y) < 1e-6}
    return sorted(ys)

  def test_no_draw_when_disabled(self):
    self._patch_ui_state(FakeUIState(enabled=False))
    self._render()

    self.line.assert_not_called()
    self.text.assert_not_called()

  def test_no_draw_before_the_model_starts(self):
    self._patch_ui_state(FakeUIState(started_frame=100))
    self._render(FakeSubMaster(recv_frame=5))

    self.line.assert_not_called()

  def test_no_draw_without_calibration(self):
    """Uncalibrated, the mount angle is unknown and the horizon would be wrong."""
    self._render(FakeSubMaster(calibrated=False))

    self.line.assert_not_called()

  def test_no_draw_when_pose_invalid(self):
    self._render(FakeSubMaster(valid=False))

    self.line.assert_not_called()

  def test_level_puts_the_horizon_on_the_boresight(self):
    self._render(FakeSubMaster(pitch=0.0))

    self.assertAlmostEqual(self._horizon_y(), CY, places=3)

  def test_nose_up_moves_the_ladder_down(self):
    """Climbing a hill, the horizon slides down the screen — the ladder is an
    attitude reference, not a fixed grid. This is the sign that matters."""
    self._render(FakeSubMaster(pitch=0.0))
    level = self._horizon_y()

    self.line.reset_mock()
    self._render(FakeSubMaster(pitch=math.radians(5.0)))
    nose_up = self._horizon_y()

    self.line.reset_mock()
    self._render(FakeSubMaster(pitch=math.radians(-5.0)))
    nose_down = self._horizon_y()

    self.assertGreater(nose_up, level)
    self.assertLess(nose_down, level)
    # 5 deg of pitch is 5 deg of screen angle either way
    self.assertAlmostEqual(nose_up - CY, CY - nose_down, places=3)
    self.assertAlmostEqual(nose_up - CY, FOCAL * math.tan(math.radians(5.0)), places=3)

  def test_bar_spacing_matches_the_step(self):
    """Neighbouring rungs sit LADDER_STEP degrees apart on screen."""
    self._render(FakeSubMaster(pitch=0.0))
    ys = self._bar_ys()

    self.assertEqual(len(ys), BARS)
    # tan spacing widens away from the boresight, so compare each gap to its own angle
    for above, below in zip(ys, ys[1:], strict=False):
      self.assertGreater(below - above, FOCAL * math.tan(math.radians(LADDER_STEP)) - 1.0)

  def test_climb_bars_solid_dive_bars_dashed(self):
    """Aircraft convention: above the horizon solid, below it broken."""
    self._render(FakeSubMaster(pitch=0.0))

    horizon_y = self._horizon_y()
    above, below = 0, 0
    for call in self.line.call_args_list:
      start, end = call[0][0], call[0][1]
      if abs(start.y - end.y) > 1e-6 or abs(start.y - horizon_y) < 1e-6:
        continue  # a tick, or the horizon itself
      if start.y < horizon_y:
        above += 1
      else:
        below += 1

    bars_per_side = (BARS - 1) // 2
    # two spans per climb bar, DASHES segments per span when diving
    self.assertEqual(above, bars_per_side * 2)
    self.assertEqual(below, bars_per_side * 2 * DASHES)

  def test_horizon_is_unbroken_and_wider(self):
    """The horizon is one continuous line, longer than a climb bar."""
    self._render(FakeSubMaster(pitch=0.0))

    horizon = [c for c in self.line.call_args_list if c[0][3] is HORIZON_COLOR]
    self.assertEqual(len(horizon), 1)

    horizon_width = abs(horizon[0][0][1].x - horizon[0][0][0].x)
    others = [abs(c[0][1].x - c[0][0].x) for c in self.line.call_args_list
              if c[0][3] is not HORIZON_COLOR and abs(c[0][0].y - c[0][1].y) < 1e-6]
    self.assertGreater(horizon_width, max(others))

  def test_bars_are_labelled_but_the_horizon_is_not(self):
    self._render(FakeSubMaster(pitch=0.0))

    labels = sorted(call[0][1] for call in self.text.call_args_list)
    self.assertEqual(labels, ['10', '10', '15', '15', '5', '5'])

  def test_roll_tilts_the_ladder(self):
    """Rolling makes the horizon bar's two ends sit at different heights."""
    self._render(FakeSubMaster(pitch=0.0, roll=0.0))
    flat = [c for c in self.line.call_args_list if c[0][3] is HORIZON_COLOR][0]
    self.assertAlmostEqual(flat[0][0].y, flat[0][1].y, places=3)

    self.line.reset_mock()
    self._render(FakeSubMaster(pitch=0.0, roll=math.radians(10.0)))
    rolled = [c for c in self.line.call_args_list if c[0][3] is HORIZON_COLOR][0]
    self.assertGreater(abs(rolled[0][0].y - rolled[0][1].y), 50.0)

  def test_centre_gap_is_clear_for_the_boresight(self):
    """Climb and dive bars stop short of the middle, where the FPV sits."""
    self._render(FakeSubMaster(pitch=0.0))

    horizon_y = self._horizon_y()
    for call in self.line.call_args_list:
      start, end = call[0][0], call[0][1]
      if abs(start.y - horizon_y) < 1e-6:
        continue
      self.assertFalse(min(start.x, end.x) < CX < max(start.x, end.x),
                       "a non-horizon bar crossed the boresight")

  def test_nothing_drawn_when_projected_far_off_screen(self):
    self._render(FakeSubMaster(pitch=0.0), rect=rl.Rectangle(0, 0, 10, 10))

    self.line.assert_not_called()

  def test_bars_and_labels_actually_consult_the_fade(self):
    """The wiring, not the curve.

    Every other fade test exercises the pure functions, so all of them would keep
    passing if the fade were never called from the draw path — which is the way
    this feature would really break. Forcing the scale to zero must silence the
    whole ladder.
    """
    with mock.patch.object(pl, 'fade_scale', return_value=0.0):
      self._render(FakeSubMaster(pitch=0.0))

    self.line.assert_not_called()
    self.text.assert_not_called()

  def test_a_partial_fade_dims_what_is_drawn(self):
    with mock.patch.object(pl, 'fade_scale', return_value=0.5):
      self._render(FakeSubMaster(pitch=0.0))

    self.assertTrue(self.line.called)
    for call in self.line.call_args_list:
      color = call[0][3]
      self.assertIn(color.a, (int(COLOR.a * 0.5), int(HORIZON_COLOR.a * 0.5)))


class TestLadderFade(unittest.TestCase):
  """The ladder fades where the annunciator row and the heading tape live.

  On the road its bars swept up behind the top row and the text sat on a green
  bar. These pin the fade curve itself, which is the part that decides whether
  anything pops on and off at a boundary.
  """
  RECT = rl.Rectangle(0, 0, 2160, 1080)

  def setUp(self):
    self.ui_state = FakeUIState(dm_annunciator=True, aircraft_tapes=True)
    patcher = mock.patch.object(pl, 'ui_state', self.ui_state)
    patcher.start()
    self.addCleanup(patcher.stop)

  def test_clear_of_both_bands_is_full_strength(self):
    self.assertEqual(pl.fade_scale(self.RECT.height / 2, self.RECT), 1.0)

  def test_inside_the_top_band_is_invisible(self):
    top, _ = pl.band_edges(self.RECT)

    self.assertEqual(pl.fade_scale(top - 1.0, self.RECT), 0.0)
    self.assertEqual(pl.fade_scale(self.RECT.y, self.RECT), 0.0)

  def test_inside_the_bottom_band_is_invisible(self):
    _, bottom = pl.band_edges(self.RECT)

    self.assertEqual(pl.fade_scale(bottom + 1.0, self.RECT), 0.0)
    self.assertEqual(pl.fade_scale(self.RECT.y + self.RECT.height, self.RECT), 0.0)

  def test_the_fade_is_gradual_not_a_step(self):
    """The whole point of fading rather than clipping."""
    top, _ = pl.band_edges(self.RECT)
    half = pl.fade_scale(top + pl.FADE_MARGIN / 2, self.RECT)

    self.assertAlmostEqual(half, 0.5, delta=0.05)
    self.assertEqual(pl.fade_scale(top + pl.FADE_MARGIN, self.RECT), 1.0)

  def test_the_top_band_sits_below_the_annunciator_row(self):
    """It must clear the legend boxes, which is what it was colliding with."""
    top, _ = pl.band_edges(self.RECT)

    self.assertGreaterEqual(top, self.RECT.y + pl.dma.TOP_MARGIN + pl.dma.TEXT_SIZE)

  def test_a_band_nobody_occupies_does_not_fade_the_ladder(self):
    """Both rows off: the ladder must be exactly as bright as before this change."""
    self.ui_state.dm_annunciator = False
    self.ui_state.aircraft_tapes = False

    for y in (self.RECT.y, self.RECT.height / 2, self.RECT.y + self.RECT.height):
      self.assertEqual(pl.fade_scale(y, self.RECT), 1.0, f"faded at y={y} with nothing there")

  def test_full_strength_returns_the_module_colour_itself(self):
    """No allocation per draw in the clear, and identity comparisons still hold."""
    self.assertIs(pl.faded(pl.COLOR, 1.0), pl.COLOR)

  def test_fading_dims_alpha_and_keeps_the_hue(self):
    dim = pl.faded(pl.COLOR, 0.25)

    self.assertEqual((dim.r, dim.g, dim.b), (pl.COLOR.r, pl.COLOR.g, pl.COLOR.b))
    self.assertEqual(dim.a, int(pl.COLOR.a * 0.25))


if __name__ == '__main__':
  unittest.main()
