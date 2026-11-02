import tempfile
import unittest
from pathlib import Path
from analyze_exports import merge, History, numeric


class ExportTests(unittest.TestCase):
    def test_merge_preserves_attributes_masks_conflicts_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder)/'a.csv', Path(folder)/'b.csv'
            header = 'entity_id,state,last_changed,temperature\n'
            row = 'climate.x,heat,2026-10-30T11:00:00Z,20\n'
            a.write_text(header+row+'sensor.x,20,2026-10-30T11:01:00Z,\n')
            b.write_text(header+row+'sensor.x,21,2026-10-30T11:01:00Z,\n')
            events, sources, duplicates, conflicts = merge([a,b])
            self.assertEqual((duplicates,conflicts),(1,1))
            self.assertEqual(events['climate.x'][0][1]['record']['temperature'],'20')
            self.assertTrue(events['sensor.x'][0][1]['conflict'])
            self.assertIsNone(History(events['sensor.x']).at(events['sensor.x'][0][0],60))

    def test_unavailable_not_skipped_and_no_future_backfill(self):
        def row(value):
            return dict(record=dict(state=value), boundary=False, conflict=False)
        h = History([(10,row('20')),(20,row('unavailable'))])
        self.assertIsNone(h.at(9,60))
        self.assertIsNone(numeric(h.at(21,60)))
        self.assertIsNone(h.at(100,60))

    def test_boundary_not_a_measurement(self):
        self.assertIsNone(History([(0,dict(boundary=True,conflict=False))]).at(0,60))


if __name__ == '__main__':
    unittest.main()
