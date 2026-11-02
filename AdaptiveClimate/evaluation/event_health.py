"""Predefined event-health sensitivity study. All accepted scores are held-state evidence."""
import argparse
import bisect
from collections import Counter, defaultdict
import json
from pathlib import Path
from analyze_exports import merge, History, numeric
from validated_scoring import timestamp, partition
from score_recorded import score

# Frozen before results: outcome hold limits versus receipt-diagnostic transport gaps.
POLICIES = [(30,30),(60,30),(300,30),(900,30),(300,60)]
LIMITS = list(map(timestamp, ['2026-10-30T11:00:00Z','2026-10-31T11:00:00Z',
                             '2026-11-01T11:00:00Z','2026-11-02T11:00:00Z']))


def value(history, t, age=float('inf')):
    row = history.at(t, age)
    return numeric(row) if row is not None else None


def state(history,t):
    row = history.at(t,float('inf'))
    return row['record']['state'] if row else None


def status_usable(text):
    if not text or 'api_disconnected' in text:
        return False
    fields = dict(part.split('=',1) for part in text.split('; ') if '=' in part)
    return (set(fields) == {'room','outdoor','valve','supply'} and
            all(fields[x] in ('recent_publication','held_unconfirmed') for x in ('room','outdoor')) and
            all(fields[x] == 'recent_publication' for x in ('valve','supply')))


class Health:
    def __init__(self, histories, room, gap):
        prefix = f'sensor.kamer_{room}_adaptive_climate_{room}_{room}_'
        self.age = [histories[prefix+x+'_input_age'] for x in
                    ('room_temperature','outdoor_temperature','valve_command','supply_temperature')]
        status = histories[prefix+'input_freshness_status']
        raw = histories[f'sensor.temp_sensor_kamer_{room}_temperature']
        uptime = histories['sensor.diyless_thermostat_uptime']
        resets = {b[0] for a,b in zip(uptime.rows,uptime.rows[1:])
                  if numeric(a[1]) is not None and numeric(b[1]) is not None and numeric(b[1]) < numeric(a[1])}
        invalid_times = [t for h in self.age+[uptime] for t,r in h.rows
                         if numeric(r) is None or r['conflict']]
        # Evaluate at 10-second checkpoints AND all raw/status changes, so short
        # invalid states are not hidden between checkpoints. Never look forward.
        self.times = sorted(set(list(range(int(LIMITS[0]),int(LIMITS[-1])+1,10)) +
            [t for h in (raw,status) for t in h.times if LIMITS[0] <= t <= LIMITS[-1]] +
            [t for t in invalid_times+list(resets) if LIMITS[0] <= t <= LIMITS[-1]]))
        self.bad = [0]
        self.reasons = Counter()
        for t in self.times:
            reason = None
            if t in resets:
                reason = 'uptime_decreased'
            elif not status_usable(state(status,t)):
                reason = 'explicit_or_unknown_input_status'
            elif value(raw,t) is None:
                reason = 'raw_unavailable'
            elif value(uptime,t,360) is None:
                reason = 'uptime_evidence_gap'
            else:
                for i,h in enumerate(self.age):
                    r = h.at(t,gap)
                    age = numeric(r) if r else None
                    if age is None or age < 0:
                        reason = 'age_diagnostic_gap_or_invalid'; break
                    projected = age+t-timestamp(r['record']['last_changed'])
                    if (i == 2 and projected > 60) or (i == 3 and projected > 900):
                        reason = 'strict_input_expired'; break
            self.reasons[reason or 'reconstructed_live_held_state'] += 1
            self.bad.append(self.bad[-1]+bool(reason))

    def interval(self,start,end):
        left = bisect.bisect_right(self.times,start)-1
        right = bisect.bisect_right(self.times,end)
        return left >= 0 and right > left and self.bad[right] == self.bad[left]


def changes(h,start,end):
    rows = h.rows[bisect.bisect_right(h.times,start):bisect.bisect_right(h.times,end)]
    return rows


