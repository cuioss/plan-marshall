---
lane:
  class: core
  cost_size: XS
name: default:emit-landing
description: Terminal machine-readable emission — assembles the run's facts into one kind:landing inbox message for the epic to drain, in the reserved terminal-emission band after every reporting step and before the archive move
order: 1000
default_on: true
presets:
  - local
  - standard
  - full
mutates_source: false
post_run_review: true
reads:
  - metrics
records_facts:
  - work_performed
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step: emit-landing

The terminal machine-readable emission. It assembles the run's facts — every finalize step's outcome and
typed facts, the deliverables, the PR reference, the token totals — into ONE `kind: landing` inbox
message the governing epic drains, and it is the LAST thing that happens before `archive-plan` moves the
plan directory. The payload it produces is specified by
[`../../plan-orchestrator/standards/landing-payload-spec.md`](../../plan-orchestrator/standards/landing-payload-spec.md);
this document is the producer, that document is the contract, and the drain-completeness check
(`_orchestrator_inbox.check_landing_completeness`) is the validator — the three share one spec.

**Why a dedicated terminal step, separate from `lessons-capture`.** The landing was historically emitted
inside `lessons-capture` at `order: 991` — before the run's own token totals (`record-metrics`, 998) and
the archive path exist, so the emission could not carry facts produced after it. This step occupies the
reserved terminal-emission band (`1000–1099`, see
[`../../extension-api/standards/finalize-step-order-bands.md`](../../extension-api/standards/finalize-step-order-bands.md))
so it runs AFTER every reporting step and can carry their facts. `lessons-capture` keeps its
candidate-lesson emission; only the landing moved here. Relocating a whole step past what it needed is
how the read-direction defect this epic tracks was created, so the two were separated deliberately.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step
explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr
  verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of
  `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This step is **non-fatal**: a failure to read a fact or to write the landing never blocks archive (see
Error Handling) — but the emission is unconditional when the step runs, so a read failure degrades a
FIELD, never the whole message.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in
`phase-6-finalize/SKILL.md` Step 3, driven solely by presence of `emit-landing` in
`manifest.phase_6.steps` (bare name — the dispatcher prepends `default:` when looking up the
dispatch-table row).

## The step exists only under an orchestrator

This step's WHOLE reason to exist is to write to an epic's inbox, and a non-orchestrated plan has no epic
inbox to write to. So it is composed **OUT** of a non-orchestrated plan at COMPOSE time — an observable
compose-time decision (a `[STATUS]` decision-log line naming the drop), never a silent runtime no-op that
leaves a dead step in the manifest. The compose gate is
`manage-execution-manifest`'s `_apply_terminal_emission_orchestration_gate`, which reads the plan's
`request.md` `source_id` and classifies it through the single sanctioned detector
(`_orchestrator_inbox.classify_source_id`) — no second detector, no new persisted field.

**Consequence for this body: when this step RUNS, the plan IS orchestrated by construction**, so it does
not re-resolve orchestration and it emits unconditionally. The `orchestrated` / `epic` runtime inputs
below are the dispatcher's already-resolved verdict, carried in so the body never re-issues the detection.

## Inputs

- `--plan-id` — plan identifier (required).
- `--iteration` — finalize iteration counter (accepted for contract compliance).
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0).

**Orchestration context (resolved once by the dispatcher, never re-derived here)**: this step writes to
the epic inbox, so it consumes the same once-per-run orchestration verdict `lessons-capture`,
`plan-retrospective`, and `finalize-step-preference-emitter` consume. The dispatcher resolves it at
`phase-6-finalize/SKILL.md` Step 3 item 4b.a0 (`manage-plan-documents request read --section source_id`,
then `orchestrator inbox detect`) and still holds it when this inline step runs at `order: 1000`, after
`lessons-capture` (991) and `record-metrics` (998).

- `orchestrated` — bool; `true` by construction when this step runs (see above). This step MUST NOT
  re-issue either resolution call.
- `epic` — string; the epic slug the landing is addressed to. Same must-not-recompute obligation.

## Ordering rationale

`order: 1000` is the reserved terminal-emission band's first slot. This step is `post_run_review: true`:
its output is a derived record of the just-finished run (P1), and the facts it carries include the merge
outcome and the token totals, which are only determined at or after the merge gate `branch-cleanup` (70)
and `record-metrics` (998) respectively (P2). It therefore MUST run after those, and `1000` places it
after every reporting step. It runs BEFORE `archive-plan` (1100), which `destroys: [plan-directory]` — so
`manage-status`, `manage-solution-outline`, and `manage-execution-manifest` reads still resolve in place
when this step runs. `1001–1099` stays reserved for a future co-terminal step; this step does not consume
the whole band.

## Workflow

### Step 0: Defensive orchestration guard

The compose gate guarantees this step is absent from a non-orchestrated plan, so reaching this body proves
the plan is orchestrated. As a fail-closed diagnostic against a mis-configured plan that hand-registered
this step without being orchestrated, check the `epic` input: when `epic` is empty (or `orchestrated` is
false), do NOT write a landing to nowhere — record a diagnosable skip and a WARNING naming the
misconfiguration, then return:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[VERIFY] (plan-marshall:phase-6-finalize:emit-landing) present in a non-orchestrated plan (empty epic) - the compose-time orchestration gate should have dropped it; emitting no landing"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step emit-landing --outcome skipped \
  --display-detail "not orchestrated, no landing emitted"
```

