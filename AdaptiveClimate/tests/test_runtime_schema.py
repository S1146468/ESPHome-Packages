import hashlib
import importlib.util
import json
from pathlib import Path
import pytest
import esphome.config_validation as cv
from test_schema import module, config

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("deployment_validation", ROOT/"deployment/validate_candidate.py")
validation=importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


def test_instrumentation_is_optional():
    result=module.CONFIG_SCHEMA(config())
    assert not any(key in result for key in ("runtime_record","input_record","pid_tick_source","writer_tick_source"))
    result=module.CONFIG_SCHEMA({**config(),"runtime_record":{"name":"Timing"},"input_record":{"name":"Origin"},"pid_tick_source":"pid_input"})
    assert "runtime_record" in result


@pytest.mark.parametrize("key",["pid_tick_source","writer_tick_source"])
def test_probes_require_runtime_record(key):
    with pytest.raises(cv.Invalid):
        module.CONFIG_SCHEMA({**config(),key:"probe"})


def test_both_learners_frozen_to_a96e05d():
    seal=json.loads((ROOT/"deployment/learner_freeze.json").read_text())
    for name,expected in seal["sha256_normalized_utf8"].items():
        actual=(ROOT/"components/adaptive_climate"/name).read_text(encoding="utf-8")
        assert hashlib.sha256(actual.encode()).hexdigest()==expected


def test_comparison_rejects_control_and_observer_changes():
    import copy
    observer={"id":"stijn","prediction_15min":{"id":"f15"},"prediction_30min":{"id":"f30"},"prediction_60min":{"id":"f60"}}
    baseline={"climate":[{"kp":.8}],"adaptive_climate":[observer,{**observer,"id":"nick"}]}
    candidate=copy.deepcopy(baseline)
    for row in candidate["adaptive_climate"]:
        row["shadow_model"]=True
        for key in ("model_record","shadow_record","shadow_forecasts","input_record","runtime_record"):
            row[key]={"id":row["id"]+key}
    assert validation.compare(baseline,candidate)["original_observers_identical"]
    changed=copy.deepcopy(candidate);changed["climate"][0]["kp"]=.9
    with pytest.raises(ValueError,match="Control domain"):
        validation.compare(baseline,changed)
    changed=copy.deepcopy(candidate);changed["adaptive_climate"][0]["stale_after"]="2min"
    with pytest.raises(ValueError,match="Original observer"):
        validation.compare(baseline,changed)
