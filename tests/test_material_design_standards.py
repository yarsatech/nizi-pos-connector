"""
Formal automated test suite verifying Material Design iconography and aesthetic compliance
across both Desktop Qt GUI and Embedded Web Dashboard.
"""

import sys
import unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QPushButton

from ui_app import TrayFlyout
from device_manager import DeviceManager

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

BASE_DIR = Path(__file__).resolve().parent.parent


class TestMaterialDesignStandards(unittest.TestCase):
    """Verifies that Material Design concepts and Material symbols are consistently utilized."""

    def test_material_svg_assets_integrity(self):
        """All core Material SVG icons must exist and contain valid 24x24 vector paths."""
        icons_dir = BASE_DIR / "assets" / "icons"
        self.assertTrue(icons_dir.exists(), "assets/icons directory must exist")

        required_icons = [
            "settings.svg",
            "refresh.svg",
            "restart_alt.svg",
            "bluetooth.svg",
            "bluetooth_disabled.svg",
            "key.svg",
            "lock_reset.svg",
            "download.svg",
            "notifications.svg",
            "notifications_off.svg",
            "folder_open.svg",
            "bedtime.svg",
            "light_mode.svg",
            "delete_forever.svg",
            "qr_code_2.svg",
            "hourglass_top.svg",
            "check_circle.svg",
            "warning.svg",
            "content_copy.svg",
            "power.svg",
            "power_off.svg",
            "send.svg",
            "info.svg",
            "cancel.svg",
        ]

        for icon_name in required_icons:
            icon_file = icons_dir / icon_name
            self.assertTrue(icon_file.exists(), f"Material SVG icon '{icon_name}' is missing")
            content = icon_file.read_text(encoding="utf-8")
            self.assertIn("<svg", content)
            self.assertIn('viewBox="0 0 24 24"', content)

    def test_web_dashboard_material_symbols_usage(self):
        """Web dashboard HTML must load Material Symbols and contain zero raw emojis."""
        index_html = (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")

        # 1. Google Material Symbols font link
        self.assertIn("Material+Symbols+Outlined", index_html)

        # 2. Material symbols classes
        self.assertIn("material-symbols-outlined", index_html)

        # 3. Explicit check that amateur emojis are not present in raw text
        forbidden_emojis = [
            "🔌", "🚀", "📱", "📺", "⚙️", "🖼", "⌨️", "📋", "🔑",
            "⚡", "💤", "☀️", "🔄", "🗑", "⏳", "📤",
        ]
        for emoji in forbidden_emojis:
            self.assertNotIn(emoji, index_html, f"Raw emoji '{emoji}' found in static/index.html")

    def test_desktop_app_buttons_have_material_icons_and_no_emojis(self):
        """Desktop UI buttons must have QIcons attached and no raw emoji strings."""
        dev = DeviceManager()
        flyout = TrayFlyout(dev, web_port=9121)

        # Verify buttons have icons bound and no emoji prefixes
        test_buttons = [
            (flyout.btn_idle, "IDLE"),
            (flyout.btn_wake, "WAKE"),
            (flyout.btn_restart, "RESTART"),
            (flyout.btn_format, "FORMAT"),
            (flyout.btn_quick_qr, "Send QR"),
            (flyout.btn_quick_wait, "WAIT"),
            (flyout.btn_quick_pass, "PASS"),
            (flyout.btn_ble_on, "BLE ON"),
            (flyout.btn_ble_off, "BLE OFF"),
            (flyout.btn_ble_change_pin, "Change PIN"),
            (flyout.btn_ble_reset_pin, "Reset PIN"),
            (flyout.btn_update_language, "Download Language Firmware"),
            (flyout.btn_buzzer_on, "Enable"),
            (flyout.btn_buzzer_off, "Disable"),
            (flyout.btn_open_log, "Open Log File"),
            (flyout.btn_refresh_log, "Refresh Logs"),
            (flyout.btn_settings, "Settings"),
            (flyout.btn_update_firmware, "Open Update Page"),
            (flyout.btn_action, "Connect Now"),
            (flyout.btn_rescan, "Rescan"),
            (flyout.btn_quit, "Quit"),
            (flyout.btn_send_status, "Send"),
            (flyout.btn_send_qr, "Send"),
            (flyout.btn_send_text, "Send"),
            (flyout.btn_select_wallpaper, "Browse Wallpaper…"),
            (flyout.btn_upload_wallpaper, "Save Wallpaper to Device"),
            (flyout.btn_select_preview, "Browse Preview Image…"),
            (flyout.btn_upload_preview, "Show Preview on Device"),
            (flyout.btn_set_idle, "Set Idle Mode"),
            (flyout.btn_set_timeout, "Set Timeouts"),
        ]

        for btn, expected_text in test_buttons:
            self.assertFalse(btn.icon().isNull(), f"Button '{btn.text()}' must have a valid QIcon")
            self.assertEqual(btn.text(), expected_text)
            for emoji in ["🔌", "🚀", "📱", "📺", "⚙", "🔑", "⚡", "💤", "☀️", "🔄", "🗑", "⏳", "✅", "📡", "🔔", "🔕", "📂", "📲"]:
                self.assertNotIn(emoji, btn.text(), f"Emoji '{emoji}' found in button label '{btn.text()}'")

        flyout.close()


if __name__ == "__main__":
    unittest.main()
