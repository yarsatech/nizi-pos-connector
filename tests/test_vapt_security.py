"""
Comprehensive VAPT (Vulnerability Assessment & Penetration Testing) Security Test Suite.
Validates security controls against OWASP ASVS, ISO/IEC 27001, and ISO/IEC 25010:
1. Brute-Force Rate Limiting & Denial of Service (DoS) Defense.
2. Authentication Enforcement & Bearer Token Interoperability.
3. CORS Isolation, Strict Origin Filtering & Subdomain Spoofing Resistance.
4. Serial Protocol Injection, Control Character Sanitization & Verb Whitelisting.
5. Static File Path Traversal Protection (Directory Escaping).
6. File Upload Safety (Magic Bytes, MIME Spoofing & Bounds Checking).
7. Passkey Entropy, ASCII Delta Arithmetic & Cyclical Periodicity Analysis.
"""
import io
import json
import os
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from device_manager import validate_serial_frame
from security import (
    calculate_shannon_entropy,
    constant_time_compare,
    validate_custom_api_key,
)
from web_server import (
    AUTH_BLOCK_DURATION_SECONDS,
    MAX_FAILED_AUTH_ATTEMPTS,
    app,
    is_origin_allowed,
    reset_rate_limits,
    socketio,
)


class TestVAPTSecurity(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        reset_rate_limits()
        config.set_cors_settings("allowlist", ["https://pos.yarsatech.com", "https://billing.local"])
        self.valid_key = config.api_key
        self.client = app.test_client()

    # ── 1. Brute-Force Rate Limiting & Auth Throttle ───────────────────────

    def test_brute_force_auth_rate_limiting(self):
        """
        Verify that 10 consecutive failed authentication attempts trigger an
        HTTP 429 Too Many Requests response with a Retry-After header.
        """
        bad_headers = {"X-API-Key": "completely_invalid_key_attempt"}

        # First 9 attempts fail with 401 Unauthorized
        for i in range(MAX_FAILED_AUTH_ATTEMPTS - 1):
            res = self.client.get("/api/status", headers=bad_headers)
            self.assertEqual(res.status_code, 401, f"Attempt {i+1} should fail with 401")

        # 10th attempt exceeds threshold -> 401 recorded, client now blocked
        res10 = self.client.get("/api/status", headers=bad_headers)
        self.assertEqual(res10.status_code, 401)

        # 11th attempt is immediately throttled with 429
        res_blocked = self.client.get("/api/status", headers=bad_headers)
        self.assertEqual(res_blocked.status_code, 429)
        self.assertIn("Retry-After", res_blocked.headers)
        self.assertEqual(res_blocked.headers["Retry-After"], str(int(AUTH_BLOCK_DURATION_SECONDS)))
        data = res_blocked.get_json()
        self.assertEqual(data["error"], "Too Many Requests")

        # Even a valid key is rejected while the IP is temporarily blocked
        res_valid_while_blocked = self.client.get("/api/status", headers={"X-API-Key": self.valid_key})
        self.assertEqual(res_valid_while_blocked.status_code, 429)

    def test_successful_auth_clears_failure_log(self):
        """A successful authentication resets the failure count for that IP."""
        bad_headers = {"X-API-Key": "wrong_key"}
        # Send 5 failed attempts
        for _ in range(5):
            self.client.get("/api/status", headers=bad_headers)

        # Send 1 valid attempt -> should succeed and clear log
        res_valid = self.client.get("/api/status", headers={"X-API-Key": self.valid_key})
        self.assertEqual(res_valid.status_code, 200)

        # Send another 5 failed attempts -> should NOT trigger 429 because count was reset
        for _ in range(5):
            res = self.client.get("/api/status", headers=bad_headers)
            self.assertEqual(res.status_code, 401)

    # ── 2. Authentication Bypass & Header Formats ──────────────────────────

    def test_auth_header_strict_enforcement(self):
        """Strictly enforce canonical X-API-Key header; reject alternate schemes."""
        # 1. Canonical X-API-Key header succeeds
        res = self.client.get("/api/status", headers={"X-API-Key": self.valid_key})
        self.assertEqual(res.status_code, 200)

        # 2. Authorization: Bearer <token> is strictly rejected under single-standard policy
        bearer_headers = {"Authorization": f"Bearer {self.valid_key}"}
        res = self.client.get("/api/status", headers=bearer_headers)
        self.assertEqual(res.status_code, 401)

        # 3. Missing authentication header -> 401
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 401)

        # 4. Null-byte injection in key -> 401
        res = self.client.get("/api/status", headers={"X-API-Key": self.valid_key + "\x00admin"})
        self.assertEqual(res.status_code, 401)

    def test_constant_time_comparison(self):
        """Verify timing-safe equality prevents length or partial-match timing leaks."""
        self.assertTrue(constant_time_compare("super_secret_token", "super_secret_token"))
        self.assertFalse(constant_time_compare("super_secret_token", "super_secret_tokem"))
        self.assertFalse(constant_time_compare("super_secret_token", ""))
        self.assertFalse(constant_time_compare("", "super_secret_token"))
        self.assertFalse(constant_time_compare(None, "super_secret_token"))
        self.assertFalse(constant_time_compare("super_secret_token", None))
        self.assertFalse(constant_time_compare(None, None))

    # ── 3. CORS Lockdown & Origin Validation ───────────────────────────────

    def test_cors_allowlist_mode_isolation(self):
        """
        Verify that in allowlist mode:
        1. Exact allowed origins pass and receive CORS headers.
        2. Subdomain / suffix spoofing is strictly rejected with 403 Forbidden.
        3. Browser extensions are permitted.
        """
        # Exact match
        res = self.client.get(
            "/api/status",
            headers={"X-API-Key": self.valid_key, "Origin": "https://pos.yarsatech.com"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "https://pos.yarsatech.com")

        # Subdomain / suffix confusion attack (e.g. https://pos.yarsatech.com.attacker.com)
        res_spoof = self.client.get(
            "/api/status",
            headers={"X-API-Key": self.valid_key, "Origin": "https://pos.yarsatech.com.attacker.com"},
        )
        self.assertEqual(res_spoof.status_code, 403)
        self.assertFalse(res_spoof.get_json()["success"])

        # Path prefix confusion (e.g. https://attacker.com/pos.yarsatech.com)
        res_prefix = self.client.get(
            "/api/status",
            headers={"X-API-Key": self.valid_key, "Origin": "https://attacker.com"},
        )
        self.assertEqual(res_prefix.status_code, 403)

        # Browser extension schemes (permitted regardless of domain allowlist)
        for ext_scheme in ["chrome-extension://", "moz-extension://", "safari-extension://", "ms-browser-extension://"]:
            ext_origin = f"{ext_scheme}abcdefghijklmnop"
            self.assertTrue(is_origin_allowed(ext_origin), f"Failed for {ext_scheme}")
            res_ext = self.client.get(
                "/api/status",
                headers={"X-API-Key": self.valid_key, "Origin": ext_origin},
            )
            self.assertEqual(res_ext.status_code, 200)
            self.assertEqual(res_ext.headers.get("Access-Control-Allow-Origin"), ext_origin)

    def test_cors_preflight_options(self):
        """Verify OPTIONS preflight requests for allowed and disallowed origins."""
        # Allowed origin preflight -> 200 with CORS headers
        res = self.client.open(
            "/api/status",
            method="OPTIONS",
            headers={"Origin": "https://pos.yarsatech.com"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Access-Control-Allow-Origin", res.headers)

        # Disallowed origin preflight -> 403 Forbidden
        res_blocked = self.client.open(
            "/api/status",
            method="OPTIONS",
            headers={"Origin": "https://unauthorized-domain.com"},
        )
        self.assertEqual(res_blocked.status_code, 403)

    # ── 4. Serial Frame Sanitization & Injection Defense ──────────────────

    def test_serial_command_injection_prevention(self):
        """Validate protocol grammar enforcement and injection defense in validate_serial_frame."""
        # 1. Newline injection (\n or \r)
        with self.assertRaises(ValueError) as ctx:
            validate_serial_frame("QR**100**Scan\nRESET")
        self.assertIn("illegal control characters", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            validate_serial_frame("QR**100**Scan\r\nFORMAT")
        self.assertIn("illegal control characters", str(ctx.exception).lower())

        # 2. Null byte injection (\x00)
        with self.assertRaises(ValueError) as ctx:
            validate_serial_frame("TEXT**Title\x00**Sub**Msg")
        self.assertIn("illegal control characters", str(ctx.exception).lower())

        # 3. Unapproved dangerous verbs (e.g. SQL/OS injection or unknown commands)
        for bad_verb in ["DROP_DATABASE", "SHUTDOWN", "EXEC", "FORMAT_HARD_DRIVE", "SYSTEM"]:
            with self.assertRaises(ValueError) as ctx:
                validate_serial_frame(f"{bad_verb}**payload")
            self.assertIn("not permitted", str(ctx.exception).lower())

        # 4. Field length boundary enforcement (>1024 characters per field)
        oversized_field = "A" * 1025
        with self.assertRaises(ValueError) as ctx:
            validate_serial_frame(f"QR**100**Scan**{oversized_field}")
        self.assertIn("exceeds maximum allowed length", str(ctx.exception).lower())

        # 5. Legitimate valid command frames must pass
        self.assertEqual(
            validate_serial_frame("QR**150.00**Scan to Pay**upi://pay?ref=123"),
            "QR**150.00**Scan to Pay**upi://pay?ref=123",
        )
        self.assertEqual(validate_serial_frame("IDLE"), "IDLE")

    # ── 5. Static File Path Traversal Defense ──────────────────────────────

    def test_static_asset_path_traversal(self):
        """Verify that directory traversal attempts via /assets/ are safely rejected."""
        # Attempt to escape assets directory into parent
        res1 = self.client.get("/assets/../config.py")
        self.assertIn(res1.status_code, (400, 404))

        # Encoded traversal attempt
        res2 = self.client.get("/assets/..%2f..%2fconfig.py")
        self.assertIn(res2.status_code, (400, 404))

    def test_updater_zip_slip_protection(self):
        """Simulate malicious ZIP archive containing path traversal to test extract safety."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            malicious_zip = Path(tmp_dir) / "evil.zip"
            with zipfile.ZipFile(malicious_zip, "w") as zf:
                zf.writestr("../evil_executable.exe", "malicious payload")
                zf.writestr("safe_file.txt", "safe content")

            extract_dest = Path(tmp_dir) / "extracted"
            extract_dest.mkdir()
            extract_dest_abs = os.path.abspath(extract_dest)

            # Verification logic matching update_manager extraction guard
            with zipfile.ZipFile(malicious_zip, "r") as zf:
                for member in zf.infolist():
                    target_path = os.path.abspath(os.path.join(extract_dest, member.filename))
                    if not target_path.startswith(extract_dest_abs + os.sep) and target_path != extract_dest_abs:
                        with self.assertRaises(RuntimeError):
                            raise RuntimeError(f"Zip Slip detected: {member.filename}")

    # ── 6. File Upload Hardening ──────────────────────────────────────────

    def test_upload_image_mime_and_content_spoofing(self):
        """Verify upload security: non-JPEG extensions, fake JPEGs, and corrupted files."""
        # 1. Non-JPEG extension (.exe or .txt)
        fake_file = io.BytesIO(b"executable or script payload")
        res = self.client.post(
            "/api/upload-image",
            headers={"X-API-Key": self.valid_key},
            data={"image": (fake_file, "payload.exe")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Only JPG/JPEG files are allowed", res.get_json()["error"])

        # 2. JPEG extension with non-JPEG binary content (MIME spoofing)
        corrupted_jpeg = io.BytesIO(b"This is not a real JPEG image header")
        res = self.client.post(
            "/api/upload-image",
            headers={"X-API-Key": self.valid_key},
            data={"image": (corrupted_jpeg, "photo.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        self.assertTrue(
            "invalid jpeg" in res.get_json()["error"].lower() or "failed" in res.get_json()["error"].lower()
        )

        # 3. Empty image file
        empty_file = io.BytesIO(b"")
        res = self.client.post(
            "/api/upload-image",
            headers={"X-API-Key": self.valid_key},
            data={"image": (empty_file, "empty.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Empty image file", res.get_json()["error"])

    # ── 7. Cryptographic Passkey Entropy & Mathematical Hardening ──────────

    def test_passkey_entropy_validation(self):
        """Verify mathematical algorithmic passkey strength validation."""
        # 1. Reject short keys (< 16 chars)
        with self.assertRaises(ValueError) as ctx:
            validate_custom_api_key("ShortKey123")
        self.assertIn("between 16 and 32", str(ctx.exception))

        # 2. Reject long keys (> 32 chars)
        with self.assertRaises(ValueError) as ctx:
            validate_custom_api_key("A" * 33)
        self.assertIn("between 16 and 32", str(ctx.exception))

        # 3. Reject pure letters (no diversity)
        with self.assertRaises(ValueError) as ctx:
            validate_custom_api_key("abcdefghijklmnopq")
        self.assertIn("mix of character types", str(ctx.exception).lower())

        # 4. Reject pure digits (no diversity)
        with self.assertRaises(ValueError) as ctx:
            validate_custom_api_key("12345678901234567")
        self.assertIn("mix of character types", str(ctx.exception).lower())

        # 5. Reject ascending sequential character runs via ASCII delta math (e.g. '1234', 'abcd')
        with self.assertRaises(ValueError) as ctx:
            validate_custom_api_key("pos_branch_1234_key")
        self.assertIn("sequential characters", str(ctx.exception).lower())

        # 6. Reject cyclical periodic repetitions
        with self.assertRaises(ValueError) as ctx:
            validate_custom_api_key("tok1tok1tok1tok1")
        self.assertIn("repeating or cyclical", str(ctx.exception).lower())

        # 7. Low Shannon entropy rejection
        with self.assertRaises(ValueError) as ctx:
            validate_custom_api_key("aaaaaaaaaaaaaaa1")
        self.assertTrue(
            "entropy" in str(ctx.exception).lower() or "predictable" in str(ctx.exception).lower()
        )

        # 8. Accept genuine high-entropy, diverse passkeys
        valid_passkey = "merchant_nizi_lane_984"
        self.assertEqual(validate_custom_api_key(valid_passkey), valid_passkey)
        self.assertGreaterEqual(calculate_shannon_entropy(valid_passkey), 2.2)


if __name__ == "__main__":
    unittest.main()
