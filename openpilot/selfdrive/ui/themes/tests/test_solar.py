"""The solar schedule and its combine with the ambient night trigger.

The observed bug this guards against: a bright streetlight at 2 a.m. reading
as daylight to the camera and flipping the day palette back on. The combine is
asymmetric by design — solar-night forces night regardless of ambient, while
solar-day leaves the ambient hysteresis in charge so a tunnel still darkens.
"""
import unittest
from datetime import UTC, datetime

from openpilot.selfdrive.ui import themes
from openpilot.selfdrive.ui.themes.solar import NIGHT_SOLAR_ELEVATION_DEG, SolarSchedule, solar_elevation

SEATTLE = (47.6, -122.3)


class FakeParams:
  def __init__(self, values=None):
    self.values = dict(values or {})
    self.puts = []

  def get(self, key, return_default=False):
    return self.values.get(key)

  def put(self, key, value, block=False):
    self.values[key] = value
    self.puts.append((key, value))


class TestSolarElevation(unittest.TestCase):
  def test_summer_solstice_noon_is_high(self):
    # 2026-06-21 ~13:00 PDT = 20:00 UTC, solar noon-ish in Seattle
    when = datetime(2026, 6, 21, 20, 0, tzinfo=UTC)
    self.assertGreater(solar_elevation(*SEATTLE, when), 60.0)

  def test_summer_midnight_is_below_horizon(self):
    when = datetime(2026, 6, 21, 9, 0, tzinfo=UTC)  # ~2am PDT
    self.assertLess(solar_elevation(*SEATTLE, when), NIGHT_SOLAR_ELEVATION_DEG)

  def test_winter_noon_is_low_but_daylight(self):
    when = datetime(2026, 12, 21, 20, 0, tzinfo=UTC)  # ~noon PST
    elevation = solar_elevation(*SEATTLE, when)
    self.assertGreater(elevation, 10.0)
    self.assertLess(elevation, 25.0)

  def test_civil_dusk_sits_between_day_and_night(self):
    # summer evening in Seattle: 21:30 PDT (04:30 UTC next day) is dusk —
    # sun below the horizon but not yet civil-night
    when = datetime(2026, 6, 22, 4, 45, tzinfo=UTC)
    elevation = solar_elevation(*SEATTLE, when)
    self.assertLess(elevation, 0.0)
    self.assertGreater(elevation, -10.0)


class TestSolarSchedule(unittest.TestCase):
  def test_blind_without_position(self):
    self.assertIsNone(SolarSchedule().is_dark())

  def test_dark_at_night_light_at_noon(self):
    schedule = SolarSchedule()
    schedule.update_position(*SEATTLE)

    self.assertTrue(schedule.is_dark(datetime(2026, 6, 21, 9, 0, tzinfo=UTC)))
    self.assertFalse(schedule.is_dark(datetime(2026, 6, 21, 20, 0, tzinfo=UTC)))

  def test_position_persists_once_per_session(self):
    params = FakeParams()
    schedule = SolarSchedule()

    schedule.update_position(*SEATTLE, params=params)
    schedule.update_position(48.0, -123.0, params=params)

    self.assertEqual(len(params.puts), 1)

  def test_load_round_trip(self):
    params = FakeParams()
    SolarSchedule().update_position(*SEATTLE, params=params)

    loaded = SolarSchedule()
    loaded.load(params)

    self.assertAlmostEqual(loaded.latitude, SEATTLE[0])
    self.assertAlmostEqual(loaded.longitude, SEATTLE[1])

  def test_garbage_cache_starts_blind(self):
    params = FakeParams({"LastGPSPosition": "not json"})
    schedule = SolarSchedule()
    schedule.load(params)

    self.assertIsNone(schedule.is_dark())


class TestAsymmetricCombine(unittest.TestCase):
  """Solar sets the baseline; ambient may only darken, never brighten."""

  def test_solar_night_forces_night_despite_bright_ambient(self):
    """The 2am streetlight: camera reads bright, palette must stay night."""
    r = themes._NightResolver()

    for i in range(100):
      r.tick(95.0, solar_dark=True, now=float(i))

    self.assertTrue(r.is_night)

  def test_solar_night_needs_no_dwell(self):
    r = themes._NightResolver()

    self.assertTrue(r.tick(95.0, solar_dark=True, now=0.0))

  def test_solar_day_leaves_ambient_in_charge(self):
    """A tunnel at noon can still go dark, via the normal hysteresis + dwell."""
    r = themes._NightResolver()

    r.tick(5.0, solar_dark=False, now=0.0)
    self.assertFalse(r.is_night)  # dwell not yet served
    r.tick(5.0, solar_dark=False, now=themes.NIGHT_DWELL_S)
    self.assertTrue(r.is_night)

  def test_dawn_hands_back_to_ambient(self):
    """When solar flips to day, bright ambient exits night through hysteresis."""
    r = themes._NightResolver()
    r.tick(95.0, solar_dark=True, now=0.0)
    self.assertTrue(r.is_night)

    r.tick(95.0, solar_dark=False, now=1.0)
    self.assertTrue(r.is_night)  # dwell not yet served
    r.tick(95.0, solar_dark=False, now=1.0 + themes.NIGHT_DWELL_S)
    self.assertFalse(r.is_night)

  def test_unknown_solar_is_ambient_only(self):
    r = themes._NightResolver()

    r.tick(5.0, solar_dark=None, now=0.0)
    r.tick(5.0, solar_dark=None, now=themes.NIGHT_DWELL_S)
    self.assertTrue(r.is_night)

  def test_manual_modes_ignore_solar(self):
    r = themes._NightResolver()
    r.set_mode("off")

    r.tick(5.0, solar_dark=True, now=0.0)

    self.assertFalse(r.is_night)


if __name__ == '__main__':
  unittest.main()
