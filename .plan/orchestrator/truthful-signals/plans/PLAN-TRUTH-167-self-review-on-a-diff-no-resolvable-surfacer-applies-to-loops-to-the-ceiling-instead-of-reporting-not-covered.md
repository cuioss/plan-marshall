# PLAN-TRUTH-167: `pre-submission-self-review` on a diff no resolvable surfacer applies to loops to the ceiling instead of reporting "not covered"

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-15 from three inbox messages describing one failure from two consuming repositories, all
on plan-marshall `0.1.1670` (which carries the shipped PLAN-TRUTH-148 verifier changes):

- `api-sheriff-pro-forma-integration-test-fixes-001.md` — API-Sheriff (Maven/Java), a live finalize: the
  verifier returned `accepted` + `may_close: no` because the surfacer saw 19/20 files as `other`; the
  operator force-closed with an improvised override. Carries three separable defects.
- `lessons-handling-26-09-04-01-057.md` — Token-Sheriff PR #744: 4 files, all class `other`, zero
  detectors; ~28 minutes, ended on an operator override recorded "NOT a converged close".
- `api-sheriff-deployment-configurability-011.md` — API-Sheriff epic ledger: every Java plan in that epic
  passed this step with a structurally uninformative green (the observability half was fixed by PR #1397;
  the coverage half never was).

## Objective

**On a consumer diff, the step selects the plan-marshall-domain surfacer merely because its notation
resolves, runs it over files it has no detectors for, and then enters a loop whose verifier refusal names a
property no further round can change — so it can only end at `max_iterations` (blocking push) or at an
operator override the workflow does not document.**

The truthful record already exists: the zero-generator fallback's **not-run** verdict
(`"self-review not run: no surfacer implementor resolved"`). It is unreachable here because selection keys
on *resolvable*, not *applicable*. A third defect widens the scope the surfacer examines: after
`finalize-step-sync-baseline` rebases onto `origin/{base}`, the surfacer — and `manage-references
compute-footprint` — still diff against local `{base}`, attributing upstream commits to the plan.

⛔ **Out of scope, recorded so it is not assumed covered:** building a Java (or any non-plan-marshall)
`ext-self-review-*` surfacer. This plan makes the step tell the truth about the gap; it does not close the
gap.

## Deliverables

Five deliverables. D0 is a gate.

**D0 — GATE: derive the applicability signal and the round-invariant refusal population.** Decide what makes
a resolvable implementor *applicable* to a footprint (a declared content-class domain on the extension
point, or `delta_coverage.by_class` showing the whole scope landed in `other`), and enumerate every
verifier-refusal reason that is invariant across rounds at an unchanged HEAD (surfacer domain, content
class, zero detectors). Publish both.

**D1 — Selection gates on applicability, not resolvability.** A resolvable implementor whose domain covers
none of the footprint's content classes routes to the not-run verdict — or to a distinct
`not_covered` / `no_applicable_detectors` verdict if D0 finds the two must differ — non-blocking, with the
coverage gap stated in `display_detail`.

**D2 — A round-invariant refusal is a terminal outcome, not a `loop_back`.** When the verifier's
`further_round_owed` / `verdict_refused` rationale names a D0 round-invariant property, the step records the
gap and closes once (or escalates once) instead of consuming the iteration budget. This is the documented
branch the two operator overrides improvised. Coordinate with PLAN-TRUTH-147's convergence-signal folds:
this deliverable owns the round-invariant case; 147's general convergence signal consumes it.

**D3 — The surfacer and `compute-footprint` diff against the base the branch was actually rebased onto.**
After `finalize-step-sync-baseline`, resolve the base as `origin/{base}` (or the merge-base with it), never
the stale local `{base}`, so upstream commits stop entering the plan's footprint.

**D4 — The not-covered verdict is machine-readable in the landing facts**, so a consuming epic can tell "no
surfacer applied" from "reviewed clean" without reading `may_close=no` from a step fact.

## Claim Labels

