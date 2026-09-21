envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T09:35:56Z

component=plan-marshall:manage-logging
category=bug
title=A multi-sentence decision message landed as four unattributed fragments plus the real entry

# A multi-sentence decision message landed as four unattributed fragments plus the real entry

Observed first-party in PLAN-203's decision log during
`project:finalize-step-lessons-housekeeping`.

## Evidence (verbatim, from `manage-logging read --type decision`)

```
2026-07-30T07:12:03Z INFO 3b5f40  test message plan ID citations regeneration
2026-07-30T07:12:13Z INFO 29ffec  retained 2026-07-29-17-002: D3 only derives inbox counts
2026-07-30T07:12:22Z INFO 40e773  lesson core guarded failure (stale plan-ID citations, no enforced regeneration) remains open
2026-07-30T07:12:31Z INFO c2d2e4  filed via D4 findings, not fixed
2026-07-30T07:12:43Z INFO 2ab924  (project:finalize-step-lessons-housekeeping) retained 2026-07-29-17-002: D3 only derives inbox counts in resume-summary. Lesson core guarded failure (stale plan-ID citations, no enforced regeneration) remains open. D4 gate filed it via findings, not fixed
```

The four 07:12:03–07:12:31 rows are **consecutive sentence fragments** of the single well-formed
07:12:43 entry, and — unlike every other row in the store — they carry **no `(component)` prefix**.
The store therefore holds **4 phantom decision entries** alongside 1 real one, for one logical
decision.

## Why it matters here specifically

The decision log is a machine-held record that other surfaces are being asked to **derive from**
(see the sibling candidate about `epic.md`'s Decisions list duplicating it). A store that silently
accretes fragments of a message is a **corrupted denominator**: any future count over the decision log
over-reports, and the over-report will look derived, not narrated. That is the epic's theme one layer
below the surfaces the epic has been auditing.

## Claim labels

- OBSERVED: the five rows above and their fragment/whole relationship, read back from the store.
- HYPOTHESIS (**not confirmed — do not act on it as fact**): the message was split at sentence
  boundaries by a shell/hook interaction on `--message` (the repo already carries a known hazard where
  a literal `;` in a `manage-logging` message trips the one-command hook), and the fragments are the
  residue of a retry. **The mechanism is unverified**; what is certain is only that four malformed
  entries reached the store.

## Suggested next step

Reproduce by logging a multi-sentence decision message and reading the store back; if confirmed,
`manage-logging` should write exactly one entry per invocation or reject the message — never a partial
prefix.
