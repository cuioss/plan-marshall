envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:28:13Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_aspects=invariant-summary,artifact-consistency

# The post-run-band dirty-tree guard excludes `.plan/`, but `.plan/project-architecture/**` is TRACKED

## Context

The `post_run_review: true` finalize steps are trusted to write nothing pushable, and the trust is checked rather than assumed. Item 5f sub-item (0) observes the main checkout on return and reports "any dirty **TRACKED** path **outside `.plan/`**" as a warning plus a finding. Both `lessons-capture` and `finalize-step-preference-emitter` cite that guard by name as the reason their `mutates_source: false` declaration is verified rather than believed.

The carve-out assumes `.plan/` is untracked runtime state. In this repository it is not, in exactly one place — and it is the one place a post-merge step is most likely to dirty.

First-party measurement, taken in this envelope on the main checkout after the merge:

```
 M .plan/project-architecture/default/enriched.json
 M .plan/project-architecture/plan-marshall/enriched.json
```

Both are **tracked** (` M` = tracked, modified, unstaged). Their content is architecture-hint prose — six added hints of the `architecture enrich best-practice` / `insight` shape, e.g. *"The project treats q-gate findings as a standing consideration…"*, *"Scope-realism findings recur and are folded into the work…"*.

The last commit touching `default/enriched.json` is **`468b8227`, 2026-07-30** (`#1065`). So these edits have been sitting uncommitted on `main` for up to nine days, across many plan finalizes, and every one of those finalizes' post-run-band guards passed clean over them — by design, because the paths are inside `.plan/`.

A second surface reports the same false clean from the other side. This plan's `architecture-refresh` logged:

> Tier 0 - `.plan/project-architecture` clean after discover, no commit needed

That verdict is true and useless: `architecture-refresh` runs pre-push, in the **worktree**, whose copy of the tracked file came from the branch and is clean. The drift accumulates on **main**. The store the check names is not the store that drifts.

## Root cause

`.plan/` is used as a proxy for "not pushable". The proxy holds for plan directories, findings, locks, and worktrees — and fails for `.plan/project-architecture/**`, which is deliberately tracked so architecture knowledge is shared. The guard's predicate is therefore path-prefix-based where it needed to be **tracked-ness**-based: `git status --porcelain` already distinguishes the two, and the guard already reads it.

The consequence is precisely the failure mode `source-edit-pushability.md` exists to prevent — an unpushable tracked-source edit stranded on `main` — reached not by a step violating the contract, but by the contract's own verifier being unable to see the violation.

Note what this does **not** claim: the writer of these particular edits is not determinable from this plan's record. `finalize-step-preference-emitter` is not a candidate in its current form — it declares `mutates_source: false`, makes no `architecture enrich` call, and its own document states that reintroducing one post-merge "would reproduce `#990`'s defect exactly". The plausible producers are the operator-run `audit-archived-plan-retrospectives` preference-pattern detector (same hint shape, same sink, no merge gate to respect) or a pre-`#990` run. **The attribution is open; the guard gap is not.**

## Proposed action

- Change the post-run-band guard's predicate from *"tracked AND outside `.plan/`"* to *"tracked"*, full stop. A tracked path is pushable regardless of where it lives, which is the property the guard is actually about. `git status --porcelain` already reports exactly this set.
- Scope `architecture-refresh`'s Tier 0 cleanliness check to the checkout that can actually accumulate the drift, or state which checkout it observed. A clean verdict over the wrong tree is worse than no verdict.
- Independently: decide whether the accumulated hints on `main` should be committed or discarded, and give the enrichment sink an owner for that. Nine days of unshared, machine-local architecture knowledge in a tracked file is a silent single-machine dependency — the hints are lost to every other checkout and to any `git checkout`/`stash` that touches them.

## Evidence

- `git -C {repo} status --porcelain` in this envelope — the two ` M` rows above, main checkout, post-merge
- `git -C {repo} diff .plan/project-architecture` — 6 insertions, 2 deletions; all added lines are architecture-hint prose
- `git -C {repo} log -3 -- .plan/project-architecture/default/enriched.json` — last commit `468b82279`, 2026-07-30 (`#1065`)
- decision.log `5b0178` — "(architecture-refresh) Tier 0 - .plan/project-architecture clean after discover, no commit needed", logged 17:56 in the worktree
- `phase-6-finalize/workflow/lessons-capture.md`:24 and `standards/finalize-step-preference-emitter.md`:223-228 — both cite the guard as "any dirty TRACKED path outside `.plan/`"
- `standards/source-edit-pushability.md` § "The discover-after-merge rule" — the contract this gap defeats
