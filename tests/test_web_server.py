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

from web_server import app, device
from config import config


class TestWebServerRoutes(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
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
        mock_device.get_ble.return_value = {
            "success": True,
            "response": "BLE_ON",
            "error": None,
        }
        res = self.client.get("/api/get-ble", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertTrue(data["ble_on"])

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
        mock_device.get_ble.return_value = {"success": True, "response": "BLE_OFF", "error": None}
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


if __name__ == "__main__":
    unittest.main()
