# `openpilot-cloud-dev` plugin — cloud session test results

- **Date:** 2026.08.02
- **Session:** Claude Code on the web (remote execution environment), `claude-opus-5`
- **Repo:** `spawahh/chameleonpilot`
- **Branch:** `claude/openpilot-cloud-dev-test-e5btaw` @ `16980c6`
- **Method:** observation only. Nothing was provisioned, installed, built, or fixed by hand.

---

## Headline

**The plugin never loaded. The hook never ran. Nothing was provisioned.**

The repo is a bare checkout: no `.venv`, no submodule contents, no compiled objects, no
environment variables. The plugin is declared correctly in `.claude/settings.json`, but this
cloud session did not act on that declaration at any point — it did not fetch the marketplace,
did not install the plugin, and therefore never discovered the SessionStart hook to run it.

Everything in sections 2–6 below is a consequence of that one fact.

---

## 1. Did the plugin load at all? — **No**

### Declaration is present and well-formed

`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "openpilot-claude-kit": {
      "source": {
        "source": "github",
        "repo": "spawahh/openpilot-claude-kit"
      }
    }
  },
  "enabledPlugins": {
    "openpilot-cloud-dev@openpilot-claude-kit": true
  }
}
```

### But nothing was loaded from it

**`openpilot-cloud-dev` is not in my available plugins.** The plugin registry is empty:

```
$ cat ~/.claude/plugins/installed_plugins.json
{
  "version": 2,
  "plugins": {}
}
```

Only two plugins are enabled for this session, both account-level, neither from this repo:

```
pdf-viewer
cowork-plugin-management
```

**The marketplace `openpilot-claude-kit` is not known to this session.** There is no
marketplace cache and no cloned plugin repo:

```
$ ls -la ~/.claude/plugins/
total 12
drwxr-xr-x 2 root root 4096 Aug  2 23:07 .
drwxr-xr-x 9 root root 4096 Aug  2 23:07 ..
-rw-r--r-- 1 root root   35 Aug  2 23:07 installed_plugins.json

$ ls ~/.claude/plugins/marketplaces/
ls: cannot access '/root/.claude/plugins/marketplaces/': No such file or directory

$ ls ~/.claude/plugins/repos/
ls: cannot access '/root/.claude/plugins/repos/': No such file or directory

$ cat ~/.claude/plugins/config.json
cat: /root/.claude/plugins/config.json: No such file or directory
```

`installed_plugins.json` is the *only* file in the plugins directory. The `marketplaces/` and
`repos/` directories — which is where a fetched marketplace and its cloned plugin repo would
live — were never created.

**The plugin's files do not exist anywhere on disk:**

```
$ find / -maxdepth 8 -name 'openpilot-claude-kit*' -not -path '/proc/*'
(no output)

$ find / -maxdepth 10 -name 'session-start.sh' -not -path '/proc/*'
(no output)
```

`plugins/openpilot-cloud-dev/scripts/session-start.sh` was never fetched, so there was no
hook script on disk for the harness to execute.

**No plugin-provided skills or commands are available.** My skills list for this session
contains no `openpilot-cloud-dev` entries and nothing openpilot-related.

### Scope note

I did **not** verify whether `spawahh/openpilot-claude-kit` exists, is public, or contains a
valid `.claude-plugin/marketplace.json`. GitHub access for this session is scoped to
`spawahh/chameleonpilot` only, and reaching outside that scope was not necessary to answer
the question: the failure is upstream of any repo fetch. There is no marketplace cache
directory at all, no partial clone, and no error artifact — consistent with the session never
*attempting* the fetch, rather than attempting it and failing. **Whether the marketplace repo
itself is well-formed is UNKNOWN and untested by this run.**

### Assessment

`extraKnownMarketplaces` + `enabledPlugins` in a **project-level** `.claude/settings.json` did
not cause a marketplace fetch or plugin install in this cloud session. The most likely
explanations, in rough order — **none of these is confirmed, all are hypotheses:**

1. Cloud sessions do not resolve `extraKnownMarketplaces` from project settings during startup
   (marketplace trust/install may be an interactive or user-scope-only action).
2. Marketplace installation requires a network fetch through the agent proxy that is not
   performed at session bootstrap.
3. Plugin resolution happens before or independently of the repo checkout, so project settings
   arrive too late to participate.

