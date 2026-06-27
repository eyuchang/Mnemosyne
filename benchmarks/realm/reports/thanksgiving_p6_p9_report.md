# Thanksgiving P6/P9 Executable Benchmark Report

## Summary

- Benchmark: `thanksgiving_p6_p9`
- Cases: P6, P9
- P6 feasible: True
- P9 feasible after repair: True
- P6 optimality: feasible_not_proven_optimal
- P9 optimality: feasible_not_proven_optimal

## P6 Static Problem

Thanksgiving dinner planning with arrivals, pickups, cooking, travel times, and 18:00 dinner deadline.

Goal: all family members home and dinner ready by 18:00.

## P6 Baseline Solution

- Solution id: `p6_thanksgiving_static_baseline`
- Solution type: deterministic_baseline
- Optimality status: feasible_not_proven_optimal

Cooking:
- turkey: Sarah at home, 09:00-13:00, supervision=continuous
- side_dishes: Sarah at home, 16:00-18:00, supervision=not_required

Transportation:
- James: land_BOS_and_rent_car, 13:00-13:30
- James: pickup_Grandma, 13:30-15:00
- Sarah: pickup_Emily, 13:30-15:30
- Michael: drive_from_NY_to_home, arrival=15:00

## P6 Evaluation

- Feasible: True
- Latest family home time: 15:30
- Dinner ready time: 18:00

- turkey_supervision_continuity: True — Sarah supervises turkey at home from 09:00 to 13:00.
- pickup_completion: True — James brings Grandma home by 15:00; Sarah brings Emily home by 15:30.
- all_family_home_by_dinner: True — Latest family arrival is 15:30, before the 18:00 deadline.
- dinner_ready_by_deadline: True — Turkey ends at 13:00 and side dishes end at 18:00.

## P9 Dynamic Disruption

Thanksgiving disruption case where James's flight delay is known at 10:00.

- Person delayed: James
- Notice time EST: 10:00
- Original arrival: 13:00
- New arrival: 16:00
- Delay minutes: 180
- Early notice window: 180 minutes

## P9 Repair Solution

- Solution id: `p9_thanksgiving_dynamic_repair_baseline`
- Repair trigger time: 10:00
- Optimality status: feasible_not_proven_optimal

Changed assignments:
- Grandma pickup: James -> Sarah because James now lands too late to complete Grandma pickup before dinner.

Transportation after repair:
- Sarah: pickup_Emily_then_Grandma, 13:30-16:00
- James: delayed_land_BOS_and_rent_car_then_drive_home, 16:00-17:30
- Michael: drive_from_NY_to_home, arrival=15:00

## P9 Evaluation

- Feasible: True
- Repair trigger time: 10:00
- Latest family home time: 17:30
- Dinner ready time: 18:00

- reacted_at_notice_time: True — Repair trigger is 10:00, the delay notice time.
- did_not_wait_until_original_arrival: True — Repair is planned before James's original 13:00 arrival time.
- pickup_repaired: True — Grandma pickup is reassigned from James to Sarah.
- all_family_home_by_dinner: True — Latest family arrival is James at 17:30, before the 18:00 deadline.
- dinner_ready_by_deadline: True — Turkey ends at 13:00 and side dishes end at 18:00.
- original_static_constraints_preserved: True — Cooking, pickup, and dinner deadline constraints remain active.

## Limitations

- This is a deterministic feasible baseline.
- Optimality is not proven.
- Later milestones can connect this benchmark to Mnemosyne CTL admission, active commitments, and recovery lineage.

