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
rediscovers by hand, and keeps *"unclaimed"*, *"crossed only by a plan that
declared itself a sweep"* and *"named only where the derivation cannot resolve
it"* as separate verdicts that are never merged.

The corpus is enumerated by glob, so a spec added to the epic is picked up with
no edit to any script.

## When to Use This Skill

Activate when you need to:
- Classify every spec's `## Expected Surface` before relying on the partition
- Find `test/` entries that no plan claims, or that two plans claim
- Size a campaign run from the budget findings grouped by owning plan

## The Model

The derivation's model tables — the spec classes `classify` assigns, the entry
kinds and the entry shapes the parser resolves, the verdicts `partition` assigns,
the attribution buckets, and the report's sections — are stated exactly once, in
[standards/epic-surface-derivation.md](standards/epic-surface-derivation.md).
None is restated here, because a second copy of a table is what lets the two
statements drift apart.

These invariants govern how a caller reads the result:

⛔ A spec whose class cannot be determined — unreadable, or carrying no
`## Expected Surface` section — **halts the run with the spec named** rather than
defaulting to a class.

⛔ `unclaimed`, `swept` and `not_derivable` are **never merged**. Merging them
would report a deliberate crossing or a limit of the derivation as a partition
defect, manufacturing a disagreement the corpus does not contain.

⛔ A **root span** — bare `test/`, or `test/**` — names every module and so
discriminates nothing. Root spans are excluded from claim matching and reported
in `root_claims[]`, so a dropped root span is **stated rather than silently
dropped**. A plan whose only claim is a root span therefore receives no module.
Breadth alone never exempts a plan from ownership: a wide claim still competes,
and only a plan whose spec DECLARES ITSELF a whole-partition sweep stops counting
as a competing owner — its crossings are then reported beside the verdict rather
than folded into the attribution.

## Workflow

### Step 1: Classify the corpus

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-epic-surface-partition:epic-surface-partition \
  classify --epic test-quality
```

### Step 1b: Derive the partition and the attribution

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-epic-surface-partition:epic-surface-partition \
  partition --epic test-quality
```

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-epic-surface-partition:epic-surface-partition \
  attribution --epic test-quality
```

`attribution` re-derives the over-budget modules from the **current** tree; a
published baseline is only ever a post-hoc comparison, never an input. A module
one slice claims is attributed to that slice however many sweeps also cross it;
modules with no single owning slice land in the explicit ownerless buckets rather
than being folded into any plan's total, so every file is attributed exactly
once. The bucket set is stated in
[standards/epic-surface-derivation.md](standards/epic-surface-derivation.md).

### Step 1c: Render the report

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-epic-surface-partition:epic-surface-partition \
  report --epic test-quality
```

Every rendered section carries the command that produced it. The set and its
order are stated once, in the report-sections table of
[standards/epic-surface-derivation.md](standards/epic-surface-derivation.md), and
are deliberately not enumerated here — an enumeration in two places is what goes
stale the next time a section is added. `report` exits 0 even when it renders
disagreements: a rendered disagreement is the product, not a failure.

### Step 2: Route on the TOON status

