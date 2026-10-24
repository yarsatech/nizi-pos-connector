"""
Tests for config.py
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, APP_NAME, APP_AUTHOR, APP_VERSION


class TestConfig(unittest.TestCase):

    @patch("config.user_config_dir")
    def test_config_dir_resolution(self, mock_user_config_dir):
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_user_config_dir.return_value = temp_dir
            cfg = Config()
            self.assertEqual(cfg.config_dir, Path(temp_dir))
            self.assertEqual(cfg.config_file, Path(temp_dir) / "config.json")

    def test_default_constants(self):
        self.assertEqual(APP_NAME, "Nizi POS Connector")
        self.assertEqual(APP_AUTHOR, "Yarsa Tech")
        # Starts with 0.0.0 from repository-root config.json in dev mode
        self.assertEqual(APP_VERSION, "0.0.0")

    @patch.dict(os.environ, {"NIZI_POS_CONNECTOR_GITHUB_REPO": "test_owner/test_repo"})
    def test_github_repo_env_override(self):
        cfg = Config()
        self.assertEqual(cfg.github_repo, "test_owner/test_repo")

    def test_resolve_main_exe_path_platforms(self):
        import tempfile
        from ota.ota_updater import _resolve_main_exe_path

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # 1. Windows: creates NiziPOSConnector.exe
            win_dir = tmppath / "win"
            win_dir.mkdir()
            win_exe = win_dir / "NiziPOSConnector.exe"
            win_exe.write_text("dummy")
            with patch("sys.platform", "win32"):
                self.assertEqual(Path(_resolve_main_exe_path(str(win_dir))), win_exe)

            # 2. Linux: creates NiziPOSConnector (no ext)
            linux_dir = tmppath / "linux"
            linux_dir.mkdir()
            linux_exe = linux_dir / "NiziPOSConnector"
            linux_exe.write_text("dummy")
            with patch("sys.platform", "linux"):
                self.assertEqual(Path(_resolve_main_exe_path(str(linux_dir))), linux_exe)

            # 3. macOS: inside .app bundle
            mac_dir = tmppath / "mac"
            mac_dir.mkdir()
            app_dir = mac_dir / "NiziPOSConnector.app" / "Contents" / "MacOS"
            app_dir.mkdir(parents=True)
            mac_exe = app_dir / "NiziPOSConnector"
            mac_exe.write_text("dummy")
            with patch("sys.platform", "darwin"):
                # When passing base dir containing .app
                self.assertEqual(Path(_resolve_main_exe_path(str(mac_dir))), mac_exe)
                # When passing .app directly
                self.assertEqual(Path(_resolve_main_exe_path(str(mac_dir / "NiziPOSConnector.app"))), mac_exe)

    def test_api_key_persistence_and_encryption(self):
        import tempfile
        from security import constant_time_compare
        with tempfile.TemporaryDirectory() as td:
            with patch("config.user_config_dir", return_value=td):
                cfg = Config()
                key1 = cfg.api_key
                self.assertIsNotNone(key1)
                self.assertTrue(len(key1) >= 40)

                # Reset cache and reload from disk
                cfg2 = Config()
                key2 = cfg2.api_key
                self.assertEqual(key1, key2)
                self.assertTrue(constant_time_compare(key1, key2))
                self.assertFalse(constant_time_compare(key1, "invalid_key"))

    def test_cors_configuration(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            with patch("config.user_config_dir", return_value=td):
                cfg = Config()
                # Test default template origins
                self.assertEqual(cfg.cors_mode, "allowlist")
                self.assertIn("https://nagarik.gibl.com.np", cfg.cors_allowed_origins)

                # Update CORS mode and origins
                cfg.set_cors_settings("allow_all", ["https://custom-pos.com/"])
                self.assertEqual(cfg.cors_mode, "allow_all")
                self.assertEqual(cfg.cors_allowed_origins, ["https://custom-pos.com"])

                # Verify persistence in config.json
                cfg_reloaded = Config()
                self.assertEqual(cfg_reloaded.cors_mode, "allow_all")
                self.assertEqual(cfg_reloaded.cors_allowed_origins, ["https://custom-pos.com"])

    def test_custom_api_key_persistence(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            with patch("config.user_config_dir", return_value=td):
                cfg = Config()
                custom_token = "nizipos-fixed-secret-token"
                saved = cfg.set_custom_api_key(custom_token)
                self.assertEqual(saved, custom_token)
                self.assertEqual(cfg.api_key, custom_token)

                # Reload in new instance
                cfg_reloaded = Config()
                self.assertEqual(cfg_reloaded.api_key, custom_token)

    def test_custom_api_key_validation_and_uuid(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            with patch("config.user_config_dir", return_value=td):
                cfg = Config()

                # 1. Empty string rejection
                with self.assertRaises(ValueError):
                    cfg.set_custom_api_key("   ")

                # 2. Too short (< 16 chars, e.g. "12345", "pin123")
                with self.assertRaises(ValueError) as ctx:
                    cfg.set_custom_api_key("12345")
                self.assertIn("between 16 and 32", str(ctx.exception))

                with self.assertRaises(ValueError):
                    cfg.set_custom_api_key("pin123")

                # 3. Too long (> 32 chars)
                with self.assertRaises(ValueError) as ctx:
                    cfg.set_custom_api_key("a" * 33)
                self.assertIn("between 16 and 32", str(ctx.exception))

                # 4. Purely digits (e.g. 16 digits)
                with self.assertRaises(ValueError) as ctx:
                    cfg.set_custom_api_key("9854720194827163")
                self.assertIn("mix of character types", str(ctx.exception))

                # 5. Purely letters (e.g. 16+ letters)
                with self.assertRaises(ValueError) as ctx:
                    cfg.set_custom_api_key("somelongalphabeticpass")
                self.assertIn("mix of character types", str(ctx.exception))

                # 6. Cyclical repeating patterns
                with self.assertRaises(ValueError) as ctx:
                    cfg.set_custom_api_key("a1a1a1a1a1a1a1a1")
                self.assertIn("repeating or cyclical", str(ctx.exception).lower())

                # 7. Sequential characters and keyboard walks
                with self.assertRaises(ValueError) as ctx:
                    cfg.set_custom_api_key("pos_12345_lane_key")
                self.assertIn("sequential", str(ctx.exception).lower())

                # 8. Valid passkeys with high entropy (16-32 chars)
                self.assertFalse(cfg.is_custom_api_key)
                token1 = cfg.set_custom_api_key("pos_counter_lane_01")
                self.assertEqual(token1, "pos_counter_lane_01")
                self.assertEqual(cfg.api_key, "pos_counter_lane_01")
                self.assertTrue(cfg.is_custom_api_key)

                token2 = cfg.set_custom_api_key("3a8f1b90d2e448b1a80c9e782fb5a11c")
                self.assertEqual(token2, "3a8f1b90d2e448b1a80c9e782fb5a11c")
                self.assertEqual(cfg.api_key, "3a8f1b90d2e448b1a80c9e782fb5a11c")
                self.assertTrue(cfg.is_custom_api_key)

                cfg.regenerate_api_key()
                self.assertFalse(cfg.is_custom_api_key)


if __name__ == "__main__":
    unittest.main()
