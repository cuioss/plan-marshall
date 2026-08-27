---
lane:
  class: core
  cost_size: M
name: default:lessons-capture
description: Capture lessons from triage findings and PR-review escalations (skipped when qgate_findings=0, pr_comments_promoted=0, and script_failure_clusters=0)
order: 991
default_on: true
mutates_source: false
post_run_review: true
presets:
  - local
  - standard
  - full
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Lessons Capture

Pure executor for the `lessons-capture` finalize step. Records lessons learned from the implementation. Advisory only — does not block.

**Post-run review (`post_run_review: true`, `mutates_source: false`)**: this step reads the triage findings and PR-review escalations the merge gate's re-review barrier produces, so its evidence is only complete once `default:branch-cleanup` has run — `order: 991` places it after that gate. Being post-merge-ordered, the step writes NO tracked source: every branch writes only UNTRACKED plan state under `.plan/` (lesson files, inbox payloads). The step therefore never reaches the dispatcher's commit instrumentation — item 5f reads the declared `mutates_source` fact first and skips (a)-(d) entirely. The declaration is not taken on trust, though: because this step also declares `post_run_review: true`, item 5f's sub-item (0) observes the MAIN CHECKOUT once on return (the worktree is gone by this order) and reports any dirty TRACKED path — source, or a tracked `.plan/` config/descriptor, the exemption being keyed on git trackedness rather than the path prefix — as a non-blocking WARNING plus a finding. So the claim is checked, not merely asserted. Branch B3's architecture hints are NOT written in the worktree — an `architecture enrich` write post-merge would land as an uncommitted diff on `main`, the exact defect [`../standards/source-edit-pushability.md`](../standards/source-edit-pushability.md) exists to prevent — so B3 names each owed hint in a follow-up artifact via that document's discover-after-merge route instead.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes non-`manage-*` scripts too, and a `manage-*`-scoped convention left exactly those calls uncovered — the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than looking for a fixed field list: beyond `status` and `error` the diagnostic fields vary by verb — `ci` verbs carry `operation`, `error_cause`, and `context`, the plan-resolution envelopes carry `message` and `plan_id` instead, and neither list is exhaustive. `error` is sometimes a hard-coded generic string whose real cause sits in one of the other fields, so dropping them can discard the cause entirely. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return — the envelope's diagnostic fields are not success payload, and dropping any of them leaves the step reporting a failure with no cause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

See also `standards/lessons-integration.md` for conceptual guidance on when and what to capture.

**Dispatcher-level Signal Gate precondition (B4)**: This body NO LONGER carries the three-signal Signal Gate. The deterministic three-signal precondition (pending Q-Gate findings, automated-review outcome, script-failure clusters) has been relocated to `phase-6-finalize/SKILL.md` Step 3 § "Lessons-capture Signal Gate" (item 4b in the dispatch loop) so the envelope spawn cost is avoided when all three signals are zero. When the dispatcher observes all three counts zero, it records `mark-step-done --outcome skipped --display-detail "no lesson-bearing signals"` directly and this workflow body is NOT dispatched — **regardless of orchestration**. This step's skip no longer carries an orchestration carve-out: the one `kind: landing` message an orchestrated run owes its epic is emitted by the dedicated `emit-landing` terminal step at `order: 1000` (after every reporting step), NOT by this step, so an orchestrated run at zero signals has nothing for lessons-capture to emit and skips exactly as a non-orchestrated one does. Reaching this body therefore proves at least one signal was non-zero. The body re-evaluates no signals: it branches on `orchestrated` first (see Execution below) to decide candidate-lesson routing and otherwise proceeds straight into the three-step path-allocate flow.

**Gate counts and orchestration context as runtime inputs**: The dispatcher forwards the three observed counts AND the once-per-run orchestration verdict on the prompt body so the body never re-issues the signal queries and never re-issues the orchestration detection. The available runtime inputs are:

- `orchestrated` — bool; `true` when this plan was launched from an epic's staged plan spec. Resolved once per finalize run by the dispatcher (`phase-6-finalize/SKILL.md` Step 3 item 4b.a0) via `manage-plan-documents request read --section source_id` then `orchestrator inbox detect`. The body MUST NOT re-issue either call.
- `epic` — string; the epic slug when `orchestrated` is `true`, the empty string otherwise. Same must-not-recompute obligation.

