# Manual LLM Injection Instructions

1. Open each file under prompts/.
2. Paste it into the LLM being tested.
3. Copy the LLM JSON answer into the matching file under responses/.
4. Do not expose hidden failure signatures or scorer labels.
5. Run the validator after responses are filled.

The LLM generates proposals. Mnemosyne owns admission. REALM owns scoring.
