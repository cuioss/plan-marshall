envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T21:28:30Z

component=plan-marshall:phase-3-outline
category=anti-pattern
title=A sweep marked COMPLETE is still a floor

# A sweep marked COMPLETE is still a floor

An enumeration produced during outline — "these are the N sites that must change" — is a
**floor on the real count, never the count itself**, and annotating it as COMPLETE does not
change that. The annotation records the author's confidence, not the population.

## Recurrence

Reproduced **twice within the single plan** `mandatory-plan-id-build-results-ledger`
(`PLAN-TRUTH-026`, PR #1075):

1. **D4** — the outline enumerated **9 sites**; implementation found **12**.
2. **D5** — the outline's sweep was explicitly annotated *"COMPLETE — no longer a floor"*.
   It was still a floor: **12 files** enumerated, **17** actually required changing.

The D5 case is the sharper one, because the enumeration carried an explicit disclaimer of
floor-ness and was wrong anyway. This is the pattern's strongest form: **the COMPLETE
marker is evidence of confidence, and confidence is exactly what is not being measured.**

## The detail that makes this hard to catch

In the D5 case the outline was **RIGHT about one symbol and WRONG about another in the SAME
file**. A per-file spot check therefore *confirms* the enumeration — the file is in the
list, and one of its sites is correctly identified — while the second site in that same
file is silently missing. Any verification strategy at file granularity passes.

The consequence: **spot-checking an enumeration at the granularity it was authored in
cannot falsify it.** The check must run at the granularity of the *thing being enumerated*
(the symbol / call site), not the container.

## Do this instead

- Treat every outline enumeration as a **lower bound**. State the count as `>= N`, never
  `N`, and never accept a COMPLETE annotation as converting one into the other.
- Re-derive the population **mechanically at implementation time** (structured query over
  the real surface) and compare against the outline count. A mismatch is normal and
  expected; a *match* is the thing worth double-checking.
- Verify at **symbol granularity, not file granularity** — a file appearing in the
  enumeration proves nothing about the other occurrences inside it.
- When an outline says COMPLETE, treat that as a claim requiring evidence, and record what
  evidence was produced. Absent evidence, downgrade it back to a floor.

## Related patterns

- *volume-read-as-coverage* — "250 candidates examined" is a volume, not a coverage number.
- *a reviewer's list of call sites is a SAMPLE, not an enumeration* — CodeRabbit named 3
  `write_status` callers; the real count was 14.
- *every set-guarding detector must be population-derived* — the same root cause seen from
  the detector side.

This lesson is the **author-side** face of that family: the other three are about
distrusting someone else's list; this one is about distrusting your own, even after you
have marked it finished.
