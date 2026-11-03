# Complete thermostat diagnostic candidate

Current preparation: [shadow installation checklist and source/rollback evidence](SHADOW_INSTALLATION.md),
[runtime build results](RUNTIME_BUILD_RESULTS.md), [Recorder fragment](recorder_shadow_example.yaml)
and [independent validation protocol](VALIDATION_PROTOCOL.md). Both learners remain
frozen to a96e05d; this step adds only optional input/runtime records. The user has
now supplied a current YAML explicitly pinning the controls to 7d925a7; the actual
running image and its rollback binary are still not independently verified.

The separate `thermostaat_shadow.yaml` pins the reviewed observer/runtime source at
`e8411b9814bc7b7d8333be3c37ea188188d8ca93` and
enables both experimental shadow models plus compact model diagnostics. It
preserves the complete candidate's thermostat package pin and control domains.
It does not establish equivalence to the actually flashed control revision.
See [November 3 findings and deployment gate](../docs/thermal_fix_20261103.md)
and [build evidence](../docs/firmware_validation_20261103.md). Neither configuration
has been uploaded by this development increment.

thermostaat.yaml is the complete supplied real configuration, with only three
source-ref replacements and the two optional cycle_record entries appended.
PID gains, limits, timing, GPIO21/22 OpenTherm pins, firmware options, sensor
bindings, window/DHW logic and secret references are preserved.

Pins:
- Adaptive component and observer: a7c299c4684b3cf7405bf04f37d721a3fba3eac8.
- Thermostat packages: 7d925a7eccb6747a0ce5dbbcc0007c6fdf1bafc0.

The thermostat pin is a deliberately selected, inspected revision, NOT a recovered
flashed revision. It includes 5% heat-output rounding (68a8220) and the outdoor
EMA change from 6h to 1h (7d925a7). If the flashed firmware predates either,
installing this candidate changes those controls. Other differences against an
unknown flashed revision cannot be enumerated. Deployment remains blocked until
this is understood and a known-working rollback image is available.

## Build versus install

The complete candidate passes ESPHome 2026.10.0 configuration validation. CI
compiles this exact complete YAML with secrets.compile-only.yaml copied to the
ignored secrets.yaml path. These are public dummy credentials and documentation
IP addresses. The generated image is build evidence only: NEVER install it.
The first validation attempt rejected an all-zero dummy API key; the committed
nonzero placeholder fixes that test-environment issue, not any user setting.

To prepare your own candidate, back up /config/esphome/thermostaat.yaml and the
known-working firmware binary. Replace the YAML with this complete candidate,
retain your existing secrets.yaml, and compile only using ESPHome 2026.10.0.
Do not install until the control-package difference/rollback decision is approved.
No upload/run command is part of this repository workflow.

## After a separately approved installation

Find text entities named Stijn Observation Cycle and Nick Observation Cycle on
the respective Adaptive Climate subdevices. HA assigns their exact entity IDs;
copy these from the entity registry into the collector list rather than guessing.
Records contain v (schema), q (per-room/per-boot cycle), t (device milliseconds),
o/r (learning outcome/reason), n (samples), f (15/30/60-minute forecasts).
Expect one record per scheduled five-minute update, including suspended cycles;
null forecasts are normal during warm-up/invalid conditions. Check sequence gaps,
monotonic timestamps, input ages and API availability with the existing collector.

## Rollback

Restore the saved known-working firmware image and its configuration/secrets.
Merely removing cycle_record and rebuilding a YAML referencing main is NOT a
reproducible rollback. Reverting the observer pin to 533b3d7 removes instrumentation,
but does not establish the historical thermostat-package revision. Preserve
package caches/build logs; do not overwrite the only known-working image.

Runtime heap, latency and actual ESP32 performance remain unmeasured. CI link
RAM/flash figures are static build results, not runtime headroom. ESP32-P4 is not
selected by this change. The eventual learner/MPC remains intended to run locally.
