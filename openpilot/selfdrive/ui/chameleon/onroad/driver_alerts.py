"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.

Ported to chameleonpilot from sunnypilot's
sunnypilot/selfdrive/controls/lib/e2e_alerts_helper.py (detection) and
selfdrive/ui/sunnypilot/onroad/circular_alerts.py (rendering).

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
from openpilot.selfdrive.ui import UI_BORDER_SIZE
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight, FONT_SCALE
from openpilot.system.ui.lib.text_measure import measure_text_cached

GREEN_LIGHT_X_THRESHOLD = 30  # m: model path this long means the road ahead opened up
LEAD_DEPART_DIST_THRESHOLD = 1.0  # m: how far the lead must pull away
TRIGGER_TIMER_THRESHOLD = 0.3  # s: the condition must hold this long
LEAD_DEPART_ARM_DIST = 8.0  # m: a lead closer than this arms the departure alert
LEAD_DEPART_ARM_TIME = 1.0  # s: the close lead must be there this long
RECENT_MOVING_TIME = 2.0  # s: do not arm right after rolling to a stop
ALERT_DISPLAY_TIME = 3.0  # s: how long the circle stays on screen
ALERT_RADIUS = 250
ALERT_RIGHT_MARGIN = 100
ALERT_RING_THICKNESS = 7.5
ALERT_TEXT_SIZE = 48


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
  """Circular pop-up on the right side of the road view, pulsing white/green
  for 3 seconds when the helper fires an alert."""

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
        self._alert_text = "GREEN\nLIGHT"
      else:
        self._alert_text = "LEAD VEHICLE\nDEPARTING"

    if self._display_timer > 0:
      self._display_timer -= 1
      self._alert_frame += 1
    else:
      self._alert_frame = 0

  def render(self, rect: rl.Rectangle) -> None:
    if not ui_state.driver_alerts or not self._allow_alerts or self._display_timer <= 0:
      return

    center = rl.Vector2(
      rect.x + rect.width - ALERT_RADIUS - ALERT_RIGHT_MARGIN - (UI_BORDER_SIZE * 3),
      rect.y + rect.height / 2 + 20,
    )

    is_pulsing = (self._alert_frame % gui_app.target_fps) < (gui_app.target_fps / 2.5)
    ring_color = rl.Color(255, 255, 255, 75) if is_pulsing else rl.Color(0, 255, 0, 75)
    text_color = rl.Color(255, 255, 255, 255) if is_pulsing else rl.Color(0, 255, 0, 190)

    rl.draw_circle_v(center, ALERT_RADIUS, rl.Color(0, 0, 0, 190))
    rl.draw_ring(center, ALERT_RADIUS - ALERT_RING_THICKNESS, ALERT_RADIUS + ALERT_RING_THICKNESS, 0, 360, 0, ring_color)

    # sunnypilot bottom-aligns the text under a 250 px image; the image is not
    # ported, so center the text block in the circle instead
    lines = self._alert_text.split('\n')
    current_y = center.y - (len(lines) * ALERT_TEXT_SIZE * FONT_SCALE) / 2
    for line in lines:
      measure = measure_text_cached(self._font, line, ALERT_TEXT_SIZE, 0)
      rl.draw_text_ex(self._font, line, rl.Vector2(center.x - measure.x / 2, current_y), ALERT_TEXT_SIZE, 0, text_color)
      current_y += ALERT_TEXT_SIZE * FONT_SCALE
