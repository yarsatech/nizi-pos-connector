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


if __name__ == "__main__":
    unittest.main()
