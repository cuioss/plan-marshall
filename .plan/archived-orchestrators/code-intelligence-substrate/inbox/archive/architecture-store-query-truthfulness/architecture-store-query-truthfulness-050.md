envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:57:33Z

component=plan-marshall:execute-task
category=bug

# A log echoing its own pytest command satisfied the "the test ran" check

Source: PR #1489 CodeRabbit inline finding 881d23 (resolution=fixed, TASK-034).

count_log_nodeids scans EVERY line with _NODEID_TOKEN_RE, and the per-identifier
exact/parametrized regexes also scan every line. A log containing the command
`pytest test/foo.py::test_login` therefore yields both a non-zero nodeid population AND
an exact identifier match, with no evidence that pytest collected or ran anything.

## Solution

Restrict BOTH the population count and the identifier match to pytest result /
enumeration lines.

The general shape: when a detector's evidence is "this token appears in the output", the
token appearing in the INVOCATION is indistinguishable from it appearing in the RESULT.
Any check that reads a command's own log for proof of what the command did must first
exclude the echo of the command itself.

## Impact

This is the mechanism the whole execute-task verification gate rests on, so a false
positive here certifies an unrun test as run.
