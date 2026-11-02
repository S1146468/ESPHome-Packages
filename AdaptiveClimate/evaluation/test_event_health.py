import unittest
from unittest.mock import patch
from datetime import datetime,timezone
from analyze_exports import History
from event_health import Health,status_usable


GOOD='room=held_unconfirmed; outdoor=held_unconfirmed; valve=recent_publication; supply=recent_publication'


def history(points):
    return History([(t,dict(record={'state':str(v),'last_changed':datetime.fromtimestamp(t,timezone.utc).isoformat()},
                            boundary=False,conflict=False)) for t,v in points])


def fixture():
    p='sensor.kamer_stijn_adaptive_climate_stijn_stijn_'
    result={p+'input_freshness_status':history([(0,GOOD)]),
        'sensor.temp_sensor_kamer_stijn_temperature':history([(0,20)]),
        'sensor.diyless_thermostat_uptime':history([(0,1000)])}
    for key in ('room_temperature','outdoor_temperature','valve_command','supply_temperature'):
        result[p+key+'_input_age']=history([(t,0) for t in range(0,101,10)])
    return result


class EventHealthTest(unittest.TestCase):
    @patch('event_health.LIMITS',[0,30,60,100])
    def test_old_status_not_required_to_republish(self):
        self.assertTrue(Health(fixture(),'stijn',30).interval(1,90))

    @patch('event_health.LIMITS',[0,30,60,100])
    def test_diagnostic_gap_rejects(self):
        data=fixture()
        data['sensor.kamer_stijn_adaptive_climate_stijn_stijn_room_temperature_input_age']=history([(0,0)])
        self.assertFalse(Health(data,'stijn',30).interval(1,90))

    @patch('event_health.LIMITS',[0,30,60,100])
    def test_brief_invalid_and_api_disconnect_not_hidden(self):
        data=fixture()
        data['sensor.kamer_stijn_adaptive_climate_stijn_stijn_input_freshness_status']=history([(0,GOOD),(22,'api_disconnected; '+GOOD),(23,GOOD)])
        self.assertFalse(Health(data,'stijn',30).interval(1,90))

    @patch('event_health.LIMITS',[0,30,60,100])
    def test_uptime_drop_masks_crossing_interval(self):
        data=fixture();data['sensor.diyless_thermostat_uptime']=history([(0,1000),(23,1)])
        self.assertFalse(Health(data,'stijn',30).interval(1,90))

    def test_only_known_statuses(self):
        self.assertTrue(status_usable(GOOD))
        self.assertFalse(status_usable(GOOD.replace('valve=recent_publication','valve=held_unconfirmed')))
        self.assertFalse(status_usable('unavailable'))


if __name__=='__main__': unittest.main()
