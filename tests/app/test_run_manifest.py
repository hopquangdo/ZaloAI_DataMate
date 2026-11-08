import json
from pathlib import Path

from datamate.app.run_manifest import build_manifest, code_fingerprint, finish_manifest
from datamate.infrastructure.config import LLMSettings
from datamate.modules.decision.consensus import ConsensusSettings
from datamate.modules.solvers.pandas import AgentSettings


def manifest() -> dict:
    llm = LLMSettings(base_url="http://x/v1", api_key="SECRET-KEY-123", model="m")
    return build_manifest(
        args={"split_dir": Path("d"), "workers": 4},
        llm=llm,
        agent=AgentSettings(),
        consensus=ConsensusSettings(),
        questions=10,
    )


def test_manifest_never_contains_the_api_key() -> None:
    text = json.dumps(finish_manifest(manifest(), {"api": 1}, 9))
    assert "SECRET-KEY-123" not in text and "api_key" not in text


def test_manifest_records_settings_and_result() -> None:
    done = finish_manifest(manifest(), {"api": 1}, 9)
    assert done["llm"]["model"] == "m" and done["consensus"]["samples"] >= 1
    assert done["questions"] == 10 and done["completed"] == 9 and done["errors"] == {"api": 1}
    assert done["args"]["split_dir"] == "d" and "seconds" in done and "_t0" not in done


def test_code_fingerprint_is_stable() -> None:
    assert code_fingerprint() == code_fingerprint() and len(code_fingerprint()) == 12
