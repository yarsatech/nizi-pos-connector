"""
Tests for device_manager.py
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from device_manager import DeviceManager


class TestDeviceManagerHelpers(unittest.TestCase):

    def setUp(self):
        self.device = DeviceManager()

    def test_extract_device_id_valid(self):
        self.assertEqual(self.device._extract_device_id("NIZIPOS_B31"), "NIZIPOSB31")
        self.assertEqual(self.device._extract_device_id("NIZI_POS_B30"), "NIZIPOSB30")
        self.assertEqual(self.device._extract_device_id("nizipos_b32"), "NIZIPOSB32")
        self.assertEqual(self.device._extract_device_id("nizi_pos_b33"), "NIZIPOSB33")

    def test_extract_device_id_invalid(self):
        self.assertIsNone(self.device._extract_device_id(""))
        self.assertIsNone(self.device._extract_device_id(None))
        self.assertIsNone(self.device._extract_device_id("OTHER_DEVICE"))


class TestDeviceManagerCommands(unittest.TestCase):

    def setUp(self):
        self.device = DeviceManager()
        self.device.send_command = MagicMock(return_value={"success": True, "error": None})

    def test_send_idle(self):
        self.device.send_idle()
        self.device.send_command.assert_called_with("IDLE")

    def test_send_text(self):
        self.device.send_text("Hello", "World", "Test")
        self.device.send_command.assert_called_with("TEXT**Hello**World**Test")

    def test_send_qr(self):
        self.device.send_qr("Rs. 100", "Scan to pay", "https://yarsa.tech")
        self.device.send_command.assert_called_with("QR**Rs. 100**Scan to pay**https://yarsa.tech")

    def test_send_wait(self):
        self.device.send_wait("Rs. 100", "Processing...")
        self.device.send_command.assert_called_with("WAIT**Rs. 100**Processing...")

    def test_send_pass(self):
        self.device.send_pass("Success", "Payment OK")
        self.device.send_command.assert_called_with("PASS**Success**Payment OK")

    def test_send_fail(self):
        self.device.send_fail("Rs. 100", "Failed")
        self.device.send_command.assert_called_with("FAIL**Rs. 100**Failed")

    def test_send_warn(self):
        self.device.send_warn("Warning", "Attention")
        self.device.send_command.assert_called_with("WARN**Warning**Attention")

    def test_send_info(self):
        self.device.send_info("Info", "Details")
        self.device.send_command.assert_called_with("INFO**Info**Details")

    def test_send_reset(self):
        self.device.send_reset()
        self.device.send_command.assert_called_with("RESET")

    def test_send_format(self):
        self.device.send_format()
        self.device.send_command.assert_called_with("FORMAT")

    def test_send_wake(self):
        self.device.send_wake()
        self.device.send_command.assert_called_with("WAKE")

    def test_set_volume(self):
        self.device.set_volume(80)
        self.device.send_command.assert_called_with("VOLUME**80")

    def test_set_brightness(self):
        self.device.set_brightness(50)
        self.device.send_command.assert_called_with("BRIGHTNESS**50")

    def test_set_screentime(self):
        self.device.set_screentime(120)
        self.device.send_command.assert_called_with("SCREENTIME**120")

    def test_set_timeout(self):
        # set_timeout takes milliseconds natively
        self.device.set_timeout(300000, 20000)
        self.device.send_command.assert_called_with("TIMEOUT**300000**20000")

    def test_activate_buzzer(self):
        self.device.activate_buzzer(1)
        self.device.send_command.assert_called_with("ACTIVATE_BUZZER**1")
        self.device.activate_buzzer(0)
        self.device.send_command.assert_called_with("ACTIVATE_BUZZER**0")

    def test_set_ble(self):
        self.device.set_ble(True)
        self.device.send_command.assert_called_with("BLE_ON")
        self.device.set_ble(False)
        self.device.send_command.assert_called_with("BLE_OFF")

    def test_set_idle_single(self):
        self.device.set_idle_single("IMG1")
        self.device.send_command.assert_called_with("IDLE_SINGLE**IMG1")

    def test_set_idle_cycle(self):
        self.device.set_idle_cycle("IMG1", 30000, "IMG2", 60000)
        self.device.send_command.assert_called_with("IDLE_CYCLE**IMG1**30000**IMG2**60000")

    def test_set_idle_sleep(self):
        self.device.set_idle_sleep("IMG1", 45000)
        self.device.send_command.assert_called_with("IDLE_SLEEP**IMG1**45000")
        
        # Test minimum limit clamp (30000 ms)
        self.device.set_idle_sleep("IMG1", 15000)
        self.device.send_command.assert_called_with("IDLE_SLEEP**IMG1**30000")

    def test_set_idle_sleep_wake(self):
        self.device.set_idle_sleep_wake("IMG1", 45000, 150000)
        self.device.send_command.assert_called_with("IDLE_SLEEP_WAKE**IMG1**45000**150000")

        # Test minimum limit clamp (30000 ms)
        self.device.set_idle_sleep_wake("IMG1", 20000, 150000)
        self.device.send_command.assert_called_with("IDLE_SLEEP_WAKE**IMG1**30000**150000")


if __name__ == "__main__":
    unittest.main()
