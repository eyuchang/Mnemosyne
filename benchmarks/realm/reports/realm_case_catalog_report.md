# REALM-Bench Case Catalog Report

## Summary

- Case count: 14
- Dynamic/disruption cases: P4, P7, P8, P9, P10, J2, J4
- Result type: case catalog and readiness report
- Executable solving result: not run in R6.4

## Case Index

| Case | Name | Family | Mode | Tier | Disruptions |
|---|---|---|---:|---:|---:|
| P1 | Campus Tour | planning | static | 1 | 0 |
| P2 | Multi-Group Campus Tours | planning | static | 2 | 0 |
| P3 | Urban Ride-Sharing | planning | static | 2 | 0 |
| P4 | Urban Ride-Sharing with Disruptions | planning | dynamic | 4 | 2 |
| P5 | Wedding Reunion Logistics | planning | static | 2 | 0 |
| P6 | Thanksgiving Dinner Planning | planning | static | 3 | 0 |
| P7 | Disaster Relief Logistics | planning | static | 3 | 4 |
| P8 | Wedding Logistics with Disruptions | planning | dynamic | 4 | 1 |
| P9 | Thanksgiving with Disruptions | planning | dynamic | 4 | 1 |
| P10 | Global Supply Chain | planning | static_dynamic | 5 | 3 |
| J1 | JSSP Basic | jssp | static | 1 | 0 |
| J2 | JSSP Basic with Disruptions | jssp | dynamic | 4 | 2 |
| J3 | JSSP Large-scale | jssp | static | 3 | 0 |
| J4 | JSSP Large-scale with Disruptions | jssp | dynamic | 4 | 2 |

## Dynamic Disruptions

### P4 Urban Ride-Sharing with Disruptions

- Type: `traffic_delay`
  - description: Airport route traffic delay.
- Type: `road_closure`
  - description: Certain local road closure.

### P7 Disaster Relief Logistics

- Type: `donation_arrival`
  - description: Unpredictable donation arrivals.
- Type: `road_blockage`
  - description: Road blockages requiring rerouting.
- Type: `emergency_hospital_demand`
  - description: Emergency hospital demands.
- Type: `fuel_shortage_delay`
  - description: Fuel shortage delays.

### P8 Wedding Logistics with Disruptions

- Type: `road_closure`
  - description: Road closure requires real-time rerouting.

### P9 Thanksgiving with Disruptions

- Type: `flight_delay`
  - description: James learns at 10 AM EST that his 1 PM BOS arrival is delayed to 4 PM.
  - new_arrival_time: 16:00
  - notice_time_est: 10:00
  - original_arrival_time: 13:00
  - person: James

### P10 Global Supply Chain

- Type: `earthquake`
  - cost_impact_percent: 30
  - delay_months: 1
  - probability_per_quarter: 0.1
- Type: `typhoon`
  - cost_impact_percent: 30
  - delay_months: 1
  - probability_per_quarter: 0.1
- Type: `shipment_delay`
  - description: Expedite one shipment by 1 month, shifting all shipments.

### J2 JSSP Basic with Disruptions

- Type: `stochastic_operation_delay`
  - distribution: Uniform(0, 2)
  - revealed_at: operation_start
- Type: `machine_breakdown_example`
  - machine: MachineA
  - unavailable_end: 6
  - unavailable_start: 4

### J4 JSSP Large-scale with Disruptions

- Type: `stochastic_operation_delay`
  - distribution: Uniform(0, 3)
- Type: `material_unavailability`
  - description: Materials may become temporarily unavailable.
  - materials_examples: ['C-X', 'F']

## Thanksgiving Static Case: P6

- Case: P6 / TD-static
- Family members: Sarah, James, Emily, Michael, Grandma
- Pickup members: Emily, Grandma
- Host members: Sarah
- Dinner deadline: 18:00

Meal tasks:
- turkey: 240 minutes, requires supervision: True
- side_dishes: 120 minutes, requires supervision: False

Travel times:
- BOS-Grandma: 60 minutes
- home-BOS: 60 minutes
- home-Grandma: 30 minutes

## Thanksgiving Dynamic Case: P9

- Case: P9 / TD-dynamic
- Extends: P6
- Person delayed: James
- Notice time EST: 10:00
- Original arrival: 13:00
- New arrival: 16:00
- Delay minutes: 180
- Early notice window: 180 minutes

Expected benchmark behavior:
- React at notice time, not at the original arrival time.
- Preserve dinner deadline if feasible.
- Preserve pickup and cooking-supervision constraints.

## Current Result Status

- Problem extracted: True
- Typed adapter loaded: True
- Solution available: False
- Evaluation available: False
- Executable solver result: not_run_in_r6.4
- Next step: R6.5 executable Thanksgiving P6/P9 benchmark

