from __future__ import annotations

import importlib
import inspect
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REALM_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ThanksgivingAPIBindingSurfaceResult:
    output_root: Path
    files: dict[str, Path]
    module_count: int
    available_module_count: int
    callable_count: int


TARGET_MODULES = [
    "mnemosyne.api.commitments",
    "mnemosyne.api.recovery",
    "mnemosyne.api.proposal_packages",
    "mnemosyne.api.audit",
    "mnemosyne.benchmarks.jssp_disruption_commitments",
    "mnemosyne.benchmarks.jssp_recovery_proposals",
    "mnemosyne.benchmarks.jssp_repair_admission",
]


def _public_callables(module: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, value in sorted(vars(module).items()):
        if name.startswith("_"):
            continue
        if not callable(value):
            continue

        try:
            signature = str(inspect.signature(value))
            signature = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", signature)
        except (TypeError, ValueError):
            signature = "<unavailable>"

        rows.append(
            {
                "name": name,
                "kind": type(value).__name__,
                "signature": signature,
            }
        )
    return rows


def build_surface_report() -> dict[str, Any]:
    modules: list[dict[str, Any]] = []

    for module_name in TARGET_MODULES:
        try:
            module = importlib.import_module(module_name)
            available = True
            error = None
            callables = _public_callables(module)
        except Exception as exc:  # pragma: no cover - diagnostic path
            available = False
            error = repr(exc)
            callables = []

        modules.append(
            {
                "module": module_name,
                "available": available,
                "error": error,
                "public_callables": callables,
            }
        )

    return {
        "schema_version": "thanksgiving_api_binding_surface.v1",
        "purpose": "Identify the real Mnemosyne APIs available for R6.7 Thanksgiving recovery binding.",
        "modules": modules,
        "summary": {
            "module_count": len(modules),
            "available_module_count": sum(1 for module in modules if module["available"]),
            "callable_count": sum(len(module["public_callables"]) for module in modules),
        },
        "next_step": "Use this inspected surface to build the API-backed Thanksgiving recovery package.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# Thanksgiving API Binding Surface Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Module count: {report['summary']['module_count']}")
    lines.append(f"- Available modules: {report['summary']['available_module_count']}")
    lines.append(f"- Public callables: {report['summary']['callable_count']}")
    lines.append("")
    lines.append("## Modules")
    lines.append("")

    for module in report["modules"]:
        lines.append(f"### `{module['module']}`")
        lines.append("")
        lines.append(f"- Available: {module['available']}")
        if module["error"]:
            lines.append(f"- Error: `{module['error']}`")
        lines.append("")
        if module["public_callables"]:
            lines.append("| Callable | Kind | Signature |")
            lines.append("|---|---|---|")
            for item in module["public_callables"]:
                lines.append(
                    f"| `{item['name']}` | {item['kind']} | `{item['signature']}` |"
                )
        else:
            lines.append("No public callables found.")
        lines.append("")

    lines.append("## Next Step")
    lines.append("")
    lines.append(report["next_step"])
    lines.append("")

    return "\n".join(lines)


def run_surface_report(
    output_root: str | Path | None = None,
) -> ThanksgivingAPIBindingSurfaceResult:
    root = Path(output_root) if output_root is not None else REALM_ROOT
    report = build_surface_report()

    files = {
        "json": root / "reports" / "thanksgiving_api_binding_surface.json",
        "markdown": root / "reports" / "thanksgiving_api_binding_surface.md",
    }

    files["json"].parent.mkdir(parents=True, exist_ok=True)
    files["json"].write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    files["markdown"].write_text(
        render_markdown(report) + "\n",
        encoding="utf-8",
    )

    return ThanksgivingAPIBindingSurfaceResult(
        output_root=root,
        files=files,
        module_count=report["summary"]["module_count"],
        available_module_count=report["summary"]["available_module_count"],
        callable_count=report["summary"]["callable_count"],
    )


def main() -> None:
    result = run_surface_report()
    print("R6.7 Thanksgiving API binding surface")
    print(f"output_root: {result.output_root}")
    print(f"module_count: {result.module_count}")
    print(f"available_module_count: {result.available_module_count}")
    print(f"callable_count: {result.callable_count}")
    for name, path in sorted(result.files.items()):
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
