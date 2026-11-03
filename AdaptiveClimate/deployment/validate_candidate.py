"""Read-only configuration safety comparison, using public dummy credentials.

Creates isolated configuration files under an ignored validation directory.
Never changes the user's secrets, connects to a device, or uploads firmware.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "AdaptiveClimate/deployment"
CONTROL_DOMAINS = ("climate", "opentherm", "output", "switch", "sensor", "binary_sensor",
                   "button", "script", "interval", "globals", "wifi", "api", "esp32", "ota", "logger")
NEW_OBSERVER_KEYS = {"model_record", "shadow_model", "shadow_record", "shadow_forecasts", "input_record",
                     "runtime_record", "pid_tick_source", "writer_tick_source"}


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor("!lambda", lambda loader, node: loader.construct_scalar(node))
Loader.add_constructor("!secret", lambda loader, node: "!secret " + loader.construct_scalar(node))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def compare(reference, candidate):
    controls = {}
    for key in CONTROL_DOMAINS:
        if reference.get(key) != candidate.get(key):
            raise ValueError(f"Control domain differs: {key}")
        controls[key] = digest(reference.get(key))
    a, b = reference["adaptive_climate"], candidate["adaptive_climate"]
    if len(a) != 2 or len(b) != 2:
        raise ValueError("Exactly two original observers required")
    diagnostic_ids = set()
    for original, shadow in zip(a, b):
        filtered = {k: v for k, v in shadow.items() if k not in NEW_OBSERVER_KEYS}
        if original != filtered:
            raise ValueError(f"Original observer differs: {original['id']}")
        if not shadow.get("shadow_model"):
            raise ValueError("Both shadows must be enabled")
        for key in ("model_record", "shadow_record", "shadow_forecasts", "input_record", "runtime_record"):
            if entity_id := shadow[key].get("id"):
                diagnostic_ids.add(entity_id)
        for key in ("prediction_15min", "prediction_30min", "prediction_60min"):
            diagnostic_ids.add(original[key]["id"])
    for key in CONTROL_DOMAINS:
        text = yaml.safe_dump(candidate.get(key), allow_unicode=True)
        for entity in diagnostic_ids:
            if f"id({entity})" in text or f"id: {entity}\n" in text or f"sensor: {entity}\n" in text:
                raise ValueError(f"Diagnostic feeds control domain {key}: {entity}")
    return dict(control_domain_sha256=controls, original_observers_identical=True,
                diagnostics_feed_heating=False, observers=[x["id"] for x in a])


def prepare(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "secrets.yaml").write_bytes((DEPLOY / "secrets.compile-only.yaml").read_bytes())
    configs = []
    for name in ("thermostaat.yaml", "thermostaat_shadow.yaml"):
        text = (DEPLOY / name).read_text(encoding="utf-8")
        text = text.replace("path: ../components", "path: " + (ROOT / "AdaptiveClimate/components").as_posix())
        path = output_dir / name
        path.write_text(text, encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "esphome", "config", str(path)],
                                capture_output=True, text=True, encoding="utf-8",
                                env={**os.environ, "PYTHONUTF8": "1"}, timeout=180)
        if result.returncode:
            raise RuntimeError(result.stderr + result.stdout)
        configs.append(yaml.load(result.stdout, Loader=Loader))
    report = compare(*configs)
    source = configs[1]["external_components"][0]["source"]
    expected_instrumentation = "e8411b9814bc7b7d8333be3c37ea188188d8ca93"
    if (source.get("type") != "git" or source.get("ref") != expected_instrumentation or
            source.get("url") != "https://github.com/S1146468/ESPHome-Packages" or
            source.get("path") != "AdaptiveClimate/components"):
        raise ValueError("Instrumentation source is not the approved immutable pin")
    seal = json.loads((DEPLOY / "learner_freeze.json").read_text(encoding="utf-8"))
    for name, expected in seal["sha256_normalized_utf8"].items():
        actual = hashlib.sha256((ROOT / "AdaptiveClimate/components/adaptive_climate" / name).read_text(encoding="utf-8").encode()).hexdigest()
        if expected != actual:
            raise ValueError(f"Learner changed: {name}")
    report["unchanged_learners"] = seal
    report["control_package"] = "7d925a7eccb6747a0ce5dbbcc0007c6fdf1bafc0"
    report["observer_package"] = "a7c299c4684b3cf7405bf04f37d721a3fba3eac8"
    report["instrumentation_source"] = source["ref"]
    report["framework"] = configs[1]["esp32"]["framework"]["version"]
    report["source_commit_at_check"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report["working_tree_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    (output_dir / "control_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".build/shadow-install-validation")
    args = parser.parse_args()
    report = prepare(args.output_dir.resolve())
    print("PASS: two unchanged observers, unchanged heating/control domains, frozen learners, read-only diagnostics")
    print("Evidence:", args.output_dir.resolve() / "control_validation.json")
