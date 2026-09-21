envelope_version=1
sender_type=plan
sender_id=domain-post-plan-narrow
epic=operator-ux
kind=candidate-lesson
created=2026-09-06T07:28:00Z

# Candidate lesson: a plan whose subject WAS a guard-discipline rule emitted nine instances of that same rule's violation in its own output

**Source**: plan `domain-post-plan-narrow` (PLAN-03, epic `operator-ux`), PR #1422
**Signal sources**: 6-finalize Q-Gate findings (self-review) + `pr-comment` findings (CodeRabbit) + an orchestrator self-observation
**Suggested component**: `pm-plugin-development:ext-self-review-plan-marshall` or `plan-marshall:phase-6-finalize`
**Suggested category**: `anti-pattern`
**Dedup read**: NEW. Not covered by any active lesson.

## Observation

The plan's own subject was the rule *"a verb that could not look must never render as a verb that looked and found nothing"* — the three-outcome contract it added to `domain-narrow`. Nine instances of that very failure class were introduced BY the plan's own output and fixed during the run:

- **3 by pre-submission self-review** — all unreachable-report-sink claims, where prose asserted a consumer that provably does not exist:
  - `cd0783` — `phase-3-outline/SKILL.md:687` claimed the orchestrator surfaces `domain_narrow_report`; an inventory-wide literal sweep (5375 files, clean coverage) found the token in two files, both producers.
  - `399e28` — the light-lane mirror of the same claim.
  - `7f14d3` — the symmetric FOURTH site the round-5 three-site fix missed.
- **5 by CodeRabbit on PR #1422.** Four were corroborated directly from the finding store while authoring this candidate; the fifth is taken from the orchestrator's own attribution and was not individually re-read here:
  - `b96f45` — the synthetic `system` domain is dropped by an *evaluation gap* rather than by the safety bound agreeing, so `claimed_by: []` (documented as "no leg claimed it, which is why it was dropped") would record a look that never happened.
  - `1a4922` — the consumer parses `retained`/`dropped`/`provenance`/`report`/`narrowed` unconditionally, implementing the module's deliberate three-outcome contract at two outcomes and reintroducing the collapse at the consumer site.
  - `eabd0e` — an empty `retained` renders `--values` with no argument; `narrowed: true` is `bool(dropped)`, so a run that drops everything fires a malformed command.
  - `e42d4c` — step 4 instructs the envelope to emit the report to a user-facing sink that the output contract does not provide.
- **1 introduced by the orchestrator into its own remedy for the class** — a strip-check asymmetry in which the sibling guard written in the SAME commit tested `.strip()` while this one stopped at truthiness.

## Why this is worth a lesson rather than nine

The nine are not nine independent defects; they are one fact. **Authoring a fix for a failure class does not immunize the authoring against that class** — and the run demonstrates the strongest form of it, because the author held the rule in working memory the entire time and still emitted it nine times, including once inside the remedy.

The nearest active lessons are each a single *instance* of the class in some other component (`2026-09-02-13-004` permission-prompt-analysis reports an unmeasured channel as a clean zero; `2026-09-03-06-003` let `should_emit` render a fragment that declares it could not look; `2026-08-25-09-011` a metacharacter-bearing `search --content` query returns a false zero; `2026-09-04-17-012` an unsweepable lint root). None of them states the meta-fact, so a reader of the corpus today learns the class exists but not that authoring against it is itself a high-risk site.

## Candidate corrective

A plan whose declared subject IS a defect class should run one self-review pass whose *stated proposition* is "does this change exhibit its own subject class?", rather than relying on the generic detector set to surface it. The evidence that the generic path is insufficient is in the ratio: self-review caught 3 of 9, and the external reviewer caught more than self-review did.

## Judgement deferred

Filed as a candidate; the epic holds the cross-plan context needed to decide whether this becomes a lesson, a standard clause, or a self-review detector.
