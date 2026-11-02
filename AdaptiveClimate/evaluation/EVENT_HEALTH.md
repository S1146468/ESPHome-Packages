# Event-driven health reconstruction

The old 360-second rule incorrectly required event-only status text to act as a heartbeat. The component publishes status only on changes; ages publish every ten seconds, including while learning is suspended. This increment preserves the old strict scorer, and adds a separately labelled reconstructed held-state analysis. It never refreshes a raw measurement timestamp from a cached status.

## Evidence and predefined policies

Strict physical-measurement/issue-time verified forecasts: **0**. Accepted rows below are bounded held-state comparisons supported by recent diagnostics, not confirmed physical measurements. The earlier unmasked change-time analysis remains exploratory.

Before calculating results, policies were fixed at raw hold limits of 30, 60, 300 and 900 seconds, with maximum age-diagnostic receipt gaps of 30 seconds. A separate 300/60 policy tests transport-gap sensitivity. Thirty seconds permits up to three nominal ten-second diagnostic intervals; 60 tests a larger logging gap. Raw holds span near-event comparisons, the original 60-second rule, one observer interval and the configured 15-minute recent-publication threshold. These are uncertainty brackets, not tuned accuracy improvements. No policy is selected on test performance.

Health checks use cached status as state, with independent live age evidence. Room/outdoor held_unconfirmed is allowed exactly as in event-driven input policy. Valve and supply receipt ages, projected forward from their last diagnostic publication, must remain <=60 and <=900 seconds. All four age streams must be finite, nonnegative and within the diagnostic-gap limit. Uptime must have finite evidence within 360 seconds; observed decreases reject crossing intervals. API-disconnected, unknown, invalid, expired or unexpected status rejects. Raw unavailable states reject. Checks run at ten-second checkpoints and every raw/status change and explicit invalid diagnostic/uptime/reset event. Thus short recorded faults are not hidden by grid sampling. Unrecorded faults shorter than the permitted gap remain uncertain. No absence of an API-disconnected event proves continuous connectivity; a disconnected device may be unable to publish that state.

Uptime uses the exported legacy diyless name; its mapping to this node remains user-verifiable. Ages arriving at HA establish transport/observer liveness, not sensor acquisition or physical accuracy. Near-simultaneous entities are not treated as an atomic snapshot. State transitions missing from Recorder cannot be reconstructed. Identical age values suppressed by Recorder can conservatively cause exclusions.

## Timing association

- stijn: 713 finite 15-minute publications; 670/712 consecutive gaps within 2 seconds of 300 seconds; 713 publications have a training-counter event within 2 seconds.
- nick: 824 finite 15-minute publications; 812/823 consecutive gaps within 2 seconds of 300 seconds; 824 publications have a training-counter event within 2 seconds.

This is a retrospective association, not a replacement timestamp or proof of an exact issue clock. Counter events on either side are used ONLY for this timing audit, never as forecast features. No forecast timestamps are rounded or shifted. Device issue time and network latency remain unknown.

## Quantitative sensitivity results

UTC splits remain Oct 30 11:00 / Oct 31 11:00 / Nov 1 11:00 / Nov 2 11:00, with 60-minute boundary embargoes. No fitting or test-set policy selection. These dates have already been explored; future candidate selection requires new untouched data. Original and persistence share origins within each room/horizon/policy. Different policies do not share populations; score differences are NOT causal improvements. Errors are event-weighted and autocorrelated. Zero N is missing evidence, not zero error.

Full split metrics, error percentiles, exclusive rejection counts and checkpoint reasons are in `event_health_results.json`. Below: accepted/rejected across all splits; mean/max age combines origin and outcome raw-state ages. Accuracy columns are TEST ONLY, Celsius.

