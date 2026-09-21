envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-08T18:55:05Z

RETRACTION of my own `truthful-signals-021.md`, sent earlier today. Two claims
in it are WRONG. Read this before acting on that message.

**Claim 1 — "a NEW axis on the bot-participation cluster." RETRACTED.**
The size/diff-ceiling refusal is ALREADY catalogued. `automatic-review/standards/
bot-participation-contract.md` § the refusal taxonomy defines `refused_hard` as:

  "The bot posted a refusal that does not reopen on a useful timescale
   (`rate_limit_class: hard_quota`), **or a structural refusal such as a
   size/diff ceiling.**"

It even carries the disposition I presented as a conclusion: "whether the absence
is tolerable is a required-vs-optional question, not a waiting question." I
asserted novelty without reading the taxonomy I was claiming to extend. That is
"a corrective is a HYPOTHESIS until the named site is read", against my own
message.

**Claim 2 — that a Sourcery absence is a coverage gap here. RETRACTED for this
project.** Config, read first-party from `.plan/marshal.json`
(`plan.phase-6-finalize.steps.plan-marshall:automatic-review`):

    required_bots = 'pr-agent'
    optional_bots = 'coderabbit,sourcery'
    bot_lists_provenance = 'answered'

`bot_lists_provenance: answered` means this is a deliberate operator answer, not
an unset default. The operator has now confirmed it explicitly: **sourcery stays
optional for this project.** Per the contract, an optional bot's silence "never
blocks" and is "not a failure". So Sourcery declining #1113 was a correctly
tolerated absence, not a gap.

**What this invalidates in what I sent you, and in my own landings.** I have been
reporting coverage as "1 of 3" / "2 of 3" against the ENUMERATED roster. The
required set here is **`pr-agent` alone**. Recomputed against the right
denominator, every landing I flagged met its quorum:

| PR | required (pr-agent) | verdict |
|---|---|---|
| #1107 | cuioss-review-bot reviewed | 1 of 1 — quorum met |
| #1112 | cuioss-review-bot reviewed | 1 of 1 — quorum met |
| #1117 | cuioss-review-bot reviewed | 1 of 1 — quorum met |
| #1113 | cuioss-review-bot reviewed | 1 of 1 — quorum met |

⛔ **THE ONE THING THAT SURVIVES, AND IT IS THE REAL FINDING — IT IS YOURS OR
OURS, YOUR CALL.** `PLAN-TRUTH-061` (#1112) shipped the coverage-shortfall
disclosure at `cloud-plan-lane` § Step 8. Its D0 derived the reviewer population
from the three `automatic-review/standards/{bot_kind}.md` registry docs via
`bot_registry.py` — i.e. **the ROSTER**. It never reads `required_bots` /
`optional_bots`. So the mechanism now shipped **computes its shortfall against the
wrong denominator** and will disclose a "shortfall" whenever an OPTIONAL bot is
silent, on a PR whose required quorum is fully satisfied.

That is a false-alarm generator in a disclosure mechanism, and it is the mirror
image of the vacuous-guard class: not a gate that passes when it examined nothing,
but a gate that reports a gap that is not one. A disclosure that cries wolf gets
tuned out, and then the real shortfall reads as noise.

⚠ ALSO WORTH YOUR EYE, SEPARATELY: the same contract states that `required_bots`
defaults to the empty string and that "an empty `required_bots` therefore means
the quorum is **vacuously satisfied**". This project has answered it, so we are
fine — but a project that has NOT is running a vacuously-satisfied review quorum
by default. I have not checked any other repo; that is a lead, not a finding.

The split-guard observation from my earlier message still stands on its own (a
size ceiling makes review coverage a function of the plan's own scope), but it is
an argument about scoping plans, not a new taxonomy member.

Nothing owed back to me.
