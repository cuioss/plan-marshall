---
name: tools-epic-surface-partition
description: Derives an epic's test-tree surface partition and per-plan budget attribution from its staged spec corpus, read-only and never a build gate
user-invocable: false
mode: script-executor
---

# Epic Surface Partition Skill

Read-only derivation over an epic's staged plan specs. It answers the question no
ledger verb answers: which entry under `test/` does each plan claim, and which
entries does no plan claim at all.

## Enforcement

**Prohibited actions:**
- Do not invoke the scripts with arguments other than those in [Canonical invocations](#canonical-invocations)
- Do not edit any spec under the orchestrator store — this skill reads it and never writes it
- Do not wire any subcommand into a build gate; the specs are git-ignored and absent from a fresh clone

**Constraints:**
- Run scripts EXACTLY as documented in [Canonical invocations](#canonical-invocations)
- All output is TOON on stdout; an operation failure is `status: error` at exit code 0

## Purpose

An entry under `test/` that no plan claims looks exactly like a clean run. This
skill makes an unclaimed entry a reported fact rather than something each run
rediscovers by hand, and keeps *"unclaimed"* and *"claimed only by a spec the
parser cannot resolve"* as two verdicts that are never merged.

The corpus is enumerated by glob, so a spec added to the epic is picked up with
no edit to any script.

## When to Use This Skill

Activate when you need to:
- Classify every spec's `## Expected Surface` before relying on the partition
- Find `test/` entries that no plan claims, or that two plans claim
- Size a campaign run from the budget findings grouped by owning plan

## The Three-Class Model

`classify` assigns every spec exactly one class and records the evidence:

| Class | Meaning |
|-------|---------|
| `declarative` | The Expected Surface resolves to at least one path entry |
| `derived` | The section declares its surface a function of other plans' surfaces |
| `prose` | A section is present, but resolves to no path entry |

The first two are usable by the partition; the third is **reported**, because a
`test/` entry claimed only by a `prose`-class spec is coverage the derivation
cannot see rather than a partition defect.

⛔ A spec whose class cannot be determined — unreadable, or carrying no
`## Expected Surface` section — **halts the run with the spec named** rather than
defaulting to a class.

## Workflow

### Step 1: Classify the corpus

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-epic-surface-partition:epic-surface-partition \
  classify --epic test-quality
```

### Step 2: Route on the TOON status

| `status` | `error` | Action |
|----------|---------|--------|
| `success` | — | Consume `specs[]`, `claimed[]`, `excluded[]` and `unresolved[]` |
| `error` | `unclassifiable_spec` | The run halted; the offending spec is in `spec`, the cause in `reason` |
| `error` | `epic_corpus_not_found` | No `plans/` directory under the named epic |
| `error` | `invalid_epic_slug` | The slug carries a path separator or traversal component |

## Output Contract

```toon
status: success
epic: test-quality
plans_dir: /abs/path/to/orchestrator/test-quality/plans
repo_root: /abs/path/to/checkout
specs_total: 21
class_tally[3]{spec_class,count}:
  declarative,19
  derived,1
  prose,1
specs[21]{plan_id,spec,spec_class,claimed_count,excluded_count,unresolved_count,evidence}:
  ...
claimed[N]{plan_id,path,kind}:
  ...
excluded[N]{plan_id,path,kind}:
  ...
unresolved[N]{plan_id,raw}:
  ...
```

`kind` is one of `directory`, `recursive_glob`, `filename_glob`, `file`.
`unresolved[]` carries every entry the parser recognised as a path but could not
anchor — a first-class result, not a silent drop.

Every class carries a `class_tally` row even at zero, so an empty class reads as
measured rather than as absent.

## Entry Shapes Resolved

| Shape | Example |
|-------|---------|
| Directory | `test/plan-marshall/manage-config/` |
| Recursive glob | `test/pm-plugin-development/**` |
| Filename glob | `plugin-doctor/test_test_conventions_rule*.py` |
| Named file | `test/test_runner_falsifiability.py` |
| Non-`test/` path | `pyproject.toml` |
| Relative continuation | `.../workflow-integration-github/`, or a bare sibling written after a rooted path in the same bullet |
| Exclusion | an entry after `excluding`, a bullet opening with `no`, or any entry under `## Out of Scope` |

`OBSERVED:` / `HYPOTHESIS:` label prefixes, `⛔` / `⚠️` markers, `**bold**` spans
and trailing em-dash commentary are tolerated and stripped.

## Related

- `plan-marshall:plan-orchestrator` — owns the epic ledger and the `corpus cross-check` collision matrix this skill deliberately does not re-derive
- `pm-plugin-development:plugin-doctor` — its `test-conventions` sweep is a read-only input, never edited here

## Canonical invocations

The canonical argparse surface for the single entry-point script this skill
registers: `epic-surface-partition.py`. The plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for the
`manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs
xref this section by name instead of restating the command inline. See
[`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../plugin-script-architecture/standards/cross-skill-integration.md)
§ "Script invocation in documentation".

### classify

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-epic-surface-partition:epic-surface-partition \
  classify --epic EPIC
```
