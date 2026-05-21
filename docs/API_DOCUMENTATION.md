# Nizi POS Connector API Documentation

The Nizi POS Connector background service exposes a REST API on `http://127.0.0.1:9121` for controlling the connected UART display device.

## Authentication is handled via a fixed API key. This key is provided to authorized users via email and must be included in the `X-API-Key` header for all requests.

**Fixed API Token:** (Refer to your distribution email — documentation uses a placeholder name only, not the live secret.)

| Header | Description |
| :--- | :--- |
| `X-API-Key` | Your secure API token. |

---

## Endpoints

### 1. Connection Status
**`GET /api/status`**  
Returns the current connection state.

**Response (JSON):**
```json
{
  "connected": true,
  "port": "COM15",
  "device_id": "NIZIPOSB31",
  "firmware_id": "2.0.0"
}
```

---

### 2. Connect Device
**`POST /api/connect`**  
Triggers a connection attempt.

**Body (JSON):**
```json
{
  "port": "COM3"
}
```
*Note: Set `"port": null` for auto-detect.*

**Response (JSON):**
```json
{
  "success": true,
  "port": "COM3",
  "device_id": "NIZIPOSB31",
  "firmware_id": "2.0.0",
  "error": null
}
```

---

### 3. Disconnect Device
**`POST /api/disconnect`**  
Safely closes the serial connection.

---

### 4. Send Command
**`POST /api/command`**  
Sends a raw command string to the device.

**Body (JSON):**
```json
{
  "command": "IDLE"
}
```

---

### 5. Update Settings
**`POST /api/settings`**  
Updates device parameters.

**Body (JSON):**
```json
{
  "volume": 80,
  "brightness": 100,
  "screentime": 300
}
```

---

### 6. Upload Image
**`POST /api/upload-image`**  
Uploads and displays a JPEG image.

**Form Data:**
- `image`: Binary JPEG file.
- `size`: (Optional) Target size, e.g., `"320x480"`.

---

### 7. Firmware Info
**`GET /api/firmware`**  
Returns the connected device's firmware version and update URL.

**Response (JSON):**
```json
{
  "connected": true,
  "device_id": "NIZIPOSB31",
  "firmware_id": "2.0.0",
  "update_url": "https://github.com/yarsatech/nizi-pos-connector/releases?q=firmware+NIZIPOSB31"
}
```

---

### 8. Set Screen Timeouts
**`POST /api/timeout`**  
Configures screen timeouts to prevent burn-in. QR and Pass/Fail screens auto-return to Idle.

**Body (JSON):**
```json
{
  "qr_timeout": 300,
  "pf_timeout": 20
}
```
*Values are in seconds (1–3600).*

---

### 9. Buzzer Control
**`POST /api/buzzer`**  
Enable or disable the buzzer. B30 and B32 devices have the buzzer disabled by default.

**Body (JSON):**
```json
{
  "enabled": 1
}
```
*Set `0` to disable, `1` to enable.*

---

### 10. Buzzer Test
**`POST /api/buzzer-test`**  
Triggers a diagnostic buzzer test (BUZZERTEST command).

---

### 11. Bluetooth Control
**`POST /api/ble`**  
Enable or disable Bluetooth on the device.

**Body (JSON):**
```json
{
  "enabled": true
}
```
*Set `true` to turn ON, `false` to turn OFF.*

---

### 12. Set Idle Mode
**`POST /api/idle-mode`**  
Configures the device idle/inactivity behavior.

**Modes:**

**SINGLE** — Fixed static background image:
```json
{
  "mode": "SINGLE",
  "image_name": "IMG1"
}
```

**CYCLE** — Alternate between two images:
```json
{
  "mode": "CYCLE",
  "img1": "IMG1",
  "time1": 60000,
  "img2": "IMG2",
  "time2": 60000
}
```
*Durations are in milliseconds.*

**SLEEP** — Turn off backlight after inactivity:
```json
{
  "mode": "SLEEP",
  "sleep_ms": 30000
}
```

**SLEEP_WAKE** — Scheduled sleep/wake cycle:
```json
{
  "mode": "SLEEP_WAKE",
  "wake_ms": 120000,
  "sleep_ms": 30000
}
```

---

### 13. Get Idle Mode
**`POST /api/get-idle`**  
Queries the current idle configuration from the device (GET_IDLE).

---

### 14. Upload Idle Image
**`POST /api/upload-idle-image`**  
Uploads a persistent image for idle display modes (IMG1 or IMG2).

**Form Data:**
- `image`: Binary JPEG file.
- `slot`: `"1"` for IMG1 (primary), `"2"` for IMG2 (secondary, used by CYCLE mode).
- `size`: (Optional) Target size, e.g., `"320x480"`.

---

## WebSocket (Socket.IO) Communication

The background service uses Socket.IO for real-time status updates and command feedback.

**Connection URL:** `ws://127.0.0.1:9121` or `http://127.0.0.1:9121`

### Authentication

Socket.IO connections require a valid API token provided in the `auth` object during the initial handshake.

**Example (Client-side):**
```javascript
const socket = io("http://127.0.0.1:9121", {
  auth: {
    token: "your-fixed-secret-token"
  }
});
```

Connections missing the token or using an invalid token will be automatically rejected by the server.

### Client-to-Server Events

#### `send_command`
Sends a raw command to the device (alternative to the POST `/api/command` endpoint).

**Payload:**
```json
{
  "command": "IDLE"
}
```

### Server-to-Client Events

#### `device_status`
Emitted immediately upon connection and whenever the device connection state changes.

**Payload:**
```json
{
  "connected": true,
  "port": "COM15",
  "device_id": "NIZIPOSB31",
  "firmware_id": "2.0.0"
}
```

#### `command_result`
Emitted after a command sent via `send_command` is processed.

**Payload:**
```json
{
  "command": "IDLE",
  "success": true,
  "error": null
}
```

---

## Error Handling

| Status Code | Description |
| :--- | :--- |
| `200` | OK. Operation completed or data returned. |
| `400` | Bad Request. Missing parameters or invalid data. |
| `401` | Unauthorized. Missing or invalid `X-API-Key`. |
| `403` | Forbidden. Attempted access from non-localhost IP. |
