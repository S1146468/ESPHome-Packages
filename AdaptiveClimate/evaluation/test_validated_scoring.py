from datetime import datetime, timezone
import unittest
from validated_scoring import evaluate, Series, partition, timestamp


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def fixture():
    meta = dict(raw_temperature_mapping_verified=True, forecast_issue_times_verified=True,
                measurement_publication_times_verified=True, units_verified=True,
                temperature_unit='degC', models=['original'],
                start=iso(0), train_end=iso(10000), validation_end=iso(20000), end=iso(30000))
    measurements, health, forecasts = [], [], []
    for room in ('stijn', 'nick'):
        for t in range(0, 6001, 60):
            measurements.append(dict(room=room, time=iso(t), value=20, available=True))
            health.append(dict(room=room, time=iso(t), available=True))
        for t in (600, 610):
            for h in (15, 30, 60):
                forecasts.append(dict(room=room, time=iso(t), horizon=h, model='original', value=19))
    return dict(metadata=meta, measurements=measurements, health=health, forecasts=forecasts)


class ValidatedScoringTest(unittest.TestCase):
    def test_common_origins_and_grid_sampling(self):
        result = evaluate(fixture())
        self.assertEqual(result['event_weighted']['stijn/train/60/original']['n'], 2)
        self.assertEqual(result['grid_sampled']['stijn/train/60/original']['n'], 1)
        self.assertEqual(result['event_weighted']['stijn/train/60/original']['bias'], -1)
        self.assertEqual(result['event_weighted']['stijn/train/60/persistence']['mae'], 0)

    def test_blocked_unverified_mapping(self):
        data = fixture()
        data['metadata']['raw_temperature_mapping_verified'] = False
        self.assertEqual(evaluate(data)['status'], 'blocked')

    def test_invalid_measurement_is_not_skipped(self):
        data = fixture()
        for r in data['measurements']:
            if r['room'] == 'stijn' and r['time'] == iso(4200):
                r['available'] = False
        result = evaluate(data)
        self.assertNotIn('stijn/train/60/original', result['event_weighted'])
        self.assertIn('nick/train/60/original', result['event_weighted'])

    def test_stale_future_measurement(self):
        data = fixture()
        data['measurements'] = [r for r in data['measurements'] if timestamp(r['time']) < 4000]
        self.assertFalse(evaluate(data)['event_weighted'])

    def test_health_interruption_masks_interval(self):
        data = fixture()
        data['health'][20]['available'] = False
        self.assertNotIn('stijn/train/15/original', evaluate(data)['event_weighted'])

    def test_missing_health_not_filled(self):
        data = fixture()
        data['health'] = []
        self.assertFalse(evaluate(data)['event_weighted'])

    def test_health_gap_uses_true_publication_age(self):
        series = Series([dict(time=iso(t), available=True) for t in (0, 500)])
        self.assertFalse(series.healthy_interval(300, 550, 360))

    def test_boundary_forecast_is_excluded(self):
        data = fixture()
        data['forecasts'][0]['boundary'] = True
        self.assertEqual(evaluate(data)['rejected']['invalid_or_boundary_forecast'], 1)

    def test_boundary_measurement(self):
        series = Series([dict(time=iso(0), value=20, available=True, boundary=True)])
        self.assertIsNone(series.at(1, 60))

    def test_no_future_match(self):
        series = Series([dict(time=iso(60), value=20, available=True)])
        self.assertIsNone(series.at(59, 60))

    def test_duplicate_and_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            Series([dict(time=iso(0))]*2)
        with self.assertRaises(ValueError):
            timestamp('2026-01-01T00:00:00')

    def test_common_candidate_mask(self):
        data = fixture()
        data['metadata']['models'].append('candidate')
        self.assertFalse(evaluate(data)['event_weighted'])

    def test_embargo(self):
        self.assertEqual(partition(0, 0, 10000, 20000, 30000), 'train')
        self.assertIsNone(partition(6400, 0, 10000, 20000, 30000))
        self.assertEqual(partition(10000, 0, 10000, 20000, 30000), 'validation')
        self.assertIsNone(partition(16400, 0, 10000, 20000, 30000))
        self.assertEqual(partition(20000, 0, 10000, 20000, 30000), 'test')

    def test_wrong_units_and_invalid_forecast(self):
        data = fixture()
        data['metadata']['temperature_unit'] = 'degF'
        with self.assertRaises(ValueError):
            evaluate(data)
        data = fixture()
        data['forecasts'][0]['value'] = float('nan')
        self.assertEqual(evaluate(data)['rejected']['invalid_or_boundary_forecast'], 1)


if __name__ == '__main__':
    unittest.main()
