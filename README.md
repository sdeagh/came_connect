# CAME Connect (Unofficial) · Home Assistant Custom Integration

> Control CAME gates via CAME Connect cloud from Home Assistant.  
> **Unofficial** community integration — not affiliated with CAME.

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
- A valid **CAME Connect** account
- Your **Device ID** (from your CAME Connect device)

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
