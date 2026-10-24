"""
Tests for web_server.py
"""
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_server import app, device, reset_rate_limits
from config import config, Config


class TestWebServerRoutes(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        reset_rate_limits()
        config.set_cors_settings("allowlist", ["https://nagarik.gibl.com.np"])
        # Use config's api key for authentication headers
        self.api_key = config.api_key
        self.headers = {"X-API-Key": self.api_key}
        self.client = app.test_client()

    def test_api_auth_required(self):
        # Unauthenticated request should fail with 401
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 401)

        # Authenticated request should succeed
        res = self.client.get("/api/status", headers=self.headers)
        self.assertEqual(res.status_code, 200)

    @patch("web_server.device")
    def test_api_get_volume(self, mock_device):
        mock_device.get_volume.return_value = {
            "success": True,
            "response": "VOLUME**45",
            "error": None,
        }
        res = self.client.get("/api/get-volume", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["volume"], 45)

    @patch("web_server.device")
    def test_api_get_brightness(self, mock_device):
        mock_device.get_brightness.return_value = {
            "success": True,
            "response": "BRIGHTNESS**75",
            "error": None,
        }
        res = self.client.get("/api/get-brightness", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["brightness"], 75)

    @patch("web_server.device")
    def test_api_get_ble(self, mock_device):
        mock_device.is_ble_on.return_value = {
            "success": True,
            "response": "TRUE",
            "error": None,
        }
        res = self.client.get("/api/get-ble", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertTrue(data["ble_on"])

    @patch("web_server.device")
    def test_api_get_ble_false(self, mock_device):
        mock_device.is_ble_on.return_value = {
            "success": True,
            "response": "FALSE",
            "error": None,
        }
        res = self.client.get("/api/get-ble", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertFalse(data["ble_on"])

    @patch("web_server.device")
    def test_api_get_idle(self, mock_device):
        mock_device.get_idle.return_value = {
            "success": True,
            "response": "MODE:SINGLE,image_name=IMG2",
            "error": None,
        }
        res = self.client.get("/api/get-idle", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["idle_config"]["mode"], "SINGLE")
        self.assertEqual(data["idle_config"]["image_name"], "IMG2")

    @patch("web_server.device")
    def test_api_settings_get(self, mock_device):
        mock_device.get_volume.return_value = {"success": True, "response": "VOLUME**30", "error": None}
        mock_device.get_brightness.return_value = {"success": True, "response": "BRIGHTNESS**40", "error": None}
        mock_device.is_ble_on.return_value = {"success": True, "response": "FALSE", "error": None}
        mock_device.get_idle.return_value = {"success": True, "response": "MODE:CYCLE,img1=IMG1,time1=60000,img2=IMG2,time2=60000", "error": None}

        res = self.client.get("/api/settings", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        settings = data["settings"]
        self.assertEqual(settings["volume"], 30)
        self.assertEqual(settings["brightness"], 40)
        self.assertFalse(settings["ble"])
        self.assertEqual(settings["idle_config"]["mode"], "CYCLE")
        self.assertEqual(settings["idle_config"]["img1"], "IMG1")

    @patch("web_server.get_languages")
    def test_api_languages(self, mock_get_languages):
        mock_get_languages.return_value = ["en", "np", "hi"]
        res = self.client.get("/api/languages", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["languages"], ["en", "np", "hi"])

    @patch("web_server.device")
    @patch("web_server.build_update_url")
    def test_api_language_update_url(self, mock_build_update_url, mock_device):
        mock_device.device_id = "NIZIPOSB31"
        mock_device.port = "COM3"
        mock_build_update_url.return_value = "https://yarsa.tech/firmware-update?model=B31&port=COM3&language=np"

        # POST format
        res = self.client.post(
            "/api/language-update-url",
            json={"language": "np"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["url"], "https://yarsa.tech/firmware-update?model=B31&port=COM3&language=np")

    @patch("web_server.device")
    def test_api_prepare_for_flash(self, mock_device):
        res = self.client.post(
            "/api/prepare-for-flash",
            json={"duration": 180},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["suspended_for"], 180)
        mock_device.suspend_auto_connect.assert_called_with(180)

    def test_client_config_auth_required(self):
        # Unauthenticated request to /client-config should fail with 401
        res = self.client.get("/client-config")
        self.assertEqual(res.status_code, 401)

        # Authenticated request succeeds and returns cors info
        res = self.client.get("/client-config", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("cors_allowed_origins", data)
        self.assertIn("cors_mode", data)

    def test_cors_allowlist_enforcement(self):
        # Disallowed origin receives 403
        bad_headers = dict(self.headers)
        bad_headers["Origin"] = "https://malicious-website.com"
        res = self.client.get("/api/status", headers=bad_headers)
        self.assertEqual(res.status_code, 403)

        # Preflight OPTIONS from disallowed origin returns 403
        res = self.client.options("/api/status", headers={"Origin": "https://malicious-website.com"})
        self.assertEqual(res.status_code, 403)

        # Allowed origin receives 200 and Access-Control-Allow-Origin header
        good_origin = "https://nagarik.gibl.com.np"
        good_headers = dict(self.headers)
        good_headers["Origin"] = good_origin
        res = self.client.get("/api/status", headers=good_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), good_origin)
        self.assertIsNone(res.headers.get("Access-Control-Allow-Credentials"))

        # Allowed origin with trailing slash should also be permitted
        slash_headers = dict(self.headers)
        slash_headers["Origin"] = "https://nagarik.gibl.com.np/"
        res = self.client.get("/api/status", headers=slash_headers)
        self.assertEqual(res.status_code, 200)

        # Browser extension origins should always be permitted (authenticated via API key)
        ext_headers = dict(self.headers)
        ext_headers["Origin"] = "chrome-extension://bbdeicbggjgcjehkpndmdfbepgebeeli"
        res = self.client.get("/api/status", headers=ext_headers)
        self.assertEqual(res.status_code, 200)

    def test_cors_allow_all_mode(self):
        with patch.object(Config, "cors_mode", new_callable=lambda: "allow_all"):
            any_origin = "https://custom-merchant-erp.org"
            headers = dict(self.headers)
            headers["Origin"] = any_origin
            res = self.client.get("/api/status", headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), any_origin)

    @patch("web_server.device")
    def test_api_command_sanitization(self, mock_device):
        mock_device.send_command.return_value = {"success": True, "response": "OK", "error": None}

        # Valid command succeeds
        res = self.client.post(
            "/api/command",
            json={"command": "TEXT**Hello**World**Test"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)

        # Command with newline injection fails with 400
        res = self.client.post(
            "/api/command",
            json={"command": "QR**10.00\nFORMAT**payload"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 400)

        # Command with unapproved verb fails with 400
        res = self.client.post(
            "/api/command",
            json={"command": "DROP_DATABASE**payload"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 400)

    def test_failed_auth_rate_limiting(self):
        reset_rate_limits()

        # 9 failed attempts return 401 Unauthorized
        for i in range(9):
            res = self.client.get("/api/status", headers={"X-API-Key": f"invalid_key_{i}"})
            self.assertEqual(res.status_code, 401)

        # 10th failed attempt triggers block threshold
        res = self.client.get("/api/status", headers={"X-API-Key": "invalid_key_10"})
        self.assertEqual(res.status_code, 401)

        # 11th attempt is throttled and returns 429 Too Many Requests
        res = self.client.get("/api/status", headers={"X-API-Key": "invalid_key_11"})
        self.assertEqual(res.status_code, 429)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Too Many Requests")
        self.assertEqual(res.headers.get("Retry-After"), "60")

        # Even with valid key, blocked client is throttled until window expires
        res = self.client.get("/api/status", headers=self.headers)
        self.assertEqual(res.status_code, 429)

        # After reset, requests succeed normally
        reset_rate_limits()
        res = self.client.get("/api/status", headers=self.headers)
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
