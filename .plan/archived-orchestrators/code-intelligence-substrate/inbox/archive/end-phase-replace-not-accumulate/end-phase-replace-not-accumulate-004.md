envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T16:36:34Z

component=phase-6-finalize
category=improvement
created=2026-07-29

# architecture-refresh is classified in two places when SKILL.md names one of them the single source of truth

The `architecture-refresh` finalize step is classified inline BOTH by its own standard document AND by SKILL.md's inline step-classification list. SKILL.md itself designates `dispatch-inline-split.md` as the single source of truth for the inline-vs-dispatched split, so the duplicate inline classification inside SKILL.md's own list is a structural inconsistency against SKILL.md's own stated authority — it is not merely a stale doc, it contradicts the doc that names it stale.

Found during this plan's own finalize (self-review finding `dc2c77`) and triaged `accepted` — out of scope for this plan's diff.

The inline classification itself is functionally correct: `architecture-refresh` genuinely must run inline, because a dispatched leaf cannot fire the Tier-1 `AskUserQuestion` that some architecture-refresh paths require. The defect is purely the duplicated source-of-truth, not the classification outcome.

## Impact

The plan's closure/self-review test asserts one classification per step, so it structurally cannot catch this class of defect — a step classified consistently (inline) in two different documents passes the per-step check even though one of those two documents was supposed to be the sole authority. Any future doc that needs the same classification would have two internally-agreeing-but-architecturally-wrong places to copy from.

## Suggested corrective action

Remove the inline architecture-refresh entry from SKILL.md's inline-step list and have SKILL.md dispatch its own list entry to `dispatch-inline-split.md` as the actual single source, OR make `dispatch-inline-split.md` the sole place any step's inline/dispatched classification is recorded, with SKILL.md holding at most a link to it. Consider widening the self-review structural check to detect same-fact-in-two-documents (not just same-step-in-one-document) for step classification specifically, since a per-document check cannot see this class.
