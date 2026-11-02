"""Strict offline scoring of normalized, provenance-checked forecast records.

JSON input: metadata, measurements, health, forecasts. See SCORING.md.
No interpolation, forecast holding, or future-input access is performed.
"""
import argparse
import bisect
from collections import Counter, defaultdict
from datetime import datetime
import json
import math
from pathlib import Path
from score_recorded import score


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('Timezone-aware timestamps required')
    return result.timestamp()


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


class Series:
    def __init__(self, rows):
        self.rows = sorted(rows, key=lambda r: timestamp(r['time']))
        self.times = [timestamp(r['time']) for r in self.rows]
        if len(set(self.times)) != len(self.times):
            raise ValueError('Duplicate timestamps must be reconciled explicitly')

    def at(self, time, maximum_age):
        index = bisect.bisect_right(self.times, time)-1
        if index < 0 or time-self.times[index] > maximum_age:
            return None
        row = self.rows[index]
        if row.get('boundary', False) or not row.get('available', False):
            return None
        return row

    def healthy_interval(self, start, end, maximum_age):
        if not all(self.at(t, maximum_age) for t in (start, end)):
            return False
        left = bisect.bisect_right(self.times, start)
        right = bisect.bisect_right(self.times, end)
        points = [self.times[left-1]] + self.times[left:right] + [end]
        return (all(b-a <= maximum_age for a, b in zip(points, points[1:])) and
                all(self.at(t, maximum_age) for t in self.times[left:right]))


def partition(origin, start, train_end, validation_end, end, embargo=3600):
    # Purge the maximum forecast horizon before BOTH split boundaries.
    if start <= origin and origin+embargo < train_end:
        return 'train'
    if train_end <= origin and origin+embargo < validation_end:
        return 'validation'
    if validation_end <= origin and origin+embargo <= end:
        return 'test'
    return None


def evaluate(data, measurement_age=60, health_age=360, grid_seconds=300):
    meta = data['metadata']
    required = ('raw_temperature_mapping_verified', 'forecast_issue_times_verified',
                'measurement_publication_times_verified', 'units_verified')
    blockers = [key for key in required if meta.get(key) is not True]
    blockers.extend('missing_entity:' + key for key in data.get('missing_entities', []))
    if blockers:
        return {'status': 'blocked', 'missing_provenance': blockers, 'scores': {}}
    if meta.get('temperature_unit') != 'degC':
        raise ValueError('Explicit degC normalization required')
    if not (0 < measurement_age <= 300 and health_age > 0 and grid_seconds > 0):
        raise ValueError('Invalid age/grid policy')
    limits = [timestamp(meta[key]) for key in ('start', 'train_end', 'validation_end', 'end')]
    if limits != sorted(set(limits)):
        raise ValueError('Split boundaries must be strictly increasing')
    models = meta['models']
    if not models or len(set(models)) != len(models) or 'persistence' in models:
        raise ValueError('Explicit unique candidate model names required')
    measurements = {room: Series([r for r in data['measurements'] if r['room'] == room])
                    for room in ('stijn', 'nick')}
    health = {room: Series([r for r in data['health'] if r['room'] == room])
              for room in ('stijn', 'nick')}
    groups = defaultdict(dict)
    for row in data['forecasts']:
        if row['room'] not in measurements or row['model'] not in models or row['horizon'] not in (15, 30, 60):
            raise ValueError('Unknown room, model or horizon')
        origin = timestamp(row['time'])
        key = (row['model'], row['horizon'])
        group = groups[(row['room'], origin)]
        if key in group:
            raise ValueError('Duplicate forecast origin/model/horizon')
        group[key] = row
    errors, grid_errors = defaultdict(list), defaultdict(list)
    used_bins, rejected, accepted = set(), Counter(), []
    for (room, origin), group in sorted(groups.items()):
        split = partition(origin, *limits)
        if split is None:
            rejected['outside_split_or_embargo'] += 1
            continue
        if any((model, h) not in group for model in models for h in (15, 30, 60)):
            rejected['incomplete_common_origin'] += 1
            continue
        if any(r.get('boundary', False) or not finite(r['value']) for r in group.values()):
            rejected['invalid_or_boundary_forecast'] += 1
            continue
        source = measurements[room]
        actuals = [source.at(origin + h*60, measurement_age) for h in (0, 15, 30, 60)]
        if any(r is None or not finite(r['value']) or not 0 <= r['value'] <= 45 for r in actuals):
            rejected['missing_invalid_or_old_raw_measurement'] += 1
            continue
        if not health[room].healthy_interval(origin, origin+3600, health_age):
            rejected['unconfirmed_health_interval'] += 1
            continue
        bin_key = (room, split, int((origin-limits[0])//grid_seconds))
        grid = bin_key not in used_bins
        used_bins.add(bin_key)
        accepted.append({'room': room, 'time': origin, 'split': split, 'grid_selected': grid,
                         'measurement_ages_seconds': [origin+h*60-timestamp(r['time'])
                             for h, r in zip((0, 15, 30, 60), actuals)]})
        for h, actual in zip((15, 30, 60), actuals[1:]):
            predictions = {model: group[(model, h)]['value'] for model in models}
            predictions['persistence'] = actuals[0]['value']
            for model, predicted in predictions.items():
                key = f'{room}/{split}/{h}/{model}'
                errors[key].append(predicted-actual['value'])
                if grid:
                    grid_errors[key].append(predicted-actual['value'])
    return dict(status='scored', policy=dict(measurement_age=measurement_age, health_age=health_age,
                grid_seconds=grid_seconds, embargo_seconds=3600), rejected=dict(rejected),
                accepted=accepted, event_weighted={k: score(v) for k, v in errors.items()},
                grid_sampled={k: score(v) for k, v in grid_errors.items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(evaluate(json.loads(args.input.read_text())), indent=2), encoding='utf-8')
