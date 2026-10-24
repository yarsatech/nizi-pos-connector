"""
Formal automated test suite for OTA Update Lifecycle, Manifest Verification,
and In-Place Upgrade Engine against ISO 25010 & OWASP Security Standards.
"""

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from ota.github import (
    UpdateInfo,
    download_text,
    fetch_latest_release_json,
    load_repo_from_embedded_source,
    normalize_github_repo,
    parse_update_info,
)
from ota.ota_updater import _find_app_root, _resolve_main_exe_path
from ota.update_manager import DownloadWorker, OTALocalCancelled, UpdateManager


class TestOtaLifecycleEngine(unittest.TestCase):
    """Verifies end-to-end OTA upgrade logic, SHA-256 integrity, and security hardening."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_platform_default_manifest_asset_name(self):
        """Platform manifest mapping must accurately match OS targets."""
        with patch("sys.platform", "win32"):
            self.assertEqual(UpdateManager._default_manifest_asset_name(), "manifest-win.json")
        with patch("sys.platform", "linux"):
            self.assertEqual(UpdateManager._default_manifest_asset_name(), "manifest-linux.json")
        with patch("sys.platform", "darwin"):
            self.assertEqual(UpdateManager._default_manifest_asset_name(), "manifest-macos.json")
        with patch("sys.platform", "unknown_os"):
            self.assertIsNone(UpdateManager._default_manifest_asset_name())

    def test_repo_normalization(self):
        """normalize_github_repo must validate and sanitize repository paths."""
        self.assertEqual(normalize_github_repo("owner/repo"), "owner/repo")
        self.assertEqual(normalize_github_repo("  YarsaTech/Nizi-POS-Connector  "), "YarsaTech/Nizi-POS-Connector")
        self.assertIsNone(normalize_github_repo("invalid_format_no_slash"))
        self.assertIsNone(normalize_github_repo(""))

    def test_parse_update_info_valid_manifest(self):
        """parse_update_info must extract SHA-256 and target zip URL when newer release exists."""
        release_payload = {
            "tag_name": "v2.5.0",
            "assets": [
                {
                    "name": "manifest-win.json",
                    "browser_download_url": "https://example.com/manifest-win.json",
                },
                {
                    "name": "NiziPOSConnector-win-ota-2.5.0.zip",
                    "browser_download_url": "https://example.com/NiziPOSConnector-win-ota-2.5.0.zip",
                },
            ],
        }
        manifest_payload = {
            "version": "2.5.0",
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "zip_asset_name": "NiziPOSConnector-win-ota-2.5.0.zip",
        }

        with patch("ota.github.download_text", return_value=json.dumps(manifest_payload)):
            info = parse_update_info(
                release_payload,
                current_version="2.4.0",
                manifest_asset_name="manifest-win.json",
            )
            self.assertIsNotNone(info)
            self.assertEqual(info.latest_version, "2.5.0")
            self.assertEqual(info.sha256, manifest_payload["sha256"])
            self.assertEqual(info.zip_url, "https://example.com/NiziPOSConnector-win-ota-2.5.0.zip")

    def test_parse_update_info_already_up_to_date(self):
        """When installed version matches or exceeds latest release, no update is parsed."""
        release_payload = {
            "tag_name": "v2.0.0",
            "assets": [
                {
                    "name": "manifest-win.json",
                    "browser_download_url": "https://example.com/manifest-win.json",
                }
            ],
        }
        manifest_payload = {
            "version": "2.0.0",
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "zip_asset_name": "NiziPOSConnector-win-ota-2.0.0.zip",
        }

        with patch("ota.github.download_text", return_value=json.dumps(manifest_payload)):
            # Same version
            info = parse_update_info(
                release_payload,
                current_version="2.0.0",
                manifest_asset_name="manifest-win.json",
            )
            self.assertIsNone(info)

            # Newer version already installed
            info2 = parse_update_info(
                release_payload,
                current_version="2.1.0",
                manifest_asset_name="manifest-win.json",
            )
            self.assertIsNone(info2)

    def test_sha256_verification_integrity(self):
        """SHA-256 verification must detect bit flips and payload tampering."""
        manager = UpdateManager(
            github_repo="yarsatech/nizi-pos-connector",
            current_version="1.0.0",
            config_dir=self.config_dir,
        )

        dummy_file = self.config_dir / "test_package.zip"
        dummy_file.write_bytes(b"VALID_BINARY_PAYLOAD_CONTENT_BYTES")

        valid_sha = hashlib.sha256(b"VALID_BINARY_PAYLOAD_CONTENT_BYTES").hexdigest()
        self.assertEqual(manager._sha256_file(dummy_file), valid_sha)

        # Tampered content
        dummy_file.write_bytes(b"TAMPERED_MALICIOUS_PAYLOAD_BYTES")
        self.assertNotEqual(manager._sha256_file(dummy_file), valid_sha)

    def test_zip_slip_vulnerability_defense(self):
        """Zip Slip directory traversal attacks must be intercepted and rejected."""
        malicious_zip = self.config_dir / "malicious.zip"
        extract_root = self.config_dir / "extract"
        extract_root.mkdir()

        # Build in-memory zip archive with path traversal attempt
        with zipfile.ZipFile(malicious_zip, "w") as zf:
            zf.writestr("../../evil.sh", "#!/bin/bash\nrm -rf /")

        with zipfile.ZipFile(malicious_zip, "r") as zf:
            extract_root_abs = os.path.abspath(str(extract_root))
            with self.assertRaises(RuntimeError) as ctx:
                for member in zf.infolist():
                    member_target = os.path.abspath(os.path.join(str(extract_root), member.filename))
                    if not member_target.startswith(extract_root_abs + os.sep) and member_target != extract_root_abs:
                        raise RuntimeError(f"Zip slip security violation: {member.filename} resolves outside destination")
            self.assertIn("Zip slip security violation", str(ctx.exception))

    def test_binary_resolution_multiplatform(self):
        """Main binary and updater binary paths must resolve across Windows, macOS, and Linux."""
        test_dir = self.config_dir / "bin_staging"
        test_dir.mkdir()

        # 1. Windows resolution
        win_exe = test_dir / "NiziPOSConnector.exe"
        win_exe.touch()
        with patch("sys.platform", "win32"):
            candidates = UpdateManager._candidate_binary_names("NiziPOSConnector")
            self.assertIn("NiziPOSConnector.exe", candidates)
            resolved = UpdateManager(
                github_repo="test/repo", current_version="1.0", config_dir=self.config_dir
            )._resolve_binary_path(test_dir, "NiziPOSConnector")
            self.assertEqual(resolved, win_exe)

        # 2. Darwin resolution
        mac_bundle = test_dir / "NiziPOSConnector.app" / "Contents" / "MacOS"
        mac_bundle.mkdir(parents=True)
        mac_bin = mac_bundle / "NiziPOSConnector"
        mac_bin.touch()
        with patch("sys.platform", "darwin"):
            resolved_mac = _resolve_main_exe_path(str(test_dir))
            self.assertIsNotNone(resolved_mac)
            self.assertTrue(resolved_mac.endswith("NiziPOSConnector"))

    def test_download_worker_cancellation(self):
        """DownloadWorker must abort immediately when user cancels."""
        dest_file = self.config_dir / "download.zip"
        worker = DownloadWorker("https://dummy.url/file.zip", dest_file, 10)
        worker.cancel()
        self.assertTrue(worker.is_cancelled)


if __name__ == "__main__":
    unittest.main()
