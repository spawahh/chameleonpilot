"""The UI -> soundd chime bus.

What must never regress: a chime is consumed exactly once (no looping ding),
unknown names are silent, and soundd's hook only runs while no real alert
sound is active — a safety alert can never be delayed by a chime.
"""
import unittest

from openpilot.chameleon.chime import CHIMES, AudibleAlert, ChimePoller, request


class FakeParams:
  """ChameleonChime is STRING-typed: get returns the string or None."""

  def __init__(self):
    self.values = {}

  def get(self, key):
    return self.values.get(key)

  def put(self, key, value, block=False):
    if not isinstance(value, str):
      raise TypeError(f"Type mismatch while writing param {key}: {type(value)=}")
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)


class TestChime(unittest.TestCase):
  def setUp(self):
    self.params = FakeParams()
    self.poller = ChimePoller(params=self.params)

  def test_request_then_pop_consumes_once(self):
    request("complete", params=self.params)

    self.assertEqual(self.poller.pop(), AudibleAlert.complete)
    self.assertEqual(self.poller.pop(), AudibleAlert.none)  # consumed, never replays

  def test_idle_is_none(self):
    self.assertEqual(self.poller.pop(), AudibleAlert.none)

  def test_unknown_name_is_silent_and_consumed(self):
    request("airhorn", params=self.params)

    self.assertEqual(self.poller.pop(), AudibleAlert.none)
    self.assertNotIn("ChameleonChime", self.params.values)

  def test_every_chime_is_a_play_once_sound(self):
    """A looping sound here would never stop; only play-once entries allowed."""
    from openpilot.selfdrive.ui.soundd import sound_list
    for name, alert in CHIMES.items():
      self.assertEqual(sound_list[alert][1], 1, f"chime {name!r} must be a play-once sound")

  def test_soundd_hook_yields_to_real_alerts(self):
    """The seam: soundd polls the chime only while no alert sound is active."""
    import openpilot.selfdrive.ui.soundd as soundd
    with open(soundd.__file__, encoding="utf-8") as f:
      source = f.read()
    self.assertIn("if self.current_alert == AudibleAlert.none:", source)
    self.assertIn("self.update_alert(self.chameleon_chime.pop())", source)


if __name__ == '__main__':
  unittest.main()
