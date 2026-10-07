envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T12:59:59Z

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall

# UNFIXED: automatic-review/SKILL.md documents a CLI surface the script no longer has

## Status

**Not fixed by PR #1078.** Filed as a live, actionable epic item. The divergence exists in merged
main right now.

## The divergence

`automatic-review/SKILL.md` documents flags and return fields that the shipped `argparse` surface
does not have:

| Surface | SKILL.md documents | Shipped argparse actually takes/returns |
|---------|--------------------|------------------------------------------|
| Input flags | `--enabled-bots`, `--settled-bots` | `--required-bots`, `--optional-bots`, `--participated-bots`, `--in-progress-bots`, `--refused-bots` |
| Return fields | `complete`, `unfetched_bots` | `participation_complete`, `unproven_bots`, `bot_states` |

Every documented invocation is therefore an `argparse` rejection (`exit_code: 2`), and every
documented return-field read resolves to nothing.

## Why this one matters more than an ordinary doc drift

The divergence is not cosmetic — the two vocabularies **model different things**:

- `--enabled-bots` is a *configuration* input: which bots are turned on. `--participated-bots` /
  `--refused-bots` are *evidence* inputs: which bots demonstrably acted. The rename tracked the
  epic's central correction, that enabled-is-not-operative.
- `complete` / `unfetched_bots` cannot express refusal at all. `participation_complete` /
  `unproven_bots` / `bot_states` can. So the documented contract is precisely the one that
  **cannot represent the absent-vs-clean distinction** the epic exists to enforce.

Anyone following the SKILL.md is not just getting a rejected command — they are getting the old,
untruthful mental model. A doc that survives its implementation keeps teaching the defect after
the code stopped having it.

## Rule

- **A renamed flag is a doc-contract change, and the doc is part of the deliverable.** A plan that
  changes an argparse surface has not finished until the SKILL.md canonical-invocations block and
  every consuming reference are updated in the same change.
- **When a rename encodes a conceptual correction, the stale doc is a live misinformation source,**
  not merely out of date. Prioritise it above ordinary doc drift.
- **`argparse` surfaces are mechanically checkable against their canonical-invocations block.**
  This class should be caught by a structural gate rather than by a reader noticing.

## Suggested epic action

Reconcile `automatic-review/SKILL.md` (canonical invocations + return-contract prose) with the
shipped argparse, and sweep for other consumers still passing `--enabled-bots` / `--settled-bots`
or reading `complete` / `unfetched_bots`.