The next diagnostic step — **not taken here, since you asked me not to fix anything** — would
be to test the same declaration in user scope (`~/.claude/settings.json`) or run
`/plugin marketplace add spawahh/openpilot-claude-kit` interactively, to separate "project
settings are ignored" from "marketplace fetch fails".

---

## 2. Did the hook run? — **No**

- **No lines beginning `openpilot-cloud-dev:` appeared in the session startup output.** None.
  There is nothing to quote verbatim, including no skip or fallback messages.
- The only SessionStart hook configured for this session is the harness's own, from
  `~/.claude/launcher-settings.json`:

```json
"SessionStart": [
    {
        "hooks": [
            {
                "type": "command",
                "command": "~/.claude/session-start-git-identity.sh"
            }
        ]
    }
]
```

  `session-start-git-identity.sh` is the built-in git identity setup. The plugin hook is
  absent from the resolved hook set.

### Startup duration

Startup was **fast — roughly 30 seconds** — which is itself the tell. A real
submodule + `uv sync` + apt + `scons` provision on 4 cores would take many minutes.

| Event | Timestamp (UTC) |
|---|---|
| Container boot (`uptime -s`) | 2026-08-02 23:07:28 |
| Repo checkout (`.git/HEAD` mtime) | 2026-08-02 23:07:38 |
| Plugin registry written (`installed_plugins.json` mtime) | 2026-08-02 23:07:45 |
| First command I could run (`date -u`) | 2026-08-02 23:08:35 |

Note that `installed_plugins.json` was written at 23:07:45 — the harness *did* touch the
plugin registry during startup, and wrote an empty `{"version": 2, "plugins": {}}`. The plugin
subsystem initialized; it just did not pick up this repo's declaration.

---

## 3. Environment facts

```
$ id -u
0

$ uv --version
uv 0.8.17

$ cat .python-version
3.12.13

$ nproc
4

$ free -g | head -2
               total        used        free      shared  buff/cache   available
Mem:              15           0          14           0           0          15

$ df -h . | tail -1
/dev/vda        252G  7.1G   30G  20% /
```

```
$ uv python list --all-versions 2>/dev/null | grep -o 'cpython-3\.12\.[0-9]*' | sort -uV | tail -3
cpython-3.12.9
cpython-3.12.10
cpython-3.12.11
```

Additional context:

```
$ python3 -V
Python 3.11.15

$ which python3 scons cc g++
/usr/local/bin/python3
/usr/bin/cc
/usr/bin/g++
```

`scons` is **not** on `PATH` (`which scons` → exit 1; `command -v scons` → exit 1). The C/C++
toolchain (`cc`, `g++`) is present. `HOME=/root`, running as uid 0.

### ⚠️ Latent trap — this container's `uv` is too old to supply the pinned Python

This one would bite even if the plugin loaded correctly:

- `.python-version` pins **3.12.13**
- `uv 0.8.17` in this image offers a maximum of **3.12.11**

```
$ uv python list --all-versions 2>/dev/null | grep -c '3\.12\.13'
0

$ uv python list --all-versions 2>/dev/null | grep -o 'cpython-3\.[0-9]*\.[0-9]*' | sort -uV | tail -3
cpython-3.13.6
cpython-3.13.7
cpython-3.14.0
```

Nothing is downloaded yet (`~/.local/share/uv/python` does not exist), so no interpreter is
cached to fall back on. Unless the hook pins or upgrades `uv` first, `uv sync` is likely to
fail on interpreter resolution. **I did not run `uv sync` to confirm this** — it is a
prediction from the version data above, not an observed failure. It is the first thing to
check once the plugin actually loads.

**This repo's own GitHub Actions CI confirms the pin itself is fine and the container's `uv`
is the problem.** The `unit tests` job resolves the pinned interpreter without complaint:

```
uv 0.12.1
.../.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/lib/python3.12/...
```

So 3.12.13 exists and is fetchable — `uv 0.8.17` in this cloud image is simply too old to
know about it. **Fix `uv`, not `.python-version`:** have the hook run `uv self update` (or
install a pinned modern `uv`) before `uv sync`. Do not relax the pin — CI would then be
building against a different interpreter than the cloud session.

---

## 4. Did provisioning actually work? — **No**

