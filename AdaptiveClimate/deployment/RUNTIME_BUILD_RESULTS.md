# Complete runtime-instrumented shadow candidate: build evidence

This is an ESP32-target compile, not a measurement on a physical ESP32. No
installation, flash access or device reset was performed. Dummy credentials are
used only inside the ignored validation directory; never install these binaries.

| Build | Link-time RAM | Flash |
|---|---:|---:|
| Supplied complete reference, previous verified build | 53,453 bytes | 802,528 bytes |
| `a96e05d` complete shadow candidate, previous verified build | 54,277 bytes | 810,456 bytes |
| Complete shadow + origin snapshots + optional runtime benchmarking | 54,733 bytes | 813,068 bytes |

Runtime preparation adds **456 RAM / 2,612 flash bytes** over `a96e05d`'s shadow
candidate. Total difference from the supplied complete reference is **1,280 RAM /
10,540 flash bytes**. Text entities and their buffers/callbacks also consume
runtime heap; link figures do not measure free heap or prove scheduling margins.
The new records will supply those measurements after approved installation.

Target: `esp32dev`, ESP-IDF **5.5.6**, ESPHome **2026.10.0**, Xtensa
**esp-14.2.0_20260121**; application partition 1,835,008 bytes. The board settings
include the user's rev3 minimum, SRAM1-as-IRAM setting and generic flash chip.
The `version: 5.5.6` pin explicitly preserves the version resolved by the pinned
ESPHome installation; no framework upgrade is introduced by this pin.

Passed:

* 63 ESPHome/schema/source tests, including optional probes, frozen learner hashes
  and a safety-comparison test that rejects changed PID/observer settings.
* Six C++ executables with assertions enabled: original thermal, shadow thermal,
  original input handling, atomic cycles, shadow integration and runtime/input
  records. The runtime test compares instrumented and uninstrumented original
  forecasts, traces, timestamps and shadow outputs, tests filtered heartbeat
  isolation, rollover and maximum-length clock/sequence records.
* All 36 existing offline evaluation tests using the compiled original replay.
* Expanded complete configuration comparison: all 15 control/board/network
  domains and both original observers equal; original and shadow learner headers
  match `a96e05d` exactly. No actuator interfaces were added to either model.
* Complete ESP32/ESP-IDF compile with optional runtime instrumentation enabled.

The first target build revealed a diagnostic printf type warning because this
Xtensa toolchain aliases `uint32_t` to unsigned long. Explicit unsigned casts
fixed it; the subsequent target build is clean. Host log stubs still emit the
existing benign unused TAG warning. Initial network-sandbox errors were resolved
with approved access to only the pinned dependencies. No model mathematics or
control source was modified to make a check pass.

The validation tool writes its checked source revision, dirty status, learner
digests, package pins and SHA-256 of each equal control domain to
`.build/shadow-install-validation/control_validation.json`. Keep this JSON,
compile logs and image/ELF/partition hashes with the final privately built image.
It separates a verified build from an unverified assumption about what is flashed.
The final delivery commit's Actions checks provide the independent Linux/GCC
status; do not infer that status from local build results.

Read-only preparation/verification commands:

```sh
python -m pip install -r AdaptiveClimate/requirements-test.txt
python AdaptiveClimate/deployment/validate_candidate.py
python -m pytest AdaptiveClimate/tests -q
# Run the six C++ test executables and the existing offline test suite.
esphome compile .build/shadow-install-validation/thermostaat_shadow.yaml
```

`validate_candidate.py` never changes the user's `secrets.yaml` and never invokes
upload/run commands. `SHADOW_INSTALLATION.md` contains the still-unmet current
image/rollback gate, exact entity mapping procedure and installation checklist.
