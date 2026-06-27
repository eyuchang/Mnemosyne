# R6.9 REALM J4 Material Recovery

R6.9 completes the R6 REALM J1-J4 executable benchmark layer by moving J4 from a contract-only dynamic case to a deterministic benchmark-local material/resource recovery baseline.

## What R6.9 adds

- Expands the J4 operation templates into 20 concrete scheduled operations.
- Defines an explicit benchmark-local material policy for the underspecified J4 case.
- Realizes deterministic material outages for `C-X` and `F`.
- Detects operations affected by unavailable materials.
- Regenerates a repaired schedule that satisfies:
  - job precedence,
  - machine capacity,
  - material availability.

## Claim boundary

R6.9 claims benchmark-local J4 material recovery.

R6.9 does not claim:

- API-bound J4 active commitment recovery,
- durable production-runtime recovery logs,
- distributed or restart-safe runtime recovery,
- globally optimal JSSP schedules.

## R6 completion state

- J1: deterministic static executable baseline.
- J2: deterministic recovery baseline plus API-bound recovery through active commitment memory and admission.
- J3: deterministic static executable baseline.
- J4: deterministic benchmark-local material/resource recovery baseline.

R7/R8 should handle durable runtime substrate and production recovery execution.
