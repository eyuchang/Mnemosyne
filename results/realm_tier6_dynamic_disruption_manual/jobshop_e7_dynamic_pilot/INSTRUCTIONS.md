# R96 Dynamic Disruption Manual Collection Instructions

This pack contains 40 prompts.

For each proposer pack:

1. Open eXX_prompt.md.
2. Paste the prompt into the target LLM.
3. Copy the model's JSON-only answer.
4. Paste it into eXX_response.json.
5. Do not edit the model answer except to remove non-JSON wrapper text if necessary.

No API keys are required.

No vendor API is called by this script.

Validation command:

python benchmarks/realm/tier6_dynamic_disruption_manual.py validate-responses --pack-dir results/realm_tier6_dynamic_disruption_manual/jobshop_e7_dynamic_pilot

Expected before collection:

- parsed responses: 40
- placeholders: 40
- all valid: false

Expected after collection:

- parsed responses: 40
- missing responses: 0
- placeholders: 0
- validation errors: 0
- all valid: true
