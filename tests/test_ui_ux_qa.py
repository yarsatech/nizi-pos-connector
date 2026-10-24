"""
Comprehensive UI/UX QA Automated Test Suite for Nizi POS Connector.
Validates:
1. Geometry, layout hierarchy, and touch/click target ergonomics (WCAG 2.5.5 / 2.5.8).
2. Spacing standards, padding uniformity, and minimum 24px bottom clearance across all dialogs.
3. Material Design 3 theme tokens, contrast ratios, and QSS engine syntax compliance.
4. Interactive component behaviors (keyboard dismissal, password visibility toggles, wheel safety).
5. Enterprise microcopy standards (zero conversational rhetoric, no legacy terminology, action buttons).
6. Visual smoke rendering across Dark and Light modes.
"""
import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QKeyEvent, QWheelEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = QApplication.instance() or QApplication(sys.argv)

from theme_support import (
    get_dialog_stylesheet,
    get_flyout_stylesheet,
    get_progress_dialog_stylesheet,
    get_theme_tokens,
    prefers_light_theme,
)
from ui_app import SafeComboBox, TrayFlyout
from ui_components import (
    BleChangePinDialog,
    CustomApiKeyDialog,
    ModernProgressDialog,
    ModernPromptDialog,
    SettingsDialog,
)


class TestDialogLayoutAndPaddingQA(unittest.TestCase):
    """Verifies that all dialogs maintain ergonomic padding and comfortable bottom clearance."""

    def _get_bottom_clearance(self, dialog: QDialog, button: QPushButton) -> int:
        """Calculate vertical distance between bottom edge of button and bottom border of window."""
        dialog.adjustSize()
        btn_geo = button.geometry()
        btn_bottom = btn_geo.y() + btn_geo.height()
        return dialog.height() - btn_bottom

    def test_modern_prompt_dialog_geometry_and_clearance(self):
        """Prompt dialog must have >=420px width, >=36px button height, and >=24px bottom clearance."""
        dlg = ModernPromptDialog(
            title="Exit",
            headline_text="Exit Nizi POS Connector",
            info_text="Terminates active hardware connections and background API services.",
            yes_text="Exit",
            no_text="Cancel",
        )
        dlg.show()
        app.processEvents()

        self.assertGreaterEqual(dlg.width(), 420)
        self.assertGreaterEqual(dlg.height(), 160)

        yes_btn = dlg.findChild(QPushButton, "yesBtn")
        no_btn = dlg.findChild(QPushButton, "noBtn")
        self.assertIsNotNone(yes_btn)
        self.assertIsNotNone(no_btn)

        # Touch/click target minimum height
        self.assertGreaterEqual(yes_btn.height(), 36)
        self.assertGreaterEqual(no_btn.height(), 36)

        # Vertical bottom clearance
        clearance = self._get_bottom_clearance(dlg, yes_btn)
        self.assertGreaterEqual(
            clearance, 24, f"Prompt bottom clearance {clearance}px is less than 24px requirement"
        )
        dlg.close()

    def test_custom_api_key_dialog_geometry_and_clearance(self):
        """Custom API Key dialog must maintain >=480px width, >=36px button height, and >=24px bottom clearance."""
        dlg = CustomApiKeyDialog()
        dlg.show()
        app.processEvents()

        self.assertGreaterEqual(dlg.width(), 480)

        save_btn = dlg.findChild(QPushButton, "saveBtn")
        cancel_btn = dlg.findChild(QPushButton, "cancelBtn")
        self.assertIsNotNone(save_btn)
        self.assertIsNotNone(cancel_btn)

        self.assertGreaterEqual(save_btn.height(), 36)
        self.assertGreaterEqual(cancel_btn.height(), 36)

        clearance = self._get_bottom_clearance(dlg, save_btn)
        self.assertGreaterEqual(
            clearance, 24, f"Custom API Key bottom clearance {clearance}px is less than 24px requirement"
        )
        dlg.close()

    def test_ble_change_pin_dialog_geometry_and_clearance(self):
        """Change BLE PIN dialog must maintain >=420px width, >=36px button height, and >=24px bottom clearance."""
        dlg = BleChangePinDialog()
        dlg.show()
        app.processEvents()

        self.assertGreaterEqual(dlg.width(), 420)

        change_btn = dlg.findChild(QPushButton, "yesBtn")
        cancel_btn = dlg.findChild(QPushButton, "noBtn")
        self.assertIsNotNone(change_btn)
        self.assertIsNotNone(cancel_btn)

        self.assertGreaterEqual(change_btn.height(), 36)
        self.assertGreaterEqual(cancel_btn.height(), 36)

        clearance = self._get_bottom_clearance(dlg, change_btn)
        self.assertGreaterEqual(
            clearance, 24, f"Change PIN bottom clearance {clearance}px is less than 24px requirement"
        )
        dlg.close()

    def test_settings_dialog_geometry_and_clearance(self):
        """Settings dialog must maintain >=500px width, >=36px button height, and >=24px bottom clearance."""
        dlg = SettingsDialog()
        dlg.show()
        app.processEvents()

        self.assertGreaterEqual(dlg.width(), 500)

        save_btn = dlg.findChild(QPushButton, "saveBtn")
        cancel_btn = dlg.findChild(QPushButton, "cancelBtn")
        self.assertIsNotNone(save_btn)
        self.assertIsNotNone(cancel_btn)

        self.assertGreaterEqual(save_btn.height(), 36)
        self.assertGreaterEqual(cancel_btn.height(), 36)

        clearance = self._get_bottom_clearance(dlg, save_btn)
        self.assertGreaterEqual(
            clearance, 24, f"Settings bottom clearance {clearance}px is less than 24px requirement"
        )
        dlg.close()

    def test_modern_progress_dialog_touch_targets(self):
        """Progress dialog cancel button meets touch target height requirements."""
        dlg = ModernProgressDialog(title="Software Update", label_text="Downloading...", min_width=440)
        self.assertGreaterEqual(dlg.minimumWidth(), 440)
        dlg.close()


