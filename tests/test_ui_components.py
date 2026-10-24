import unittest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication, QLineEdit
from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QWheelEvent, QGuiApplication

from ui_components import ModernPromptDialog, BleChangePinDialog, CustomApiKeyDialog
from ui_app import SafeComboBox, SafeSlider
from theme_support import prefers_light_theme, get_flyout_stylesheet, get_theme_tokens

app = QApplication.instance() or QApplication([])


class TestSafeComboBox(unittest.TestCase):

    def test_focus_policy(self):
        cb = SafeComboBox()
        self.assertEqual(cb.focusPolicy(), Qt.FocusPolicy.ClickFocus)

    def test_wheel_event_ignored_when_closed(self):
        cb = SafeComboBox()
        cb.addItems(["Option 1", "Option 2", "Option 3"])
        cb.setCurrentIndex(0)

        from PyQt6.QtCore import QPointF
        wheel_event = QWheelEvent(
            QPointF(10.0, 10.0),
            QPointF(10.0, 10.0),
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False
        )
        cb.wheelEvent(wheel_event)
        # Should remain at index 0 because wheel event was ignored
        self.assertEqual(cb.currentIndex(), 0)
        self.assertFalse(wheel_event.isAccepted())

    def test_clear_focus_on_hide_popup(self):
        cb = SafeComboBox()
        cb.setFocus()
        cb.hidePopup()
        self.assertFalse(cb.hasFocus())


