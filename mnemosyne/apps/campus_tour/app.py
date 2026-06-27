# File: mnemosyne/apps/campus_tour/app.py
#
# Purpose:
#   Minimal Campus Tour app used for REALM-Bench P1A fixture replay.
#
# Stage:
#   Stage 1.6R-P1A introduces a P1-compatible campus-tour FSM.
#
# Note:
#   This app supports replaying a canonical oracle trace.
#   It is not yet a route optimizer or planner.

from __future__ import annotations

from mnemosyne.core.fsm import FSMDef, FSMEdge
from mnemosyne.core.models import PolicyDef, SchemaDef, SolverProfile


class CampusTourApp:
    app_id = "campus_tour"
    app_version = "1.0"

    def schemas(self):
        return [SchemaDef("campus_tour.transition", "1.0")]

    def fsms(self):
        return [
            FSMDef(
                "CampusTourFSM",
                "1.0",
                "not_started",
                (
                    FSMEdge("not_started", "visited_dorm", "visit_dorm"),
                    FSMEdge("visited_dorm", "visited_auditorium", "visit_auditorium"),
                    FSMEdge("visited_auditorium", "visited_lab", "visit_lab"),
                    FSMEdge("visited_lab", "visited_library", "visit_library"),
                    FSMEdge("visited_library", "completed", "return_to_student_center"),
                ),
            )
        ]

    def constraints(self):
        return []

    def policies(self):
        return [PolicyDef("campus_tour.default", "1.0")]

    def compensation_handlers(self):
        return []

    def event_mappers(self):
        return []

    def solver_profiles(self):
        return [SolverProfile("campus_tour.oracle_trace", "none")]

    def example_commit_batches(self, tenant_id: str):
        return []