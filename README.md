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
- Optional **Open Door** and discovered **AUX** buttons for BPT/X1 intercom systems
- Status sensors: Phase, Position (%), Hub Online, Hub Last Seen, Error
- Config Flow (UI) — no YAML required
- Options for Redirect URI, WebSocket URL, and optional BPT door-open settings

> **Note:** API and endpoints are based on reverse-engineered calls used by CAME’s web app. CAME can change them at any time.
> BPT setup details are documented in [docs/user/bpt-door-setup.md](/home/d0m/Projects/gtapps/came_connect/docs/user/bpt-door-setup.md).

---

## ✅ Requirements

- Home Assistant 2023.9+ (tested on recent releases)
- **Client ID** and **Client Secret** (see “How to obtain…” below)
- A valid **CAME Connect** account (username/password)
- Your **Device ID**
  - Found at the end of the URL after selecting your site and device in the CAME Connect web app, e.g. https://app.cameconnect.net/home/devices/XXXXXX (typically 6 digits)
- A compatible **CAME** controller that works with CAME Connect
  - ⚠️ confirmed on **ZLX24SA board** (other models untested)

## ℹ️ Compatibility

- Gate and automation control is the main public feature of this integration.
- BPT/X1 intercom support has been validated on setups using **XTS7-style**
  indoor monitors.
- Other BPT/X1 or video-entry variants may still work, but they should be
  treated as compatible-on-test rather than guaranteed.

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

