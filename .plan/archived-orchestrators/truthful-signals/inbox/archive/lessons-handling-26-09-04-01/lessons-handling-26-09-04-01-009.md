envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T07:51:50Z

component=plan-marshall:build-maven
category=bug

# The maven wrapper's own --timeout defaults to 300s independently of the daemon's supervisory bound, so a long build silently times out

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-01
(`pre-commit-gate-truthfulness`, merged as PR #713 / `29d9f6c5`).

## Observation

The maven build wrapper carries its **own** `--timeout`, which defaults to **300 s**
when no learned value exists for the build. That default is applied independently of
the build daemon's supervisory bound — raising the daemon's budget does not raise the
wrapper's.

The consequence is a build killed at 300 s while every visible budget says it had far
longer. Nothing in the surrounding configuration (`build.queue.upper_limit_seconds`,
the per-step timeouts, the Bash tool timeout) explains the cut-off, so the timeout
reads as a hang or a flake rather than as the enforcement of a limit nobody set
deliberately.

The trap is specifically the **cold** case: once a learned value exists the default
never applies, so the failure appears on a first run of a slow build — exactly when
the operator has the least basis for expecting it.

## The generalisable rule

Two independent timeouts governing one operation, where only one of them is visible at
the configuration surface, is a false-signal generator. The tighter-and-invisible
bound wins, and its enforcement is indistinguishable from the operation failing on its
own.

Nested budgets must either derive from one another, or the inner one must be reported
when it fires ("killed by wrapper --timeout=300s") so the cause is readable from the
failure itself.

## Suggested remedy

- Derive the wrapper's default from the daemon's supervisory bound instead of
  hard-coding 300 s, so raising one raises both; OR
- make the wrapper's timeout kill emit an explicit message naming the flag and the
  value that fired.
- Until then, the operational rule is: pass `--timeout` explicitly to the maven wrapper
  for any build expected to exceed five minutes; do not assume the daemon's budget
  governs it.
