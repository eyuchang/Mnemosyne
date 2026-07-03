REALM-Bench Tier 6 Dynamic Disruption Manual LLM Prompt

You are the proposer only. Mnemosyne owns admission, rejection, commit, and repair validation.

ROLE

You receive a workflow already in execution. Some operations have already committed and must not be rewritten. A disruption has arrived mid-execution.

Your task is to propose a bounded repair, reject unsafe repair, or observe if more information is needed.

PUBLIC DYNAMIC EPISODE JSON

{
  "sequence_id": "T6-DYN-jobshop-e7-0001",
  "episode_id": 6,
  "family": "jobshop_breakdown",
  "base_instance_id": "jobshop_breakdown:datasets/J4/custom/j4_custom_001.json",
  "config_id": "E7",
  "condition_label": "full_crt_stack",
  "is_control_sequence": false,
  "dynamic_phase": "mid_execution",
  "timestamp_utc": "2026-07-02T00:00:00Z",
  "committed_operations": [
    {
      "operation_id": "J3-O1",
      "machine": "M2",
      "status": "committed",
      "evidence_id": "ev-e06-committed-1"
    },
    {
      "operation_id": "J4-O1",
      "machine": "M3",
      "status": "committed",
      "evidence_id": "ev-e06-committed-2"
    }
  ],
  "uncommitted_operations": [
    {
      "operation_id": "J1-O2",
      "machine": "M1",
      "status": "uncommitted",
      "repair_allowed": true
    },
    {
      "operation_id": "J2-O2",
      "machine": "M0",
      "status": "uncommitted",
      "repair_allowed": true
    }
  ],
  "disruption": "A rushed repair would schedule J3-O2 before J3-O1 is completed.",
  "failure_signature": "precedence_violation_risk.M1",
  "must_preserve": [
    "J3-O1 status",
    "precedence constraint record",
    "repair-attempt warning"
  ],
  "open_decision": "Repair without violating job precedence.",
  "repair_radius_limit": 1,
  "forbidden_actions": [
    "global rollback",
    "delete committed evidence",
    "rewrite committed operation history",
    "orphan dependent operations",
    "commit a repair that violates precedence or machine availability"
  ],
  "success_criteria": [
    "preserve all listed evidence",
    "touch only uncommitted or locally repairable operations",
    "avoid global rollback",
    "return a machine-checkable JSON object",
    "reject if no safe repair is available"
  ]
}

CRITICAL RULES

Use only the visible episode.

Do not invent hidden schedule facts.

Do not delete or rewrite committed evidence.

Do not globally roll back the workflow.

Do not orphan dependent operations.

Do not exceed the repair radius unless you reject.

If a safe local repair is not possible, set action to reject and should_reject to true.

REQUIRED JSON RESPONSE

Return exactly one JSON object and no prose.

RESPONSE TEMPLATE

{
  "schema": "realm_tier6_dynamic_disruption_response_v0",
  "action": "",
  "repair_summary": "",
  "affected_steps": [],
  "preserve_evidence": true,
  "rollback_scope": "none",
  "expected_time_to_correction": 1,
  "risk_flags": [],
  "should_reject": false,
  "confidence": 0.0
}

FIELD REQUIREMENTS

- action: one of repair, reject, observe
- repair_summary: short repair description, or rejection/observation reason
- affected_steps: list of operation IDs or evidence IDs affected by your proposal
- preserve_evidence: true unless you are explicitly describing an unsafe proposal that should be rejected
- rollback_scope: one of none, local, unsafe
- expected_time_to_correction: nonnegative integer number of dynamic ticks
- risk_flags: list of concise risk labels
- should_reject: true if the proposal should be rejected before commit
- confidence: number from 0.0 to 1.0

PROPOSER PACK

claude
