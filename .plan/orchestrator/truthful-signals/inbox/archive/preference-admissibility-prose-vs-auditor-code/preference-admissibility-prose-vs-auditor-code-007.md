envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T14:29:22Z

component=plan-marshall:manage-architecture
category=bug
bundle=plan-marshall

# `architecture search` and `find` return a coverage-clean zero against a deleted worktree root

## Rule

When a client resolves its data root from recorded state that a later step can invalidate, every
verb reading that root must fail the same way when it is gone. A verb that answers `count: 0` while
its sibling answers `data_not_found` over the identical root is not reporting a negative result — it
is reporting that it could not look, in the vocabulary reserved for having looked.

## Observation

Observed during the retrospective of PLAN `preference-admissibility-prose-vs-auditor-code`, after
`branch-cleanup` removed the plan's worktree. Four calls, same machine, same moment:

| Call | Result |
|---|---|
| `architecture --plan-id P search --content --literal --pattern _preference_admissible` | `status: success`, `count: 0`, `file_count: 0`, `files_scanned: 0`, `unreadable[0]`, `truncated: false`, `elided[0]` |
| `architecture search --content --literal --pattern _preference_admissible` (no `--plan-id`) | `status: success`, `count: 2`, `file_count: 1`, `files_scanned: 5361` |
| `architecture --plan-id P find --pattern 'marketplace/.../manage-findings/scripts/*'` | `status: success`, `count: 0`, `truncated: false`, `elided[0]` |
| `architecture find --pattern 'marketplace/.../manage-findings/scripts/*'` (no `--plan-id`) | `status: success`, `count: 10` |

`_preference_admissible` is a literal **this plan shipped**, so the zero is definitively wrong.
`architecture --plan-id P info` on the same root fails loudly:

```
status: error
error: data_not_found
expected_file: /Users/oliver/git/plan-marshall/.plan/local/worktrees/preference-admissibility-prose-vs-auditor-code/.plan/project-architecture/_project.json
resolution: Run 'architecture.py discover' first
```

So one resolver, three verbs, two behaviours: `info` reports the missing root; `search` and `find`
report a clean empty tree.

## Why the published coverage block does not cover it

CLAUDE.md instructs readers to trust a `count: 0` only when the coverage block is clean, and names
that block as the discriminator. Here the block IS clean — `unreadable[0]`, `truncated: false`,
`elided[0]` — because there was nothing to fail on. The only field that betrays the state is
`files_scanned: 0`, and it is not among the fields the documented complete-coverage rule names.
`find` is worse: it publishes **no** population field at all, so its dead-root zero is
indistinguishable from a real zero by any published field.

## Blast radius

`architecture` is the repository's mandated first-line discovery seam ("Structured queries first"),
and `--plan-id` is the documented way to scope it. Every finalize step ordered after
`branch-cleanup` runs against a removed worktree — this plan ran six of them
(`deploy-target`, `sync-plugin-cache`, `review-retrospective`, `plan-retrospective`,
`lessons-capture`, `preference-emitter`) — and any of them passing `--plan-id` gets a confident,
coverage-clean "not in any inventoried file" over a tree that was never opened.

## How to apply

- **Fail closed at the resolver.** If `info` raises `data_not_found` for a root, `search` and `find`
  must raise it too. One root-existence check, applied before any verb answers.
- **Publish the population on every enumerating verb.** `find` needs a `files_scanned` (or
  equivalent) field; a zero with no denominator cannot support a negative claim.
- **Add `files_scanned: 0` to the complete-coverage rule** in `manage-architecture/standards/client-api.md`
  § search, alongside `unreadable` / `truncated` / `elided`. A clean coverage block over an empty
  scan population is not a clean result.
- **Reader side, until fixed:** a positive control is the only reliable check. This defect was found
  by searching for a literal known to exist, not by inspecting the response.
