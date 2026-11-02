"""Render development experiment results; no model selection is performed."""
import json
from pathlib import Path

ROOT=Path(__file__).parent
d=json.loads((ROOT/'experiment_results.json').read_text())
lines=['# Offline thermal candidate experiments', '',
'These are **development experiments**, not validated accuracy or active-control readiness. '
'The same three days have already been explored. Newly collected future data must be reserved '
'for independent validation; no candidate is selected here.', '',
'## Implemented candidates', '',
'- `production_rls`: the unchanged C++ Observer implementation in the compiled replay executable, '
'cold-started on an assumed five-minute UTC grid. This reproduces the production mathematics, '
'NOT the running device state or exact observation timestamps.',
'- `radiator_5`, `two_state_20`, `radiator_40`: bounded offline least-squares room-rate models with '
'separate room and normalized radiator heat states. The radiator state follows previous measured '
'heating proxy with a fixed 5/20/40-minute time constant. This is a lightweight two-state proxy, '
'not a calibrated radiator surface temperature or identified physical RC network.',
'- `trv_20`: adds TRV-local minus predicted room temperature. During a rollout TRV-local temperature '
'is held at its origin value, not replaced with future measurements. TRV is not heating power.',
'- `solar_proxy_20`: adds measured KNMI irradiance held at the origin. This is a scalar solar proxy, '
'not a historical weather forecast or orientation-corrected solar model.',
'- `wind_vent_20`: adds reported wind times outdoor-room difference and a ventilation demand proxy '
'(Low=0, Mid=.5, High=1, mean of three requests). Demand is not airflow. No airflow or energy claim.', '',
'`facade_projection` and a facade-feature candidate are implemented and tested with explicit solar '
'azimuth/elevation inputs and the user orientations 251.44°/71.44°. Historical directional scoring '
'is deferred: site coordinates or solar geometry are absent. No location, glazing, area or shading '
'was invented. Projection of global irradiance is only a geometric proxy, not direct-beam power.', '',
'## Protocol and assumptions', '',
'The first 24 hours beginning 2026-10-30 11:00 UTC supply one-step training targets. Candidate '
'coefficients are then frozen. The next 24 hours are development-validation; the following period '
'through Nov 2 11:00 UTC is development-later, **not untouched test data**. A 60-minute origin '
'embargo before each boundary prevents multi-horizon labels crossing a split. One-step training '
'labels must end before the training boundary. No random shuffling.', '',
'All forecasts use only values available at their grid origin. Future room values are labels only; '
'future CH/valve records are retrospective regime labels only. No future weather, TRV or PID decisions '
'are used as inputs. Forecasts are constant-drive thermal scenarios evaluated against PID-operated '
'outcomes, not forecasts of future PID decisions. No oracle-input conditional rollout is reported.', '',
'Held raw room outcomes/origins are capped at 900 seconds, supply at 900 seconds, outdoor/TRV/solar/wind '
'at 1800 seconds. These explicit exploratory bounds are not changes to the strict scorer. Inputs '
'must be valid at the origin and age diagnostics no older than 30 seconds, with strict valve/supply '
'ages <=60/900 seconds. Window-open and DHW origins are excluded. Binary/command/ventilation states '
'are event-held with explicit unknown/unavailable rejection. Continuous future interval health is '
'not certified; endpoint matches are bounded held observations, not physical measurements. '
'No interpolation or future backfill is used. Missing TRV/weather values are never zero-imputed.', '',
'The production reference adapts online to past measurements; candidate coefficients are frozen '
'after training. This is an explicit protocol difference, not a claim of equal identification '
'conditions. The cold start, assumed tick phase, incomplete suspension history and sparse inputs '
'prevent interpreting reference errors as the deployed device’s accuracy. Invalid replay rows '
'use valid=0 and ignored numeric placeholders, never fabricated learning observations.', '',
'Features use numeric scaling (temperature difference /10; irradiance /1000; wind × difference /100). '
'Unit metadata for KNMI wind/irradiance is not independently confirmed by the CSV. These are empirical '
'reported-unit experiments only: coefficient units and physical interpretation remain provisional. '
'Bounds and ridge .01 are predeclared, not tuned to later-period error. Limited excitation and '
'tiny training sets make coefficient identification uncertain.', '',
'## Coverage', '',
'The core cohort intersects every core candidate, production and persistence across all three '
'horizons. TRV has a separately reported intersection with production/persistence, restricted to '
'the core origins. This prevents missing Nick TRV from deleting all other Nick comparisons. '
'Never compare MAE across these different populations as a model advantage.', '']
for room,v in d['rooms'].items():
    lines.append(f"- {room}: counts `{v['counts']}`; training pairs `{v['training_samples']}`.")
lines += ['', '## Core cohort — both development periods', '',
'All errors °C; N identical within a room/period across core models and horizons. Full RMSE, bias, '
'p50/p95 and operating strata are in experiment_results.json.', '',
'| Room | Period | Horizon | Model | N | MAE | RMSE | Bias |',
'|---|---|---:|---|---:|---:|---:|---:|']
for room,v in d['rooms'].items():
    for k,m in v['metrics'].items():
        if k.startswith('trv_cohort'):continue
        period,h,model=k.split('/')
        lines.append(f"| {room} | {period} | {h} | {model} | {m['n']} | {m['mae']:.3f} | {m['rmse']:.3f} | {m['bias']:.3f} |")
lines+=['','## TRV cohort','','Nick has no common evaluated TRV origins under these bounds; '
'this is missing evidence, not a zero-error result. Stijn results:','',
'| Period | Horizon | Model | N | MAE | RMSE | Bias |','|---|---:|---|---:|---:|---:|---:|']
for k,m in d['rooms']['stijn']['metrics'].items():
    if not k.startswith('trv_cohort'):continue
    _,period,h,model=k.split('/')
    lines.append(f"| {period} | {h} | {model} | {m['n']} | {m['mae']:.3f} | {m['rmse']:.3f} | {m['bias']:.3f} |")
lines+=['','## Interpretation and next experiment','',
'Persistence remains a strong reference. Lower candidate error than this cold-start production '
'experiment is not evidence that the deployed learner should be replaced. The later-period '
'60-minute core comparison contains only 24 Stijn and 10 Nick origins; development-validation '
'contains only 6 and 8. Do not choose a radiator lag or an extra sensor based on these samples.', '',
'The machine-readable report includes warming, cooling, unchanged, stable CH on/off, CH changes, '
'valve changes, DHW and unknown-operation strata when populated. Some bins are empty or tiny; '
'absence means no estimate. Regime and temperature-change labels use future outcomes solely to '
'describe errors, not to inform predictions. Recorded stable commands do not imply stable delivered heat.', '',
'Next: preserve this candidate set/protocol, collect multiple weeks with cycle diagnostics, verify '
'weather units and solar geometry, then fit on a new training block and evaluate frozen candidates '
'on a separately held future block. Measure sensitivity to held-state assumptions and maintain '
'a common-origin cohort. Reject extras that do not improve repeatable future performance. '
'No active MPC or energy-saving claim follows from these experiments.', '',
'Reproduce: compile evaluation/replay.cpp; run experiment_run.py with histories (5),(6),(8), '
'--replay pointing to that executable and --output experiment_results.json; run experiment_report.py. '
'Only Python standard library is required. No runtime learner, thermostat or actuator code is used '
'by these candidate implementations.']
(ROOT/'EXPERIMENTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
