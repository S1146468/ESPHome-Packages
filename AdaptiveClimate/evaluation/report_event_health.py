"""Render the fixed sensitivity study without selecting a winning policy."""
import json
from pathlib import Path

ROOT=Path(__file__).parent
d=json.loads((ROOT/'event_health_results.json').read_text())
lines=['# Event-driven health reconstruction', '',
'The old 360-second rule incorrectly required event-only status text to act as a heartbeat. '
'The component publishes status only on changes; ages publish every ten seconds, including while learning is suspended. '
'This increment preserves the old strict scorer, and adds a separately labelled reconstructed held-state analysis. '
'It never refreshes a raw measurement timestamp from a cached status.', '',
'## Evidence and predefined policies', '',
'Strict physical-measurement/issue-time verified forecasts: **0**. '
'Accepted rows below are bounded held-state comparisons supported by recent diagnostics, not confirmed physical measurements. '
'The earlier unmasked change-time analysis remains exploratory.', '',
'Before calculating results, policies were fixed at raw hold limits of 30, 60, 300 and 900 seconds, '
'with maximum age-diagnostic receipt gaps of 30 seconds. A separate 300/60 policy tests transport-gap sensitivity. '
'Thirty seconds permits up to three nominal ten-second diagnostic intervals; 60 tests a larger logging gap. '
'Raw holds span near-event comparisons, the original 60-second rule, one observer interval and the configured '
'15-minute recent-publication threshold. These are uncertainty brackets, not tuned accuracy improvements. '
'No policy is selected on test performance.', '',
'Health checks use cached status as state, with independent live age evidence. Room/outdoor held_unconfirmed '
'is allowed exactly as in event-driven input policy. Valve and supply receipt ages, projected forward from '
'their last diagnostic publication, must remain <=60 and <=900 seconds. All four age streams must be finite, '
'nonnegative and within the diagnostic-gap limit. Uptime must have finite evidence within 360 seconds; '
'observed decreases reject crossing intervals. API-disconnected, unknown, invalid, expired or unexpected status '
'rejects. Raw unavailable states reject. Checks run at ten-second checkpoints and every raw/status change '
'and explicit invalid diagnostic/uptime/reset event. Thus short recorded faults are not hidden by grid sampling. '
'Unrecorded faults shorter than the permitted gap remain uncertain. No absence of an API-disconnected event '
'proves continuous connectivity; a disconnected device may be unable to publish that state.', '',
'Uptime uses the exported legacy diyless name; its mapping to this node remains user-verifiable. '
'Ages arriving at HA establish transport/observer liveness, not sensor acquisition or physical accuracy. '
'Near-simultaneous entities are not treated as an atomic snapshot. State transitions missing from Recorder '
'cannot be reconstructed. Identical age values suppressed by Recorder can conservatively cause exclusions.', '',
'## Timing association', '']
for room,v in d['timing'].items():
    lines.append(f"- {room}: {v['finite_publications']} finite 15-minute publications; {v['within_2s_of_300']}/{v['consecutive_gaps']} consecutive gaps within 2 seconds of 300 seconds; {v['training_counter_event_within_2s']} publications have a training-counter event within 2 seconds.")
lines += ['', 'This is a retrospective association, not a replacement timestamp or proof of an exact issue clock. '
'Counter events on either side are used ONLY for this timing audit, never as forecast features. '
'No forecast timestamps are rounded or shifted. Device issue time and network latency remain unknown.', '',
'## Quantitative sensitivity results', '',
'UTC splits remain Oct 30 11:00 / Oct 31 11:00 / Nov 1 11:00 / Nov 2 11:00, '
'with 60-minute boundary embargoes. No fitting or test-set policy selection. These dates have already been '
'explored; future candidate selection requires new untouched data. Original and persistence share origins '
'within each room/horizon/policy. Different policies do not share populations; score differences are NOT '
'causal improvements. Errors are event-weighted and autocorrelated. Zero N is missing evidence, not zero error.', '',
'Full split metrics, error percentiles, exclusive rejection counts and checkpoint reasons are in '
'`event_health_results.json`. Below: accepted/rejected across all splits; mean/max age combines origin and '
'outcome raw-state ages. Accuracy columns are TEST ONLY, Celsius.', '',
'| Room/min | Hold/gap s | Accepted/rejected | Mean/max age s | Test N | MAE | RMSE | Bias | Persistence MAE |',
'|---|---|---:|---:|---:|---:|---:|---:|---:|']
for key,v in d['policies'].items():
    room,h,p=key.split('/');n=v['counts'].get('accepted_held_state',0);m=v['metrics'].get('test/recorded',{});b=v['metrics'].get('test/persistence',{})
    age=v['raw_ages'];a=f"{age['mean']:.1f}/{age['max']:.1f}" if age['n'] else '—'
    fmt=lambda x: f'{x:.3f}' if x is not None else '—'
    lines.append(f"| {room}/{h} | {p} | {n}/{v['counts']['total']-n} | {a} | {m.get('n',0)} | {fmt(m.get('mae'))} | {fmt(m.get('rmse'))} | {fmt(m.get('bias'))} | {fmt(b.get('mae'))} |")