- `signal_qgate_pending_count` — integer; sum across `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize`.
- `signal_automated_review_count` — integer (0 or 1); 1 when the `automated-review` step had an outstanding/non-done state (outcome anything other than `done`, or its `display_detail` reports a non-zero promoted-comment count) OR when the run remediated one or more actionable review-bot findings (`manage-findings list --type pr-comment --resolution fixed` returned `filtered_count >= 1`). The remediated-in-run trigger fires the signal even when the step `outcome=done` and zero comments are outstanding at gate-evaluation time — a review-bot finding caught-and-fixed in-run is exactly the slipped-then-caught defect class lessons-capture exists to record.
- `signal_script_failure_clusters_count` — integer; number of distinct failing script notations across three marker classes: `[FAILED]` work-log lines, `[ERROR] ... script_failure` lines (the per-call non-zero-exit marker emitted by phase error handling), and `voluntary_checkpoint → error` reclassifications (dispatch-boundary no-progress reclassifications). A notation that fails under more than one marker class counts once (union dedup by distinct notation).

These counts MAY be consulted as context when authoring the lesson bodies (e.g., to focus recording on whichever signal source dominated), but the body MUST NOT re-issue `manage-findings qgate list`, `manage-status read`, or `manage-logging read --type work` to recompute them — the dispatcher already paid that cost. The prohibition is on re-deriving the COUNTS, not on reading the records they summarise: a body that needs a finding's or a log line's content in order to author the candidate it represents may read it.

When the lesson author needs the original/clarified request as context, read it via the canonical verb chain:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request read --plan-id {plan_id} --section clarified_request
```

`manage-plan-documents`' only top-level choices are `{list-types, request}` — the request read is the `request` noun's `read` sub-verb, NOT a top-level `read` (and there is no `references` noun).

This step runs as a Task dispatch under the `post-run-review` sub-key — the dispatcher derives that sub-key from this doc's `post_run_review: true` frontmatter fact rather than from a hand-maintained step list, so the ordering obligation and the dispatch role read from one source (resolved via `manage-config effort resolve-target --phase phase-6-finalize --role post-run-review`) — with a 5-minute (300 s) per-agent timeout budget enforced by the SKILL.md Step 3 dispatch loop. The dispatcher passes the dispatch context to its `effort resolve-target`, so the resolve seam emits the `[DISPATCH]` work-log line and the paired decision-log record, per firing — see [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) for the canonical emission contract. The `post-run-review` sub-key bundles lessons-capture with retrospective — both workflows look back at the full plan history and ride the same level. On timeout the dispatcher records `outcome=failed` with `display_detail="timed out after 300s"` and continues — lessons capture is advisory and never blocks the rest of the pipeline.

## Execution

### Orchestration branch (evaluate FIRST)

Branch on the `orchestrated` runtime input before anything else. The branch supersedes the ACTIONABLE/KNOWLEDGE partition and the three-gate lesson-creation policy for the orchestrated case.

- **`orchestrated: false`** — every existing path below is unchanged: the ACTIONABLE/KNOWLEDGE partition, the three-gate policy, the three-step path-allocate `manage-lessons` flow, and Branches A / B / B2 / B3. Continue at "The dispatcher-level Signal Gate…" below.
- **`orchestrated: true`** — make **zero** `manage-lessons add` calls for lesson-shaped output, and do NOT run the ACTIONABLE/KNOWLEDGE partition or the three-gate policy. Classification is deferred to the orchestrator-side pickup, because only the orchestrator holds the cross-plan context that judgement needs. Follow the message-emission contract immediately below, then record **Branch B4**. (No branch of this body calls `architecture enrich` — see the KNOWLEDGE routing section below for why the hints store is unreachable from a post-merge-ordered step.)

#### Orchestrated emission contract

Message granularity is **one message per emitted item** — that is what the envelope's sequence exists to allocate:

- **One `kind: candidate-lesson` message per candidate.** Every candidate lesson and every finding rides as `candidate-lesson`; the plan performs **no** global-vs-epic classification.

This branch emits **NO `kind: landing` message**. The one landing an orchestrated finalize run owes its epic is emitted by the dedicated `emit-landing` terminal step (`order: 1000`), after every reporting step so it can carry the run's facts; a landing from here too would put two landings on one run. This step's job is the candidate-lesson stream alone.

**Where the candidates come from.** This branch skips the ACTIONABLE/KNOWLEDGE partition and the three-gate policy, but it does NOT skip candidate collection — those sections govern classification and allocation, not production. The candidate population is the one every branch draws on: the concrete records behind the dispatcher's three forwarded signal counts.

- `signal_qgate_pending_count` — the Q-Gate findings across `2-refine`, `3-outline`, `4-plan`, `5-execute`, and `6-finalize`, pending and resolved-in-run alike.
- `signal_automated_review_count` — the `plan-marshall:automatic-review` step's outstanding state, plus the review-bot findings the run remediated (`--type pr-comment --resolution fixed`).
- `signal_script_failure_clusters_count` — the distinct failing script notations behind the `[FAILED]`, `[ERROR] … script_failure`, and `voluntary_checkpoint → error` markers.

Each such record is one `kind: candidate-lesson` message. Reading those records for their CONTENT is not a recomputation: the must-not-recompute rule above bars re-deriving the three COUNTS, not reading the findings and log lines those counts summarise. Classification stays deferred to the orchestrator-side pickup exactly as stated above — the plan transmits candidates, it does not judge them.

Reaching this branch proves at least one signal was non-zero (the dispatcher's Signal Gate skips this step at zero signals regardless of orchestration — see the precondition above), so this branch always emits at least one `kind: candidate-lesson` message.

For each message, stage the payload body with the `Write` tool first, then write it:

```text
Write {plan_dir}/work/inbox-payload.md
```

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox write \
  --slug {epic} --sender-type plan --sender-id {plan_id} --kind {kind} \
  --payload-file {plan_dir}/work/inbox-payload.md
```

