# Offline thermal candidate experiments

These are **development experiments**, not validated accuracy or active-control readiness. The same three days have already been explored. Newly collected future data must be reserved for independent validation; no candidate is selected here.

## Implemented candidates

- `production_rls`: the unchanged C++ Observer implementation in the compiled replay executable, cold-started on an assumed five-minute UTC grid. This reproduces the production mathematics, NOT the running device state or exact observation timestamps.
- `radiator_5`, `two_state_20`, `radiator_40`: bounded offline least-squares room-rate models with separate room and normalized radiator heat states. The radiator state follows previous measured heating proxy with a fixed 5/20/40-minute time constant. This is a lightweight two-state proxy, not a calibrated radiator surface temperature or identified physical RC network.
- `trv_20`: adds TRV-local minus predicted room temperature. During a rollout TRV-local temperature is held at its origin value, not replaced with future measurements. TRV is not heating power.
- `solar_proxy_20`: adds measured KNMI irradiance held at the origin. This is a scalar solar proxy, not a historical weather forecast or orientation-corrected solar model.
- `wind_vent_20`: adds reported wind times outdoor-room difference and a ventilation demand proxy (Low=0, Mid=.5, High=1, mean of three requests). Demand is not airflow. No airflow or energy claim.

`facade_projection` and a facade-feature candidate are implemented and tested with explicit solar azimuth/elevation inputs and the user orientations 251.44°/71.44°. Historical directional scoring is deferred: site coordinates or solar geometry are absent. No location, glazing, area or shading was invented. Projection of global irradiance is only a geometric proxy, not direct-beam power.

## Protocol and assumptions

The first 24 hours beginning 2026-10-30 11:00 UTC supply one-step training targets. Candidate coefficients are then frozen. The next 24 hours are development-validation; the following period through Nov 2 11:00 UTC is development-later, **not untouched test data**. A 60-minute origin embargo before each boundary prevents multi-horizon labels crossing a split. One-step training labels must end before the training boundary. No random shuffling.

All forecasts use only values available at their grid origin. Future room values are labels only; future CH/valve records are retrospective regime labels only. No future weather, TRV or PID decisions are used as inputs. Forecasts are constant-drive thermal scenarios evaluated against PID-operated outcomes, not forecasts of future PID decisions. No oracle-input conditional rollout is reported.

Held raw room outcomes/origins are capped at 900 seconds, supply at 900 seconds, outdoor/TRV/solar/wind at 1800 seconds. These explicit exploratory bounds are not changes to the strict scorer. Inputs must be valid at the origin and age diagnostics no older than 30 seconds, with strict valve/supply ages <=60/900 seconds. Window-open and DHW origins are excluded. Binary/command/ventilation states are event-held with explicit unknown/unavailable rejection. Continuous future interval health is not certified; endpoint matches are bounded held observations, not physical measurements. No interpolation or future backfill is used. Missing TRV/weather values are never zero-imputed.

The production reference adapts online to past measurements; candidate coefficients are frozen after training. This is an explicit protocol difference, not a claim of equal identification conditions. The cold start, assumed tick phase, incomplete suspension history and sparse inputs prevent interpreting reference errors as the deployed device’s accuracy. Invalid replay rows use valid=0 and ignored numeric placeholders, never fabricated learning observations.

Features use numeric scaling (temperature difference /10; irradiance /1000; wind × difference /100). Unit metadata for KNMI wind/irradiance is not independently confirmed by the CSV. These are empirical reported-unit experiments only: coefficient units and physical interpretation remain provisional. Bounds and ridge .01 are predeclared, not tuned to later-period error. Limited excitation and tiny training sets make coefficient identification uncertain.

## Coverage

The core cohort intersects every core candidate, production and persistence across all three horizons. TRV has a separately reported intersection with production/persistence, restricted to the core origins. This prevents missing Nick TRV from deleting all other Nick comparisons. Never compare MAE across these different populations as a model advantage.

