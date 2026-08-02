import unittest
from types import SimpleNamespace
from unittest import mock

import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad.aircraft import tapes as tp
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.tapes import MIN_HEADING_SPEED, AircraftTapes, VerticalTape, angle_diff

SCREEN = rl.Rectangle(0, 0, 2160, 1080)


class FakeFont:
  pass


def fake_car_state(v_ego=25.0, v_cluster=0.0, v_cruise=0.0):
  return SimpleNamespace(vEgo=v_ego, vEgoCluster=v_cluster, vCruiseCluster=v_cruise)


def fake_gps(has_fix=True, altitude=100.0, bearing=90.0):
  return SimpleNamespace(hasFix=has_fix, altitude=altitude, bearingDeg=bearing,
                         latitude=47.6, longitude=-122.3)


def fake_live_map(limit=0.0, valid=False):
  return SimpleNamespace(speedLimit=limit, speedLimitValid=valid)


class FakeSubMaster(dict):
  def __init__(self, car=None, gps=None, gps_updated=True, recv_frame=10, live=None, live_frame=10):
    super().__init__(carState=car or fake_car_state(), gpsLocation=gps or fake_gps(),
                     controlsState=SimpleNamespace(deprecated=SimpleNamespace(vCruise=0.0)),
                     liveMapData=live or fake_live_map())
    self.updated = {'gpsLocation': gps_updated}
    self.recv_frame = {'carState': recv_frame, 'liveMapData': live_frame}


class FakeUIState:
  def __init__(self, enabled=True, metric=False):
    self.aircraft_tapes = enabled
    self.is_metric = metric
    self.started_frame = 1


class TapesTestCase(unittest.TestCase):
  def setUp(self):
    self._patch(mock.patch.object(tp.gui_app, 'font', return_value=FakeFont()))
    self.line = self._patch(mock.patch.object(tp.rl, 'draw_line_ex'))
    self.text = self._patch(mock.patch.object(tp.rl, 'draw_text_ex'))
    self._patch(mock.patch.object(tp.rl, 'draw_rectangle_rec'))
    self._patch(mock.patch.object(tp.rl, 'draw_rectangle_lines_ex'))
    # every raylib draw call the tapes make has to be stubbed here, not in the
    # subclass that happens to exercise it: reaching a real one without a GL
    # context segfaults the whole run, taking the other 245 tests with it
    self.triangle = self._patch(mock.patch.object(tp.rl, 'draw_triangle'))
    self._patch(mock.patch.object(tp, 'measure_text_cached', return_value=rl.Vector2(60, 40)))
    self.ui_state = FakeUIState()
    self._patch(mock.patch.object(tp, 'ui_state', self.ui_state))
    self.tapes = AircraftTapes()

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def _texts(self):
    return [c[0][1] for c in self.text.call_args_list]

  def test_no_draw_when_disabled(self):
    self.ui_state.aircraft_tapes = False
    self.tapes.render(SCREEN, FakeSubMaster())

    self.line.assert_not_called()

  def test_speed_readout_in_mph(self):
    self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_ego=13.4)))

    self.assertIn("30", self._texts())  # 13.4 m/s = 30 mph

  def test_speed_uses_the_cluster_latch(self):
    """Once the car reports a cluster speed, the tape reads what the dash reads."""
    self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cluster=14.0)))
    self.assertIn("31", self._texts())  # cluster wins: 14.0 m/s = 31 mph

    # cluster momentarily zero: the latch holds, vEgo is not used again
    self.text.reset_mock()
    self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cluster=0.0)))
    self.assertIn("0", self._texts())

  def test_altitude_hidden_until_first_fix(self):
    self.tapes.render(SCREEN, FakeSubMaster(gps=fake_gps(has_fix=False)))

    self.assertNotIn("328", self._texts())  # 100 m = 328 ft never drawn

  def test_altitude_snaps_on_first_fix_then_holds(self):
    self.tapes.render(SCREEN, FakeSubMaster(gps=fake_gps(altitude=100.0)))
    self.assertIn("328", self._texts())  # 100 m = 328 ft, no glide up from zero

    # fix lost: the tape keeps drawing the last altitude
    self.text.reset_mock()
    self.tapes.render(SCREEN, FakeSubMaster(gps=fake_gps(has_fix=False), gps_updated=False))
    self.assertIn("328", self._texts())

  def test_altitude_metric(self):
    self.ui_state.is_metric = True
    self.tapes.render(SCREEN, FakeSubMaster(gps=fake_gps(altitude=100.0)))

    self.assertIn("100", self._texts())

  def test_heading_readout_and_cardinal(self):
    self.tapes.render(SCREEN, FakeSubMaster(gps=fake_gps(bearing=90.0)))

    texts = self._texts()
    self.assertIn("090", texts)
    self.assertIn("E", texts)

  def test_heading_hidden_below_walking_pace(self):
    self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_ego=MIN_HEADING_SPEED - 0.5),
                                            gps=fake_gps(bearing=90.0)))

    self.assertNotIn("090", self._texts())

  def test_heading_wraps_at_north(self):
    """At 358 degrees the tape must show ticks on both sides of north."""
    self.tapes.render(SCREEN, FakeSubMaster(gps=fake_gps(bearing=358.0)))

    texts = self._texts()
    self.assertIn("358", texts)
    self.assertIn("N", texts)   # 0/360 within the +/-60 view
    self.assertIn("330", texts)

  def test_angle_diff_shortest_arc(self):
    self.assertAlmostEqual(angle_diff(10.0, 350.0), 20.0)
    self.assertAlmostEqual(angle_diff(350.0, 10.0), -20.0)
    self.assertAlmostEqual(angle_diff(180.0, 0.0), -180.0)


