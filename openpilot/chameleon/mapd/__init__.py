"""
Offline OSM map data for chameleonpilot, built on pfeiferj's mapd.

The Go binary (https://github.com/pfeiferj/openpilot-mapd) reads a position
out of the memory params, looks up the current way in its downloaded OSM
extracts, and writes speed limit / road name back into the memory params. The
fork's manager daemon (manager.py) feeds it position from gpsLocation and
republishes its output as the liveMapData cereal service at 1 Hz.

Differences from sunnypilot's integration, all deliberate:
- The binary is DOWNLOADED at first run and verified against a pinned SHA-256
  (GitHub's own release digest, checked 2026.07.29) — sunnypilot vendors a
  9.4 MB unverifiable blob in-repo and re-downloads with no checksum.
- It installs under the map-data root, not inside the repo checkout, so the
  working tree stays clean.
- Position comes straight from gpsLocation. sunnypilot feeds it from
  liveLocationKalman, which needs their extra locationd_llk daemon and does
  not exist on upstream master at all.
"""
import os

from openpilot.common.hardware import TICI
from openpilot.common.hardware.hw import Paths

MAPD_ROOT = "/data/media/0/osm" if TICI else os.path.join(Paths.comma_home(), "media", "0", "osm")
MAPD_BIN = os.path.join(MAPD_ROOT, "bin", "mapd")
OFFLINE_DIR = os.path.join(MAPD_ROOT, "offline")
MEM_PARAMS_PATH = "/dev/shm/params"

VERSION = "v1.12.0"
# GitHub's release-asset digest for this exact version; the installer refuses anything else
SHA256 = "fdb3b49ee19956e6ce09fdc3373cbba557f1263b2180e9f344c1d4053852284b"
URL = f"https://github.com/pfeiferj/openpilot-mapd/releases/download/{VERSION}/mapd"
