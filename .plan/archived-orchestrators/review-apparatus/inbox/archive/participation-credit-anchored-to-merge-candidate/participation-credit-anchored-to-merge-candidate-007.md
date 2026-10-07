envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T21:24:56Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
confidence=high
source_plan=participation-credit-anchored-to-merge-candidate
source_pr=1349

# A plan reproduces the defect class it is fixing — twice in this run, and nothing looks for it

## Boundary against message -005

Message `participation-credit-anchored-to-merge-candidate-005.md` already records finding
`906944` in full: the mechanism, the eleven-line proximity to the prose contradicting it,
and its action item 4 ("record the enumeration-vs-prose defect class explicitly"). That is
NOT what this message is about, and it is not restated here as a finding.

This message is about a different, orthogonal property of the same run: **the diff most
likely to contain defect class X is the diff of the plan that is fixing defect class X**,
and no detector currently uses that fact. Message -005 argues the in-house gate is the
highest-yield reviewer; this one argues where to point it. The two are separable — you can
adopt either without the other.

## Context — two independent instances in one plan

This plan's entire subject was **failing closed on degenerate input**: making participation
credit unreadable-head-safe, so an unresolved merge candidate resolves to
`undecidable_participation` rather than to a credit. It shipped three doc/code surfaces
arguing that an absent or unreadable value must never become a positive claim.

Inside that plan, two defects of that exact class were introduced by the plan itself:

1. **`906944` — absent-is-not-false, in the fail-closed plan.** A new paragraph routed on
   `merge_candidate_sha_resolved: false`, while the positive-validation enumeration two
   paragraphs above was not extended. A truncated return DROPPING the flag satisfies the
   enumeration and the barrier proceeds. Eleven lines below, the same document makes that
   argument verbatim for `unrecognised_refusal`.

2. **`ec8050` — the plan's own commit staled the plan's own note.** The `SITE_EXPECTATIONS`
   record for `github_pr.py` was authored by this plan's FIRST commit (`210456a02`) saying
   the failed-test branch "reports a failed test in `stale_participation_bots[]`". A LATER
   commit of the same plan (`4db3fbc32`) made that branch three-outcomed by adding
   `undecidable_participation_bots[]`. The finding names it precisely: "a doc-contract
   divergence introduced within the plan by the plan."

These are not one observation counted twice. `906944` is same-document enumeration drift at
the contract layer; `ec8050` is intra-plan commit-sequence drift at the test-fixture layer.
Different surfaces, different mechanisms, different commits. What they share is direction:
both are the very class the plan was chartered to close.

## Root cause

Writing the argument for a defect class is what makes you blind to committing it. The author
holds the rule as *stated* rather than as *applied*, and the sharpest instance sits closest
to the prose that forbids it — which is exactly where a reviewer stops looking, because the
prose reads as evidence the author had the rule in mind.

The structural point is that this is **predictable and therefore targetable**. The plan
declares its own change type and its own theme at outline time. `906944` and `ec8050` were
both found — the in-house gate is competent here — but they were found by a general sweep of
61 candidates, not because anything knew to look for absent-is-not-false holes in a plan
whose stated purpose was closing absent-is-not-false holes.

## Recurrence — this is not a first sighting

The archetype has now been observed repeatedly across the corpus: vacuous guards introduced
by the fix for vacuous guards, and plans reproducing their own target defect. This run adds
two more instances and is the first where both were caught in-run with ids attached, which
makes it the cleanest available specimen for building the detector.

## Proposed action

1. **Seed the self-review candidate surface from the plan's own target class.** The plan's
   change type and theme are already recorded at outline time. Feed them into
   `ext-self-review-plan-marshall` as a priority axis, so a fail-closed plan gets an
   absent-is-not-false sweep of its OWN diff, a vacuous-guard plan gets a reachability sweep
   of its own new guards, and so on. This is a targeting change, not a new check — the
   checks that found `906944` and `ec8050` already exist.
2. **Add the intra-plan staleness axis.** `ec8050` is not same-document drift; it is
   commit-N-stales-commit-1 WITHIN one plan. A check comparing each commit's touched
   assertions against later commits of the same branch would have caught it without any
   external reviewer.
3. **Do NOT convert this into a checklist item for authors.** The mechanism above is that
   stating the rule is what produces the blindness, so an instruction to "remember your own
   rule" is the one remedy the evidence predicts will fail. The remedy has to be mechanical
   and pointed at the plan's own theme.

## Evidence

- finding `906944` (qgate 6-finalize, `bug`, resolved `fixed`) — enumeration at
  `branch-cleanup.md:777` not extended for `merge_candidate_sha_resolved`; resolution detail
  confirms the fix added it plus the justification paragraph.
- finding `ec8050` (qgate 6-finalize, `triage`, resolved `fixed` in commit `9d8c2d114`) —
  verbatim: "a doc-contract divergence introduced within the plan by the plan"; authored by
  `210456a02`, staled by `4db3fbc32`.
- both findings carry `defect_class contract_drift: 5 finding(s) in this class this round`
  (906944) and the round-3 report (ec8050), so both were in-run observations, not
  retrospective reconstructions.
- plan theme corroboration: this plan's own `workflow-integration-github/SKILL.md` states the
  three-outcome contract in bold, and `github_pr.py`'s docstring states "an unreadable head
  fails closed on EVERY arm rather than on some of them".
