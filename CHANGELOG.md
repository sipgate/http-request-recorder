# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-05-29

### Added/Changed

- Library now pins and hashes versions when developing locally (#10706a5)
- Library now uses `pyproject.toml` instead of `setup.py` (#e266c6b)

## [2.1.2] - 2026-05-21

### Fixed

- use non-vulnerable aiohttp (#54f9ce8)

## [2.1.1] - 2026-05-21

superseeded by 2.1.2, where actual fix is located

## [2.1.0] - 2025-08-26

### Added

- added top-level export for `RecordedRequest` (#2c0c29f).

### Changed

- deprecated `expect_json_rpc(...)`, `expect_xml_rpc(...)` matchers (#bf4468f)

## [2.0.0] - 2025-04-14

### Added

- `expect_json_rpc(...)` helper (#474589d).

### Changed

- `expect_xml_rpc(...)` now only accepts method name (#d6b50d8).

[2.2.0]: https://github.com/sipgate/http-request-recorder/compare/v2.1.2...v2.2.0
[2.1.2]: https://github.com/sipgate/http-request-recorder/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/sipgate/http-request-recorder/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/sipgate/http-request-recorder/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/sipgate/http-request-recorder/releases/tag/v2.0.0

