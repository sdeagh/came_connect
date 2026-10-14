# Changelog

All notable changes to this project will be documented here.

## Unreleased

### Fixed

- Retry the web MFA OAuth endpoint when the legacy auth-code endpoint returns
  `invalid_grant` / `invalid_request`, keeping PKCE and token exchange on the
  same OAuth path. Interactive second-factor prompts are not implemented.
- Allow complete manual BPT SIP settings without a mobile device token; skip
  push registration for this path and discover button labels and AUX actions
  through web `sites/admin` and `plants` metadata.
- Show the direct SIP metadata source in the BPT options preview.

### Documentation

- Document the PLX WiFi setup with user-validated AUX2 gate opening and the
  limits of that hardware validation.

## [1.2.0] - 2025-09-13

### Added

- WebSocket realtime updates; no periodic polling after startup.

### Changed

- Phase sensor now: Open/Closed/Opening/Closing/Stopped (capitalised).
- Simplified Options: only Redirect URI and WebSocket URL.

### Fixed

- Moving sensor now false for Stopped.

### Removed

- Poll interval / motion polling options and code paths.

## [1.1.0] - 2025-09-10

### Fixed

- Cover properties now properly associated with the device
