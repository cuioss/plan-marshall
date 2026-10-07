envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=review-apparatus
kind=finding
created=2026-08-02T14:42:34Z

# Finding: `automatic-review` workflow docs prescribe a `--enabled-bots` flag no script declares

## What was observed

During PLAN-CIS-027's finalize (PR #1079), the dispatched `automatic-review` leaf
followed `automatic-review/SKILL.md` verbatim and hit a hard argparse rejection:

```
github_pr.py: error: unrecognized arguments: --enabled-bots pr-agent,coderabbit,sourcery
```

Both consuming scripts have moved to a required/optional split that the docs never
caught up with:

| Site | Doc prescribes | Live argparse surface |
|------|----------------|-----------------------|
| `github_pr fetch_findings` | `--enabled-bots` | `--required-bots` / `--optional-bots` |
| `review_completeness check` | `--enabled-bots`, `--settled-bots` | `--required-bots`, `--optional-bots`, `--participated-bots`, `--in-progress-bots`, `--refused-bots` |

## Why this belongs to review-apparatus

The drift is entirely inside the automated-PR-review surface: the FIND producer, the
participation predicate, and the docs that drive them. It is not a
code-intelligence-substrate concern; PLAN-CIS-027 only encountered it as a caller.

## Why it is worse than an ordinary stale doc

This is the argparse-rejection archetype **sourced from the workflow doc itself**
rather than from model improvisation. A leaf that obeys the "no improvisation" hard
rule and quotes the doc verbatim is guaranteed to fail. The usual mitigation
("quote the doc, never invent a verb") does not help when the doc is the thing that
is wrong.

Two second-order consequences:

1. The doc's D3 instructions tell the caller to compute a `{settled_bots}` union.
   The live `review_completeness` script rejects a bare `bot_kind` with no
   `evidence_kind`, deliberately, so that unqualified presence cannot be mistaken
   for proof of review. A caller following the doc would fail closed — but for the
   wrong reason, and the failure would read as a participation gap rather than a
   caller bug.
2. `enabled_bots` also survives as a `configurable:` key in the frontmatter, while
   the live step-params carry `required_bots` / `optional_bots` /
   `bot_lists_provenance`.

## Affected sites

- `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` —
  section "Producer: FIND", section "Step-done completeness guard (D3)", the
  `## Canonical invocations` block, and the `enabled_bots` frontmatter key.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` —
  section Canonical invocations, `github_pr fetch_findings` omits both live flags.

## Suggested check to add alongside the fix

A doc-vs-argparse conformance check over `## Canonical invocations` blocks would
catch this class structurally: every flag a canonical block prescribes must exist in
the referenced script's declared surface. The existing `manage-invocation-invalid`
plugin-doctor rule already parses those blocks, so the flag-level assertion is an
extension of a mechanism that is already in place rather than a new one.

## Provenance

Surfaced by the `automatic-review` dispatch during PLAN-CIS-027 finalize
(PR #1079). The leaf worked around it by reading the live `--help` surface, so the
plan was not blocked and no code was changed for it.
