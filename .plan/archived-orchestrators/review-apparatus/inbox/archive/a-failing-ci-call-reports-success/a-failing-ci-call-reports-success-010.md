envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=candidate-lesson
created=2026-08-27T15:50:04Z

# Five transcribed populations reached review, and one had under-scoped its own premise

component: pm-plugin-development:ext-self-review-plan-marshall
category: improvement
confidence: high
source_plan: a-failing-ci-call-reports-success
source_pr: 1356

## Context

Five of the 19 remediated review findings are one shape: a hand-copied list
standing in for an authoritative definition, with nothing keeping the two in step.

- **a1ebb0** — a prose paragraph hardcodes the bot-observation flag forms
  implemented by `_parse_bot_observations`. Hand-reconciliation had already failed
  **twice on this one paragraph during this run**: the pair-form arm needed
  deriving as four against a docstring claiming two, and self-review round 4
  caught the bare-form arm naming five where the parser routes six.
- **986369** — `test/conftest.py` maintains a guard roster separately from the
  modules that publish guard population metadata, so a live publisher can be
  omitted silently.
- **097b85** — a table transcribes a `hits/8` denominator that the same change had
  just de-pinned on purpose, so the module documents a number its own assertions
  would reject.
- **bc1344** — `api-contract.md` hardcodes four `error_cause` and four
  `landing_state` values; runtime populations are guarded, their documentation is
  not.
- **df7702** — `branch-cleanup.md` hardcodes a four-value `overall_status`
  vocabulary. The reply records that the finding's own premise was under-scoped:
  there are **two** `_derive_overall_status` definitions (github `_github_checks.py`
  as well as gitlab `gitlab_ops.py`), not the one the comment named.

## Root cause

The self-review surfacer already advertises candidate classes for
source-of-truth duplicates, stale count-prose and scan-derived keys, yet all five
of these reached the external bot unflagged. The common trigger is textual and
cheap to detect: a doc or test literal enumerating a closed set that a named
symbol also defines.

`df7702` adds the sharper point. Even the *reviewer's* statement of the
authoritative site was a sample of one when the population was two. A transcribed
population is not repaired by transcribing a corrected version of it — it is
repaired by deriving it, or by a parity guard that publishes the size it measured.

## Proposed action

1. Add a surfacer candidate for *closed-set literal adjacent to a named symbol
   that defines the same set* — a doc list, a test tuple, or a table column whose
   members match an enum/constant/regex-derived population elsewhere in the tree.
2. Require that any parity guard added in response **publishes its measured
   population size**, so the guard cannot pass over an empty or halved population.
3. When a finding names the authoritative definition, verify that the definition is
   unique before scoping the fix to it; `df7702` is the worked example of that
   check paying off.

## Evidence

- Class B of the complete 19-finding partition: a1ebb0, 986369, 097b85, bc1344, df7702
- a1ebb0 records two failed hand-reconciliations of one paragraph inside this run
- df7702 corrects the finding's premise from one authoritative definition to two
- Related standing rule: derive completeness, never assert it
