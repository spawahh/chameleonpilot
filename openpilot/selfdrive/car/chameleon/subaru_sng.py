"""
Turns the SubaruStopAndGo param into the two CarParams fields the feature reads.

Ported to chameleonpilot from the Subaru half of sunnypilot's
opendbc/sunnypilot/car/interfaces.py (_initialize_stop_and_go).

Why this exists here rather than in opendbc: opendbc does not read openpilot
params, by design. sunnypilot solved that with a whole parallel CarParamsSP
struct threaded through every interface; this fork does not have one and adding
one to carry a single bool would be a large permanent upstream diff. So card
does what it already does for NNLC -- reads the param and mutates CP directly,
while CP is still a builder and before it is serialized.

Two fields, and both matter:
  - CP.flags gates the car-layer code in opendbc/car/subaru/stop_and_go.py
  - safetyConfigs[0].safetyParam gates the panda TX allowlist, which is what
    actually permits the two messages onto the camera bus

Setting one without the other is a silent no-op in one direction and blocked
transmissions in the other, so they are set together or not at all.

TIMING. This runs after CarInterface has already constructed CarState and
CarController, so the mixins there read CP.flags live rather than caching it in
__init__ -- everything holds the same CarParams object. It runs well before
CarParams is written to the params store, so panda gets the safety param.

The three refusals below are not cosmetic:
  - GEN2 and HYBRID have a different bus layout and message set. The panda
    change only widened the allowlist on the stock-longitudinal non-GEN2 path,
    and HYBRID has no Throttle on the powertrain bus at all.
  - openpilot longitudinal means openpilot is already doing the stopping and
    starting. This feature exists to drive the CAR's ACC; with openpilot long
    there is no camera ACC to nudge.
"""
from opendbc.car.subaru.values import SubaruFlags, SubaruSafetyFlags
from openpilot.common.swaglog import cloudlog


def setup_subaru_stop_and_go(CP, params) -> None:
  if not params.get_bool("SubaruStopAndGo"):
    return

  if CP.brand != "subaru":
    return

  if CP.flags & (SubaruFlags.GLOBAL_GEN2 | SubaruFlags.HYBRID):
    cloudlog.warning("chameleon subaru sng: GEN2/hybrid platform, staying stock")
    return

  if CP.openpilotLongitudinalControl:
    cloudlog.warning("chameleon subaru sng: openpilot longitudinal is on, staying stock")
    return

  cloudlog.warning(f"chameleon subaru sng: arming stop-and-go on {CP.carFingerprint}")
  CP.flags |= SubaruFlags.STOP_AND_GO_MANUAL_PARKING_BRAKE.value
  CP.safetyConfigs[0].safetyParam |= SubaruSafetyFlags.STOP_AND_GO.value
