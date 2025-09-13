# CAME Connect · Home Assistant Custom Integration

> Control CAME gates via CAME Connect cloud from Home Assistant.
> **Unofficial** community integration — not affiliated with CAME.
> Tested with a **CAME ZLX24SA board**. Other board types may or may not work.

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-41BDF5?logo=homeassistant&logoColor=white)
![HACS](https://img.shields.io/badge/HACS-Custom%20Repository-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

- Log in to **CAME Connect** and control your gate/automation
- **Real-time updates** via WebSocket (no periodic polling after startup)
- Exposes a **Cover** entity (`cover.gate`) with **open / close / stop**
- Status sensors: Phase, Position (%), Hub Online, Hub Last Seen, Error
- Config Flow (UI) — no YAML required
- Options for Redirect URI and WebSocket URL

> **Note:** API and endpoints are based on reverse-engineered calls used by CAME’s web app. CAME can change them at any time.

---

## ✅ Requirements

- Home Assistant 2023.9+ (tested on recent releases)
- **Client ID** and **Client Secret** (see “How to obtain…” below)
- A valid **CAME Connect** account (username/password)
- Your **Device ID**
  - Found at the end of the URL after selecting your site and device in the CAME Connect web app, e.g. https://app.cameconnect.net/home/devices/XXXXXX (typically 6 digits)
- A compatible **CAME** controller that works with CAME Connect
  - ⚠️ confirmed on **ZLX24SA board** (other models untested)

---

## 📦 Installation

### Option A — HACS (Custom repository)

1. In HACS → **Integrations** → 3-dot menu → **Custom repositories**.
2. Repository: `https://github.com/sdeagh/came_connect`  
   Category: **Integration** → **Add**.
3. Install **CAME Connect**.
4. **Restart Home Assistant**.
5. Go to **Settings → Devices & Services → + Add Integration → CAME Connect**.

### Option B — Manual

1. Copy this folder to your HA config:
2. **Restart Home Assistant**.
3. Add the integration from **Settings → Devices & Services**.

---

## 🔧 Configuration (UI)

When adding the integration you’ll be prompted for:

- **Client ID**
- **Client Secret**
- **Username (email)**
- **Password**
- **Device ID**

No YAML configuration is supported.

---

## 🔑 How to Obtain Client ID and Client Secret

CAME does not provide a public developer portal. Instead, we reuse the same OAuth
client credentials that the web app uses. You can extract them yourself:

1. Open [https://app.cameconnect.net](https://app.cameconnect.net)) in a desktop browser but **don't** log in yet.
2. Open your browser’s **Developer Tools → Network** tab.
3. **Log in** to the web application
4. Look for a request to an endpoint like:

`https://auth.cameconnect.net/oauth/token`

5. Select that request and look at the **Request Headers**.
6. Find the header:

Authorization: Basic <long-base64-string>

7. Copy the `<long-base64-string>` part and **decode it from Base64** (many online tools e.g. [https://www.base64decode.org](https://www.base64decode.org/) or `base64 -d` in a terminal).

- The result will be:
  ```
  clientId:clientSecret
  ```

8. Use those two values when configuring the integration.

⚠️ **Note:** These values are not officially documented and may change if CAME rotates or replaces them. If the integration suddenly fails, repeat the steps above to extract new values.

---

## 🔁 Redirect URI

Your OAuth client is registered to **exactly one** Redirect **URI**. Use the one that matches where you captured the Client ID/Secret:

- **Default (most users):** `https://app.cameconnect.net/role`
- **Beta (only if your client lives on beta):** `https://beta.cameconnect.net/role`

You can change this anytime in **Options → Redirect URI** (no reinstall; the integration reloads itself).

**Tips**

- Keep it **exactly** as shown (no trailing slash, case-sensitive).
- If login fails with a redirect mismatch, switch to the other URI.

**Typical mismatch error**

```
invalid_request: 'redirect_uri' does not match any registered URLs
```

---

## ⚙️ Options

After initial setup, you can tweak settings from the integration’s Options:

1. Go to **Settings → Devices & Services** in Home Assistant.
2. Find **CAME Connect** in your list of integrations.
3. Click the **cog icon (⚙️)** on the integration page.

You will see two configurable options:

- **Redirect URI**
  The URI used when authenticating with the CAME Connect cloud.
  Default: `https://app.cameconnect.net/role`

In most cases you don’t need to change this unless CAME updates their API endpoints.

- **WebSocket URL**
  The realtime events endpoint used to receive live state updates (no polling).
  Default: `wss://app.cameconnect.net/api/events-real-time`

You should not have to change either of these - only do so if you know what you are doing.

---

## 🧩 Entities

### Cover

- **Gate** (`cover.gate`) — supports **open**, **close**, **stop**  
  _Attributes:_ `phase` (code), `phase_name` (Open/Closed/Opening/Closing/Stopped), `direction` (Opening/Closing), `last_pos`, `raw_data`.

### Sensors

- **Gate Phase** (`sensor.gate_phase`) — human-readable phase (Open/Closed/Opening/Closing/Stopped).
- **Gate Position** (`sensor.gate_position`) — position in %, state class _measurement_.
- **Gate Hub Last Seen** (`sensor.gate_hub_last_seen`) — timestamp of the last update received.
- **Gate Error** (`sensor.gate_error`) — last non-zero error/response code (if exposed).

### Binary Sensors

- **Gate Moving** (`binary_sensor.gate_moving`) — **on** while opening/closing; off when open/closed/stopped.
- **Gate Hub Online** (`binary_sensor.gate_hub_online`) — cloud hub connectivity status (if exposed).

> Entity IDs may differ if you rename the device in Home Assistant.

---

## 🛠️ Services

This integration does **not** add custom services. Use the standard Home Assistant **cover** services:

- `cover.open_cover` — open the gate
- `cover.close_cover` — close the gate
- `cover.stop_cover` — stop movement

**Examples**

```yaml
# Open the gate
service: cover.open_cover
target:
  entity_id: cover.gate

# Close the gate
service: cover.close_cover
target:
  entity_id: cover.gate

# Stop the gate
service: cover.stop_cover
target:
  entity_id: cover.gate
```

---

## 🔍 Troubleshooting

### Redirect URI mismatch (400 invalid_request)

Your OAuth client is registered to a different URL.
**Fix:** In **Options** set **Redirect URI** to the correct value (typically `https://app.cameconnect.net/role`; use `https://beta.cameconnect.net/role` only if your client is registered on beta).

### WebSocket won’t connect / shows 401

- Confirm **Options → WebSocket URL** is `wss://app.cameconnect.net/api/events-real-time`.
- Make sure your Home Assistant host has correct **date/time** (OAuth can fail if the clock is off).
- Check network filters (AdGuard, corporate proxy, firewall, VPN) aren’t blocking `wss://app.cameconnect.net`.
- If you changed credentials, **remove & re-add** the integration to refresh tokens.

### Entities don’t update in real time

- Open **Settings → System → Logs** and enable debug (below) to see WS frames.
- Reload the integration: **Settings → Devices & Services → CAME Connect → Reload**.
- If the **Phase** or **Position** remains unknown, verify WS frames with `EventId: 21` are arriving (you’ll see them in the logs when debug is on).

### “No entities created”

- Verify **Client ID/Secret**, **Username/Password**, and **Device ID**.
- Confirm the device is visible in the CAME Connect app under the same account.

### Enable debug logging

Add to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.came_connect: debug
    custom_components.came_connect.api.ws: debug
    custom_components.came_connect.coordinator: debug
```

### Still Stuck?

- **Remove and re-add** the integration and check **Settings→System→Logs**
- Include a short log excerpt (with WS lines) when opening an issue.

---

## 🔐 Security & Privacy

- Credentials are stored by Home Assistant’s standard config entry storage.

- Client Secret is sensitive — treat it like a password.

- The integration talks only to official \*.cameconnect.net endpoints used by the web app.

---

## 🧭 Roadmap

- **Multi-device support**  
  Discover and add multiple CAME devices under one account; device picker in the config flow.

- **Richer entities**  
  Expose obstruction/photocell status (if available), fault codes mapped to friendly text, cycle/runtime counters.

- **WebSocket resilience**  
  Heartbeat (ping/pong), stale-connection watchdog, and proactive token refresh before expiry.

- **Smarter setup**  
  Auto-detect the correct Redirect URI, verify WebSocket URL, and fetch Device IDs automatically.

- **Diagnostics & logging**  
  One-click diagnostics download and a toggle to surface WS frames safely when debugging.

- **Localization & docs**  
  More translations and clearer setup/FAQ guides.

- **Testing & quality**  
  Add unit/integration tests and CI, and prepare for HACS default store inclusion.

Have a feature request? Please open a GitHub issue.

---

## 🤝 Contributing

PRs are welcome!

Code style: match HA core (black, isort, flake8 where applicable)

Folder layout:
custom_components/came_connect/
**init**.py
api.py
binary_sensor.py
config_flow.py
const.py
cover.py
manifest.json
sensor.py
translations/

Keep network calls in api.py, HA glue in platform files.

Avoid breaking changes; if necessary, bump version and document in Changelog.

---

## 🙏 Acknowledgements

Thanks to the HA community and everyone testing against different CAME setups.
This project is not affiliated with or endorsed by CAME.
