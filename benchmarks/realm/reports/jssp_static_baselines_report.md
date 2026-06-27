# REALM JSSP Static Baselines Report

## Summary

- Case count: 2
- Feasible static baselines: 2
- Optimality status: feasible_not_proven_optimal

## Cases

| Case | Complexity | Feasible | Requires recovery | Optimality |
|---|---|---:|---:|---|
| J1 | simple | True | False | feasible_not_proven_optimal |
| J3 | complex | True | False | feasible_not_proven_optimal |

## What this commit proves

- J1 and J3 static JSSP case files are executable benchmark inputs.
- Static baseline artifacts can be regenerated deterministically.
- Static cases are kept separate from dynamic recovery claims.
- J2/J4 disruption and recovery work remains future R6.8 work.

## Non-goals

- Do not claim J1/J3 optimality.
- Do not claim J2/J4 dynamic recovery.
- Do not claim durable production recovery logs.
- Do not bind to production runtime in R6.8 static baseline work.

