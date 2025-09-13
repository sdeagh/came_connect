# Changelog

All notable changes to this project will be documented here.

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
