> ⛔ **MERGED OUT 2026-09-18 (cleanup A5) — this spec is RETIRED and must not be launched.**
> Its substance now lives in **PLAN-TRUTH-171** as D5a/D5b: state writers that fabricate, collide or fail silently — the same workflow-integration-git sibling pair.
> The deliverables were carried, not summarised, and this spec's own gate collapsed into the
> receiving spec's D0 rather than being duplicated. This file stays on disk unchanged below the
> line — a superseded spec is never deleted. Its queue row is `parked`, because
> `queue --transition` cannot write `superseded` (see PLAN-TRUTH-143 D9).

# PLAN-TRUTH-164: `worktree-remove` is not the symmetric counterpart of `worktree-create`, and the stale `use_worktree`/`worktree_path` it leaves behind now has five sightings

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-15. This defect has been epic-tracked since at least PLAN-TRUTH-089's shipped run (two
first-party archived sightings, `-126`/`-093`) and was carried forward in `epic.md` as `-024` — "the stale
`worktree_path` reaches FOUR independent sightings... fully diagnosed, UNOWNED, and the count measures the
DELAY, not the defect." PLAN-TRUTH-148's own finalize run (2026-09-15) hit it a FIFTH time: `metadata.
use_worktree`/`worktree_path` still pointed at a worktree `branch-cleanup` had already deleted, and three
dispatched post-merge finalize steps correctly REFUSED rather than operate against the wrong tree. The
operator worked around it in-session by setting `use_worktree=false` after `branch-cleanup`, which resolved
every step after that — a workaround, not a fix, and the fifth recurrence of an already-fully-diagnosed
defect this epic has left unowned for too long.

## Objective

**`worktree-remove` deletes the physical git worktree but never clears the plan's `status.json` metadata
fields (`use_worktree`, `worktree_path`, and the related `worktree_branch`) that record a worktree is in
use and where it lives — so every reader of those fields after a `worktree-remove` sees a confident,
well-formed answer pointing at a tree that no longer exists.** `worktree-create` sets these fields when it
provisions a worktree; `worktree-remove` has no corresponding clear, so the two verbs are not symmetric —
the root cause this epic named at the second sighting and has not yet fixed.

The FAIL-CLOSED behaviour this produced in PLAN-TRUTH-148 — three dispatched post-merge steps refusing
rather than silently operating against a deleted tree — is the CORRECT response to stale metadata, and is
NOT what this spec changes. The defect is that the metadata goes stale in the first place, forcing every
downstream reader to defend against it (or, worse, not defend against it and silently read the wrong tree)
instead of the producer simply not publishing a false claim.

## Deliverables

Two deliverables. D0 is a gate.

**D0 — GATE: derive the population of readers that consult `use_worktree`/`worktree_path`/`worktree_branch`
after finalize's `branch-cleanup` step, and confirm the fail-closed refusals PLAN-TRUTH-148 observed are
the general shape rather than one lucky instance.** Five sightings are recorded but the reader population
has never been enumerated. Publish it before choosing where the clear belongs.

**D1 — `worktree-remove` clears `use_worktree`/`worktree_path`/`worktree_branch` (or an equivalent honest
marker) in the same act that removes the worktree, making it the symmetric counterpart `worktree-create`
already is.** Do not weaken any downstream reader's fail-closed refusal — the fix is at the producer, so
the metadata a downstream reader consults is honest, not so that a downstream reader trusts it less
carefully.

## Claim Labels

- OBSERVED: `git-workflow.py`'s `cmd_worktree_remove` (the `worktree-remove` implementation) contains no
  call clearing `use_worktree`, `worktree_path`, or `worktree_branch` in `status.json` metadata — checked
  first-party at staging via `architecture search --content` over the implementing script (verify-at-outline
  against the exact current line numbers, since this was a pattern-presence check, not a full read).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: Whole-file grep of git-workflow.py for use_worktree/worktree_path confirms only read-side references (comments, resolver lookups); no write/clear call found anywhere in the file at this HEAD
- OBSERVED: `epic.md`'s own `-024` entry records four prior independent sightings (two first-party,
  archived records `-126`/`-093`) with the root cause already named: "`worktree-remove` is not the
  symmetric counterpart of `worktree-create`."
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: epic.md's -024 entry re-read at this pass: confirms four prior sightings and the named root cause, unchanged
- OBSERVED: PLAN-TRUTH-148's finalize run hit a fifth sighting — three dispatched post-merge steps
  correctly refused against a `use_worktree=true` / stale `worktree_path` pointing at an already-removed
  worktree; the operator resolved it in-session by setting `use_worktree=false`. Reported directly by the
  plan's own operator-facing summary.
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: Reported first-party, in detail, by the operator directly (not via inbox) in the prior session turn; treated as a reliable first-party account consistent with the already-corroborated PLAN-TRUTH-148 landing
- ⚠ HYPOTHESIS: the reader population that consults these fields post-`branch-cleanup` is small enough
  that D0's derivation is cheap. ⛔ Not yet enumerated — D0 owns it and may find otherwise
  (verify-at-outline).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: The reader population was not enumerated at cleanup time; D0 owns this per the spec's own text

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` —
  `cmd_worktree_remove` and its `worktree-create` counterpart (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/**` — the metadata read/write surface
  for `use_worktree`/`worktree_path`/`worktree_branch` (D0, D1) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**` — the dispatched post-merge
  steps D0's population sweep must enumerate (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-git/**` — coverage for the symmetric clear
  (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_prune_ref.py` —
  `prune-local-and-remote-ref`, the sibling that fails on `worktree-remove`'s deletion (D2, folded
  2026-09-15 (c))

## Dependencies and Sequencing

- Depends on: none. Five independent sightings across five different plans over an extended period —
  genuinely unowned, not blocked on anything else landing first.
- Adjacent to `PLAN-TRUTH-147`'s D6/convergence-signal work (both concern finalize-dispatch robustness) but
  a different mechanism — not merged.

## ⭐ FOLDED 2026-09-15 (c) — `worktree-remove`'S OTHER CASUALTY: `prune-local-and-remote-ref` IS NOT IDEMPOTENT

Forwarded from `api-sheriff-deployment-configurability-016.md` § `-012` (API-Sheriff PR #305). Expected
Surface extended in the same act (`_cmd_prune_ref.py`, above). This takes ownership of the epic's standing
**UNOWNED** Open Defect *"2026-09-07 — `prune-local-and-remote-ref` IS NOT IDEMPOTENT AGAINST ITS OWN
SIBLING"* — now a second independent sighting, from a consuming repo. Folded here because it is the same
defect family as this spec's subject: `worktree-remove` changes state its post-merge siblings still assume.

`worktree-remove` deleted the plan's local branch with the worktree; `prune-local-and-remote-ref` then tried
to delete that branch, errored on its absence, and stopped before pruning the remote-tracking ref — leaving
exactly the stale `origin/{branch}` it exists to remove. Two independent defects, both from the 2026-09-07
entry: an already-absent local branch is treated as an error rather than a no-op, and the verb fails fast
across INDEPENDENT operations.

**D2 (added) — `prune-local-and-remote-ref` is idempotent per ref.** An already-absent local branch reports
`skipped / already_absent`, the verb still prunes the remote-tracking ref, and each ref's outcome is
reported separately — or the two verbs agree on which one owns local-branch deletion. Matched control:
`worktree-remove` → `prune-local-and-remote-ref` leaves no tracking ref and reports no error.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-164-worktree-remove-leaves-use-worktree-and-worktree-path-stale.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