Staging the body with `Write` first is the same shell-safety reason the lesson three-step flow exists — the anti-pattern list below (inline `python -c`, `$(printf …)`, `#`-bearing heredocs) applies verbatim to inbox payload bodies. See [`../../plan-orchestrator/standards/inbox-envelope.md`](../../plan-orchestrator/standards/inbox-envelope.md) for the envelope schema, the `kind` enum, and the header-field table; do not restate them here.

Branch B4 writes only under `.plan/`, matching the step's `mutates_source: false` fact — so, exactly like every other branch, it never reaches the dispatcher's commit instrumentation at all (item 5f skips (a)-(d) on the declared fact), and, exactly like every other branch, the claim is checked by item 5f's sub-item (0) post-run-band guard rather than trusted.

### Non-orchestrated execution

The dispatcher-level Signal Gate (see header above, and `phase-6-finalize/SKILL.md` Step 3 item 4b) has already certified that at least one of the three signal sources is non-zero before this body runs. Proceed to the `Skill: plan-marshall:manage-lessons` load below, then run the three-gate lesson-creation policy before allocating any new lesson.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:manage-lessons"
```

```text
Skill: plan-marshall:manage-lessons
```

### Classify each candidate signal: ACTIONABLE vs KNOWLEDGE

Before running the lesson-creation policy gates, partition each candidate signal into one of two shapes. Only ACTIONABLE signals proceed to the lesson-creation gates; KNOWLEDGE signals route to the architecture-hints store instead and do NOT also create a lesson.

- **ACTIONABLE** — a defect plus a corrective action (a recurrence with a "do X instead of Y" rule). These are the genuine lessons: keep the `manage-lessons add` path below.
- **KNOWLEDGE** — a durable, non-actionable project fact with no defect + corrective-action shape (an implementation gotcha, a learned observation about how the codebase behaves, an established convention). A KNOWLEDGE fact is NOT a lesson — its destination is the per-module architecture-hints store.

**The hints store is unreachable from here, so the hint is OWED, not written.** This step is `post_run_review: true` and runs after the merge gate, where an `architecture enrich` call would write the per-module `enriched.json` — tracked source — onto `main` as an uncommitted diff that can never ride the plan's PR. Do **not** call `architecture enrich` from this body. Instead, take the discover-after-merge route in [`../standards/source-edit-pushability.md`](../standards/source-edit-pushability.md) § "The discover-after-merge rule": name each owed hint in an explicit follow-up artifact so the enrichment is scheduled and visible rather than lost.

File the follow-up artifact through the SAME three-step path-allocate flow documented below (`add` → Write → `set-body`), with:

- `--component "{bundle}:{skill}"` — the component that owns the module the hint belongs to.
- `--category improvement`.
- `--title "Owed architecture hint: {module} — {one-line fact}"`.

The body MUST name, per owed hint: the target `--module`, the enrich verb the fact's shape calls for (`tip` for an implementation gotcha, `insight` for a learned observation, `best-practice` for an established convention — see `manage-architecture` SKILL.md § "enrich tip / insight / best-practice"), and the verbatim hint text, so the owed `architecture enrich` call is reconstructible without re-deriving the fact.

- **Module selection**: use `default` when the fact is cross-cutting (not specific to one bundle/module — a project-wide convention or root-level fact); use the owning module otherwise. The `default` module is the first-class home for cross-cutting project knowledge.
- **The follow-up artifact is not a reclassification.** Recording an owed hint does not turn a KNOWLEDGE fact into an ACTIONABLE lesson: the artifact records *an enrichment this run could not perform*, and the fact's destination is still the hints store. The no-dual-write rule is unchanged in substance — a KNOWLEDGE signal produces exactly ONE record (the owed-hint artifact), never both an owed-hint artifact and a defect lesson for the same signal.

When every candidate signal is KNOWLEDGE (only owed-hint artifacts were filed, no defect lesson allocated), record the outcome via Branch B3 in the Mark-Step-Complete section below.

### Run the lesson-creation policy gates first

Run the gates below only for the ACTIONABLE signals identified above. Before allocating a new lesson, run the canonical three-gate sequence defined in [`../../manage-lessons/standards/lesson-creation-policy.md`](../../manage-lessons/standards/lesson-creation-policy.md): Gate 1 (dedup against the existing corpus), Gate 2 (active-plan check), then Gate 3 (create). Do not restate the gate mechanics here — follow the standard.

- **Gate 1 → `merge_into`**: extend the existing lesson (append a `## Recurrence` section / broaden scope) instead of adding a new one. Record nothing new; this is a Branch B2 outcome below.
- **Gate 1 → `already_closed`**: follow the standard's closed-lesson contract (deletion requires user confirmation). Branch B2 outcome.
- **Gate 2 → covering active plan**: fold the observation into that plan; do not file a standalone lesson. Branch B2 outcome.
- **Gates 1 and 2 both clear**: proceed to the three-step path-allocate add flow below — this IS Gate 3.

