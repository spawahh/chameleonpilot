# panda-safety differential fuzzing: methodology & gotchas

Hard-won notes from building `test_panda_safety_tx_fuzzy` (openpilot bounty #32425,
mirror of the merged RX fuzzer #30443). Read before iterating on either fuzzer.

## Core invariant

openpilot's CarController clamps its commands with the same limit functions panda safety
enforces (`opendbc/car/lateral.py` ↔ `opendbc/safety/lateral.h` etc.), both driven by
measured state. Panda's checks are deliberately *more permissive* envelopes (sample-window
min/max, ±1 CAN-unit slack, speed fudged by −1 m/s). Therefore: **feed identical fuzzed CAN
to both `safety_rx_hook` and `CI.update`, sync panda's controls state to the fuzzed
CarControl, advance `now_nanos` and `set_timer` in lockstep (timer is µs, relative epoch,
mod 2^32) → every message openpilot sends must pass `safety_tx_hook`.** A blocked message is
a TX-logic divergence (the class of commaai/panda#1948).

## Making fuzzed payloads count

- Panda's RxChecks and openpilot's `CANParser` both drop bad-checksum/bad-counter frames —
  raw random bytes update measured state ~0.4% of the time on checksummed brands. Fix up
  counter (+1 sequence from the parser's `MessageState.counter`) and checksum
  (`sig.calc_checksum`) per payload, splicing with `opendbc/can/packer.set_value`.
- Quality flags are panda-only (parser has no concept): force Ford's `*_D_Qf` signals to 3
  or the two sides desync on which frames they accept.
- Draw the payload sequence from a small pool (1–3 payloads) **seeded with the last real
  warmup payload**, sampled repeatedly — this creates oscillation between plausible and
  extreme readings, which is exactly the input sample-window bugs (#1948) need. Pure
  per-frame random values almost never produce "low instantaneous reading while window
  extremes are high".
- Parsers populate lazily (`VLDict._add_message` on access) — snapshot
  `cp.message_states` only *after* a warmup `CI.update`.
- Hyundai CANFD parser buses are 4–6 (harness offset): keep them, pass `bus % 4` to panda
  (`make_CANPacket`), original bus to `CanData.src`. Skip only buses ≥8 (GM loopback 128).

## The controlsd contract (fuzzed CarControl must honor it)

CarControllers assume controlsd's guarantees; violating them creates false positives:
- `actuators.torque`/`accel` are zeroed and `longControlState='off'` while lat/long inactive.
- `longActive` requires `CP.openpilotLongitudinalControl` and is dropped when panda's
  `get_longitudinal_allowed()` goes false (gas press) — re-derive per frame; also set
  `cruiseControl.override = enabled and not longActive and openpilotLongitudinalControl`
  (Hyundai CANFD zeroes accel instantly on override; without it the jerk-smoothed aReqValue
  ramps down over ~0.4 s and panda blocks it).
- `cancel` only while stock cruise engaged and not enabled; `resume` only while enabled.
- `set_gas_pressed_prev` is overwritten by every rx (panda copies current `gas_pressed`
  into `_prev`) — force it in the per-frame resync block, not once per example. Routes can
  end with the driver on gas, which otherwise pins `longitudinal_allowed` false for the
  whole test and silently kills all longitudinal coverage.

## Measured-state coherence: gate, don't special-case

Where openpilot and panda genuinely can't be compared under fuzzing, skip the assert for
that frame (still call `tx_hook` to keep panda's tracking state moving) rather than
special-casing per test. Known divergence classes:

1. **Two-sensor sources with learned offsets**: Toyota LTA angle (0x25 sensor + slow
   offset filter vs 0x260), Tesla angle (0x129 vs 0x370), Tesla speed (DI vs ESP). Check
   openpilot's value against panda's envelope ±1 (`ANGLE_DEG_TO_CAN` table); speed via
   `vEgoRaw/wheelSpeedFactor` in panda's speed envelope.
2. **Sample-window vs instantaneous**: Toyota LTA wind-down uses `MIN(|win.min|,|win.max|)`
   of panda's 6-sample window vs openpilot's instantaneous reading. They only agree when
   openpilot's value *is one of the window extremes* — require that (±1/±2), not mere
   within-window containment, or mid-window near-zero samples false-positive.
3. **Command-stream re-anchoring**: openpilot re-anchors its angle/curvature command on
   internal gates fuzz can flip (Tesla `hands_on_level` from 0x370 — exclude that rx from
   the draw; accel-clip on fuzzed speed jumps; VW MEB winddown tracking fuzzed measured
   curvature). Guards: skip on |Δout.steeringAngleDeg| > 25°, on angle jumps >1° while
   vEgo rose >0.5 m/s/frame, and on curvature deltas beyond panda's jerk allowance
   (`(3.0+9.81*0.06)/max(speed_min−1,1)²/freq`); bound |curvature| by the lateral-accel cap.
4. **Baseline drift**: panda resets `desired_angle_last`/`desired_curvature_last` to the
   clamped measured value on any violation, openpilot keeps its own — re-anchor panda's
   baseline to openpilot's applied command (`set_desired_angle_last(out.steeringAngleDeg *
   ANGLE_DEG_TO_CAN[brand])`, curvature via brand sign/scale) **every frame**. This concedes
   steering rate-limit-only coverage (deterministic anyway) to keep measured-state-dependent
   checks assertable. Track blocked addrs: after a skipped block, don't assert that addr
   until a send passes again.
5. **Panda-only TX lockouts** (no CarController analog; panda blocks openpilot in reality
   too): Tesla Autopark (0x286), stock LKAS (bus-2 0x488), stock AEB (bus-2 0x2b9), Honda
   `fwd_brake` — exclude the latch-source rx from the draw / reset the flag per frame.
6. **Panda self-disengage inside tx_hook** (e.g. two-source speed mismatch check): if
   `controls_allowed` reads false right after a block despite being forced true, skip.
7. **Toyota inactive LTA frames** (both request bits clear) carry no actuation but must
   echo measured angle ±1 through a float-degree + learned-offset round trip — skip asserts
   on them (check the *sent request bits*, not the drawn lat_active; openpilot emits
   inactive frames inside active examples too). Pin `STEER_ANGLE` in fuzzed 0x260 payloads
   to 0 so the wind-down/torque checks stay assertable while angle stays coherent.

## Validation recipe (the merge bar)

Prove the fuzzer catches bugs by planting mutations in the local opendbc checkout
(libsafety recompiles at next import; revert with `git -C opendbc_repo checkout -- .`):

- Toyota LTA wind-down `SAFETY_MIN`→`SAFETY_MAX` (toyota.h ~299/304) — the #1948 revert →
  RAV4_TSS2_2023.
- Toyota `.max_torque_error` 350→200 (tighter than op's STEER_ERROR_MAX) → COROLLA_TSS2.
- Hyundai `STEER_DELTA_UP` 3→4 (op ramps faster than panda's rate_up) →
  `opendbc/car/hyundai/values.py`, HYUNDAI_SONATA.
- GM `.max_gas` 1018→700 → CHEVROLET_VOLT (GM is always op-long).

Each mutant must fail while the clean tree passes repeatedly (5× at MAX_EXAMPLES=1000).
Also verify speed parity vs the RX fuzzer (same platform, `--durations`); ~1.1–1.2× is fine.

## Real findings to remember

- panda decodes VW MQB `LH_EPS_03` driver torque as 13 bits (`data[6] & 0x1F`) where the
  DBC defines the signal as 10 bits at bit 40 — bits 50–52 are undefined/always-zero on the
  wire. Masked in the fuzzer (`TX_FUZZ_PAYLOAD_MASKS`); panda's mask should be tightened
  upstream.
- Ford: panda blocks openpilot's curvature commands during curve-engagement ramps (op jerk-
  ramps toward the measured window; panda's curvature-error check has no convergence
  allowance) — real, known-tolerated behavior, gated in the fuzzer.