- stijn: counts `{'candidate_origins': 553, 'common_model_unavailable': 35, 'invalid_origin_or_optional_input': 350, 'missing_bounded_outcome': 106, 'accepted_common_all_horizons': 30, 'core_optional_input_missing_or_untrained': 32}`; training pairs `{'radiator_5': 72, 'two_state_20': 72, 'radiator_40': 72, 'trv_20': 63, 'solar_proxy_20': 30, 'wind_vent_20': 42}`.
- nick: counts `{'candidate_origins': 553, 'missing_bounded_outcome': 109, 'accepted_common_all_horizons': 18, 'invalid_origin_or_optional_input': 401, 'core_optional_input_missing_or_untrained': 16, 'common_model_unavailable': 9}`; training pairs `{'radiator_5': 71, 'two_state_20': 71, 'radiator_40': 71, 'trv_20': 41, 'solar_proxy_20': 23, 'wind_vent_20': 30}`.

## Core cohort — both development periods

All errors °C; N identical within a room/period across core models and horizons. Full RMSE, bias, p50/p95 and operating strata are in experiment_results.json.

| Room | Period | Horizon | Model | N | MAE | RMSE | Bias |
|---|---|---:|---|---:|---:|---:|---:|
| stijn | development_validation | 15 | radiator_5 | 6 | 0.109 | 0.142 | 0.014 |
| stijn | development_validation | 30 | radiator_5 | 6 | 0.233 | 0.287 | -0.005 |
| stijn | development_validation | 60 | radiator_5 | 6 | 0.667 | 0.788 | -0.310 |
| stijn | development_validation | 15 | two_state_20 | 6 | 0.117 | 0.144 | 0.026 |
| stijn | development_validation | 30 | two_state_20 | 6 | 0.233 | 0.287 | 0.019 |
| stijn | development_validation | 60 | two_state_20 | 6 | 0.667 | 0.771 | -0.262 |
| stijn | development_validation | 15 | radiator_40 | 6 | 0.121 | 0.145 | 0.031 |
| stijn | development_validation | 30 | radiator_40 | 6 | 0.233 | 0.288 | 0.029 |
| stijn | development_validation | 60 | radiator_40 | 6 | 0.667 | 0.765 | -0.243 |
| stijn | development_validation | 15 | solar_proxy_20 | 6 | 0.153 | 0.158 | 0.087 |
| stijn | development_validation | 30 | solar_proxy_20 | 6 | 0.271 | 0.297 | 0.139 |
| stijn | development_validation | 60 | solar_proxy_20 | 6 | 0.606 | 0.671 | -0.035 |
| stijn | development_validation | 15 | wind_vent_20 | 6 | 0.262 | 0.303 | 0.262 |
| stijn | development_validation | 30 | wind_vent_20 | 6 | 0.492 | 0.557 | 0.492 |
| stijn | development_validation | 60 | wind_vent_20 | 6 | 0.689 | 0.761 | 0.689 |
| stijn | development_validation | 15 | production_rls | 6 | 1.022 | 1.208 | -1.022 |
| stijn | development_validation | 30 | production_rls | 6 | 1.971 | 2.262 | -1.971 |
| stijn | development_validation | 60 | production_rls | 6 | 3.878 | 4.183 | -3.878 |
| stijn | development_validation | 15 | persistence | 6 | 0.100 | 0.141 | 0.000 |
| stijn | development_validation | 30 | persistence | 6 | 0.233 | 0.289 | -0.033 |
| stijn | development_validation | 60 | persistence | 6 | 0.667 | 0.812 | -0.367 |
| stijn | development_later | 15 | radiator_5 | 24 | 0.111 | 0.127 | 0.082 |
| stijn | development_later | 30 | radiator_5 | 24 | 0.200 | 0.217 | 0.100 |
| stijn | development_later | 60 | radiator_5 | 24 | 0.318 | 0.377 | 0.145 |
| stijn | development_later | 15 | two_state_20 | 24 | 0.121 | 0.136 | 0.095 |
| stijn | development_later | 30 | two_state_20 | 24 | 0.211 | 0.230 | 0.126 |
| stijn | development_later | 60 | two_state_20 | 24 | 0.353 | 0.401 | 0.196 |
| stijn | development_later | 15 | radiator_40 | 24 | 0.124 | 0.139 | 0.100 |
| stijn | development_later | 30 | radiator_40 | 24 | 0.215 | 0.236 | 0.136 |
| stijn | development_later | 60 | radiator_40 | 24 | 0.369 | 0.412 | 0.216 |
| stijn | development_later | 15 | solar_proxy_20 | 24 | 0.169 | 0.186 | 0.164 |
| stijn | development_later | 30 | solar_proxy_20 | 24 | 0.290 | 0.319 | 0.254 |
| stijn | development_later | 60 | solar_proxy_20 | 24 | 0.512 | 0.546 | 0.425 |
| stijn | development_later | 15 | wind_vent_20 | 24 | 0.432 | 0.490 | 0.432 |
| stijn | development_later | 30 | wind_vent_20 | 24 | 0.833 | 0.940 | 0.801 |
| stijn | development_later | 60 | wind_vent_20 | 24 | 1.641 | 1.855 | 1.552 |
| stijn | development_later | 15 | production_rls | 24 | 0.567 | 0.813 | -0.567 |
| stijn | development_later | 30 | production_rls | 24 | 1.128 | 1.551 | -1.128 |
| stijn | development_later | 60 | production_rls | 24 | 2.085 | 2.671 | -2.085 |
| stijn | development_later | 15 | persistence | 24 | 0.100 | 0.119 | 0.067 |
| stijn | development_later | 30 | persistence | 24 | 0.188 | 0.205 | 0.071 |
| stijn | development_later | 60 | persistence | 24 | 0.279 | 0.359 | 0.088 |
| nick | development_validation | 15 | radiator_5 | 8 | 0.243 | 0.284 | 0.019 |
| nick | development_validation | 30 | radiator_5 | 8 | 0.358 | 0.410 | 0.260 |
| nick | development_validation | 60 | radiator_5 | 8 | 0.508 | 0.563 | 0.506 |
| nick | development_validation | 15 | two_state_20 | 8 | 0.240 | 0.293 | -0.050 |
| nick | development_validation | 30 | two_state_20 | 8 | 0.304 | 0.343 | 0.124 |
| nick | development_validation | 60 | two_state_20 | 8 | 0.270 | 0.323 | 0.248 |
| nick | development_validation | 15 | radiator_40 | 8 | 0.239 | 0.298 | -0.069 |
| nick | development_validation | 30 | radiator_40 | 8 | 0.291 | 0.333 | 0.086 |
| nick | development_validation | 60 | radiator_40 | 8 | 0.226 | 0.264 | 0.173 |
| nick | development_validation | 15 | solar_proxy_20 | 8 | 0.237 | 0.301 | -0.077 |
| nick | development_validation | 30 | solar_proxy_20 | 8 | 0.293 | 0.332 | 0.071 |
| nick | development_validation | 60 | solar_proxy_20 | 8 | 0.209 | 0.239 | 0.141 |
| nick | development_validation | 15 | wind_vent_20 | 8 | 0.230 | 0.312 | -0.110 |
| nick | development_validation | 30 | wind_vent_20 | 8 | 0.285 | 0.330 | 0.006 |
| nick | development_validation | 60 | wind_vent_20 | 8 | 0.158 | 0.204 | 0.017 |
| nick | development_validation | 15 | production_rls | 8 | 1.830 | 1.855 | -1.830 |
| nick | development_validation | 30 | production_rls | 8 | 2.974 | 3.003 | -2.974 |
| nick | development_validation | 60 | production_rls | 8 | 4.550 | 4.589 | -4.550 |
| nick | development_validation | 15 | persistence | 8 | 0.238 | 0.298 | -0.062 |
| nick | development_validation | 30 | persistence | 8 | 0.300 | 0.339 | 0.100 |
| nick | development_validation | 60 | persistence | 8 | 0.225 | 0.278 | 0.200 |
| nick | development_later | 15 | radiator_5 | 10 | 0.141 | 0.149 | 0.124 |
| nick | development_later | 30 | radiator_5 | 10 | 0.262 | 0.285 | 0.262 |
| nick | development_later | 60 | radiator_5 | 10 | 0.491 | 0.507 | 0.491 |
| nick | development_later | 15 | two_state_20 | 10 | 0.062 | 0.079 | 0.015 |
| nick | development_later | 30 | two_state_20 | 10 | 0.093 | 0.114 | 0.049 |
| nick | development_later | 60 | two_state_20 | 10 | 0.132 | 0.145 | 0.086 |
| nick | development_later | 15 | radiator_40 | 10 | 0.044 | 0.078 | -0.015 |
| nick | development_later | 30 | radiator_40 | 10 | 0.067 | 0.101 | -0.009 |
| nick | development_later | 60 | radiator_40 | 10 | 0.081 | 0.118 | -0.029 |
| nick | development_later | 15 | solar_proxy_20 | 10 | 0.051 | 0.082 | -0.034 |
| nick | development_later | 30 | solar_proxy_20 | 10 | 0.082 | 0.109 | -0.048 |
| nick | development_later | 60 | solar_proxy_20 | 10 | 0.114 | 0.154 | -0.106 |
| nick | development_later | 15 | wind_vent_20 | 10 | 0.086 | 0.105 | 0.032 |
| nick | development_later | 30 | wind_vent_20 | 10 | 0.139 | 0.158 | 0.085 |
| nick | development_later | 60 | wind_vent_20 | 10 | 0.193 | 0.223 | 0.158 |
| nick | development_later | 15 | production_rls | 10 | 1.411 | 1.417 | -1.411 |
| nick | development_later | 30 | production_rls | 10 | 2.438 | 2.445 | -2.438 |
| nick | development_later | 60 | production_rls | 10 | 3.787 | 3.794 | -3.787 |
| nick | development_later | 15 | persistence | 10 | 0.040 | 0.077 | -0.020 |
| nick | development_later | 30 | persistence | 10 | 0.060 | 0.100 | -0.020 |
| nick | development_later | 60 | persistence | 10 | 0.070 | 0.122 | -0.050 |

