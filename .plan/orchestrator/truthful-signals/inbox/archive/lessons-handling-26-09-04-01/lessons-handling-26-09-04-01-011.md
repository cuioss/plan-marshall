envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T07:53:55Z

component=pm-dev-java:java-core
category=anti-pattern

# Narrowing a catch clause silently drops the cleanup that followed the try block

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-01
(`pre-commit-gate-truthfulness`, merged as PR #713 / `29d9f6c5`).

⚠ **Routing note, stated so the receiving drain can correct it.** This is NOT a
signal-truthfulness defect and `truthful-signals` may not be its right home. It is sent
here because that is this sender's only established channel into this repository. Its
component `pm-dev-java:java-core` is a bundle THIS repository owns — the Token-Sheriff
lessons store refused to file it (`wrong_store`), which is how the routing was
determined rather than guessed. Please re-route it to whichever epic owns `pm-dev-java`
standards. The `--allow-foreign-store` override was deliberately NOT used.

The companion half of this candidate — the self-review surfacer improvement — was
relayed separately as `lessons-handling-26-09-04-01-010.md`.

## Observation

A plan narrowed two broad catch clauses in `TokenLifecycleManager`. At `refresh` the
narrowing was done correctly: the cleanup the old broad catch had been performing was
first hoisted into a `finally` block, so it still ran on the newly-escaping exception
types. At `revokeAndClearFailClosed` the same narrowing was applied WITHOUT carrying the
pattern across. The result was a retained-credential exposure on a fail-closed path —
exactly the path whose entire purpose is to guarantee the credential is gone.

A review bot caught it. The run's own pre-submission self-review did not.

## The generalisable rule

When you narrow a `catch`, the question is not "are the new exception types handled" —
it is:

> **What ran AFTER the try/catch, and must it now run unconditionally?**

A broad catch swallows everything, so any statement after it executes on every path.
Narrowing the catch turns those statements into conditionally-executed code **without
editing a single line of them**. The diff shows a smaller catch; it does not show the
cleanup that stopped running. Move the cleanup into `finally` FIRST, then narrow.

## Suggested rule for the corpus

Java review: narrowing a catch requires an explicit statement of what followed the try
block and whether it is now conditional. The reviewer should be able to answer that
question from the diff; if they cannot, the diff is incomplete rather than clean.
