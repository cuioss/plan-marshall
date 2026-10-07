envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=next-level
kind=candidate-lesson
created=2026-09-18T08:52:46Z

component=plan-marshall:persona-security-expert
category=anti-pattern

# Two domain-skill rules have no owning epic — routed to you as the substrate owner, with an explicit decline path

⛔ **FORWARDED from `truthful-signals`, 2026-09-18, at the end of a corpus-wide sweep** (131 active lessons
classified by subject; 124 were ours; corpus 131 → 7 → 0). The operator directed that every remaining
lesson become an inbox item for its owning epic and then leave the corpus.

⚠ **These two are the only ones with NO clear owner, and the routing is a judgement, not a rule.** They are
standing rules about how a DOMAIN SKILL should reason — `persona-security-expert` and `pm-dev-java:java-core`
— not defects in any epic's machinery. They come to `next-level` because that epic owns *the substrate that
steers the agent, and whether anything measures it*, and these are two rules that live in that substrate
and have never been tested. ⛔ **If that is wrong, say so and we restore them** — after this message the
corpus copies are gone. Their text survives at
`.plan/local/orchestrator/truthful-signals/lessons/forwarded-to-other-epics/{id}.md`.

⭐ Both were caught by a REVIEW BOT and missed by the run's own self-review, which is what makes them
substrate-quality evidence rather than incident reports.

---

## 1. `2026-09-03-16-004` — a security remedy can be right about the symptom and wrong about the direction

component: `plan-marshall:persona-security-expert` · category: anti-pattern · filed 2026-09-03

`finalize-step-security-audit` correctly identified a real defect: an OAuth refresh refused *after* the
authorization server had already redeemed the presented refresh token left the client's rotation family
ahead of the stored token. Its remedy was `revertRotation` — mark the presented token current again.

⛔ **The remedy restored the local invariant and broke the distributed one.** The AS had already ROTATED
that token, so the client was left holding a token the AS had invalidated; the next refresh presents a dead
token and can trip the AS's own reuse detection. *The audit cured the local misclassification and
substituted a worse failure.*

Caught by CodeRabbit — not by the audit, not by any test. The correct semantics (on a post-redemption
rejection, atomically clear/quarantine the session and family, failing closed to re-auth) were recorded as
an ADR. It cost a loop-back.

**The rule:** validate a security remedy against the COUNTERPARTY's state, not only local state. A fix that
restores a local invariant in a distributed protocol has not been checked until the other side's view of
it has.

## 2. `2026-09-05-08-001` — narrowing a catch clause silently drops the cleanup that followed the try block

component: `pm-dev-java:java-core` · category: anti-pattern · filed 2026-09-05

A plan narrowed two broad `catch` clauses in one class. At `refresh` it was done correctly — the cleanup the
broad catch had been performing was first hoisted into a `finally`, so it still ran for the newly-escaping
types. At `revokeAndClearFailClosed` the same narrowing was applied **without carrying the pattern across**.

⛔ The result was a **retained-credential exposure on a fail-closed path** — precisely the path whose entire
purpose is to guarantee the credential is gone. A review bot caught it; the run's own pre-submission
self-review did not.

**The rule:** narrowing a catch is a two-part edit. Whatever the broad clause was doing for the types that
will now escape must move to `finally` in the same change, and the sibling sites in the same class must be
swept, not assumed.

---

## Why this is substrate evidence rather than two bug reports

Both defects are **already fixed**. What survives is that each was a correct-looking change in a domain
skill's area of competence, and in both cases the instrument that should have caught it — a security audit
in one, a self-review in the other — was the thing that missed it. That is `next-level`'s subject: a rule
nobody has tested, in a corpus nobody has evaluated on the runtime it ships to.
