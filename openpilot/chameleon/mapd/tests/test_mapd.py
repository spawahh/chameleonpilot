"""The mapd manager and installer.

The two things that must never regress: a download whose hash doesn't match
the pinned release digest can never become an executable, and every
degraded state (no binary, no fix, no data) publishes quiet zeros instead of
crashing or going silent.
"""
import hashlib
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from openpilot.chameleon.mapd import SHA256, VERSION
from openpilot.chameleon.mapd import installer as installer_mod
from openpilot.chameleon.mapd.manager import MapdManager, haversine_m


# the declared types from params_keys.h for every key mapd touches — the fake
# must deserialize/enforce exactly like the real Params or it hides type bugs
# (an untyped fake is how the 2026.07.29 on-road TypeError got through)
KEY_TYPES = {
  "LastGPSPosition": str,
  "MapSpeedLimit": float,
  "MapdVersion": str,
  "NextMapSpeedLimit": dict,
  "OSMDownloadBounds": str,
  "OSMDownloadLocations": dict,
  "OSMDownloadProgress": dict,
  "OsmDbUpdatesCheck": bool,
  "OsmLocationName": str,
  "OsmStateName": str,
  "RoadName": str,
}


class FakeParams:
  """Stores serialized strings like the on-disk params, deserializes on get()
  and type-checks on put(), mirroring common/params.py's CPP_2_PYTHON /
  PYTHON_2_CPP behaviour for the key types mapd uses."""

  def __init__(self, values=None):
    self.values = dict(values or {})  # serialized, as the files hold them

  def get(self, key, return_default=False):
    raw = self.values.get(key)
    if raw is None:
      return None
    t = KEY_TYPES[key]
    try:
      if t is float:
        return float(raw)
      if t is dict:
        return json.loads(raw)
      if t is bool:
        return raw == "1"
      return raw
    except (TypeError, ValueError):
      return None  # the real Params falls back to the default (None here)

  def get_bool(self, key):
    return self.values.get(key) == "1"

  def put(self, key, value, block=False):
    t = KEY_TYPES[key]
    if t is dict and isinstance(value, (dict, list)):
      self.values[key] = json.dumps(value)
    elif t is float and isinstance(value, float):
      self.values[key] = str(value)
    elif t is str and isinstance(value, str):
      self.values[key] = value
    else:
      raise TypeError(f"Type mismatch while writing param {key}: {type(value)=} {value=}")

  def put_bool(self, key, value, block=False):
    self.values[key] = "1" if value else "0"


class FakeSubMaster(dict):
  def __init__(self, gps=None):
    super().__init__(gpsLocation=gps or SimpleNamespace(hasFix=False, latitude=0.0, longitude=0.0, bearingDeg=0.0))
    self.updated = {'gpsLocation': gps is not None}

  def update(self, timeout=0):
    pass


class FakePubMaster:
  def __init__(self):
    self.sent = []

  def send(self, service, msg):
    self.sent.append((service, msg))


def make_manager(params=None, mem=None, gps=None):
  return MapdManager(params=params or FakeParams(), mem_params=mem or FakeParams(),
                     sm=FakeSubMaster(gps), pm=FakePubMaster())


