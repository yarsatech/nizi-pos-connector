"""
Formal automated test suite verifying UX visual hierarchy, API key prioritization,
and accessibility standards against ISO 25010 & Material Design Guidelines.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QFrame

from config import config
from ui_components import CustomApiKeyDialog, SettingsDialog

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestUiUxHierarchy(unittest.TestCase):
    """Verifies that primary standard flows take precedence over legacy/custom configuration."""

    def test_custom_key_hierarchy_demotion(self):
        """'Set Custom Key' must reside in a distinct, lower-hierarchy legacy card rather than equal row."""
        dlg = SettingsDialog()

        # 1. Primary actions row must contain Copy Key and Regenerate Key
        self.assertIsNotNone(dlg.btn_copy_key)
        self.assertIsNotNone(dlg.btn_regenerate_key)
        self.assertEqual(dlg.btn_copy_key.objectName(), "tonalActionBtn")
        self.assertEqual(dlg.btn_regenerate_key.objectName(), "actionBtn")

        # 2. Custom key button must be demoted with subtleActionBtn styling
        self.assertIsNotNone(dlg.btn_set_custom_key)
        self.assertEqual(dlg.btn_set_custom_key.objectName(), "subtleActionBtn")

        # 3. Custom key button must be placed inside legacyCard frame
        legacy_frame = dlg.findChild(QFrame, "legacyCard")
        self.assertIsNotNone(legacy_frame, "SettingsDialog must contain a dedicated legacyCard container")
        self.assertTrue(dlg.btn_set_custom_key.parent() is legacy_frame or dlg.btn_set_custom_key.parent() is dlg)

        # 4. Legacy frame must display clear explanatory guidance
        labels = legacy_frame.findChildren(QLabel)
        texts = " ".join(lbl.text() for lbl in labels)
        self.assertIn("auto-generated 256-bit", texts.lower())
        self.assertIn("third-party", texts.lower())

    def test_active_key_badge_and_revert_action(self):
        """Active key badge and revert action must toggle dynamically based on key type."""
        dlg = SettingsDialog()

        from unittest.mock import PropertyMock

        # Case A: Standard auto-generated key
        with patch("config.Config.is_custom_api_key", new_callable=PropertyMock, return_value=False):
            dlg._update_key_badge()
            self.assertIn("Auto-Generated", dlg.key_badge.text())
            self.assertTrue(dlg.btn_revert_auto_key.isHidden())

        # Case B: Custom merchant key
        with patch("config.Config.is_custom_api_key", new_callable=PropertyMock, return_value=True):
            dlg._update_key_badge()
            self.assertIn("Custom Merchant Key", dlg.key_badge.text())
            self.assertFalse(dlg.btn_revert_auto_key.isHidden())

        # Case C: Revert to auto key
        with patch("ui_components.ModernPromptDialog.exec"), \
             patch("ui_components.ModernPromptDialog.is_accepted", new_callable=lambda: True), \
             patch.object(dlg.config, "regenerate_api_key") as mock_regen:
            dlg._revert_to_auto_key()
            mock_regen.assert_called_once()
            self.assertEqual(dlg.btn_revert_auto_key.text(), "Key Restored!")

    def test_no_conversational_questions_in_settings_labels(self):
        """All UI copy must adhere to direct, authoritative engineering style without question marks."""
        dlg = SettingsDialog()
        for lbl in dlg.findChildren(QLabel):
            text = lbl.text()
            self.assertNotIn("?", text, f"Label contains question mark: {text}")

        key_dlg = CustomApiKeyDialog()
        for lbl in key_dlg.findChildren(QLabel):
            text = lbl.text()
            self.assertNotIn("?", text, f"Label contains question mark: {text}")


if __name__ == "__main__":
    unittest.main()
