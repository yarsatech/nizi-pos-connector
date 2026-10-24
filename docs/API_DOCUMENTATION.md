# Nizi POS Connector API Documentation

The Nizi POS Connector background service exposes a REST API on `http://127.0.0.1:9121` for controlling the connected UART display device.

## Authentication

Every REST and WebSocket request to `http://127.0.0.1:9121` requires authentication via the `X-API-Key` HTTP header.

| Header | Description |
| :--- | :--- |
| `X-API-Key` | Your installation API token. |

### API Key Options

1. **Default Dynamic Key (Cryptographically Unique):**
   - On initial launch, the Desktop Connector automatically generates a cryptographically random 256-bit key.
   - The key is encrypted at rest using OS-level protection (Windows DPAPI / POSIX 0600).
   - Can be copied directly from the Desktop App Settings by clicking **"Copy Key"**.

2. **Standardized Merchant Integration Key (Multi-Terminal & Fleet Deployment):**
   - In multi-lane retail setups (e.g. supermarkets, multi-counter restaurants, or multi-branch stores), generating and configuring a different random dynamic token *per device/workstation* creates severe operational maintenance overhead when integrating POS billing systems.
   - Setting a verified custom key allows store administrators to configure a uniform, secure integration key across all checkout lanes and POS terminals without having to extract and manage distinct per-device tokens manually.
   - In the Desktop App, open **Settings** and click **"Set Custom Key"**.
   - **Key Validation Standards:** Must be between 16 and 32 characters and passes algorithmic mathematical validation:
     - **Shannon Entropy Analysis:** Enforces minimum information density ($\ge 2.2$ bits/symbol and $\ge 20.0$ bits total entropy) to mathematically reject low-entropy inputs.
     - **ASCII Delta Arithmetic:** Strict rejection of ascending/descending character runs (e.g. `1234`, `abcd`, `4321`) via first-order difference analysis ($\Delta_i \in \{+1, -1\}$).
     - **Periodicity Decomposition:** Mathematically detects and rejects repeating cyclical chunks (e.g. `a1a1a1a1`, `term1term1`).
     - **Character Diversity:** Enforces combined character classes (letters with numbers/symbols).
   - Setting a custom key is gated behind a confirmation prompt to ensure awareness that existing clients must be updated.
   - The connector encrypts and persists this key, immediately accepting it across all endpoints without requiring cloud dependencies.

> [!NOTE]
> For complete VAPT threat modeling, OWASP ASVS alignment, and ISO/IEC 27001 / ISO/IEC 25010 control mapping, refer to the [ISO Compliance & VAPT Security Guide](./ISO_COMPLIANCE_AND_VAPT.md).

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

### 5. Settings
**`GET /api/settings`**  
Queries the current device parameters (volume, brightness, BLE status, and idle configuration).

**Response (JSON):**
```json
{
  "success": true,
  "settings": {
    "volume": 80,
    "brightness": 100,
    "ble": true,
    "idle_config": {
      "mode": "SINGLE",
      "image_name": "IMG1"
    }
  }
}
```

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
Enable or disable Bluetooth Low Energy on the device (`DO_BLE_MODE_ENABLE` / `BLE_OFF`).

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
  "image_name": "IMG1",
  "inactivity_ms": 30000
}
```

**SLEEP_WAKE** — Scheduled sleep/wake cycle:
```json
{
  "mode": "SLEEP_WAKE",
  "image_name": "IMG1",
  "sleep_ms": 30000,
  "wake_ms": 120000
}
```

---

### 13. Get Idle Mode
**`GET /api/get-idle`** or **`POST /api/get-idle`**  
Queries the current idle configuration from the device (`GET_IDLE`).

---

### 14. Upload Idle Image
**`POST /api/upload-idle-image`**  
Uploads a persistent image for idle display modes (IMG1 or IMG2).

**Form Data:**
- `image`: Binary JPEG file.
- `slot`: `"1"` for IMG1 (primary), `"2"` for IMG2 (secondary, used by CYCLE mode).
- `size`: (Optional) Target size, e.g., `"320x480"`.

---

### 15. Query Bluetooth Status
**`GET /api/get-ble`** or **`POST /api/get-ble`**  
Queries whether the BLE stack is currently active (via `IS_BLE_ON`).

**Response (JSON):**
```json
{
  "success": true,
  "response": "TRUE",
  "ble_on": true,
  "error": null
}
```

---

### 16. Query Volume Level
**`GET /api/get-volume`** or **`POST /api/get-volume`**  
Queries the device speaker volume (via `GET_VOLUME`).

**Response (JSON):**
```json
{
  "success": true,
  "response": "VOLUME**80",
  "volume": 80,
  "error": null
}
```

---

### 17. Query Brightness Level
**`GET /api/get-brightness`** or **`POST /api/get-brightness`**  
Queries LCD backlight brightness (via `GET_BRIGHTNESS`).

**Response (JSON):**
```json
{
  "success": true,
  "response": "BRIGHTNESS**100",
  "brightness": 100,
  "error": null
}
```

---

### 18. Supported Languages
**`GET /api/languages`**  
Fetches the list of supported voice/sound firmware languages from the firmware API.

**Response (JSON):**
```json
{
  "success": true,
  "languages": ["English", "Nepali"]
}
```

---

### 19. Language Update URL
**`GET /api/language-update-url`** or **`POST /api/language-update-url`**  
Builds the WebSerial firmware update URL for a specific language and device model.

**Query Parameters / JSON Body:**
- `language`: Target language string (e.g. `"English"`).

**Response (JSON):**
```json
{
  "success": true,
  "url": "https://update.yarsatech.com/pos/?model=B31&port=COM15&lang=English"
}
```

---

### 20. Prepare for Flashing
**`POST /api/prepare-for-flash`**  
Suspends background serial auto-connection for a given duration and releases the serial port so an external tool (like WebSerial) can flash the hardware.

**Body (JSON):**
```json
{
  "duration": 120
}
```
*`duration` is in seconds (default `120`).*

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
  "firmware_id": "2.0.0",
  "update_available": false
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
| `403` | Forbidden. Attempted access from non-localhost IP or disallowed origin. |
| `429` | Too Many Requests. Throttled due to excessive failed auth attempts (max 10/min). `Retry-After: 60` enforced. |

---

## Integration Architecture & Multi-Terminal Setup

Depending on your architecture, network topology, and website security requirements, choose the integration method that fits best:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                INTEGRATION OPTIONS                                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  [Method 1: Direct REST/WS with Custom Key]                                            │
│  Billing Website (JS/Backend) ──── HTTP/WS (X-API-Key) ───► Desktop Connector (9121)   │
│  * Merchant sets matching custom key in Desktop Settings via "Set Custom Key"          │
│                                                                                        │
│  [Method 3: Extension Provider Bridge (Zero-Key)]                                      │
│  Billing Website ──── window.postMessage ───► Browser Extension ──── HTTP ───► Connector│
│  * Zero keys hardcoded in website. Extension handles auth & localhost dispatch.        │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Method 1: Direct Integration with Custom Key (Implemented)

For setups where your billing website or backend makes direct HTTP/WebSocket requests to `http://127.0.0.1:9121`:

