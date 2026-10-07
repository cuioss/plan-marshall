envelope_version=1
sender_type=plan
sender_id=truth-168-sync-defaults-reverting-remove
epic=truthful-signals
kind=candidate-lesson
created=2026-10-02T15:45:14Z

component=plan-marshall:manage-config
category=bug
created=2026-10-02

# sync-defaults must preserve operator removals and ask before back-filling

When `sync-defaults` merges default step maps into live `marshal.json`, a present-but-partial `steps` map was treated as needing a full seed. The merge re-added steps the operator had deliberately removed via `remove-step`, and reported them as `added` rather than as held or re-added. The plan truth-168 fixed this by distinguishing absent-map seeding from present-map merge, deferring `qgate` lane migration until the owner step is accepted, and reporting `held_for_ask` / `re_added` buckets separately.

Q-Gate evidence: `contract_drift at _cmd_sync_defaults.py:577` (producer emitted `held_for_ask`, `re_added` buckets the SKILL Output TOON did not declare) and the missing-yield `pre-submission-self-review` finding, both fixed in-run.

## Solution

Seed defaults only when the step map key is absent. When the map is present, deep-merge missing keys only, never resurrect `removed_steps` entries without operator accept, and defer legacy `qgate` lane migration until the owner step exists. Declare every emitted bucket (`added`, `held_for_ask`, `re_added`) in the SKILL Output contract.

## Impact

Any config reconciler that merges curated defaults into operator-edited maps. Prevents silent revert of deliberate removals across `phase-5-execute.verification_steps` and `phase-6-finalize.steps`.
