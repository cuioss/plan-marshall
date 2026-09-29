envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:59Z

# Loop-back fix tasks carry no envelope_id, and no doc says how to dispatch them

**Observed (plan-12-tool-triage, finalize → 5-execute loop-back):** the wait-region unified triage (`verification-feedback`, `producer=finalize-feedback`) allocated TASK-12..18, and the operator-chosen split added TASK-19 via `prepare-add`/`commit-add`. All eight carry `cost_size: null`, `predicted_cost_tokens: null`, `envelope_id: null`.

The phase-5 contract is envelope-bounded: the orchestrator drives exactly `envelope_count` dispatches, each passing an assigned `envelope_id`, and the executor runs only tasks whose `envelope_id` equals it (execution.md § "Execute Phase"; phase-5-execute SKILL § "Deterministic exit clause"). Neither document says what to pass for tasks created after phase-4 packing. `manage-tasks pack-envelopes` is a phase-4 verb that re-packs the whole plan (done tasks included) and requires `derive-cost-size` first — nothing sanctions running it on a loop-back.

**What the orchestrator did:** dispatched one envelope with `envelope_id: null`, relying on null-equality to group the eight unpacked tasks — an improvisation, recorded here.

**Also observed:** phase-6-finalize SKILL item 7b's 5-execute branch says "Dispatch the execute pipeline inline by re-loading `phase-5-execute`: `Skill: plan-marshall:phase-5-execute`", while phase-5-execute's own SKILL says the document IS the dispatched envelope workflow and must be wired as the `workflow:` of an `execution-context` Task dispatch. The two instructions contradict; the orchestrator followed the envelope-dispatch form.

**Suggested fix directions:** have the triage allocation path (and `commit-add` generally, when the plan is past phase-4) stamp cost + a fresh `envelope_id`; or document `envelope_id: null` as the sanctioned "unpacked loop-back group"; and align 7b's wording with the envelope-dispatch contract.
