envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:04:32Z

# Candidate lesson: a required review bot that publishes only `issue_comment` can NEVER give the merge barrier a machine-verified HEAD binding

**Source**: PR #1129 review rounds; pr-comment finding `273d12` (`rejected`), plus the 8 `fixed` findings
**Defect class**: vacuous-authority / enabled-bots-vs-operative drift
**Theme fit**: confident-signal-hides-a-caveat — `participation_complete: true` is the confident signal

## The structural claim

The pre-merge re-review barrier's participation predicate keys on **comment MUTATION**, not on
**HEAD identity**. A bot whose only publish shape is a repo-level `issue_comment` therefore cannot
supply the barrier with evidence that it reviewed *this* HEAD:

> `participation_complete: true` for such a bot is **structurally unable** to mean "reviewed this
> HEAD". It can only ever mean "this bot's comment changed since we last looked".

This is not a tuning problem or a flaky-bot problem. It is a property of the publish shape. An
inline review comment carries a path + line + commit binding; an `issue_comment` carries none. No
amount of barrier logic can recover a binding the payload does not contain.

## The measured instance on PR #1129

Verified against the stored findings, not against a summary:

| Bot | Findings | Publish shape | Outcome |
|-----|----------|---------------|---------|
| `cuioss-review-bot` (pr-agent) — **required** | 1 | `issue_comment` | **rejected** |
| `coderabbitai` — **optional** | the substantive remainder (8 `fixed` of 11 total pr-comment findings) | `inline` (path + line + `reviewed_commit_sha`) | fixed |

Over three rounds, the **required** bot produced exactly one finding and it was refuted; the
**optional** bot produced every substantive one. The required-ness of a bot is uncorrelated with
its yield here, and inversely correlated in this sample.

Worth noting *how* the one required-bot finding was disposed of, because it is the right shape:
it was **refuted on mechanism, not on a single passing run** — the claim (a `ModuleNotFoundError`
on a cross-skill `_plan_parsing` import) was answered by reading
`execute-script.py.template:270-276`, where `_SCRIPT_DIRS_FROM_MAPPINGS` unions the parent dirs of
every registered notation into `PYTHONPATH` before the spawn, plus the observation that seven other
skills already import the same module the same way, so the claim would imply
`ModuleNotFoundError` on every plan-marshall invocation.

## Candidate rule

> A review bot's barrier credit must be derived from a HEAD-bound artifact. When a bot's only
> publish shape is `issue_comment`, the barrier MUST record its participation as
> **unverifiable-against-HEAD** rather than as `participation_complete: true`, and MUST NOT let it
> satisfy a currency requirement it cannot structurally meet.

> Required-vs-optional bot designation should track measured yield, not configuration inertia.
> A required bot with a `issue_comment`-only publish shape imposes a barrier cost while supplying
> a signal the barrier cannot verify.

## Routing note

Per the standing three-way routing rule, PR/review findings route to `review-apparatus`, not to
`truthful-signals`. This is emitted here because it arrived on this plan's finalize; the
orchestrator should **delegate it to `review-apparatus` via that epic's INBOX** rather than file
it locally. It is closely related to the already-shipped PLAN-PR-007 currency test, which keys on
comment mutation rather than HEAD identity — this is the value-side evidence for why that key is
the wrong one.
