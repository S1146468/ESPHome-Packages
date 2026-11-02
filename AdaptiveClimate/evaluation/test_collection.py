import io
import json
import unittest
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from collect_states import snapshot
from continuous_collection import Journal, handle_message, event_session


class CollectionTest(unittest.TestCase):
    @patch('collect_states.urllib.request.urlopen')
    def test_get_only_preserves_original_timestamps(self,open_url):
        row=dict(entity_id='sensor.x',state='20',last_changed='2026-10-30T11:00:00Z',attributes={})
        open_url.return_value=io.BytesIO(json.dumps([row,dict(entity_id='sensor.other')]).encode())
        self.assertEqual(snapshot('http://localhost:8123','test-token',{'sensor.x'}),[row])
        request=open_url.call_args.args[0]
        self.assertEqual(request.get_method(),'GET')
        self.assertEqual(request.full_url,'http://localhost:8123/api/states')
        self.assertIsNone(request.data)

    def test_event_preserves_unavailable_and_removal(self):
        recorded=[]
        journal=SimpleNamespace(write=lambda kind,**kw:recorded.append((kind,kw)))
        for new in ({'state':'unavailable','last_changed':'original'},None):
            event={'event_type':'state_changed','time_fired':'event-time',
                   'data':{'entity_id':'sensor.x','new_state':new}}
            handle_message({'type':'event','event':event},{'sensor.x'},journal)
            self.assertEqual(recorded[-1][1]['event'],event)
        handle_message({'type':'event','event':{'event_type':'state_changed',
                       'data':{'entity_id':'sensor.other'}}},{'sensor.x'},journal)
        self.assertEqual(len(recorded),2)

    def test_restart_append_rotation_and_crash_tail(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'records.jsonl'
            path.write_text('partial-record',encoding='utf-8')
            journal=Journal(path,rotate_bytes=500)
            journal.write('test',value='a'*600);journal.write('next');journal.close()
            journal=Journal(path);journal.write('restarted');journal.close()
            text=''.join(p.read_text() for p in Path(folder).glob('records.jsonl*') if not p.name.endswith('.lock'))
            self.assertIn('partial-record\n',text)
            self.assertIn('"kind": "recovery"',text)
            self.assertIn('"kind": "next"',text)
            self.assertIn('"kind": "restarted"',text)

    def test_websocket_subscribe_before_boundary_and_only_read_commands(self):
        stop=threading.Event();sent=[];recorded=[]
        messages=[{'type':'auth_required'},{'type':'auth_ok'},
                  {'id':1,'type':'result','success':True},
                  {'id':2,'type':'result','success':True,'result':[{'entity_id':'sensor.x','state':'20'}]},
                  {'type':'event','event':{'event_type':'state_changed','data':{'entity_id':'sensor.x','new_state':None}}}]
        def recv():
            message=messages.pop(0)
            if not messages:stop.set()
            return json.dumps(message)
        ws=SimpleNamespace(recv=recv,send=lambda s:sent.append(json.loads(s)),close=lambda:None)
        module=SimpleNamespace(create_connection=lambda *a,**kw:ws,WebSocketTimeoutException=TimeoutError)
        journal=SimpleNamespace(write=lambda kind,**kw:recorded.append((kind,kw)))
        with patch.dict('sys.modules',{'websocket':module}):
            event_session('https://ha.example','secret',{'sensor.x'},journal,stop)
        self.assertEqual([s['type'] for s in sent],['auth','subscribe_events','get_states'])
        self.assertEqual([r[0] for r in recorded],['connected','boundary_snapshot','state_changed'])
        self.assertNotIn('secret',json.dumps(recorded))

    def test_silent_socket_ping_then_disconnect(self):
        sent=[];closed=[]
        messages=[{'type':'auth_required'},{'type':'auth_ok'},{'id':1,'type':'result','success':True}]
        def recv():
            if messages:return json.dumps(messages.pop(0))
            raise TimeoutError()
        ws=SimpleNamespace(recv=recv,send=lambda s:sent.append(json.loads(s)),close=lambda:closed.append(True))
        module=SimpleNamespace(create_connection=lambda *a,**kw:ws,WebSocketTimeoutException=TimeoutError)
        journal=SimpleNamespace(write=lambda *a,**kw:None)
        with patch.dict('sys.modules',{'websocket':module}):
            with self.assertRaises(TimeoutError):
                event_session('https://ha.example','secret',{'sensor.x'},journal,threading.Event())
        self.assertEqual(sent[-1]['type'],'ping')
        self.assertEqual(closed,[True])


if __name__=='__main__':unittest.main()
