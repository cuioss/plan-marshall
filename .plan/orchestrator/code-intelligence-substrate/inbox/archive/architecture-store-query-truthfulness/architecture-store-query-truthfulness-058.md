envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:58:54Z

component=plan-marshall:manage-architecture
category=bug

# The same router-flag placement error hit the architecture surface in two different phases

Source: script-failure cluster, notation plan-marshall:manage-architecture:architecture
(exit_code=2, failure_kind=argparse_rejection). 2 occurrences.

1. 3-outline: an undeclared flag on `architecture search`. Declared set: category,
   content, ignore-case, literal, pattern, plan-id, pre, project-dir.
2. 6-finalize: `--plan-id architecture-store-query-truthfulness` placed AFTER the verb.
   The rejection message states the fix outright — "--plan-id is a top-level flag and
   belongs BEFORE the subcommand (verb), not after it. The flag exists — it is only in
   the wrong position."

## Solution

The second is the interesting one, because the error message already contains the
complete remedy and the call still failed. The flag-position rule is per-SURFACE and it
inverts between surfaces: on `architecture` and `ci` the flag is router-scoped
(before the verb); on other manage-* scripts the same flag NAME is declared on the
subcommand (after the verb). An agent generalizing from one surface to the other
produces a rejection whose message reads like "this flag does not exist".

## Impact

Two rejections in one run on one script, three phases apart, from two different causes.
