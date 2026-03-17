# BPT/X1 Door Setup

This integration treats BPT/X1 door opening as an optional add-on to the
normal CAME gate integration.

This guide is for BPT/X1 intercom units such as the **XTS7**.

## Recommended Setup

The cleanest approach is to create a **separate `cameconnect.net` account** for
Home Assistant and tie that account to its own dedicated **Mobile App slot** on
the intercom.

That gives you:

- a dedicated SIP user for Home Assistant
- a dedicated Mobile App password for the intercom path
- less chance of breaking the slot used by your everyday phone

## Which Account Should I Use?

For normal gate control, you can use your usual owner or administrator CAME
account.

For BPT/X1, the recommended setup is:

- keep your normal account for day-to-day app use
- create a **separate invited `cameconnect.net` account** for Home Assistant
- bind that account to its own dedicated **Mobile App slot**

This keeps the intercom integration separate from the slot used by your phone.

## Before You Start

Make sure the normal CAME integration is already working in Home Assistant
first.

You should already have:

- the integration added successfully
- valid CAME credentials
- the correct CAME device visible in Home Assistant

## Step 1: Create a Dedicated CAME Account

Create a separate `cameconnect.net` account that you want to dedicate to the
X1 path in Home Assistant.

## Step 2: Find the Unit Local IP

If you do not know the local IP of your XTS7:

1. Go to the **XTS7 panel**
2. Open **Settings**
3. Open **Advanced**
4. Open **Network**
5. Note the unit IP address

## Step 3: Configure the Mobile App Slot on the Unit

Open the unit web interface in a browser:

```text
http://<your-unit-ip>
```

Then:

1. Select **Installer**
2. Enter the installer password
   - on **XTS7**, the default is typically `112233`
   - on other units, use your actual installer password
3. Open **Credentials**
4. Choose the **Mobile App** slot you want Home Assistant to use
5. Set a password for that slot
6. Note the slot's **SIP ID / SIP user**, for example `00700100001`

You will need:

- the **Mobile App SIP password**
- optionally the **Mobile App SIP user**

Safety note:

- changing the password of a Mobile App slot can affect any phone or integration
  already using that same slot
- this is why a dedicated slot for Home Assistant is strongly recommended

## Step 4: Invite the Dedicated Account

Using the **Came Access** app on Android or iPhone, sign in with the
administrator or owner account that already manages the installation.

Then go to:

1. **Profile**
2. **Installations** or **Systems**
3. Select your system
4. Select the **Video Entry unit** you want to control
5. Edit the **Mobile App** slot you prepared for Home Assistant
6. Send the invite to the new dedicated `cameconnect.net` account

Make sure you keep track of the **Mobile App SIP user** for that slot.

## Step 5: Accept the Invite

Sign in to the **Came Access** mobile app with the **new dedicated account**
and accept the invitation.

This step ensures the new account is actually linked to the installation and
the selected video entry unit.

## Step 6: Configure Home Assistant

Open the Home Assistant integration options:

1. **Settings -> Devices & Services**
2. Open **CAME Connect**
3. Open **Options**
4. Open **BPT/X1 door button**

Important:

- the integration entry that should control the BPT/X1 device must use the
  CAME account that was invited to that Mobile App slot
- if you created a dedicated `cameconnect.net` account for Home Assistant, use
  that account's CAME username and password in the integration

In normal setups, you usually only need:

- `Mobile App SIP password`
- optionally `Mobile App slot / SIP user`

Use `Mobile App slot / SIP user` when:

- you want to force the exact slot you prepared
- the unit has multiple enabled `Mobile App` slots
- the options flow asks you to choose between multiple discovered slots

## What The Integration Auto-Discovers

When you press the BPT button, the integration resolves the remaining details
from the authenticated CAME metadata path.

That normally means you do **not** need to fill:

- `BPT device token`
- `BPT keycode override`
- `BPT source L3 override`
- `BPT subject label override`
- `BPT target SIP user override`
- `BPT panel L3 override`

Leave those blank unless you are troubleshooting or forcing known-good values.

## Expected Result

When setup succeeds, Home Assistant should:

1. resolve the intercom and entry-panel metadata
2. keep the normal gate entities on the main **CAME Connect** device
3. create a separate **BPT/X1** child device
4. expose **Open Door**
5. expose discovered **AUX** buttons when the unit provides them

When live discovery is available, the options flow should also show:

- the selected Mobile App slot
- the intercom name
- the entry panel name
- the door action label

## What Should Appear After Setup?

In Home Assistant you should normally see:

- one main **CAME Connect** device for gate control
- one **BPT/X1** child device for intercom actions
- `Open Door` on the BPT/X1 device
- one or more discovered `AUX` buttons when the unit exposes AUX functions

## Automation Example

The BPT/X1 actions use the normal Home Assistant `button.press` service.

Example:

```yaml
service: button.press
target:
  entity_id: button.open_door
```

Example AUX button:

```yaml
service: button.press
target:
  entity_id: button.aux_1
```

## Advanced Overrides

The options flow also includes:

- `Advanced BPT overrides`

These fields are troubleshooting-only. Leave them blank unless autodiscovery
fails or you are forcing a known-good value from prior testing.

## Troubleshooting

### BPT/X1 device or buttons do not appear

- confirm the invited account accepted the invite in the **Came Access** app
- confirm the integration is using that same invited account
- verify the **Mobile App SIP password**
- if multiple Mobile App slots exist, set **Mobile App slot / SIP user**
  explicitly

### Gate works but Open Door does not

- recheck the Mobile App slot password in the unit web interface
- confirm you edited the correct Mobile App slot
- confirm the SIP user you noted matches the slot assigned to the invited
  account
- leave advanced overrides blank unless you are troubleshooting
