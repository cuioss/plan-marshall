envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T22:44:34Z

component=plan-marshall:plan-retrospective
category=bug
title=extract-chat-signal reported no_signal=false while retaining zero operator-authored turns - the earlier fix enumerated a sample, not the population

# A "Tier 1" verdict on a transcript with no operator content in it

## Observation

`extract-chat-signal run` on this run's 1122-turn session returned:

```
reduced_turn_count: 4      raw_turn_count: 1122     dropped_turn_count: 1118
no_signal: false           over_budget: false       reduced_bytes: 732
```

`no_signal: false` and `over_budget: false` is the **Tier 1** condition, so the aspect is
contractually told to feed those 4 turns to the LLM as this run's chat history. The 4 turns
are:

| role | what it actually is | operator-authored |
|------|--------------------|:-----------------:|
| user | `<command-message>/<command-name>/<command-args>` slash-command injection | no |
| user | `"Skill /plan-marshall:plan-marshall is already loaded above; instructions unchanged."` | no |
| assistant | one `[STATUS]` marker line | no |
| user | `<task-notification>` block (PR #1080 MERGED monitor event) | no |

**Zero operator-authored turns survived.** Retention 0.36%. The run's real operator
decisions — the `blocked_user_review` escalation at 19:02:27 where the operator
dispositioned two CodeRabbit Majors FIX-HERE, creating TASK-021 and TASK-022 — are not in
the reduced set.

## Why this is a recurrence, not a new bug

The script's docstring records a **prior fix for exactly this failure**:

> Filtering by turn ROLE alone made these indistinguishable from real operator utterances,
> so the "reduced" transcript was dominated by framework boilerplate (measured: ~90% of
> 285 KB, fewer than 10 of 287 turns operator-authored) and **a transcript with almost no
> operator signal was confidently classified Tier 1.**

That fix added drop rules for the **two** synthetic classes visible in the sample it had:
empty/whitespace turns, and skill-load bodies. The population is larger. This run exhibits
**three more** synthetic `user` classes it never enumerated. And the code carries the
resulting false claim inline:

```python
# ``no_signal`` is computed from the SURVIVING turn count — the set that is
# operator-authored by construction after the reduction above.
```

That "by construction" is false on this transcript. It is the load-bearing justification
for the `no_signal` verdict.

## Rule

- **A negation-list drop filter derived from a sample will always be incomplete.** Invert
  it: derive synthetic-ness **positively** from the harness's own injection markers — any
  `user` turn whose text is wholly enclosed in a harness tag block (`<command-message>`,
  `<command-name>`, `<command-args>`, `<task-notification>`, `<system-reminder>`,
  `<local-command-stdout>`) or is a verbatim re-entry notice — and keep what is left.
  A positive predicate fails toward "synthetic" when the harness adds a new wrapper;
  the drop-list fails toward "operator", which is the direction that produces the false
  Tier-1.
- **`no_signal` must count operator-authored survivors, not survivors.** A survivor count
  that includes harness boilerplate is the same measurement the earlier fix was written to
  remove; only the boilerplate's shape changed.
- **A fix that closes the sites its motivating sample named has not closed the class.**
  This is the second concrete instance of that archetype in this run alone (the other:
  a reviewer's named site list, `…-003`), and it is the more instructive one, because here
  the *remediation itself* was the thing that sampled.
- Cheap regression: assert that a transcript with `retention_rate < 1%` and zero turns
  passing the positive operator predicate reports `no_signal: true`.

## Impact

`plan-marshall:plan-retrospective:extract-chat-signal`, the Aspect-14 two-tier degradation
path, and every retrospective whose chat-history section currently reads as `success` on an
empty operator signal.
