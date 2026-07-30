# Installing chameleonpilot

**Read this whole page before you install.** This is one person's fork, developed against one car
on one device. It is not a product and there is no support commitment.

---

## Before you start

| | |
|---|---|
| **Device** | comma 3X (`tizi`). See the comma four note below. |
| **Car** | Anything upstream openpilot supports — but only a **2022 Subaru Crosstrek** (`SUBARU_IMPREZA_2020`) has actually been driven with this fork. |
| **Branch** | `main` |
| **Base** | upstream openpilot **`master`**, not a release branch |

### Three things that will surprise you

1. **First boot compiles from source.** `main` tracks upstream `master`, so there is no prebuilt
   branch. The first boot after installing builds openpilot on the device — expect **10–20 minutes
   with a dark or idle screen**. That is normal. Do not pull power thinking it has hung.
2. **`master` is openpilot's rawest branch.** comma ships `release-tizi` to users and describes even
   `nightly` as "do not expect this to be stable". This fork sits on top of something less stable
   than nightly, because that is what keeps it rebaseable.
3. **On a comma four you get almost none of this.** The themes and the aircraft HUD are written
   against the `tizi`/`tici` renderers. comma's `mici` device tree has its own renderers and is
   deliberately untouched, so a comma four would install this and see a near-stock UI.

Everything this fork adds is **off by default**. A fresh install behaves like upstream openpilot
with the `Stock` theme, which is bit-for-bit upstream colours. You turn things on in
**Settings → Chameleon**.

---

## Install

During device setup, choose **Custom Software** and enter:

```
installer.comma.ai/spawahh/main
```

That is it. The installer downloads, installs AGNOS if needed, clones the branch and reboots.

<details>
<summary>Why that URL says <code>spawahh</code> and not <code>chameleonpilot</code></summary>

comma's fork installer takes a **GitHub username and a branch** — the repository name is hardcoded
to `openpilot` (`# TODO: repo name not yet supported for installation` in the installer generator).
This repository is named `chameleonpilot`, so the installer asks GitHub for
`spawahh/openpilot`, and GitHub redirects that to `spawahh/chameleonpilot`. Git follows the
redirect, so the install works.

</details>

### Already running openpilot or another fork?

You do not need to reflash. SSH in and point the existing install at this fork:

```bash
cd /data/openpilot
git remote add chameleon https://github.com/spawahh/chameleonpilot.git
git fetch chameleon main
git checkout -B main chameleon/main
git submodule update --init --recursive
sudo reboot
```

The reboot triggers the build described above. **Do not run `launch_openpilot.sh` by hand** — if the
branch pins a different AGNOS than the one installed, that script starts an OS reflash before
anything else.

---

## Going back to stock

```bash
cd /data/openpilot
git remote set-url origin https://github.com/commaai/openpilot.git
git fetch origin release-tizi
git checkout -B release-tizi origin/release-tizi
sudo reboot
```

Or reflash from `openpilot.comma.ai` through the setup flow. Your settings live in `/data/params`
and are not touched by switching branches, so this fork's toggles simply stop being read.

---

## After it boots

Everything is in **Settings → Chameleon**:

- **Theme** — `Stock`, `Cascade`, `Rainier`, `Baker`, `Hood`
- **Night Mode** — off / on / auto (auto combines the light sensor with a solar schedule)
- **Map Data** — pick a US state to download offline OSM data (~200 MB+). Needed by the speed limit
  sign, the road name display and the speed limit caret.
- **HUD Widgets** — the aircraft HUD, the ported sunnypilot widgets, and the hide-stock-graphics
  toggles.

Two settings interact in a way that is not obvious:

- The **aircraft tapes** replace the stock speed readout, so turn on **Hide Speed Cluster** with them
  or you get both.
- **Hide Driver Monitoring Face** removes the only on-screen driver-monitoring indicator unless you
  also enable the **Driver Monitoring Annunciator**. Monitoring itself keeps running and still
  alerts either way.

---

## If something goes wrong

Issues are **disabled** on this repository — see the support note in the
[README](README.md#support-and-expectations). Nothing here is monitored, so treat this as
use-at-your-own-risk software.

To collect something useful for yourself, logs live in `/data/media/0/realdata/<route>/` and can be
read back with [opdm](https://opdm.mindflakes.com/) or comma's own tooling.

---

## Safety

openpilot is alpha-quality driver assistance and **you are driving the car**. This fork does not
change the safety model: the code enforcing it lives in panda, in C, and is untouched here. It does
add display elements that can hide stock warnings if you ask it to — `Hide Lane Lines` also hides
the red road-edge warning, and `Hide Driver Monitoring Face` removes that indicator. Those are
choices you are making deliberately.

The safety-critical colours (road edge red, lead marker, prompt and critical alert backgrounds,
sidebar status) are **identical in every theme, day and night, enforced by test**. A theme cannot
recolour a warning.

Read [`docs/SAFETY.md`](docs/SAFETY.md) and the upstream terms in the README before you drive.