### Gate 3 — Create: the three-step path-allocate add flow

Lessons are added in **three steps** via the path-allocate flow. This is the single canonical sequence — there is no inline `--detail` form and no alternative API variant. The body is staged to a plan-scoped file with the Write tool, then applied to the lesson via `set-body`, so arbitrary markdown (sections with `##` headings, fenced code blocks, multi-paragraph prose) never passes through a shell argument.

### Step 1 — Allocate the lesson file

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "{bundle}:{skill}" \
  --category {bug|improvement|anti-pattern} \
  --title "{concise summary}"
```

Required flags: `--component`, `--category`, `--title`. The call creates a file with the metadata header and the `# {title}` heading already in place (body is empty) and returns both the lesson `id` and absolute `path` in the TOON output.

### Step 2 — Stage the body via the Write tool

Parse `id` from Step 1's TOON output. Use the Write tool to write the lesson body markdown to a plan-scoped staging file:

```text
Write {plan_dir}/work/lesson-body-{id}.md
```

Where `{plan_dir}` is the absolute path to the active plan directory and `{id}` is the lesson identifier from Step 1 (e.g., `lesson-body-2026-04-27-10-005.md`). The body may contain arbitrary markdown — `##` section headings, fenced code blocks, lists, multiple paragraphs — because the Write tool delivers the content directly without shell quoting.

### Step 3 — Apply the staged body via `set-body`

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-body \
  --lesson-id {id} \
  --file {plan_dir}/work/lesson-body-{id}.md
```

The script reads the staged file from disk and replaces the body section of the lesson, preserving the metadata header and `# {title}` heading written in Step 1. On success the call returns the lesson `path` and `body_bytes_written`.

### Anti-patterns — prohibited shortcuts

Do **not** attempt to compress the three steps into a single shell-mediated write. The following shortcuts are explicitly prohibited because they either trip the host platform's path-validation heuristic on `#`-bearing markdown, mangle whitespace and code fences, or otherwise corrupt the lesson body:

