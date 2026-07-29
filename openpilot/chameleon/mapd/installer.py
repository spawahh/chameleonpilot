"""
Verified download of the pfeiferj mapd binary.

Refuses any download whose SHA-256 does not match the pinned release digest —
a wrong hash means the temp file is deleted and nothing is installed, so a
tampered or truncated download can never become an executable. The install is
atomic (write .tmp, fsync, rename), and MapdVersion records what is installed
so a version bump in the package constants triggers a fresh download.
"""
import hashlib
import os
from pathlib import Path

import requests

from openpilot.chameleon.mapd import MAPD_BIN, OFFLINE_DIR, SHA256, URL, VERSION
from openpilot.common.swaglog import cloudlog

# connect fast or fail; reads tolerate a slow device WiFi as long as bytes keep arriving
DOWNLOAD_TIMEOUT = (10, 120)
CHUNK_BYTES = 1 << 20


def ensure_directories() -> None:
  for d in (os.path.dirname(MAPD_BIN), OFFLINE_DIR):
    Path(d).mkdir(parents=True, exist_ok=True)


def install_needed(params) -> bool:
  return not os.path.isfile(MAPD_BIN) or params.get("MapdVersion") != VERSION


def download_and_install(params) -> bool:
  """One attempt: download, verify, atomically install. True on success."""
  ensure_directories()
  temp_path = Path(MAPD_BIN + ".tmp")
  try:
    response = requests.get(URL, timeout=DOWNLOAD_TIMEOUT, stream=True)
    response.raise_for_status()
    content = b"".join(response.iter_content(chunk_size=CHUNK_BYTES))

    digest = hashlib.sha256(content).hexdigest()
    if digest != SHA256:
      cloudlog.error(f"chameleon mapd: download hash mismatch ({digest}), refusing to install")
      return False

    with open(temp_path, "wb") as f:
      f.write(content)
      f.flush()
      os.fsync(f.fileno())
    os.chmod(temp_path, 0o755)
    temp_path.replace(MAPD_BIN)

    params.put("MapdVersion", VERSION)
    cloudlog.info(f"chameleon mapd: installed {VERSION}")
    return True
  except requests.RequestException as e:
    cloudlog.warning(f"chameleon mapd: download failed ({e}); will retry later")
    return False
  finally:
    temp_path.unlink(missing_ok=True)
