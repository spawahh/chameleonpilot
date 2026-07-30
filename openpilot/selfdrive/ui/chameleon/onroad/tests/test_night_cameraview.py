"""Night-video decision logic and wiring.

The shader itself needs a GL context and a dark road — device-only. What can
be pinned offline: the uniform follows toggle AND night-palette state, the
shader source keeps upstream's math when the uniform is 0, and only the road
view gets the subclass (the driver camera must never desaturate).
"""
import unittest
from unittest import mock

import pyray as rl

from openpilot.selfdrive.ui.chameleon.onroad import night_cameraview as ncv
from openpilot.selfdrive.ui.chameleon.onroad.night_cameraview import NIGHT_FRAGMENT_SHADER, NightCameraView


class FakeUIState:
  def __init__(self, night_video=True):
    self.night_video = night_video


class TestNightDecision(unittest.TestCase):
  def setUp(self):
    self.ui_state = FakeUIState()
    self._patch(mock.patch.object(ncv, 'ui_state', self.ui_state))
    self.set_value = self._patch(mock.patch.object(ncv.rl, 'set_shader_value'))
    self._patch(mock.patch.object(ncv.CameraView, '_render'))

    self.view = NightCameraView.__new__(NightCameraView)
    self.view.shader = mock.Mock()
    self.view._night_loc = 7
    self.view._night_val = rl.ffi.new("int[1]", [0])
    # __init__ was bypassed, so the real __del__ -> close() would hit missing
    # attributes at GC time — an unraisable AttributeError that pytest pins on
    # whatever test happens to be running (the source of an intermittent CI red)
    self.view.close = lambda: None

  def _patch(self, patcher):
    patched = patcher.start()
    self.addCleanup(patcher.stop)
    return patched

  def _night(self, is_night):
    patcher = mock.patch.object(ncv.themes.night, 'is_night', is_night)
    patcher.start()
    self.addCleanup(patcher.stop)

  def test_on_at_night(self):
    self._night(True)
    self.view._render(rl.Rectangle(0, 0, 100, 100))

    self.assertEqual(self.view._night_val[0], 1)
    self.set_value.assert_called_once()

  def test_off_in_daylight_even_with_the_toggle_on(self):
    """Follows the night palette: toggle on but day means full color."""
    self._night(False)
    self.view._render(rl.Rectangle(0, 0, 100, 100))

    self.assertEqual(self.view._night_val[0], 0)

  def test_off_when_toggle_is_off_even_at_night(self):
    self._night(True)
    self.ui_state.night_video = False
    self.view._render(rl.Rectangle(0, 0, 100, 100))

    self.assertEqual(self.view._night_val[0], 0)


class TestShaderSource(unittest.TestCase):
  def test_uniform_and_luma_present(self):
    from openpilot.selfdrive.ui.onroad.cameraview import TICI
    self.assertIn("uniform int night", NIGHT_FRAGMENT_SHADER)
    if TICI:
      self.assertIn("0.299, 0.587, 0.114", NIGHT_FRAGMENT_SHADER)  # Rec.601 from RGB
    else:
      self.assertIn("vec3(y)", NIGHT_FRAGMENT_SHADER)  # the Y plane already is luma

  def test_single_fragcolor_write(self):
    """The mici shader's double-write bug must not be reproduced."""
    writes = NIGHT_FRAGMENT_SHADER.count("fragColor =")
    self.assertEqual(writes, 1)

  def test_stock_math_preserved_when_uniform_off(self):
    """Whichever variant compiled for this platform keeps upstream's math."""
    from openpilot.selfdrive.ui.onroad.cameraview import TICI
    if TICI:
      self.assertIn("1.0/1.28", NIGHT_FRAGMENT_SHADER)  # gamma in every branch
    else:
      self.assertIn("y + 1.402*uv.y", NIGHT_FRAGMENT_SHADER)  # NV12 -> RGB


class TestWiring(unittest.TestCase):
  def test_road_view_gets_the_subclass(self):
    import openpilot.selfdrive.ui.onroad.augmented_road_view as arv

    with open(arv.__file__, encoding="utf-8") as f:
      source = f.read()
    self.assertIn("from openpilot.selfdrive.ui.chameleon.onroad.night_cameraview import NightCameraView as CameraView", source)

  def test_driver_camera_keeps_the_stock_base(self):
    """The driver preview must never desaturate."""
    import openpilot.selfdrive.ui.onroad.driver_camera_dialog as dcd

    with open(dcd.__file__, encoding="utf-8") as f:
      source = f.read()
    self.assertNotIn("night_cameraview", source)
    self.assertIn("from openpilot.selfdrive.ui.onroad.cameraview import CameraView", source)


if __name__ == '__main__':
  unittest.main()
