envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:35:26Z

component=project:finalize-step-lessons-housekeeping
category=bug
confidence=high
source_plan=plan-04-autonomy-gate-defaults

# Step reads references.modified_files, a key retired with the change-ledger

## Context

`project:finalize-step-lessons-housekeeping` fired three times this run
(`firing_count: 3`). All three read the plan footprint via

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} --field modified_files
```

and all three got `error: field_not_found`:

- `20:22:42Z` — "references.modified_files not set — proceeding on request.md alone"
- `21:21:13Z` — "references field modified_files not_found — classifying from request.md alone"
- `09:43:26Z` — "Footprint grounded on git diff origin/main...HEAD because
  manage-references modified_files is field_not_found"
- decision.log `09:43:21Z` — "...returned field_not_found for the third
  consecutive run"

This is reproducible right now, post-merge, against the same plan.

## Root cause

`references.modified_files` is a **retired legacy key**, not a missing write.
`plan-retrospective/scripts/_footprint_resolver.py:225-231` documents it as
tier 4 of the footprint chain and marks it explicitly:

```
# SHIM(B): archived plans' references.modified_files key, written before the
#   change-ledger was removed.
# shim-floor: ... the current writer no longer emits the key
# shim-remove-when: no archived plan predating the ledger removal is retained
```

No plan created today carries the key, so this read cannot succeed on any current
plan — it is not intermittent, it is 100% and permanent. The current declared
footprint lives under `references.affected_files`; the realized footprint lives
under `references.realized_footprint` or is recovered through the five-tier
shared resolver.

The step is worse off than a single broken read suggests, because **both** of its
documented Step 3 classification inputs are unavailable by construction:

- `quality-verification-report.md` is absent because the retrospective that
  writes it runs at order 995, after this step's settle-band order. The step's
  own SKILL.md acknowledges this and says to "proceed using `request.md` +
  `modified_files` alone".
- `modified_files` is absent because it was retired.

So the documented fallback names the one other input that also cannot be read.
The step's actual behaviour is to fall back to `request.md` alone (firings 1 and
2) or to a hand-run `git diff origin/main...HEAD` (firing 3) — neither of which
its documentation describes.

## Proposed action

Repoint `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:90` at a
footprint source that exists. In preference order:

1. `_footprint_resolver.resolve_footprint` — the shared five-tier resolver, which
   already handles the worktree-present, realized-footprint, merge-commit,
   PR-number and legacy cases and distinguishes an unresolvable footprint from an
   empty one.
2. Failing that, `manage-references get --field realized_footprint` with an
   explicit documented fallback to `affected_files` (the declared footprint) and
   a stated consequence of using the declaration in place of the realization.

Also correct the Error Handling row at SKILL.md:318, which currently offers
`request.md` + `modified_files` as the non-fatal fallback for a missing
retrospective report — both halves of that fallback are unavailable at this
step's order.

## Evidence

- Reproduced post-merge: `manage-references get --plan-id
  plan-04-autonomy-gate-defaults --field modified_files` →
  `error: field_not_found`.
- `_footprint_resolver.py:225-231` — the SHIM(B) block declaring the key retired.
- `references.json` for this plan carries `affected_files` (26) and
  `read_intent_files` (0), and no `modified_files`.
- work.log `20:22:42Z`, `21:21:13Z`, `09:43:26Z`; decision.log `09:43:21Z`.

## Note on blast radius

This skill lives under `.claude/skills/`, which is outside the architecture
inventory that `architecture search --content` walks. A content sweep for
`modified_files` over the marketplace tree does not reach it — which is part of
why a read against a key retired in the marketplace survived in a project-local
skill.
