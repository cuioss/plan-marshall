---
lane:
  class: core
  cost_size: XS
name: default:finalize-step-preference-emitter
description: Per-plan preference-learning sweep — generalizes recurring user gate-dispositions in the just-finished plan into owed durable architecture hints via the shared disposition-to-hint contract
order: 992
default_on: true
presets: []
mutates_source: false
post_run_review: true
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
threshold-gates them via the `preference_min_recurrence` config knob, and names
the cleared patterns as owed `architecture enrich` hints — the SAME sink the
meta-only cross-plan auditor uses, with no new store. Because the step is
`post_run_review: true` and runs after the merge gate, it files those hints as a
follow-up artifact rather than writing them (see Step 4). This is the cheap
per-plan path that ships to consumer projects via the standard finalize-step
discovery mechanism; the richer corpus-wide path is the meta-only
`audit-archived-plan-retrospectives` auditor (Step 4c).

Domain-agnostic by construction — it reads dispositions through `manage-findings`
and generalizes them through the shared disposition-to-hint contract, with no
language- or bundle-specific logic.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code
contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This step is **non-fatal**: a failure to read dispositions or to file the owed-hint
artifact never blocks finalize (see Error Handling). The exit-code contract above
applies to the diagnostic reads; the artifact-filing step degrades gracefully
instead.

This document carries NO step-activation logic. Activation is controlled by the
dispatcher in `phase-6-finalize/SKILL.md` Step 3, driven solely by presence of
`finalize-step-preference-emitter` in `manifest.phase_6.steps` (bare name — the
dispatcher prepends `default:` when looking up the dispatch-table row).

## Inputs

- `--plan-id` — plan identifier (required).
- `--iteration` — finalize iteration counter (accepted for contract compliance).
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0).

**Orchestration context (resolved once by the dispatcher, never re-derived here)**: this step
emits lesson-shaped output, so it consumes the same once-per-run orchestration verdict
`lessons-capture` and `plan-retrospective` Step 5b consume. The dispatcher resolves it at
`phase-6-finalize/SKILL.md` Step 3 item 4b.a0 (`manage-plan-documents request read --section
source_id`, then `orchestrator inbox detect`) and still holds it when this inline step runs at
`order: 992`, after `lessons-capture` at `991`.

- `orchestrated` — bool; `true` when this plan was launched from an epic's staged plan spec. This step MUST NOT re-issue either resolution call.
- `epic` — string; the epic slug when `orchestrated` is `true`, the empty string otherwise. Same must-not-recompute obligation.

## Ordering rationale

This step is `post_run_review: true`: its output is a derived assessment of the
just-finished run (P1), and the dispositions it generalizes include those triaged
at the merge gate's re-review barrier, which are only determined at or after
`branch-cleanup` (P2). `order: 992` therefore places it AFTER that merge gate,
and — preserving the dependency the settle-band placement encoded — AFTER
`lessons-capture` (991), so the plan's finding dispositions are settled before
they are read. It still runs BEFORE `record-metrics` (998) and `archive-plan`
(1000) — the latter moves the plan directory out from under the
`manage-findings` read — so the plan's findings remain readable in place when it
runs. The governing constraint is
[source-edit-pushability.md](source-edit-pushability.md), cross-referenced here
rather than restated.

An early (`order: < 10`) slot is explicitly REJECTED for the same reason it
always was: that early there is nothing to promote, because the finding
dispositions this step reads do not yet exist at the start of finalize.

### Why the post-merge move does not revert `#990`

`#990` moved this step from `order: 80` to the pre-merge settle band, and that
placement was **correct for a source-mutating step**: the step then wrote tracked
source (the per-module `enriched.json` under `.plan/project-architecture/`, via
`architecture enrich`), and a post-merge write of tracked source lands as an
uncommitted diff on `main` that can never ride the plan's own PR. Read the
renumber to 992 as a package with the `mutates_source: false` flip below, never
as a bare relocation: the source mutation is REMOVED, not relocated. With no
source write left, the failure mode `#990` closed cannot recur — the owed
enrichment is named in an explicit follow-up artifact instead of landing dirty on
`main`. A future change that reintroduces an in-worktree `architecture enrich`
call here without also moving the step back before the merge gate would
reproduce `#990`'s defect exactly.

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
return — no artifact filed, no error.

### Step 4: Generalize the cleared patterns and file the owed hints

For each cleared tuple, generalize the disposition recurrence into a hint string
following the shared contract in
[`disposition-to-hint-routing.md`](disposition-to-hint-routing.md) for the
generalization rule, the intended routing targets
(`architecture enrich best-practice --module {module}` for module-attributed
patterns, `architecture enrich insight --module default` for cross-cutting
patterns), and the "generalize, do not log raw dispositions" privacy invariant.
This step MUST NOT restate those rules inline — the shared contract is the single
source of truth (the meta-only cross-plan auditor's Step 4c references the same
contract).

**Do NOT call `architecture enrich` from this step.** It is `post_run_review: true`
and runs after the merge gate, where the enrich write would put tracked source
(`.plan/project-architecture/{module}/enriched.json`) on `main` as an uncommitted
diff — the `#990` defect described in the Ordering rationale above. Take the
discover-after-merge route in
[source-edit-pushability.md](source-edit-pushability.md) § "The discover-after-merge
rule" instead: name every owed hint in an explicit follow-up record so the enrichment is
scheduled and visible rather than lost. WHERE that record is filed is decided by the
orchestration branch below.