- `python -c "open(...).write(...)"` — inline Python that smuggles body content through the shell argument vector. Forbidden.
- `$(printf ...)` — command substitution to assemble multi-line markdown. Forbidden.
- Heredocs containing lines that begin with `#` — markdown headings inside `<<EOF` blocks trip the bare-comment heuristic and trigger security prompts. Forbidden.

Use the three-step path-allocate flow above (Step 1 `add` → Step 2 Write tool → Step 3 `set-body --file`) for every lesson body. There is no `--detail`, no `--detail-file`, no inline-body variant on `add` — the path-allocate flow is the single supported API for non-trivial bodies.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the capture outcome. The payload differs by branch:

**Branch A — one or more lessons recorded**: `{N}` is the count of ACTIONABLE **defect lessons** allocated in this step — owed-hint follow-up artifacts (Branch B3) are counted separately and never fold into this number. `{lesson_ids}` is the comma-joined list of lesson identifiers returned by those calls (e.g. `lesson-2026-04-17-005,lesson-2026-04-17-006`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "{N} lesson(s) recorded ({lesson_ids})"
```

**Branch B — no lessons recorded** (advisory step; nothing lesson-worthy emerged from this plan):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "no lessons recorded"
```

**Branch B2 — folded into an existing lesson or active plan, no new lesson recorded**: the gate sequence resolved the observation at Gate 1 (`merge_into` / `already_closed`) or Gate 2 (covering active plan), so no new lesson was allocated:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "folded into existing lesson/plan, no new lesson"
```

**Branch B3 — owed architecture hints filed, no defect lesson recorded**: every candidate signal was KNOWLEDGE and was named in an owed-hint follow-up artifact (the hints store is unreachable from this post-merge-ordered step); no defect lesson was allocated. `{N}` is the count of owed-hint artifacts filed in this step.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "{N} owed architecture hint(s) filed"
```

**Branch B4 — routed to epic inbox, no global-store write**: the `orchestrated: true` branch fired; every emitted item was written as one `kind: candidate-lesson` inbox message and zero `manage-lessons add` / `architecture enrich` calls were made. `{N}` is the count of `orchestrator inbox write` calls made in this step (≥ 1 — this branch runs only when at least one signal was non-zero, so at least one candidate-lesson is emitted; the run's one `kind: landing` message is the `emit-landing` step's, not this one's).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome done \
  --display-detail "{N} inbox message(s) -> epic {epic}"
```

**Branch C — no lesson-bearing signals (skip)**: NOT emitted by this body. The `outcome=skipped` recording is now the dispatcher's responsibility (see `phase-6-finalize/SKILL.md` Step 3 item 4b) and fires before this workflow is dispatched, at zero signals **regardless of orchestration** — the three-zero short-circuit no longer carries an orchestration carve-out (the landing an orchestrated run owes is the `emit-landing` terminal step's now, not this step's). This body therefore runs only when at least one signal was non-zero, and its `mark-step-done` calls are drawn from Branches A, B, B2, B3, and B4 above — an orchestrated run with at least one signal routes its candidate-lessons through B4.

## Output

```toon
status: success | error
display_detail: "<{N} lessons recorded or `no lessons recorded` or `{N} owed architecture hint(s) filed` or `{N} inbox message(s) -> epic {epic}`>"
lessons_recorded: {N}
owed_hints_filed: {N}
inbox_messages_written: {N}
```

`lessons_recorded` is the count of defect lessons allocated in this step (Branch A); it is `0` for Branches B, B2, B3, and B4. `owed_hints_filed` is the count of owed-architecture-hint follow-up artifacts filed in this step (Branch B3); it is `0` when no KNOWLEDGE signals were processed and `0` on B4. `inbox_messages_written` is the count of `orchestrator inbox write` calls made in this step (Branch B4, all `kind: candidate-lesson`); it is `0` on every non-orchestrated branch and `≥ 1` on B4 (this step runs only when at least one signal was non-zero). Downstream consumers MUST check `owed_hints_filed` and `inbox_messages_written` to distinguish the three zero-lesson outcomes: B3 (all-KNOWLEDGE) sets a non-zero `owed_hints_filed`, B4 (routed to the epic inbox) sets a non-zero `inbox_messages_written`, and B/B2 (nothing lesson-worthy) leaves both `0` — all three set `lessons_recorded: 0`. The `display_detail` value (≤80 chars, ASCII, no trailing period) is forwarded verbatim via `mark-step-done --display-detail` above.
