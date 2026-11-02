"""Set ADAPTIVE_REPLAY_EXE to exercise the compiled production observer replay."""
import csv
import io
import os
import subprocess
import unittest


@unittest.skipUnless(os.environ.get('ADAPTIVE_REPLAY_EXE'), 'compiled replay not configured')
class ReplayTest(unittest.TestCase):
    def run_replay(self, rows):
        return subprocess.run([os.environ['ADAPTIVE_REPLAY_EXE']], input='\n'.join(rows)+'\n',
                              capture_output=True, text=True, check=False)

    def test_deterministic_independent_and_interruptions(self):
        rows = []
        for i in range(32):
            rows.append(f'stijn {i*300000} 20 10 50 50 1 0 0 1')
            rows.append(f'nick {i*300000} 20 10 0 50 0 0 0 1')
        first = self.run_replay(rows)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, self.run_replay(rows).stdout)
        both = list(csv.DictReader(io.StringIO(first.stdout)))
        solo = self.run_replay(rows[::2])
        self.assertEqual([r for r in both if r['room'] == 'stijn'],
                         list(csv.DictReader(io.StringIO(solo.stdout))))
        self.assertNotEqual(both[-2]['gain'], both[-1]['gain'])
        self.assertEqual(both[-2]['samples'], '31')
        interrupted = self.run_replay(rows + [
            'stijn 9600000 20 10 50 50 1 1 0 1',
            'nick 9600000 20 10 0 50 0 0 1 1',
            'stijn 9900000 20 10 50 50 1 0 0 0'])
        tail = list(csv.DictReader(io.StringIO(interrupted.stdout)))[-3:]
        self.assertEqual([r['status'] for r in tail], ['window_open', 'domestic_hot_water', 'masked_input'])
        self.assertTrue(all(r['forecast15'] == 'nan' for r in tail))

    def test_malformed_and_reverse_clock(self):
        self.assertEqual(self.run_replay(['stijn 0 20 10 0 40 2 0 0 1']).returncode, 2)
        self.assertEqual(self.run_replay(['stijn 100 20 10 0 40 0 0 0 1',
                                          'stijn 0 20 10 0 40 0 0 0 1']).returncode, 2)


if __name__ == '__main__':
    unittest.main()
