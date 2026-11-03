"""Focused development comparison of actual C++ reference and shadow learners.

Uses the existing bounded held-history rules, not exact device replay. Grid
origins are identical; only real exported raw room events can train the shadow.
No November 3 EMA is used as raw temperature or as a scoring target.
"""
import argparse
from collections import Counter, defaultdict
import csv
import io
import hashlib
import json
import math
from pathlib import Path
import subprocess
from analyze_exports import merge, History
from event_health import LIMITS, value, state, status_usable, regime
from experiment_run import row_at
from score_recorded import score


def run(paths, exe, health_policy):
    events, sources, duplicates, conflicts = merge(paths)
    histories = defaultdict(lambda: History([]), {k: History(v) for k,v in events.items()})
    report = dict(sources=sources, duplicate_source_rows=duplicates, conflicting_source_rows=conflicts, health_policy=health_policy,
        protocol="development only; cold start; assumed 5min common origins; exported change times approximate receipt times; held raw endpoints <=900s; actual C++ models",
        limitations=["not independent validation", "correlated overlapping origins", "publication selection and timestamp uncertainty", "visibility gates are provisional, not calibrated confidence", "no EMA targets"], rooms={})
    component=Path(__file__).resolve().parents[1]/"components/adaptive_climate"
    report["model_sha256"]={name:hashlib.sha256((component/name).read_bytes()).hexdigest()
                            for name in ("thermal_model.h","shadow_model.h")}
    for room in ("stijn", "nick"):
        ticks = list(range(int(LIMITS[0])+300, int(LIMITS[-1])+1, 300))
        tick_set = set(ticks)
        raw_key=f"sensor.temp_sensor_kamer_{room}_temperature"
        prefix=f"sensor.kamer_{room}_adaptive_climate_{room}_{room}_"
        keys=[raw_key,"sensor.temperature","sensor.thermostaat_heating_temperature",
              f"sensor.climate_{room}_valve_opening_degree", "binary_sensor.thermostaat_heating_active",
              "binary_sensor.thermostaat_hot_water_active", f"binary_sensor.raam_sensor_kamer_{room}_contact",
              prefix+"input_freshness_status"]+[prefix+x+"_input_age" for x in ("room_temperature","outdoor_temperature","valve_command","supply_temperature")]
        pub_times={t for t,r in events.get(raw_key,[]) if not r["boundary"] and not r["conflict"]}
        times=sorted(tick_set | {t for key in keys for t,_ in events.get(key,[]) if LIMITS[0]<t<=LIMITS[-1]})
        lines=[];tick_rows={}
        for t in times:
            r=row_at(histories,room,t)
            if health_policy == "held_status":
                # Sensitivity only: assume cached usable firmware status implies
                # continuous input health. Recorder's missing/repeated age values
                # cannot establish this; keep conservative analysis separately.
                r["room"]=value(histories[raw_key],t)
                r["outdoor"]=value(histories["sensor.temperature"],t)
                r["supply"]=value(histories["sensor.thermostaat_heating_temperature"],t)
                flags=[state(histories[k],t) for k in ("binary_sensor.thermostaat_heating_active",
                    f"binary_sensor.raam_sensor_kamer_{room}_contact","binary_sensor.thermostaat_hot_water_active")]
                r["valid"]=status_usable(state(histories[prefix+"input_freshness_status"],t)) and all(
                    r[k] is not None and lo<=r[k]<=hi for k,lo,hi in (("room",0,45),("outdoor",-40,50),("valve",0,100),("supply",0,100))) and all(f in ("on","off") for f in flags)
                for k,f in zip(("ch","window","dhw"),flags):r[k]=f=="on"
            numbers=[r[k] if r[k] is not None else 0 for k in ("room","outdoor","valve","supply")]
            tick=t in tick_set
            if tick:tick_rows[t]=r
            lines.append(" ".join(map(str,[room,round((t-LIMITS[0])*1000),*numbers,
                int(r["ch"]),int(r["window"]),int(r["dhw"]),int(r["valid"]),int(t in pub_times),int(tick)])))
        result=subprocess.run([str(exe)],input="\n".join(lines)+"\n",capture_output=True,text=True,check=True)
        outputs=list(csv.DictReader(io.StringIO(result.stdout)))
        errors=defaultdict(list);strata=defaultdict(list);counts=Counter();ranges=defaultdict(list)
        common_origins=defaultdict(list)
        for t,o in zip(ticks,outputs):
            r=tick_rows[t];counts["origins"]+=1
            counts["reference_status/"+o["ref_status"]]+=1
            counts["shadow_status/"+o["shadow_status"]]+=1
            for m in ("ref","shadow"):
                for suffix in ("a","b","c"):ranges[m+"_"+suffix].append(float(o[m+"_"+suffix]))
                counts[m+"_saturated_origins"]+=int(o[m+"_sat"])!=0
            # Scores describe later development blocks; training is online on
            # preceding input events only. All scoring targets are future data.
            if t<LIMITS[1]:continue
            if not r["valid"] or r["window"] or r["dhw"]:continue
            if value(histories[raw_key],t,900) is None:continue
            for h in (15,30,60):
                target=value(histories[raw_key],t+h*60,900)
                if target is None or not 0<=target<=45 or t+h*60>LIMITS[-1]:continue
                a,b=float(o["ref"+str(h)]),float(o["shadow"+str(h)])
                counts[f"bounded_target/{h}"]+=1
                counts[f"ref_available/{h}"]+=math.isfinite(a)
                counts[f"shadow_available/{h}"]+=math.isfinite(b)
                if not all(map(math.isfinite,(a,b))):continue
                counts[f"common/{h}"]+=1
                common_origins[str(h)].append(t)
                label=regime(histories,room,t,t+h*60)
                thermal="warming" if target>r["room"] else ("cooling" if target<r["room"] else "unchanged")
                for model,pred in (("reference",a),("shadow",b),("persistence",r["room"])):
                    error=pred-target;errors[f"{h}/{model}"].append(error)
                    strata[f"{h}/{model}/{label}"].append(error);strata[f"{h}/{model}/{thermal}"].append(error)
        report["rooms"][room]=dict(counts=dict(counts), input_events=len(times), raw_publications=len(pub_times),
            final={k:outputs[-1][k] for k in outputs[-1] if k.endswith(("_n","_resets","_attempts","_accepted","_rejected"))},
            coefficients={k:dict(min=min(v),max=max(v),final=v[-1]) for k,v in ranges.items()},
            metrics={f"{h}/{m}":score(errors[f"{h}/{m}"]) for h in (15,30,60) for m in ("reference","shadow","persistence")},
            strata={k:score(v) for k,v in strata.items()}, common_origins=dict(common_origins))
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files",type=Path,nargs="+");parser.add_argument("--replay",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.write_text(json.dumps({p:run(args.files,args.replay.resolve(),p) for p in ("conservative","held_status")},indent=2),encoding="utf-8")
