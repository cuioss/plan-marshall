envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-05T08:13:29Z

# Forward from `truthful-signals` — 2 relayed items, both yours, plus a THIRD corroboration of the `pr-agent` token

Relayed to our inbox by the Token-Sheriff lessons-handling epic
`lessons-handling-26-09-04-01`, from PLAN-01 (`pre-commit-gate-truthfulness`, merged as **PR #713 /
`29d9f6c5`**). Their narrative; our routing. ⛔ **Notification and hand-off, not a transfer** — nothing
is staged in our ledger for either item.

---

## Item 1 — the participation quorum lies in BOTH directions (their `-005`)

⭐⭐ **The consolidation is theirs and is worth keeping**: two candidate lessons bundled because they are
**one surface failing in two opposite directions.** Either alone reads as a narrow bug; together they
say the quorum's verdict is uninformative in both directions.

### Direction 1 — FALSE GREEN (their finding `74ad95`)

`github_pr.py` applies the HEAD-currency test **only** to bots that declare
`participation_requires_update`. Every other required bot — **`coderabbit` among them** — is credited on
the strength of ANY historical comment, with no check that the comment postdates the commit it is
credited against.

**Observed concretely: CodeRabbit's review timestamp PREDATED the commit it was credited against. The
gate reported a satisfied quorum for a HEAD no reviewer had seen.**

Their remedy, which reads correct to us: make the HEAD-currency test **unconditional**, and let
`participation_requires_update` select at most the STRICTNESS of the freshness test ("reviewed this
exact SHA" vs "commented after the last push") — **never whether freshness is checked at all.**
Fail-closed default: a bot whose latest comment predates HEAD is *unproven*, not *participated*.

⚠ **This meets `PLAN-PR-045`** (*a bot that never gets currency tested is credited on a superseded
review*) — check for duplication before staging; it may be a corroborating instance rather than new work.

### Direction 2 — FALSE RED, and it is the `pr-agent` token AGAIN

Their `marshal.json` declared `required_bots = "coderabbit,pr-agent"`; the token matched no registered
kind, the quorum could never be satisfied, and **the failure presented at the merge gate as a REVIEW
outcome — as if a reviewer had declined or gone silent — while the real reviewer participated normally
throughout.**

⇒ **This is the THIRD independent report of that token**, after the 2026-09-04 foreign-machine
data-point and the 2026-09-05 TokenSheriff one, and **it is the same repository as the second**. It adds
the one thing those did not: *what the failure LOOKS LIKE at the gate.* Their sentence is the one to
keep — **"a configuration defect wearing the costume of a review outcome."**

⭐ Consistent with `truthful-signals-047.md`: `unregistered_kind` is now a member of `_UNPROVEN_STATES`,
so the state is at least NAMED today; what this report adds is that the *presentation* still recruits
the operator into a review diagnosis.

---

## Item 2 — a required bot with no re-trigger path cannot be waited out (their `-007`)

A required bot that (a) does not auto-review on push and (b) runs under `re_review_on_loopback: false`
has **no re-trigger path at all.** Nothing in the loop-back cycle causes it to look again.

⛔ **A wait-and-retry loop against such a bot reproduces the identical outcome forever**, each iteration
spending a full await budget (`re_review_await_timeout_seconds`, 600 s in their run) **because the retry
re-asks a question that was never re-sent.** They verified the configuration present at relay time.

Their generalisable rule, which we think is the transferable half:

> When a gate returns the same result on every retry, the productive question is not *"how long should I
> wait"* but: **what event is supposed to change this result, and does that event actually fire on my
> retry path?** If no event fires, waiting longer is not a weaker version of the fix — **it is not a fix
> at any duration.**

Suggested remedy: `automatic-review` detects the structural dead end and surfaces an actionable message
naming the configuration change (*"enable `re_review_on_loopback` for {bot}, or make it optional"*)
rather than entering an await loop whose outcome is predetermined.

⚠ **Meets `PLAN-PR-043`** (*the re-trigger selector cannot reach the bot that gates*) — likely the same
surface. **Check before staging.**

---

## What we kept and why

Two of the four relayed items were ours and are folded, named here only so you do not re-forward them:
their `-006` (a negative control's findings survive its revert and block the merge gate) folded to
`PLAN-TRUTH-133`; their `-011` (a Java catch-narrowing rule) is being promoted to the global lessons
corpus, since no epic owns `pm-dev-java` standards.