lines += ['', '## Operating-condition diagnosis', '',
'Below is the predefined 300/30 policy, not a winner. Regimes use realized future '
'CH/DHW/valve changes ONLY to label errors after scoring. They are not available-at-origin predictors. '
'Priority: unknown operation, DHW, CH transition, valve transition, stable CH on/off. '
'Stable means no recorded CH or valve changes; it does not imply constant supply temperature, physical '
'valve position or delivered heat. Binary states are event-held, not independently measured continuously. '
'No conditional oracle thermal rollout or future PID simulation was performed.', '',
'| Room/min | Test regime | N | Forecast bias | Forecast MAE | Persistence MAE |',
'|---|---|---:|---:|---:|---:|']
for key,v in d['policies'].items():
    if not key.endswith('hold300_gap30'):continue
    for k,m in v['regimes'].items():
        if not k.startswith('test/') or not k.endswith('/recorded'):continue
        b=v['regimes'][k.replace('/recorded','/persistence')]
        lines.append(f"| {'/'.join(key.split('/')[:2])} | {k.split('/')[1]} | {m['n']} | {m['bias']:.3f} | {m['mae']:.3f} | {b['mae']:.3f} |")
lines += ['', 'Negative bias in a stable recorded-input stratum weakens—but cannot eliminate—the explanation '
'that all error is caused by future valve changes. Unmeasured heat delivery, changing supply, initial '
'radiator state, coefficient estimation and timestamp uncertainty remain confounded. Small stratum counts '
'preclude causal attribution. No coefficient, lag or controller change is justified by this analysis.', '',
'## Minimal read-only collection improvement', '',
'`collect_states.py` uses only GET /api/states and logs selected existing entities in append-only JSONL '
'every ten seconds. Set HA_URL and HA_TOKEN in the local process environment; supply a JSON list of '
'entity IDs and an output file. Example: `python collect_states.py entities.json observations.jsonl --once`. '
'Omit --once for sustained collection. It preserves all HA timestamps and attributes verbatim, adds '
'request/receipt UTC and duration, records failures/missing entities and never treats repeated cached '
'values as new measurements. Credentials are neither printed nor saved. Keep outputs local.', '',
'Include both raw room sensors, all eight age diagnostics, both freshness and model-status entities, '
'training counters, all six forecasts, uptime, effective valve commands, actual CH/DHW/flame/supply, '
'window contacts and master climates (exact names in MAPPINGS.md). This reuses existing diagnostics; '
'no firmware change or duplicate HA sensors. REST snapshots may miss intermediate events; polling is '
'not a guaranteed event logger and cannot recover exact firmware issue times. If strict issue-time '
'validation is later required, a per-update sequence and device monotonic issue timestamp would need '
'a separately reviewed observer diagnostic. That firmware change is not included here.', '',
'`collection_entities.json` supplies the existing entity list. 27 tests passed locally, including '
'replay, event-health and read-only collection tests. The collector was tested with mocked HTTP responses, not connected to the user’s HA. '
'Endpoint reference: [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/).', '',
'Reproduce with event_health.py using histories (5), (6), (8); render with report_event_health.py. '
'No runtime component or thermostat files were changed.']
(ROOT/'EVENT_HEALTH.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