1. Open [https://app.cameconnect.net](https://app.cameconnect.net) in a desktop browser but **don't** log in yet.
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

The options flow is split into separate branches:

- **Cloud settings**
  Contains `Redirect URI` and `Realtime WebSocket URL`.
  Most users should leave both values at their defaults.

- **BPT/X1 door button**
  Only relevant for BPT/X1 intercom units such as XTS7 indoor monitors.
  Normal setup usually needs only:
  - **Mobile App SIP password**
  - optionally **Mobile App slot / SIP user** if more than one `Mobile App` slot is enabled on the account

  When live discovery is available, the options flow now shows:
  - a dropdown of valid Mobile App slots instead of a free-text SIP user field
  - a read-only discovery summary with the resolved intercom name, entry panel, door label, selected slot, and token source

- **Advanced BPT overrides**
  Contains the HA1, legacy device token, and low-level protocol overrides.
  These are normally auto-discovered from `/api/sipaccounts` plus the site/device metadata chain, so leave them blank unless autodiscovery fails or you are forcing known-good values from traces.

---

## 📟 BPT/X1 Intercom Setup

This section is only relevant for BPT/X1 intercom units such as the **XTS7**.
If you only want gate control, you can skip it.

### Recommended Approach

The cleanest setup is to use a **separate `cameconnect.net` account** for Home Assistant's
BPT/X1 access, so it can be tied to its own dedicated **Mobile App slot** on the unit.

That gives you:

- a dedicated SIP user for Home Assistant
- a separate Mobile App password for the X1 path
- less risk of interfering with the mobile app slot you use on your personal phone

### Before You Start

You should already have the normal CAME integration working first:

- the integration added in Home Assistant
- your main CAME account credentials working
- the correct CAME device visible in Home Assistant

### Which Account Should I Use?

For normal gate control, you can use your usual owner or administrator CAME
account.

For BPT/X1, the recommended setup is:

- keep your main account for day-to-day app use
- create a **separate invited `cameconnect.net` account** for Home Assistant
- bind that account to its own dedicated **Mobile App slot**

This avoids reusing the same Mobile App slot that your phone depends on.

### Step 1: Create a Dedicated CAME Account for Home Assistant

Create a second `cameconnect.net` account that you want Home Assistant to use for the
X1 integration path.

### Step 2: Find the Unit Local IP

If you do not know the local IP of your XTS7 unit:

1. Go to the **XTS7 panel**
2. Open **Settings**
3. Open **Advanced**
4. Open **Network**
5. Note the unit IP address

### Step 3: Set the Mobile App Password on the Unit

Open the unit web interface in your browser:

```text
http://<your-unit-ip>
```

Then:

1. Select **Installer**
2. Enter the installer password
   - for **XTS7**, the default is typically `112233`
   - for other units, use your actual installer password
3. Open **Credentials**
4. Choose the **Mobile App** slot you want to dedicate to Home Assistant
5. Set a password for that Mobile App slot
6. Note the slot's **SIP ID / SIP user**, for example `00700100001`

You will need:

- the **Mobile App SIP password** you just set
- the **Mobile App SIP user** if you want to force a specific slot or if multiple slots are enabled

Safety note:

- changing the password of a Mobile App slot can affect any phone or integration
  already using that same slot
- this is another reason to dedicate a separate Mobile App slot to Home Assistant

### Step 4: Invite the Dedicated Account to the Correct Video Entry Unit

Using the normal **Came Access** mobile app on Android or iPhone, sign in with the
administrator or owner account that already manages the system.

Then go to:

1. **Profile**
2. **Installations** or **Systems**
3. Select your system
4. Select the **Video Entry unit** you want to grant access to
5. Edit the **Mobile App** slot you prepared for Home Assistant
6. Send the invite to the new dedicated `cameconnect.net` account

Make sure you remember which **Mobile App SIP user** belongs to that slot.

### Step 5: Accept the Invite in the Mobile App

Now sign in to the **Came Access** Android or iOS app with the **new dedicated account**
and accept the invitation.

This step matters because the account must actually be linked to the system and the
selected video entry unit before Home Assistant can use that slot reliably.

### Step 6: Configure Home Assistant

In Home Assistant:

1. Open **Settings -> Devices & Services**
2. Open the **CAME Connect** integration
3. Open **Options**
4. Open **BPT/X1 door button**

Important:

- the integration entry that should control the BPT/X1 device must use the
  CAME account that was invited to that Mobile App slot
- if you create a dedicated `cameconnect.net` account for Home Assistant, use
  that account's CAME username and password in the integration

In normal setups, you usually only need:

- **Mobile App SIP password**
- optionally **Mobile App slot / SIP user**

Use **Mobile App slot / SIP user** when:

- you want to force the exact slot you prepared
- your unit has multiple enabled Mobile App slots
- the options flow asks you to choose between multiple discovered slots

Leave **Advanced BPT overrides** blank unless you are troubleshooting.

### What Home Assistant Should Discover

When setup succeeds, the integration should:

- resolve the intercom and entry-panel metadata automatically
- keep the normal gate entities on the main **CAME Connect** device
- create a separate **BPT/X1** child device
- expose **Open Door**
- expose one button per discovered **AUX** feature, when available

If live discovery is available, the options flow should also show:

- the selected Mobile App slot
- the resolved intercom name
- the entry panel name
- the door action label

### What Should Appear After Setup?

In Home Assistant you should normally see:

- one main **CAME Connect** device for gate or automation control
- one **BPT/X1** child device when intercom setup is enabled
- `Open Door` on that BPT/X1 device
- one or more discovered `AUX` buttons on that same BPT/X1 device when the
  unit exposes AUX functions

For more detail, see [docs/user/bpt-door-setup.md](/home/d0m/Projects/gtapps/came_connect/docs/user/bpt-door-setup.md).

---

## 🧩 Entities

### Cover

- **Gate** (`cover.gate`) — supports **open**, **close**, **stop**  
  _Attributes:_ `phase` (code), `phase_name` (Open/Closed/Opening/Closing/Stopped), `direction` (Opening/Closing), `last_pos`, `raw_data`.

### Button

- **Open Door** (`button.open_door`) — sends the BPT/X1 cloud SIP open-door command.
  _Attributes:_ `last_run`, `last_register_status`, `last_message_status`, `last_error`, SIP addressing fields.
- **AUX buttons** — one button per discovered BPT/X1 AUX feature on the intercom device.
  Labels come from the unit metadata when available.

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

This integration does **not** add custom services. Use the standard Home Assistant **cover** and **button** services:

- `cover.open_cover` — open the gate
- `cover.close_cover` — close the gate
- `cover.stop_cover` — stop movement
- `button.press` — trigger the optional BPT open-door button

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

# Trigger the BPT door-open action
service: button.press
target:
  entity_id: button.open_door
```

### Automation Example: X1 Door Or AUX

Entity IDs depend on your naming in Home Assistant, but the action is always
the standard `button.press` service.

```yaml
automation:
  - alias: Trigger X1 door
    triggers: []
    conditions: []
    actions:
      - action: button.press
        target:
          entity_id: button.open_door

  - alias: Trigger X1 AUX output
    triggers: []
    conditions: []
    actions:
      - action: button.press
        target:
          entity_id: button.aux_1
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

### BPT/X1 device or buttons do not appear

- Confirm the invited account accepted the invite in the **Came Access** app.
- Confirm the integration is using that same invited CAME account.
- Re-open **Options → BPT/X1 door button** and verify the **Mobile App SIP password**.
- If the unit has multiple Mobile App slots, set **Mobile App slot / SIP user**
  explicitly.

### Gate works but Open Door does not

- Recheck the Mobile App slot password in the unit web interface.
- Confirm you edited the correct **Mobile App** slot for the invited account.
- Confirm the **Mobile App SIP user** you noted from the unit matches the slot
  assigned to that invited account.
- Leave advanced overrides blank unless you are troubleshooting a known issue.

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
