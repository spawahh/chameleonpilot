"""
Fork subclasses of the two upstream onroad renderers.

These exist so hiding a stock HUD element never means editing the upstream
renderer: each override is a visibility gate around one upstream draw method,
and `AugmentedRoadView` constructs these classes instead of the parents — the
seam the aircraft layout will also use.

Failure mode is deliberately fail-safe: if upstream renames an overridden
method, the override stops being called and stock drawing returns — the hide
stops working, nothing crashes. test_renderers.py pins each overridden name
against the parent class so that drift is loud.
"""
from openpilot.selfdrive.ui.onroad.driver_state import DriverStateRenderer
from openpilot.selfdrive.ui.onroad.hud_renderer import HudRenderer
from openpilot.selfdrive.ui.onroad.model_renderer import ModelRenderer
from openpilot.selfdrive.ui.ui_state import ui_state


class ChameleonModelRenderer(ModelRenderer):
  def _draw_lane_lines(self) -> None:
    if not ui_state.hide_lane_lines:
      super()._draw_lane_lines()

  def _draw_path(self, sm) -> None:
    if not ui_state.hide_driving_path:
      super()._draw_path(sm)

  def _draw_lead_indicator(self) -> None:
    # the target designator replaces the chevron, it does not stack on it
    if not ui_state.target_designator:
      super()._draw_lead_indicator()


class ChameleonHudRenderer(HudRenderer):
  def __init__(self):
    super().__init__()
    # an invisible Widget neither draws nor takes taps, so user_interacting()
    # goes quiet with it and road-view taps route normally
    self._exp_button.set_visible(lambda: not ui_state.hide_wheel_button)

  def _draw_set_speed(self, rect) -> None:
    if not ui_state.hide_speed_cluster:
      super()._draw_set_speed(rect)

  def _draw_current_speed(self, rect) -> None:
    if not ui_state.hide_speed_cluster:
      super()._draw_current_speed(rect)


class ChameleonDriverStateRenderer(DriverStateRenderer):
  # gates the draw, not Widget.render: upstream's own set_visible gate (no face
  # during a full-screen alert, none before driverStateV2) must keep running
  def _render(self, rect) -> None:
    if not ui_state.hide_driver_face:
      super()._render(rect)
