envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-10T17:28:32Z

component=plan-marshall:workflow-integration-github
category=bug

Relayed from Token-Sheriff PLAN-09 (`mtls-alpha-reclassification`, PR #731 / `b6b1a94d`). ⛔ **The plan flagged this as the highest-reuse item of the run.** For a HEAD CodeRabbit has already seen incrementally, only `@coderabbitai full review` produces a review object the participation guard can verify — and `github_re_review` exposes **no flag for it**. So a bot that has genuinely re-reviewed can be unverifiable through the sanctioned surface, which is the false-RED half of the quorum problem reported across `-005`/`-012`/`-017` arriving by a new route.

component=plan-marshall:automatic-review
category=bug
bundle=plan-marshall

# CodeRabbit incremental re-review declines an already-seen HEAD; only `full review` produces a verifiable review

`github_re_review` exposes exactly one trigger form: the incremental
`@coderabbitai review` comment. When the PR HEAD is one CodeRabbit has already
reviewed incrementally, the bot does not re-review — it replies:

```text
Already reviewed the last commit. Use @coderabbitai full review to rerun a
review of the entire changeset.
```

That refusal arrives as an `issue_comment`, not as a GitHub review object, so it
carries `head_sha_verified: false`. The participation guard classifies it
correctly as a DECLINE rather than a completed review — the guard is not the
defect. The defect is that the only trigger form the tool offers cannot clear the
guard on an already-seen HEAD, so the loop re-triggers, re-declines, and
escalates.

Two `escalate_ask` rounds were burned on this before the cause was found, and it
was found by reading the PR conversation directly rather than by reading the
tool's return envelope. The envelope reported "a comment was posted" — true, and
useless; the refusal text only existed on the PR.

## Solution

For a HEAD CodeRabbit has already seen incrementally, post
`@coderabbitai full review`. It is the only trigger form that produces a GitHub
**review object** the participation guard can verify against the HEAD SHA.
`github_re_review` has no flag selecting it, so today this must be posted as a
plain PR comment through the CI provider rather than through the re-review verb.

Two follow-ups worth considering at the orchestrator's discretion:

1. Give `github_re_review` a way to request the full form (a flag, or automatic
   escalation to `full review` after a decline on an unchanged HEAD).
2. When a re-review attempt returns `head_sha_verified: false` with no new review
   object, read the bot's reply text before escalating — a DECLINE that names its
   own remedy is not an ambiguous state needing operator input.

## Impact

Any orchestrated run that re-triggers CodeRabbit on a HEAD it has already
reviewed — which is the normal case whenever a review round produces no code
change, or when a re-review is requested to confirm remediation. Costs two
escalation rounds and the operator attention they consume, every time.
