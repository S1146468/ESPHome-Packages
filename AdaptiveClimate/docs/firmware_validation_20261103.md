# Firmware and regression validation — 3 November 2026

Build-only results. No device was contacted or flashed. Public dummy credentials
from `deployment/secrets.compile-only.yaml` were used for complete-device builds;
these images must not be installed. All builds use ESPHome 2026.10.0,
esp32dev, ESP-IDF 5.5.6 and Xtensa esp-14.2.0_20260121.

| Firmware | Link RAM bytes | Flash bytes |
|---|---:|---:|
| Frozen `4725022` single-room cycle fixture | 22,700 | 197,691 |
| Single-room shadow + reference/candidate details + shadow forecasts | 23,108 | 205,179 |
| Unchanged complete supplied thermostat, pinned remote observer | 53,453 | 802,528 |
| Complete two-room shadow candidate + six optional text diagnostics | 54,277 | 810,456 |

Single-room delta: **408 RAM / 7,488 flash bytes**. Complete two-room delta:
**824 RAM / 7,928 flash bytes**. These include instrumentation and entities,
not just numerical learner cost. ESPHome reports 180,736 bytes available for
its RAM percentage and a 1,835,008-byte application partition. This is static
link evidence, not a measurement of available runtime heap or MPC headroom.
The original complete YAML and all thermostat package pins remain unchanged.

The complete shadow YAML's expanded `climate`, `opentherm`, `output`, `switch`,
`sensor`, `binary_sensor`, `button`, `script`, `interval`, `globals`, `wifi`,
`api`, `esp32` and `ota` domains were compared against the supplied complete
reference and are equal. The differences are the local observer component,
shadow settings and optional diagnostic text entities. The original complete
candidate's existing unknown-flashed-revision limitation still applies.

Xtensa object symbols independently measure these object sizes:

| Object | Bytes |
|---|---:|
| Frozen ThermalModel / Observer | 68 / 92 |
| Instrumented ThermalModel / Observer | 104 / 128 |
| ShadowModel / ShadowObserver | 132 / 208 |

No numerical update allocates dynamic storage. Callback registration and text
entities add bounded allocations through ESPHome. Actual two-room update time,
worst stack usage, minimum free heap, fragmentation and watchdog latency have
not been measured because hardware execution was not authorized or available.
No ESP32-P4 requirement has been demonstrated.

Passed host checks:

* 58 pytest tests: typed ESPHome bindings/config generation, input-policy and
  source-contract checks, unchanged control domains, opt-in candidate schema.
* Five C++ executables with assertions explicitly enabled: original thermal
  learner, original input handling, original atomic cycles, shadow learner and
  shadow component integration. Tests include 20,000 paired reference numerical
  updates, >one simulated year, real-source sensor callback contracts, CH/DHW
  residual heat, invalid/numerical recovery and bounded 64-bit records.
* All 36 existing offline unittest cases, using a compiled actual reference
  replay executable. Both C++ replay programs compiled successfully.
* Focused November 3 cycle audit and chronological C++ reference/candidate
  comparisons on all supplied development exports. No EMA scoring targets.
* `git diff --check`.

Host compiler: Zig 0.15.2's C++ frontend, C++17, `-O2 -UNDEBUG -Wall -Wextra
-pedantic`. The existing CI also runs GCC C++17. Host stubs produce one benign
unused `TAG` warning because their log macros discard arguments. Test assertions
are explicitly enabled: an initial compiler-default NDEBUG build was discarded
and rerun with `-UNDEBUG` before accepting any results.

Resolved validation failures are retained here for transparency:

* The machine initially had ESPHome 2025.3.0 and no host C++ compiler. An isolated
  workspace environment installed the repository pins and Zig; the global
  ESPHome installation was not upgraded.
* Initial fixture builds lacked cache access/download permissions and then the
  pinned ESPHome tool-path discovery additionally required RISC-V and dfu-util
  tools. Approved build-tool downloads resolved these environment failures.
  No project source or ESPHome package was patched to bypass them.
* Source-contract tests initially assumed no binary flag callbacks and no trace
  instrumentation. They now distinguish raw numeric callbacks from binary flag
  callbacks and verify the frozen original by digest plus executable parity.
* ESPHome does not support the attempted `!override` wrapper tag. It was removed;
  the final separate full candidate was generated from the preserved supplied
  YAML and checked for equal expanded control domains.

Current test/build checks pass. GitHub CI status belongs to the pushed commit;
consult its Actions checks rather than interpreting these local results as an
already completed remote CI run.

Reproduction:

```sh
pip install -r AdaptiveClimate/requirements-test.txt
python -m pytest AdaptiveClimate/tests -q
g++ -std=c++17 -O2 AdaptiveClimate/tests/test_thermal_model.cpp -o thermal-tests
g++ -std=c++17 -O2 AdaptiveClimate/tests/test_shadow_model.cpp -o shadow-tests
g++ -std=c++17 -O2 -DUSE_API -IAdaptiveClimate/tests/stubs AdaptiveClimate/tests/test_shadow_component.cpp AdaptiveClimate/components/adaptive_climate/adaptive_climate.cpp -o shadow-component-tests
g++ -std=c++17 -O2 AdaptiveClimate/evaluation/replay.cpp -o replay
g++ -std=c++17 -O2 AdaptiveClimate/evaluation/shadow_replay.cpp -o shadow-replay
# Run the compiled executables; set ADAPTIVE_REPLAY_EXE to the absolute replay path.
python -m unittest discover -s AdaptiveClimate/evaluation -p 'test_*.py'
esphome compile AdaptiveClimate/examples/shadow_diagnostics.yaml
# Supply only compile-only credentials, then compile; do not upload:
esphome compile AdaptiveClimate/deployment/thermostaat_shadow.yaml
```

The frozen single-room comparison was built from a `git archive` of `4725022`.
This avoids substituting another algorithm as the reference.
