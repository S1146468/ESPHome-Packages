"""Merge original HA event exports and audit bounded, change-time comparisons.

These diagnostics do not certify issue-time or continuous-health provenance.
No interpolation or resampling. All attributes and source timestamps retained.
"""
import argparse
import bisect
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
from validated_scoring import timestamp, partition, Series
from score_recorded import score


def merge(paths):
    events = defaultdict(dict)
    provenance = []
    duplicates = conflicts = 0
    for path in paths:
        with path.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        boundary = min(timestamp(r['last_changed']) for r in rows)
        provenance.append(dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), rows=len(rows)))
        for row in rows:
            t = timestamp(row['last_changed'])
            entity = row['entity_id']
            cleaned = {k: v for k, v in row.items() if v not in ('', None)}
            if t in events[entity]:
                previous = events[entity][t]
                if previous['record'] != cleaned:
                    conflicts += 1
                    previous['conflict'] = True
                else:
                    duplicates += 1
                previous['sources'].append(path.name)
                previous['boundary'] = previous['boundary'] and t == boundary
            else:
                events[entity][t] = dict(record=cleaned, sources=[path.name], boundary=t == boundary, conflict=False)
    return {k: sorted(v.items()) for k, v in events.items()}, provenance, duplicates, conflicts


def numeric(row):
    try:
        value = float(row['record']['state'])
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


class History:
    def __init__(self, rows):
        self.rows = rows
        self.times = [t for t, _ in rows]

    def at(self, t, max_age):
        i = bisect.bisect_right(self.times, t)-1
        if i < 0 or t-self.times[i] > max_age:
            return None
        row = self.rows[i][1]
        if row['boundary'] or row['conflict']:
            return None
        return row


def analyze(events):
    result = {}
    limits = list(map(timestamp, ['2026-10-30T11:00:00Z', '2026-10-31T11:00:00Z',
                                  '2026-11-01T11:00:00Z', '2026-11-02T11:00:00Z']))
    for room in ('stijn', 'nick'):
        raw = History(events[f'sensor.temp_sensor_kamer_{room}_temperature'])
        prefix = 'sensor.server_thermostaat_stijn_' if room == 'stijn' else 'sensor.kamer_nick_adaptive_climate_nick_nick_'
        status = History(events[prefix+'model_status'])
        health_key = f'sensor.kamer_{room}_adaptive_climate_{room}_{room}_input_freshness_status'
        health = Series([dict(time=r['record']['last_changed'], boundary=r['boundary'],
            available=not r['conflict'] and r['record']['state'] ==
                'room=recent_publication; outdoor=recent_publication; valve=recent_publication; supply=recent_publication')
            for _, r in events[health_key]])
        for horizon in (15, 30, 60):
            counts = Counter()
            errors = defaultdict(lambda: defaultdict(list))
            for t, forecast in events[prefix+f'forecast_{horizon}min']:
                counts['total_forecast_events'] += 1
                split = partition(t, *limits)
                if split is None:
                    counts['outside_split_or_60min_embargo'] += 1
                    continue
                if forecast['boundary'] or forecast['conflict'] or numeric(forecast) is None:
                    counts['invalid_boundary_or_conflicting_forecast'] += 1
                    continue
                current = raw.at(t, 60)
                if current is None or numeric(current) is None or not 0 <= numeric(current) <= 45:
                    counts['origin_raw_missing_invalid_or_over_60s'] += 1
                    continue
                future = raw.at(t+horizon*60, 60)
                if future is None or numeric(future) is None or not 0 <= numeric(future) <= 45:
                    counts['outcome_raw_missing_invalid_or_over_60s'] += 1
                    continue
                counts['bounded_raw_pairs'] += 1
                if health.healthy_interval(t, t+3600, 360):
                    counts['bounded_pairs_confirmed_360s_health'] += 1
                else:
                    counts['bounded_pairs_unconfirmed_360s_health'] += 1
                for model, value in [('recorded', numeric(forecast)), ('persistence', numeric(current))]:
                    errors[split][model].append(value-numeric(future))
                state = status.at(t, 360)
                if state is None or state['record']['state'] not in ('learning_unvalidated', 'low_excitation'):
                    counts['bounded_pairs_without_recent_ready_status'] += 1
                else:
                    counts['bounded_pairs_with_recent_ready_status'] += 1
                # Status text is NOT proof of continuous sensor/connection health.
            result[f'{room}_{horizon}'] = dict(counts=dict(counts),
                change_time_diagnostic={split: {m: score(e) for m, e in models.items()} for split, models in errors.items()},
                strict_verified_scores={}, strict_blocker='Issue times and continuous health not established by change history')
    return result


def run(paths, output):
    events, sources, duplicates, conflicts = merge(paths)
    output.mkdir(parents=True, exist_ok=True)
    # Local-only merged history: never commit raw household histories.
    with (output/'merged.jsonl').open('w', encoding='utf-8') as f:
        for entity, rows in sorted(events.items()):
            for t, row in rows:
                f.write(json.dumps(dict(entity=entity, timestamp=t, **row))+'\n')
    summary = {}
    for entity, rows in events.items():
        gaps = sorted(b[0]-a[0] for a, b in zip(rows, rows[1:]))
        summary[entity] = dict(rows=len(rows), start=rows[0][1]['record']['last_changed'],
            end=rows[-1][1]['record']['last_changed'], median_change_gap_s=gaps[len(gaps)//2] if gaps else None,
            max_change_gap_s=max(gaps) if gaps else None,
            unavailable=sum(r['record']['state'] in ('unknown', 'unavailable') for _, r in rows),
            conflicts=sum(r['conflict'] for _, r in rows))
    age_audit = {}
    for room in ('stijn', 'nick'):
        raw = History(events[f'sensor.temp_sensor_kamer_{room}_temperature'])
        age_key = f'sensor.kamer_{room}_adaptive_climate_{room}_{room}_room_temperature_input_age'
        differences, reset_times, previous_age = [], [], None
        for t, row in events[age_key]:
            age = numeric(row)
            if age is None or age < 0 or row['boundary'] or row['conflict']:
                previous_age = None
                continue
            held = raw.at(t, float('inf'))
            if held is not None and numeric(held) is not None:
                # Only past raw events are used. Difference is not acquisition latency.
                differences.append(abs((t-age)-timestamp(held['record']['last_changed'])))
            if previous_age is not None and age < previous_age:
                reset_times.append(t)
            previous_age = age
        ordered = sorted(differences)
        age_audit[room] = dict(comparisons=len(ordered), age_decreases=len(reset_times),
            receipt_vs_last_raw_change_abs_median_s=ordered[len(ordered)//2] if ordered else None,
            receipt_vs_last_raw_change_abs_p95_s=ordered[int((len(ordered)-1)*.95)] if ordered else None,
            agreement_within_2s=sum(x <= 2 for x in ordered))
    report = dict(sources=sources, duplicates=duplicates, conflicts=conflicts, inventory=summary,
                  receipt_age_audit=age_audit, results=analyze(events))
    (output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run(args.files, args.output)
