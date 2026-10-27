# Validation

## Per-input freshness — 2026-10-27

Source commit `7c751f77fae6917c49a6cf78e3b136f5dec0365e` passed
[GitHub Actions run 40564081205](https://github.com/S1146468/ESPHome-Packages/actions/runs/40564081205).
All **52 Python tests**, the unchanged **C++ numerical tests**, and the new
**C++ input-handling tests** passed locally and on Linux CI. All four firmware
builds compiled and linked successfully with **ESPHome 2026.10.0, ESP32 esp32dev,
ESP-IDF**:

| Example | Reported image size | Reported static RAM |
| --- | ---: | ---: |
| Single room, no API | 197,087 bytes | 22,636 bytes |
| Generic two-room HA observer | 741,527 bytes | 46,212 bytes |
| Original Stijn-only thermostat fixture | 813,311 bytes | 52,988 bytes |
| Stijn + Nick thermostat fixture, explicit freshness policies | 814,447 bytes | 53,964 bytes |

The input tests compile the actual wrapper implementation with controlled-clock
ESPHome test doubles. They cover a stable hour, mixed strict/held inputs, immediate
raw updates, invalid/NaN/out-of-range readings, startup without data, strict expiry,
independent rooms, health/API guards, window/DHW, filtered heartbeat exclusion,
long-uptime age tracking and raw valve scaling. Python tests verify upstream
ESPHome raw/heartbeat/HA conversion contracts, real configuration/code generation,
all 24 diagnostic assignments, and unchanged PID/OpenTherm configuration.

The complete `thermal_model.h`, existing numerical tests, `Thermostat/` and root
`Thermostat.yaml` have no diff from `4982bcb`. The extraction manifest is preserved
as historical provenance; the wrapper/schema now intentionally differ from it.

These are complete fixture sizes, not incremental costs or runtime heap results.
The final validation-record commit changes documentation only. No firmware was
deployed, no live HA device registry was changed, and physical sensor reporting or
availability was not tested. See [the exact integration changes and limitations](freshness.md).

## Sub-device change — 2026-10-27

Source commit `5c0a6070a5c3efb2ac1ecba2c8e8afffe02806ec` passed
[GitHub Actions run 40484375248](https://github.com/S1146468/ESPHome-Packages/actions/runs/40484375248).
All **32 Python tests**, including real ESPHome configuration validation, and the
unchanged **C++ numerical tests** passed locally and in CI. All three firmware
builds compiled and linked with **ESPHome 2026.10.0, ESP32 esp32dev, ESP-IDF**:

| Example | Reported image size | Reported static RAM |
| --- | ---: | ---: |
| Single room | 194,995 bytes | 22,284 bytes |
| Two independent rooms | 738,911 bytes | 45,508 bytes |
| Stijn with existing PID/OpenTherm packages | 811,319 bytes | 52,588 bytes |

These are complete example sizes, not incremental costs or runtime heap measurements.
The Stijn fixture is compile-only, with placeholder controller settings; use
[the merge snippet](../examples/stijn_integration.yaml) for your working thermostat.

Tests verify all six numeric outputs and the status text sensor have the intended
device ID, valid unique IDs/names, metadata and declared room areas. They reject
missing device/area references, check all seven generated native C++ device
assignments, and compare the original PID/OpenTherm configuration with and without
the observer. The original Thermostat files, all four component source files and
the numerical tests have no changes from reviewed commit `c9b98da`.

Only this validation record was added after the successful run. No firmware was
deployed and no live Home Assistant registry migration was tested. Follow the
[migration verification instructions](subdevices.md#identity-and-home-assistant-migration)
to check entity IDs, history and area assignment after installation. Native
sub-device grouping changes the device-aware integration unique ID; retaining
entity registry entries depends on Home Assistant's migration handling.

## Original standalone extraction (historical results)

Verified build target: ESPHome 2026.10.0, ESP32 `esp32dev`, ESP-IDF, with no PSRAM
configuration. Both extracted examples compiled and linked successfully in
[GitHub Actions run 40476020667](https://github.com/S1146468/ESPHome-Packages/actions/runs/40476020667)
on 2026-10-27, for source commit `c2a961c26b4cefb459af360d76313834966b5c4d`.

All **23 Python schema/integration tests** and the desktop **C++ model tests** passed
both locally and on the Linux CI runner. The single-room build has no Home
Assistant, PID or OpenTherm components. The two-room build uses read-only HA
imports and contains no heating controller or actuator actions.

| Example | Reported image size | App partition use | Reported static RAM |
| --- | ---: | ---: | ---: |
| Single room, no networking | 194,587 bytes | 10.6% of 1,835,008 bytes | 22,188 bytes |
| Two rooms, Wi-Fi/encrypted API/HA | 737,183 bytes | 40.2% of 1,835,008 bytes | 45,348 bytes |

The build summary image sizes exclude any additional binary padding. These are
complete example sizes, not incremental observer costs. Static RAM is not free
heap. No runtime memory, largest-allocation or device loop-latency claim follows
from these build measurements. On the Linux host, ThermalModel was 68 bytes and
Observer was 92 bytes; the microbenchmark measured 0.22288 microseconds mean per
learn plus 60-minute forecast. Those are host results, not ESP32 runtime results.

The final validation-record update changes documentation only; the code and
examples remain exactly those tested by the linked run. The original `Thermostat/`
directory and root `Thermostat.yaml` have no diff from the base main revision.

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
been deployed. Physical-input availability and real-room prediction validation
remain necessary before considering any use beyond observation.
