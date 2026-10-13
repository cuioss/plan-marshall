envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=finding
created=2026-10-13T06:27:57Z

# Follow-up: shell-quote free-text placeholders in every workflow command template

**From:** lb-37-functional-review (PLAN-LB-37), raised by Sourcery on PR #1759 (finding 639e7d, `phase-6-finalize/workflow/functional-review.md:463`)

## Observation

Workflow documents give command templates that interpolate free text into a double-quoted shell argument. For example:

```text
manage-logging decision ... --message "(...) Advisory {kind} at {ref} — {title}"
manage-findings qgate add ... --title "{kind} at {ref}" --detail "{title} [fix_kind {fix_kind}]"
```

Values such as finding titles, reasons and refs regularly contain backticks, `$(...)`, double quotes or `$VAR`. Substituted into a double-quoted argument, they break the command or execute unintended shell code.

## Done in PLAN-LB-37

The operator chose to fix the two review workflows this plan changed, `functional-review.md` and `code-review.md`, in the plan itself. Both now state a quoting rule for free-text placeholders, and contract tests pin it.

## Remaining scope for a later plan

Apply the same rule to every other workflow and standards document that interpolates free text into a command template. That includes at least `plan-marshall/workflow/triage.md`, `plan-marshall/workflow/verification-feedback.md` and the remaining `phase-6-finalize/standards/*.md` and `workflow/*.md` (e.g. `sonar-roundtrip.md`, `ci-verify.md`, `push.md`, the order-band and loop-back logging lines). Consider a plugin-doctor rule that flags a `{placeholder}` inside a double-quoted argument of a documented command.
