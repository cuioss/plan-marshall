> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Migrate the remaining dispatch callers to the resolve seam

**Epic:** truthful-signals
**Branch prefix:** chore — maintenance/refactor of workflow-doc dispatch instrumentation (harness-assigned `claude/*` branch kept as-is in the cloud session)

## Problem

Plan 280 moved the `[DISPATCH]` audit emission **into the resolution seam**: `effort resolve-target`
now emits both audit surfaces (the `work.log` `[DISPATCH]` line and its paired `decision.log`
resolution record) per firing when the caller passes the dispatch context (`--workflow`/`--plan-id`/
`--caller`). It migrated the emitter and exactly two re-fire dispatch sites (`execution.md`
phase-5-execute and verification-feedback), and **deferred every other caller** to follow-up, keeping
each on its still-valid hand-written path.

Fourteen dispatch sites across eight workflow docs still hand-write a `manage-logging work
--message "[DISPATCH] …"` step next to their `effort resolve-target` call. Each is exactly the
per-role blind spot the seam exists to close: a step that re-fires N times (a q-gate `until_clean`
loop, a finalize loop-back, a verification re-fire) logs its `[DISPATCH]` **once** — the re-fires
re-point at the prior `Task:` block without re-running the hand-written logging line, so they vanish
from the audit trail. This is the same "machinery silently loses the information it was handed"
defect the epic targets.

The emitter (`manage-config/scripts/_cmd_effort.py` `_emit_dispatch_records` +
`cmd_effort_resolve_target`) is already in place and tested (280); it emits when `--workflow` is
present and derives the emitted `role=` from `--role` (else `--phase`, else the resolver payload
role, else `default`). This plan is instrumentation-only: it touches **no** script and adds **no**
test — it rewires the fourteen doc-level callers onto the existing seam.

## Goal

Every execution-context dispatch site in the plan-marshall workflow docs emits its `[DISPATCH]`
evidence from the resolve seam — per firing, re-fire-safe — with **no** hand-written
`manage-logging work "[DISPATCH]"` step remaining. A re-fire that re-resolves re-emits by
construction, so the audit trail no longer loses re-fired dispatches at any of these sites.

## Deliverables

Each site's migration is: **add** `--workflow {doc} --plan-id {plan_id} --caller {caller}` to the
resolve it already performs (keeping the resolve's existing `--role`/`--phase`/`--default` so the
resolved target is byte-identical), **delete** the co-located hand-written `[DISPATCH]` block, and
**update** the surrounding prose to name the seam as the emitter. The emitted `role=` is preserved by
choosing the resolve's `--role`/`--phase` to reproduce the old label — with two deliberate,
audit-safe corrections noted in D1.

1. **D1 — Phase 2–4 planning dispatches (6 sites).** `plan-marshall/workflow/planning.md`
   (phase-2-refine dispatch; phase-2 q-gate-validation) and `plan-marshall/workflow/planning-outline.md`
   (phase-3-outline dispatch; phase-3 q-gate; phase-4-plan dispatch; phase-4 q-gate). The phase
   dispatches keep `--role phase-{N}` and reproduce `role=phase-{N}` exactly. The two q-gate sites
   whose hand-written line drifted to `role=q-gate-validation` (`planning.md` phase-2 q-gate;
   `planning-outline.md` phase-4 q-gate) resolve `--role phase-{N}` and therefore now emit
   `role=phase-{N}` — the value `dispatch-logging.md` § "Field semantics" specifies (*the role-key the
   caller resolved against*), matching the already-correct phase-3 q-gate site. The `[ATTEMPT]`
   pre-dispatch lines present at the two `planning.md` sites are out of scope and left intact.
   *Done when:* neither file contains a `--message "[DISPATCH]"` step; each of the 6 resolves carries
   `--workflow`/`--plan-id`/`--caller plan-marshall:plan-marshall`; the emitted `role=`/`workflow=`
   for each site is confirmed field-for-field against the old line (equal, or the documented q-gate
   correction).

