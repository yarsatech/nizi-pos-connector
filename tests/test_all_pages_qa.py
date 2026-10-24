"""
Comprehensive End-to-End Automated QA Test Suite for all 7 Stacked Pages and UI controls in TrayFlyout.
Verifies page index alignment, widget initialization, dynamic interactions, and error-free operation.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QLineEdit, QTextEdit, QSlider, QPushButton
from PyQt6.QtCore import Qt

from ui_app import TrayFlyout, SafeComboBox
from device_manager import DeviceManager

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

BASE_DIR = Path(__file__).resolve().parent.parent


class TestAllPagesQA(unittest.TestCase):
    """Rigorous QA verification across all 7 stacked pages of the Desktop Application."""

    def setUp(self):
        self.dev = DeviceManager()
        self.dev._connected = False
        self.dev._port = "COM3"
        self.dev._device_id = "B30"
        self.dev._firmware_id = "v1.2.0"
        self.patcher = patch.object(TrayFlyout, "_fetch_languages", return_value=None)
        self.patcher.start()
        self.flyout = TrayFlyout(self.dev, web_port=9121)

    def tearDown(self):
        self.flyout.close()
        self.patcher.stop()

    def test_page_selector_items_and_count(self):
        """Page selector must have exactly 7 pages matching stack widget count."""
        expected_pages = [
            "Quick Actions",
            "Device Config",
            "Upload Images",
            "Status Screen",
            "QR Display",
            "Text Display",
            "Idle Mode",
        ]
        self.assertEqual(self.flyout.page_selector.count(), 7)
        for i, expected_title in enumerate(expected_pages):
            self.assertEqual(self.flyout.page_selector.itemText(i), expected_title)
        self.assertEqual(self.flyout.stack.count(), 7)

    def test_page_switching_geometry_and_visibility(self):
        """Switching between pages must update stack currentIndex properly."""
        for i in range(7):
            self.flyout.page_selector.setCurrentIndex(i)
            self.assertEqual(self.flyout.stack.currentIndex(), i)
            current_widget = self.flyout.stack.currentWidget()
            self.assertIsNotNone(current_widget)

    def test_page_0_quick_actions(self):
        """Page 0: Quick Actions must trigger corresponding device calls without errors."""
        self.flyout.page_selector.setCurrentIndex(0)
        self.dev._connected = True
        self.dev.send_command = MagicMock(return_value={"success": True})

        # Test each quick action invocation
        self.flyout._quick_send_idle()
        self.dev.send_command.assert_called_with("IDLE")

        self.flyout._quick_send_wake()
        self.dev.send_command.assert_called_with("WAKE")

        self.flyout._quick_send_restart()
        self.dev.send_command.assert_called_with("RESET")

        self.flyout._quick_send_wait()
        self.assertTrue(self.dev.send_command.called)

        self.flyout._quick_send_pass()
        self.assertTrue(self.dev.send_command.called)

    def test_page_1_device_config(self):
        """Page 1: Device Config controls (Sliders, Timeouts, BLE, Buzzer, Logs)."""
        self.flyout.page_selector.setCurrentIndex(1)
        self.dev._connected = True
        self.dev.set_volume = MagicMock(return_value={"success": True})
        self.dev.set_brightness = MagicMock(return_value={"success": True})
        self.dev.set_timeout = MagicMock(return_value={"success": True})

        # Volume slider
        self.flyout.volume_slider.setValue(65)
        self.assertEqual(self.flyout.volume_val_label.text(), "65%")
        self.flyout._send_volume()
        self.dev.set_volume.assert_called_with(65)

        # Brightness slider
        self.flyout.brightness_slider.setValue(90)
        self.assertEqual(self.flyout.brightness_val_label.text(), "90%")
        self.flyout._send_brightness()
        self.dev.set_brightness.assert_called_with(90)

        # Timeouts
        self.flyout.timeout_qr.setText("180")
        self.flyout.timeout_pf.setText("15")
        self.flyout._send_timeout()
        self.dev.set_timeout.assert_called_with(180000, 15000)

    def test_page_2_upload_images(self):
        """Page 2: Upload Images controls and validation."""
        self.flyout.page_selector.setCurrentIndex(2)

        self.assertIsInstance(self.flyout.wallpaper_slot, SafeComboBox)
        self.assertEqual(self.flyout.wallpaper_slot.count(), 2)

        self.assertIsInstance(self.flyout.wallpaper_size, SafeComboBox)
        self.assertEqual(self.flyout.wallpaper_size.count(), 2)

        self.assertFalse(self.flyout.btn_upload_wallpaper.isEnabled())
        self.assertFalse(self.flyout.btn_upload_preview.isEnabled())

    def test_page_3_status_screen(self):
        """Page 3: Status Screen preset changes update fields predictably."""
        self.flyout.page_selector.setCurrentIndex(3)

        # Changing dropdown updates fields
        self.flyout.status_type.setCurrentIndex(1)  # PASS
        self.assertEqual(self.flyout.status_field1.text(), "SUCCESS!")
        self.assertEqual(self.flyout.status_field2.text(), "Payment successful")

        self.flyout.status_type.setCurrentIndex(2)  # WAIT
        self.assertEqual(self.flyout.status_field1.text(), "Rs. 560.50")
        self.assertEqual(self.flyout.status_field2.text(), "Please wait...")

        self.flyout.status_type.setCurrentIndex(3)  # FAIL
        self.assertEqual(self.flyout.status_field1.text(), "Rs. 560.50")
        self.assertEqual(self.flyout.status_field2.text(), "Payment Failed")

        self.flyout.status_type.setCurrentIndex(0)  # INFO
        self.assertEqual(self.flyout.status_field1.text(), "Important")
        self.assertEqual(self.flyout.status_field2.text(), "Keep device connected")

    def test_page_4_qr_display(self):
        """Page 4: QR Display input fields and send dispatch."""
        self.flyout.page_selector.setCurrentIndex(4)
        self.dev._connected = True
        self.dev.send_command = MagicMock(return_value={"success": True})

        self.flyout.qr_amount.setText("Rs. 500.00")
        self.flyout.qr_scan_text.setText("SCAN & PAY")
        self.flyout.qr_payload.setPlainText("upi://pay?pa=merchant@bank&am=500")

        self.flyout._send_qr()
        self.dev.send_command.assert_called_with(
            "QR**Rs. 500.00**SCAN & PAY**upi://pay?pa=merchant@bank&am=500"
        )

    def test_page_5_text_display(self):
        """Page 5: Text Display input fields and send dispatch."""
        self.flyout.page_selector.setCurrentIndex(5)
        self.dev._connected = True
        self.dev.send_command = MagicMock(return_value={"success": True})

        self.flyout.text_title.setText("Special Notice")
        self.flyout.text_subtitle.setText("Banking Channel")
        self.flyout.text_msg.setPlainText("Service operational until 6 PM.")

        self.flyout._send_text()
        self.dev.send_command.assert_called_with(
            "TEXT**Special Notice**Banking Channel**Service operational until 6 PM."
        )

    def test_page_6_idle_mode_dynamic_controls(self):
        """Page 6: Idle Mode dropdown dynamic toggling of image/time inputs."""
        self.flyout.page_selector.setCurrentIndex(6)

        # SLEEP_WAKE: (index 0) - IMG1, sleep_sec, wake_sec visible; IMG2 and cycle times hidden
        self.flyout.idle_mode_dropdown.setCurrentIndex(0)
        self.assertFalse(self.flyout.idle_img1.isHidden())
        self.assertFalse(self.flyout.idle_sleep_sec.isHidden())
        self.assertFalse(self.flyout.idle_wake_sec.isHidden())
        self.assertTrue(self.flyout.idle_img2.isHidden())
        self.assertTrue(self.flyout.idle_time1_sec.isHidden())

        # SINGLE: (index 1) - Only IMG1 visible
        self.flyout.idle_mode_dropdown.setCurrentIndex(1)
        self.assertFalse(self.flyout.idle_img1.isHidden())
        self.assertTrue(self.flyout.idle_sleep_sec.isHidden())
        self.assertTrue(self.flyout.idle_img2.isHidden())

        # CYCLE: (index 2) - IMG1, IMG2, time1, time2 visible
        self.flyout.idle_mode_dropdown.setCurrentIndex(2)
        self.assertFalse(self.flyout.idle_img1.isHidden())
        self.assertFalse(self.flyout.idle_img2.isHidden())
        self.assertFalse(self.flyout.idle_time1_sec.isHidden())
        self.assertFalse(self.flyout.idle_time2_sec.isHidden())

        # SLEEP: (index 3) - IMG1 and sleep_sec visible, wake_sec and IMG2 hidden
        self.flyout.idle_mode_dropdown.setCurrentIndex(3)
        self.assertFalse(self.flyout.idle_img1.isHidden())
        self.assertFalse(self.flyout.idle_sleep_sec.isHidden())
        self.assertTrue(self.flyout.idle_wake_sec.isHidden())
        self.assertTrue(self.flyout.idle_img2.isHidden())

    def test_connection_state_visual_updates(self):
        """Device connected vs disconnected toggles commands area visibility and button icons."""
        # Disconnected state
        self.flyout._on_status_updated(False, "")
        self.assertTrue(self.flyout.commands_container.isHidden())
        self.assertEqual(self.flyout.btn_action.text(), "Connect Now")
        self.assertFalse(self.flyout.btn_action.icon().isNull())

        # Connected state
        self.flyout._on_status_updated(True, "COM3")
        self.assertFalse(self.flyout.commands_container.isHidden())
        self.assertEqual(self.flyout.btn_action.text(), "Disconnect")
        self.assertFalse(self.flyout.btn_action.icon().isNull())


if __name__ == "__main__":
    unittest.main()
