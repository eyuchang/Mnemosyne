# REALM-Bench Assets

This directory contains reusable REALM-Bench assets for Mnemosyne.

## Layout

    cases/
        Canonical JSON problem definitions for P1-P10 and J1-J4.

    adapters/
        Python loaders and typed adapters for benchmark cases.

    reports/
        Human-readable and machine-readable benchmark reports.

    solutions/
        Baseline and reference solutions.

    evaluations/
        Evaluation outputs and constraint-checking summaries.

    scripts/
        Report-generation and benchmark utility scripts.

## Current status

R6.4 starts by moving REALM-Bench assets out of the test-only tree and into a public benchmark directory.

The tests under `tests/benchmarks/realm/` verify that these assets load and remain deterministic.
