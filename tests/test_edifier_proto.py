import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import edifier_proto as ep
import headset_battery as hb


def frame(level, command=0xD0):
    data = bytes([0xBB, 2, command, level])
    return data + ((sum(data) + 0x2019) & 0xFFFF).to_bytes(2, "big")


class DirectProtocol(unittest.TestCase):
    def test_real_captured_94_percent_reply(self):
        self.assertEqual(ep.parse_battery_frame(bytes.fromhex("BB 02 D0 5E 22 04")), 94)

    def test_zero_is_valid_in_a_checked_direct_reply(self):
        self.assertEqual(ep.parse_battery_frame(frame(0)), 0)

    def test_bad_crc_length_and_unrelated_commands_are_ignored(self):
        for raw in (b"", frame(94)[:-1], frame(94)+b"\0", frame(94, 0xCC),
                    frame(94)[:-1]+b"\0", b"\xAA"+frame(94)[1:]):
            with self.subTest(raw=raw):
                self.assertIsNone(ep.parse_battery_frame(raw))

    def test_out_of_range_is_not_clamped_to_full(self):
        self.assertIsNone(ep.parse_battery_frame(frame(255)))

    def test_stream_finds_checked_battery_after_noise_or_bad_candidate(self):
        result = ep.find_battery_frame(b"noise"+b"\xBB\x02\xD0\x5E\0\0"+frame(94))
        self.assertEqual(result.level, 94)
        self.assertIsNone(ep.find_battery_frame(frame(94)[:4]))

    def test_only_battery_get_packet_is_exposed(self):
        self.assertEqual(ep.BATTERY_QUERY, bytes.fromhex("AA 01 D0 21 94"))


class PreferDirectReading(unittest.TestCase):
    def setUp(self):
        self.node = SimpleNamespace(name="EDIFIER W820NB 双金标版 Hands-Free AG", is_handsfree=True,
                                    instance_id="BTHENUM\\PROFILE\\7&0&001122AABBCC_C0000",
                                    battery=100, has_property=True)
        self.patch = patch.dict(sys.modules, {
            "bt_battery": SimpleNamespace(displayable_devices=lambda: [self.node]),
            "win_bluetooth": SimpleNamespace(connection_states=lambda: {"001122AABBCC": True})})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_windows_full_is_replaced_by_actual_reply(self):
        with patch.object(ep, "read_battery", return_value=ep.Reading(94, "live", frame(94))) as query:
            result = hb.read_headsets()[0]
            self.assertEqual(result.level, 94)
            self.assertTrue(result.direct)
            query.assert_called_once_with("001122AABBCC")

    def test_query_failure_never_promotes_windows_full_to_live(self):
        with patch.object(ep, "read_battery", return_value=ep.Reading(detail="timeout")):
            result = hb.read_headsets()[0]
            self.assertIsNone(result.level)
            self.assertFalse(result.direct)
            self.assertIn("参考值 100%", result.detail)

    def test_disconnected_headset_is_not_queried(self):
        with patch.dict(sys.modules, {"win_bluetooth": SimpleNamespace(connection_states=lambda: {})}):
            with patch.object(ep, "read_battery") as query:
                result = hb.read_headsets()[0]
                self.assertIsNone(result.level)
                query.assert_not_called()

    def test_other_models_remain_explicit_system_reference(self):
        self.node.name = "Other Headset Hands-Free AG"
        with patch.object(ep, "read_battery") as query:
            result = hb.read_headsets()[0]
            self.assertEqual(result.level, 100)
            self.assertFalse(result.direct)
            self.assertIn("参考值", result.detail)
            query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
