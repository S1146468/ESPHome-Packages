"""Inventory HA event exports without interpolating or inventing measurement units."""
import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def inventory(paths):
    result = []
    for path in paths:
        groups = defaultdict(list)
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                groups[row["entity_id"]].append(row)
        entities = {}
        for entity, rows in sorted(groups.items()):
            times = [datetime.fromisoformat(r["last_changed"].replace("Z", "+00:00")) for r in rows]
            ordered = sorted(set(times))
            gaps = [(b-a).total_seconds() for a, b in zip(ordered, ordered[1:])]
            numeric = []
            invalid = 0
            for row in rows:
                invalid += row["state"].lower() in ("unknown", "unavailable", "", "none")
                try:
                    value = float(row["state"])
                    if math.isfinite(value):
                        numeric.append(value)
                except ValueError:
                    pass
            entities[entity] = dict(rows=len(rows), start=ordered[0].isoformat(), end=ordered[-1].isoformat(),
                duplicate_timestamps=len(times)-len(ordered), out_of_order=times != sorted(times),
                invalid_rows=invalid, numeric_rows=len(numeric),
                minimum=min(numeric) if numeric else None, maximum=max(numeric) if numeric else None,
                median_event_gap_seconds=statistics.median(gaps) if gaps else None,
                maximum_event_gap_seconds=max(gaps) if gaps else None,
                units="not present in export", states=sorted(set(r["state"] for r in rows))[:20] if not numeric else None)
        result.append(dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), entities=entities))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inventory(args.files), indent=2), encoding="utf-8")
