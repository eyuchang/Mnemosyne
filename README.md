# Mnemosyne

Mnemosyne is the reference runtime for **Agentic Transaction Processing (ATP)**: a transaction architecture for admitting generated workflow actions, repairs, plans, and active-memory wakeups into committed truth.

The core design rule is:

```text
Proposal is not truth.
```

LLMs, solvers, agents, runtime drivers, workflow engines, benchmark adapters, and active commitment records may propose or orchestrate. They do **not** own committed truth.

The committed-state boundary is:

```text
Proposal package -> Deterministic admission under C -> CTL/store -> StateView
```

where:

```text
CTL/store = committed truth
StateView = current effective truth
Proposers = non-authoritative proposal sources
Admission gate = only authority boundary
```

---

## Paper

**Mnemosyne: Agentic Transaction Processing for Validating and Repairing AI-generated Workflows**  
Edward Y. Chang, Longling Geng, Emily J. Chang  
arXiv: [2607.00269](https://arxiv.org/abs/2607.00269)

## Current milestone

Current verified milestone:

```text
R8: Deployment service boundary and local deployment load audit
```

The project has completed the implementation path from the early correctness kernel through recovery, proposal packages, Temporal-style boundaries, PostgreSQL-backed storage validation, RQ1--RQ9b artifact experiments, and the R8 deployable service boundary.

Current artifact tag:

```text
arxiv-atp-rq1-rq9b-r8-v1
```

Public artifact URL:

```text
https://github.com/eyuchang/Mnemosyne/tree/arxiv-atp-rq1-rq9b-r8-v1
```

The R8 branch was merged through PR #34:

```text
Merge pull request #34 from eyuchang/r8-deployment-service-boundary
```

---

## System status

Mnemosyne is currently best described as:

> A deterministic ATP reference implementation and product kernel for committed-transition logging, effective-state projection, validated admission, compensation safety, active commitment memory, recovery proposal packages, SQLite and PostgreSQL storage substrates, workflow/runtime boundaries, and a deployable R8 service shell.

It is suitable for:

- reproducing the ATP artifact experiments;
- studying the ATP authority-separation architecture;
- extending domain validators and proposal packages;
- testing workflow/saga guardrail failure modes;
- evaluating committed-state safety under generated proposals;
- building toward production service deployment.

It is **not yet** a fully hardened production cloud deployment. Kubernetes deployment, third-party workflow baselines, live LLM proposer experiments, production observability, and operational hardening are active next-stage work.

---

# Architecture

Mnemosyne implements the ATP correctness boundary:

```text
Generated proposal
    |
    v
Proposal package
    |
    v
Admission gate under C + StateView
    |
    +--> rejected proposal with durable reason
    |
    v
Committed-transition log / Store
    |
    v
StateView effective-state projection
```

The key invariant is:

```text
Only admitted transitions may become committed truth.
```

A proposer may be an LLM, solver, agent, benchmark adapter, workflow driver, Temporal-style activity, active commitment wakeup, or learned policy. All such sources are non-authoritative. They can change the proposal stream, but they cannot directly mutate committed state.

## Implemented authority planes

Mnemosyne separates four planes:

| Plane | Role | Authority |
|---|---|---|
| Proposal plane | LLMs, solvers, agents, ACR wakeups, benchmark adapters | May propose |
| Admission plane | deterministic validators under constraint set `C` | May admit or reject |
| Commit plane | CTL/store | Owns committed truth |
| Projection plane | StateView | Owns current effective truth |

Runtime drivers and workflow engines orchestrate execution, retries, timers, and wakeups. They do not own committed truth.

---

# Core implemented components

## Correctness kernel

Implemented:

- `CommitBatch`
- `TransitionCandidate`
- `CTLRecord`
- `Validator`
- committed-transition log append
- SQLite-backed store
- PostgreSQL-backed store
- StateView projection
- effective-history view
- full-history view
- compensation handling
- fail-closed compensation invariants
- operation-key logical idempotency
- inbox/event-log idempotency
- outbox staging

Source-of-truth rule:

```text
CTL/store owns committed truth.
StateView owns current effective truth.
Inbox deduplicates external events.
Recovery/event logs record observed causes.
Outbox stages external side effects.
```

## Active commitment memory

Implemented:

- `ActiveCommitment`
- `CommitmentEvent`
- commitment lifecycle records
- CTL serialization through extension fields
- replay-derived active commitment index
- store-backed active commitment index
- bounded recursive recovery loop
- recovery policy
- recovery orchestration
- recovery admission boundary

Core invariant:

```text
A fired commitment may wake recovery,
but it cannot mutate domain state directly.

Only separately admitted domain CTL records mutate domain state.
```

## Runtime active recovery

Implemented:

- `LocalActiveRecoveryExecutor`
- runtime planning from CTL-derived active commitment index
- commitment-FSM-only recovery execution
- admission-validated recovery execution through `Validator`
- local runtime recovery demos
- runtime parity and protocol-alignment tests

Core invariant:

```text
Runtime recovery may update commitment state,
but it may not mutate domain state directly.
```

## Recovery proposal packages

Implemented:

- `RecoveryProposalPackage`
- package serialization helpers
- package references in commitment-event payloads
- package-backed commitment proposal candidates
- package admission-boundary tests
- proposal package demos

Core invariant:

```text
A recovery proposal package may contain proposed domain candidates,
but those candidates are not committed truth.

Commitment events record package references.
Domain state changes still require separate domain CTL admission.
```

## Temporal-style runtime boundary

Implemented:

- Temporal-style active recovery activity boundary
- `ActiveRecoveryActivityResult`
- commitment-FSM-only recovery commits through activity boundary
- validation and CTL commit behind the activity boundary
- retry and idempotency tests
- Temporal boundary demos and regression tests

Core invariant:

```text
Temporal or workflow-engine code remains orchestration-only.

Active recovery planning, validation, and CTL commit happen through an
activity boundary.

Temporal-style recovery may update commitment state,
but it may not mutate domain state directly.
```

## Storage substrate and PostgreSQL path

Implemented:

- SQLite default store
- store protocol conformance
- store factory
- PostgreSQL-backed store implementation
- PostgreSQL database URL configuration
- optional live PostgreSQL adapter path
- pooled PostgreSQL runtime path
- PostgreSQL connection-pooling boundary
- PostgreSQL live conformance tests
- PostgreSQL concurrent recovery-event tests
- PostgreSQL pooled transaction-boundary tests
- storage-level uniqueness and idempotency checks
- recovery-event store conformance

Storage-substrate rule:

```text
The store provides atomicity, durability, idempotency, recovery-event persistence,
and projection support. Semantic validity remains owned by admission under C.
```

SQLite is the default deterministic local backend. PostgreSQL is implemented as the live/durable backing store path and is exercised by gated conformance and pooled-runtime tests.

## R8 deployment service boundary

Implemented:

- `mnemosyne/service/config.py`
- `mnemosyne/service/metrics.py`
- `mnemosyne/service/schemas.py`
- `mnemosyne/service/app.py`
- `mnemosyne/service/worker.py`
- HTTP health endpoint
- HTTP proposal endpoint
- StateView endpoint
- Prometheus-style metrics endpoint
- Dockerfile
- docker-compose service shell
- R8 smoke script
- R8 local deployment load script
- worker-boundary tests
- service-boundary tests

R8 exposes:

```text
GET  /health
GET  /metrics
POST /proposals
GET  /state/{tenant}/{entity}
```

R8 invariant:

```text
The deployment service exposes proposal submission,
not direct committed-truth mutation.
```

A valid proposal may be admitted. Explicit bypass attempts, direct-commit flags, raw append attempts, and invalid-under-C payloads are rejected before they can become effective state.

---

# Evaluation artifact

The current artifact supports the ATP paper's reorganized evaluation spine:

| RQ | Question | Evidence |
|---|---|---|
| RQ1 | Does the authority boundary hold across ATP hazard classes? | six falsification benchmarks |
| RQ2 | Does ATP catch hazards workflow/saga guardrails miss? | mechanism-level guardrail comparator |
| RQ3 | Does the boundary hold end-to-end on planning/recovery cases? | J1--J4 end-to-end runs |
| RQ4 | Does proposer quality affect usefulness but not correctness? | proposer-quality benchmark |
| RQ5 | What is the artifact-level cost of safety? | RQ9b infrastructure-cost audit |

The artifact includes evidence for:

- authority separation;
- serial-equivalent generative admission;
- evidence-preserving repair;
- obligation containment;
- effective-state compensation;
- storage-substrate correctness;
- J1--J4 end-to-end execution;
- proposer-quality safety invariance;
- workflow/saga guardrail comparison;
- runtime infrastructure-cost audit;
- R8 deployment smoke/load behavior.

## R8 local deployment audit

The R8 deployment smoke test verifies:

- `/health` exposes the authority boundary;
- valid proposals are admitted;
- explicit direct-commit bypass attempts are rejected;
- effective state contains only admitted proposals;
- `/metrics` records proposal, admission, rejection, and latency counters.

The R8 load audit exercises concurrent HTTP proposal submission across multiple client worker settings. The stable safety result is:

```text
invalid commits = 0
```

Throughput and latency are reported as local diagnostic evidence only, not as production load-test claims.

---

# Repository layout

Important top-level modules:

```text
mnemosyne/
  api/              product-facing APIs and audit/recovery surfaces
  apps/             application registry and common app helpers
  benchmarks/       benchmark cases, solvers, proposal conflict tests
  cli/              command-line report and product tools
  compensation/     compensation DAG utilities
  core/             core models, commitments, recovery, validation
  effects/          effect/outbox-related boundaries
  eval/             evaluation helpers
  obs/              observability namespace
  projection/       StateView and effective-state projection
  runtime/          runtime sessions, admission, Temporal/local boundaries
  service/          R8 deployment service boundary
  store/            SQLite/PostgreSQL store substrates and factory
```

Important test areas:

```text
tests/runtime/      runtime, admission, kernel, session, registry tests
tests/core/         recovery, Temporal, store, PostgreSQL, conformance tests
tests/benchmarks/   benchmark and REALM/J1-J4 tests
tests/service/      R8 deployment service and worker-boundary tests
tests/experiments/  experiment-specific tests
```

Important experiment/report areas:

```text
experiments/
benchmarks/realm/
benchmarks/realm/reports/
docs/
docs/release_notes/
```

---

# Quick start

Install in editable mode:

```bash
pip install -e .
```

Run the service-boundary tests:

```bash
python -m pytest -q tests/service
```

Run selected runtime and boundary tests:

```bash
python -m pytest -q   tests/runtime/test_runtime_admission.py   tests/runtime/test_kernel_admission.py   tests/core/test_temporal_activity_boundary.py   tests/core/test_postgres_connection_pooling_boundary.py
```

Run the R8 service locally:

```bash
python -m mnemosyne.service.app --host 127.0.0.1 --port 8088
```

In another terminal:

```bash
scripts/r8_smoke.sh
```

Run the R8 local load audit:

```bash
scripts/r8_load.sh
```

Optional Docker/compose run:

```bash
docker compose up --build
```

Then:

```bash
scripts/r8_smoke.sh
```

---

# Artifact reproduction

The tagged artifact version is:

```bash
git checkout arxiv-atp-rq1-rq9b-r8-v1
```

Run core service tests:

```bash
python -m pytest -q tests/service
```

Run RQ9b infrastructure-cost benchmark:

```bash
python experiments/rq9b_real_infra_benchmark.py
```

Run R8 service smoke/load audit:

```bash
python -m mnemosyne.service.app --host 127.0.0.1 --port 8088
scripts/r8_smoke.sh
scripts/r8_load.sh
```

Generated R8 reports are written under:

```text
benchmarks/realm/reports/r8_deployment/
```

Generated RQ9b reports are written under:

```text
benchmarks/realm/reports/rq9b_*/
```

---

# PostgreSQL-backed execution

PostgreSQL is implemented as a durable backing store path. To exercise the live PostgreSQL tests, set the database URL expected by the store configuration and run the gated PostgreSQL test subset.

Example:

```bash
export MNEMOSYNE_POSTGRES_DATABASE_URL="postgresql://mnemosyne:mnemosyne@localhost:54329/mnemosyne"
python -m pytest -q tests/core/test_postgres_live_database_url_conformance.py
python -m pytest -q tests/core/test_postgres_live_conformance_boundary.py
python -m pytest -q tests/core/test_postgres_live_pooled_runtime_path.py
python -m pytest -q tests/core/test_postgres_live_concurrent_recovery_events.py
```

Use docker-compose for a local PostgreSQL service:

```bash
docker compose up postgres
```

PostgreSQL implementation status:

```text
Implemented:
  PostgreSQL-backed store
  live adapter path
  pooled runtime path
  conformance tests
  concurrent recovery-event tests

Future hardening:
  production migrations
  cloud deployment recipes
  operational monitoring
  long-running stress tests
```

---

# Design principles

## 1. Proposal non-authority

A generated action is not committed truth merely because it is produced by a model, solver, agent, workflow driver, or recovery mechanism.

## 2. Deterministic admission under C

Every candidate transition must pass deterministic admission under the declared executable constraint set `C`.

## 3. Effective state, not raw history

Admission reads StateView, the effective projection of committed history. It does not validate against speculative, rejected, compensated, or superseded proposal history.

## 4. Compensation is logical, not deletion

Compensation is represented as an admitted transition. Historical records remain queryable; effective state excludes records that are no longer current.

## 5. Active memory is non-authoritative

Active commitment records may wake, resume, and propose. They cannot directly mutate domain truth.

## 6. Evidence-preserving repair

A repair may not discharge its own trigger by deleting, compensating, or obscuring the evidence that justified it, unless admission verifies that the underlying condition is resolved under `C`.

## 7. Runtime engines orchestrate

Local drivers, Temporal-style activities, and future Kubernetes workers may orchestrate work, but they do not own committed truth.

---

# What is not yet production-complete

Important next-stage production work remains:

- real third-party workflow baseline, e.g. Temporal, LangGraph, or saga-library comparison;
- live LLM proposer experiment;
- Kubernetes deployment and service scaling;
- production Temporal SDK workers;
- production-grade PostgreSQL migrations and operational deployment scripts;
- full R8 HTTP service wiring to durable SQLite/PostgreSQL service modes;
- worker-safe inbox processing;
- worker-safe outbox claiming;
- provider adapters;
- external OR solver adapters;
- production authentication and authorization;
- structured observability dashboards;
- production audit/report APIs;
- long-running stress tests;
- cloud deployment documentation.

Current status:

```text
R7 completed the PostgreSQL-backed storage/runtime path.
R8 completes the deployable service-boundary artifact milestone.
Production hardening continues as the next stage.
```

---

# Documentation

Useful documentation entry points:

```text
ARTIFACT_EVALUATION.md
PHASE0_CONTRACT.md
docs/
docs/release_notes/
docs/benchmark_readiness_matrix.md
docs/user_guide_j1_j4_experiments.md
```

Current readiness notes:

```text
R7 PostgreSQL runtime adapter path is complete.
J1--J4 benchmark/user workflow is runnable in the default suite.
R8 deployment service boundary is implemented and tagged.
P1--P10 broader readiness suites should not yet be claimed as fully certified.
```

---

# Suggested current development track

The next recommended stage is post-R8 product hardening:

```text
R9: durable production service runtime
```

Recommended R9 subgoals:

```text
R9.1 wire the R8 HTTP service directly to RuntimeAdmissionFacade / KernelAdmissionAdapter / StoreFactory
R9.2 expose durable service modes: memory, SQLite, PostgreSQL
R9.3 add repeated load tests with median/p10/p90 reporting
R9.4 add property-based bypass-freedom fuzzing
R9.5 add live LLM proposer adapter
R9.6 add third-party workflow/saga baseline
R9.7 add Kubernetes deployment and service scaling
```

The R9 goal is not to implement PostgreSQL from scratch; that path already exists. R9 hardens how the deployable service uses the existing durable store/admission/runtime machinery in production-style deployment.

The semantic boundary remains:

```text
proposal -> admission -> CTL/store -> StateView
```

---

# Citation / paper context

Mnemosyne implements the ATP architecture described in:

```text
Agentic Transaction Processing:
Decoupling Committed-State Correctness from the Intelligence Layer
```

The public artifact tag for the arXiv/VLDB preparation version is:

```text
arxiv-atp-rq1-rq9b-r8-v1
```
