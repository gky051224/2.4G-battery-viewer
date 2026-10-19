import unittest
from types import SimpleNamespace
from unittest.mock import patch

import headset_battery as hb


def node(name="Test Headset", address="001122AABBCC", battery=90, has=True):
    return SimpleNamespace(name=name + " Hands-Free AG", is_handsfree=True,
                           instance_id=f"BTHENUM\\PROFILE\\7&TEST&0&{address}_C00000000",
                           battery=battery, has_property=has)


class ConnectionAwareBattery(unittest.TestCase):
    def test_connected_headset_uses_matching_address_and_removes_profile_suffix(self):
        result = hb.combine([node()], {"001122AABBCC": True})[0]
        self.assertEqual((result.name, result.level, result.connected), ("Test Headset", 90, True))

    def test_disconnected_cached_battery_is_hidden(self):
        result = hb.combine([node(battery=100)], {"001122AABBCC": False})[0]
        self.assertIsNone(result.level)
        self.assertFalse(result.connected)

    def test_same_name_on_different_address_does_not_borrow_connection(self):
        result = hb.combine([node()], {"FFEEDDCCBBAA": True})[0]
        self.assertIsNone(result.level)

    def test_missing_or_invalid_battery_is_unknown_while_connected(self):
        for value, has in ((None, False), (100, False), (0, True), (101, True), (255, True)):
            with self.subTest(value=value, has=has):
                result = hb.combine([node(battery=value, has=has)], {"001122AABBCC": True})[0]
                self.assertIsNone(result.level)
                self.assertTrue(result.connected)

    def test_selected_headset_does_not_fall_back_to_another(self):
        result = hb.combine([node()], {"001122AABBCC": True}, "Other Headset")[0]
        self.assertEqual(result.name, "Other Headset")
        self.assertIsNone(result.level)

    def test_duplicate_profiles_prefer_valid_reading(self):
        results = hb.combine([node(battery=None), node(battery=80)], {"001122AABBCC": True})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].level, 80)

    def test_non_audio_devices_are_ignored(self):
        item = node()
        item.is_handsfree = False
        result = hb.combine([item], {"001122AABBCC": True})[0]
        self.assertEqual(result.name, "蓝牙耳机")
        self.assertIsNone(result.level)

    def test_auto_only_shows_connected_headsets(self):
        readings = [hb.HeadsetReading("Disconnected"), hb.HeadsetReading("Connected", 100, True)]
        with patch.object(hb, "read_headsets", return_value=readings):
            self.assertEqual(hb.selected_headsets("auto"), [readings[1]])
            self.assertEqual(hb.selected_headsets("all"), readings)

    def test_disconnect_after_success_does_not_retain_level(self):
        item = node()
        self.assertEqual(hb.combine([item], {"001122AABBCC": True})[0].level, 90)
        self.assertIsNone(hb.combine([item], {})[0].level)


if __name__ == "__main__":
    unittest.main()
