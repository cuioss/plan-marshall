envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=landing
created=2026-07-30T12:04:16Z

## What landed

**Plan**: `plan-less-pr-can-be-opened-but-never-corrected`
**PR**: #1065
**Deliverables**: 7 (D1 gate + D2-D7 implementation)

The plan opened as a narrow ask — `ci pr create` has a plan-less `--body-file` path, its
sibling verbs (`ci pr edit`, `ci pr prepare-comment`, and the widened `ci issue` group) do
not — and D1's GATE was required to evaluate *both* candidate remedies (a plan-less body
channel vs. an explicit adopt verb) rather than silently defaulting to the cheaper one.

D1's population derivation is the load-bearing outcome of this plan: it found the
`--plan-id` binding was **not** a `ci`-local asymmetry at all. Classifying every consumer as
**load-bearing** (resolves a real per-plan artifact) vs. **incidental** (only locates a
working-tree/scratch path) turned up ~18 incidental consumers spread across `build-npm`,
`extension-api`, `manage-architecture`, `manage-solution-outline`, `phase-5-execute`,
`platform-runtime`, `script-shared`, `manage-tasks`, `workflow-integration-git`,
`manage-maven-profiles`, and `ext-self-review-plan-marshall` — each re-deriving the working
tree from a plan id it did not actually need.

What shipped as a result:

- **D2** — one `resolve_plan_context` resolver plus a `NO_PLAN` sentinel in `tools-file-ops`,
  replacing the per-call-site re-derivation.
- **D3** — every "Bucket B" (working-tree-binding) consumer migrated onto that single
  resolver; ~18 production scripts and their test mirrors.
- **D4** — the pre-existing `ci pr create --body-file` outlier absorbed into the sentinel, so
  the plan-less shape is one convention rather than a one-off on a single verb.
- **D5** — sentinel-body retention wired into the steward's `.plan/`-store cleanup surface,
  with the retention default backfilled in `_config_defaults.py`.
- **D6** — a population-derived plugin-doctor check (`_analyze_plan_path_in_scripts.py`,
  incl. a new Form C resolver-bypass detector) so a straggler consumer cannot silently
  reappear.
- **D7** — the describe-side doc contract reconciled across the `ci` / `github` / `gitlab` /
  `git` skill surfaces.

## Signals at finalize

- `signal_qgate_pending_count`: 2
- `signal_automated_review_count`: 1 (8 CodeRabbit findings remediated in-run across
  TASK-013 … TASK-018, on follow-up commits `fa0b5737`, `65a2df32`, `4ad98b41`)
- `signal_script_failure_clusters_count`: 0

## Residue the epic should track

1. **The narrow-request / wide-population gap.** The request was framed as a two-verb `ci`
   asymmetry; the derived population was ~18 consumers in 11 skills. The gate caught it, but
   only because D1 was explicitly mandated to derive the population rather than accept the
   request's framing. This is the epic's confident-signal-hides-a-caveat theme in its
   request-scoping form.
2. **The unselected remedy.** D1's mandate allowed "one now plus a filed follow-up". The
   explicit *adopt verb* (bind a plan to an existing branch/PR) was NOT implemented by this
   plan. If the epic wants it, it needs a separate staged spec — this landing does not carry
   it.
3. **Six candidate lessons** ride alongside this landing as `kind: candidate-lesson`
   messages, all derived from the eight review findings this run remediated. Four of them
   (vacuous parity test, AST detector population gaps, hardcoded dispatch-table mirror,
   unreachable predicate half) are recurrences of archetypes the epic already tracks; two
   (review-body findings outside the diff range, doc drift on a widening argument surface)
   may belong to the sibling `review-apparatus` epic — the plan performs no classification.
4. **`2` Q-Gate findings were still pending** at finalize. They are advisory, but the epic
   should confirm they were dispositioned rather than aged out.
