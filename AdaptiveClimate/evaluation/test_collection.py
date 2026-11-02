import io
import json
import unittest
from unittest.mock import patch
from collect_states import snapshot


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


if __name__=='__main__':unittest.main()
