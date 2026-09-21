envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:58:55Z

component=plan-marshall:manage-findings
category=bug

# Six argparse rejections on the findings surface, three of them the identical call retried

Source: script-failure cluster, notation plan-marshall:manage-findings:manage-findings
(exit_code=2, failure_kind=argparse_rejection). 6 occurrences across 5-execute and
6-finalize.

- `add` with an undeclared flag (1).
- `list` with an undeclared flag (3). Declared: any-checkout, author, bot-kind,
  file-pattern, include-qgate, kind, plan-id, preference-admissible, promoted,
  resolution, type.
- `qgate resolve` with an undeclared flag (3 CONSECUTIVE occurrences at 13:00:53,
  13:00:55 and 13:00:57). Declared: detail, hash-id, phase, plan-id, resolution.

## Solution

The three-in-three-seconds burst is a blind retry: the same rejected shape re-issued for
three different findings without reading the rejection between calls. The rejection
already named the declared flag set on the first call.

Rule worth enforcing: an `exit_code=2 / argparse_rejection` is a CONTRACT error, never a
transient one. Retrying it across a loop body multiplies one mistake by the loop count,
and the log then shows a cluster where there was a single unread message.

## Impact

Six failed calls; at most two distinct mistakes.