class TestInstaller(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    self.bin_path = os.path.join(self.tmp, "bin", "mapd")
    self._patch(mock.patch.object(installer_mod, 'MAPD_BIN', self.bin_path))
    self._patch(mock.patch.object(installer_mod, 'OFFLINE_DIR', os.path.join(self.tmp, "offline")))

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def _response(self, content):
    return SimpleNamespace(raise_for_status=lambda: None,
                           iter_content=lambda chunk_size: [content])

  def test_wrong_hash_never_installs(self):
    """A tampered or truncated download must not become an executable."""
    self._patch(mock.patch.object(installer_mod.requests, 'get', return_value=self._response(b"evil")))
    params = FakeParams()

    self.assertFalse(installer_mod.download_and_install(params))

    self.assertFalse(os.path.exists(self.bin_path))
    self.assertFalse(os.path.exists(self.bin_path + ".tmp"))
    self.assertIsNone(params.values.get("MapdVersion"))

  def test_matching_hash_installs_atomically(self):
    content = b"pretend go binary"
    self._patch(mock.patch.object(installer_mod, 'SHA256', hashlib.sha256(content).hexdigest()))
    self._patch(mock.patch.object(installer_mod.requests, 'get', return_value=self._response(content)))
    params = FakeParams()

    self.assertTrue(installer_mod.download_and_install(params))

    with open(self.bin_path, "rb") as f:
      self.assertEqual(f.read(), content)
    self.assertTrue(os.access(self.bin_path, os.X_OK))
    self.assertEqual(params.values["MapdVersion"], VERSION)

  def test_network_failure_is_quiet(self):
    self._patch(mock.patch.object(installer_mod.requests, 'get',
                                  side_effect=installer_mod.requests.RequestException("offline")))

    self.assertFalse(installer_mod.download_and_install(FakeParams()))

  def test_install_needed_tracks_version(self):
    params = FakeParams({"MapdVersion": VERSION})
    with mock.patch.object(installer_mod.os.path, 'isfile', return_value=True):
      self.assertFalse(installer_mod.install_needed(params))

    params.values["MapdVersion"] = "v0.0.1"
    with mock.patch.object(installer_mod.os.path, 'isfile', return_value=True):
      self.assertTrue(installer_mod.install_needed(params))

  def test_pinned_hash_is_the_release_digest(self):
    """Guard against someone 'temporarily' blanking the pin."""
    self.assertEqual(len(SHA256), 64)
    int(SHA256, 16)  # raises if not hex


class TestManagerPublish(unittest.TestCase):
  def _sent(self, manager):
    manager.publish()
    self.assertEqual(len(manager.pm.sent), 1)
    return manager.pm.sent[0][1].liveMapData, manager.pm.sent[0][1]

  def test_no_data_publishes_quiet_zeros(self):
    live, msg = self._sent(make_manager())

    self.assertFalse(msg.valid)
    self.assertFalse(live.speedLimitValid)
    self.assertEqual(live.speedLimit, 0.0)
    self.assertEqual(live.roadName, "")

  def test_map_answers_flow_through(self):
    mem = FakeParams({"MapSpeedLimit": "13.4", "RoadName": "NE 45th St",
                      "NextMapSpeedLimit": json.dumps({"speedlimit": 20.1, "latitude": 47.66, "longitude": -122.3})})
    manager = make_manager(mem=mem)
    manager._last_position = (47.65, -122.3)

    live, msg = self._sent(manager)

    self.assertTrue(msg.valid)
    self.assertTrue(live.speedLimitValid)
    self.assertAlmostEqual(live.speedLimit, 13.4, places=3)
    self.assertEqual(live.roadName, "NE 45th St")
    self.assertTrue(live.speedLimitAheadValid)
    self.assertAlmostEqual(live.speedLimitAhead, 20.1, places=3)
    # ~1.11 km per 0.01 deg of latitude
    self.assertAlmostEqual(live.speedLimitAheadDistance, 1112, delta=15)

  def test_garbage_limits_are_invalid(self):
    for garbage in ("999", "-5", "not a number"):
      manager = make_manager(mem=FakeParams({"MapSpeedLimit": garbage}))
      live, _ = self._sent(manager)
      self.assertFalse(live.speedLimitValid, garbage)

  def test_null_next_limit_fields_are_quiet(self):
    """The Go binary's JSON can carry nulls; float(None) must not kill the daemon."""
    mem = FakeParams({"NextMapSpeedLimit": json.dumps({"speedlimit": None, "latitude": None, "longitude": None})})
    live, _ = self._sent(make_manager(mem=mem))
    self.assertFalse(live.speedLimitAheadValid)

  def test_non_dict_json_is_quiet(self):
    for garbage in ("[1, 2]", '"just a string"', "not json at all"):
      manager = make_manager(mem=FakeParams({"NextMapSpeedLimit": garbage}))
      live, _ = self._sent(manager)
      self.assertFalse(live.speedLimitAheadValid, garbage)


class TestManagerInputs(unittest.TestCase):
  def test_position_written_only_with_a_fix(self):
    gps = SimpleNamespace(hasFix=False, latitude=47.6, longitude=-122.3, bearingDeg=90.0)
    manager = make_manager(gps=gps)
    manager.update_position()
    self.assertIsNone(manager._last_position)

    gps.hasFix = True
    manager.update_position()

    self.assertEqual(manager._last_position, (47.6, -122.3))
    written = json.loads(manager.mem_params.values["LastGPSPosition"])
    self.assertEqual(written["bearing"], 90.0)

  def test_state_download_request(self):
    params = FakeParams({"OsmDbUpdatesCheck": "1", "OsmLocationName": "US", "OsmStateName": "Washington"})
    manager = make_manager(params=params)

    manager.update_download_request()

    locations = json.loads(manager.mem_params.values["OSMDownloadLocations"])
    self.assertEqual(locations, {"nations": [], "states": ["Washington"]})
    self.assertFalse(params.get_bool("OsmDbUpdatesCheck"))

  def test_all_states_downloads_the_nation(self):
    params = FakeParams({"OsmDbUpdatesCheck": "1", "OsmLocationName": "US", "OsmStateName": "All"})
    manager = make_manager(params=params)

    manager.update_download_request()

    locations = json.loads(manager.mem_params.values["OSMDownloadLocations"])
    self.assertEqual(locations, {"nations": ["US"], "states": []})

  def test_a_bad_tick_never_raises(self):
    """One uncaught exception once left the daemon dead for a whole drive and
    blocked engagement. step() must swallow, log, and carry on."""
    manager = make_manager()
    with mock.patch('openpilot.chameleon.mapd.manager.install_needed', return_value=False), \
         mock.patch.object(manager, 'publish', side_effect=RuntimeError("boom")), \
         mock.patch('openpilot.chameleon.mapd.manager.cloudlog') as log:
      manager.step()  # must not raise
    log.exception.assert_called_once()

  def test_failed_install_backs_off(self):
    manager = make_manager()
    with mock.patch("openpilot.chameleon.mapd.manager.install_needed", return_value=True), \
         mock.patch("openpilot.chameleon.mapd.manager.download_and_install", return_value=False) as dl:
      for _ in range(30):
        manager.maybe_install()

    dl.assert_called_once()  # the rest of the ticks sat out the cooldown


class TestHaversine(unittest.TestCase):
  def test_known_distance(self):
    # Seattle to Portland is ~233 km
    self.assertAlmostEqual(haversine_m(47.6062, -122.3321, 45.5152, -122.6784), 233000, delta=3000)


if __name__ == '__main__':
  unittest.main()
