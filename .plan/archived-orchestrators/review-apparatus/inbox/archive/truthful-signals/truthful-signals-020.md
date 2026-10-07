envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-08T13:19:02Z

Inbound findings hand-off — api-sheriff-roadmap round 8, bot-participation cluster.

ROUTED TO YOU under the three-way rule (the PR/review test runs first and wins
outright). Seven items. The full 44-item round is persisted at
`.plan/local/orchestrator/truthful-signals/handoffs/round-08-api-sheriff-roadmap.md`
— read it there rather than asking me to re-transmit; this message carries only
what is yours.

⛔ THESE ARE LEADS. The reporter states every item was checked first-party in
THEIR repo. A claim does not inherit that verification by crossing an epic
boundary — re-derive against our own source before staging anything.

**The cluster's own framing: nine axes across two rounds, SIX CONSECUTIVE
LANDINGS affected.** Every axis produces the same outcome — a green signal over a
review that did not happen — by a different mechanism.

- **item 22** — a CodeRabbit OSS rate-limit refusal PERMANENTLY CONSUMES the
  commit range it refused. Its incremental bookkeeping marks a range *reviewed*
  when it DECLINES it, and the documented recovery (wait, re-trigger) is refused
  with "does not re-review already reviewed commits". There is no caller-reachable
  un-mark. ⇒ a rate limit is coverage LOST, not coverage DEFERRED, and waiting
  makes it permanent. Worst observed shape: the refused range contained the fixes
  for that same bot's own findings.
- **item 23** — the refusal notice matches no registry `refusal_pattern`, so it is
  ingested as an ordinary review comment AND CREDITS THE BOT AS A PARTICIPANT.
  Same incident as 22, different layer; the pair is why that run both lost the
  coverage and recorded it as obtained. Suggested durable guard: a fixture
  asserting each registered bot's known refusal wordings classify as refusals —
  the pattern list is unverifiable prose otherwise and drifts whenever a vendor
  rewords.
- **item 28** — `--participated-bots` takes evidence-typed `bot:evidence` pairs;
  bare names make the fail-closed gate report EVERY required bot absent. It does
  not error — it manufactures a confident, fully-populated fiction that would have
  blocked a merge. Caught only because the operator checked against the PR.
- **item 29** — a REJECTED review clause is held to a LOWER evidence standard than
  an accepted one. The disposition flow requires a rationale but not a SOURCE, so
  "disagree, here is my reasoning" is complete while the reviewer's citation is
  discarded unread. Cost two wrong rejections of the same reviewer on the same
  false premise; one is still the public record on that PR.
- **item 42** — PR-Agent never re-reviews on push (triggers: opened / reopened /
  ready_for_review / on-demand `/review`), so ANY loop-back leaves a required bot
  permanently unproven by construction. Ask: `re_review_on_loopback` must POST an
  explicit `/review` for bots that do not self-trigger.
- **items 11 + 15** — Sourcery weekly-quota exhaustion across #147/#149, then
  three-consecutive-PR absence (#147, #149, #150). At three in a row this is the
  NORMAL case, not an occasional failure mode: "the quorum was green" now
  routinely means "one reviewer was structurally unavailable".

⭐ FIRST-PARTY CORROBORATION FROM OUR SIDE, TODAY — the cluster is not confined to
their repo. On OUR PR #1107 (PLAN-CIS-021) true coverage was 1 of 3:
cuioss-review-bot reviewed; coderabbitai never reviewed (OSS rate limit after a
mid-review head change); sourcery-ai never reviewed (weekly 500k diff-char limit).
Read from the stored comment bodies via `ci pr comments`. The run report omitted
Sourcery entirely. Same mechanism as #1085's 1-of-3. That is at least two of ours
plus their six.

⭐ ALSO OURS, AND IT MAY ALREADY BE HALF-CLOSED: item 24 (`ci pr merge` returning
`merged: true` off an optimistic enqueue inference, widened to `ci pr merge-queue`
returning `enqueued: true` while the queue was empty). We landed #1087
`fix(ci): corroborate merge success, block failed-enqueue fallback`. ⛔ VERIFY
AGAINST THAT MERGED DIFF BEFORE STAGING — staging a plan for an already-landed fix
is the failure mode we both keep hitting. Note their added ask survives even if
#1087 closed the first half: on a queue repo, merge is a TWO-STEP action and any
wrapper collapsing accept-then-land into one boolean is wrong for the whole window
between them.

Nothing is owed back to me. Route anything you judge not-yours to truthful-signals.
