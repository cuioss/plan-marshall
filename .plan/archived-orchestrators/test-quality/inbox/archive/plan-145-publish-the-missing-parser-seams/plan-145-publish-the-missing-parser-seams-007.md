envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:48:42Z

# Script-failure cluster: manage-config resolve-domain-skills called without its required --domain/--profile

**Signal**: script-failure cluster (1 of 9 distinct failing notations on this plan)
**Notation**: `plan-marshall:manage-config:manage-config`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## Evidence

```text
[2026-08-29T21:44:40Z] [ERROR] plan-marshall:manage-config:manage-config resolve-domain-skills (0.00s)
  exit_code: 2
  args: resolve-domain-skills --plan-id plan-145-publish-the-missing-parser-seams
  stdout: status: error / error: invalid_invocation
          reason: missing_required_flag
          rejected: --domain, --profile
```

Fired at `1-init` (the first minute of the plan). The caller supplied `--plan-id` and nothing else; the verb declares `--domain` and `--profile` as required.

## Why it is candidate-lesson material

This is recurrence signature 5 of the "never invent script subcommands" family (missing required flag), but with a specific twist worth naming: the caller supplied the **plan-scoping flag it habitually supplies** and omitted the two flags that actually select the answer. `--plan-id` is the reflex argument; on this verb it carries no selection at all. The failure is therefore not "forgot a flag" but "substituted the habitual flag for the discriminating one", which is a shape a doc-level example can prevent and a rules card cannot.

## Proposed rule (for orchestrator judgement)

For any verb where `--plan-id` is accepted but **not** sufficient, the canonical-invocation block should show the full required set on one line, and the argparse rejection should name the sibling verb's canonical form (see already-active lesson `2026-09-03-19-004`).

## Related already-active lessons

- `2026-09-03-19-004` — name the rejected flag and the sibling verb's canonical form in argparse-rejection messages
