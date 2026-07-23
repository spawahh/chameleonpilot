---
name: openpilot-bounty-dev
description: >-
  Working on comma.ai openpilot bounties or the openpilot codebase in a fresh cloud
  container. Use whenever the task involves: setting up the openpilot repo/environment
  (submodules, uv, scons), running or writing car tests (test_models.py, test_car_interfaces),
  panda safety / opendbc fuzz testing (test_panda_safety_carstate_fuzzy,
  test_panda_safety_tx_fuzzy), the comma bounty board, or opening PRs against
  openpilot/opendbc. Trigger on "openpilot", "opendbc", "panda safety", "comma bounty",
  "test_models", or CAN-message fuzzing work in this repo.
---

# openpilot bounty development

Working knowledge for openpilot bounty work in an ephemeral container. The environment is
rebuilt every session — do the setup below first, in order. Repo layout note: the checkout
root contains an `openpilot/` python package dir plus `opendbc_repo/`, `panda/`, etc. as
git submodules.

## 1. Environment setup (fresh container)

Run from the repo root (`/home/user/openpilot` or equivalent):

```bash
# 1. Submodules (uninitialized by default; remotes are reachable through the proxy)
git submodule update --init opendbc_repo msgq_repo panda rednose_repo teleoprtc_repo tinygrad_repo

# 2. Python deps. The repo pins Python 3.12.x via .python-version; uv's managed 3.12 is
#    usually absent, so point at the system interpreter. --all-extras is REQUIRED:
#    without it the comma-deps build packages (bzip2, acados, capnproto, ...) are missing
#    and scons dies at "ModuleNotFoundError: No module named 'bzip2'".
uv sync --frozen --python /usr/bin/python3.12 --all-extras
source .venv/bin/activate

# 3. Build. A raylib font-asset failure ("raylib failed to load font data") near the end
#    is IGNORABLE for car/safety test work — the needed artifacts are already built.
scons -j$(nproc)
```

Sanity check the two imports the car tests need:

```bash
python -c "from openpilot.selfdrive.pandad import can_capnp_to_list; \
from opendbc.safety.tests.libsafety import libsafety_py; libsafety_py.libsafety; print('ok')"
```

`libsafety` needs no scons — it self-compiles the opendbc safety C code with `cc` at first
import (so edits to `opendbc_repo/opendbc/safety/**` take effect in the *next* Python
process, no rebuild step).

## 2. Running the car tests

- Route CAN logs download from openpilotci on first run and are cached; first run per
  platform is slow, later runs are fast.
- `MAX_EXAMPLES` (env) drives hypothesis example counts (default 300).
- `NUM_JOBS` / `JOB_ID` shard platforms; GH CI runs `MAX_EXAMPLES=1 SKIP_SLOW=1` (the
  test_models classes are `SLOW_TEST`, so they're skipped in the smoke run); the full
  300-example fuzz runs in Jenkins via `openpilot/selfdrive/car/tests/big_cars_test.sh`
  against 300 internal segments.
- pytest `-k` matching is **case-insensitive against the whole test id including the file
  path** — `-k "not LF"` matches nothing because "lf" ⊂ "se**lf**drive". Use full platform
  substrings like `not SONATA_LF`.

```bash
# one platform
MAX_EXAMPLES=300 pytest openpilot/selfdrive/car/tests/test_models.py -k "tx_fuzzy and TOYOTA_COROLLA_TSS2" -q

# full-platform sweep (~5 min on 8 cores)
MAX_EXAMPLES=150 pytest openpilot/selfdrive/car/tests/test_models.py -k tx_fuzzy -n 8 --dist worksteal -q
```

Hypothesis stores failing examples in `.hypothesis/` and replays them first
(`Phase.reuse`) — stale entries from runs of *older test code* can cause confusing
one-off failures/Flaky errors; nuke the directory when in doubt.

## 3. Bounty workflow

1. Bounties live at https://github.com/orgs/commaai/projects/26 (redirect target of
   comma.ai/bounties); the issues carry the `bounty` label on commaai/openpilot. The board
   is a JS SPA — read the label search page instead:
   `https://github.com/commaai/openpilot/issues?q=is:issue state:open label:bounty`.
   Most bounties are hardware-gated (comma 3X, specific cars); check for competing open PRs
   before starting — **first merged PR wins**.
2. Develop on the user's fork **`spawahh/openpilot`**, branch pattern
   `claude/comma-ai-bounties-*`. The fork has no CI; comma's suite runs only on the
   upstream PR.
3. Follow comma's CONTRIBUTING.md (https://docs.comma.ai/CONTRIBUTING/) for every PR:
   single focused goal, **under ~500 lines**, body contains purpose statement +
   verification method + justification/benchmarks, target `master`. openpilot is
   feature-complete — tests/fixes/ports merge, features mostly don't.
4. The bounty pays the **author of the merged upstream PR** — the upstream
   `commaai/openpilot` PR must be opened by the user, under the account they want paid
   (they have more than one; ask). Keep upstream PR bodies/commits clean (no AI trailers).
5. No Algora/`/claim` mechanism on comma bounties — payment is comma's manual process on
   merge.

## 4. Fuzz-testing methodology

For writing or iterating on the panda-safety differential fuzzers in `test_models.py`
(RX: `test_panda_safety_carstate_fuzzy`, TX: `test_panda_safety_tx_fuzzy`), read
[references/fuzzer-notes.md](references/fuzzer-notes.md) before touching the code — it
documents the measured-state coherence gotchas that cost the most debugging time.