1. **Merchant UI Setup:**
   - Open Nizi POS Desktop App > **Settings**.
   - Click **"Set Custom Key"**.
   - Input your custom merchant token or legacy API key (e.g., `nizipos-fixed-secret-token` or your merchant account ID) and click **Save Key**.
   - The key is securely encrypted at rest using OS-level protection (Windows DPAPI / POSIX permissions).
2. **Billing Request:**
   - Add the header `X-API-Key: <your-custom-key>` to your HTTP/WebSocket calls.
   - Any client with this key can command the local POS display without code modifications on existing legacy billing systems.

---

### Method 3: Browser Extension Provider Bridge (Zero-Key Web Integration)

> **Architectural Specification (Specification Only)**  
> This method completely decouples web applications from local API keys and eliminates HTTPS-to-HTTP mixed content warnings in modern browsers.

#### 1. How It Works
Instead of having billing web apps store or hardcode API keys and make direct `fetch('http://127.0.0.1:9121/...')` calls, the **Nizi POS Browser Extension** acts as a client-side provider bridge:

1. The billing webpage communicates with the extension via `window.postMessage` or the injected `window.niziPos` SDK object.
2. The extension's background service holds the local API key securely in Chrome/Edge sync storage.
3. The extension performs the localhost API requests and posts the result back to the page.

#### 2. Web Application Integration Example

Web developers do not include any secrets in their source code. Simply dispatch a DOM message or call the provider:

```javascript
// Example: Trigger dynamic payment QR code on customer display
async function displayPaymentQR(amount, qrPayload) {
  // Option A: Using window.postMessage bridge
  window.postMessage({
    target: "NIZI_POS_EXTENSION",
    action: "SHOW_QR",
    data: {
      amount: amount,
      qr_data: qrPayload,
      note: "Invoice #1042"
    }
  }, "*");
}

// Listen for device responses / customer confirmation
window.addEventListener("message", (event) => {
  if (event.data?.source === "NIZI_POS_EXTENSION") {
    const { action, status, payload } = event.data;
    console.log(`[POS Event] Action: ${action}, Status: ${status}`, payload);
    
    if (status === "SUCCESS") {
      console.log("QR successfully displayed on customer-facing terminal");
    }
  }
});
```

#### 3. Standard Message Payload Schema

**Request (Page to Extension):**
```json
{
  "target": "NIZI_POS_EXTENSION",
  "action": "SHOW_QR" | "PASS" | "FAIL" | "IDLE" | "STATUS",
  "data": {
    "amount": "450.00",
    "qr_data": "000201010212...",
    "note": "Payment Complete"
  }
}
```

**Response (Extension to Page):**
```json
{
  "source": "NIZI_POS_EXTENSION",
  "action": "SHOW_QR",
  "status": "SUCCESS" | "ERROR",
  "error": null,
  "data": {
    "device_connected": true,
    "port": "COM3"
  }
}
```

#### 4. Key Benefits of Method 3
- **Zero Secrets on the Web:** No API tokens exist in website JavaScript, GitHub repos, or browser network logs.
- **Multi-Terminal Portability:** Central cloud billing software works identically on 100 different checkout counters; each cashier machine's browser extension communicates with its own local desktop connector automatically.
- **No Mixed Content / CORS Restrictions:** Eliminates issues where secure HTTPS cloud POS platforms are blocked by browsers when calling insecure HTTP localhost (`http://127.0.0.1:9121`).
- **Complete VAPT Compliance:** Eliminates NIZI-001 static token risks entirely.

