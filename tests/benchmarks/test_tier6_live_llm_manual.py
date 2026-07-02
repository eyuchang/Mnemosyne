import importlib.util
import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = REPO_ROOT / "benchmarks" / "realm" / "tier6_live_llm_manual.py"

spec = importlib.util.spec_from_file_location("tier6_live_llm_manual", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


def test_extract_json_object_plain():
    parsed = adapter.extract_json_object('{"predicted_outcome": "ok", "confidence": 0.8}')
    assert parsed["predicted_outcome"] == "ok"
    assert parsed["confidence"] == 0.8


def test_extract_json_object_fenced():
    parsed = adapter.extract_json_object('```json\n{"action": "repair", "should_reject": false}\n```')
    assert parsed["action"] == "repair"
    assert parsed["should_reject"] is False


@pytest.mark.skipif(not os.environ.get("REALM_BENCH_ROOT"), reason="REALM_BENCH_ROOT not set")
def test_export_validate_fixture_pack(tmp_path):
    realm_root = adapter.resolve_realm_root()
    pack_dir = tmp_path / "pack"

    manifest = adapter.export_prompt_pack(
        realm_root=realm_root,
        output_dir=pack_dir,
        config_ids=["E7"],
        subset="pilot",
        max_sequences=1,
    )

    assert manifest["num_prompts"] > 0
    assert (pack_dir / "manifest.json").exists()
    assert (pack_dir / "PROMPT_MANUAL_INSTRUCTIONS.md").exists()

    before = adapter.validate_response_pack(pack_dir)
    assert before["num_missing"] == manifest["num_prompts"]

    fixture = adapter.write_fixture_responses(pack_dir)
    assert fixture["responses_written"] == manifest["num_prompts"]

    after = adapter.validate_response_pack(pack_dir)
    assert after["num_parsed"] == manifest["num_prompts"]
    assert after["num_errors"] == 0