| `status` | `error` | Action |
|----------|---------|--------|
| `success` | — | Consume the payload of the subcommand that was invoked — the four shapes differ, see [Output Contract](#output-contract) |
| `error` | `unclassifiable_spec` | The run halted; the offending spec is in `spec`, the cause in `reason` |
| `error` | `epic_corpus_not_found` | No `plans/` directory under the named epic |
| `error` | `invalid_epic_slug` | The slug carries a path separator or traversal component |

All four subcommands share those three error shapes; only the `success` payload
is subcommand-specific.

## Output Contract

Every payload — success and error alike — carries `status` and `epic`. Those two
are the only keys common to all four emitted shapes.

A **success** payload additionally carries `plans_dir` and the keys of the
subcommand that produced it, documented per subcommand below. An **error**
payload instead carries `error` plus the keys that error names: `reason` for
`invalid_epic_slug` and `unclassifiable_spec` (the latter also naming the
offending `spec`), and `plans_dir` for `epic_corpus_not_found`.

⛔ Do not read `plans_dir` off an error payload unconditionally. Only
`epic_corpus_not_found` carries it, because only that error resolved a directory
before failing; an `invalid_epic_slug` never resolved one, so it emits no
`plans_dir` and a caller assuming otherwise raises `KeyError`.

### `classify`

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
sweep_plans[N]:
  ...
specs[21]{plan_id,spec,spec_class,is_sweep,claimed_count,excluded_count,unresolved_count,evidence}:
  ...
claimed[N]{plan_id,path,kind,shape}:
  ...
excluded[N]{plan_id,path,kind,shape}:
  ...
unresolved[N]{plan_id,raw}:
  ...
```

`kind` is one of `directory`, `recursive_glob`, `filename_glob`, `file`, and
`shape` is `claim` or `lead`. `unresolved[]` carries every entry the parser
recognised as a path but could not anchor — a first-class result, not a silent
drop.

`sweep_plans[]` names the plans whose specs declare themselves whole-partition
sweeps, and `is_sweep` is that verdict projected onto each spec row. Both are
emitted even when no spec declares one, so "no sweep" reads as measured.

Every class carries a `class_tally` row even at zero, so an empty class reads as
measured rather than as absent.

### `partition`

```toon
status: success
epic: test-quality
plans_dir: /abs/path/to/orchestrator/test-quality/plans
test_root: /abs/path/to/checkout/test
modules_total: 214
verdict_tally[N]{verdict,count}:
  ...
sweep_plans[N]:
  ...
root_claims[N]{plan_id,path}:
  ...
contested[N]{path,plans}:
  ...
sweep_crossings[N]{path,verdict,sweeps}:
  ...
modules[214]{path,verdict,plans,sweeps}:
  ...
```

`plans` is a comma-joined list of the SLICE plans the verdict rests on — empty
for `unclaimed` and `swept`, one id for `claimed`, several for `contested`.
`sweeps` is the separate, comma-joined list of self-declared sweep plans that
also cross the module: a crossing is reported beside the verdict, never as
competing ownership. `contested` and `sweep_crossings` isolate the two
populations a caller reads for different reasons, and `verdict_tally` carries a
row for every verdict even at zero. `root_claims[]` carries every span excluded
from claim matching by the root-span rule above; it too is emitted even when
empty, so an absent root claim reads as measured.

### `attribution`

```toon
status: success
epic: test-quality
plans_dir: /abs/path/to/orchestrator/test-quality/plans
test_root: /abs/path/to/checkout/test
budget: 400
modules_total: 214
findings_total: 12
sweep_plans[N]:
  ...
contested[N]{path,plans}:
  ...
sweep_crossings[N]{path,verdict,sweeps}:
  ...
buckets[N]{owner,count}:
  ...
findings[12]{owner,path,line_count}:
  ...
```

`owner` is a plan id, or one of the ownerless buckets the derivation standard
names, so every over-budget module is attributed exactly once and none is folded
into a plan's total. `contested` and `sweep_crossings` carry the same two
populations `partition` emits, so the disagreement behind a bucket can be read
without a second call.

### `report`

```toon
status: success
epic: test-quality
plans_dir: /abs/path/to/orchestrator/test-quality/plans
test_root: /abs/path/to/checkout/test
report_only: true
gates_build: false
sections[N]{section,command,summary}:
  ...
partition_tally[N]{verdict,count}:
  ...
attribution_buckets[N]{owner,count}:
  ...
disagreements[N]{path,verdict,plans}:
  ...
sweep_plans[N]:
  ...
contested[N]{path,plans}:
  ...
sweep_crossings[N]{path,verdict,sweeps}:
  ...
baseline_drift{baseline_supplied,baseline_count,observed_count,added_count,removed_count}:
  ...
baseline_drift_instances[N]{path,drift}:
  ...
not_derivable_modules[N]{path,plans}:
  ...
not_derivable_specs[N]{plan_id,spec,spec_class,unresolved_count}:
  ...
injected_controls[N]{control,expectation,demonstrated_by}:
  ...
test_count{before,after,method}:
  ...
provenance{overlap_live,overlap_count}:
  ...
provenance_placement[N]{claim,value,citation}:
  ...
provenance_overlaps[N]{plan_id,path}:
  ...
root_claims[N]{plan_id,path}:
  ...
```

`gates_build: false` is asserted in the payload rather than only in prose: this
subcommand renders disagreements and still exits 0. `sections[]` carries every
section the derivation standard's report-sections table names, in that order,
each with the command that reproduces it.

⛔ Read `baseline_drift.baseline_supplied` before either drift count. With no
`--baseline-findings` the run compared nothing, and `added_count: 0` there means
"nothing was compared" rather than "nothing drifted". Drift is reported per
instance in `baseline_drift_instances[]` and never changes the exit status.

## Standards

| Standard | Contents |
|----------|----------|
| [standards/epic-surface-derivation.md](standards/epic-surface-derivation.md) | Where the parse lives (`plan-marshall:script-shared`) and why this skill owns the partition rather than the parse, the split the entry-shape rules run along, the three-class model and its evidence rules, the entry kinds and the claim-or-lead shape with its marker rules, the partition verdicts, sweep plans and why `unclaimed`, `swept` and `not_derivable` stay separate, the attribution buckets, the report's sections and what `provenance` must assert, and the never-a-gate contract |

## Related

- `plan-marshall:script-shared` — **owns the `## Expected Surface` parse.** Its `epic_spec_parser` is the marketplace's single reader of that section, and this skill consumes it as stage 1 rather than holding a copy. This skill owns the PARTITION; the parse lives there because the orchestrator's disjointness gate reads the same section, and two readers of one grammar is the defect that split them
- `plan-marshall:plan-orchestrator` — owns the epic ledger and the `corpus cross-check` collision matrix this skill deliberately does not re-derive. Its `corpus surfaces` verb is a sibling CONSUMER of the same shared reader, never a second one
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

### partition

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-epic-surface-partition:epic-surface-partition \
  partition --epic EPIC
```

### attribution

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-epic-surface-partition:epic-surface-partition \
  attribution --epic EPIC [--budget BUDGET]
```

### report

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-epic-surface-partition:epic-surface-partition \
  report --epic EPIC [--budget BUDGET] [--tests-before TESTS_BEFORE] \
  [--baseline-findings BASELINE_FINDINGS]
```