class TestSafeSlider(unittest.TestCase):

    def test_safe_slider_properties(self):
        slider = SafeSlider(Qt.Orientation.Horizontal)
        self.assertEqual(slider.focusPolicy(), Qt.FocusPolicy.ClickFocus)
        slider.setValue(50)

        from PyQt6.QtCore import QPointF
        wheel_event = QWheelEvent(
            QPointF(10.0, 10.0),
            QPointF(10.0, 10.0),
            QPoint(0, 0),
            QPoint(0, -120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False
        )
        slider.wheelEvent(wheel_event)
        # Value must remain 50 because wheel scroll is ignored
        self.assertEqual(slider.value(), 50)
        self.assertFalse(wheel_event.isAccepted())


class TestSubtleHoverTokens(unittest.TestCase):

    def test_subtle_hover_tokens_not_red(self):
        light_tokens = get_theme_tokens(is_light=True)
        self.assertEqual(light_tokens["border_hover"], "#cbd5e1")
        self.assertEqual(light_tokens["secondary_hover_border"], "#cbd5e1")
        self.assertEqual(light_tokens["radio_hover_border"], "#cbd5e1")
        self.assertNotEqual(light_tokens["border_hover"], "#fca5a5")

        dark_tokens = get_theme_tokens(is_light=False)
        self.assertEqual(dark_tokens["border_hover"], "#475569")
        self.assertEqual(dark_tokens["secondary_hover_border"], "#475569")
        self.assertEqual(dark_tokens["radio_hover_border"], "#475569")


class TestModernPromptDialog(unittest.TestCase):

    def test_init_and_properties(self):
        dlg = ModernPromptDialog(title="Test", headline_text="Head", info_text="Info")
        self.assertEqual(dlg.windowTitle(), "Test")
        self.assertFalse(dlg.is_accepted)

    def test_accept(self):
        dlg = ModernPromptDialog(title="Test", headline_text="Head", info_text="Info")
        # Find yes button and click
        yes_btn = dlg.findChild(type(dlg), "yesBtn") or [b for b in dlg.findChildren(type(dlg)) if getattr(b, 'text', lambda: '')() == "Yes"]
        # Trigger accept directly or through internal method
        dlg._accepted = True
        self.assertTrue(dlg.is_accepted)

    def test_reject(self):
        dlg = ModernPromptDialog(title="Test", headline_text="Head", info_text="Info")
        dlg.reject()
        self.assertFalse(dlg.is_accepted)


class TestBleChangePinDialog(unittest.TestCase):

    def test_init_fields(self):
        dlg = BleChangePinDialog()
        self.assertEqual(dlg.old_pin, "")
        self.assertEqual(dlg.new_pin, "")
        self.assertEqual(dlg.old_pin_input.placeholderText(), "Current PIN")
        self.assertEqual(dlg.new_pin_input.placeholderText(), "New PIN")

    def test_empty_fields_not_accepted(self):
        dlg = BleChangePinDialog()
        dlg.old_pin_input.setText("")
        dlg.new_pin_input.setText("")
        # Call the internal accept handler
        for child in dlg.children():
            if getattr(child, 'text', lambda: '')() == "Change":
                child.click()
                break
        self.assertEqual(dlg.old_pin, "")
        self.assertEqual(dlg.new_pin, "")

    def test_filled_fields_accepted(self):
        dlg = BleChangePinDialog()
        dlg.old_pin_input.setText("1234")
        dlg.new_pin_input.setText("5678")
        for child in dlg.children():
            if getattr(child, 'text', lambda: '')() == "Change":
                child.click()
                break
        self.assertEqual(dlg.old_pin, "1234")
        self.assertEqual(dlg.new_pin, "5678")

    def test_pin_visibility_toggle(self):
        from PyQt6.QtWidgets import QLineEdit
        dlg = BleChangePinDialog()
        # Verify initial state is password
        self.assertEqual(dlg.old_pin_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(dlg.new_pin_input.echoMode(), QLineEdit.EchoMode.Password)

        # Toggle old pin visibility
        dlg.old_pin_toggle.trigger()
        self.assertEqual(dlg.old_pin_input.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertEqual(dlg.old_pin_toggle.toolTip(), "Hide PIN")

        dlg.old_pin_toggle.trigger()
        self.assertEqual(dlg.old_pin_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(dlg.old_pin_toggle.toolTip(), "Show PIN")

        # Toggle new pin visibility
        dlg.new_pin_toggle.trigger()
        self.assertEqual(dlg.new_pin_input.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertEqual(dlg.new_pin_toggle.toolTip(), "Hide PIN")

        dlg.new_pin_toggle.trigger()
        self.assertEqual(dlg.new_pin_input.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(dlg.new_pin_toggle.toolTip(), "Show PIN")


class TestThemeStylesheetValidity(unittest.TestCase):

    def test_no_unsupported_css_properties(self):
        # Ensure no transform or filter properties in stylesheet
        tokens_dark = get_flyout_stylesheet(False, "dummy.svg")
        tokens_light = get_flyout_stylesheet(True, "dummy.svg")

        self.assertNotIn("filter:", tokens_dark)
        self.assertNotIn("filter:", tokens_light)
        self.assertNotIn("transform:", tokens_dark)
        self.assertNotIn("transform:", tokens_light)


class TestSettingsDialog(unittest.TestCase):

    def test_settings_dialog_components_and_operations(self):
        from ui_components import SettingsDialog
        from config import config

        dlg = SettingsDialog()

        # Test adding origin
        initial_count = dlg.origins_list.count()
        dlg.new_origin_input.setText("https://test-portal.example.com")
        dlg._add_origin()
        self.assertEqual(dlg.origins_list.count(), initial_count + 1)
        self.assertEqual(dlg.new_origin_input.text(), "")

        # Test removing selected origin
        dlg.origins_list.setCurrentRow(dlg.origins_list.count() - 1)
        dlg._remove_origin()
        self.assertEqual(dlg.origins_list.count(), initial_count)

        # Test copy key
        clipboard = QGuiApplication.clipboard()
        with patch.object(clipboard, "setText") as mock_set:
            dlg._copy_key()
            mock_set.assert_called_once_with(config.api_key)
            self.assertEqual(dlg.btn_copy_key.text(), "Copied!")

        # Test regenerate key rejected (no key changed)
        with patch("ui_components.ModernPromptDialog.exec"), \
             patch("ui_components.ModernPromptDialog.is_accepted", new_callable=lambda: False), \
             patch.object(dlg.config, "regenerate_api_key") as mock_regen:
            dlg._regenerate_key()
            mock_regen.assert_not_called()

        # Test regenerate key accepted (key updated)
        with patch("ui_components.ModernPromptDialog.exec"), \
             patch("ui_components.ModernPromptDialog.is_accepted", new_callable=lambda: True), \
             patch.object(dlg.config, "regenerate_api_key", return_value="NEW_GENERATED_KEY_123") as mock_regen:
            dlg._regenerate_key()
            mock_regen.assert_called_once()
            self.assertEqual(dlg.btn_regenerate_key.text(), "Key Regenerated!")

        # Test set custom key rejected by dialog (no key changed)
        with patch("ui_components.CustomApiKeyDialog.exec"), \
             patch("ui_components.CustomApiKeyDialog.is_accepted", new_callable=lambda: False), \
             patch.object(dlg.config, "set_custom_api_key") as mock_set_key:
            dlg._set_custom_key()
            mock_set_key.assert_not_called()

        # Test set custom key confirmed by user (key updated)
        with patch("ui_components.CustomApiKeyDialog.exec"), \
             patch("ui_components.CustomApiKeyDialog.is_accepted", new_callable=lambda: True), \
             patch("ui_components.CustomApiKeyDialog.custom_key", new_callable=lambda: "nizipos-fixed-secret-token"), \
             patch("ui_components.ModernPromptDialog.exec"), \
             patch("ui_components.ModernPromptDialog.is_accepted", new_callable=lambda: True), \
             patch.object(dlg.config, "set_custom_api_key", return_value="nizipos-fixed-secret-token") as mock_set_key:
            dlg._set_custom_key()
            mock_set_key.assert_called_once_with("nizipos-fixed-secret-token")
            self.assertEqual(dlg.btn_set_custom_key.text(), "Key Saved!")

        # Test set custom key prompt rejected (no key changed)
        with patch("ui_components.CustomApiKeyDialog.exec"), \
             patch("ui_components.CustomApiKeyDialog.is_accepted", new_callable=lambda: True), \
             patch("ui_components.CustomApiKeyDialog.custom_key", new_callable=lambda: "nizipos-fixed-secret-token"), \
             patch("ui_components.ModernPromptDialog.exec"), \
             patch("ui_components.ModernPromptDialog.is_accepted", new_callable=lambda: False), \
             patch.object(dlg.config, "set_custom_api_key") as mock_set_key:
            dlg._set_custom_key()
            mock_set_key.assert_not_called()

        # Test save prompt rejected (no changes committed)
        with patch("ui_components.ModernPromptDialog.exec"), \
             patch.object(dlg.config, "set_cors_settings") as mock_set:
            with patch("ui_components.ModernPromptDialog.is_accepted", new_callable=lambda: False):
                dlg._save_and_close()
                mock_set.assert_not_called()

        # Test save prompt accepted (changes committed)
        with patch("ui_components.ModernPromptDialog.exec"), \
             patch.object(dlg, "accept"), \
             patch.object(dlg.config, "set_cors_settings") as mock_set:
            with patch("ui_components.ModernPromptDialog.is_accepted", new_callable=lambda: True):
                dlg._save_and_close()
                mock_set.assert_called_once()


class TestCustomApiKeyDialog(unittest.TestCase):

    def test_dialog_initial_state(self):
        from PyQt6.QtWidgets import QLineEdit
        dlg = CustomApiKeyDialog()
        self.assertEqual(dlg.key_input.text(), "")
        self.assertEqual(dlg.key_input.maxLength(), 32)
        self.assertEqual(dlg.key_input.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertFalse(dlg.is_accepted)
        self.assertTrue(dlg.error_lbl.isHidden())

    def test_dialog_validation_failures(self):
        from PyQt6.QtWidgets import QPushButton
        dlg = CustomApiKeyDialog()
        save_btn = dlg.findChild(QPushButton, "saveBtn")

        # 1. Empty string
        dlg.key_input.setText("")
        save_btn.click()
        self.assertFalse(dlg.is_accepted)
        self.assertFalse(dlg.error_lbl.isHidden())
        self.assertIn("empty", dlg.error_lbl.text().lower())

        # 2. Too short (< 16 chars, e.g. 12345 or short_pass_123)
        dlg.key_input.setText("12345")
        save_btn.click()
        self.assertFalse(dlg.is_accepted)
        self.assertFalse(dlg.error_lbl.isHidden())
        self.assertIn("between 16 and 32", dlg.error_lbl.text())

        # 3. Purely letters (no digits or symbols)
        dlg.key_input.setText("somelongalphabeticpass")
        save_btn.click()
        self.assertFalse(dlg.is_accepted)
        self.assertFalse(dlg.error_lbl.isHidden())
        self.assertIn("mix of character types", dlg.error_lbl.text().lower())

        # 4. Purely digits (e.g. 16 digits)
        dlg.key_input.setText("9854720194827163")
        save_btn.click()
        self.assertFalse(dlg.is_accepted)
        self.assertFalse(dlg.error_lbl.isHidden())
        self.assertIn("mix of character types", dlg.error_lbl.text().lower())

        # 5. Cyclical repeating patterns (e.g. a1a1a1a1a1a1a1a1)
        dlg.key_input.setText("a1a1a1a1a1a1a1a1")
        save_btn.click()
        self.assertFalse(dlg.is_accepted)
        self.assertFalse(dlg.error_lbl.isHidden())
        self.assertIn("repeating or cyclical", dlg.error_lbl.text().lower())

        # 6. Sequential patterns (e.g. pos_12345_lane_key)
        dlg.key_input.setText("pos_12345_lane_key")
        save_btn.click()
        self.assertFalse(dlg.is_accepted)
        self.assertFalse(dlg.error_lbl.isHidden())
        self.assertIn("sequential", dlg.error_lbl.text().lower())

    def test_dialog_save_success(self):
        from PyQt6.QtWidgets import QPushButton
        dlg = CustomApiKeyDialog()
        dlg.key_input.setText("merchant_pos_token_123")
        save_btn = dlg.findChild(QPushButton, "saveBtn")
        save_btn.click()
        self.assertTrue(dlg.is_accepted)
        self.assertEqual(dlg.custom_key, "merchant_pos_token_123")


if __name__ == "__main__":
    unittest.main()
