"""Manual screen brightness.

The value worth pinning hardest is 0 (Auto), because it is the default: every
device that never touches this setting must keep upstream's automatic backlight
untouched, bit for bit.
"""
import ast
import inspect
import types
import unittest
from unittest import mock

from openpilot.selfdrive.ui.chameleon import brightness


class TestResolve(unittest.TestCase):
  def test_auto_passes_the_automatic_value_straight_through(self):
    """The default must be a no-op on upstream's backlight."""
    for auto in (0.0, 30.0, 47.5, 100.0):
      with self.subTest(auto=auto):
        self.assertEqual(brightness.resolve(brightness.AUTO, auto), auto)

  def test_a_level_replaces_the_automatic_value(self):
    self.assertEqual(brightness.resolve(40, 100.0), 40.0)
    self.assertEqual(brightness.resolve(100, 30.0), 100.0)

  def test_a_level_can_go_below_the_automatic_floor(self):
    """The point of the setting: Auto never goes under 30% onroad."""
    self.assertLess(brightness.resolve(brightness.MIN_PERCENT, 30.0), 30.0)

  def test_below_the_floor_clamps_up(self):
    """A screen too dark to read is a screen you cannot fix the setting on."""
    for percent in (1, -20):
      with self.subTest(percent=percent):
        self.assertEqual(brightness.resolve(percent, 50.0), float(brightness.MIN_PERCENT))

  def test_above_full_clamps_down(self):
    self.assertEqual(brightness.resolve(150, 50.0), float(brightness.MAX_PERCENT))

  def test_returns_a_float_for_the_filter(self):
    """It is fed to FirstOrderFilter.update, then rounded."""
    self.assertIsInstance(brightness.resolve(50, 30.0), float)

  def test_the_picker_levels_are_all_readable_and_reach_full(self):
    self.assertEqual(brightness.LEVELS[0], brightness.MIN_PERCENT)
    self.assertEqual(brightness.LEVELS[-1], brightness.MAX_PERCENT)
    self.assertNotIn(brightness.AUTO, brightness.LEVELS)
    for percent in brightness.LEVELS:
      self.assertEqual(brightness.resolve(percent, 50.0), float(percent), "a listed level must not be clamped")


class TestBacklightPath(unittest.TestCase):
  """The setting is only real if it reaches `Device._update_brightness`.

  Pinned behaviourally rather than by reading the source: an upstream rewrite of
  that method must fail here, and Auto must be provably identical to stock.
  """

  def setUp(self):
    from openpilot.selfdrive.ui import ui_state as us
    self.us = us
    self._patch(mock.patch.object(us.device, '_brightness_filter', PassThroughFilter()))
    self._patch(mock.patch.object(us.device, '_awake', True))
    self._patch(mock.patch.object(us.device, '_last_brightness', -1))
    self._patch(mock.patch.object(us.device, '_offroad_brightness', 50))
    self._patch(mock.patch.object(us.ui_state, 'started', False))

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def _brightness_for(self, percent):
    with mock.patch.object(self.us.ui_state, 'brightness_percent', percent):
      self.us.device._update_brightness()
    return self.us.device._brightness_target

  def test_auto_is_upstreams_own_value(self):
    self.assertEqual(self._brightness_for(brightness.AUTO), 50)

  def test_a_level_wins(self):
    self.assertEqual(self._brightness_for(20), 20)

  def test_asleep_still_beats_a_manual_level(self):
    """A manual brightness must never keep the screen lit past the timeout."""
    with mock.patch.object(self.us.device, '_awake', False):
      self.assertEqual(self._brightness_for(100), 0)


class PassThroughFilter:
  """FirstOrderFilter with the 10 s ramp removed, so one call is measurable."""

  def update(self, value):
    return value


class FakeParams:
  """Types matter: an INT key's `get` returns an int, never a string to parse."""

  def __init__(self, values):
    self.values = values

  def get_bool(self, key):
    return bool(self.values.get(key, False))

  def get(self, key, return_default=False):
    return self.values.get(key, 0)


class TestUiParamsRead(unittest.TestCase):
  def test_the_level_lands_on_ui_state(self):
    """`ui_params.refresh` runs at both UIState param sites. A setting read in
    only one of them takes effect on restart instead of immediately — a bug this
    fork has shipped before, which is why there is one mapping."""
    from openpilot.selfdrive.ui.chameleon import ui_params
    state = types.SimpleNamespace()

    ui_params.refresh(state, FakeParams({"ChameleonBrightness": 30}))

    self.assertEqual(state.brightness_percent, 30)

  def test_unset_reads_as_auto(self):
    from openpilot.selfdrive.ui.chameleon import ui_params
    state = types.SimpleNamespace()

    ui_params.refresh(state, FakeParams({}))

    self.assertEqual(state.brightness_percent, brightness.AUTO)


class TestNoImports(unittest.TestCase):
  def test_the_module_imports_nothing(self):
    """`ui_state` imports this at module load, so anything from the widget or
    params layers here risks an import cycle — same rule as `ui_params`."""
    tree = ast.parse(inspect.getsource(brightness))
    imports = [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]

    self.assertEqual(imports, [])


if __name__ == '__main__':
  unittest.main()
