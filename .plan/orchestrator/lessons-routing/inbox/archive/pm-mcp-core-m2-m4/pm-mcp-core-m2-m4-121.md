envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T05:32:00Z

# q-gate-validation has no verb for deliverable hashes and hard-codes the 3-outline phase

Source: plan-retrospective of static-verifier-and-fuzzer (llm-to-script and chat-history aspects); hand-back reports of the two q-gate-validation passes.

## What happened

- Pass 1 (3-outline) could not write `work/deliverable-hashes.toon`: computing a SHA-256 over the outline would have meant reading `.plan` files directly. It skipped the file, so the next run had to re-check every deliverable in full.
- Pass 2 (4-plan) wrote the per-deliverable and `__whole_outline__` hashes with a small ad-hoc Python script in the scratchpad, "because no existing verb computes them".
- Pass 2 also noted that Step 8 of the workflow hard-codes `--phase 3-outline` for the pending-findings count, while the call site was 4-plan. The leaf substituted 4-plan itself.

Two leaves, two different answers to the same step, and one of them outside the script surface.

## Candidate rule / fix

Add a deterministic verb (for example on `manage-solution-outline`) that computes and persists the per-deliverable and whole-outline hashes, and call it from q-gate-validation's hash step. Parameterise Step 8's `--phase` from the activation context instead of the literal `3-outline`. Owner: plan-marshall `plan-marshall/workflow/q-gate-validation.md` and `manage-solution-outline`.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-and-fuzzer-008.md` from plan static-verifier-and-fuzzer (PLAN-10, #32)
