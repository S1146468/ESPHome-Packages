"""Development-only chronological experiments, using bounded event-held inputs.

The C++ observer runs on an explicitly assumed five-minute grid, cold-started.
This is an experiment using production mathematics, NOT exact firmware replay.
"""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import subprocess
from collections import Counter,defaultdict
from analyze_exports import merge,History
from event_health import value,state,regime,LIMITS,status_usable
from experimental_models import heat_proxy,specifications
from score_recorded import score
from validated_scoring import partition,timestamp


def row_at(histories,room,t):
    get=lambda key,age=float('inf'):value(histories[key],t,age)
    row=dict(room=get(f'sensor.temp_sensor_kamer_{room}_temperature',900),
        outdoor=get('sensor.temperature',1800),supply=get('sensor.thermostaat_heating_temperature',900),
        valve=get(f'sensor.climate_{room}_valve_opening_degree'),
        trv=get(f'sensor.radiatorknop_{room}_local_temperature',1800),
        solar=get('sensor.knmi_solar_irradiance',1800),wind=get('sensor.knmi_wind_speed',1800),
        ch=state(histories['binary_sensor.thermostaat_heating_active'],t),
        dhw=state(histories['binary_sensor.thermostaat_hot_water_active'],t),
        window=state(histories[f'binary_sensor.raam_sensor_kamer_{room}_contact'],t))
    vents=[state(histories['input_select.ventilatie_vraag_'+name],t) for name in ('badkamer','keuken','toilet')]
    row['vent']=sum({'Low':0,'Mid':.5,'High':1}.get(v,0) for v in vents)/3 if all(v in ('Low','Mid','High') for v in vents) else None
    prefix=f'sensor.kamer_{room}_adaptive_climate_{room}_{room}_'
    valid=status_usable(state(histories[prefix+'input_freshness_status'],t))
    for signal,timeout in [('room_temperature',None),('outdoor_temperature',None),('valve_command',60),('supply_temperature',900)]:
        h=histories[prefix+signal+'_input_age'];r=h.at(t,30)
        age=get(prefix+signal+'_input_age',30)
        projected = age+t-timestamp(r['record']['last_changed']) if r is not None and age is not None else None
        if projected is None or projected<0 or (timeout and projected>timeout):valid=False
    valid=valid and all(row[k] is not None for k in ('room','outdoor','supply','valve'))
    valid=valid and all(row[k] in ('on','off') for k in ('ch','dhw','window'))
    if valid:valid=0<=row['room']<=45 and -40<=row['outdoor']<=50 and 0<=row['valve']<=100 and 0<=row['supply']<=100
    for key in ('ch','dhw','window'):row[key]=row[key]=='on'
    row['valid']=bool(valid)
    row['extras_valid']=all(row[k] is not None for k in ('trv','solar','wind','vent'))
    return row


def run(paths,exe):
    events,sources,_,_=merge(paths);histories={k:History(v) for k,v in events.items()}
    output=dict(sources=sources,protocol='exploratory cold-start assumed grid; held inputs; frozen candidates; online production reference',rooms={},
        solar_orientation=dict(stijn=251.44,nick=71.44,status='projection function implemented; projected historical evaluation blocked by missing solar azimuth/elevation or site coordinates'),
        no_final_test=True)
    for room in ('stijn','nick'):
        ticks=list(range(int(LIMITS[0])+300,int(LIMITS[-1])+1,300))
        rows=[row_at(histories,room,t) for t in ticks]
        lines=[]
        for t,r in zip(ticks,rows):
            nums=[r[k] if r[k] is not None else 0 for k in ('room','outdoor','valve','supply')]
            lines.append(' '.join(map(str,[room,int((t-LIMITS[0])*1000),*nums,int(r['ch']),int(r['window']),int(r['dhw']),int(r['valid'])])))
        completed=subprocess.run([str(exe)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True)
        production=list(csv.DictReader(io.StringIO(completed.stdout)))
        models=specifications(); states={m.name:[] for m in models}
        fit_counts={}
        for model in models:
            rad=0;previous=None
            for r in rows:
                if not r['valid'] or r['window'] or r['dhw']:
                    rad=0;previous=None;states[model.name].append(None);continue
                drive=heat_proxy(r['room'],r['supply'],r['valve'],r['ch'])
                if previous is None:rad=drive
                else:rad=previous+(rad-previous)*math.exp(-5/model.tau)
                states[model.name].append(dict(r,radiator=rad));previous=drive
            samples=[]
            for i in range(len(rows)-1):
                a,b=states[model.name][i:i+2]
                if ticks[i+1]>=LIMITS[1] or a is None or b is None or any(a[x] is None for x in model.extras):continue
                rate=(b['room']-a['room'])/5
                if abs(rate)<=.15:samples.append((a,rate))
            if samples:model.fit(samples)
            fit_counts[model.name]=len(samples)
        errors=defaultdict(list);strata=defaultdict(list);counts=Counter()
        for i,(t,r) in enumerate(zip(ticks,rows)):
            split=partition(t,*LIMITS)
            if split not in ('validation','test'):continue
            split='development_validation' if split=='validation' else 'development_later'
            counts['candidate_origins']+=1
            if not r['valid'] or r['window'] or r['dhw']:
                counts['invalid_origin_or_optional_input']+=1;continue
            futures=[]
            for h in (15,30,60):futures.append(value(histories[f'sensor.temp_sensor_kamer_{room}_temperature'],t+h*60,900))
            if any(v is None or not 0<=v<=45 for v in futures):counts['missing_bounded_outcome']+=1;continue
            core=[m for m in models if 'trv' not in m.extras]
            if any(not fit_counts[m.name] or any(r[x] is None for x in m.extras) for m in core):
                counts['core_optional_input_missing_or_untrained']+=1;continue
            predictions={m.name:[m.forecast(states[m.name][i],h) for h in (15,30,60)] for m in core}
            predictions['production_rls']=[float(production[i]['forecast'+str(h)]) for h in (15,30,60)]
            predictions['persistence']=[r['room']]*3
            if any(v is None or not math.isfinite(v) for values in predictions.values() for v in values):counts['common_model_unavailable']+=1;continue
            counts['accepted_common_all_horizons']+=1
            trv=next(m for m in models if m.name=='trv_20')
            if fit_counts['trv_20'] and r['trv'] is not None:
                trv_predictions=[trv.forecast(states['trv_20'][i],h) for h in (15,30,60)]
                if all(v is not None for v in trv_predictions):
                    for model,values in [('trv_20',trv_predictions),('production_rls',predictions['production_rls']),('persistence',predictions['persistence'])]:
                        for h,pred,target in zip((15,30,60),values,futures):
                            errors[f'trv_cohort/{split}/{h}/{model}'].append(pred-target)
            for model,values in predictions.items():
                for h,pred,target in zip((15,30,60),values,futures):
                    key=f'{split}/{h}/{model}';e=pred-target;errors[key].append(e)
                    label=regime(histories,room,t,t+h*60)
                    thermal='warming' if target>r['room'] else ('cooling' if target<r['room'] else 'unchanged')
                    strata[key+'/'+label].append(e);strata[key+'/'+thermal].append(e)
        output['rooms'][room]=dict(counts=dict(counts),training_samples=fit_counts,
            coefficients={m.name:m.coefficients for m in models},metrics={k:score(v) for k,v in errors.items()},
            strata={k:score(v) for k,v in strata.items()})
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('files',nargs='+',type=Path)
    parser.add_argument('--replay',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();a.output.write_text(json.dumps(run(a.files,a.replay.resolve()),indent=2),encoding='utf-8')
