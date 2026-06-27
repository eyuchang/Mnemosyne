# Thanksgiving P9 Recovery Trace Report

## Summary

- Trace id: `p9_thanksgiving_recovery_trace`
- Case: P9
- Feasible after repair: True
- Wakeups: 2
- Proposals: 1
- Admitted repairs: 1

## Disruption

- Person: James
- Notice time EST: 10:00
- Original arrival: 13:00
- New arrival: 16:00
- Delay minutes: 180

## Active Commitments

- `p9-cook-turkey-supervision`: not affected. Sarah supervises turkey from 09:00 to 13:00.
- `p9-pickup-emily`: not affected. Emily is picked up from BOS before dinner.
- `p9-pickup-grandma-by-james`: affected. Original plan assigns Grandma pickup to James.
- `p9-dinner-ready-by-1800`: affected. All family members home and dinner ready by 18:00.

## Commitment Wakeups

- `p9-wakeup-grandma-pickup` wakes `p9-pickup-grandma-by-james` at 10:00: James now lands at 16:00, too late to perform Grandma pickup safely.
- `p9-wakeup-dinner-deadline` wakes `p9-dinner-ready-by-1800` at 10:00: The delay threatens the all-family-home-before-dinner condition.

## Repair Proposals

- `p9-proposal-reassign-grandma-to-sarah`: Reassign Grandma pickup from James to Sarah.
  - Grandma pickup assignee: James -> Sarah

## Repair Admission

- `p9-admit-reassign-grandma-to-sarah` status: admitted
- Boundary: domain_validated_repair
- Admitted at: 10:00
- repair_triggered_at_notice_time: True -- Repair is triggered at 10:00 when delay notice arrives.
- pickup_assignment_repaired: True -- Grandma pickup is reassigned from James to Sarah.
- dinner_deadline_preserved: True -- All family members home by 17:30 and dinner ready at 18:00.

## Audit Lineage

1. disruption_event `p9-disruption-james-flight-delay` -- James flight delay notice received at 10:00.
2. commitment_wakeup `p9-wakeup-grandma-pickup` -- Grandma pickup commitment wakes.
3. commitment_wakeup `p9-wakeup-dinner-deadline` -- Dinner deadline commitment wakes.
4. repair_proposal `p9-proposal-reassign-grandma-to-sarah` -- Repair proposal reassigns Grandma pickup from James to Sarah.
5. repair_admission `p9-admit-reassign-grandma-to-sarah` -- Selected repair is admitted after validation.

## Result

- Repair trigger time: 10:00
- Latest family home time: 17:30
- Dinner ready time: 18:00
- Feasible after repair: True
- Optimality status: feasible_not_proven_optimal

