envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-23T08:24:41Z

# Free-text placeholders in documented commands are not shell-quoted

Severity: high. Bundle: **plan-marshall** (workflow and standards command templates across `phase-6-finalize` and `plan-marshall`). Filed under RULING 2026-10-09 (a) — a documented command that interpolates a finding title into a double-quoted argument can execute unintended shell code.

## Sources

- corpus `2026-10-13-07-002`

## Consolidated statement

Workflow documents give command templates that interpolate free text into a double-quoted shell argument:

```text
manage-logging decision ... --message "(...) Advisory {kind} at {ref} — {title}"
manage-findings qgate add ... --title "{kind} at {ref}" --detail "{title} [fix_kind {fix_kind}]"
```

Values such as finding titles, reasons and refs regularly contain backticks, `$(...)`, double quotes or `$VAR`. Substituted into a double-quoted argument, they break the command or execute unintended shell code.

`functional-review.md` and `code-review.md` were fixed in PLAN-LB-37 (both now state a quoting rule and have contract tests). `triage.md` and `verification-feedback.md` were covered by earlier plans. The remaining scope is the other templates: the remaining `phase-6-finalize/standards/*.md` and `workflow/*.md` (e.g. `sonar-roundtrip.md`, `ci-verify.md`, `push.md`, the order-band and loop-back logging lines).

## What is asked

- Apply the single-quote-for-free-text rule to every workflow and standards document that interpolates free text into a command template.
- Consider a plugin-doctor rule that flags a `{placeholder}` inside a double-quoted argument of a documented command, so a new template cannot reintroduce the class.

## Evidence

As recorded by the sender (a Sourcery finding on PR #1759 and the two shipped fixes). Not re-verified against HEAD in this run.
