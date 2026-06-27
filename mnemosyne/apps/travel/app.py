from __future__ import annotations

from mnemosyne.core.fsm import FSMDef, FSMEdge
from mnemosyne.core.models import CommitBatch, PolicyDef, SchemaDef, SolverProfile, TransitionCandidate


class TravelApp:
    app_id = "travel"
    app_version = "1.0"

    def schemas(self):
        return [SchemaDef("travel.transition", "1.0")]

    def fsms(self):
        return [
            FSMDef(
                "ItineraryFSM",
                "1.0",
                "draft",
                (
                    FSMEdge("draft", "flight_held", "hold_flight"),
                    FSMEdge("flight_held", "hotel_held", "hold_hotel"),
                    FSMEdge("hotel_held", "confirmed", "confirm"),
                    FSMEdge("flight_held", "cancelled", "cancel"),
                ),
            )
        ]

    def constraints(self):
        return []

    def policies(self):
        return [PolicyDef("travel.default", "1.0")]

    def compensation_handlers(self):
        return []

    def event_mappers(self):
        return []

    def solver_profiles(self):
        return [SolverProfile("travel.simple", "none")]

    def example_commit_batches(self, tenant_id: str):
        workflow_id = "trip:T001"
        return [
            CommitBatch(
                batch_id="b-tv-1",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                tx_group_id="g-flight",
                candidates=[
                    TransitionCandidate(
                        rid="tv-001",
                        tenant_id=tenant_id,
                        tx_group_id="g-flight",
                        workflow_id=workflow_id,
                        binding_id="binding:T001",
                        eid="itinerary:T001",
                        fsm="ItineraryFSM",
                        state_before="draft",
                        state_after="flight_held",
                        action_type="hold_flight",
                        extension={"attrs_after": {"flight": "UA123", "day": "D"}},
                        app_id=self.app_id,
                        app_version=self.app_version,
                        schema_id="travel.transition",
                    )
                ],
            ),
            CommitBatch(
                batch_id="b-tv-2",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                tx_group_id="g-hotel",
                candidates=[
                    TransitionCandidate(
                        rid="tv-002",
                        tenant_id=tenant_id,
                        tx_group_id="g-hotel",
                        workflow_id=workflow_id,
                        binding_id="binding:T001",
                        eid="itinerary:T001",
                        fsm="ItineraryFSM",
                        state_before="flight_held",
                        state_after="hotel_held",
                        action_type="hold_hotel",
                        dependencies=["tv-001"],
                        extension={"attrs_after": {"hotel": "Kyoto Inn"}},
                        app_id=self.app_id,
                        app_version=self.app_version,
                        schema_id="travel.transition",
                    )
                ],
            ),
        ]
