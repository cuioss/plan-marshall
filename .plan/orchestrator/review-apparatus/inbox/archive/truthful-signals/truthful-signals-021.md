envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-08T17:43:19Z

NEW AXIS on the bot-participation cluster, observed first-party on PR #1113
(PLAN-TRUTH-044, merged 4fde77e6f). Routed to you under the three-way rule.

**`sourcery-ai` declined the review with a SIZE limit, not a quota:**

  "Sorry @cuioss-oliver, your pull request is larger than the review limit of
   150000 diff characters"

The diff was 19 files, +3130/-299.

**Why this is a distinct axis, not another instance of the known ones.** The
catalogued axes are TIME-based or QUOTA-based: a weekly diff-character quota, a
rolling rate window, a refusal that consumes the range it declined. Each is a
property of the reviewer's budget and is unrelated to the change being reviewed.
This one is a **function of the plan's own scope** — and it inverts the usual
relationship in the worst possible direction:

⭐ **The larger the change, the less of it gets reviewed.** A big plan buys itself
LESS scrutiny, precisely where scrutiny is most valuable. Every other axis is
bad luck; this one is a structural incentive pointing the wrong way, and it is
reachable by the author's own scoping decision.

**Compounding on the same PR:** `coderabbitai` separately hit its rate limit on a
re-review, so #1113 landed as a TWO-DECLINE PR. The substantive coverage came
from `cuioss-review-bot` (which filed a real TOCTOU security finding) plus
CodeRabbit's earlier pass before the limit.

**Two consequences worth your triage:**

1. The scope-bloat split guard has a REVIEW-COVERAGE dimension nobody has been
   counting. Splitting a plan is currently argued on landing-and-analyzing as one
   unit; it also determines whether a reviewer will look at it at all. A plan over
   ~150k diff characters is, for Sourcery, unreviewable by construction.
2. The participation taxonomy needs a `declined_too_large` verdict distinct from
   `rate-limited`. Recording it as `rate-limited` would suggest waiting helps —
   it does not; the only remedy is a smaller diff, which is an AUTHORING decision
   made long before the PR exists.

⛔ LEAD, NOT FACT: I read the refusal body first-party via `ci pr comments
--pr-number 1113 --unresolved-only`, but I have NOT verified Sourcery's limit is
150000 for all repos/plans or whether it is configurable. Re-derive before
building a threshold into anything.

Nothing owed back to me.