- OBSERVED: Step 1 selects "the first implementor whose notation **resolves in the current executor**" —
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` line 115,
  read at `7a028157e`.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:119 still reads Select the first implementor whose notation resolves in the current executor (line moved from 115).
- OBSERVED: the zero-generator fallback and its not-run verdict exist but are reached only when NO
  implementor resolves — `pre-submission-self-review.md` lines 177–179 and 395, read at `7a028157e`.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:181-183 carries the zero-generator fallback and the not-run verdict string, gated on when NO discovered implementor resolves (lines moved from 177-179).
- OBSERVED: `verdict_refused`, `further_round_owed`, and `verifier_unavailable` all map to `loop_back` —
  `pre-submission-self-review.md` lines 503–505, read at `7a028157e`.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:505-509 is a three-row table mapping verdict_refused, further_round_owed and verifier_unavailable all to recorded outcome loop_back, restated as absolute at line 518.
- OBSERVED: the plan-marshall surfacer defaults its base to local `main` —
  `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py`
  line 285 (`base_branch = args.base_branch or 'main'`), read at `7a028157e`.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: self_review.py:285 is exactly base_branch = args.base_branch or main - unchanged, same line number.
- OBSERVED: `ext-self-review-plan-marshall` is the only surfacer implementor; no detector reads Java (per the
  sender's `git ls-tree` sweep at `7a028157e`, corroborated by directory listing at staging).
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: architecture search --content over 3097 files (clean coverage) shows exactly one implementor bundle, pm-plugin-development:ext-self-review-plan-marshall; no Java/other-domain surfacer exists.
- HYPOTHESIS: `manage-references compute-footprint` resolves `--base-ref` to local `{base}` after a rebase
  onto `origin/{base}` — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_cmd_compute_footprint.py` § the base-ref
  default (verify-at-outline).
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_compute_footprint.py:69 calls resolve_base_ref, which (_references_core.py:167-176) falls back to the bare LOCAL branch name and finally the literal main. Never origin/{base}. HYPOTHESIS confirmed.
- HYPOTHESIS: the extension point declares no content-class domain an implementor could be matched on —
  confirm/refute at `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`
  § the implementor contract (verify-at-outline).
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: ext-point-self-review-surfacing.md declares an implementor via implements: frontmatter plus a CLI contract only; no content-class/domain declaration exists for selection to match on. delta_coverage per-content-class counts are an OUTPUT field, not an applicability declaration.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — selection, verdicts, verifier dispositions (D1, D2, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — the applicability declaration (D0, D1) (verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py` — base resolution and declared domain (D1, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_cmd_compute_footprint.py` — base resolution (D3) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py` — `resolve_base_ref` (line 171-176) and `compute_plan_branch_diff` (line 241) plus its docstring guarantee (D3, folded 2026-09-17)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — the not-covered fact key (D4) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` and `test/pm-plugin-development/ext-self-review-plan-marshall/` — coverage (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Shares `pre-submission-self-review.md` with staged PLAN-TRUTH-147 (convergence-signal folds) — never pair
  them in one `next` block; D2 states the ownership split.
- Shares `manage-references/scripts/` with staged PLAN-TRUTH-145 — sequence.
- Running PLAN-TRUTH-166's D0 may read the plan footprint; if D3 lands first, 166 consumes it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-167-self-review-on-a-diff-no-resolvable-surfacer-applies-to-loops-to-the-ceiling-instead-of-reporting-not-covered.md"
```

## ⭐ FOLDED 2026-09-17 — D3 IS NOW FIRST-PARTY, WITH THE SOURCE LINES AND A SHIPPED CONSEQUENCE

Forwarded from `truth-166-architecture-refresh-migration-churn-003.md` and
`lessons-handling-26-09-04-01-066.md`. Expected Surface extended in the same act (`_references_core.py`,
above). ⛔ D3 was a HYPOTHESIS when this spec was staged; it is now OBSERVED, and its consequence has
been seen in a merged PR.

**The mechanism, named exactly (`-003`).** `resolve_base_ref` falls back to `references.base_branch`, the
bare LOCAL branch name (`main`), with a final fallback to the literal `'main'`; `compute_plan_branch_diff`
then runs `{base_ref}...HEAD`. That three-dot form is chosen precisely to exclude files absorbed from
upstream — and its docstring asserts that guarantee unconditionally. The guarantee holds only while local
`main` is level with the remote. After `finalize-step-sync-baseline` rebases onto `origin/main`, local
`main` is an ANCESTOR of HEAD, so every upstream commit between the two lands on the HEAD side and is
attributed to the plan. ⭐ **The workflow outruns its own anchor**: `branch-cleanup` is what advances local
`main`, and it runs near the END of finalize, so the whole middle of the phase diffs against a stale ref.
The landed plan recorded `upstream_commit_count: "3"` while `base_branch` stayed `main`.

**The shipped consequence.** `finalize-step-simplify` proposed dead-branch removals in three files that had
arrived from upstream `main` (`effort_pins.py`, `runtime_info.py`, `argparse_surface.py`) — outside the
plan's declared surface. All three were reverted before the PR landed, so nothing shipped; the defect is
that the step was handed a footprint that included them. D3 additionally corrects
`compute_plan_branch_diff`'s docstring, which states its guarantee without the staleness precondition it
depends on.

**Confirm-and-close on the older `affected_files` observation (`-066`).** A 2026-09-08 Token-Sheriff
observation held that `references.affected_files` under-records a landing's realized footprint. **Answer:
superseded on the key it named** — `affected_files` is the declared MUTATION half, and the realized side
now has its own derived key (`realized_footprint`), captured by `capture-footprint` inside
`branch-cleanup` (finalize step 13), i.e. AFTER the review-fix rounds that the original observation said an
early capture would miss. ⛔ **Not fully closed, though**: that capture takes a `--base-ref`, so it inherits
exactly the staleness D3 fixes. The under-recording did not survive under a new key; the base-ref defect it
would have been measured with did.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
