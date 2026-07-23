---
lane:
  class: core
  cost_size: XS
name: default:finalize-step-preference-emitter
description: Per-plan preference-learning sweep — promotes recurring user gate-dispositions in the just-finished plan to durable architecture hints via the shared disposition-to-hint contract
order: 61
default_on: true
presets: []
mutates_source: true
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
configurable:
  - key: preference_min_recurrence
    default: 2
    description: Within-plan disposition recurrence count that promotes a (module, finding-class, disposition) pattern to an architecture hint. A pattern must recur at least this many times in the just-finished plan to be promoted.
---

# Finalize Step: preference-emitter

Consumer-available per-plan preference-learning pass for the
`default:finalize-step-preference-emitter` finalize step. It reads the
just-finished plan's finding dispositions, aggregates
`(module, finding-class, disposition)` recurrences WITHIN this single plan,
threshold-gates them via the `preference_min_recurrence` config knob, and routes
the promoted patterns to `architecture enrich` — the SAME sink the meta-only
cross-plan auditor uses, with no new store. This is the cheap per-plan path that
ships to consumer projects via the standard finalize-step discovery mechanism;
the richer corpus-wide path is the meta-only `audit-archived-plan-retrospectives`
auditor (Step 4c).

Domain-agnostic by construction — it reads dispositions through `manage-findings`
and routes through `architecture enrich`, with no language- or bundle-specific
logic.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code
contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This step is **non-fatal**: a failure to read dispositions or to enrich never
blocks finalize (see Error Handling). The exit-code contract above applies to the
diagnostic reads; the enrich routing step degrades gracefully instead.

This document carries NO step-activation logic. Activation is controlled by the
dispatcher in `phase-6-finalize/SKILL.md` Step 3, driven solely by presence of
`finalize-step-preference-emitter` in `manifest.phase_6.steps` (bare name — the
dispatcher prepends `default:` when looking up the dispatch-table row).

## Inputs

- `--plan-id` — plan identifier (required).
- `--iteration` — finalize iteration counter (accepted for contract compliance).
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0).

## Ordering rationale

`order: 61` places this step in the **settle band**: AFTER `lessons-capture`
(order 60), so the plan's finding dispositions are settled before they are read,
and BEFORE the merge gate `branch-cleanup` (order 70). The placement is
load-bearing: this step promotes recurring dispositions into `architecture enrich`
hints, which mutate tracked source, so it MUST run while the feature branch is
still open — before the branch is squash-merged, after which the edit can no
longer ride the PR. The step declares `mutates_source: true` accordingly; the
governing constraint is
[source-edit-pushability.md](source-edit-pushability.md) (the pre-merge
source-edit pushability contract), cross-referenced here rather than restated.

An `order: < 10` slot is explicitly REJECTED: that early there is nothing to
promote, because the finding dispositions this step reads and generalizes do not
yet exist at the start of finalize — they are only settled once `lessons-capture`
(60) has run. The step is therefore floored at the settle band, not hoisted to
the front of the pipeline. It still runs WELL BEFORE `record-metrics` (998) and
`archive-plan` (1000) — the latter moves the plan directory out from under the
`manage-findings` read — so the plan's findings remain readable in place when it
runs.

## Workflow

### Step 1: Read the just-finished plan's dispositions

Read the plan's finding dispositions for each of the three user-gate
dispositions, one `manage-findings list` call per disposition:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --resolution suppressed
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --resolution accepted
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --resolution taken_into_account
```

Aggregate the returned findings into `(module, finding-class, disposition)`
recurrences within this single plan: the disposition is the queried
`--resolution` value, the finding-class is the finding's `title`/`type`
collapsed at the first `:` and lowercased, and the module is the finding's
`module` attribution (falling back to `component`, then `default`). Count how
many times each tuple recurs within the plan.

### Step 2: Read the per-plan promotion threshold knob

Read the live `preference_min_recurrence` knob value exactly as
`finalize-step-simplify` reads its `simplify` gate:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize step get --step-id default:finalize-step-preference-emitter
```

Read `params.preference_min_recurrence` from the returned TOON (default `2`).

### Step 3: Threshold-gate and skip-clean

Keep only the tuples whose within-plan recurrence count is at least
`preference_min_recurrence`. When NO tuple clears the threshold (the common
case), skip-clean: mark the step done with a `no patterns promoted` detail and
return — no enrich call, no error.

### Step 4: Generalize and route the cleared patterns

For each cleared tuple, generalize the disposition recurrence into a hint string
and route it to `architecture enrich`, following the shared contract in
[`disposition-to-hint-routing.md`](disposition-to-hint-routing.md) for the
generalization rule, the routing targets
(`architecture enrich best-practice --module {module}` for module-attributed
patterns, `architecture enrich insight --module default` for cross-cutting
patterns), and the "generalize, do not log raw dispositions" privacy invariant.
This step MUST NOT restate those rules inline — the shared contract is the single
source of truth (the meta-only cross-plan auditor's Step 4c references the same
contract).

### Step 5: Mark step done

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-preference-emitter \
  --outcome done \
  --display-detail "Preference-emitter: {N} patterns promoted, {M} skipped"
```

The `display_detail` string appears in the renderer's per-step `[OK]` row.

## Activation note

The step is **default-active** — its frontmatter declares `default_on: true`
(like `finalize-step-simplify`), so the discovery query
(`extension_discovery.find_implementors`) includes it in the default-on seed and
a fresh consumer `marshal.json` picks it up without manual addition. It is cheap (one `manage-findings list` per
disposition plus a bounded generalization, gated by the threshold so it usually
no-ops) and skip-clean when the plan has zero promotable dispositions.

## Error Handling

| Scenario | Action |
|----------|--------|
| No dispositions found / nothing clears the threshold | Mark `done` with `display_detail "Preference-emitter: no patterns promoted"` — skip-clean, never an error |
| `manage-findings list` returns an error | Mark `done` with the read failure noted in `display_detail`; learning must NEVER block finalize |
| `architecture enrich` fails for a pattern | Non-fatal: log the failure, continue with the remaining patterns, and mark `done` — a failed enrich never blocks finalize |

## Related

- [disposition-to-hint-routing.md](disposition-to-hint-routing.md) — the shared generalization + routing + privacy contract this step consumes (single source of truth)
- [finalize-step-simplify.md](finalize-step-simplify.md) — the built-in finalize-step exemplar this step is modeled on (frontmatter, configurable block, mark-step-done tail)
- [../../../../../../.claude/skills/audit-archived-plan-retrospectives/checks/preference-pattern-detector.md](../../../../../../.claude/skills/audit-archived-plan-retrospectives/checks/preference-pattern-detector.md) — the richer meta-only cross-plan preference path sharing the same contract and sink
