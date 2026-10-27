"""Validate real ESPHome package expansion and typed ID binding."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

class ConfigLoader(yaml.SafeLoader):
    pass

ConfigLoader.add_constructor("!lambda", lambda loader, node: loader.construct_scalar(node))

def validate(example, tmp_path, replacement=None):
    text = (ROOT / "examples" / example).read_text(encoding="utf-8")
    text = text.replace("../components", (ROOT / "components").as_posix())
    text = text.replace("../ObserveRoom.yaml", (ROOT / "ObserveRoom.yaml").as_posix())
    if replacement:
        text = text.replace(*replacement)
    path = tmp_path / "test.yaml"
    path.write_text(text, encoding="utf-8")
    return subprocess.run([sys.executable, "-m", "esphome", "config", str(path)],
                          capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, "PYTHONUTF8": "1"}, timeout=60)

@pytest.mark.parametrize("example,count", [("single_room.yaml", 1), ("two_rooms.yaml", 2)])
def test_complete_examples(example, count, tmp_path):
    result = validate(example, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    config = yaml.load(result.stdout, Loader=ConfigLoader)
    assert len(config["adaptive_climate"]) == count
    assert config["esp32"]["framework"]["type"] == "esp-idf"
    for forbidden in ("climate", "opentherm", "output", "switch"):
        assert forbidden not in config
    if count == 2:
        a, b = config["adaptive_climate"]
        assert a["id"] == "model_a" and b["id"] == "model_b"
        for field, first, second in (
            ("room_temperature", "temperature_a", "temperature_b"),
            ("outdoor_temperature", "outdoor", "outdoor"),
            ("valve_command", "command_a", "command_b"),
            ("supply_temperature", "supply", "supply"),
            ("heating_active", "heating", "heating"),
            ("window_open", "window_a", "window_b"),
            ("dhw_active", "dhw", "dhw"),
        ):
            assert a[field] == first and b[field] == second
        assert a["stale_after"] == "15min"
        assert b["stale_after"] == "20min"

@pytest.mark.parametrize("before,after", [
    ("room_temperature_id: room_measurement", "room_temperature_id: missing_sensor"),
    ("window_open_id: window_contact", "window_open_id: room_measurement"),
    ("      supply_temperature_id: water_measurement\n", ""),
])
def test_bad_bindings_rejected(before, after, tmp_path):
    result = validate("single_room.yaml", tmp_path, (before, after))
    assert result.returncode != 0

def test_duplicate_model_id_rejected(tmp_path):
    result = validate("two_rooms.yaml", tmp_path, ("observer_id: model_b", "observer_id: model_a"))
    assert result.returncode != 0

def test_extracted_runtime_matches_source_manifest():
    manifest = json.loads((ROOT / "docs/source_manifest.json").read_text())
    for name, digest in manifest["sha256_normalized_utf8"].items():
        source = (ROOT / "components/adaptive_climate" / name).read_text(encoding="utf-8")
        assert hashlib.sha256(source.encode("utf-8")).hexdigest() == digest