class TestSpeedBugs(TapesTestCase):
  """The two carets on the speed tape: cruise setpoint (magenta) and posted
  speed limit (white), pinned to the tape end when off-scale.

  Both are solid now and told apart by colour — a hollow green caret on green
  ticks was the one you could not see. The carets are matched by *identity*
  against the module colours: rl.Color is a cffi struct, so two structurally
  equal colours are not `==`, and the constant travels through unchanged.
  """

  def _carets(self, color):
    return [c for c in self.triangle.call_args_list if c.args[3] is color]

  def _colors_in_order(self):
    return [c.args[3] for c in self.triangle.call_args_list]

  def test_no_bugs_by_default(self):
    self.tapes.render(SCREEN, FakeSubMaster())

    self.triangle.assert_not_called()

  def test_cruise_bug_at_the_set_speed(self):
    # 13.4 m/s = 30 mph shown; cruise 56 km/h = ~35 mph -> 5 units above centre
    sm = FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cruise=56.0))
    self.tapes.render(SCREEN, sm)

    carets = self._carets(tp.SET_COLOR)
    self.assertEqual(len(carets), 1)
    apex = carets[0].args[0]
    cy = SCREEN.height / 2
    expected = cy - (56.0 * tp.CV.KPH_TO_MPH - 30.0) * (tp.TAPE_HEIGHT / 20.0)
    self.assertAlmostEqual(apex.y, expected, delta=1.5)

  def test_cruise_sentinels_draw_nothing(self):
    for sentinel in (0.0, 255.0):
      self.triangle.reset_mock()
      self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_cruise=sentinel)))
      self.triangle.assert_not_called()

  def test_speed_limit_bug_is_white(self):
    sm = FakeSubMaster(car=fake_car_state(v_ego=13.4), live=fake_live_map(limit=11.176, valid=True))
    self.tapes.render(SCREEN, sm)

    carets = self._carets(tp.LIMIT_COLOR)
    self.assertEqual(len(carets), 1)
    self.assertEqual(self._carets(tp.SET_COLOR), [])
    apex = carets[0].args[0]
    expected = SCREEN.height / 2 - (25.0 - 30.0) * (tp.TAPE_HEIGHT / 20.0)  # 11.176 m/s = 25 mph
    self.assertAlmostEqual(apex.y, expected, delta=1.5)

  def test_every_bug_gets_a_dark_backing_first(self):
    """The backing is what makes a bug legible over a tick or a label."""
    sm = FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cruise=56.0), live=fake_live_map(limit=11.176, valid=True))
    self.tapes.render(SCREEN, sm)

    colors = self._colors_in_order()
    self.assertEqual(len(self._carets(tp.BUG_BACKING)), 2)
    # backing, colour, backing, colour — each bug's own backing immediately under it
    self.assertEqual(colors, [tp.BUG_BACKING, tp.LIMIT_COLOR, tp.BUG_BACKING, tp.SET_COLOR])

  def test_backing_is_larger_than_the_bug(self):
    sm = FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cruise=56.0))
    self.tapes.render(SCREEN, sm)

    def height(call):
      return abs(call.args[1].y - call.args[2].y)

    self.assertGreater(height(self._carets(tp.BUG_BACKING)[0]), height(self._carets(tp.SET_COLOR)[0]))

  def test_setpoint_draws_over_the_limit(self):
    """They coincide exactly when cruising at the posted limit; the setpoint is
    the actionable one, so it goes down last."""
    sm = FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cruise=56.0), live=fake_live_map(limit=11.176, valid=True))
    self.tapes.render(SCREEN, sm)

    colors = self._colors_in_order()
    self.assertLess(colors.index(tp.LIMIT_COLOR), colors.index(tp.SET_COLOR))

  def test_invalid_speed_limit_draws_nothing(self):
    sm = FakeSubMaster(live=fake_live_map(limit=11.176, valid=False))
    self.tapes.render(SCREEN, sm)

    self.assertEqual(self._carets(tp.LIMIT_COLOR), [])

  def test_off_scale_bug_pins_to_the_tape_end(self):
    # 30 mph shown, cruise 129 km/h = ~80 mph: far beyond the +/-10 view
    sm = FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cruise=129.0))
    self.tapes.render(SCREEN, sm)

    apex = self._carets(tp.SET_COLOR)[0].args[0]
    self.assertAlmostEqual(apex.y, SCREEN.height / 2 - tp.TAPE_HEIGHT / 2, delta=0.1)