```
$ ls -d .venv && .venv/bin/python -V
ls: cannot access '.venv': No such file or directory
```

```
$ git submodule status | head
-6a8d2e8f06f7864976d148f3cf423e8b3a418e8a msgq_repo
-58e07d4aaa82147a631d2f38e23013780442dd4f opendbc_repo
-d9ed70b850513f65e2a69707835f818409fe6052 panda
-9e19086c26ca35708870d50ebcf237d65d0b163e rednose_repo
-3ac144dc9a57ace70172d338690b121c42c5add2 teleoprtc_repo
-ef37830d138838933d6d70d0024de9f130cb2308 tinygrad_repo
```

**Every submodule is uninitialized** — the leading `-` on all six lines means not checked out.
`git submodule update --init` never ran.

All three Python probes failed identically, because there is no virtualenv to run them with:

```
$ PYTHONPATH="$PWD" .venv/bin/python -c "from openpilot.common.params import Params; Params(); print('params OK')"
/bin/bash: line 8: .venv/bin/python: No such file or directory

$ PYTHONPATH="$PWD" .venv/bin/python -c "import pyray; print('pyray OK')"
/bin/bash: line 9: .venv/bin/python: No such file or directory

$ PYTHONPATH="$PWD" .venv/bin/python -c "from openpilot.cereal import messaging; print('cereal OK')"
/bin/bash: line 10: .venv/bin/python: No such file or directory
```

These are **shell** errors, not Python `ImportError`s — the failure is one level earlier than
the import. They say nothing about whether the packages themselves would work.

### GLES libraries — not installed

The libraries `pyray` needs, and which the hook is supposed to install, are absent:

```
$ ldconfig -p | grep -cE 'libGLESv2|libEGL\.so'
0

$ ldconfig -p | grep -E 'libGLESv2|libEGL'
(none)
```

Only adjacent graphics libraries ship in the base image — no GLES, no EGL:

```
$ ldconfig -p | grep -iE 'GLESv|EGL|libgbm|libdrm' | head
	libwayland-egl.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libwayland-egl.so.1
	libgbm.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libgbm.so.1
	libdrm_intel.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libdrm_intel.so.1
	libdrm_amdgpu.so.1 (libc6,x86-64) => /lib/x86_64-linux-gnu/libdrm_amdgpu.so.1
	libdrm.so.2 (libc6,x86-64) => /lib/x86_64-linux-gnu/libdrm.so.2
```

`libwayland-egl.so.1` is present but that is the Wayland EGL platform shim, **not** `libEGL.so`
or `libGLESv2.so`. So the apt step the hook owns is genuinely load-bearing for `pyray` on this
image — it is not something the base image happens to provide for free.

**Independent corroboration from this repo's CI.** The PR carrying this report triggered the
repo's GitHub Actions run, and the `unit tests` and `Create UI Report` jobs both failed on the
exact same missing library — verbatim:

```
E   ImportError: libGLESv2.so.2: cannot open shared object file: No such file or directory
```

...surfacing through `pyray` as:

```
ImportError: failed to load raylib headless backend extension _raylib_cffi_headless
```

That produced `4 failed, 947 passed, 90 skipped, 1 xfailed, 18 errors` — every one of the 4
failures and 18 errors traced to that single missing `.so`. Two independent environments (this
cloud container and a GitHub Actions runner) are missing `libGLESv2.so.2`, which makes the
hook's GLES install step the single highest-value thing it does. It is worth verifying first
once the plugin loads.

---

## 5. Did the build finish? — **No, it never started**

`scons` is not installed and was never invoked. There is no build log, no `.sconsign.dblite`,
no error output — nothing ran.

```
$ find . -name '*.so' -not -path './.git/*' -not -path './.venv/*' | wc -l
0
```

Zero compiled objects.

---

## 6. Did the environment persist? — **No**

None of the variables the hook is supposed to write to `$CLAUDE_ENV_FILE` are set in my shell:

```
VIRTUAL_ENV=[]
PYTHONPATH=[]
RAYLIB_BACKEND=[]
CLAUDE_ENV_FILE=[]
```

`CLAUDE_ENV_FILE` itself is unset in the Bash tool's environment. The per-session env directory
exists but is **empty**:

