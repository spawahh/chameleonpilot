"""
Black & white night video, the aircraft HUD treatment for the road camera.

A subclass of upstream's CameraView whose fragment shaders carry one extra
`uniform int night`: when set, the frame renders as pure luma (Rec.601
weights), like a night-vision display. AugmentedRoadView gets this class via
an import alias, so only the ROAD view desaturates — the driver-camera dialog
and every other CameraView user keep the stock shader.

Both shader variants mirror upstream's exactly when the uniform is 0: the TICI
path keeps its 1/1.28 gamma in BOTH branches and writes fragColor once (the
mici copy of this idea has a double-write and a missing gamma in its else
branch — deliberately not reproduced), and the PC path keeps upstream's
NV12-to-RGB math. Upstream's shader is compiled first by the parent
constructor and replaced here — unloaded before the swap, so nothing leaks.

The uniform is driven per frame from the toggle AND the active night palette,
so the video only goes monochrome while the theme itself is in night mode.
"""
import pyray as rl

from openpilot.selfdrive.ui import themes
from openpilot.selfdrive.ui.onroad.cameraview import TICI, VERSION, VERTEX_SHADER, CameraView
from openpilot.selfdrive.ui.ui_state import ui_state

if TICI:
  NIGHT_FRAGMENT_SHADER = """
    #version 300 es
    #extension GL_OES_EGL_image_external_essl3 : enable
    precision mediump float;
    in vec2 fragTexCoord;
    uniform samplerExternalOES texture0;
    uniform int night;
    out vec4 fragColor;
    void main() {
      vec4 color = texture(texture0, fragTexCoord);
      vec3 rgb = color.rgb;
      if (night == 1) {
        rgb = vec3(dot(rgb, vec3(0.299, 0.587, 0.114)));
      }
      fragColor = vec4(pow(rgb, vec3(1.0/1.28)), color.a);
    }
  """
else:
  NIGHT_FRAGMENT_SHADER = VERSION + """
    in vec2 fragTexCoord;
    uniform sampler2D texture0;
    uniform sampler2D texture1;
    uniform int night;
    out vec4 fragColor;
    void main() {
      float y = texture(texture0, fragTexCoord).r;
      vec2 uv = texture(texture1, fragTexCoord).ra - 0.5;
      vec3 rgb = vec3(y + 1.402*uv.y, y - 0.344*uv.x - 0.714*uv.y, y + 1.772*uv.x);
      if (night == 1) {
        rgb = vec3(y);
      }
      fragColor = vec4(rgb, 1.0);
    }
  """


class NightCameraView(CameraView):
  def __init__(self, name: str, stream_type):
    super().__init__(name, stream_type)
    # the parent compiled the stock shader from module globals; swap it for
    # ours, releasing the stock one so nothing leaks
    rl.unload_shader(self.shader)
    self.shader = rl.load_shader_from_memory(VERTEX_SHADER, NIGHT_FRAGMENT_SHADER)
    self._texture1_loc = rl.get_shader_location(self.shader, "texture1") if not TICI else -1
    self._night_loc = rl.get_shader_location(self.shader, "night")
    self._night_val = rl.ffi.new("int[1]", [0])

  def _render(self, rect: rl.Rectangle) -> None:
    self._night_val[0] = 1 if (ui_state.night_video and themes.night.is_night) else 0
    rl.set_shader_value(self.shader, self._night_loc, self._night_val, rl.ShaderUniformDataType.SHADER_UNIFORM_INT)
    super()._render(rect)
