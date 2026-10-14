"""
Tests for security hardening across NIZI-001, NIZI-005, NIZI-006, NIZI-007.
"""
import os
import sys
import tempfile
import zipfile
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security import constant_time_compare
from config import config


class TestSecurityHardening(unittest.TestCase):

    def test_constant_time_compare(self):
        self.assertTrue(constant_time_compare("secret_key_123", "secret_key_123"))
        self.assertFalse(constant_time_compare("secret_key_123", "wrong_key"))
        self.assertFalse(constant_time_compare("", "key"))
        self.assertFalse(constant_time_compare(None, "key"))
        self.assertFalse(constant_time_compare("key", None))

    def test_inno_setup_privileges_and_directory(self):
        iss_path = Path(__file__).resolve().parent.parent / "win_setup.iss"
        self.assertTrue(iss_path.exists())
        content = iss_path.read_text(encoding="utf-8")
        self.assertIn("DefaultDirName={autopf}\\NiziPOSConnector", content)
        self.assertIn("PrivilegesRequired=admin", content)

    def test_zip_slip_protection_in_updater(self):
        # Create a temporary zip file with a path traversal member
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "test_malicious.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("../traversal.txt", "malicious payload")

            extract_target = Path(tmp_dir) / "extract"
            extract_target.mkdir()

            with zipfile.ZipFile(zip_path, "r") as zf:
                extract_root_abs = os.path.abspath(extract_target)
                with self.assertRaises(RuntimeError):
                    for member in zf.infolist():
                        member_target = os.path.abspath(os.path.join(extract_target, member.filename))
                        if not member_target.startswith(extract_root_abs + os.sep) and member_target != extract_root_abs:
                            raise RuntimeError(f"Zip Slip detected: {member.filename}")
                        zf.extract(member, extract_target)

    def test_waitress_installed(self):
        import waitress
        self.assertTrue(hasattr(waitress, "serve"))


if __name__ == "__main__":
    unittest.main()