```
$ ls -laR ~/.claude/session-env/
/root/.claude/session-env/:
drwxr-xr-x 3 root root 4096 Aug  2 23:07 .
drwxr-xr-x 9 root root 4096 Aug  2 23:07 ..
drwxr-xr-x 2 root root 4096 Aug  2 23:07 d6d0be7c-42b1-5cc0-97a3-9558d26cf407

/root/.claude/session-env/d6d0be7c-42b1-5cc0-97a3-9558d26cf407:
total 8
drwxr-xr-x 2 root root 4096 Aug  2 23:07 .
drwxr-xr-x 3 root root 4096 Aug  2 23:07 ..
```

The mechanism is wired up and the directory was created at 23:07 — the hook simply never wrote
into it. **The env-file mechanism itself is untested by this run**; we only know nothing used it.

---

## 7. Anything else that would bite a real user

1. **Silent failure is the worst part.** The plugin did not error, warn, or log. Startup looked
   completely normal. A user who trusted the plugin would open a session, see a clean prompt,
   and only discover the bare checkout when a build or test failed several steps later — with
   no breadcrumb pointing at plugin loading as the cause. A loud "marketplace not found" would
   have been far better than this.

2. **Fast startup is the symptom.** ~30 seconds from boot to usable prompt *feels* like a win
   and is actually the clearest evidence of failure. If you are testing this again, treat a
   fast startup as a red flag, not a pass.

3. **`.python-version` pins 3.12.13; `uv 0.8.17` maxes out at 3.12.11.** Fix this regardless of
   the plugin outcome, or the hook will trade a silent no-op for a loud `uv sync` failure the
   first time it does run. Either pin `uv` to a newer version in the hook, relax
   `.python-version`, or have the hook `uv self update` before syncing.

4. **GLES really is missing from the base image**, so the apt step is genuinely required —
   worth keeping even though it slows startup. `libwayland-egl.so.1` being present is a red
   herring; it is not what `pyray` links against.

5. **`scons` is not preinstalled** — the hook must install it (via `uv`/`pip` into the venv, or
   apt). Do not assume it is on `PATH`.

6. **The base image is otherwise well-provisioned**: uid 0 (no `sudo` needed — which matters,
   since `Bash(sudo *)` is in this session's deny list), 4 cores, 15 GB RAM, 30 GB free disk,
   `cc`/`g++` present. `scons -j4` is realistic here; there is no resource obstacle to a full
   build. The only obstacle is that the hook never ran.

7. **Nothing needed cleanup afterward** — because nothing happened. The working tree was clean
   apart from this file.

8. **CI on this branch is red for reasons that predate it.** The PR carrying this report
   changes three files and no code, yet four checks failed. All four are pre-existing on
   `main`:

   | Check | Cause | Related to this diff? |
   |---|---|---|
   | `static analysis` | `codespell` — 139 en-GB spelling hits in `openpilot/selfdrive/ui/**`; `ruff` passed | No — zero hits in the three changed files |
   | `unit tests` | `ImportError: libGLESv2.so.2` — 4 failed, 18 errors | No |
   | `Create UI Report` | same `libGLESv2.so.2` ImportError | No |
   | `process replay` | 9 segments differ in `carControl.actuators.torque` and `torqueState.*` vs reference logs | No — the diff contains no Python or C++ |

   Worth knowing before the next cloud test: **a green CI is not the bar on this fork right
   now.** Also note `[tool.codespell]` in `pyproject.toml` sets `builtin = "...,en-GB_to_en-US"`
   and its `skip` list does not exclude `*.md`, so en-GB spellings are rejected in new
   documentation too — easy to trip when writing prose about en-GB spellings.

---

## Reproduce

```bash
cat .claude/settings.json                       # declaration present
cat ~/.claude/plugins/installed_plugins.json    # {"version": 2, "plugins": {}}
ls ~/.claude/plugins/                           # only installed_plugins.json
find / -name 'session-start.sh' -not -path '/proc/*'   # nothing
ls -d .venv                                     # nothing
git submodule status                            # all six prefixed with '-'
find . -name '*.so' -not -path './.git/*' -not -path './.venv/*' | wc -l   # 0
env | grep -E 'VIRTUAL_ENV|PYTHONPATH|RAYLIB_BACKEND|CLAUDE_ENV_FILE'      # nothing
```
