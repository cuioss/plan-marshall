envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:05:58Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# Two prescribed manage-logging messages contain a literal semicolon and can never be emitted in this repo

Two workflow documents prescribe a `manage-logging` invocation whose `--message` text contains a **literal semicolon**. The one-command-per-Bash-call enforcement hook rejects such a command outright, so as written those two log records can never be emitted in this repository.

Affected sites:

1. `project:finalize-step-plugin-doctor` SKILL.md — the scoped-mode warning message.
2. `plan-marshall:phase-6-finalize` SKILL.md — item 5f(d), the freshness-reconcile message.

Both are latent: the surrounding step succeeds, the log line simply never appears, so the absence is invisible at the call site and only shows up as a gap in the work log.

## Solution

Rewrite both message strings so they carry no shell-significant character. Use an em dash, a comma, or a second clause in place of the semicolon. Do not attempt to escape or quote around the hook — the hook is correct and the message text is what is wrong.

Then close the class rather than the two instances: add a plugin-doctor check that flags shell-significant characters inside a prescribed `--message` literal in marketplace docs, so the next author cannot reintroduce it.

## Impact

Every plan that reaches these two finalize steps loses the corresponding audit record. The wider point is the recurring shape: a **prescribed** command in a workflow doc is executable content, and a doc-level defect in it is a runtime defect, not a typo. Prescribed invocations deserve the same structural linting as source.