#### Orchestration branch (evaluate FIRST)

Branch on the `orchestrated` runtime input before filing anything. The branch decides the
DESTINATION of the owed-hint record only — the generalization above and the
`architecture enrich` prohibition are common to both branches.

- **`orchestrated: false`** — unchanged: the record goes to the global lessons store via the
  canonical `manage-lessons` three-step path-allocate flow. Continue at "Non-orchestrated
  filing" below.
- **`orchestrated: true`** — make **zero** `manage-lessons add` calls. The record belongs to
  the epic that launched this plan, not to the global corpus: route it to the epic's `inbox/`
  OUTBOX instead, exactly as `lessons-capture` and `plan-retrospective` Step 5b do at their own
  write-sites. Follow the emission contract immediately below and skip the non-orchestrated
  filing entirely.

##### Orchestrated emission contract

Message granularity is **one message per emitted item**, per
[`../../marshall-orchestrator/standards/inbox-envelope.md`](../../marshall-orchestrator/standards/inbox-envelope.md):
emit **one `kind: candidate-lesson` message per owed hint**. The payload is lesson-shaped —
the same `key=value` header plus markdown body the lessons corpus uses — so the
orchestrator-side pickup lifts it with zero transcoding. The plan performs **no**
global-vs-epic classification; only the orchestrator holds the cross-plan context that
judgement needs.

Each payload MUST name the same three facts the non-orchestrated body names, so the owed
`architecture enrich` call stays reconstructible without re-deriving the pattern from
dispositions `archive-plan` is about to move: the target `--module`, the enrich verb the
shared contract selects for that pattern (`best-practice` or `insight`), and the verbatim
generalized hint text.

For each message, stage the payload body with the `Write` tool first, then write it:

```text
Write {plan_dir}/work/inbox-payload.md
```

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator inbox write \
  --slug {epic} --sender-type plan --sender-id {plan_id} --kind candidate-lesson \
  --payload-file {plan_dir}/work/inbox-payload.md
```

Staging the body with `Write` first is the same shell-safety reason the lesson three-step flow
exists — inline `python -c`, `$(printf …)`, and `#`-bearing heredocs are prohibited for inbox
payload bodies exactly as they are for lesson bodies. The envelope schema, the `kind` enum, and
the header-field table live in the standard cross-referenced above; do not restate them here.

This branch emits NO `kind: landing` message. The one landing an orchestrated finalize run
owes its epic is `lessons-capture`'s, emitted unconditionally there; a second one from here
would put two landings on one run.

This branch writes only under `.plan/`, so the step's `mutates_source: false` fact is unchanged
and the step never reaches the dispatcher's commit instrumentation at all — item 5f reads the
declared `mutates_source` fact first and skips (a)-(d). The declaration is not trusted blind:
this step also declares `post_run_review: true`, so item 5f's sub-item (0) observes the worktree
on return and reports any dirty TRACKED path outside `.plan/` as a non-blocking WARNING.

##### Non-orchestrated filing (`orchestrated: false`)

File ONE follow-up artifact naming every owed hint, via the canonical `manage-lessons`
three-step path-allocate flow (see
[`../workflow/lessons-capture.md`](../workflow/lessons-capture.md) § "Gate 3 — Create"
for the flow; do not restate it here):

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:phase-6-finalize" --category improvement \
  --title "Owed architecture hints: preference-emitter, plan {plan_id}"
```

Write the body with the `Write` tool, then apply it with `manage-lessons set-body
--lesson-id {id} --file {path}`. The body MUST name, per owed hint: the target
`--module`, the enrich verb the shared contract selects for that pattern
(`best-practice` or `insight`), and the verbatim generalized hint text — so the
owed `architecture enrich` call is reconstructible without re-deriving the pattern
from dispositions that `archive-plan` is about to move.

The pairing with `lessons-capture` is deliberate and symmetric: both steps owe hints to
the same `architecture enrich` sink without writing it, both are `post_run_review: true`, both take this same
discover-after-merge route, and both branch on `orchestrated` to decide whether the record
lands in the global corpus or in the epic's inbox. Changing one without the other leaves the
pair half-resolved.

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
| Filing the owed-hint record fails — either the `manage-lessons` artifact (`orchestrated: false`) or an `orchestrator inbox write` (`orchestrated: true`) | Non-fatal: log the failure and mark `done` — a failed owed-hint write never blocks finalize |

## Related

- [disposition-to-hint-routing.md](disposition-to-hint-routing.md) — the shared generalization + routing + privacy contract this step consumes (single source of truth)
- [finalize-step-simplify.md](finalize-step-simplify.md) — the built-in finalize-step exemplar this step is modeled on (frontmatter, configurable block, mark-step-done tail)
- [../../../../../../.claude/skills/audit-archived-plan-retrospectives/checks/preference-pattern-detector.md](../../../../../../.claude/skills/audit-archived-plan-retrospectives/checks/preference-pattern-detector.md) — the richer meta-only cross-plan preference path sharing the same contract and sink
