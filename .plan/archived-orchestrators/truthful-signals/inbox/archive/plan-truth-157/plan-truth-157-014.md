envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:42Z

component=plan-marshall:manage-config
category=improvement
bundle=plan-marshall

# A config block regenerated from the default seed loses project-tuned entries invisibly — the key REORDER is the tell

The post-image of `plan.phase-5-execute.verification_steps` in `.plan/marshal.json`
dropped `default:verify:coverage`, which `main` still carried (confirmed by a
two-dot diff against main, not only the three-dot merge-base diff). The same hunk
reordered `per_envelope_budget_tokens` / `verification_steps` / `effort` to sit
after `cost_size_token_table` — the signature of the block being REGENERATED from
the default seed rather than surgically edited, with the project's extra entry lost
in the rebuild.

The effect is silent. No test pins the committed `verification_steps` set (only
fixture and defaults tests touch that key), so every future plan in the repo would
stop running the coverage verification step with nothing failing.

This is the exact class the same change added `_PROJECT_TUNED_ORCHESTRATOR_KNOBS`
to prevent for the sibling orchestrator block — "a tuning change wearing a
surfacing change's clothes" — applied in one block and missed in the other.

Source record: Q-Gate finding `66f749`, phase `6-finalize`, defect_class
`contract_drift`, resolution `accepted`.

## Solution

Two independent moves:

- **Read the reorder as evidence.** A key reorder inside a config hunk that was
  supposed to be a surgical edit is the observable signature of a seed
  regeneration. Diff the block's MEMBERSHIP against the base, two-dot, whenever
  that signature appears.
- **Pin the project-tuned set.** When a guard is added to protect one block from
  seed-regeneration drift, apply it to every sibling block with project-tuned
  entries in the same change, or state why not.

## Impact

On this run the coverage removal turned out to be a deliberate operator decision
made mid-finalize (repeated local build-server memory-pressure failures on coverage
builds), with the rationale living in commit `45da55aab`'s message — so it was
accepted rather than reverted. The lesson is the DETECTION half: the finding could
not tell a deliberate removal from an accidental one from the artifact alone,
because nothing pinned the set either way.
