from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REALM_CASE_FIXTURE = Path(__file__).resolve().parents[1] / "cases" / "realm_bench_cases.json"


@dataclass(frozen=True)
class REALMBenchCaseStore:
    path: Path
    data: dict[str, Any]

    @property
    def cases(self) -> list[dict[str, Any]]:
        return list(self.data["cases"])

    @property
    def case_ids(self) -> list[str]:
        return [case["case_id"] for case in self.cases]

    def by_id(self, case_id: str) -> dict[str, Any]:
        for case in self.cases:
            if case["case_id"] == case_id:
                return case
        raise KeyError(case_id)

    def by_family(self, family: str) -> list[dict[str, Any]]:
        return [
            case
            for case in self.cases
            if case.get("family") == family
        ]

    def by_mode(self, mode: str) -> list[dict[str, Any]]:
        return [
            case
            for case in self.cases
            if case.get("mode") == mode
        ]

    def dynamic_cases(self) -> list[dict[str, Any]]:
        return [
            case
            for case in self.cases
            if case.get("mode") == "dynamic"
        ]

    def thanksgiving_cases(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.by_id("P6"), self.by_id("P9")


def load_realm_bench_cases(path: Path = REALM_CASE_FIXTURE) -> REALMBenchCaseStore:
    return REALMBenchCaseStore(
        path=path,
        data=json.loads(path.read_text(encoding="utf-8")),
    )
