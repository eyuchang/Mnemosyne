# ProductionTPComparatorBench

Deterministic coverage audit; not a throughput benchmark.

## Summary

- Cases: 9
- ATP/Mnemosyne caught: 9 / 9
- PostgreSQL-style TP caught: 2 / 9
- Workflow/saga guardrails caught: 3 / 9

## Coverage table

| Hazard | PostgreSQL-style TP | Workflow/saga | ATP/Mnemosyne | Rationale |
|---|---:|---:|---:|---|
| `primary_key_unique_duplicate` | caught | caught | caught | This is a storage-level uniqueness/idempotency violation. |
| `missing_foreign_key_dependency` | caught | caught | caught | This is a storage-level referential-integrity violation. |
| `finite_state_invalid_transition` | app-only | caught | caught | A TP substrate can enforce this only if the application encodes the FSM rule; workflow guardrails and ATP naturally check it. |
| `stale_world_proposal` | missed | missed | caught | Generic TP executes submitted transactions; ATP checks proposal world assumptions against effective state before authority is granted. |
| `orphaning_compensation_effective_state` | app-only | partial | caught | A saga may run local compensation but need not check effective-state dependency closure unless the application encodes it. |
| `evidence_destroying_repair` | missed | missed | caught | Evidence preservation is an ATP-specific admission rule: a repair must resolve the failure or preserve the triggering evidence. |
| `acr_direct_domain_mutation` | missed | missed | caught | ATP treats ACR wakeups as non-authoritative; they may only emit proposal packages that re-enter admission. |
| `generative_conflict_scope_collision` | app-only | partial | caught | TP can serialize rows, but generative conflict scopes are an ATP authority-level declaration over proposal semantics. |
| `duplicate_side_effect_intent` | partial | partial | caught | Outbox/idempotency can partially catch duplicates; ATP stages the intent and admits observed effects as later transitions. |

## Conclusion

Production TP substrates catch storage-level violations; workflow/saga guardrails catch classical guardrail hazards; ATP/Mnemosyne adds proposal-authority semantics for stale-world proposals, evidence-preserving repair, ACR non-authority, dependency-closed compensation, and generative conflict scopes.
