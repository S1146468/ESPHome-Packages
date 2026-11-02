"""Score recorded forecasts against HA held state; not fresh measurement accuracy.

The first export row is excluded because it may be a synthetic boundary state.
No interpolation, backward filling, or prediction-value forward filling is used.
"""
import bisect
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def score(errors):
    n = len(errors)
    if not n:
        return {"n": 0}
    absolute = sorted(map(abs, errors))
    return dict(n=n, mae=sum(absolute)/n, rmse=math.sqrt(sum(e*e for e in errors)/n),
                bias=sum(errors)/n, absolute_p50=absolute[int((n-1)*.5)],
                absolute_p95=absolute[int((n-1)*.95)])


def evaluate(path):
    events = defaultdict(list)
    with open(path, encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            t = datetime.fromisoformat(row['last_changed'].replace('Z', '+00:00')).timestamp()
            try:
                value = float(row['state'])
            except ValueError:
                value = float('nan')
            events[row['entity_id']].append((t, value))
    result = {}
    for room in ('stijn', 'nick'):
        entity = f'sensor.climate_{room}_temp'
        if entity not in events:
            raise ValueError(f'Missing explicitly mapped room sensor: {entity}')
        actual = sorted(events[entity])
        times = [x[0] for x in actual]
        def held(t):
            i = bisect.bisect_right(times, t)-1
            return actual[i][1] if i >= 0 and t <= times[-1] else float('nan')
        for horizon in (15, 30, 60):
            matches = [key for key in events if room in key and key.endswith(f'_forecast_{horizon}min')]
            if len(matches) != 1:
                raise ValueError(f'Ambiguous forecast entity: {matches}')
            errors, persistence = [], []
            for t, predicted in sorted(events[matches[0]])[1:]:
                current, future = held(t), held(t+horizon*60)
                if all(math.isfinite(x) for x in (current, future, predicted)):
                    errors.append(predicted-future)
                    persistence.append(current-future)
            result[f'{room}_{horizon}'] = dict(recorded=score(errors), persistence=score(persistence))
    return result


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(json.dumps(evaluate(sys.argv[1]), indent=2), encoding='utf-8')
