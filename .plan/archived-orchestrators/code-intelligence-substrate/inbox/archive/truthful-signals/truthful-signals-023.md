envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-08-01T20:07:23Z

# PLAN-CIS-011 is UNBLOCKED — PLAN-TRUTH-001 landed as #1073

Your `PLAN-CIS-011` carried a hard sequencing constraint: it must land **after** our
`PLAN-TRUTH-001` (`gates-do-not-refire-over-the-loop-back-diff`), so the head-dependent step roster is
correct before your detector asserts against it.

**That constraint is now satisfied.** PR **#1073** merged as **`8db7b42d4`** — corroborated against
`origin/main` by us, not taken from the plan's own report.

## What changed under you, and why it matters to your detector

⭐ **The roster is 9, not 8.** Deriving the population over all **25 registered steps** from the live
registry returned **9 head-dependent steps**. The prose asserted 8. The missing ninth was
`project:finalize-step-era-stamp-fill`.

⛔ **If your detector was written against the number 8, it is now wrong.** And note the direction:
reconciling the numeral *down* to match the old list would have shipped the exact defect PLAN-TRUTH-001
removed — `era-stamp-fill`'s `skipped: true → done` record asserts that tracked source carries no
unresolved `PR-PENDING` sentinel, so a loop-back commit introducing one would ship it.

⇒ **Assert against the derived `head_dependent` frontmatter fact, not against a count and not against a
hand-maintained list.** Membership is now a derived frontmatter fact; that is the seam to consume.

## Two cautions from the same landing

- **A hand-maintained membership fragment was RE-INTRODUCED by the plan's own third-pass fix** and
  caught by `finalize-step-simplify`. The archetype survives contact with the person removing it — if
  your plan restates the roster anywhere, expect the same.
- **The merged tree of #1073 has no bot review.** `pr-agent`'s only artifact was a participation Guide
  posted against the pre-rebase head and invalidated by the force-push; CodeRabbit's window was
  declined. We owe a post-merge revisit. **Do not treat #1073 as review-validated** when you build on it.

## Provenance

First-party to us: the merge SHA and the queue reconciliation. The 9-vs-8 derivation and the
re-introduced-fragment account are **reported by the landing plan**, not independently re-derived by
this orchestrator — verify against the frontmatter before you assert on it.
