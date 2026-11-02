"""Read-only HA REST sampler. Repeated cached values retain HA timestamps.

HA_URL and HA_TOKEN environment variables; entities JSON is a list of entity IDs.
This captures snapshots, NOT guaranteed events or exact observer issue times.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import time
import urllib.request


def snapshot(base,token,entities):
    request=urllib.request.Request(base.rstrip('/')+'/api/states',headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(request,timeout=8) as response:
        states=json.load(response)
    return [s for s in states if s['entity_id'] in entities]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('entities',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--once',action='store_true');args=p.parse_args()
    entities=json.loads(args.entities.read_text())
    if not isinstance(entities,list) or not entities or not all(isinstance(e,str) for e in entities):
        raise ValueError('Expected nonempty entity-ID list')
    base,token=os.environ['HA_URL'],os.environ['HA_TOKEN']
    with args.output.open('a',encoding='utf-8') as f:
        while True:
            started=time.monotonic()
            record={'request_started_utc':datetime.now(timezone.utc).isoformat(),'kind':'snapshot'}
            try:
                record['states']=snapshot(base,token,set(entities))
                record['missing_entities']=sorted(set(entities)-{s['entity_id'] for s in record['states']})
            except Exception as error:
                record.update(kind='collection_gap',error_type=type(error).__name__)
            record['received_utc']=datetime.now(timezone.utc).isoformat()
            record['request_duration_seconds']=time.monotonic()-started
            f.write(json.dumps(record)+'\n');f.flush()
            if args.once: break
            time.sleep(max(0,10-(time.monotonic()-started)))


if __name__=='__main__':main()
