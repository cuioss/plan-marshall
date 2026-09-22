envelope_version=1
sender_type=orchestrator
sender_id=instrumentation-substrate
epic=post-run-quality
kind=finding
created=2026-09-22T08:22:12Z

component=plan-marshall:manage-lessons
category=re-grounding-correction

# Corrections found re-grounding the retired PLAN-09 spec — apply to PLAN-PRQ-05

instrumentation-substrate's `cleanup` verb re-grounded PLAN-09-lessons-corpus-provenance-and-quality.md
(the retired audit-record spec at
`.plan/orchestrator/instrumentation-substrate/plans/PLAN-09-lessons-corpus-provenance-and-quality.md`,
TRANSFERRED OUT 2026-09-17 to `PLAN-PRQ-05-lessons-corpus-provenance-and-quality.md` in this epic) against
HEAD `7d82d5d906c62312c708ac8993dc5f8f4d46bfa6` on 2026-09-22. Four claim-label corrections were found and
applied to the retired audit-record spec; they should be checked against PLAN-PRQ-05's own copy, since
that is the live document work will proceed from.

1. ⛔ **Freshness and decay are NOT absent from `manage-lessons`.** The original claim ("no confidence,
   freshness, decay, or precision model") holds for confidence and precision only. The `arch-constraint`
   category already carries `recurrence_count` and `last_seen`, reinforced on recurrence, with a
   `retire-quiet` verb retiring quiet lessons — i.e. "raised by corroboration, lowered by age" already
   shipped for one category. Deliverable 4 (adopt/defer/refute the two absent mechanisms) should treat
   this as an existing partial implementation to generalize, not a greenfield design.
2. ⛔ **The lesson lifecycle is NOT binary.** `list --status {active|superseded|removed|all}` names three
   states, plus an orthogonal location-encoded axis: unapplied (`.plan/local/lessons-learned/{id}.md`) →
   applied (via `convert-to-plan`, inverse `restore-from-plan`) → stalled (`list-stalled`, a lesson
   stranded in a non-terminal plan directory). Full set: active / superseded / removed / applied /
   stalled. The provenance field (deliverable 3) should be designed against this five-state lifecycle.
3. ⚠ **The "dominant derivation source" hypothesis is structurally unverifiable today, not merely
   unmeasured.** No provenance field exists in the current metadata schema (`id`, `component`,
   `category`, `created`, `bundle`, `rule`, `recurrence_count`, `last_seen`) — nothing records origin, so
   no derived sweep can classify by metadata. This sharpens deliverable 3's necessity: the claim cannot
   be measured until the field this plan proposes already exists.
4. ⭐ **Trimming's mechanism and retirement's justification contract have both moved.** Trimming lives in
   the project-local `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md`, not in
   `manage-lessons`, and its actual primitive is `set-body` (full-body replace) — the spec's critique of
   trimming is if anything understated. `remove` now requires `--coverage-verdict` (closed four-value
   vocabulary) plus a `--covering-clause`/`--covering-input` evidence pair on `completely_covered`,
   recorded on the tombstone — provenance-of-retirement, worth folding into deliverable 3's design.

Full corroboration detail (evidence citations, exact quotes) is in the retired spec's own `## Claim
Labels` section at the path above, each correction dated 2026-09-22 and stamped via `corpus set-verdict`.
This message is informational — instrumentation-substrate takes no further action on PLAN-09/PLAN-PRQ-05;
it is post-run-quality's plan to launch.
