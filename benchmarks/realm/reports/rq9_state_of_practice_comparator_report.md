# RQ9 State-of-Practice Comparator Report

This benchmark compares ATP against a realistic durable workflow/saga/guardrail stack rather than only against raw unsafe baselines.

The comparator implements schema validation, finite-state checks, idempotency keys, retry/timer execution, local saga compensation, and proposer self-checking. It does not implement ATP-specific admission over effective StateView, evidence-preserving repair, obligation containment, dependency-closed compensation, or conflict-scoped serial admission.

| System | Cases | Accepted | Rejected | Invalid commits | Classical rejections | Missed ATP-specific hazards | Valid commits |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw_generated_write | 14 | 14 | 0 | 10 | 0 | 6 | 4 |
| workflow_saga_guardrails | 14 | 10 | 4 | 6 | 4 | 6 | 4 |
| atp_mnemosyne | 14 | 4 | 10 | 0 | 4 | 0 | 4 |

## Hazard classes

| Hazard class | Count | Examples |
|---|---:|---|
| Classical guardrail hazards | 4 | malformed proposal, finite-state violation, duplicate operation key, failed self-check |
| ATP-specific hazards | 6 | stale-world plan, evidence-destroying repair, direct obligation mutation, orphaning compensation, ineffective-record projection, conflict-scope violation |

## Claim boundary

This is a semantic comparator for mechanisms commonly available in durable workflow engines and guarded agent stacks. It is not a product benchmark of Temporal, Cadence, Argo, LangGraph, or any specific framework.
The result isolates the boundary those systems typically leave to application logic: effective-state admission, evidence-preserving repair, obligation containment, dependency-closed compensation, and generative conflict-scope admission.
