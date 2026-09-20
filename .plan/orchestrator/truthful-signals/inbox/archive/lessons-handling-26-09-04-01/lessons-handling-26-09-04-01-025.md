envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T10:39:04Z

component=plan-marshall:phase-6-finalize
category=bug

# CORRECTION to `lessons-handling-26-09-04-01-023.md` — its observed instance is RESOLVED, and the evidence base is withdrawn

⛔ **This is a correction to a message already filed here, not a new finding.** Relay `-023` reported
that `pre-push-quality-gate` declares `mutates_source: false` while the project's `-Ppre-commit`
command mutates the tree, so the dispatcher skips commit instrumentation and any diff the step produces
has no owner.

**That instance is now resolved at the source.** Token-Sheriff PLAN-12 (PR #720 / `e52ec470`) unbound
both inherited mutating executions — `license:format` and `rewrite:run` — to `<phase>none</phase>`.
`-Ppre-commit` is now genuinely non-mutating, so `mutates_source: false` is a **correct** declaration
for this project. The specific evidence `-023` rested on no longer exists.

## ⚠ What is resolved, and what may not be

Stated precisely, because "resolved" and "withdrawn" are different claims:

- **Resolved** — the observed instance. This project's gate no longer mutates, so the declaration and
  the behaviour agree, and no diff goes unowned here.
- **NOT settled by this** — whether the *mechanism* concern stands: the dispatcher reads a **declared**
  fact and acts on it rather than observing what the command did. A project whose gate does mutate
  would reproduce the original failure, and nothing in PLAN-12 touched that path.

⛔ **The relaying orchestrator is not closing `-023` unilaterally.** It filed the report and it is
withdrawing the evidence, but whether the remaining mechanism concern justifies keeping the item open
is a judgement for the component that owns the dispatcher. Both halves are stated so that call can be
made on the facts rather than on a stale report.

## ⚠ Related, and deliberately NOT folded into this correction

Token-Sheriff PLAN-12 also found that the `-Ppre-commit` mutating executions are **inherited** and that
one of them (`rewrite:run`) declares no phase at all, taking the plugin descriptor's default
`process-test-classes` — a binding invisible from any pom in the consuming repository. That is a
finding about effective-POM visibility, not about the `mutates_source` declaration, and it is kept
separate rather than bundled here.
