"""
Tests for ota/firmware_api.py

Run with:
    python -m pytest tests/test_firmware_api.py -v
or directly:
    python tests/test_firmware_api.py
"""
import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

# Add the project root to sys.path so imports work without installing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ota.firmware_api import (
    extract_model_code,
    _strip_firmware_prefix,
    _parse_version_tuple,
    _is_newer,
    build_update_url,
    get_firmware_by_model,
    check_update_available,
    _FIRMWARE_UPDATE_PAGE,
)


# ── extract_model_code ────────────────────────────────────────────────────────

class TestExtractModelCode(unittest.TestCase):

    def test_b31_compact(self):
        self.assertEqual(extract_model_code("NIZIPOSB31"), "B31")

    def test_b30_compact(self):
        self.assertEqual(extract_model_code("NIZIPOSB30"), "B30")

    def test_b32_compact(self):
        self.assertEqual(extract_model_code("NIZIPOSB32"), "B32")

    def test_b33_compact(self):
        self.assertEqual(extract_model_code("NIZIPOSB33"), "B33")

    def test_b31_with_underscores(self):
        self.assertEqual(extract_model_code("NIZI_POS_B31"), "B31")

    def test_b30_with_underscores(self):
        self.assertEqual(extract_model_code("NIZI_POS_B30"), "B30")

    def test_lowercase(self):
        self.assertEqual(extract_model_code("niziposb31"), "B31")

    def test_mixed_case(self):
        self.assertEqual(extract_model_code("NiziPosB32"), "B32")

    def test_none_returns_none(self):
        self.assertIsNone(extract_model_code(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(extract_model_code(""))

    def test_unrecognized_returns_none(self):
        self.assertIsNone(extract_model_code("UNKNOWN_DEVICE"))

    def test_result_is_uppercase(self):
        result = extract_model_code("niziposb31")
        self.assertEqual(result, result.upper())


# ── _strip_firmware_prefix ────────────────────────────────────────────────────

class TestStripFirmwarePrefix(unittest.TestCase):

    def test_full_prefix(self):
        self.assertEqual(_strip_firmware_prefix("FW-B31-v1.2.0"), "1.2.0")

    def test_v_prefix(self):
        self.assertEqual(_strip_firmware_prefix("v2.0.0"), "2.0.0")

    def test_no_prefix(self):
        self.assertEqual(_strip_firmware_prefix("2.0.0"), "2.0.0")

    def test_b30_prefix(self):
        self.assertEqual(_strip_firmware_prefix("FW-B30-v1.0.5"), "1.0.5")

    def test_rc_version_strip(self):
        # rc suffix should not affect extraction of leading numeric part
        result = _strip_firmware_prefix("FW-B31-v2.0.0-rc.1")
        self.assertTrue(result.startswith("2.0"))

    def test_empty_string(self):
        result = _strip_firmware_prefix("")
        self.assertEqual(result, "")


# ── _parse_version_tuple ──────────────────────────────────────────────────────

class TestParseVersionTuple(unittest.TestCase):

    def test_plain_version(self):
        self.assertEqual(_parse_version_tuple("2.0.0"), (2, 0, 0))

    def test_v_prefixed(self):
        self.assertEqual(_parse_version_tuple("v1.2.3"), (1, 2, 3))

    def test_capital_v(self):
        self.assertEqual(_parse_version_tuple("V1.2.3"), (1, 2, 3))

    def test_two_part(self):
        self.assertEqual(_parse_version_tuple("1.5"), (1, 5))

    def test_empty(self):
        self.assertEqual(_parse_version_tuple(""), ())

    def test_none(self):
        self.assertEqual(_parse_version_tuple(None), ())


# ── _is_newer ─────────────────────────────────────────────────────────────────

class TestIsNewer(unittest.TestCase):

    def test_newer_patch(self):
        self.assertTrue(_is_newer("2.0.1", "2.0.0"))

    def test_newer_minor(self):
        self.assertTrue(_is_newer("1.3.0", "1.2.0"))

    def test_newer_major(self):
        self.assertTrue(_is_newer("3.0.0", "2.9.9"))

    def test_same_version(self):
        self.assertFalse(_is_newer("2.0.0", "2.0.0"))

    def test_older(self):
        self.assertFalse(_is_newer("1.9.9", "2.0.0"))

    def test_api_version_vs_device(self):
        # API: FW-B31-v1.2.0 stripped → 1.2.0 vs device: 1.1.0
        latest = _strip_firmware_prefix("FW-B31-v1.2.0")
        self.assertTrue(_is_newer(latest, "1.1.0"))

    def test_device_up_to_date(self):
        latest = _strip_firmware_prefix("FW-B31-v1.2.0")
        self.assertFalse(_is_newer(latest, "1.2.0"))


# ── build_update_url ──────────────────────────────────────────────────────────

class TestBuildUpdateUrl(unittest.TestCase):

    def test_all_params(self):
        url = build_update_url("B31", "FW-B31-v1.2.0", "COM15")
        self.assertIn("model=B31", url)
        self.assertIn("firmware=FW-B31-v1.2.0", url)
        self.assertIn("port=COM15", url)
        self.assertTrue(url.startswith(_FIRMWARE_UPDATE_PAGE))

    def test_no_port(self):
        url = build_update_url("B30", "FW-B30-v1.0.5", None)
        self.assertIn("model=B30", url)
        self.assertNotIn("port=", url)

    def test_port_with_special_chars(self):
        # Linux port like /dev/ttyUSB0 should be URL-encoded
        url = build_update_url("B32", "FW-B32-v1.0.0", "/dev/ttyUSB0")
        self.assertIn("port=", url)
        self.assertIn("ttyUSB0", url)

    def test_empty_params_returns_base(self):
        url = build_update_url("", "", None)
        self.assertEqual(url, _FIRMWARE_UPDATE_PAGE)

    def test_url_contains_base(self):
        url = build_update_url("B31", "FW-B31-v1.2.0", "COM3")
        self.assertIn("yarsa.tech/firmware-update", url)


# ── get_firmware_by_model (mocked HTTP) ───────────────────────────────────────

class TestGetFirmwareByModel(unittest.TestCase):

    def _make_response(self, success=True, data=None, error=None):
        payload = {
            "message": {
                "success": success,
                "message": "Firmware found" if success else "Not found",
                "data": data or {
                    "model": "B31",
                    "item_code": "P063101",
                    "item_prefix": "P0631",
                    "firmware_version": "FW-B31-v1.2.0",
                    "firmware_zip_url": "/files/fw_b31_v120.zip",
                    "remark": "Stable release",
                },
                "error": error,
            }
        }
        return json.dumps(payload).encode("utf-8")

    @patch("ota.firmware_api.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._make_response()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        data = get_firmware_by_model("B31")
        self.assertEqual(data["firmware_version"], "FW-B31-v1.2.0")
        self.assertEqual(data["model"], "B31")

    @patch("ota.firmware_api.urllib.request.urlopen")
    def test_api_error_response(self, mock_urlopen):
        payload = json.dumps({
            "message": {
                "success": False,
                "message": "Firmware not found",
                "data": {},
                "error": {"code": "FIRMWARE_NOT_FOUND", "message": "No firmware mapped"},
            }
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with self.assertRaises(RuntimeError) as ctx:
            get_firmware_by_model("B99")
        self.assertIn("FIRMWARE_NOT_FOUND", str(ctx.exception))

    @patch("ota.firmware_api.urllib.request.urlopen")
    def test_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = OSError("Connection refused")
        with self.assertRaises(RuntimeError) as ctx:
            get_firmware_by_model("B31")
        self.assertIn("Connection refused", str(ctx.exception))

    @patch("ota.firmware_api.urllib.request.urlopen")
    def test_invalid_json(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with self.assertRaises(RuntimeError) as ctx:
            get_firmware_by_model("B31")
        self.assertIn("invalid JSON", str(ctx.exception))


# ── check_update_available ────────────────────────────────────────────────────

class TestCheckUpdateAvailable(unittest.TestCase):

    def _mock_api(self, firmware_version="FW-B31-v1.2.0"):
        return {
            "model": "B31",
            "item_code": "P063101",
            "firmware_version": firmware_version,
            "firmware_zip_url": "/files/fw.zip",
            "remark": "",
        }

    @patch("ota.firmware_api.get_firmware_by_model")
    def test_update_available(self, mock_get):
        mock_get.return_value = self._mock_api("FW-B31-v1.2.0")
        result = check_update_available("NIZIPOSB31", "1.1.0", "COM15")

        self.assertTrue(result["update_available"])
        self.assertEqual(result["model"], "B31")
        self.assertEqual(result["installed"], "1.1.0")
        self.assertEqual(result["latest_clean"], "1.2.0")
        self.assertIn("model=B31", result["update_url"])
        self.assertIn("port=COM15", result["update_url"])
        self.assertIsNone(result["error"])

    @patch("ota.firmware_api.get_firmware_by_model")
    def test_no_update_same_version(self, mock_get):
        mock_get.return_value = self._mock_api("FW-B31-v1.2.0")
        result = check_update_available("NIZIPOSB31", "1.2.0")

        self.assertFalse(result["update_available"])
        self.assertIsNone(result["error"])

    @patch("ota.firmware_api.get_firmware_by_model")
    def test_no_update_newer_installed(self, mock_get):
        mock_get.return_value = self._mock_api("FW-B31-v1.2.0")
        result = check_update_available("NIZIPOSB31", "1.3.0")

        self.assertFalse(result["update_available"])

    @patch("ota.firmware_api.get_firmware_by_model")
    def test_api_error_graceful(self, mock_get):
        mock_get.side_effect = RuntimeError("MODEL_NOT_FOUND")
        result = check_update_available("NIZIPOSB31", "1.0.0")

        self.assertFalse(result["update_available"])
        self.assertIn("MODEL_NOT_FOUND", result["error"])

    def test_unknown_device_id(self):
        result = check_update_available("UNKNOWN_DEVICE_XYZ", "1.0.0")
        self.assertFalse(result["update_available"])
        self.assertIsNotNone(result["error"])
        self.assertIsNone(result["model"])

    @patch("ota.firmware_api.get_firmware_by_model")
    def test_b30_device(self, mock_get):
        mock_get.return_value = {
            "model": "B30", "item_code": "P063001",
            "firmware_version": "FW-B30-v1.0.5",
            "firmware_zip_url": "/files/fw.zip", "remark": "",
        }
        result = check_update_available("NIZIPOSB30", "1.0.4", "COM3")
        self.assertTrue(result["update_available"])
        self.assertEqual(result["model"], "B30")
        self.assertIn("model=B30", result["update_url"])

    @patch("ota.firmware_api.get_firmware_by_model")
    def test_no_port_in_url(self, mock_get):
        mock_get.return_value = self._mock_api("FW-B31-v1.2.0")
        result = check_update_available("NIZIPOSB31", "1.0.0", port=None)
        self.assertNotIn("port=", result["update_url"])

    @patch("ota.firmware_api.get_firmware_by_model")
    def test_url_structure(self, mock_get):
        mock_get.return_value = self._mock_api("FW-B31-v1.2.0")
        result = check_update_available("NIZIPOSB31", "1.0.0", "COM15")
        url = result["update_url"]
        self.assertTrue(url.startswith("https://yarsa.tech/firmware-update"))
        self.assertIn("?", url)
        self.assertIn("model=B31", url)
        self.assertIn("firmware=FW-B31-v1.2.0", url)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestExtractModelCode))
    suite.addTests(loader.loadTestsFromTestCase(TestStripFirmwarePrefix))
    suite.addTests(loader.loadTestsFromTestCase(TestParseVersionTuple))
    suite.addTests(loader.loadTestsFromTestCase(TestIsNewer))
    suite.addTests(loader.loadTestsFromTestCase(TestBuildUpdateUrl))
    suite.addTests(loader.loadTestsFromTestCase(TestGetFirmwareByModel))
    suite.addTests(loader.loadTestsFromTestCase(TestCheckUpdateAvailable))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