| Room/min | Hold/gap s | Accepted/rejected | Mean/max age s | Test N | MAE | RMSE | Bias | Persistence MAE |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| stijn/15 | hold30_gap30 | 6/735 | 15.7/28.7 | 3 | 0.187 | 0.199 | -0.187 | 0.100 |
| stijn/30 | hold30_gap30 | 6/735 | 13.3/29.7 | 3 | 0.523 | 0.526 | -0.523 | 0.133 |
| stijn/60 | hold30_gap30 | 3/738 | 14.3/23.2 | 2 | 1.159 | 1.160 | -1.159 | 0.100 |
| stijn/15 | hold60_gap30 | 11/730 | 23.1/59.9 | 6 | 0.223 | 0.237 | -0.223 | 0.083 |
| stijn/30 | hold60_gap30 | 6/735 | 13.3/29.7 | 3 | 0.523 | 0.526 | -0.523 | 0.133 |
| stijn/60 | hold60_gap30 | 4/737 | 17.8/49.8 | 3 | 1.148 | 1.150 | -1.148 | 0.167 |
| stijn/15 | hold300_gap30 | 59/682 | 106.7/282.6 | 21 | 0.302 | 0.335 | -0.183 | 0.133 |
| stijn/30 | hold300_gap30 | 28/713 | 101.7/298.6 | 11 | 0.579 | 0.590 | -0.579 | 0.173 |
| stijn/60 | hold300_gap30 | 6/735 | 48.5/233.4 | 5 | 1.195 | 1.198 | -1.195 | 0.120 |
| stijn/15 | hold900_gap30 | 155/586 | 261.0/898.8 | 55 | 0.283 | 0.307 | -0.237 | 0.100 |
| stijn/30 | hold900_gap30 | 82/659 | 299.4/898.8 | 37 | 0.587 | 0.597 | -0.587 | 0.146 |
| stijn/60 | hold900_gap30 | 25/716 | 294.6/898.8 | 19 | 1.268 | 1.345 | -0.945 | 0.205 |
| stijn/15 | hold300_gap60 | 91/650 | 105.2/282.6 | 30 | 0.322 | 0.371 | -0.140 | 0.170 |
| stijn/30 | hold300_gap60 | 75/666 | 103.0/298.6 | 21 | 0.736 | 0.831 | -0.284 | 0.238 |
| stijn/60 | hold300_gap60 | 40/701 | 100.0/277.4 | 15 | 1.639 | 1.871 | -0.326 | 0.140 |
| nick/15 | hold30_gap30 | 8/830 | 16.8/28.2 | 4 | 0.138 | 0.160 | -0.138 | 0.075 |
| nick/30 | hold30_gap30 | 2/836 | 18.2/26.4 | 2 | 0.416 | 0.426 | -0.416 | 0.100 |
| nick/60 | hold30_gap30 | 0/838 | — | 0 | — | — | — | — |
| nick/15 | hold60_gap30 | 15/823 | 23.3/57.5 | 7 | 0.121 | 0.141 | -0.121 | 0.071 |
| nick/30 | hold60_gap30 | 5/833 | 28.2/54.4 | 5 | 0.314 | 0.348 | -0.290 | 0.160 |
| nick/60 | hold60_gap30 | 1/837 | 33.0/48.5 | 1 | 0.915 | 0.915 | -0.915 | 0.300 |
| nick/15 | hold300_gap30 | 70/768 | 96.8/288.7 | 18 | 0.118 | 0.133 | -0.110 | 0.061 |
| nick/30 | hold300_gap30 | 36/802 | 113.5/278.5 | 15 | 0.289 | 0.330 | -0.282 | 0.140 |
| nick/60 | hold300_gap30 | 6/832 | 110.3/263.9 | 4 | 0.681 | 0.770 | -0.681 | 0.350 |
| nick/15 | hold900_gap30 | 139/699 | 231.9/884.2 | 49 | 0.129 | 0.147 | -0.114 | 0.071 |
| nick/30 | hold900_gap30 | 69/769 | 237.1/875.5 | 30 | 0.252 | 0.304 | -0.244 | 0.163 |
| nick/60 | hold900_gap30 | 18/820 | 336.6/875.3 | 12 | 0.586 | 0.692 | -0.586 | 0.350 |
| nick/15 | hold300_gap60 | 103/735 | 96.7/289.2 | 25 | 0.121 | 0.137 | -0.115 | 0.060 |
| nick/30 | hold300_gap60 | 65/773 | 110.3/292.7 | 20 | 0.259 | 0.301 | -0.253 | 0.140 |
| nick/60 | hold300_gap60 | 35/803 | 107.4/288.7 | 10 | 0.462 | 0.572 | -0.455 | 0.360 |

