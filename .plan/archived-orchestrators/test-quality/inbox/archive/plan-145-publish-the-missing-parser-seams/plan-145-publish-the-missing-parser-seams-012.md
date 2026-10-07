envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:49:07Z

# Script-failure cluster: ci pr prepare-body rejected --pr-number, the flag the sibling verbs all take

**Signal**: script-failure cluster (1 of 9 distinct failing notations on this plan)
**Notation**: `plan-marshall:tools-integration-ci:ci`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## Evidence

```text
[2026-09-03T21:34:17Z] [ERROR] plan-marshall:tools-integration-ci:ci pr (0.00s)
  exit_code: 2
  args: pr prepare-body --plan-id ... --for edit --pr-number 1395
  stdout: status: error / error: invalid_invocation
          reason: unknown_flag / rejected: --pr-number
          accepted: for, plan-id, slot
```

Corrected on the next call four seconds later.

## Why it is candidate-lesson material

`--pr-number` is the flag nearly every other `ci pr` verb takes (`view`, `comment`, `merge`), so supplying it to `prepare-body` is the natural generalization from the surrounding surface — and `prepare-body` is precisely the verb that does not need it, because it prepares a body for a slot rather than acting on a PR. The rejection is correct; the surface is the trap.

This notation also carries the mirror-position hazard the project already names as recurrence signature 4: on `ci`, `--plan-id` is **router**-scoped and must precede the first positional, the opposite of the `manage-architecture` / `manage-config` rule. Two adjacent, oppositely-signed rules on one script surface is a standing recurrence source.

## Proposed rule (for orchestrator judgement)

`ci pr prepare-body` should reject `--pr-number` **by name with its reason** ("prepare-body is slot-scoped; use `--slot`"), not by listing the accepted set and leaving the caller to infer why the obvious flag is absent. This is the same remedy already recorded for the router-position `--plan-id` case.

## Related already-active lessons

- `2026-09-03-19-003` — `ci pr prepare-body` must reject a router-position `--plan-id` by name instead of reporting it missing
- `2026-09-03-02-002` — `ci pr view` returns no `body` field, forcing a `gh` bypass on any PR-body edit flow
- `2026-09-03-19-004` — name the rejected flag and the sibling verb's canonical form in argparse-rejection messages
