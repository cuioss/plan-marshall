envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T07:51:49Z

component=plan-marshall:build-server-client
category=anti-pattern

# marshalld submit rejects a relative executor path as `executor_mismatch`, which reads as a version problem and is not

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-01
(`pre-commit-gate-truthfulness`, merged as PR #713 / `29d9f6c5`).

## Observation

The marshalld build-server `submit` verb requires `argv[1]` to be the **absolute**
`{exec_path}/.plan/execute-script.py`. Passing the relative `.plan/execute-script.py`
— which is the form every other call site in the project uses, and the form the
surrounding documentation shows — is refused with `executor_mismatch`.

`executor_mismatch` names a *version/identity* disagreement between the client's
executor and the daemon's. The actual cause is a *path-form* disagreement. The error
therefore sends the reader to check the daemon version, the enrolment record, and the
bundle copy — none of which are wrong — while the fix is to make one argument
absolute.

## The generalisable rule

An error code that names a plausible-but-wrong cause is worse than a generic one. A
caller who trusts the code spends its diagnostic budget in the wrong place; a caller
who receives `invalid_argument` at least starts by re-reading the argument.

When one predicate can fail for two structurally different reasons — here, "these are
different executors" and "this is the same executor spelled differently" — the two
must not share an error code.

## Suggested remedy

- Normalise the path before comparing, so a relative and an absolute spelling of the
  same executor compare equal; OR
- if the absolute form is genuinely required, refuse a relative path with a distinct
  code (e.g. `executor_path_not_absolute`) whose message names the required form.
- Either way, the canonical-invocation block should show the absolute
  `{exec_path}/.plan/execute-script.py` form explicitly, since the relative form is
  what a reader would otherwise copy from every neighbouring example.