## Operating-condition diagnosis

Below is the predefined 300/30 policy, not a winner. Regimes use realized future CH/DHW/valve changes ONLY to label errors after scoring. They are not available-at-origin predictors. Priority: unknown operation, DHW, CH transition, valve transition, stable CH on/off. Stable means no recorded CH or valve changes; it does not imply constant supply temperature, physical valve position or delivered heat. Binary states are event-held, not independently measured continuously. No conditional oracle thermal rollout or future PID simulation was performed.

| Room/min | Test regime | N | Forecast bias | Forecast MAE | Persistence MAE |
|---|---|---:|---:|---:|---:|
| stijn/15 | ch_transition | 7 | -0.173 | 0.389 | 0.200 |
| stijn/15 | stable_ch_off | 10 | -0.250 | 0.250 | 0.060 |
| stijn/15 | dhw_interval | 3 | -0.210 | 0.210 | 0.100 |
| stijn/15 | valve_transition | 1 | 0.501 | 0.501 | 0.500 |
| stijn/30 | stable_ch_off | 7 | -0.514 | 0.514 | 0.143 |
| stijn/30 | ch_transition | 4 | -0.693 | 0.693 | 0.225 |
| stijn/60 | ch_transition | 1 | -1.127 | 1.127 | 0.300 |
| stijn/60 | stable_ch_off | 1 | -1.095 | 1.095 | 0.200 |
| stijn/60 | dhw_interval | 3 | -1.251 | 1.251 | 0.033 |
| nick/15 | stable_ch_off | 15 | -0.126 | 0.130 | 0.047 |
| nick/15 | ch_transition | 3 | -0.033 | 0.056 | 0.133 |
| nick/30 | stable_ch_off | 12 | -0.332 | 0.332 | 0.108 |
| nick/30 | ch_transition | 3 | -0.079 | 0.118 | 0.267 |
| nick/60 | stable_ch_off | 2 | -0.910 | 0.910 | 0.300 |
| nick/60 | dhw_interval | 1 | -0.844 | 0.844 | 0.200 |
| nick/60 | ch_transition | 1 | -0.059 | 0.059 | 0.600 |

Negative bias in a stable recorded-input stratum weakens—but cannot eliminate—the explanation that all error is caused by future valve changes. Unmeasured heat delivery, changing supply, initial radiator state, coefficient estimation and timestamp uncertainty remain confounded. Small stratum counts preclude causal attribution. No coefficient, lag or controller change is justified by this analysis.

## Minimal read-only collection improvement

`collect_states.py` uses only GET /api/states and logs selected existing entities in append-only JSONL every ten seconds. Set HA_URL and HA_TOKEN in the local process environment; supply a JSON list of entity IDs and an output file. Example: `python collect_states.py entities.json observations.jsonl --once`. Omit --once for sustained collection. It preserves all HA timestamps and attributes verbatim, adds request/receipt UTC and duration, records failures/missing entities and never treats repeated cached values as new measurements. Credentials are neither printed nor saved. Keep outputs local.

Include both raw room sensors, all eight age diagnostics, both freshness and model-status entities, training counters, all six forecasts, uptime, effective valve commands, actual CH/DHW/flame/supply, window contacts and master climates (exact names in MAPPINGS.md). This reuses existing diagnostics; no firmware change or duplicate HA sensors. REST snapshots may miss intermediate events; polling is not a guaranteed event logger and cannot recover exact firmware issue times. If strict issue-time validation is later required, a per-update sequence and device monotonic issue timestamp would need a separately reviewed observer diagnostic. That firmware change is not included here.

`collection_entities.json` supplies the existing entity list. 27 tests passed locally, including replay, event-health and read-only collection tests. The collector was tested with mocked HTTP responses, not connected to the user’s HA. Endpoint reference: [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/).

Reproduce with event_health.py using histories (5), (6), (8); render with report_event_health.py. No runtime component or thermostat files were changed.
