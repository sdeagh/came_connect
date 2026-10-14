# PLX WiFi: manual SIP and AUX2 gate opening

This path was validated by a user on one PLX WiFi X1 installation: Home
Assistant discovered the AUX2 button and pressing it opened the gate. OAuth
login worked with `https://app.cameconnect.net/role` on that installation.

This does not establish compatibility with every PLX variant. Video, incoming
calls, gate position, close/stop commands and continued phone registration
after a Home Assistant command have not been validated in this test.

## Why a separate setup path?

On the tested setup, `/api/sipaccounts` returned HTTP 200 with HTML, not SIP
account JSON. The web portal instead provided X1 plant metadata through:

```text
GET /api/evo/v1/sites/admin
GET /api/evo/v1/sites/<site-id>/plants
```

`plants` includes modules, Mobile App slots, SIP usernames, L3 addresses and
door/AUX labels. It did not provide a SIP password or mobile `DeviceToken`.
For a complete manual SIP configuration, this integration therefore reads
the web metadata and sends SIP commands without mobile push registration.
Other installations retain the existing token-based discovery path.

## Prerequisites

- A working CAME Connect integration using the intended CAME account.
- The matching Mobile App **SIP username and SIP password**. These differ
  from the CAME account email and password. Do not publish either password.
- The unit KeyCode, source L3 address, target SIP user and panel L3 address.

Use a dedicated Mobile App slot where possible. A slot shared with CAME
Access may affect phone registration; verify that the phone still works
after testing. Do not reset a phone's slot just to configure Home Assistant.

## Read the values for your installation

In the browser's Network panel, open the unit in CAME Connect and inspect
the JSON response to the `plants` request. Find the record whose `DeviceId`
matches the integration's Device ID.

| Integration setting | Source in that record |
| --- | --- |
| Keycode | `Keycode` |
| Mobile App SIP user | Matching `ModuleId: 2` / `FeatureId: 4` slot: `Settings` entry with `SettingId: 1`; also shown as `SipAccount.SipUsername` |
| Source L3 | The same slot's `Settings` entry with `SettingId: 2`; also shown as `SipAccount.BptL3Addr` |
| Subject label | That slot's `AliasName`, or its `Name` if no alias is set |
| Target SIP user | `ModuleId: 1` settings, `SettingId: 3` |
| Panel L3 | `ModuleId: 1` settings, `SettingId: 4` |

Select the slot belonging to the intended account, using `SipAccount.UserEmail`
to check ownership locally. Do not copy values from another user's slot.
Do not publish the raw response: it may contain KeyCodes, account information
and other private identifiers. This document intentionally has no real unit
IDs, KeyCodes, account details or passwords.

## Configure Home Assistant

1. Open CAME Connect **Options → Advanced BPT overrides**.
2. Fill in the Keycode, Source L3, Subject label, Target SIP user and Panel L3
   from the table above. Leave **Legacy device token** blank. Leave HA1 blank
   when using a SIP password. Save.
3. Open **BPT/X1 door button**, enter the matching SIP username and SIP password,
   and save. Before all these values are stored, the preview may still report
   the unavailable legacy SIP-account discovery; save the complete settings.
4. After the integration reloads, the BPT/X1 child device should show Open Door
   and the discovered AUX buttons. Reopening the options should show
   **Direct SIP (no device token; web plants metadata)**.

The tested installation opened its gate using **AUX2**, not Open Door. Use
the action assigned by your installer. Names come from the web metadata;
the integration must not assume every gate uses AUX2.

Test once only when you can verify the physical result. Confirm that CAME
Access still receives calls and controls the unit afterwards.

## OAuth and status notes

The original OAuth path is attempted first. For the observed HTTP 400
`invalid_grant` / `invalid_request` rejection, the integration retries once
with `/oauth/mfa/auth-code` and exchanges the returned code on
`/oauth/mfa/token`. This does **not** implement an interactive MFA code prompt.
Use the redirect accepted by your OAuth client; do not change a working URI
just because the browser is on a different hostname.

An online intercom may return `States: []` and `LastSeen: null` from
`devicestatus`. In that case, generic gate phase, movement, position and
last-seen sensors can remain unknown even when a SIP command succeeds.
