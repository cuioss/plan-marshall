envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T10:39:05Z

component=plan-marshall:automatic-review
category=improvement

Relayed from Token-Sheriff PLAN-12 (PR #720 / `e52ec470`). ⚠ **Self-reported by the plan, and worth relaying for that reason**: a review bot's claim about inherited build configuration was reported to the operator as confirmed BEFORE the effective POM was resolved; triage then refuted it (the config is declared at plugin level, which Maven applies to `default-cli`). ⛔ The plan whose own subject is build-config truthfulness skipped the effective-POM pre-flight its sibling shipped into `AGENTS.md`. A discipline that its own author forgets under review pressure is a candidate for a mechanical check rather than a documented rule.

# Candidate lesson: a mechanism claim about inherited build configuration was reported to the operator as confirmed before it was checked against the effective POM

**Component**: `plan-marshall:phase-6-finalize` (review-comment triage / orchestrator reporting)
**Signal class**: automated-review (`signal_automated_review_count`) — remediated review-bot finding
**Landed in**: PR #720, squash commit `e52ec470`.

## Observation

CodeRabbit reported that the documented apply command

```text
./mvnw -Ppre-commit license:format rewrite:run
```

would not inherit execution-scoped configuration, and would therefore run unconfigured.

Before verifying it, the orchestrator asserted to the operator that this was a confirmed real
defect. The subsequent triage **refuted** it against the effective POM: `cui-java-parent`
declares `activeRecipes` and the license configuration at **plugin** level — a sibling of
`<executions>`, not inside one — and Maven applies plugin-level configuration to `default-cli`
invocations. The unqualified command is correct as documented.

## The generalizable rule

A plausible mechanism claim about inherited build configuration must be checked against the
**resolved effective POM** before it is reported as established. Plugin-level and
execution-level configuration are visually adjacent in a POM and produce opposite answers for a
CLI-goal invocation; reasoning about which one applies without resolving inheritance is a guess
that reads like an analysis.

The self-reinforcing part: this plan exists to enforce exactly that effective-POM pre-flight,
and the error was committed while working on it. The pre-flight is not just a rule the tooling
applies to the repository — it is a rule the reporting path owes the operator.

## Suggested direction (for orchestrator judgement)

Separate "a reviewer claims X" from "X is established" in what is said to the operator, and
require the effective-POM resolution before any inherited-build-config claim crosses that line.
