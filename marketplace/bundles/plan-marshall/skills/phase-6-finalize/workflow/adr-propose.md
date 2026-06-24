---
name: default:adr-propose
description: Propose ADRs from plan decisions
order: 62
default_on: false
presets: []
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
---

# ADR Propose

Pure executor for the `adr-propose` finalize step. Reads the completed plan's artefacts, detects decision-shape signals, and proposes draft ADRs (status `Proposed`) for the architectural decisions the plan settled. Advisory only — never blocks the finalize pipeline.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

See also `standards/adr-integration.md` for conceptual guidance on when adr-propose fires, the decision-shape signals it detects, and the lesson-vs-ADR divide.

## The lesson-vs-ADR divide

`adr-propose` and `lessons-capture` are siblings that look back at the same plan history, but they record different kinds of durable signal — they MUST NOT double-record the same observation:

- **`lessons-capture` records a recurrence pattern** — "we hit this defect, watch for this diagnostic signature next time". Ephemeral; pruned once the recurrence stops.
- **`adr-propose` records a decision** — "the architecture is X because alternatives Y and Z fail in ways A and B". Durable; reads as a standalone decision record years later.

If a plan signal is "we chose this shape and rejected these concrete alternatives for these architectural reasons", it is an ADR. If it is "this bug class recurred, here is the pattern to watch for", it is a lesson. When in doubt, the `manage-adr` Authoring Discipline (§ "What goes into a lesson instead") is the single source of truth for the boundary — do not restate the criteria, follow the standard.

## Dispatch contract

**Dispatcher-level Signal Gate precondition**: This body does NOT carry its own decision-shape gate. The deterministic decision-shape precondition is owned by `phase-6-finalize/SKILL.md` Step 3 § "Adr-propose Signal Gate" (the dispatch loop). When the dispatcher observes no decision-shape signal, it records `mark-step-done --outcome skipped --display-detail "no decision-shape signals"` directly and this workflow body is NOT dispatched. Reaching this body therefore PROVES at least one decision-shape signal was present — the body proceeds straight into ADR proposal without re-evaluating the gate.

This step runs as a Task dispatch under the `post-run-review` sub-key (resolved via `manage-config effort resolve-target --phase phase-6-finalize --role post-run-review`) with a 5-minute (300 s) per-agent timeout budget enforced by the SKILL.md Step 3 dispatch loop. The dispatcher emits the standardized `[DISPATCH]` work-log line at the call site — see [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) for the canonical emission contract. The `post-run-review` sub-key bundles adr-propose with lessons-capture and retrospective — all three look back at the full plan history and ride the same level. On timeout the dispatcher records `outcome=failed` with `display_detail="timed out after 300s"` and continues — ADR proposal is advisory and never blocks the rest of the pipeline.

### `[DISPATCH]` log line (emitted by the dispatcher)

The phase-6-finalize SKILL.md dispatcher emits the line below immediately before invoking this workflow:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role=post-run-review workflow=plan-marshall:phase-6-finalize/workflow/adr-propose.md plan_id={plan_id}"
```

## Execution

### Step 1 — Load the manage-adr skill

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:manage-adr"
```

```
Skill: plan-marshall:manage-adr
```

### Step 2 — Read the plan's decision-bearing artefacts

Author the proposals from the plan's own record. Read the clarified request, the solution outline, the decision log, and the task descriptions as the evidence base for decision-shape detection.

Read the clarified request narrative via the canonical verb chain:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request read --plan-id {plan_id} --section clarified_request
```

`manage-plan-documents`' only top-level choices are `{list-types, request}` — the request read is the `request` noun's `read` sub-verb, NOT a top-level `read` (and there is no `references` noun).

Read the solution outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file solution_outline.md
```

Read the decision log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  read --plan-id {plan_id} --type decision
```

### Step 3 — Detect decision-shape signals

Scan the artefacts read in Step 2 for decision-shape signals — the markers that distinguish an architectural decision (ADR-worthy) from incidental implementation work. A signal is present when the plan record shows one or more of:

- **Rejected concrete alternatives**: the outline or decision log names an alternative approach and states why it was not chosen (e.g. the solution_outline `compatibility` line, an "Alternatives Considered" passage, or a decision-log entry that records a fork with a rationale).
- **Principle statements**: the plan asserts a general rule the architecture now follows ("X is always owned by Y", "Z is derived, never authored").
- **Architecture-affecting changes**: the plan introduces, relocates, or removes a structural element (a new extension point, a bundle move, an ownership transfer, a new lifecycle hook) whose shape future work must respect.

The detail standard `standards/adr-integration.md` carries the authoritative signal taxonomy and the lesson-vs-ADR split — consult it rather than re-deriving the criteria here.

### Step 4 — Avoid double-recording an already-captured decision

Before proposing, scan the existing ADR corpus so the step never re-proposes a decision the corpus already records:

```bash
python3 .plan/execute-script.py plan-marshall:manage-adr:manage-adr scan \
  --affects {module}
```

Read the returned `summary` fields. When a detected decision is already covered by an existing ADR's summary, skip the proposal for that decision (it is already in the corpus). The `--affects` filter scopes the scan to the plan's declared module(s); omit it to scan the whole corpus.

### Step 5 — Propose each detected decision for user confirmation

For each decision-shape signal that is NOT already covered by the existing corpus:

1. Compose a concise draft ADR title that names the decision (not the plan).
2. Surface the draft title to the user for confirmation via `AskUserQuestion` (advisory — the user may decline any individual proposal). Never auto-create without confirmation.
3. On confirmation, create the ADR as `Proposed`, which emits the progressive-disclosure metadata block from D1:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-adr:manage-adr create \
     --title "{confirmed_title}" --status Proposed
   ```

4. Parse the created `path` from the TOON output and write the ADR body via the Write tool, filling the metadata block (`summary`, `tags`, `affects`, `supersedes`) and the decision sections (Context, Decision, Consequences, Alternatives Considered, References) per the `manage-adr` Authoring Discipline. The body MUST follow the durable-decision-record shape — no PR numbers, commit SHAs, lesson IDs, dates, or incident narrative.

When the user declines all proposals, record nothing new and fall through to the Branch B `mark-step-done` below.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the proposal outcome. The payload differs by branch:

**Branch A — one or more ADRs proposed**: `{N}` is the count of `manage-adr create` calls made in this step. `{adr_numbers}` is the comma-joined list of ADR numbers returned by those calls (e.g. `ADR-004,ADR-005`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step adr-propose --outcome done \
  --display-detail "{N} ADR(s) proposed ({adr_numbers})"
```

**Branch B — no ADRs proposed** (advisory step; decision-shape signals were present but already covered, or the user declined every proposal):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step adr-propose --outcome done \
  --display-detail "no ADRs proposed"
```

**Branch C — no decision-shape signals (skip)**: NOT emitted by this body. The `outcome=skipped` recording is the dispatcher's responsibility (see `phase-6-finalize/SKILL.md` Step 3 § "Adr-propose Signal Gate") and fires before this workflow is dispatched. This body only runs when at least one decision-shape signal was present, so its `mark-step-done` calls are exclusively Branches A or B above.

## Output

```toon
status: success | error
display_detail: "<{N} ADRs proposed or `no ADRs proposed`>"
adrs_proposed: {N}
```

The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded verbatim via `mark-step-done --display-detail` above.
