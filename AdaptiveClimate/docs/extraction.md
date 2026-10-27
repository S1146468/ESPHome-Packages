# Extraction scope and provenance

Source: `S1146468/ESPHome-Packages`, branch
`feature/adaptive-thermostat-observe`, commit
`5153b6287faedd810d105b53f71a0b489f0c22a0`.

Destination: `feature/adaptive-climate-standalone`, based on main commit
`023b5b63249228d61328a9ea107b183e5dc6f6a5`. Basing on main avoids bringing the copied
thermostat along. The source branch remains intact. The existing `Thermostat/`
directory, root `Thermostat.yaml`, and unrelated packages are unchanged.

## Extracted unchanged

All four files under `components/adaptive_climate` were copied without functional
changes: Python schema/code generation, C++ header, C++ implementation and the
header-only thermal model. `source_manifest.json` records SHA-256 hashes over UTF-8
text with normalized line endings; a regression test verifies preservation.
Dependencies are ESPHome core plus sensor, binary_sensor and text_sensor. There
is no mandatory API/Home Assistant, PID, climate-controller or OpenTherm dependency.

## Adapted

- `ObserveRoom.yaml` moved to the package root. All seven inputs and the observer
  ID/name are mandatory include variables; only the 15-minute timeout has a default.
  No IDs are derived from a room prefix or tied to the old thermostat.
- Relevant schema and C++ tests are retained. The thermostat-copy test was removed
  because no thermostat is copied. Runtime-preservation, real ESPHome package/ID
  validation and independent-room tests were added.
- Examples were replaced with generic single-room and two-room integrations that
  neither include nor define a controller. HA entity placeholders in the optional
  HA example are all configurable substitutions.
- A separate GitHub Actions workflow builds both ESP32/ESP-IDF examples using
  ESPHome 2026.10.0 and runs the schema/integration/C++ tests.

## Deliberately not extracted

The duplicated ClimatePID files, OpenTherm configuration, boiler output calculation,
full thermostat example, old workflow and room-specific historical CSV analyzer,
replay mapping and historical-data reports are not part of this independent package.
The original runtime's model safeguards and behaviour have not been weakened or
retuned. This extraction adds no controller, physical-device action or deployment.
