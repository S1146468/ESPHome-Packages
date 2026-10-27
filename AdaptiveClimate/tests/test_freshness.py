"""Configuration, source-publication contracts, and both actual room bindings."""
import re
from pathlib import Path
import pytest
import yaml
import esphome
import esphome.config_validation as cv
from test_schema import config, module
from test_integration import ROOT, ConfigLoader, validate

@pytest.mark.parametrize('field', module.INPUTS)
def test_per_input_policy(field):
    c = module.CONFIG_SCHEMA({**config(), 'input_freshness': {
        field: {'mode': 'event_driven', 'stale_after': '2min', 'availability': 'healthy'}}})
    assert c['input_freshness'][field]['mode'] == 'event_driven'
    assert c['input_freshness'][field]['stale_after'].total_milliseconds == 120000
    assert c['require_api_connection'] is False
    assert c['valve_command_scale'] == 1.0

@pytest.mark.parametrize('policy', [
    {'room_temperature': {'mode': 'ignore'}},
    {'room_temperature': {'stale_after': '0s'}},
    {'room_temperature': {'stale_after': '61min'}},
    {'room_temperature': {'fake_heartbeat': True}},
    {'unknown_input': {'mode': 'strict'}},
])
def test_bad_policy_rejected(policy):
    with pytest.raises(cv.Invalid):
        module.CONFIG_SCHEMA({**config(), 'input_freshness': policy})

def test_api_guard_requires_api(tmp_path):
    r = validate('single_room.yaml', tmp_path, transform=lambda s: s.replace(
        '      observer_id:', '      observer_require_api_connection: "true"\n      observer_id:'))
    assert r.returncode != 0

@pytest.mark.parametrize('scale', [0, -1, 50, float('nan')])
def test_bad_raw_scale_rejected(scale):
    with pytest.raises(cv.Invalid):
        module.CONFIG_SCHEMA({**config(), 'valve_command_scale': scale})

@pytest.mark.parametrize('health,valid', [('window_contact', True), ('room_measurement', False), ('missing_health', False)])
def test_health_typed_binding(tmp_path, health, valid):
    r = validate('single_room.yaml', tmp_path, transform=lambda s: s.replace(
        '      observer_id:',
        '      observer_input_freshness:\n        room_temperature:\n          mode: event_driven\n'
        f'          availability: {health}\n      observer_id:'))
    assert (r.returncode == 0) == valid, r.stdout + r.stderr

def test_both_actual_rooms_and_all_diagnostics(tmp_path):
    r = validate('rooms_device_check.yaml', tmp_path, generate=True)
    assert r.returncode == 0, r.stdout + r.stderr
    cpp, = tmp_path.rglob('src/main.cpp')
    source = cpp.read_text(encoding='utf-8')
    for room in ('stijn', 'nick'):
        assert source.count(f'->set_device_(adaptive_climate_{room});') == 12
        for field in module.INPUTS:
            assert f'{room}_thermal_model_{field}_age->set_device_(adaptive_climate_{room});' in source
        assert f'{room}_thermal_model_input_status->set_device_(adaptive_climate_{room});' in source
        assert f'{room}_thermal_model->set_valve_command_scale(100.0f);' in source
    r = validate('rooms_device_check.yaml', tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    c = yaml.load(r.stdout, Loader=ConfigLoader)
    all_ids, all_names = [], []
    for obs, room in zip(c['adaptive_climate'], ('stijn', 'nick')):
        assert obs['id'] == f'{room}_thermal_model'
        assert obs['valve_command'] == f'pid_output_{room}'
        assert obs['require_api_connection'] is True
        for field in module.INPUTS:
            d = obs[field + '_age']
            assert d['device_id'] == f'adaptive_climate_{room}'
            assert d['unit_of_measurement'] == 's' and d['device_class'] == 'duration'
            assert d['entity_category'] == 'diagnostic'
        outputs = (*module.OUTPUTS, 'status', *(f + '_age' for f in module.INPUTS), 'input_status')
        for field in outputs:
            d = obs[field]
            assert d['device_id'] == f'adaptive_climate_{room}'
            assert d['entity_category'] == 'diagnostic'
            all_ids.append(d['id']); all_names.append(d['name'])
        policies = obs['input_freshness']
        assert policies['room_temperature']['mode'] == 'event_driven'
        assert policies['outdoor_temperature']['mode'] == 'event_driven'
        assert policies['valve_command']['mode'] == 'strict'
        assert policies['valve_command']['stale_after'] == '1min'
    assert len(set(all_ids)) == len(set(all_names)) == 24

def test_two_room_controls_unchanged(tmp_path):
    r = validate('rooms_device_check.yaml', tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    observed = yaml.load(r.stdout, Loader=ConfigLoader)
    def strip_observers(text):
        return re.sub(r'(?ms)^  stijn_observer: !include\n.*?(?=^external_components:)', '', text)
    r = validate('rooms_device_check.yaml', tmp_path, transform=strip_observers)
    assert r.returncode == 0, r.stdout + r.stderr
    baseline = yaml.load(r.stdout, Loader=ConfigLoader)
    for domain in ('climate', 'opentherm', 'output', 'switch', 'sensor', 'binary_sensor',
                   'text_sensor', 'button', 'script', 'interval', 'globals'):
        assert observed[domain] == baseline[domain], domain

def test_pinned_esphome_raw_and_ha_contract():
    # Protect the assumptions used by the C++ test doubles against upstream changes.
    base = Path(esphome.__file__).parent / 'components'
    ha = (base / 'homeassistant/sensor/homeassistant_sensor.cpp').read_text()
    assert 'parse_number<float>' in ha and 'publish_state(NAN)' in ha
    sensor = (base / 'sensor/sensor.cpp').read_text()
    assert sensor.index('raw_callback_.call(state)') < sensor.index('filter_list_->input(state)')
    filters = (base / 'sensor/filter.cpp').read_text()
    heartbeat = filters.split('void HeartbeatFilter::initialize', 1)[1].split('void HeartbeatFilter::dump_config', 1)[0]
    assert 'this->output(this->last_input_)' in heartbeat
    assert 'publish_state(' not in heartbeat
    output = filters.split('void Filter::output', 1)[1].split('void Filter::', 1)[0]
    assert 'internal_send_state_to_frontend' in output
    source = (ROOT / 'components/adaptive_climate/adaptive_climate.cpp').read_text()
    assert 'add_on_raw_state_callback' in source and 'add_on_state_callback' not in source
    assert source.count('.receive(') == 1
    assert 'is_connected_with_state_subscription()' in source
