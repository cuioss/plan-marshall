envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:49:13Z

# Script-failure cluster: architecture search rejected a post-verb --plan-id it declares at top level

**Signal**: script-failure cluster (1 of 9 distinct failing notations on this plan)
**Notation**: `plan-marshall:manage-architecture:architecture`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## Evidence

```text
[2026-09-04T11:31:16Z] [ERROR] plan-marshall:manage-architecture:architecture search (0.30s)
  exit_code: 2
  args: search --content --literal --pattern declined --plan-id plan-145-publish-the-missing-parser-seams
  stderr: usage: architecture.py [-h] [--project-dir PROJECT_DIR] [--plan-id PLAN_ID]
                                 {discover,init,...,search,...}
          architecture.py: error: unrecognized arguments: --plan-id plan-145-publish-the-missing-parser-seams
          note: --plan-id
```

The very next `architecture` call (`11:31:35`) is logged with the verb `--plan-id`, i.e. the corrected pre-verb position.

## Why it is candidate-lesson material

The usage line the caller was shown **displays `--plan-id` as a top-level option** and then rejects it as "unrecognized" — which reads as "this flag does not exist" while the flag is printed one line above. The flag was real, declared, and in the wrong position.

The deeper hazard is that `--plan-id`'s scope is **per-script and oppositely signed across the surfaces a single workflow touches**: router-scoped (pre-verb) on `architecture` and `ci`, verb-scoped (post-verb) on `manage-findings` / `manage-status` / `manage-lessons`, and undeclared on others. A caller moving between them within one step has no positional rule to carry, only a per-script lookup. The project's recurrence-signature list names both directions precisely because neither generalizes.

## Proposed rule (for orchestrator judgement)

When argparse rejects a flag that the script **does** declare at a different scope, say so: "`--plan-id` is a top-level flag on this script; place it before the verb." The rejection already prints a `note: --plan-id` stub — completing that note into the positional instruction is a one-line change that converts an unreadable rejection into a self-correcting one.

## Related already-active lessons

- `2026-09-03-19-004` — name the rejected flag and the sibling verb's canonical form in argparse-rejection messages
- `2026-08-25-09-011` — `search --content` patterns are regexes, so a metacharacter-bearing query can return a false zero
