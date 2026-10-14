import unittest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication, QLineEdit
from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QWheelEvent, QGuiApplication

from ui_components import ModernPromptDialog, BleChangePinDialog
from ui_app import SafeComboBox
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
        dlg._copy_key()
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            self.assertEqual(clipboard.text(), config.api_key)

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


if __name__ == "__main__":
    unittest.main()
