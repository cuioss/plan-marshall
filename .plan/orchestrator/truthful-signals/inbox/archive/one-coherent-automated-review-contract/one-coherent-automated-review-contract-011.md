envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:05:36Z

component=plan-marshall:platform-runtime
category=bug
bundle=plan-marshall

# `session capture` overwrites an existing session_id, so a late-running dispatched step destroys the plan's transcript pointer

## Observation

`plan-retrospective` SKILL.md Step 1 mandates
`platform_runtime session capture --plan-id {plan_id}` and describes it as a read
("On Claude Code the runtime reads the stored `session_id`"). It does not only read — it WRITES,
unconditionally.

Observed in `one-coherent-automated-review-contract` (PLAN-92):

- `status.metadata.session_id` before the retrospective ran: `e666ac2e-768e-4004-b736-36ebe79b012e`
  — the orchestrating session that executed phases 1-6, stamped at `work.log` 14:36:48Z and
  re-stamped 15:06:13Z.
- The retrospective is a DISPATCHED leaf and therefore runs in its own session. Its mandated
  `session capture` call replaced the value with `85147d4b-80c3-4132-8209-641263eb5173`
  (`work.log` 04:51:21Z, `[MANAGE-STATUS] Metadata: session_id=...`).

The clobbered value is the pointer `manage-metrics enrich` uses to locate the parent transcript and
attribute per-phase token usage across phases 1-5. After the overwrite it points at a transcript
that contains only the retrospective. Any later `enrich` will silently attribute near-zero and
report success.

This plan was doubly exposed: `work.log:3` records
"session_id not captured at plan-init — phase-6-finalize will attempt a late session capture", so
the correct value had itself only just been recovered by the late-capture path before the
retrospective overwrote it.

## Do this instead

- **Make `session capture` write-once.** If `status.metadata.session_id` is already populated, keep
  it and return the stored value; report `stored: false` so the caller can tell a read from a
  write. A dispatched leaf must never be able to overwrite the orchestrating session's id.
- If a leaf's own session id is genuinely wanted, store it under a **distinct** key
  (e.g. `retrospective_session_id`), never over the plan-level pointer.
- Fix the SKILL prose to match the behaviour, or fix the behaviour to match the prose — currently
  Step 1 documents a read and performs a write.

## Recurrence context

Epic theme `truthful-signals`: the call returns `status: success, stored: true` while destroying the
one datum that makes downstream token attribution meaningful, and the resulting `enrich` run will
report success over a transcript that never saw the work.
