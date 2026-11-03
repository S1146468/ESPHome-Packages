import pytest
import esphome.config_validation as cv
from test_schema import module, config
from test_integration import validate


def test_shadow_opt_in():
    assert module.CONFIG_SCHEMA(config())["shadow_model"] is False
    result=module.CONFIG_SCHEMA({**config(),"shadow_model":True,"model_record":{"name":"Reference Details"},
        "shadow_record":{"name":"Candidate Details"},"shadow_forecasts":{"name":"Conditional Forecasts"}})
    assert result["shadow_model"] is True


def test_shadow_fixture_generates(tmp_path):
    # Include chain resolved in the repository, as with the existing cycle test.
    from pathlib import Path
    import os,subprocess,sys
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,"-m","esphome","compile",str(root/"examples/shadow_diagnostics.yaml"),"--only-generate"],
        capture_output=True,text=True,encoding="utf-8",env={**os.environ,"PYTHONUTF8":"1"},timeout=60)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize("key",["shadow_record","shadow_forecasts"])
def test_shadow_records_need_explicit_enable(key):
    with pytest.raises(cv.Invalid):
        module.CONFIG_SCHEMA({**config(),key:{"name":"Accidental disabled record"}})
