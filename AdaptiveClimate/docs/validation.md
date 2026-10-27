# Standalone validation

Compatibility target: ESPHome 2026.10.0, ESP32 `esp32dev`, ESP-IDF, no PSRAM required
by the numerical model. The source component was previously compiled in this
environment, but the extracted examples must pass their own build checks.

The test suite covers:

- Observe-only schema, required inputs and timeout bounds.
- Actual ESPHome YAML package expansion and ID/type resolution for one/two rooms.
- Rejection of missing inputs, unknown IDs, wrong sensor types and duplicate model IDs.
- Absence of heating-control configuration in the standalone examples.
- Source-manifest verification of all four unchanged runtime/schema files.
- Numerical convergence, invalid inputs, stale timestamps and clock rollover,
  window/DHW interruption, timing gaps, disturbance rejection and model reset.
- Independent room models, diagnostic forecast bounds and suspension.

The tests do not prove physical sensor freshness, closed-loop control benefit,
runtime ESP32 heap margin or predictive accuracy in a real room. No firmware has
been deployed. Build results for this extraction will be recorded after CI completes.
