"""Exercise native ESPHome device registration, not custom registration mocks."""
import re
import subprocess

import pytest
import yaml

from test_integration import ROOT, ConfigLoader, validate

OUTPUTS = ("prediction_15min", "prediction_30min", "prediction_60min",
           "residual_rmse", "training_samples", "heating_excitation", "status")
LABELS = ("Forecast 15min", "Forecast 30min", "Forecast 60min", "Model Residual RMSE",
          "Model Training Samples", "Model Heating Excitation", "Model Status")

@pytest.fixture(scope="module")
def configs(tmp_path_factory):
    result = {}
    for name in ("single_room.yaml", "two_rooms.yaml", "stijn_device_check.yaml"):
        run = validate(name, tmp_path_factory.mktemp(name))
        assert run.returncode == 0, run.stdout + run.stderr
        result[name] = yaml.load(run.stdout, Loader=ConfigLoader)
    return result

@pytest.mark.parametrize("example,devices,areas,prefixes", [
    ("single_room.yaml", ["adaptive_room"], ["room_area"], ["Room"]),
    ("two_rooms.yaml", ["adaptive_a", "adaptive_b"], ["area_a", "area_b"], ["Room A", "Room B"]),
    ("stijn_device_check.yaml", ["adaptive_climate_stijn"], ["kamer_stijn"], ["Stijn"]),
])
def test_all_seven_entities(configs, example, devices, areas, prefixes):
    config = configs[example]
    declared = {d["id"]: d for d in config["esphome"]["devices"]}
    area_ids = {d["id"] for d in config["esphome"]["areas"]}
    names, ids = [], []
    assert len(config["adaptive_climate"]) == len(devices)
    for observer, device, area, prefix in zip(config["adaptive_climate"], devices, areas, prefixes):
        assert declared[device]["area_id"] == area and area in area_ids
        for key, label in zip(OUTPUTS, LABELS):
            entity = observer[key]
            assert entity["device_id"] == device  # Includes the text sensor.
            assert entity["name"] == f"{prefix} {label}"
            assert entity["id"] == f"{observer['id']}_{key}"
            assert re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", entity["id"])
            assert entity["entity_category"] == "diagnostic"
            assert entity["icon"].startswith("mdi:")
            names.append(entity["name"])
            ids.append(entity["id"])
            if key != "status":
                assert entity["accuracy_decimals"] == (0 if key == "training_samples" else 3)
                assert entity["unit_of_measurement"] == ("°C" if key in OUTPUTS[:4] else "")
            if key in OUTPUTS[:3]:
                assert entity["device_class"] == "temperature"
            else:
                assert entity.get("device_class", "") == ""
    assert len(ids) == len(set(ids)) and len(names) == len(set(names))

def test_stijn_existing_device_and_input_contract(configs):
    c = configs["stijn_device_check.yaml"]
    devices = {d["id"]: d for d in c["esphome"]["devices"]}
    for key, name, area in (("climate_stijn", "Climate Stijn", "kamer_stijn"),
                            ("climate_nick", "Climate Nick", "kamer_nick"),
                            ("adaptive_climate_stijn", "Adaptive Climate Stijn", "kamer_stijn")):
        assert devices[key]["name"] == name and devices[key]["area_id"] == area
    assert len(devices) == 3  # Main physical device is implicit.
    obs, = c["adaptive_climate"]  # No Nick observer.
    assert obs["id"] == "stijn_thermal_model" and obs["stale_after"] == "15min"
    expected = dict(room_temperature="climate_stijn_temperature", outdoor_temperature="outside_temperature_sensor",
                    valve_command="climate_stijn_valve_opening_degree", supply_temperature="ch_temperature",
                    heating_active="boiler_active", window_open="climate_stijn_window", dhw_active="dhw_active")
    assert {key: obs[key] for key in expected} == expected
    assert {x["device_id"] for x in c["climate"]} == {"climate_stijn", "climate_nick"}

def test_existing_thermostat_configuration_unchanged(configs, tmp_path):
    def without_observer(text):
        return re.sub(r"(?ms)^  stijn_observer: !include\n.*?(?=^[a-z_]+:|\Z)", "", text)
    run = validate("stijn_device_check.yaml", tmp_path, transform=without_observer)
    assert run.returncode == 0, run.stdout + run.stderr
    baseline = yaml.load(run.stdout, Loader=ConfigLoader)
    observed = configs["stijn_device_check.yaml"]
    assert "adaptive_climate" not in baseline
    for domain in ("climate", "opentherm", "output", "switch", "sensor", "binary_sensor",
                   "text_sensor", "button", "script", "interval", "globals"):
        assert observed[domain] == baseline[domain], domain
    # Check the source and numerical test did not change at all from the reviewed commit.
    for relative in ("Thermostat", "Thermostat.yaml", "AdaptiveClimate/components", "AdaptiveClimate/tests/test_thermal_model.cpp"):
        diff = subprocess.check_output(["git", "diff", "c9b98da68d882c1f12a2bafd5714ce67ed4a7096", "--", relative], cwd=ROOT.parent)
        assert not diff, relative

@pytest.mark.parametrize("replacement", [
    ("        id: adaptive_room", "        id: missing_device"),
    ("      device:\n        id: adaptive_room\n        name: Adaptive Room\n", ""),
    ("      area_id: room_area", "      area_id: missing_area"),
])
def test_missing_device_or_area_rejected(tmp_path, replacement):
    result = validate("single_room.yaml", tmp_path, replacement)
    assert result.returncode != 0

def test_native_codegen_assigns_every_output(tmp_path):
    run = validate("stijn_device_check.yaml", tmp_path, generate=True)
    assert run.returncode == 0, run.stdout + run.stderr
    cpp, = list(tmp_path.rglob("src/main.cpp"))
    source = cpp.read_text(encoding="utf-8")
    for key in OUTPUTS:
        assert f"stijn_thermal_model_{key}->set_device_(adaptive_climate_stijn);" in source
    assert source.count("->set_device_(adaptive_climate_stijn);") == 7
