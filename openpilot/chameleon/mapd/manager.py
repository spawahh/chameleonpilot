"""
The mapd manager daemon: feeds the Go binary, republishes its answers.

The Go mapd never touches msgq — it reads a position out of the memory params
and writes MapSpeedLimit / NextMapSpeedLimit / RoadName back. This daemon, at
1 Hz:
- installs the binary when missing or outdated (verified download; retried
  once a minute on failure, so a device without internet just idles),
- writes LastGPSPosition into the memory params from gpsLocation (the qcom
  GPS service the 3X actually publishes; hasFix-gated),
- forwards a region-download request from the settings panel to the Go binary
  (OsmDbUpdatesCheck -> OSMDownloadLocations),
- publishes liveMapData from the Go binary's outputs.

Everything degrades to quiet zeros: no binary, no fix, or no downloaded
region all mean liveMapData with speedLimitValid=False and an empty roadName.
"""
import json
import math
from typing import Any

import openpilot.cereal.messaging as messaging
from openpilot.chameleon.mapd import MEM_PARAMS_PATH
from openpilot.chameleon.mapd.installer import download_and_install, ensure_directories, install_needed
from openpilot.common.params import Params
from openpilot.common.realtime import Ratekeeper
from openpilot.common.swaglog import cloudlog

INSTALL_RETRY_TICKS = 60  # 1 Hz loop -> retry a failed install once a minute
MAX_SPEED_LIMIT_MS = 75.0  # ~270 km/h; above this the value is OSM garbage


def safe_float(value: Any) -> float:
  """Zero for anything that isn't a number — the Go binary's JSON can carry nulls."""
  try:
    return float(value) if value is not None else 0.0
  except (TypeError, ValueError):
    return 0.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
  r = 6371000.0
  p1, p2 = math.radians(lat1), math.radians(lat2)
  dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
  a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
  return 2 * r * math.asin(math.sqrt(a))


class MapdManager:
  def __init__(self, params: Params | None = None, mem_params: Params | None = None, sm=None, pm=None):
    self.params = params if params is not None else Params()
    self.mem_params = mem_params if mem_params is not None else Params(MEM_PARAMS_PATH)
    self.sm = sm if sm is not None else messaging.SubMaster(['gpsLocation'])
    self.pm = pm if pm is not None else messaging.PubMaster(['liveMapData'])

    self._install_cooldown = 0
    self._last_position: tuple[float, float] | None = None

    # the Go binary reads these keys at startup; seed them so it never sees a missing file
    self.mem_params.put("OSMDownloadBounds", self.params.get("OSMDownloadBounds") or "")
    self.mem_params.put("LastGPSPosition", "{}")

  def maybe_install(self) -> None:
    if not install_needed(self.params):
      return
    if self._install_cooldown > 0:
      self._install_cooldown -= 1
      return
    if not download_and_install(self.params):
      self._install_cooldown = INSTALL_RETRY_TICKS

  def update_position(self) -> None:
    if not self.sm.updated['gpsLocation']:
      return
    gps = self.sm['gpsLocation']
    if not gps.hasFix:
      return
    self._last_position = (gps.latitude, gps.longitude)
    self.mem_params.put("LastGPSPosition", json.dumps({
      "latitude": gps.latitude,
      "longitude": gps.longitude,
      "bearing": gps.bearingDeg,
    }))

  def update_download_request(self) -> None:
    """The settings panel sets OsmDbUpdatesCheck; hand the region to the Go binary."""
    if not self.params.get_bool("OsmDbUpdatesCheck"):
      return
    self.params.put_bool("OsmDbUpdatesCheck", False)

    nation = self.params.get("OsmLocationName", return_default=True) or "US"
    state = self.params.get("OsmStateName", return_default=True) or ""
    # a specific US state downloads just that state; "All" (or none) downloads the nation
    if nation == "US" and state and state != "All":
      locations = {"nations": [], "states": [state]}
    else:
      locations = {"nations": [nation], "states": []}

    # OSMDownloadLocations is JSON-typed: Params.put wants the dict itself, not a string.
    # A string here raises TypeError — the crash that killed this daemon on-road 2026.07.29.
    self.mem_params.put("OSMDownloadLocations", locations)
    cloudlog.info(f"chameleon mapd: requested OSM download {locations}")

  def publish(self) -> None:
    msg = messaging.new_message('liveMapData')
    msg.valid = self._last_position is not None
    live = msg.liveMapData

    speed_limit = self._mem_float("MapSpeedLimit")
    live.speedLimit = speed_limit
    live.speedLimitValid = bool(0.0 < speed_limit < MAX_SPEED_LIMIT_MS)
    live.roadName = self.mem_params.get("RoadName") or ""

    next_limit = self._mem_json("NextMapSpeedLimit")
    ahead = safe_float(next_limit.get("speedlimit"))
    live.speedLimitAhead = ahead
    live.speedLimitAheadValid = bool(0.0 < ahead < MAX_SPEED_LIMIT_MS)
    if live.speedLimitAheadValid and self._last_position is not None:
      live.speedLimitAheadDistance = haversine_m(*self._last_position,
                                                 safe_float(next_limit.get("latitude")),
                                                 safe_float(next_limit.get("longitude")))

    self.pm.send('liveMapData', msg)

  def _mem_float(self, key: str) -> float:
    return safe_float(self.mem_params.get(key))

  def _mem_json(self, key: str) -> dict:
    # JSON-typed keys come out of Params.get already parsed (dict), or None when
    # empty/garbage. Anything that isn't a dict — including a bare JSON list — is nothing.
    value = self.mem_params.get(key)
    return value if isinstance(value, dict) else {}

  def step(self) -> None:
    # display-only daemon: a bad tick is dropped and logged, never a crash loop.
    # An uncaught exception here once left the process dead for a whole drive.
    try:
      self.sm.update(0)
      self.maybe_install()
      self.update_position()
      self.update_download_request()
      self.publish()
    except Exception:
      cloudlog.exception("chameleon mapd: tick failed")


def main():
  ensure_directories()
  manager = MapdManager()
  rk = Ratekeeper(1, print_delay_threshold=None)
  while True:
    manager.step()
    rk.keep_time()


if __name__ == "__main__":
  main()
