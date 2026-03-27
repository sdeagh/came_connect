# Integration Overview

This document is a sanitized maintainer overview of the Home Assistant
integration. It describes the public architecture without including raw traces,
captured identifiers, or reverse-engineering artifacts.

## Scope

The integration supports two main capabilities:

- CAME gate or automation control through the CAME Connect cloud API
- Optional BPT/X1 intercom actions, currently exposed as Home Assistant buttons

## Main Runtime Modules

- [api.py](/custom_components/came_connect/api.py)
  Central API client and protocol orchestration.
- [config_flow.py](/custom_components/came_connect/config_flow.py)
  Integration setup and options flow.
- [cover.py](/custom_components/came_connect/cover.py)
  Gate cover entity.
- [button.py](/custom_components/came_connect/button.py)
  BPT/X1 door and AUX buttons.
- [sensor.py](/custom_components/came_connect/sensor.py)
  Status sensors.
- [binary_sensor.py](/custom_components/came_connect/binary_sensor.py)
  Connectivity and motion state.

## Gate Control Path

1. The integration authenticates against CAME Connect using OAuth.
2. It subscribes to realtime updates through the CAME websocket path.
3. Device state is mapped into Home Assistant entities.
4. Cover actions call the cloud API and rely on realtime updates to reflect the
   resulting state.

## BPT/X1 Path

1. BPT setup is optional and configured in the options flow.
2. The integration resolves the intercom slot and metadata from the authenticated
   CAME account path.
3. Button entities are created on a separate BPT/X1 child device.
4. Button presses send the validated cloud SIP/TLS command flow through
   [api.py](/custom_components/came_connect/api.py).

## Device Model

- The main Home Assistant device represents the CAME gate or automation.
- When BPT/X1 is enabled, a second child device is created for intercom actions.
- Gate entities stay on the gate device.
- Door and AUX buttons stay on the BPT/X1 device.

## Test Strategy

The public test suite is intentionally limited to commit-safe tests:

- parsing and discovery tests
- transport orchestration tests
- button behavior tests
- options flow tests

See [tests](/tests) for the current suite.

## Local-Only Boundary

The following stay out of the public repo surface:

- raw captures and system logs
- reverse-engineering probes and temporary tooling
- AI workflow files and planning state
- unsanitized protocol notes

Those artifacts live under `.local/` and are ignored by Git.
