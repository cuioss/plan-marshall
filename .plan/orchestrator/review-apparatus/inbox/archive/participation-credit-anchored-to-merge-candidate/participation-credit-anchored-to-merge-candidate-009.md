envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T21:26:20Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=participation-credit-anchored-to-merge-candidate
source_pr=1349

# A required-bot set of ONE, whose member's default output is contentless, cannot tell a reviewed PR from an unreviewed one

## Boundary against message -005

Message `participation-credit-anchored-to-merge-candidate-005.md` records the reviewer
COMPARISON on this PR: in-house self-review found 5, the external set found 0, and its
actions are about weighting the in-house gate and not spending another round on bot
charter exhortation. Its item 3 addresses `refused_structural` specifically.

This message is about a different thing: **the shape of the participation predicate that
returned green**. Message -005 observes that the barrier let the PR through; this one names
the mechanism that made that outcome guaranteed rather than unlucky, and the fix is a
configuration/predicate change that -005 does not propose. Adopting -005's actions in full
would leave this defect exactly as it is.

## Context

The manifest configured, for this run:

```
required_bots: "pr-agent"
optional_bots: "coderabbit,sourcery"
bot_lists_provenance: "answered"
```

The observed outcome per reviewer, from `ci pr comments` evidence only (4 comments fetched,
3 bots looked for, `unclassified_bots` empty):

| bot | role | resolution | cause |
|---|---|---|---|
| pr-agent | **REQUIRED** | `participated_but_empty` | published its declared shape, produced nothing actionable |
| coderabbit | optional | `refused_awaitable` | quota, no ETA |
| sourcery | optional | `refused_structural` | diff size cap |

And the barrier returned **`participation_complete: true`**.

## Root cause — the predicate is satisfiable by a reviewer that reviewed nothing

Three properties compose into a vacuous gate, and each is individually defensible:

1. **The required set has cardinality one.** There is no second required opinion to
   disagree with the first, so the quorum is whatever that one bot did.
2. **That one bot's satisfying outcome is `participated_but_empty`.** Publishing an
   `issue_comment` matching its declared publish shape IS participation under the contract.
   pr-agent's default output is contentless, so its *normal, healthy, nothing-wrong* run
   satisfies the required set.
3. **The predicate's own return says so.** It returns `proves: participation_only` — the
   contract is honest about what it establishes. Nothing consumes that honesty.

Compose them and the gate cannot distinguish its two most important cases. A PR that was
reviewed thoroughly and a PR that no reviewer read produce the **identical** verdict,
because the only required member emits the same observable either way. This is the
vacuous-authority shape: an authority whose approval carries no information, and which
therefore reports the same green whether or not it looked.

Note carefully what is NOT claimed here. This says nothing about pr-agent's quality — the
population of measurable external reviews on this PR is zero, so no quality claim about any
bot is supportable in either direction. The defect is in the gate's construction, and it
would be a defect on a PR where pr-agent found ten real bugs, because the green would still
have been guaranteed in advance.

The two refusals did not gate the quorum: both refusing bots are optional, and the
rate-window recovery is required-bots-only with `review_rate_window_await: false`. So the
one structurally durable refusal — sourcery's diff-size cap, which no amount of waiting or
re-triggering clears — was invisible to the barrier by design.

## The settle window was honest, which is what isolates the defect

This must not be read as a detection failure. The observation was clean: 7 polls over 189s,
`baseline_count 4 -> final_count 4`, `new_count 0`, `detector_answerable: true`, and
`ci checks pull-request-runs` reported `has_pull_request_run: true` (5 of 6 runs
`pull_request`-triggered). The reviewers were demonstrably asked, and the no-movement
reading was a genuine measurement rather than an unanswerable one.

Everything downstream of the predicate worked. The predicate itself is what cannot fail.

## Proposed action

1. **Make `participated_but_empty` insufficient to satisfy a REQUIRED slot.** A required
   reviewer's contribution should have to be *measurable* — an actionable finding, or an
   explicit reviewed-and-clean assertion the bot actually emits — not merely the presence of
   a comment in the declared shape. `participated_but_empty` on a required bot should
   resolve the slot to undecidable, the same way an unreadable head does.
2. **Refuse, or loudly disclose, a required set of cardinality one whose member's default
   output is contentless.** The pairing is the defect; either half alone is fine. If the set
   stays a singleton, the barrier's green must carry the `proves: participation_only`
   qualifier into the operator-visible summary rather than leaving it in the payload.
3. **Let a `refused_structural` on an OPTIONAL bot still register as coverage lost.** A
   diff-size cap is permanent for that diff. Today it is silently absorbed because the bot
   is optional; it should at minimum count against a coverage figure the barrier reports,
   so "3 configured, 0 measurable" is visible at the gate instead of only in a
   retrospective.
4. **Report reviewer coverage as a fraction, not a boolean.** `participation_complete: true`
   next to `0 of 3 reviewers measurable` is the pair that makes this diagnosable at a
   glance.

## Why this belongs to this epic specifically

This plan's own subject was closing a fail-open in participation credit — ensuring credit is
anchored to the commit actually being merged. It closed that hole and shipped. The hole
described here is the adjacent one: the credit is now correctly anchored, and the set of
reviewers whose credit is required is small enough, and undemanding enough, that anchoring
it correctly does not make the gate mean anything.

## Evidence

- finding `5dfac8` (qgate 6-finalize, `insight`, `info`, resolved `taken_into_account`) —
  the full per-reviewer table, `participation_complete: true` "rests on a required set of
  ONE", and `proves: participation_only`, quoted above.
- manifest `phase_6.step_params.automatic-review` — `required_bots: "pr-agent"`,
  `optional_bots: "coderabbit,sourcery"`, `review_rate_window_await: false`,
  `bot_lists_provenance: "answered"`.
- `status.json` — `automatic-review`: `"0 comments - 1 empty, 1 refused, 1
  refused-structural (triage pending)"`.
- `status.json` — `project:finalize-step-review-retrospective`: `"clean grade but 0/3
  reviewers measurable; self-review 5 defects, bots 0"`.
- settle-window measurement: 7 polls / 189s, `new_count 0`, `detector_answerable: true`,
  `has_pull_request_run: true`.
