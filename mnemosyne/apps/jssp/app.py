from __future__ import annotations

from mnemosyne.core.fsm import FSMDef, FSMEdge
from mnemosyne.core.models import CommitBatch, PolicyDef, SchemaDef, SolverProfile, TransitionCandidate


class JSSPApp:
    app_id = "jssp"
    app_version = "1.0"

    def schemas(self):
        return [SchemaDef("jssp.transition", "1.0")]

    def fsms(self):
        return [
            FSMDef(
                "JobOpFSM",
                "1.0",
                "ready",
                (
                    FSMEdge("ready", "scheduled", "schedule"),
                    FSMEdge("scheduled", "running", "start"),
                    FSMEdge("running", "done", "finish"),
                    FSMEdge("scheduled", "scheduled", "reschedule"),
                ),
            )
        ]

    def constraints(self):
        return []

    def policies(self):
        return [PolicyDef("jssp.default", "1.0")]

    def compensation_handlers(self):
        return []

    def event_mappers(self):
        return []

    def solver_profiles(self):
        return [SolverProfile("jssp.cp_sat", "ortools-cp-sat")]

    def example_commit_batches(self, tenant_id: str):
        workflow_id = "jssp:demo"
        return [
            CommitBatch(
                batch_id="b-js-1",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                tx_group_id="g-op1",
                candidates=[
                    TransitionCandidate(
                        rid="js-001",
                        tenant_id=tenant_id,
                        tx_group_id="g-op1",
                        workflow_id=workflow_id,
                        binding_id="binding:jssp-demo",
                        eid="job:J1:op:1",
                        fsm="JobOpFSM",
                        state_before="ready",
                        state_after="scheduled",
                        action_type="schedule",
                        extension={"attrs_after": {"machine": "M1", "start": 0, "duration": 3}},
                        app_id=self.app_id,
                        app_version=self.app_version,
                        schema_id="jssp.transition",
                    )
                ],
            )
        ]
