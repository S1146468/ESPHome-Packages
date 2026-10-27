"""Run with python -m pytest AdaptiveClimate/tests."""
import importlib.util
from pathlib import Path
import pytest
import esphome.config_validation as cv

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("adaptive_climate_schema", ROOT / "components/adaptive_climate/__init__.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def config():
    return {**{key: f"input_{key}" for key in module.INPUTS + module.FLAGS}, "id": "test_observer"}

def test_observe_only_defaults():
    result = module.CONFIG_SCHEMA(config())
    assert result["mode"] == "observe"
    assert result["stale_after"].total_milliseconds == 900000

@pytest.mark.parametrize("mode", ["control", "adaptive", "mpc"])
def test_rejects_actuation(mode):
    with pytest.raises(cv.Invalid):
        module.CONFIG_SCHEMA({**config(), "mode": mode})

@pytest.mark.parametrize("key,value", [("output", "valve"), ("stale_after", "0s"), ("stale_after", "61min"), ("update_interval", "1ms")])
def test_rejects_unsafe_configuration(key, value):
    with pytest.raises(cv.Invalid):
        module.CONFIG_SCHEMA({**config(), key: value})

@pytest.mark.parametrize("key", module.INPUTS + module.FLAGS)
def test_required_inputs(key):
    data = config()
    del data[key]
    with pytest.raises(cv.Invalid):
        module.CONFIG_SCHEMA(data)

def test_no_actuator_dependencies():
    source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "components/adaptive_climate").glob("*.*") if p.suffix in (".py", ".cpp", ".h"))
    for forbidden in ("set_level(", "make_call(", "turn_on(", "turn_off(", "homeassistant.service", "components/output/", "components/switch/"):
        assert forbidden not in source
