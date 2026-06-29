from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
import sys
import time
import uuid
from typing import Any

from mnemosyne.service.config import ServiceConfig, service_config_from_env
from mnemosyne.service.metrics import ServiceMetrics
from mnemosyne.service.schemas import ProposalDecision, ProposalRequest


@dataclass
class R8DeploymentService:
    """Deployment-facing ATP service boundary.

    R8 is a deployment layer. It must preserve the ATP authority rule:
    service clients may submit proposal packages, but this layer must not expose
    a direct committed-truth write API.

    This first R8 implementation provides a dependency-light local service
    boundary and metrics. It is intentionally conservative: all domain mutation
    is represented as an admitted proposal decision.
    """

    metrics: ServiceMetrics = field(default_factory=ServiceMetrics)
    committed: dict[str, ProposalRequest] = field(default_factory=dict)
    rejected: list[dict[str, Any]] = field(default_factory=list)

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "service": "mnemosyne-r8-deployment-service",
            "mode": "local",
            "authority_boundary": "proposal_admission_only",
        }

    def submit_proposal(self, req: ProposalRequest) -> ProposalDecision:
        self.metrics.inc("mnemosyne_service_proposals_total")

        with self.metrics.time_ms("mnemosyne_service_admission_latency_ms"):
            decision = self._admit(req)

        if decision.accepted:
            self.metrics.inc("mnemosyne_service_admitted_total")
            if decision.committed_record_id is not None:
                self.committed[decision.committed_record_id] = req
        else:
            self.metrics.inc("mnemosyne_service_rejected_total")
            self.rejected.append(
                {
                    "tenant": req.tenant,
                    "workflow": req.workflow,
                    "entity": req.entity,
                    "operation": req.operation,
                    "reason": decision.reason,
                }
            )

        return decision

    def state(self, tenant: str, entity: str) -> dict[str, Any]:
        # Minimal effective-state projection for the service boundary.
        records = [
            {
                "record_id": rid,
                "workflow": req.workflow,
                "operation": req.operation,
                "payload": dict(req.payload),
            }
            for rid, req in self.committed.items()
            if req.tenant == tenant and req.entity == entity
        ]
        return {
            "tenant": tenant,
            "entity": entity,
            "effective_record_count": len(records),
            "records": records,
        }

    def _admit(self, req: ProposalRequest) -> ProposalDecision:
        """Deterministic local C for R8 service smoke/deployment tests.

        This is not a new ATP semantics layer; it is the service's deployment
        boundary. The rule intentionally rejects common bypass attempts:
        direct mutation flags, explicit bypass requests, malformed payloads,
        and proposals marked invalid by a test/workload generator.
        """
        payload = dict(req.payload)

        if payload.get("bypass_admission") is True:
            return ProposalDecision(False, "rejected", "bypass_admission_requested")

        if payload.get("direct_commit") is True:
            return ProposalDecision(False, "rejected", "direct_commit_forbidden")

        if payload.get("valid_under_c") is False:
            return ProposalDecision(False, "rejected", "constraint_violation")

        if req.operation.lower() in {"direct_write", "raw_append", "bypass_commit"}:
            return ProposalDecision(False, "rejected", "operation_not_admissible")

        record_id = f"r8-{uuid.uuid4().hex}"
        return ProposalDecision(True, "admitted", "accepted_under_service_c", record_id)


SERVICE = R8DeploymentService()


def make_handler(service: R8DeploymentService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "MnemosyneR8Service/0.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("[mnemosyne-r8] " + fmt % args + "\n")

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send_json(200, service.health())
                return

            if self.path == "/metrics":
                body = service.metrics.render_prometheus().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path.startswith("/state/"):
                parts = self.path.strip("/").split("/")
                if len(parts) != 3:
                    self._send_json(404, {"error": "expected /state/{tenant}/{entity}"})
                    return
                _, tenant, entity = parts
                self._send_json(200, service.state(tenant, entity))
                return

            self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/proposals":
                self._send_json(404, {"error": "not found"})
                return

            try:
                data = self._read_json()
                req = ProposalRequest.from_json(data)
                decision = service.submit_proposal(req)
                self._send_json(200, decision.to_json())
            except ValueError as exc:
                service.metrics.inc("mnemosyne_service_malformed_total")
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:
                service.metrics.inc("mnemosyne_service_errors_total")
                self._send_json(500, {"error": type(exc).__name__, "message": str(exc)})

        def _read_json(self) -> dict[str, Any]:
            raw_len = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_len)
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            body = self.rfile.read(length)
            if not body:
                return {}
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON body must be an object")
            return data

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def run_server(config: ServiceConfig | None = None) -> None:
    config = config or service_config_from_env()
    server = ThreadingHTTPServer(config.bind, make_handler(SERVICE))
    print(f"Mnemosyne R8 service listening on http://{config.host}:{config.port}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    env_config = service_config_from_env()

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=env_config.host)
    parser.add_argument("--port", type=int, default=env_config.port)
    args = parser.parse_args(argv)

    run_server(ServiceConfig(host=args.host, port=args.port, mode=env_config.mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
