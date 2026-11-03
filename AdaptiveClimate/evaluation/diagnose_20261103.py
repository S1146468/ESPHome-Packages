"""Focused cycle audit. Does not treat EMA temperatures as raw measurements."""
import argparse
import bisect
import csv
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo


def analyze(path):
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    events = defaultdict(list)
    for row in rows:
        t = datetime.fromisoformat(row["last_changed"].replace("Z", "+00:00")).timestamp()
        events[row["entity_id"]].append((t, row["state"]))
    start = min(t for series in events.values() for t, _ in series)
    report = dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  rows=len(rows), entities=len(events), rooms={}, raw_room_histories_present={
                      room: f"sensor.temp_sensor_kamer_{room}_temperature" in events for room in ("stijn", "nick")})
    for room in ("stijn", "nick"):
        key = next(k for k in events if room in k and k.endswith("_observation_cycle"))
        cycles, seen, duplicates, invalid = [], set(), 0, 0
        boundary = None
        for t, state in events[key]:
            try:
                record = json.loads(state)
            except (ValueError, TypeError):
                invalid += 1
                continue
            if t == start:
                boundary = (t, record)
                continue
            identity = record["q"], record["t"]
            if identity in seen:
                duplicates += 1
                continue
            seen.add(identity)
            cycles.append((t, record))
        ages = sorted(events[next(k for k in events if room in k and k.endswith("_room_temperature_input_age"))])
        times = [t for t, _ in ages]
        resets, age_counts, held_rejections = [], Counter(), []
        previous = boundary
        for t, c in cycles:
            i = bisect.bisect_right(times, t) - 1
            age = None
            if i >= 0 and t - times[i] <= 30:
                try:
                    age = float(ages[i][1]) + t - times[i]
                except ValueError:
                    pass
            age_counts[f"{c['o']}/" + ("unknown" if age is None else ("held_over_15min" if age > 900 else "recent"))] += 1
            if previous:
                pt, p = previous
                if c["n"] < p["n"]:
                    resets.append(dict(local_time=datetime.fromtimestamp(t, ZoneInfo("Europe/Amsterdam")).isoformat(),
                                       q=c["q"], before=p["n"], after=c["n"], reason=c["r"],
                                       previous_is_export_boundary=pt == start))
                # An age greater than the complete preceding device interval,
                # with a 30s margin for diagnostic receipt/rounding, proves no
                # raw room publication in that interval. Thus dT=0, not a rate
                # disturbance. Numeric failure cannot yield this status here.
                if c["o"] == "rejected" and c["q"] == p["q"] + 1 and age is not None and age > (c["t"] - p["t"])/1000 + 30:
                    held_rejections.append(c["q"])
            previous = t, c
        entry = dict(unique_cycles=len(cycles), duplicate_publications=duplicates, invalid_states=invalid,
                     outcomes=dict(Counter(c["o"] for _, c in cycles)),
                     statuses=dict(Counter(c["r"] for _, c in cycles)),
                     forecast_cycles=sum(all(v is not None for v in c["f"]) for _, c in cycles),
                     resets=resets, age_counts=dict(age_counts),
                     proven_zero_change_residual_rejection_cycles=held_rejections)
        if room == "nick":
            t, c = next((t, c) for t, c in reversed(cycles) if all(v is not None for v in c["f"]))
            f15, f30, f60 = c["f"]
            # For zero drive after suspension, the fixed lag state is also zero.
            # f60-f30 = (f30-f15)*(k+k^2), k=(1-a)^15.
            ratio = (f60-f30)/(f30-f15)
            k = (-1 + math.sqrt(1 + 4*ratio))/2
            a = 1-k**(1/15)
            equilibrium = (f30-k*f15)/(1-k)
            origin = equilibrium+(f15-equilibrium)/k
            entry["last_forecast"] = dict(local_time=datetime.fromtimestamp(t, ZoneInfo("Europe/Amsterdam")).isoformat(),
                q=c["q"], forecasts=c["f"], inferred_loss_per_minute=a,
                inferred_equilibrium=equilibrium, inferred_origin=origin,
                inference="zero delivered proxy/lag; coefficients not directly exported; offset and outdoor not separately identifiable")
        report["rooms"][room] = entry
    return report


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv",type=Path);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.csv),indent=2),encoding="utf-8")
