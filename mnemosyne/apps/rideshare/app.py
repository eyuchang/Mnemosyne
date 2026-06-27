from __future__ import annotations

from mnemosyne.apps.common import ConstraintDef
from mnemosyne.core.fsm import FSMDef, FSMEdge
from mnemosyne.core.models import CommitBatch, ConstraintResult, PolicyDef, SchemaDef, SolverProfile, TransitionCandidate


async def passenger_pickup_requires_driver_arrived(candidate, store):
    driver_eid = candidate.extension.get("driver_eid")
    if not driver_eid:
        return ConstraintResult.fail("DRIVER_EID_MISSING")
    driver_state = await store.get_state_view(candidate.tenant_id, driver_eid, "DriverFSM")
    if driver_state.state != "arrived":
        return ConstraintResult.fail("DRIVER_NOT_ARRIVED", {"driver_state": driver_state.state})
    if candidate.extension.get("passenger_location") != candidate.extension.get("driver_location"):
        return ConstraintResult.fail("NOT_CO_LOCATED")
    return ConstraintResult.pass_()


class RideshareApp:
    app_id = "rideshare"
    app_version = "1.0"

    def schemas(self):
        return [SchemaDef("rideshare.transition", "1.0")]

    def fsms(self):
        return [
            FSMDef(
                "PassengerFSM",
                "1.0",
                "ordered",
                (
                    FSMEdge("ordered", "waiting", "wait"),
                    FSMEdge("waiting", "picked_up", "pickup"),
                    FSMEdge("picked_up", "dropped_off", "dropoff"),
                    FSMEdge("waiting", "cancelled", "cancel"),
                ),
            ),
            FSMDef(
                "DriverFSM",
                "1.0",
                "idle",
                (
                    FSMEdge("idle", "bid", "bid"),
                    FSMEdge("bid", "accepted", "accept"),
                    FSMEdge("accepted", "arrived", "arrive"),
                    FSMEdge("arrived", "picked_up", "pickup"),
                    FSMEdge("picked_up", "driving", "drive"),
                    FSMEdge("driving", "completed", "complete"),
                ),
            ),
            FSMDef(
                "RideFSM",
                "1.0",
                "requested",
                (
                    FSMEdge("requested", "assigned", "assign"),
                    FSMEdge("assigned", "pickup_ready", "ready"),
                    FSMEdge("pickup_ready", "in_progress", "start"),
                    FSMEdge("in_progress", "in_progress", "reroute"),
                    FSMEdge("in_progress", "completed", "complete"),
                    FSMEdge("pickup_ready", "cancelled", "cancel"),
                ),
            ),
        ]

    def constraints(self):
        return [ConstraintDef("PassengerFSM", "pickup", passenger_pickup_requires_driver_arrived)]

    def policies(self):
        return [PolicyDef("rideshare.default", "1.0")]

    def compensation_handlers(self):
        return []

    def event_mappers(self):
        return []

    def solver_profiles(self):
        return [SolverProfile("rideshare.urs", "ortools-routing")]

    def example_commit_batches(self, tenant_id: str):
        workflow_id = "ride:R001"
        binding_id = "binding:R001"
        return [
            CommitBatch(
                batch_id="b-rs-1",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                tx_group_id="g-assign",
                candidates=[
                    TransitionCandidate(
                        rid="rs-001",
                        tenant_id=tenant_id,
                        tx_group_id="g-assign",
                        workflow_id=workflow_id,
                        binding_id=binding_id,
                        eid="ride:R001",
                        fsm="RideFSM",
                        state_before="requested",
                        state_after="assigned",
                        action_type="assign",
                        app_id=self.app_id,
                        app_version=self.app_version,
                        schema_id="rideshare.transition",
                    ),
                    TransitionCandidate(
                        rid="rs-002",
                        tenant_id=tenant_id,
                        tx_group_id="g-assign",
                        workflow_id=workflow_id,
                        binding_id=binding_id,
                        eid="driver:Joe",
                        fsm="DriverFSM",
                        state_before="idle",
                        state_after="bid",
                        action_type="bid",
                        app_id=self.app_id,
                        app_version=self.app_version,
                        schema_id="rideshare.transition",
                    ),
                ],
            ),
            CommitBatch(
                batch_id="b-rs-2",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                tx_group_id="g-accept",
                candidates=[
                    TransitionCandidate(
                        rid="rs-003",
                        tenant_id=tenant_id,
                        tx_group_id="g-accept",
                        workflow_id=workflow_id,
                        binding_id=binding_id,
                        eid="driver:Joe",
                        fsm="DriverFSM",
                        state_before="bid",
                        state_after="accepted",
                        action_type="accept",
                        dependencies=["rs-001", "rs-002"],
                        app_id=self.app_id,
                        app_version=self.app_version,
                        schema_id="rideshare.transition",
                    ),
                ],
            ),
            CommitBatch(
                batch_id="b-rs-3",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                tx_group_id="g-arrive",
                candidates=[
                    TransitionCandidate(
                        rid="rs-004",
                        tenant_id=tenant_id,
                        tx_group_id="g-arrive",
                        workflow_id=workflow_id,
                        binding_id=binding_id,
                        eid="driver:Joe",
                        fsm="DriverFSM",
                        state_before="accepted",
                        state_after="arrived",
                        action_type="arrive",
                        dependencies=["rs-003"],
                        extension={"attrs_after": {"location": "pickup"}},
                        app_id=self.app_id,
                        app_version=self.app_version,
                        schema_id="rideshare.transition",
                    ),
                ],
            ),
            CommitBatch(
                batch_id="b-rs-4",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                tx_group_id="g-pickup",
                candidates=[
                    TransitionCandidate(
                        rid="rs-005",
                        tenant_id=tenant_id,
                        tx_group_id="g-pickup",
                        workflow_id=workflow_id,
                        binding_id=binding_id,
                        eid="passenger:Mary",
                        fsm="PassengerFSM",
                        state_before="ordered",
                        state_after="waiting",
                        action_type="wait",
                        dependencies=["rs-001"],
                        extension={"attrs_after": {"location": "pickup"}},
                        app_id=self.app_id,
                        app_version=self.app_version,
                        schema_id="rideshare.transition",
                    ),
                ],
            ),
            CommitBatch(
                batch_id="b-rs-4",
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                tx_group_id="g-pickup",
                candidates=[
                    TransitionCandidate(
                        rid="rs-006",
                        tenant_id=tenant_id,
                        tx_group_id="g-pickup",
                        workflow_id=workflow_id,
                        binding_id=binding_id,
                        eid="passenger:Mary",
                        fsm="PassengerFSM",
                        state_before="waiting",
                        state_after="picked_up",
                        action_type="pickup",
                        dependencies=["rs-004", "rs-005"],
                        extension={
                            "driver_eid": "driver:Joe",
                            "passenger_location": "pickup",
                            "driver_location": "pickup",
                        },
                        app_id=self.app_id,
                        app_version=self.app_version,
                        schema_id="rideshare.transition",
                    ),
                ],
            ),
        ]