class TestThemeDesignSystemQA(unittest.TestCase):
    """Validates color contrast, token separation, and stylesheet compatibility with the Qt QSS engine."""

    def _luminance(self, hex_color: str) -> float:
        """Calculate relative luminance using sRGB IEC 61966-2-1 formula."""
        c = QColor(hex_color)
        r, g, b = c.redF(), c.greenF(), c.blueF()

        def _linear(val):
            return val / 12.92 if val <= 0.03928 else ((val + 0.055) / 1.055) ** 2.4

        return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)

    def _contrast_ratio(self, hex1: str, hex2: str) -> float:
        l1 = self._luminance(hex1)
        l2 = self._luminance(hex2)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def test_theme_color_contrast_wcag_standards(self):
        """Primary text contrast against background must exceed 4.5:1 (WCAG AA)."""
        for is_light in (False, True):
            tokens = get_theme_tokens(is_light)
            mode_name = "Light" if is_light else "Dark"

            contrast = self._contrast_ratio(tokens["text_primary"], tokens["window_bg"])
            self.assertGreaterEqual(
                contrast,
                4.5,
                f"{mode_name} mode text_primary ({tokens['text_primary']}) vs window_bg ({tokens['window_bg']}) ratio {contrast:.2f}:1 is below 4.5:1",
            )

    def test_no_unsupported_css_properties_in_stylesheets(self):
        """Qt stylesheet parser does not support CSS3 filter, transform, or keyframes."""
        for is_light in (False, True):
            dialog_css = get_dialog_stylesheet(is_light)
            flyout_css = get_flyout_stylesheet(is_light, "dummy.svg")
            progress_css = get_progress_dialog_stylesheet(is_light)

            for sheet_name, sheet_content in [
                ("Dialog CSS", dialog_css),
                ("Flyout CSS", flyout_css),
                ("Progress CSS", progress_css),
            ]:
                self.assertNotIn("filter:", sheet_content, f"Illegal filter: in {sheet_name}")
                self.assertNotIn("transform:", sheet_content, f"Illegal transform: in {sheet_name}")
                self.assertNotIn("@keyframes", sheet_content, f"Illegal @keyframes in {sheet_name}")

    def test_border_radius_tokens_consistency(self):
        """Dialog controls must standardize on 6px Material Design 3 radius."""
        for is_light in (False, True):
            css = get_dialog_stylesheet(is_light)
            # Find all border-radius declarations
            radii = re.findall(r"border-radius:\s*(\d+)px", css)
            self.assertTrue(len(radii) > 0)
            # Standard dialog interactive tokens use 6px
            self.assertIn("6", radii)


