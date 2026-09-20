envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=finding
created=2026-07-29T05:22:20Z

## PR #1041 merged with a REQUIRED bot that never reviewed — and its CI check read SUCCESS at merge time

**Outcome record for the PLAN-92 / PR #1041 finalize run.** This complements
the landing message's residue item 1 with what actually happened at the merge
gate, plus one piece of evidence not captured there.

### The coverage gap, as shipped

`required_bots = coderabbit,pr-agent`; `optional_bots = sourcery`.

| Bot | Required? | What it actually did |
|-----|:---------:|----------------------|
| `coderabbit` | yes | **Never reviewed.** Posted only a rate-limit refusal notice. |
| `pr-agent` | yes | Reviewed. Raised 1 finding (`1a69d5`), which was fixed. |
| `sourcery` | no | **Never reviewed.** Hard-refused: PR exceeds its 150,000 diff-char limit. |

So of the two REQUIRED bots, one reviewed. The single defect found on this PR
was found by the only bot that reviewed it — which is the uncomfortable part:
the found-defect count is not evidence the coverage was adequate, it is
evidence that the one reviewer that ran was productive.

### The new evidence: a green check for a review that never happened

At merge time the `ci checks wait` result carried:

```
CodeRabbit   SUCCESS   pass
```

The merge queue's authoritative CI gate went green with a **`CodeRabbit`
check reporting SUCCESS** on a PR CodeRabbit had explicitly declined to
review. The check concluded; no review occurred. Nothing in the pre-merge
signal path distinguishes those two states.

This is the epic's theme in its sharpest form so far: not a signal that is
merely optimistic, but a **named-after-the-reviewer check that reads green
when the reviewer refused**. Candidate-lesson `-004` states the principle
("a concluded check-run means the check concluded, not that a review
happened"); this is the confirming instance where that exact conflation stood
between an unreviewed change and `main`, and did not stop it.

### The rate-limit ETA was not a wait budget

CodeRabbit's refusal stated **"Next review available in: 51 minutes"**
(posted 19:31Z). It was still refusing at 20:49Z — ~90 minutes later, ~40
minutes past its own stated window. CodeRabbit's own docs explain why:
adaptive per-developer limits stretch under sustained high-volume activity,
so the quoted figure is a floor, not an ETA. Candidate-lesson `-003` covers
the principle; recording the measured overshoot here as its evidence.

Cost of trusting it: **two loop_back iterations** (2 of the 3-iteration
ceiling) were spent before the operator intervened. The second dispatch alone
burned **~184K tokens over ~25 minutes** of polling that could not have
succeeded — the window had not cleared and nothing in the loop could observe
that it would not.

### How it was resolved

The operator was given the state explicitly (bot-by-bot, with the overshoot
measured) and chose to merge with partial required-bot coverage. The gap was
recorded truthfully at every layer that had a place to record it:

- `automatic-review` display_detail: `"pr-agent reviewed 1 finding fixed,
  coderabbit rate-limited, sourcery over size limit"`
- `finalize-step-review-retrospective`: `"1/3 bots reviewed"`
- a WARNING decision-log entry naming the unreviewed HEAD

**Nothing laundered the gap.** The reporting layers did their job. The
failure is upstream of reporting: the pipeline had no way to convert
"required bot refused, recoverably, on an unbounded timeline" into a decision
without a human, and the one machine-readable signal that could have flagged
it (`CodeRabbit` check status) was green.

### Residue for the epic

1. A required-bot refusal with class `awaitable_window` has **no bounded
   resolution path**. `review_rate_window_await` + `review_rate_window_timeout_seconds`
   bound the *wait*, not the *outcome* — when the budget expires the plan is
   in exactly the state it started in, having spent real tokens.
2. Consider whether `required_bots` should distinguish "required to
   participate" from "required to review", since a refusal notice IS
   participation by the current publish-shape definition.
3. A size-keyed refusal (`sourcery` at 150K diff chars) is **structurally
   unrecoverable by any wait** — covered by candidate-lesson `-005`, and this
   PR is its instance. Worth asking whether such a bot should be
   auto-demoted out of the gating set rather than counted as refused each
   run.
4. Post-merge PR revisit is the standing safety net for a late CodeRabbit
   review landing on #1041 after the merge.
