# Long-Horizon Transaction Test Policy

## Purpose

Mnemosyne / ALAS is designed for long-horizon transactional memory.

The system must preserve historical memory while maintaining a correct current operational view across many steps, corrections, compensations, supersessions, retries, and delayed side effects.

Long-horizon transaction tests are important for:

- book evidence
- research validation
- stress testing
- architectural confidence
- future benchmark design

However, long-horizon tests should not slow down or destabilize the standard public test suite.

---

## Core decision

Long-horizon transaction tests should be included in the repository but excluded from the default test run.

The default test command remains:

`python -m pytest -q`

The default suite should be:

- fast
- deterministic
- local
- free of external services
- suitable for public release
- suitable for contributors and CI smoke checks

Long-horizon tests are opt-in:

`python -m pytest -q -m long_horizon`

For research runs, use:

`python -m pytest -q -m "long_horizon or research"`

---

## Why long-horizon tests matter

Long-horizon tests verify the main Mnemosyne / ALAS memory claim:

History is preserved. Current truth is projected. Corrections do not erase memory. Compensation and supersession update effective state. Side effects are durably staged through outbox.

They test behaviors such as:

- many sequential CTL commits
- long entity histories
- compensation cascades
- supersession chains
- retry and idempotency behavior
- delayed outbox effects
- projection correctness after many transitions
- local log position monotonicity
- effective-record correctness
- StateView consistency after long histories

---

## Public release policy

Long-horizon tests should not be hidden.

They should remain visible to users and reviewers because they show that the system is designed for long-running reasoning and planning scenarios.

However, they should be marked clearly and excluded from the default test suite.

Recommended markers:

- unit
- integration
- long_horizon
- research
- external
- temporal

Marker meanings:

- unit: Fast, deterministic, local tests. Safe for default public test runs.
- integration: Tests requiring broader integration surfaces. May be slower.
- long_horizon: Tests involving many-step transaction histories, compensation chains, or stress-like CTL behavior.
- research: Tests used for book, paper, benchmark, or evidence generation. May be heavier.
- external: Tests requiring external APIs, providers, LLMs, solvers, or services.
- temporal: Tests requiring Temporal SDK or a Temporal server.

---

## Default test policy

The default command must stay fast:

`python -m pytest -q`

The default suite should not require:

- Temporal server
- Postgres server
- OR-Tools
- LLM APIs
- external provider APIs
- long-running stress tests

---

## Long-horizon test design

A deterministic long-horizon CTL test should initially be local and SQLite-only.

Suggested first test:

`tests/research/test_long_horizon_transactions.py`

Suggested marker:

`@pytest.mark.long_horizon`

Suggested scenario:

1. Create one tenant and one entity.
2. Commit 50 to 100 sequential CTL records.
3. Periodically add supersession or compensation records.
4. Verify CTL preserves full history.
5. Verify effective_record_index marks corrected records ineffective.
6. Verify StateView reflects latest effective truth.
7. Verify local_log_position is monotonic.
8. Verify outbox idempotency if outbox intents are included.

---

## Book and research use

For the book effort, long-horizon tests provide concrete evidence for the Mnemosyne / ALAS thesis:

A planning system can preserve full transactional memory while exposing a coherent current operational state.

These tests can support chapters or sections on:

- long-horizon planning
- memory and correction
- compensation
- transactional cognition
- durable workflow reasoning
- CTL as structured memory
- separation between historical truth and current truth

---

## CI recommendation

Public CI should run:

`python -m pytest -q`

Research CI or nightly CI may run:

`python -m pytest -q -m long_horizon`

or:

`python -m pytest -q -m "long_horizon or research"`

Temporal integration CI should remain separate:

`python -m pytest -q -m temporal`

---

## Release guidance

For public release:

- keep long-horizon tests in the repository
- mark them clearly
- exclude them from default public tests
- document how to run them
- keep at least one small deterministic smoke test in the default suite if needed
- keep heavier research and benchmark tests opt-in

This provides transparency without burdening normal users.

---

## Current status

This policy establishes the design decision.

Implementation of the first marked long-horizon test is deferred to the next development slice.