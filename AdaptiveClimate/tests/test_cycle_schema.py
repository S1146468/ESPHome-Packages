from test_schema import module, config
from test_integration import validate, ROOT


def test_cycle_record_optional():
    assert 'cycle_record' not in module.CONFIG_SCHEMA(config())
    assert 'cycle_record' in module.CONFIG_SCHEMA({**config(), 'cycle_record': {'name': 'Cycle'}})


def test_cycle_fixture_codegen(tmp_path):
    result = validate('cycle_diagnostics.yaml', tmp_path, generate=True,
                      transform=lambda s: s.replace('!include single_room.yaml',
                          '!include ' + (ROOT / 'examples/single_room.yaml').as_posix()))
    assert result.returncode == 0, result.stdout + result.stderr
