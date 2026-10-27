# Standalone validation

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
