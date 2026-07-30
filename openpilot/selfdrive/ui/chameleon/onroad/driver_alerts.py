"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's
sunnypilot/selfdrive/controls/lib/e2e_alerts_helper.py (detection). The
rendering began as a port of selfdrive/ui/sunnypilot/onroad/circular_alerts.py
and was reworked into an aircraft-style annunciator legend drawn in line with
the driver-monitoring readout; only the detection half still follows sunnypilot.

In sunnypilot the detection half runs inside the longitudinal planner and
reaches the UI through a custom cereal field (longitudinalPlanSP.e2eAlerts).
The stock UI already subscribes to everything the detection reads (carState,
carControl, modelV2, radarState), so here both halves run in the UI process
and the control path is untouched. Deliberately not ported: the audible chime
(needs the selfdrived events path), the standstill timer (separate sunnypilot
feature), and the green_light/lead_depart PNGs (new LFS assets do not survive
the git-bundle workflow this fork uses to move commits between machines).
"""
import pyray as rl

from openpilot.cereal import log
from openpilot.chameleon import chime
from openpilot.selfdrive.ui.chameleon.onroad.aircraft.dm_annunciator import TOP_MARGIN
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached

GREEN_LIGHT_X_THRESHOLD = 30  # m: model path this long means the road ahead opened up
LEAD_DEPART_DIST_THRESHOLD = 1.0  # m: how far the lead must pull away
TRIGGER_TIMER_THRESHOLD = 0.3  # s: the condition must hold this long
LEAD_DEPART_ARM_DIST = 8.0  # m: a lead closer than this arms the departure alert
LEAD_DEPART_ARM_TIME = 1.0  # s: the close lead must be there this long
RECENT_MOVING_TIME = 2.0  # s: do not arm right after rolling to a stop
ALERT_DISPLAY_TIME = 3.0  # s: how long the legend stays on screen
ALERT_TEXT_SIZE = 44  # matches the DM annunciator, so the row reads as one panel
CENTER_GAP = 250.0  # px between screen centre and the legends' right edge; clears "LOCKOUT 30 MIN"
ROW_STEP = 84.0  # second legend row sits this far below the first
PAD_X, PAD_Y = 24.0, 10.0
BOX_THICKNESS = 4.0
BOX_BG = rl.Color(0, 0, 0, 140)
GREEN = rl.Color(0, 255, 70, 230)  # aircraft green, same as the tapes and FPV
WHITE = rl.Color(255, 255, 255, 255)
DIM = rl.Color(0, 255, 70, 70)  # unlit annunciator legend

LEGENDS = ("GREEN LIGHT", "LEAD DEPARTING")
CHIME = "complete"  # upstream's ding, played once by soundd


class E2EStates:
  INACTIVE = 0
  ARMED = 1
  CONSUMED = 2


class DriverAlertsHelper:
  """Detects a green light (stopped, no lead, model path opens up) and a
  departing lead (stopped behind a close lead that pulls away)."""

  def __init__(self):
    self._dt = 1 / gui_app.target_fps
    self.frame = -1

    self.green_light_state = E2EStates.INACTIVE
    self.lead_depart_state = E2EStates.INACTIVE
    self.green_light_alert = False
    self.lead_depart_alert = False

    self.green_light_trigger_timer = 0
    self.lead_depart_trigger_timer = 0
    self.last_lead_distance = -1.0
    self.last_moving_frame = -1

    self.allowed = False
    self.last_allowed = False
    self.has_lead = False

    self.lead_depart_arm_timer = 0
    self.lead_depart_confirmed_lead = False
    self.lead_depart_armed = False

  def update_alert_trigger(self, sm) -> tuple[bool, bool]:
    CS = sm['carState']
    CC = sm['carControl']

    model_x = sm['modelV2'].position.x
    max_idx = len(model_x) - 1
    model_x_max = model_x[max_idx] if max_idx >= 0 else 0.0
    self.has_lead = sm['radarState'].leadOne.present
    lead_dRel = sm['radarState'].leadOne.dRel

    standstill = CS.standstill
    moving = not standstill and CS.vEgo > 0.1

    if moving:
      self.last_moving_frame = self.frame
    recent_moving = self.last_moving_frame == -1 or (self.frame - self.last_moving_frame) * self._dt < RECENT_MOVING_TIME

    self.allowed = not moving and not CS.gasPressed and not CC.enabled and not recent_moving

    # Green light alert
    green_light_trigger = False
    if self.green_light_state == E2EStates.ARMED:
      if model_x_max > GREEN_LIGHT_X_THRESHOLD:
        self.green_light_trigger_timer += 1
      else:
        self.green_light_trigger_timer = 0

      if self.green_light_trigger_timer * self._dt > TRIGGER_TIMER_THRESHOLD:
        green_light_trigger = True
    else:
      self.green_light_trigger_timer = 0

    # Lead departure alert
    close_lead_valid = self.has_lead and lead_dRel < LEAD_DEPART_ARM_DIST
    if self.allowed and not self.last_allowed and close_lead_valid:
      self.lead_depart_confirmed_lead = True
    elif not self.allowed:
      self.lead_depart_confirmed_lead = False

    if self.allowed and self.lead_depart_confirmed_lead and close_lead_valid:
      self.lead_depart_arm_timer += 1

      if self.lead_depart_arm_timer * self._dt >= LEAD_DEPART_ARM_TIME:
        self.lead_depart_armed = True
    else:
      self.lead_depart_arm_timer = 0
      self.lead_depart_armed = False

    lead_depart_trigger = False
    if self.lead_depart_state == E2EStates.ARMED:
      if self.last_lead_distance == -1 or lead_dRel < self.last_lead_distance:
        self.last_lead_distance = lead_dRel

      if self.last_lead_distance != -1 and (lead_dRel - self.last_lead_distance > LEAD_DEPART_DIST_THRESHOLD):
        self.lead_depart_trigger_timer += 1
      else:
        self.lead_depart_trigger_timer = 0

      if self.lead_depart_trigger_timer * self._dt > TRIGGER_TIMER_THRESHOLD:
        lead_depart_trigger = True
    else:
      self.last_lead_distance = -1.0
      self.lead_depart_trigger_timer = 0

    self.last_allowed = self.allowed

    return green_light_trigger, lead_depart_trigger

  @staticmethod
  def update_state_machine(state: int, enabled: bool, allowed: bool, triggered: bool) -> tuple[int, bool]:
    if state != E2EStates.INACTIVE:
      if not allowed or not enabled:
        state = E2EStates.INACTIVE
      elif state == E2EStates.ARMED and triggered:
        state = E2EStates.CONSUMED

    elif allowed and enabled:
      state = E2EStates.ARMED

    return state, triggered

  def update(self) -> None:
    enabled = ui_state.driver_alerts

    green_light_trigger, lead_depart_trigger = self.update_alert_trigger(ui_state.sm)

    self.green_light_state, self.green_light_alert = self.update_state_machine(
      self.green_light_state,
      enabled,
      self.allowed and not self.has_lead,
      green_light_trigger,
    )

    self.lead_depart_state, self.lead_depart_alert = self.update_state_machine(
      self.lead_depart_state,
      enabled,
      self.allowed and self.lead_depart_armed,
      lead_depart_trigger,
    )

    self.frame += 1


class DriverAlerts:
  """Annunciator legends in line with the driver-monitoring readout, just left
  of centre so they never collide with its text. Both legends stay visible but
  unlit (dim outline) whenever the widget is allowed to draw; a firing alert
  brightens its legend with a white/green pulse for 3 seconds and asks soundd
  for a one-shot chime."""

  def __init__(self):
    self._helper = DriverAlertsHelper()
    self._font: rl.Font = gui_app.font(FontWeight.BOLD)

    self._display_timer = 0
    self._alert_frame = 0
    self._alert_text = ""
    self._allow_alerts = False

  def update(self) -> None:
    self._helper.update()

    sm = ui_state.sm
    # No pop-up on top of a real alert, and not before driver monitoring is up
    self._allow_alerts = sm['selfdriveState'].alertSize == log.SelfdriveState.AlertSize.none and \
                         sm.recv_frame['driverStateV2'] > ui_state.started_frame

    if self._helper.green_light_alert or self._helper.lead_depart_alert:
      self._display_timer = int(ALERT_DISPLAY_TIME * gui_app.target_fps)
      if self._helper.green_light_alert:
        self._alert_text = "GREEN LIGHT"
      else:
        self._alert_text = "LEAD DEPARTING"
      chime.request(CHIME)

    if self._display_timer > 0:
      self._display_timer -= 1
      self._alert_frame += 1
    else:
      self._alert_frame = 0

  def render(self, rect: rl.Rectangle) -> None:
    if not ui_state.driver_alerts or not self._allow_alerts:
      return

    is_pulsing = (self._alert_frame % gui_app.target_fps) < (gui_app.target_fps / 2.5)
    active_color = WHITE if is_pulsing else GREEN

    # right-aligned against the centre gap, stacked from the DM annunciator's line
    for i, text in enumerate(LEGENDS):
      active = self._display_timer > 0 and text == self._alert_text
      color = active_color if active else DIM
      measure = measure_text_cached(self._font, text, ALERT_TEXT_SIZE, 0)
      x = rect.x + rect.width / 2 - CENTER_GAP - measure.x
      y = rect.y + TOP_MARGIN + i * ROW_STEP
      box = rl.Rectangle(x - PAD_X, y - PAD_Y, measure.x + 2 * PAD_X, measure.y + 2 * PAD_Y)
      if active:
        rl.draw_rectangle_rec(box, BOX_BG)
      rl.draw_rectangle_lines_ex(box, BOX_THICKNESS, color)
      rl.draw_text_ex(self._font, text, rl.Vector2(x, y), ALERT_TEXT_SIZE, 0, color)
