envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:16:35Z

component=plan-marshall:phase-6-finalize
category=bug
disposition=new
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369
source_finding=266d55

# The PR-body Intent section is appended by the renderer but positioned third by the template, and its character budget clipped the one non-goal a reviewer most needed

## Provenance

Q-Gate finding `266d55` (6-finalize), resolved `taken_into_account` and **"Routed to the
truthful-signals epic, not fixed here."** No inbox message carried it. Two defects on one surface.

## Defect 1 — placement drift

`templates/pr-template.md` positions the Intent heading **third**, between Summary and Changes.
`pr_intent_section cmd_render` unconditionally **appends** to the end of the body file. The two
cannot both be right.

The create-pr agent worked around it by omitting the heading from its own body *and* dropping the
template's trailing footer, which would otherwise have rendered **above** the appended Intent and
read as broken. So the shipped PR has Intent as its **last** section, not its third — and the
workaround is invisible to anyone reading either the template or the renderer alone.

## Defect 2 — truncation loss

The renderer reported `truncated: true`, `chars_written 1493` of a 1500 budget, showing 1392 of
1678 draft characters. Two non-goals were clipped mid-item:

- one (*no provider de-duplication*) survives elsewhere in the body under **Known limits**;
- the other is **absent from the PR entirely**: that the freshness-gate cross-check is deliberately
  **additive** and must not turn an adequate run into a stale verdict.

That is precisely the non-goal a reviewer of deliverable 3 most needs, because without it the
change reads as making the gate stricter without bound.

## The distinction worth keeping

The truncation is **disclosed** — a reader sees the rendered marker. Disclosure is not restoration.
This is a case where the honest-signal property held and the outcome was still a lost claim, which
is worth recording precisely because the epic's usual remedy (make the signal honest) was already
satisfied here and did not help.

## Why it was not repaired in-run

`cmd_render` **appends rather than replaces**, so a second call would have shipped a duplicate
Intent section on a live PR. The renderer's own API shape blocked the repair.

Mitigation that did apply: the lost claim is reachable from the diff — it is asserted by the
matched positive control `test_a_whole_tree_verify_row_still_certifies_the_same_change`, and stated
in the deliverable-3 commit message.

## Remedy (for the epic to scope)

1. Decide the placement question once: either move the template heading to the end, or make
   `cmd_render` **replace in place** rather than append. The second also makes re-rendering
   idempotent, which is what made the in-run repair impossible.
2. When the budget binds, prefer clipping **whole items** over mid-item truncation, and name the
   dropped items rather than only the character counts.
