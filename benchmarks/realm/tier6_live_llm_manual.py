"""Manual live-LLM proposal injection for REALM-Bench Tier 6.

The LLM generates proposal text. Mnemosyne owns admission. REALM owns scoring.

This first R83.5a step exports prompts and validates pasted JSON responses.
It intentionally does not yet emit kernel traces, avoiding nondeterministic
events.jsonl churn during prompt-protocol development.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.realm.tier6_mnemosyne_adapter import (  # noqa: E402
    CONFIGS,
    load_realm_support,
    resolve_realm_root,
)


ADAPTER_ID = "tier6-live-llm-manual-adapter-v0"
PACK_VERSION = "tier6-live-llm-manual-pack-v0"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_id(value: str) -> str:
    return value.replace("/", "_").replace(":", "_").replace(" ", "_").replace(".", "_")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty LLM response")

    if "```" in stripped:
        parts = stripped.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return json.loads(candidate)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("could not find JSON object in LLM response")
    return json.loads(stripped[start : end + 1])


def prompt_key(config_id: str, sequence_id: str, episode_id: int) -> str:
    return f"{safe_id(config_id)}__{safe_id(sequence_id)}__e{episode_id:02d}"


def load_sequences_for_pack(
    *,
    realm_root: Path,
    subset: str = "pilot",
    max_sequences: int = 1,
) -> list[dict[str, Any]]:
    generator, _ = load_realm_support(realm_root)
    development = generator.generate_development_sequences(realm_root)

    if subset == "development":
        return development[:max_sequences]

    if subset != "pilot":
        raise ValueError(f"unknown subset: {subset}")

    pilot_path = realm_root / "datasets" / "T6" / "pilot_subset_v0.json"
    if pilot_path.exists():
        payload = load_json(pilot_path)
        sequence_ids: set[str] = set()

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "sequence_id" and isinstance(item, str):
                        sequence_ids.add(item)
                    else:
                        walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(payload)
        selected = [seq for seq in development if seq.get("sequence_id") in sequence_ids]
        if selected:
            return selected[:max_sequences]

    jobshop = [
        seq for seq in development
        if seq.get("base_instance", {}).get("family") == "jobshop_breakdown"
    ]
    return (jobshop or development)[:max_sequences]


def build_prompt(
    *,
    config_id: str,
    sequence: dict[str, Any],
    episode: dict[str, Any],
    visible_history: list[dict[str, Any]],
) -> str:
    public_episode = {
        "sequence_id": sequence["sequence_id"],
        "episode_id": episode["episode_id"],
        "family": episode["family"],
        "base_instance_id": episode["base_instance_id"],
        "source_path": episode["source_path"],
        "is_control_sequence": sequence["is_control_sequence"],
        "config_id": config_id,
        "condition_switches": CONFIGS[config_id],
    }

    instructions = {
        "role": "You are a planning/recovery LLM proposing the next action for a REALM-Bench Tier-6 episode.",
        "critical_rule": "Use only the visible episode and history.",
        "hidden_from_you": [
            "ground-truth failure_signature",
            "scorer labels",
            "future observed outcome",
            "answer key",
        ],
        "output_requirement": "Return one JSON object only.",
        "json_schema": {
            "proposal_summary": "short proposal",
            "predicted_outcome": "expected outcome if proposal is used",
            "action": "specific action, repair, observation, or rejection recommendation",
            "should_reject": "boolean",
            "risk_factors": ["visible risks"],
            "evidence_to_preserve": ["facts/evidence not to destroy"],
            "horizon_rationale": "why this is good or bad over later episodes",
            "confidence": "number between 0 and 1",
        },
    }

    return (
        "# REALM-Bench Tier 6 Manual LLM Prompt\n\n"
        "You generate a proposal. Mnemosyne, not you, owns final admission.\n\n"
        "## Public episode\n\n"
        f"{json.dumps(public_episode, indent=2, sort_keys=True)}\n\n"
        "## Visible prior history\n\n"
        f"{json.dumps(visible_history, indent=2, sort_keys=True)}\n\n"
        "## Instructions\n\n"
        f"{json.dumps(instructions, indent=2, sort_keys=True)}\n\n"
        "Return JSON only.\n"
    )


def export_prompt_pack(
    *,
    realm_root: Path,
    output_dir: Path,
    config_ids: Iterable[str],
    subset: str = "pilot",
    max_sequences: int = 1,
) -> dict[str, Any]:
    sequences = load_sequences_for_pack(
        realm_root=realm_root,
        subset=subset,
        max_sequences=max_sequences,
    )

    prompts_dir = output_dir / "prompts"
    responses_dir = output_dir / "responses"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for config_id in config_ids:
        if config_id not in CONFIGS:
            raise ValueError(f"unknown config_id: {config_id}")

        for sequence in sequences:
            visible_history: list[dict[str, Any]] = []
            for episode in sequence["episodes"]:
                key = prompt_key(config_id, sequence["sequence_id"], episode["episode_id"])
                prompt_text = build_prompt(
                    config_id=config_id,
                    sequence=sequence,
                    episode=episode,
                    visible_history=visible_history,
                )

                prompt_path = prompts_dir / config_id / f"{key}.md"
                response_path = responses_dir / config_id / f"{key}.txt"
                prompt_path.parent.mkdir(parents=True, exist_ok=True)
                response_path.parent.mkdir(parents=True, exist_ok=True)

                prompt_path.write_text(prompt_text, encoding="utf-8")
                if not response_path.exists():
                    response_path.write_text(
                        "Paste one JSON LLM response here.\n",
                        encoding="utf-8",
                    )

                entries.append({
                    "key": key,
                    "config_id": config_id,
                    "sequence_id": sequence["sequence_id"],
                    "episode_id": episode["episode_id"],
                    "prompt_path": str(prompt_path.relative_to(output_dir)),
                    "response_path": str(response_path.relative_to(output_dir)),
                    "prompt_sha256": sha256_text(prompt_text),
                })

                visible_history.append({
                    "episode_id": episode["episode_id"],
                    "visible_status": "previous prompt emitted",
                })

    manifest = {
        "pack_version": PACK_VERSION,
        "adapter_id": ADAPTER_ID,
        "mode": "manual_live_llm_proposal_injection",
        "claim_status": "manual_live_llm_proposal_behavior_not_confirmatory",
        "realm_root": str(realm_root),
        "subset": subset,
        "max_sequences": max_sequences,
        "config_ids": list(config_ids),
        "num_sequences": len(sequences),
        "num_prompts": len(entries),
        "sequence_ids": [seq["sequence_id"] for seq in sequences],
        "entries": entries,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "PROMPT_MANUAL_INSTRUCTIONS.md").write_text(
        "# Manual LLM Injection Instructions\n\n"
        "1. Open each file under prompts/.\n"
        "2. Paste it into the LLM being tested.\n"
        "3. Copy the LLM JSON answer into the matching file under responses/.\n"
        "4. Do not expose hidden failure signatures or scorer labels.\n"
        "5. Run the validator after responses are filled.\n\n"
        "The LLM generates proposals. Mnemosyne owns admission. REALM owns scoring.\n",
        encoding="utf-8",
    )
    return manifest


def validate_response_pack(pack_dir: Path) -> dict[str, Any]:
    manifest = load_json(pack_dir / "manifest.json")
    parsed = []
    missing = []
    errors = []

    for entry in manifest["entries"]:
        response_path = pack_dir / entry["response_path"]
        raw = response_path.read_text(encoding="utf-8")
        if "Paste one JSON LLM response here" in raw:
            missing.append(entry["key"])
            continue
        try:
            obj = extract_json_object(raw)
            parsed.append({
                "key": entry["key"],
                "response_sha256": sha256_text(raw),
                "fields": sorted(obj.keys()),
            })
        except Exception as exc:
            errors.append({"key": entry["key"], "error": str(exc)})

    return {
        "pack_dir": str(pack_dir),
        "num_entries": len(manifest["entries"]),
        "num_parsed": len(parsed),
        "num_missing": len(missing),
        "num_errors": len(errors),
        "missing": missing,
        "errors": errors,
        "parsed": parsed,
    }


def write_fixture_responses(pack_dir: Path) -> dict[str, Any]:
    manifest = load_json(pack_dir / "manifest.json")
    count = 0
    for entry in manifest["entries"]:
        response_path = pack_dir / entry["response_path"]
        fixture = {
            "proposal_summary": f"Fixture proposal for {entry['key']}.",
            "predicted_outcome": "fixture predicted outcome",
            "action": "preserve evidence and avoid unsafe dependent changes",
            "should_reject": False,
            "risk_factors": ["visible uncertainty"],
            "evidence_to_preserve": ["prior observation", "current constraints"],
            "horizon_rationale": "prefer an action that remains safe in later episodes",
            "confidence": 0.5,
        }
        response_path.write_text(
            json.dumps(fixture, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        count += 1
    return {"responses_written": count, "pack_dir": str(pack_dir)}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    export_p = sub.add_parser("export")
    export_p.add_argument("--realm-root", default=os.environ.get("REALM_BENCH_ROOT"))
    export_p.add_argument("--output-dir", default="results/realm_tier6_live_llm_manual/prompt_pack_v0")
    export_p.add_argument("--configs", nargs="+", default=["E7"])
    export_p.add_argument("--subset", choices=["pilot", "development"], default="pilot")
    export_p.add_argument("--max-sequences", type=int, default=1)

    validate_p = sub.add_parser("validate-responses")
    validate_p.add_argument("--pack-dir", default="results/realm_tier6_live_llm_manual/prompt_pack_v0")

    fixture_p = sub.add_parser("write-fixture-responses")
    fixture_p.add_argument("--pack-dir", default="results/realm_tier6_live_llm_manual/prompt_pack_v0")

    args = parser.parse_args()

    if args.command == "export":
        realm_root = resolve_realm_root(args.realm_root)
        result = export_prompt_pack(
            realm_root=realm_root,
            output_dir=Path(args.output_dir),
            config_ids=args.configs,
            subset=args.subset,
            max_sequences=args.max_sequences,
        )
        print(json.dumps({
            "pack_dir": args.output_dir,
            "num_prompts": result["num_prompts"],
            "config_ids": result["config_ids"],
            "sequence_ids": result["sequence_ids"],
        }, indent=2, sort_keys=True))
        return

    if args.command == "validate-responses":
        print(json.dumps(validate_response_pack(Path(args.pack_dir)), indent=2, sort_keys=True))
        return

    if args.command == "write-fixture-responses":
        print(json.dumps(write_fixture_responses(Path(args.pack_dir)), indent=2, sort_keys=True))
        return


if __name__ == "__main__":
    main()
