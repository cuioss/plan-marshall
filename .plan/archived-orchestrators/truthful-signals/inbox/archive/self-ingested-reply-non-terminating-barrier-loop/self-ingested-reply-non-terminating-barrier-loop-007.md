envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:18:38Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# The retrospective's own coverage check reports 0% recall for a footprint it never resolved

## Observation

`check-artifact-consistency.py` reported `affected_files_recall: fail — "Recall 0% below 70% threshold"` for this plan, with `declared: 4, found: 0`. The plan's declared set and its actual merged footprint are **identical** — all four files in `references.affected_files` appear verbatim in the merge commit `978afd18`. Recall was in fact 100%.

The 0% comes from `_resolve_footprint()`, whose three-tier resolution is:

1. live diff from `status.metadata.worktree_path` — **the worktree no longer exists**, `branch-cleanup` removed it;
2. legacy `references.modified_files` — **absent**, that ledger key was removed;
3. **empty set**.

Tier 3 fires and the empty set is fed straight into `recall = len(declared & actual) / len(declared)` = 0.0, which then renders as a substantive threshold failure.

## Why it matters — this is not a one-off

`plan-marshall:plan-retrospective` sits at position **17** in `manifest.phase_6.steps`; `branch-cleanup` sits at position **16**. The worktree is therefore gone by construction every time the retrospective runs in the normal finalize flow. The check is not occasionally wrong — it reports `fail` with 0% recall for **every** plan, and has no way to report anything else.

The sharpest part: the **sibling check in the same file already models this correctly.** `check_affected_files_exact_match` explicitly returns `inconclusive` for the both-empty case with the docstring rationale *"two empty sets are trivially equal whether the plan really touched no files or the parser and the footprint resolver both failed — so it reports `inconclusive` rather than a vacuous `pass`."* The recall check consumes the same unresolved footprint and turns it into a confident `fail`.

## Corrective rule

`_resolve_footprint` must distinguish **"resolved to empty"** from **"could not resolve"**, and `check_affected_files_recall` must return `inconclusive` (never `fail`) on the second. Two concrete options, not mutually exclusive:

- Add a merge-commit resolution tier: derive the footprint from the PR merge sha (recorded at branch-cleanup) via `git show --name-only {merge_sha}`. This makes the check *work* post-cleanup instead of merely failing honestly.
- Return a sentinel (`None` rather than `set()`) from tier 3 and have both consumers report `inconclusive`.

## Evidence

- `check-artifact-consistency.py` `_resolve_footprint` docstring, tiers 1-3; `check_affected_files_recall` line ~310-324.
- This plan's fragment: `declared: 4, found: 0, recall_pct: 0.0, missing[4]` — the four "missing" files are exactly the four merged files.
- `execution.toon` `phase_6.steps`: `branch-cleanup` at index 15, `plan-marshall:plan-retrospective` at index 16 (0-based).
- Contrast: `check_affected_files_exact_match` `inconclusive` branch in the same module.
