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

    def test_defaults(self):
        cfg = Config()
        self.assertEqual(cfg.server_host, "127.0.0.1")
        self.assertEqual(cfg.server_port, 9121)
        self.assertTrue(len(cfg.api_key) > 50)  # Verify presence of long api key


if __name__ == "__main__":
    unittest.main()
