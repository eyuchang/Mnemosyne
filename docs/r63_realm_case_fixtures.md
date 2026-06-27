# R6.3 REALM-Bench Case Fixtures

## Status

R6.3 extracts the REALM-Bench paper cases into deterministic reusable test fixtures.

Current validation:

    248 passed, 24 skipped

## Purpose

R6.3 makes the REALM-Bench problem set available inside the test tree so future benchmark, recovery, disruption, and admission tests can reuse the same canonical cases.

This is not R7.0 infrastructure work.

R6.3 does not add Postgres, production runtime, workers, migrations, or durable services.

## Added fixtures

R6.3 adds:

    tests/benchmarks/fixtures/realm_bench_cases.json

This fixture contains all 14 REALM-Bench cases:

    P1   Campus Tour
    P2   Multi-Group Campus Tours
    P3   Urban Ride-Sharing
    P4   Urban Ride-Sharing with Disruptions
    P5   Wedding Reunion Logistics
    P6   Thanksgiving Dinner Planning
    P7   Disaster Relief Logistics
    P8   Wedding Logistics with Disruptions
    P9   Thanksgiving with Disruptions
    P10  Global Supply Chain
    J1   JSSP Basic
    J2   JSSP Basic with Disruptions
    J3   JSSP Large-scale
    J4   JSSP Large-scale with Disruptions

## Added loader

R6.3 adds:

    tests/benchmarks/realm_case_loader.py

The loader provides reusable accessors:

    load_realm_bench_cases()
    by_id(case_id)
    by_family(family)
    by_mode(mode)
    dynamic_cases()
    thanksgiving_cases()

## Added Thanksgiving adapter

R6.3 adds:

    tests/benchmarks/realm_thanksgiving_cases.py

The adapter materializes P6 and P9 into typed deterministic test objects:

    ThanksgivingScenario
    ThanksgivingFamilyMember
    ThanksgivingMealTask
    ThanksgivingFlightDelay

The static Thanksgiving case is:

    P6 / TD-static

The dynamic Thanksgiving disruption case is:

    P9 / TD-dynamic

## Thanksgiving static case

The static case includes:

    Sarah at home as host
    James landing at BOS at 13:00 from SF and requiring car rental
    Emily landing at BOS at 14:30 from Chicago and requiring pickup
    Michael driving from NY and arriving at 15:00
    Grandma requiring pickup from suburban Boston

Meal tasks:

    turkey: 240 minutes, supervision required
    side dishes: 120 minutes

Travel times:

    home-BOS: 60 minutes
    BOS-Grandma: 60 minutes
    home-Grandma: 30 minutes

Goal:

    all family members home and dinner ready by 18:00

## Thanksgiving dynamic case

The dynamic case extends P6 with James's flight delay:

    person: James
    original arrival: 13:00
    new arrival: 16:00
    notice time EST: 10:00

Derived values:

    delay_minutes: 180
    early_notice_minutes: 180

This case is important because the system must react at notice time, not at the original arrival time.

## Why this matters

Before R6.3, REALM-Bench cases were only described externally or scattered across older benchmark code.

After R6.3:

    all 14 cases are available as deterministic JSON fixtures
    future tests can load cases by id
    dynamic cases can be enumerated consistently
    Thanksgiving static and disruption cases are typed and reusable
    benchmark probes no longer need to re-extract case definitions

## Next possible R6.3 extension

A future small R6.3 extension may add an executable Thanksgiving baseline:

    P6 static admission
    P9 James-delay disruption signal
    recovery proposal
    explicit admission boundary

But that is intentionally separate from this fixture extraction checkpoint.

## Validation

    248 passed, 24 skipped
