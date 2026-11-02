"""Sustained read-only HA collection. Event mode requires websocket-client."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import threading
import time
import urllib.parse
import uuid


class Journal:
    """Append only; process lock; flush every record, fsync at most every 10s."""
    def __init__(self, path, rotate_bytes=128*1024*1024):
        path = Path(path)
        self.path, self.rotate_bytes = path, rotate_bytes
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = open(str(path)+'.lock', 'a+b')
        self.lock.write(b'0'); self.lock.flush(); self.lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        partial = False
        if path.exists() and path.stat().st_size:
            with path.open('rb') as f:
                f.seek(-1, 2); partial = f.read(1) != b'\n'
        self.stream = path.open('a', encoding='utf-8')
        self.run_id, self.sequence = str(uuid.uuid4()), 0
        self.last_sync = time.monotonic()
        if partial:
            self.stream.write('\n')  # Preserve truncated bytes, isolate new records.
            self.write('recovery', prior_tail_may_be_incomplete=True)

    def write(self, kind, **fields):
        if self.stream.tell() >= self.rotate_bytes:
            self.stream.flush(); os.fsync(self.stream.fileno()); self.stream.close()
            suffix = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
            self.path.rename(self.path.with_name(self.path.name+'.'+suffix))
            self.stream = self.path.open('a', encoding='utf-8')
        self.sequence += 1
        self.stream.write(json.dumps(dict(schema=1, run_id=self.run_id, sequence=self.sequence,
            received_utc=datetime.now(timezone.utc).isoformat(), received_monotonic_ns=time.monotonic_ns(),
            kind=kind, **fields))+'\n')
        self.stream.flush()
        if time.monotonic()-self.last_sync >= 10:
            os.fsync(self.stream.fileno()); self.last_sync = time.monotonic()

    def close(self):
        self.stream.flush(); os.fsync(self.stream.fileno()); self.stream.close(); self.lock.close()


def handle_message(message, entities, journal):
    if message.get('type') == 'event':
        event = message.get('event', {})
        if event.get('event_type') == 'state_changed' and event.get('data', {}).get('entity_id') in entities:
            journal.write('state_changed', event=event)
    elif message.get('type') == 'result' and message.get('id') == 2:
        if not message.get('success'):
            raise RuntimeError('Initial state retrieval rejected')
        states = [s for s in message['result'] if s['entity_id'] in entities]
        journal.write('boundary_snapshot', states=states,
                      missing_entities=sorted(entities-{s['entity_id'] for s in states}))


def event_session(base, token, entities, journal, stop):
    import websocket
    parts = urllib.parse.urlsplit(base)
    url = urllib.parse.urlunsplit(('wss' if parts.scheme == 'https' else 'ws', parts.netloc,
                                  parts.path.rstrip('/')+'/api/websocket', '', ''))
    ws = websocket.create_connection(url, timeout=30, enable_multithread=True)
    try:
        if json.loads(ws.recv()).get('type') != 'auth_required':
            raise RuntimeError('Unexpected handshake')
        ws.send(json.dumps({'type': 'auth', 'access_token': token}))
        if json.loads(ws.recv()).get('type') != 'auth_ok':
            raise PermissionError('Authentication rejected')
        ws.send(json.dumps({'id': 1, 'type': 'subscribe_events', 'event_type': 'state_changed'}))
        reply = json.loads(ws.recv())
        if reply.get('id') != 1 or not reply.get('success'):
            raise RuntimeError('Subscription rejected')
        journal.write('connected', transport='websocket', recovery_is_not_backfill=True)
        ws.send(json.dumps({'id': 2, 'type': 'get_states'}))
        ping_id, awaiting_pong = 2, False
        while not stop.is_set():
            try:
                raw = ws.recv()
                if not raw:
                    raise ConnectionError('Socket closed')
                message = json.loads(raw)
            except websocket.WebSocketTimeoutException:
                if awaiting_pong:
                    raise TimeoutError('No heartbeat reply')
                ping_id += 1
                ws.send(json.dumps({'id': ping_id, 'type': 'ping'})); awaiting_pong = True
                continue
            if message.get('type') == 'pong' and message.get('id') == ping_id:
                journal.write('transport_heartbeat', evidence='connection_only'); awaiting_pong = False
            handle_message(message, entities, journal)
    finally:
        ws.close()


def main():
    from collect_states import snapshot
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('entities', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--mode', choices=('events', 'poll'), default='events')
    p.add_argument('--once', action='store_true', help='One REST reachability check, not event capture')
    p.add_argument('--interval', type=float, default=60)
    p.add_argument('--allow-http', action='store_true')
    args = p.parse_args()
    entities = json.loads(args.entities.read_text())
    if not isinstance(entities, list) or not entities or not all(isinstance(e, str) and '.' in e for e in entities):
        p.error('Expected nonempty entity-ID list')
    if args.interval < 10:
        p.error('Polling interval must be >=10 seconds')
    base = os.environ['HA_URL'].rstrip('/')
    token = Path(os.environ['HA_TOKEN_FILE']).read_text().strip() if os.environ.get('HA_TOKEN_FILE') else os.environ['HA_TOKEN']
    parts = urllib.parse.urlsplit(base)
    if parts.scheme not in ('http', 'https') or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
        p.error('HA_URL must be an HTTP(S) base URL without credentials/query/fragment')
    if parts.scheme == 'http' and not args.allow_http:
        p.error('Use HTTPS or opt in to trusted-LAN plaintext with --allow-http')
    if not token:
        p.error('Empty token')
    if args.mode == 'events' and not args.once:
        try:
            import websocket
        except ImportError:
            p.error('Install requirements-collection.txt for event mode')
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    journal = Journal(args.output)
    journal.write('collector_start', mode='poll' if args.once else args.mode, entities=sorted(set(entities)))
    delay, code = 1, 0
    try:
        while not stop.is_set():
            started = time.monotonic()
            try:
                if args.mode == 'events' and not args.once:
                    event_session(base, token, set(entities), journal, stop)
                else:
                    states = snapshot(base, token, set(entities))
                    journal.write('poll_snapshot', states=states, cached_states_are_not_measurements=True,
                                  missing_entities=sorted(set(entities)-{s['entity_id'] for s in states}))
                    delay = 1
                    if args.once: break
                    stop.wait(max(0, args.interval-(time.monotonic()-started)))
            except Exception as error:
                # Never log exception text, auth frames, headers, token or URL.
                if isinstance(error, OSError) and error.errno in (28, 122):
                    raise  # Disk full/quota: supervisor must stop/recover, no retry flood.
                journal.write('collection_gap', error_type=type(error).__name__, retry_seconds=delay)
                if args.once: code = 1; break
                stop.wait(delay)
                delay = min(60, delay*2) if time.monotonic()-started < 60 else 1
    finally:
        journal.write('collector_stop', clean=True); journal.close()
    return code


if __name__ == '__main__': raise SystemExit(main())