## TRV cohort

Nick has no common evaluated TRV origins under these bounds; this is missing evidence, not a zero-error result. Stijn results:

| Period | Horizon | Model | N | MAE | RMSE | Bias |
|---|---:|---|---:|---:|---:|---:|
| development_validation | 15 | trv_20 | 3 | 0.074 | 0.075 | 0.074 |
| development_validation | 30 | trv_20 | 3 | 0.149 | 0.150 | 0.149 |
| development_validation | 60 | trv_20 | 3 | 0.200 | 0.201 | 0.200 |
| development_validation | 15 | production_rls | 3 | 1.526 | 1.622 | -1.526 |
| development_validation | 30 | production_rls | 3 | 2.842 | 2.996 | -2.842 |
| development_validation | 60 | production_rls | 3 | 5.068 | 5.258 | -5.068 |
| development_validation | 15 | persistence | 3 | 0.100 | 0.100 | 0.100 |
| development_validation | 30 | persistence | 3 | 0.200 | 0.200 | 0.200 |
| development_validation | 60 | persistence | 3 | 0.300 | 0.300 | 0.300 |
| development_later | 15 | trv_20 | 19 | 0.133 | 0.153 | 0.102 |
| development_later | 30 | trv_20 | 19 | 0.220 | 0.250 | 0.123 |
| development_later | 60 | trv_20 | 19 | 0.385 | 0.436 | 0.188 |
| development_later | 15 | production_rls | 19 | 0.642 | 0.902 | -0.642 |
| development_later | 30 | production_rls | 19 | 1.280 | 1.720 | -1.280 |
| development_later | 60 | production_rls | 19 | 2.341 | 2.946 | -2.341 |
| development_later | 15 | persistence | 19 | 0.105 | 0.126 | 0.063 |
| development_later | 30 | persistence | 19 | 0.195 | 0.214 | 0.047 |
| development_later | 60 | persistence | 19 | 0.284 | 0.380 | 0.042 |

## Interpretation and next experiment

Persistence remains a strong reference. Lower candidate error than this cold-start production experiment is not evidence that the deployed learner should be replaced. The later-period 60-minute core comparison contains only 24 Stijn and 10 Nick origins; development-validation contains only 6 and 8. Do not choose a radiator lag or an extra sensor based on these samples.

The machine-readable report includes warming, cooling, unchanged, stable CH on/off, CH changes, valve changes, DHW and unknown-operation strata when populated. Some bins are empty or tiny; absence means no estimate. Regime and temperature-change labels use future outcomes solely to describe errors, not to inform predictions. Recorded stable commands do not imply stable delivered heat.

Next: preserve this candidate set/protocol, collect multiple weeks with cycle diagnostics, verify weather units and solar geometry, then fit on a new training block and evaluate frozen candidates on a separately held future block. Measure sensitivity to held-state assumptions and maintain a common-origin cohort. Reject extras that do not improve repeatable future performance. No active MPC or energy-saving claim follows from these experiments.

Reproduce: compile evaluation/replay.cpp; run experiment_run.py with histories (5),(6),(8), --replay pointing to that executable and --output experiment_results.json; run experiment_report.py. Only Python standard library is required. No runtime learner, thermostat or actuator code is used by these candidate implementations.
