# Frozen independent validation protocol

This protocol is prepared before installation. No model, PID, OpenTherm or
forecast-gate tuning is part of the validation period. Both actual C++ learners
continue their normal causal online learning from past inputs; future scoring
targets must never be fed back as special training data or used to change code.

## Commissioning and period

After separately approved installation, first reserve 48 hours for checking
entities, Recorder retention, boot/sequence association, heat-input attribution,
heap, stack and timing. Do not use those hours to rank model accuracy. Fixing a
collection defect invalidates commissioning and requires a new start.

Before examining validation errors, save the approved firmware SHA-256,
repository commit, manifest, exact entity-ID mapping, timezone and the next
14-day UTC start/end timestamps. Start at the next UTC midnight after successful
commissioning. End exactly 14 days later; do not move the end to obtain favorable
scores. Preserve every day, including faults, missing targets and withheld
forecasts. If evidence is inadequate, report that outcome and register a new
future block after reporting this one. Keep Recorder raw state history for at
least 35 days, with database backups before purge can remove any of the block.

## Origins, boot identity and targets

1. Join each room's original cycle, input snapshot, original/shadow model details,
   shadow forecast and runtime record by device boot tag, `q` and integer device
   `t`. Scope old v1 cycle records to the boot tag of the matching input snapshot.
   Deduplicate repeated `(device,boot,room,q,t)` publications after reconnects.
   Sequence gaps, inconsistent records, future records, unknown boot association
   and suspended/invalid input states cannot be silently repaired by forward fill.
2. Use `i1`'s room value as the common prediction origin and persistence forecast.
   It is the exact raw value held by the ESP32 at that observation, not the EMA.
   Require usable input-state codes (recent or event-held as configured), API
   policy passed, valid numeric ranges, known CH/window/DHW flags, and no open
   window or active DHW at origin. Keep held-origin age as a separate stratum;
   do not silently redefine event-held as a fresh physical reading.
3. Primary origin time is the HA receipt/change timestamp of the original atomic
   cycle record. Device `t` is authoritative for ordering and five-minute gaps,
   not an independently synchronized UTC clock. Report receipt-time differences
   among matched records; exclude joins differing by more than 2 seconds from
   the strict timing cohort and report their count. Recorder-only data cannot
   establish exact sensor acquisition time or network latency. Never label this
   cohort "physically timestamp verified" without additional sensor evidence.
4. For each 15/30/60-minute horizon, choose the **first valid raw room state
   publication on or after origin UTC + horizon, no more than 60 seconds later**.
   Use the same target value/time for all three predictions. Never use an EMA,
   master-climate temperature attribute, interpolation, or a fabricated unchanged
   sample. Require source raw state in 0–45°C and known availability; preserve
   explicit unavailable spans. Report target delay distribution and exclusions.
   This change-only target cohort can overrepresent temperature changes and is
   not a random sample of all physical temperatures.
5. Separately report a predefined held-state sensitivity using the last valid raw
   state at/before each horizon, with age <=15 minutes and no intervening explicit
   unavailability. Label it event-held evidence. It cannot replace the primary
   cohort or be selected because it gives better errors. Report both origin and
   outcome ages and the absence of confirmed physical acquisition timestamps.

## Denominators and matched comparisons

Report separately for each room and horizon:

* All scheduled cycles, received cycles, valid input origins and target-matched
  origins, with mutually exclusive exclusion counts and reasons.
* Forecast availability = finite forecast / valid input origins, **before**
  conditioning on target presence. Report original and shadow separately,
  reason-specific shadow withholding and complete sequence delivery coverage.
* Target coverage = valid targets / valid input origins. Report original and
  shadow finite forecasts among target-matched origins as a second coverage rate.
* Primary common cohort = valid target + finite original + finite shadow. On
  exactly those origins calculate MAE, RMSE and signed bias for original, shadow
  and temperature persistence. Also retain common-all-three-horizons counts;
  horizon-specific cohorts need not contain the same origins.
* Additional original-versus-persistence and shadow-versus-persistence cohorts
  may use each learner's own availability, but their populations must be named
  and cannot be compared with each other as an algorithm improvement.

`null`, unknown, missing, unavailable, suspended and withheld forecasts are
**not successful predictions, zero errors, or persistence substitutes**. Exclude
them from error calculations and retain them in availability denominators.

Label realized operating conditions from recorded CH/DHW/valve histories only
after making predictions. Report stable CH off/on, CH transitions, valve-command
transitions, DHW interruptions and the first 30 minutes after DHW, plus warming,
cooling, unchanged and raw-publication-age bins. If more than one transition
occurs, retain multiple labels or state an explicit exclusive priority. Missing
operation history is an unknown stratum. These future labels are not forecast
features. Constant heating proxy forecasts do not predict future PID decisions.

Use paired per-origin errors and day-block bootstrap intervals (resample whole
UTC days, keeping all models and operating labels together; fixed seed 20261103,
2,000 replicates) for MAE differences and RMSE/bias where sample size permits.
Do not treat overlapping horizons as independent samples. With fewer than ten
represented days, intervals are descriptive and evidence is insufficient.

## Acceptance gates fixed before errors are inspected

These are proposed trial decision rules, not established physical safety limits.
Agree/freeze them with the validation start; changing them requires a later
independent block and disclosure of the original result.

**Commissioning:** no unexplained restart/watchdog, unchanged PID settings and
command path, no persistent API disconnect, no numerical learner reset, internal
minimum free heap >=32 KiB, largest internal free block >=16 KiB and loop-task
minimum free stack >=1 KiB. Require measured original work, individual shadow
feed handlers and three-horizon shadow rollout each <5 ms, and completed whole
observation update <20 ms. If a budget is exceeded, stop promotion and inspect
the timing scope and control scheduling; do not auto-disable heating or flash a
different image. Long loop/callback gaps can have causes other than the model.
The PID-input and water-target callbacks should follow their existing 5-second
cadence; gaps >5.25 seconds are counted and must be explained, particularly when
aligned to model updates. These probes cannot certify actual OpenTherm telegram
deadlines, PID end-to-end runtime or causation without a separate timing trace.

**Collection quality:** >=99% cycle delivery in each room while the device/HA are
expected online; every missing cycle must be accounted for. Keep all outages in
the report. At least 200/150/100 strict common origins at 15/30/60 minutes per
room, spread across >=10 validation days, and >=30 common origins in the combined
CH/valve/DHW transition strata per horizon. Below these counts report insufficient
evidence instead of a favorable accuracy claim.

**Forecast utility:** provisional minimum shadow availability of 70%/50%/20%
at 15/30/60 minutes on all valid origins. The previous development replay had
low 60-minute availability, so this gate may fail; do not loosen it after seeing
new data. Low coverage can justify further future development, never counting
withholding as accuracy success.

**Accuracy:** on each room's strict common cohort, shadow MAE must beat the
original at all horizons, must not exceed persistence MAE at 15 or 30 minutes,
and must improve persistence MAE by >=10% at 60 minutes, with the day-block 95%
interval for the paired MAE difference below zero. Require absolute shadow bias
<=0.1°C at 15/30 minutes and <=0.2°C at 60 minutes; inspect transition strata for
material degradation and require no MAE regression >0.1°C versus persistence
in adequately populated transition strata. RMSE, tails, availability and missing
target/health evidence must accompany these gates. Failure or insufficient
evidence is an outcome, not permission to retune this period or deploy MPC.

Passing only permits consideration of another read-only/shadow experiment. This
protocol grants no authority to change heating or enable active MPC.
