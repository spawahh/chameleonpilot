"""
Solar schedule for night mode: is it actually night outside?

The ambient trigger alone has a known failure — a bright streetlight at 2 a.m.
reads as daylight to the camera and flips the day palette back on. Solar
elevation from a rough position and the clock is immune to that. Position
comes from `gpsLocation` while driving and is cached to the `LastGPSPosition`
param (which upstream registers but nothing currently writes) so the schedule
also works at startup, before the first fix. A theme switch does not need a
surveyor: anywhere within a few hundred km gives the same answer to "is it
night", so a stale cache is fine.

The elevation math is the standard NOAA approximation — pure arithmetic, no
dependencies, accurate to a fraction of a degree, which is far more than the
one threshold here needs.
"""
import json
import math
from datetime import UTC, datetime

from openpilot.common.swaglog import cloudlog

# Civil twilight: the sun more than 6 degrees below the horizon is night.
NIGHT_SOLAR_ELEVATION_DEG = -6.0

POSITION_PARAM = "LastGPSPosition"


def solar_elevation(latitude_deg: float, longitude_deg: float, when: datetime | None = None) -> float:
  """Sun elevation above the horizon in degrees, NOAA approximation, UTC in."""
  t = when if when is not None else datetime.now(UTC)
  hour = t.hour + t.minute / 60 + t.second / 3600
  gamma = 2 * math.pi / 365 * (t.timetuple().tm_yday - 1 + (hour - 12) / 24)

  eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                     - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
  decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
          - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
          - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))

  true_solar_minutes = hour * 60 + eqtime + 4 * longitude_deg  # UTC input, so no zone offset
  hour_angle = math.radians(true_solar_minutes / 4 - 180)

  lat = math.radians(latitude_deg)
  cos_zenith = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(hour_angle)
  return math.degrees(math.asin(max(-1.0, min(1.0, cos_zenith))))


class SolarSchedule:
  """Tracks a rough position and answers `is_dark()`; None while no position
  has ever been seen, so the caller can fall back to ambient-only."""

  def __init__(self):
    self.latitude: float | None = None
    self.longitude: float | None = None
    self._persisted = False

  def load(self, params) -> None:
    raw = params.get(POSITION_PARAM)
    if not raw:
      return
    try:
      pos = json.loads(raw)
      self.latitude, self.longitude = float(pos["latitude"]), float(pos["longitude"])
    except (ValueError, KeyError, TypeError):
      cloudlog.warning(f"unreadable {POSITION_PARAM}, solar schedule starts blind")

  def update_position(self, latitude: float, longitude: float, params=None) -> None:
    self.latitude, self.longitude = latitude, longitude
    # one persist per UI session is plenty — position accuracy is irrelevant here
    if params is not None and not self._persisted:
      params.put(POSITION_PARAM, json.dumps({"latitude": latitude, "longitude": longitude}))
      self._persisted = True

  def is_dark(self, when: datetime | None = None) -> bool | None:
    if self.latitude is None or self.longitude is None:
      return None
    return solar_elevation(self.latitude, self.longitude, when) < NIGHT_SOLAR_ELEVATION_DEG