2. **D2 — Phase-6-finalize generic dispatch templates (3 sites).** `phase-6-finalize/SKILL.md`: the
   agent-suitable dispatched-step block, the DISPATCHED project/skill branch, and the wait-region
   unified-triage hook. The two generic templates resolve `--phase phase-6-finalize` and, per their
   own prose, label `role=default` when no `--role` is passed; the seam given a bare `--phase` would
   emit `role=phase-6-finalize`, so the migrated resolve passes an **explicit** `--role {role}` (the
   value `default` for the no-sub-key case, otherwise the step's sub-key) — `default` is a registered
   sub-key resolving to the identical target, so the label is preserved with no target change. The
   unified-triage hook keeps `--role verification-feedback`.
   *Done when:* the file contains no `--message "[DISPATCH]"` step; each of the 3 resolves carries
   `--role {role}`/`--workflow`/`--plan-id`/`--caller plan-marshall:phase-6-finalize`; the generic
   templates document that `{role}` is `default` or the sub-key.

3. **D3 — Phase-6-finalize workflow bodies (3 sites).** `pre-submission-self-review.md`'s inner
   LLM-cognitive-phase dispatch migrates like D2 (`--role default`). `adr-propose.md` and
   `lessons-capture.md` each carry a "### `[DISPATCH]` log line (emitted by the dispatcher)" section
   that **restates** the line the SKILL.md dispatcher emits (`role=post-run-review`); with D2 landed
   that hand-written restatement is stale, so each section is rewritten to describe the seam emission
   (the dispatcher's resolve carries `--workflow`, so the seam writes both records — no separate step).
   *Done when:* `pre-submission-self-review.md` has no `--message "[DISPATCH]"` step and its resolve
   carries the dispatch context; the two echo sections no longer show a hand-written `manage-logging
   work "[DISPATCH]"` block and instead point at the seam emission.

4. **D4 — Outline and pr-doctor callers (2 sites).** `phase-3-outline/standards/outline-workflow-detail.md`
   (detect-change-type dispatch, which resolves `--default`; the seam's `role=` falls through to
   `default` with no `--role` needed) and `workflow-pr-doctor/SKILL.md` (`--role verification-feedback`).
   *Done when:* neither file contains a `--message "[DISPATCH]"` step; each resolve carries the
   dispatch context with the caller notation matching its old `[DISPATCH]` caller prefix
   (`plan-marshall:phase-3-outline`, `plan-marshall:workflow-pr-doctor`).

5. **D5 — Re-fire loop wording.** Where a q-gate `until_clean` re-run or a verification/triage re-fire
   is described as "re-dispatch via the same `Task:` envelope" (implying the cached target is reused
   without re-resolving), reword it to "re-run the resolve (which re-emits per firing) and
   re-dispatch," so the doc no longer instructs the exact envelope-reuse the seam's re-fire guarantee
   depends on being avoided.
   *Done when:* no migrated re-fire path instructs reusing a cached `Task:` block in place of
   re-running the resolve; each such loop names the resolve as the per-firing re-emit point.

## Out of scope

- **The emitter and its tests.** `_cmd_effort.py` / `manage-config.py` and
  `test_dispatch_seam_emission.py` shipped in 280 and are unchanged here. This plan adds no test —
  the seam's behaviour is already covered; the callers are workflow prose with no unit-test surface.
- **The dispatch audit detector.** `plan-retrospective/standards/execution-context-dispatch-audit.md`
  and its checks are owned by `code-intelligence-substrate` plans (280's ownership block). This plan
  changes only emitters; it relies on — and does not alter — the audit's documented pairing rule.
- **The `[ATTEMPT]` pre-dispatch lines** in `planning.md`. They are a separate marker, not the
  `[DISPATCH]` contract, and are left intact.
- **`branch-cleanup` and other inline-classified steps.** They never resolve a target and carry no
  `[DISPATCH]` line by design (inline classification); their absence from the trail is owned by the
  detector/roster concern, not the emitter.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — D1 (2 sites)
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` — D1 (4 sites), D5
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — D2 (3 sites), D5
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — D3 (1 site)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/adr-propose.md` — D3 (echo)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md` — D3 (echo)
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/outline-workflow-detail.md` — D4 (1 site)
- `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/SKILL.md` — D4 (1 site)

No `*.py` is expected to change — this is a workflow-doc (skill) change, so the local build gate is
skipped (`*.py`-only) while the change still gets full bot review (a skill is code).

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Exactly 14 hand-written `--message "[DISPATCH]"` sites remain across these 8 files | OBSERVED | `grep '--message "\[DISPATCH\]'` over `marketplace/bundles` on `origin/main` — 14 hits in these 8 files |
| The seam emits `role=` from `--role` → `--phase` → payload role → `default` | OBSERVED | `_cmd_effort.py` `cmd_effort_resolve_target` (emission_role) + `_emit_dispatch_records` (`role_display`) |
| `resolve-target` accepts `--workflow`/`--plan-id`/`--caller` alongside `--default`/`--role`/`--phase` (no mutually-exclusive group) | OBSERVED | `manage-config.py` `effort_resolve_target` sub-parser (lines ~471–520) |
| Emitting `role=phase-{N}` (not `q-gate-validation`) for a q-gate dispatch creates no audit finding | OBSERVED | `execution-context-dispatch-audit.md` § "Pairing rule" (A↔B share the seam emitter, so pair verbatim) + § "Detection Logic" (`dispatch_coverage` is scoped to finalize/execute steps, not q-gate) |
| `--role default` and bare `--phase phase-6-finalize` resolve to the identical target | OBSERVED | `_cmd_effort.py` `_resolve_level` (bare-group and `default` sub-key both walk to `plan.<phase>.effort.default`) |

## Verification

There is no unit-test surface (workflow-doc prose). Verification is structural and by-reading:

1. **Structural sweep:** `grep '--message "\[DISPATCH\]'` over `marketplace/bundles` returns **zero**
   after the migration (every hand-written emission removed; the echo sections rewritten). Contrast
   with the 14-hit pre-state.
2. **Per-site field check:** for each of the 14 sites, the migrated resolve carries `--workflow`, and
   the seam-emitted `role=`/`workflow=`/`caller` reproduce the old hand-written line field-for-field —
   except the two documented q-gate `role=` corrections (D1), which are confirmed audit-safe against
   the pairing rule.
3. **Pre-PR verification sub-agent (lane Step 6):** an independent read of the diff against this plan,
   plus a beyond-diff sweep for any prose/example elsewhere that still teaches the old hand-written
   pattern for these sites (e.g. `dispatch-walkthrough.md`, `api-reference.md`) and is now stale.
4. **Merge-queue build:** the docs-only change is verified by the queue's `merge_group` run before it
   lands (the local `*.py`-only gate is skipped).

## Notes

- Follow-up to plan 280 (`280-the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one`),
  whose run report enumerated these sites as deferred residue. This plan was authored from the
  operator's direct request in a cloud session (not handed off as a pre-existing plan file); the run
  report records that provenance.
- The canonical emitter contract this plan wires callers onto is
  `ref-workflow-architecture/standards/dispatch-logging.md` § "Emission contract" / "Canonical
  invocation"; the two already-migrated reference sites are in `plan-marshall/workflow/execution.md`.
