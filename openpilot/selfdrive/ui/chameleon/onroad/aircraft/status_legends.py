"""
The annunciator row's status legends: turn signals and system temperature.

Marcus wants five indicators spaced evenly across the top (2026.07.30). The
first three slots are the driver-alert legends and the DM readout; these two
fill the row out:

- TURN (slot 3): dim while no signal; a blinker turns it bright green with a
  direction arrow ("< TURN" / "TURN >"), flashing at the same period as the
  ported edge arrows so the two never disagree.
- TEMP (slot 4): always lit, coloured by deviceState.thermalStatus — green
  (ok), amber (overheated), red with the dark fill (critical, the state where
  openpilot refuses to engage). The amber/red are the theme-pinned
  WARNING/DANGER values, same rule as the rest of the row: escalation colors
  are not themeable.

Both ride the DmAnnunciator toggle — they are parts of the annunciator row,
not features of their own — and hide during a full-screen alert like the rest
of the row.
"""
import time

import pyray as rl

from openpilot.cereal import log
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.dm_annunciator import (
  AMBER, GREEN, RED, SLOT_TEMP, SLOT_TURN, TOP_MARGIN, draw_legend, slot_x,
)
from openpilot.selfdrive.ui.mici.onroad.alert_renderer import TURN_SIGNAL_BLINK_PERIOD
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight

DIM = rl.Color(0, 255, 70, 70)  # unlit legend, same as the driver alerts

ThermalStatus = log.DeviceState.ThermalStatus
AlertSize = log.SelfdriveState.AlertSize

TEMP_COLORS = {
  ThermalStatus.ok: (GREEN, False),
  ThermalStatus.overheated: (AMBER, False),
  ThermalStatus.critical: (RED, True),
}


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

    color, filled = TEMP_COLORS.get(sm['deviceState'].thermalStatus, (RED, True))
    draw_legend(self._font, "TEMP", slot_x(rect, SLOT_TEMP), rect.y + TOP_MARGIN, color, filled)
