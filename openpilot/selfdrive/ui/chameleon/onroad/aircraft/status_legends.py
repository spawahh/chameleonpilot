"""
The annunciator row's status legends: turn signal, temperature, GPS, engagement.

Marcus wants the indicators spaced evenly across the top (2026.07.30, seven
slots). The first three are the driver-alert legends and the DM readout; these
fill the row out:

- TURN (slot 3): dim while no signal; a blinker turns it bright green with a
  direction arrow ("< TURN" / "TURN >"), flashing at the same period as the
  ported edge arrows so the two never disagree. The box reserves room for both
  arrows at all times — watching it resize as a signal came on was worse than
  the arrow was worth.
- TEMP (slot 4): always lit, coloured by deviceState.thermalStatus — green
  (ok), amber (overheated), red with the dark fill (critical, the state where
  openpilot refuses to engage). The amber/red are the theme-pinned
  WARNING/DANGER values, same rule as the rest of the row: escalation colors
  are not themeable.
- GPS (slot 5): green on a good fix, amber on a degraded one, dim with none —
  the honest answer to "can I trust the tapes and the speed limit right now".
- ENGAGE (slot 6): green engaged, amber engageable, dim otherwise.

All ride the DmAnnunciator toggle — they are parts of the annunciator row, not
features of their own — and hide during a full-screen alert like the rest of
the row.
"""
import time

import pyray as rl

from openpilot.cereal import log
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.dm_annunciator import (
  AMBER, GREEN, RED, SLOT_ENGAGE, SLOT_GPS, SLOT_TEMP, SLOT_TURN, TOP_MARGIN, draw_legend, slot_x,
)
from openpilot.selfdrive.ui.mici.onroad.alert_renderer import TURN_SIGNAL_BLINK_PERIOD
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight

DIM = rl.Color(0, 255, 70, 70)  # unlit legend, same as the driver alerts
GPS_GOOD_ACCURACY = 10.0  # m of horizontal accuracy; beyond this the fix is degraded

ThermalStatus = log.DeviceState.ThermalStatus
AlertSize = log.SelfdriveState.AlertSize

def temp_style(thermal_status) -> tuple[rl.Color, bool]:
  """Colour + fill for a thermalStatus.

  ⚠️ Compare with `==`, never a dict lookup. A capnp enum field reads back as a
  `_DynamicEnum` that equals the module-level int (`ThermalStatus.ok == 0` is
  True, which is how upstream's own if/elif works) but **hashes differently**,
  so `{ThermalStatus.ok: ...}[field]` misses every time. That is exactly what
  pinned TEMP red for a whole trip on 2026.07.30, because the fallback was red.
  Unknown or deprecated states are a caution, not a danger.
  """
  if thermal_status == ThermalStatus.critical:
    return RED, True
  if thermal_status == ThermalStatus.ok:
    return GREEN, False
  return AMBER, False  # overheated, warmDEPRECATED, anything new upstream adds


def _row_hidden(sm) -> bool:
  if not ui_state.dm_annunciator:
    return True
  return sm['selfdriveState'].alertSize != AlertSize.none


class TurnLegend:
  def __init__(self):
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if _row_hidden(sm) or sm.recv_frame['carState'] < ui_state.started_frame:
      return

    cs = sm['carState']
    text, color = "TURN", DIM
    if cs.leftBlinker or cs.rightBlinker:
      text = "< TURN" if cs.leftBlinker else "TURN >"
      on_phase = (time.monotonic() % (2 * TURN_SIGNAL_BLINK_PERIOD)) < TURN_SIGNAL_BLINK_PERIOD
      color = GREEN if on_phase else DIM

    draw_legend(self._font, text, slot_x(rect, SLOT_TURN), rect.y + TOP_MARGIN, color)


class TempLegend:
  def __init__(self):
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if _row_hidden(sm):
      return

    color, filled = temp_style(sm['deviceState'].thermalStatus)
    draw_legend(self._font, "TEMP", slot_x(rect, SLOT_TEMP), rect.y + TOP_MARGIN, color, filled)


class GpsLegend:
  """Whether the tapes, road name and speed limits can be trusted right now:
  green on a good fix, amber on a degraded one, dim with no fix at all."""

  def __init__(self):
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if _row_hidden(sm):
      return

    gps = sm['gpsLocation']
    if not gps.hasFix:
      color = DIM
    elif gps.horizontalAccuracy > GPS_GOOD_ACCURACY or gps.horizontalAccuracy <= 0.0:
      color = AMBER  # fix, but not one to navigate by
    else:
      color = GREEN

    draw_legend(self._font, "GPS", slot_x(rect, SLOT_GPS), rect.y + TOP_MARGIN, color)


class EngageLegend:
  """openpilot's own state, spelled out: green engaged, amber ready to engage,
  dim when it cannot. The screen border says the same thing in colour only."""

  def __init__(self):
    self._font: rl.Font = gui_app.font(FontWeight.MEDIUM)

  def render(self, rect: rl.Rectangle, sm) -> None:
    if _row_hidden(sm):
      return

    ss = sm['selfdriveState']
    if ss.enabled:
      color = GREEN
    elif ss.engageable:
      color = AMBER
    else:
      color = DIM

    draw_legend(self._font, "ENGAGE", slot_x(rect, SLOT_ENGAGE), rect.y + TOP_MARGIN, color)
