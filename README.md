# CAME Connect (Unofficial) · Home Assistant Custom Integration

> Control CAME gates via CAME Connect cloud from Home Assistant.
> **Unofficial** community integration — not affiliated with CAME.
> Tested with a **CAME ZLX24SA board**. Other board types may or may not work.

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-41BDF5?logo=homeassistant&logoColor=white)
![HACS](https://img.shields.io/badge/HACS-Custom%20Repository-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

- Log in to **CAME Connect** and control your gate/automation
- Exposes a **Cover** entity (`cover.gate`) with **open / close / stop**
- Status sensors (e.g. connection state, last update)
- Config Flow (UI) — no YAML required
- Adjustable poll interval (via Options) - TODO

> **Note:** API and endpoints are based on reverse-engineered calls used by CAME’s web app. CAME can change them at any time.

---

## ✅ Requirements

- Home Assistant 2023.9+ (tested on recent HA releases)
- Your Client Id and Client Secret (see below on how to get these)
- A valid **CAME Connect** account (username/password)
- Your **Device ID** (from your CAME Connect device). This can be found at the end of the URL (e.g. `https://cameconnect.net/home/devices/XXXXXX`) once you have selected your site and then your device. Probably will be 6 digits.
- A CAME controller that works with the CAME Connect cloud  
  (⚠️ confirmed on **ZLX24SA board**, other models untested)

---

## 📦 Installation

### Option A — HACS (Custom repository)

1. In HACS → **Integrations** → 3-dot menu → **Custom repositories**.
2. Repository: `https://github.com/sdeagh/came_connect`  
   Category: **Integration** → **Add**.
3. Install **CAME Connect (Unofficial)**.
4. **Restart Home Assistant**.
5. Go to **Settings → Devices & Services → + Add Integration → CAME Connect (Unofficial)**.

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

The integration internally uses a **Redirect URI** (see the next section).  
Default **poll interval** is **5 seconds** and can be changed later in **Options**.

No YAML configuration is supported.

---

## 🔑 How to Obtain Client ID and Client Secret

CAME does not provide a public developer portal. Instead, we reuse the same OAuth
client credentials that the web app uses. You can extract them yourself:

1. Open [https://beta.cameconnect.net](https://beta.cameconnect.net) (or [https://app.cameconnect.net](https://app.cameconnect.net)) in a desktop browser but **don't** log in yet.
2. Open your browser’s **Developer Tools → Network** tab.
3. **Log in** to the web application
4. Look for a request to an endpoint like:

https://auth.cameconnect.net/oauth/token

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

## 🔁 About the Redirect URI (important)

CAME’s OAuth server checks that the `redirect_uri` **exactly matches** the ones registered for your OAuth client.

- If your client is registered against the **beta** site, you must use: https://beta.cameconnect.net/role
- If your client is registered against the **production** site, you must use: https://app.cameconnect.net/role

This integration defaults to the **beta** redirect (because that’s what our test client requires).  
If your client uses production, open **Options → Advanced** and set a **Redirect URI override**.

**Typical error if it doesn’t match:**
auth-code failed: 400 {"error":"invalid_request","error_description":
"The request is missing a required parameter ... The 'redirect_uri' parameter
does not match any of the OAuth 2.0 Client's pre-registered redirect urls."}

---

## ⚙️ Options

- **Poll interval (seconds)** — default **5**
- **Redirect URI override** — optional (use if your client is bound to `https://app.cameconnect.net/role` or a future URL)

> You can change options in **Settings → Devices & Services → CAME Connect → Configure**.

---

## 🧩 Entities

### Cover

- `cover.came_gate` — supports **open**, **close**, **stop**

### Sensors (may vary)

- `sensor.came_connect_status` — connection / last update
- Additional sensors can be added as the API is expanded.

---

## 🛠️ Services

- Standard **cover** services:
  - `cover.open_cover`
  - `cover.close_cover`
  - `cover.stop_cover`

---

## 🔍 Troubleshooting

### Redirect URI mismatch (400 invalid_request)

Your OAuth client is registered to a different URL.  
**Fix:** In Options set **Redirect URI override** to the correct value (typically `https://app.cameconnect.net/role` or `https://beta.cameconnect.net/role`).

### Auth fails / invalid credentials

- Double-check **Client ID/Secret**, **Username**, **Password**.
- Make sure your CAME account has access to the **Device ID** you entered.

### No entities created

- Open **Settings → System → Logs** and enable debug (below).
- Verify your Device ID is correct and reachable via CAME Connect.

### Enable debug logging

Add to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.came_connect: debug

Then restart HA and check Settings → System → Logs.
```

---

## 🔐 Security & Privacy

- Credentials are stored by Home Assistant’s standard config entry storage.

- Client Secret is sensitive — treat it like a password.

- The integration talks only to official \*.cameconnect.net endpoints used by the web app.

---

## 🧭 Roadmap

Auto-discovery of devices (multi-device accounts)

More sensors (gate state, obstruction, errors if exposed)

Local control if/when APIs allow

Config flow to auto-probe the correct redirect URI

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