def regime(histories,room,start,end):
    ch = histories['binary_sensor.thermostaat_heating_active']
    dhw = histories['binary_sensor.thermostaat_hot_water_active']
    valve = histories[f'sensor.climate_{room}_valve_opening_degree']
    streams = [(ch,('on','off')), (dhw,('on','off'))]
    for h,allowed in streams:
        if state(h,start) not in allowed or any(r['conflict'] or r['record']['state'] not in allowed for _,r in changes(h,start,end)):
            return 'unknown_operation'
    if state(dhw,start) == 'on' or any(r['record']['state']=='on' for _,r in changes(dhw,start,end)):
        return 'dhw_interval'
    if value(valve,start) is None or any(numeric(r) is None or r['conflict'] for _,r in changes(valve,start,end)):
        return 'unknown_operation'
    if changes(ch,start,end):
        return 'ch_transition'
    if changes(valve,start,end):
        return 'valve_transition'
    return 'stable_ch_on' if state(ch,start)=='on' else 'stable_ch_off'


def run(paths):
    events,sources,duplicates,conflicts=merge(paths)
    histories={k:History(v) for k,v in events.items()}
    result=dict(evidence='reconstructed live diagnostics + bounded held raw states; NOT physical measurements',
                sources=sources,strict_verified_origins=0,policies={},timing={})
    for room in ('stijn','nick'):
        prefix='sensor.server_thermostaat_stijn_' if room=='stijn' else 'sensor.kamer_nick_adaptive_climate_nick_nick_'
        raw=histories[f'sensor.temp_sensor_kamer_{room}_temperature']
        ready=histories[prefix+'model_status']
        training=histories[prefix+'model_training_samples']
        published=[t for t,r in events[prefix+'forecast_15min'] if numeric(r) is not None and not r['boundary']]
        gaps=[b-a for a,b in zip(published,published[1:])]
        result['timing'][room]=dict(finite_publications=len(published),
            consecutive_gaps=len(gaps),within_2s_of_300=sum(abs(g-300)<=2 for g in gaps),
            training_counter_event_within_2s=sum(any(abs(x-t)<=2 for x in training.times[bisect.bisect_left(training.times,t-2):bisect.bisect_right(training.times,t+2)]) for t in published),
            interpretation='HA receipt/change times consistent with cycles, not exact device issue timestamps')
        for hold,gap in POLICIES:
            health=Health(histories,room,gap)
            for horizon in (15,30,60):
                counts=Counter(); errors=defaultdict(list); groups=defaultdict(list); ages=[]
                for t,r in events[prefix+f'forecast_{horizon}min']:
                    counts['total']+=1
                    split=partition(t,*LIMITS)
                    if split is None: counts['split_embargo']+=1; continue
                    if r['boundary'] or r['conflict'] or numeric(r) is None: counts['invalid_forecast']+=1; continue
                    if state(ready,t) not in ('learning_unvalidated','low_excitation'): counts['not_ready_at_publication']+=1; continue
                    a,b=raw.at(t,hold),raw.at(t+horizon*60,hold)
                    if a is None or b is None or any(numeric(x) is None or not 0<=numeric(x)<=45 for x in (a,b)):
                        counts['raw_pair_missing_invalid_or_old']+=1; continue
                    if not health.interval(t,t+horizon*60): counts['health_interval']+=1; continue
                    counts['accepted_held_state']+=1
                    ages.extend([t-timestamp(a['record']['last_changed']),t+horizon*60-timestamp(b['record']['last_changed'])])
                    label=regime(histories,room,t,t+horizon*60)
                    for model,pred in [('recorded',numeric(r)),('persistence',numeric(a))]:
                        e=pred-numeric(b)
                        errors[split+'/'+model].append(e)
                        groups[split+'/'+label+'/'+model].append(e)
                key=f'{room}/{horizon}/hold{hold}_gap{gap}'
                result['policies'][key]=dict(counts=dict(counts),metrics={k:score(v) for k,v in errors.items()},
                    regimes={k:score(v) for k,v in groups.items()},
                    raw_ages=dict(n=len(ages),mean=sum(ages)/len(ages) if ages else None,max=max(ages) if ages else None),
                    health_checkpoints=dict(health.reasons))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('files',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.write_text(json.dumps(run(args.files),indent=2),encoding='utf-8')
