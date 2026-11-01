"""CI Orchestra Oracle: restricted, deterministic pipeline templates.

Input is JSON (valid YAML 1.2 subset) or YAML with PyYAML installed.
Only named step IDs are supported: no arbitrary shell, Groovy, or K8s templates.
Generation never claims a job ran, a signature exists, or a target is deployed.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

class OracleRejected(ValueError): pass

STEP_COMMANDS = {
    "compile": "python -m compileall -q core proof integrations",
    "frontier_tests": "python -m unittest discover -s tests -p 'test_frontier_evidence.py' -v",
    "receipt_tests": "python -m unittest discover -s tests -p 'test_pop_inference_print.py' -v",
    "ci_tests": "python -m unittest discover -s tests -p 'test_ci_oracle.py' -v",
    "sign_gate": "python -m integrations.ci_sign_gate",
}
DEFAULT_STEPS = ["compile", "frontier_tests", "receipt_tests", "ci_tests", "sign_gate"]
VALID_ID = re.compile(r"^[a-z][a-z0-9_-]{0,40}$")

def parse_intent(value: str) -> dict:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        try:
            import yaml
        except ImportError:
            raise OracleRejected("YAML needs PyYAML; JSON is supported without dependencies") from None
        data = yaml.safe_load(value)
    if not isinstance(data, dict) or set(data) - {"project", "steps"}:
        raise OracleRejected("Invalid intent object")
    project = data.get("project")
    steps = data.get("steps")
    if not isinstance(project, str) or not VALID_ID.fullmatch(project):
        raise OracleRejected("Invalid project identifier")
    if not isinstance(steps, list) or not steps or len(steps) > 12:
        raise OracleRejected("Missing or oversized step list")
    if any(not isinstance(s, str) or s not in STEP_COMMANDS for s in steps):
        raise OracleRejected("Unknown or unsafe step")
    if len(set(steps)) != len(steps):
        raise OracleRejected("Duplicate steps")
    if steps[-1] != "sign_gate":
        raise OracleRejected("Final signing and verification gate required")
    return {"project": project, "steps": steps}

def translate(intent: dict, engine: str) -> str:
    validated = parse_intent(json.dumps(intent))
    commands = [STEP_COMMANDS[s] for s in validated["steps"]]
    if engine == "woodpecker":
        # Modern Woodpecker syntax uses 'steps', not deprecated 'pipeline'.
        doc = {"steps": [{"name": s, "image": "python:3.12-slim",
                  "commands": [STEP_COMMANDS[s]]} for s in validated["steps"]]}
        return json.dumps(doc, indent=2) + "\n"  # JSON is valid YAML
    if engine == "bitbucket":
        doc = {"image": "python:3.12-slim", "pipelines": {"custom": {
            "verified-evidence": [{"step": {"name": "PoP evidence verification",
              "script": ["python -m pip install -r requirements.txt"] + commands}}]}}}
        return json.dumps(doc, indent=2) + "\n"
    if engine == "jenkins":
        # Commands come exclusively from the predefined allowlist.
        stages = "\n".join(
            "    stage('" + s + "') { steps { sh '" + STEP_COMMANDS[s] + "' } }"
            for s in validated["steps"])
        return "pipeline {\n  agent any\n  stages {\n" + stages + "\n  }\n}\n"
    raise OracleRejected("Unsupported engine")

def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--intent", required=True, type=Path)
    p.add_argument("--engine", required=True, choices=["bitbucket", "woodpecker", "jenkins"])
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    data = parse_intent(a.intent.read_text(encoding="utf-8"))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(translate(data, a.engine), encoding="utf-8")
    print("GENERATED_ONLY: " + str(a.output))

if __name__ == "__main__": main()