This is a diagnosable skip (it names why), NOT a silent no-op — the compose gate remains the sanctioned
decision, and this guard only makes a compose-gate escape visible instead of writing a malformed message.

### Step 1: Read the run's facts

Read each fact from its authoritative source. Every read is on the LIVE plan directory (archive has not
run yet). A read that fails degrades its field to `n/a` (Error Handling), never the whole message.

1. **Per-step outcomes and typed facts** — the phase-6 step records:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
     --plan-id {plan_id}
   ```

   Read `metadata.phase_steps["6-finalize"]` — a dict of `{step_name: {outcome, display_detail, facts}}`.
   The `facts` sub-dict is the typed per-step facts each step recorded via `mark-step-done --fact`
   (`branch-cleanup`'s `merge_mechanism` / `action`, `record-metrics`'s `total_tokens` /
   `total_wall_seconds`, `sonar-roundtrip`'s scan facts, and so on). These are transcribed into the
   payload as-is — do NOT re-narrate them into prose.

2. **Composed step order** — the order the manifest declares, so the landing carries the composed order
   rather than a re-narrated one:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest read \
     --plan-id {plan_id}
   ```

   Read `phase_6.steps` (bare step IDs, composed order).

3. **Deliverables** — count and completion from the solution outline:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline read \
     --plan-id {plan_id}
   ```

4. **PR reference and merge state** — the STEP's own recorded claim, never a corroboration (see the
   payload spec's finding #4: a contradiction of a step's merge claim is operator narrative, not a fact
   this step fabricates). Both are **typed facts**, read from the `facts` sub-dict of the step records
   in item 1 — do NOT re-parse either out of a `display_detail` string:

   - `pr` ← `create-pr`'s `pr_number` fact, rendered as `#{pr_number}`.
   - `merge_state` ← `branch-cleanup`'s `merge_state` fact, transcribed verbatim
     (`merged` / `open` / `n/a`).

   A fact absent because its step did not run (the manifest excluded it, or it has no record) is
   written as `n/a`, its key still present, per the Error Handling table.

### Step 2: Assemble the machine-readable landing payload

Stage the payload body with the `Write` tool. The body is: an optional one-line narrative headline, the
required `landing-facts` fenced block, and an optional `## Residue` section for the narrative-only class.

```text
Write {plan_dir}/work/inbox-payload.md
```

The body has three parts, in order:

1. **An optional one-line narrative headline** under a `## What landed` heading — e.g. `{plan_id} shipped as {pr} ({merge_state}).`
2. **The required `landing-facts` fenced block** — it MUST open with a ` landing-facts ` info-string fence and close with a bare fence, and MUST carry every required key from the payload spec — `schema=landing-facts/1`, `plan_id`, `pr`, `merge_state`, `deliverables_total`, `deliverables_done`, `total_tokens`, and `steps` (comma-joined `{step}:{outcome}` in composed order). A value that could not be read is written as `n/a` (its key still present). Optional keys (`epic`, `total_wall_seconds`, per-step `step.{name}.{fact}=…`) MAY follow. The block's contents are `key=value` lines:

```landing-facts
schema=landing-facts/1
plan_id={plan_id}
epic={epic}
pr={pr}
merge_state={merge_state}
deliverables_total={N}
deliverables_done={M}
total_tokens={tokens}
total_wall_seconds={seconds}
steps={step1}:{outcome1},{step2}:{outcome2},...
```

3. **An optional `## Residue` section** — narrative-only items the epic should track that no step recorded as a fact (a contradicted merge claim, a review-bot withdrawal, a producer-gap the run could not mechanise). Omit the section when there is none.

The `## Residue` section is prose by design and is NOT validated by the completeness check — it is where
the irreducibly-narrative half of the delta rides. Do NOT put a required fact there; required facts belong
in the fenced block. The anti-pattern list for payload bodies (inline `python -c`, shell command
substitution, `#`-bearing heredocs) applies here exactly as it does for lesson bodies — the `Write`-first
staging is the shell-safety reason it exists.

### Step 3: Write the landing message

Exactly ONE `kind: landing` message per orchestrated finalize run:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox write \
  --slug {epic} --sender-type plan --sender-id {plan_id} --kind landing \
  --payload-file {plan_dir}/work/inbox-payload.md
```

The envelope schema, the `kind` enum, and the header-field table are owned by
[`../../plan-orchestrator/standards/inbox-envelope.md`](../../plan-orchestrator/standards/inbox-envelope.md)
and the payload body by
[`../../plan-orchestrator/standards/landing-payload-spec.md`](../../plan-orchestrator/standards/landing-payload-spec.md);
do not restate them here.

This step writes only under `.plan/`, matching its `mutates_source: false` fact, so it never reaches the
dispatcher's commit instrumentation (item 5f skips (a)-(d) on the declared fact). Because it also declares
`post_run_review: true`, item 5f's sub-item (0) observes the MAIN CHECKOUT on return and reports any dirty
TRACKED path outside `.plan/` as a non-blocking WARNING plus a finding — the declaration is checked, not
trusted.

### Step 4: Mark step done

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step emit-landing --outcome done \
  --fact work_performed=true \
  --display-detail "landing -> epic {epic}"
```

The `display_detail` string appears in the renderer's per-step `[OK]` row.

`work_performed=true` records that a landing message actually reached the inbox on this path. The
step declares `records_facts: [work_performed]` because it has an `--outcome done` branch reachable
WITHOUT having performed its characteristic work — the Error Handling row below marks `done` after an
inbox write that failed — which is the contract's stated trigger for the declaration. A consumer
asking *"did this run actually emit a landing?"* reads the fact; `outcome: done` alone cannot answer
it.

## Error Handling

| Scenario | Action |
|----------|--------|
| A fact read (`manage-status` / `manage-solution-outline` / `manage-execution-manifest`) returns an error | Write that field as `n/a` in the fenced block (key still present) and continue — a missing field never blocks the emission or archive |
| `orchestrator inbox write` returns an error | Non-fatal: log the failure, then mark `done` recording `work_performed=false` (the call is spelled out below); a failed landing write never blocks finalize |
| `epic` is empty / plan not orchestrated | Step 0's diagnosable skip fires — no landing is written and the misconfiguration is surfaced as a WARNING |

The failed-write branch terminates with this call — spelled out rather than left to prose, because it
is the one `done` branch on which no landing was emitted, and `work_performed=false` is the only signal
that distinguishes it from the Step 4 success above:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step emit-landing --outcome done \
  --fact work_performed=false \
  --display-detail "landing write failed: {error}"
```

## Related

- [../../plan-orchestrator/standards/landing-payload-spec.md](../../plan-orchestrator/standards/landing-payload-spec.md) — the payload contract this step produces (single source of truth for the required fact keys)
- [../../plan-orchestrator/standards/inbox-envelope.md](../../plan-orchestrator/standards/inbox-envelope.md) — the envelope schema and the `landing` kind
- [finalize-step-preference-emitter.md](finalize-step-preference-emitter.md) — the inline post-merge-ordered finalize-step exemplar this step is modeled on
- [../../extension-api/standards/finalize-step-order-bands.md](../../extension-api/standards/finalize-step-order-bands.md) — the reserved terminal-emission band this step occupies
