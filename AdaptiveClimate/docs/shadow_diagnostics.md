# Optional thermal model details and shadow forecasts

All entities are diagnostic/read-only and publish only on the existing
five-minute observation cycle, including suspended cycles. No flash persistence
or new high-frequency telemetry is added. Existing `cycle_record` v1 remains
unchanged; correlate records by boot, per-room `q` and device `t`.

```yaml
adaptive_climate:
  - id: !extend your_existing_observer_id
    model_record:
      name: Reference Model Details
    shadow_model: true
    shadow_record:
      name: Shadow Model Details
    shadow_forecasts:
      name: Shadow Conditional Forecasts
```

`model_record` does not enable the candidate. `shadow_model` defaults to false;
candidate record keys require explicit `shadow_model: true`. Use the local
component from this reviewed checkout or pin an approved commit, never `main`.
`examples/shadow_diagnostics.yaml` is a build-only observer fixture. The separate
complete deployment candidate preserves the supplied control pins/bindings and
uses the local observer, but does not establish the flashed control revision.

Model records use a compact versioned format under HA's 255-character limit:

```
m1|q|t|n|loss,gain,offset|change,predicted,residual,heat|consecutive,resets,saturation|learning_reason|last_reset_reason
```

Numbers have five significant digits. `null` represents unavailable/nonfinite
values. Change/predicted/residual are °C **over the most recent attempted learning
interval**, heat is that interval's mean normalized proxy, and coefficients use
the original physical units (minutes/Celsius). These are last-learning snapshots;
they are not necessarily a new learning attempt at the cycle timestamp. The
reference learns on polls; the shadow learns between cycles on publications.
Unchanged `n` and last-learning reason can persist. Suspension is recorded by
the cycle/forecast status. `resets` counts automatic coefficient/covariance
resets since boot; initialization is not a reset. The shadow's bounded uncertainty
restoration after six outliers does not increment this counter. Reset reason
persists until another reset. Rejection reasons are `rate`, `residual`, `invalid`,
`constraint` (candidate) and `numerical`. Saturation bits are 1=loss, 2=heating gain,
4=offset. Reference bits mean a clipped coefficient; shadow bits mean an entire
constrained step was rejected. Instrumentation does not change reference maths.

The separate forecast record is JSON:

```json
{"v":1,"q":100,"t":30000000,"s":"unidentified","l":"publication_pair","f":[null,null,null]}
```

`f` is 15/30/60 minutes from the current observation origin. `s` explains forecast
eligibility; `l` is the last publication-pair status. Possible states include
`suspended`, `held_origin`, `radiator_settling`, `recovering`, `constraint`,
`unidentified`, `uncertainty`, and `conditional_unvalidated`. `uncertainty` means
at least one horizon was withheld; inspect each array position. Non-null values
are still unvalidated conditional constant-proxy forecasts, not predictions of
future PID decisions. No nominal covariance width is a calibrated confidence
interval. Physical acquisition time remains unknown for HA state publications.

Records use bounded buffers and are not truncated. Regression tests exercise
large sequence/device clocks, missing forecasts, independent rooms and optional
instrumentation parity. If collection resumes after an availability interruption,
deduplicate `(boot,q,t)`; Recorder can republish the same atomic state.
