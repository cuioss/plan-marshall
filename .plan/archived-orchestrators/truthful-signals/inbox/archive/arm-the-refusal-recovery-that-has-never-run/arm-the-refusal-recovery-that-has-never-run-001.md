envelope_version=1
sender_type=plan
sender_id=arm-the-refusal-recovery-that-has-never-run
epic=truthful-signals
kind=finding
created=2026-09-06T16:59:37Z

# Two finalize-time scope defects, both reproduced first-party on PLAN-PR-025B

Filed out of `arm-the-refusal-recovery-that-has-never-run` (review-apparatus / PLAN-PR-025B).
Neither is that plan's surface, so neither was fixed there. Both are **scope-derivation** defects:
each makes a finalize step reason about a file set that is not the one the plan actually changed.

## 1. Declared footprint understates the realized diff, and the sync verb cannot close it

`references.affected_files` declared **19** files; `git diff --name-only origin/main...HEAD` was **21**.
Missing:

- `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/references/stdlib-modules.md`
- `test/plan-marshall/script-shared/test_extension_base.py`

⛔ **`sync-affected-files` added 0 when re-run.** It re-derives from the SOLUTION OUTLINE
(`deliverables_scanned: 5`, `bullets_parsed: 36`), and the outline is what is short — so the verb
is structurally incapable of closing this particular gap. That is the part worth carrying: the
obvious remedy does not work, and a run that reaches for it gets a clean-looking `added_count: 0`
that reads as confirmation.

**Cause, recorded honestly including the orchestrator's share.** The `stdlib-modules.md` row was an
ORCHESTRATOR-DIRECTED addition made mid-execute (TASK-5) to keep an index complete, and no step
re-declared it on the outline. `test_extension_base.py` was touched by TASK-9 beyond its declared
step targets. So scope moved during execute and nothing re-declared it — the declared footprint is
written once at outline and has no writer after that.

**Consequence.** Every finalize step deriving scope from `affected_files` under-scopes on such a
plan. On this run `project:finalize-step-plugin-doctor` detected it and widened to a superset BY
HAND (6 skill dirs → 7), which is the correct behaviour but is per-step and does not carry.

Second independent corroboration of the `affected_files` under-recording archetype already on
record from PLAN-CIS-001.

## 2. The self-review surfacer passes no `--base-branch`, inflating scope ~6x on any rebased plan

`pre-submission-self-review.md` Step 1 invokes the surfacer with no `--base-branch`, so it defaults
to local `main`. On this run local `main` was `66320e70d` while `origin/main` was `1c4e6febb`, and
the branch had been rebased onto `origin/main` by `finalize-step-sync-baseline` (order 3).

Result: `files_in_scope: 136` against a real diff of **21** — roughly 115 files of absorbed upstream
the plan never touched.

**Why it matters beyond noise.** A ~6x over-scope is a direct driver of the runaway this step is
already known for: a prior plan fired self-review **19 times and consumed all 17 loop-back
iterations**, with the finalize gate costing 81% of a 13.9M-token run. The self-review leaf detected
the inflation itself and re-ran with `--base-branch origin/main`, but that correction is
per-invocation and depends on the leaf noticing.

**Fix**: pass `--base-branch origin/{base_branch}` at the Step 1 call site.

⭐ This is a fresh reproduction of lesson **`2026-09-03-05-002`**, which is already in the corpus and
still open. The lesson predicted it; this run observed it. Note the interaction with the sibling
`finalize-step-sync-baseline` step, which is what creates the local-vs-origin divergence in the
first place — the two steps are individually correct and jointly wrong.

## Disposition

Recorded on the originating plan as `f94f11` and `d66348`, resolved there as `taken_into_account`
with this transfer named. Neither blocks that plan's merge; both are real and unowned.