class TestSetSpeedTag(TapesTestCase):
  """The fixed "SET nn" readout above the speed tape.

  The caret alone cannot say what the cruise is set to once the value leaves the
  20-unit window, which is the whole reason the tag exists.
  """

  def test_tag_shows_the_set_speed(self):
    # cruise 56 km/h = 34.8 mph -> 35
    self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cruise=56.0)))

    self.assertIn("SET 35", self._texts())

  def test_tag_is_metric_when_the_ui_is(self):
    self.ui_state.is_metric = True
    self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cruise=56.0)))

    self.assertIn("SET 56", self._texts())

  def test_no_tag_without_a_setpoint(self):
    for sentinel in (0.0, 255.0):
      self.text.reset_mock()
      self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_cruise=sentinel)))
      self.assertNotIn("SET 0", self._texts())
      self.assertFalse([t for t in self._texts() if t.startswith("SET")])

  def test_tag_still_reads_when_the_bug_is_off_scale(self):
    """The pinned caret cannot show the value; this is the number that can."""
    self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cruise=129.0)))

    self.assertIn("SET 80", self._texts())

  def test_tag_sits_clear_above_the_tape(self):
    self.tapes.render(SCREEN, FakeSubMaster(car=fake_car_state(v_ego=13.4, v_cruise=56.0)))

    tag = [c for c in self.text.call_args_list if c[0][1] == "SET 35"][0]
    top, height = tag[0][2].y, 40.0  # the faked measure_text_cached height
    tape_top = SCREEN.height / 2 - tp.TAPE_HEIGHT / 2
    self.assertLessEqual(top + height, tape_top, "the tag overlaps the top of the tape")


class TestTapeLabelGeometry(TapesTestCase):
  """A tick label must stay beyond the far end of its own tick.

  It did not: the measure.x offset sat on the wrong branch, so on the speed
  tape the number's right edge was pinned past the tick and the text ran
  backwards over the tick and into the boxed readout at the index line —
  visible on the road as the number and the tick overlapping. The altitude
  tape had the mirror-image fault.
  """
  MAJOR_TICK = tp.TICK * 1.6

  def _label_spans(self):
    # tick labels only, by font size — the boxed readout at the index line is
    # drawn through the same call at VALUE_SIZE and is what they must clear.
    # fake measure_text_cached gives every label a width of 60
    return [(c[0][2].x, c[0][2].x + 60) for c in self.text.call_args_list if c[0][3] == tp.LABEL_SIZE]

  def _draw(self, ticks_on_right):
    tape = VerticalTape(FakeFont(), ticks_on_right=ticks_on_right, minor_step=5.0, major_step=10.0,
                        px_per_unit=tp.TAPE_HEIGHT / 20.0)  # the shipping speed-tape scale
    tape.draw(0.0, 500.0, 30.0)
    self.assertTrue(self._label_spans(), "no tick labels drawn")

  def test_right_side_labels_clear_the_ticks_and_the_readout(self):
    self._draw(ticks_on_right=True)

    edge = tp.TAPE_WIDTH  # drawn at x = 0
    for left, _ in self._label_spans():
      self.assertGreaterEqual(left, edge + self.MAJOR_TICK,
                              "label runs back over the tick into the readout box")

  def test_left_side_labels_clear_the_ticks_and_the_readout(self):
    self._draw(ticks_on_right=False)

    edge = 0.0  # drawn at x = 0, ticks grow leftward
    for _, right in self._label_spans():
      self.assertLessEqual(right, edge - self.MAJOR_TICK,
                           "label runs back over the tick into the readout box")


if __name__ == '__main__':
  unittest.main()