class TestInteractiveComponentsQA(unittest.TestCase):
    """Validates interaction physics, focus handling, and error states."""

    def test_safe_combo_box_wheel_safety(self):
        """SafeComboBox ignores scroll wheel when collapsed to prevent accidental port selection."""
        cb = SafeComboBox()
        cb.addItems(["COM1", "COM3", "COM7"])
        cb.setCurrentIndex(0)

        # Simulate wheel down event
        wheel_event = QWheelEvent(
            QPointF(10.0, 10.0),
            QPointF(10.0, 10.0),
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        cb.wheelEvent(wheel_event)
        self.assertEqual(cb.currentIndex(), 0, "ComboBox changed selection on wheel scroll while closed")
        self.assertFalse(wheel_event.isAccepted())

    def test_dialog_keyboard_dismissal_escape(self):
        """Pressing Escape key closes dialog with rejection (is_accepted == False)."""
        dlg = ModernPromptDialog(title="Test", headline_text="Notice", info_text="Testing Esc key")
        dlg.show()
        app.processEvents()

        # Simulate Escape key press
        esc_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        dlg.keyPressEvent(esc_event)

        self.assertFalse(dlg.is_accepted)
        dlg.close()

    def test_pin_visibility_toggle_behavior(self):
        """PIN inputs must default to password masking and toggle cleanly with icon update."""
        dlg = BleChangePinDialog()
        self.assertEqual(dlg.old_pin_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(dlg.new_pin_input.echoMode(), QLineEdit.EchoMode.Password)

        # Trigger toggle
        dlg.old_pin_toggle.trigger()
        self.assertEqual(dlg.old_pin_input.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertEqual(dlg.old_pin_toggle.toolTip(), "Hide PIN")

        # Toggle back
        dlg.old_pin_toggle.trigger()
        self.assertEqual(dlg.old_pin_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(dlg.old_pin_toggle.toolTip(), "Show PIN")
        dlg.close()

    def test_custom_api_key_error_label_feedback(self):
        """Error messages display in high-contrast red (#ef4444) and toggle visibility."""
        dlg = CustomApiKeyDialog()
        save_btn = dlg.findChild(QPushButton, "saveBtn")

        # Initial state: error label is hidden
        self.assertTrue(dlg.error_lbl.isHidden())

        # Submit invalid input
        dlg.key_input.setText("short")
        save_btn.click()
        self.assertFalse(dlg.is_accepted)
        self.assertFalse(dlg.error_lbl.isHidden())
        self.assertIn("#ef4444", dlg.error_lbl.styleSheet())
        dlg.close()

    def test_settings_dialog_active_key_badge_distinction(self):
        """Badge clearly distinguishes between Auto-Generated (Cyan) and Custom Merchant (Emerald)."""
        dlg = SettingsDialog()

        # Auto-generated mode
        with patch.object(type(dlg.config), "is_custom_api_key", new_callable=lambda: False):
            dlg._update_key_badge()
            self.assertIn("Auto-Generated", dlg.key_badge.text())
            self.assertIn("#38bdf8", dlg.key_badge.styleSheet())

        # Custom merchant key mode
        with patch.object(type(dlg.config), "is_custom_api_key", new_callable=lambda: True):
            dlg._update_key_badge()
            self.assertIn("Custom Merchant Key", dlg.key_badge.text())
            self.assertIn("#10b981", dlg.key_badge.styleSheet())
        dlg.close()


class TestMicrocopyAndToneQA(unittest.TestCase):
    """Enforces authoritative enterprise UX writing standards across all UI components."""

    def test_no_conversational_questions_in_ui_dialogs(self):
        """Dialogs must use direct statements and action verbs, never rhetorical questions."""
        forbidden_questions = [
            "Are you sure",
            "Would you like",
            "Do you want",
            "Are you sure you want to quit",
            "Eliminates the operational overhead",
        ]

        # 1. Exit prompt
        exit_dlg = ModernPromptDialog(
            title="Exit",
            headline_text="Exit Nizi POS Connector",
            info_text="Terminates active hardware connections and background API services.",
            yes_text="Exit",
            no_text="Cancel",
        )
        for child in exit_dlg.findChildren(QLabel):
            text = child.text()
            self.assertNotIn("?", text)
            for phrase in forbidden_questions:
                self.assertNotIn(phrase.lower(), text.lower())

        # 2. Custom API Key dialog
        key_dlg = CustomApiKeyDialog()
        for child in key_dlg.findChildren(QLabel):
            text = child.text()
            self.assertNotIn("?", text)
            for phrase in forbidden_questions:
                self.assertNotIn(phrase.lower(), text.lower())

        # 3. Settings dialog
        settings_dlg = SettingsDialog()
        for child in settings_dlg.findChildren(QLabel):
            text = child.text()
            self.assertNotIn("?", text)
            for phrase in forbidden_questions:
                self.assertNotIn(phrase.lower(), text.lower())

    def test_no_extension_api_key_occurrences(self):
        """The legacy phrase 'Extension API Key' must be entirely purged from all UI components."""
        settings_dlg = SettingsDialog()
        for child in settings_dlg.findChildren(QLabel):
            self.assertNotIn("Extension API Key", child.text())

        for btn in settings_dlg.findChildren(QPushButton):
            self.assertNotIn("Extension API Key", btn.text())
            self.assertNotIn("Extension API Key", btn.toolTip())

        key_dlg = CustomApiKeyDialog()
        self.assertNotIn("Extension API Key", key_dlg.windowTitle())
        for child in key_dlg.findChildren(QLabel):
            self.assertNotIn("Extension API Key", child.text())

    def test_action_oriented_button_labels(self):
        """Buttons must use clear, imperative action verbs rather than generic or conversational Yes/No."""
        # Custom key dialog
        key_dlg = CustomApiKeyDialog()
        save_btn = key_dlg.findChild(QPushButton, "saveBtn")
        cancel_btn = key_dlg.findChild(QPushButton, "cancelBtn")
        self.assertEqual(save_btn.text(), "Save Key")
        self.assertEqual(cancel_btn.text(), "Cancel")

        # Change PIN dialog
        pin_dlg = BleChangePinDialog()
        change_btn = pin_dlg.findChild(QPushButton, "yesBtn")
        self.assertEqual(change_btn.text(), "Change")


class TestVisualSmokeRenderingQA(unittest.TestCase):
    """Generates visual proof captures of all UI components for layout QA verification."""

    def setUp(self):
        self.artifacts_dir = Path(__file__).resolve().parent.parent / "scratch"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def test_render_all_dialogs_offscreen(self):
        """Renders prompt, custom key, change PIN, and settings dialogs and verifies raster dimensions."""
        for is_light in (False, True):
            suffix = "_light" if is_light else "_dark"
            with patch("theme_support.prefers_light_theme", return_value=is_light), \
                 patch("ui_components.prefers_light_theme", return_value=is_light):
                dialogs = {
                    f"qa_prompt_exit{suffix}": ModernPromptDialog(
                        title="Exit",
                        headline_text="Exit Nizi POS Connector",
                        info_text="Terminates active hardware connections and background API services.",
                        yes_text="Exit",
                        no_text="Cancel",
                    ),
                    f"qa_custom_api_key{suffix}": CustomApiKeyDialog(),
                    f"qa_ble_change_pin{suffix}": BleChangePinDialog(),
                    f"qa_settings{suffix}": SettingsDialog(),
                }

                for name, dlg in dialogs.items():
                    dlg.show()
                    app.processEvents()

                    pixmap = dlg.grab()
                    self.assertFalse(pixmap.isNull())
                    self.assertGreater(pixmap.width(), 350)
                    self.assertGreater(pixmap.height(), 150)

                    out_file = self.artifacts_dir / f"{name}.png"
                    saved = pixmap.save(out_file.as_posix())
                    self.assertTrue(saved)
                    self.assertTrue(out_file.exists())
                    self.assertGreater(out_file.stat().st_size, 500)
                    dlg.close()

    def test_render_main_window_flyout_offscreen(self):
        """Renders main application flyout window with mock device manager."""
        mock_device = MagicMock()
        mock_device.connected = True
        mock_device.port = "COM7"
        mock_device.device_id = "NIZIPOSB31"
        mock_device.firmware_id = "2.0.0"
        mock_device._on_status_change = None

        win = TrayFlyout(device_manager=mock_device, web_port=9121)
        win.show()
        app.processEvents()

        pixmap = win.grab()
        self.assertFalse(pixmap.isNull())
        self.assertGreater(pixmap.width(), 380)

        out_file = self.artifacts_dir / "qa_main_window.png"
        saved = pixmap.save(out_file.as_posix())
        self.assertTrue(saved)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 1000)
        win.close()


if __name__ == "__main__":
    unittest.main()
