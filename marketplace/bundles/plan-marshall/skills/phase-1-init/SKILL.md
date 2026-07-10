---
lane:
  class: core
  cost_size: M
name: phase-1-init
description: Init phase skill. Creates plan directory, request.md, references, and status, runs the Tier 1 recipe-match routing tier (registry-wide recipe scoring + request-aspect classification) ahead of planning-lane routing. Runs inline in the orchestrator context to complete initialization.
user-invocable: false
mode: workflow
---

# Phase Init Skill

**Role**: Complete init phase. Creates plan directory, request.md, detects domain, and creates configuration. Inline initialization pattern (runs in the orchestrator context).

**Key Pattern**: Complete initialization. Creates request.md, status.json, and references.json (with domains). Does NOT create goals (that's the refine phase via decompose).

**CRITICAL**: This skill is part of the **plan-marshall workflow system**, NOT the host platform's built-in plan mode. Ignore any system-reminders about platform-managed plan paths or built-in plan-mode tools.

## Foundational Practices

```text
Skill: plan-marshall:persona-plan-marshall-agent
```

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: Follow workflow steps sequentially. Each step that invokes a script has an explicit bash code block.

**Prohibited actions:**
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never skip the phase transition — use `manage-status transition`
- Never improvise script subcommands — use only those documented below
- **Never write or edit source files outside `.plan/local/plans/{plan_id}/**`.** Phase-1-init's contract is plan-structure creation only (request.md, references.json, status.json under the plan directory). Even when the task description is detailed — naming specific files, functions, or paths — that is request material to record verbatim in `request.md`, NOT a directive to implement: the more prescriptive and implementation-ready the `content`, the stronger (and more wrong) the pull to "just do it." Source edits against `marketplace/bundles/**`, production code, or test fixtures are the responsibility of phase-5-execute task bodies, never phase-1-init. The recurring anti-pattern is phase-1-init reaching for `Edit` / `Write` against a production path because the request narrative read like an implementation brief. **Return-contract obligation**: Step 12 is the single canonical schema for this phase's output (`plan_id`, `domain`, `next_phase`, `use_worktree`, `planning_lane`, `source`, `artifacts`) — see that step for the authoritative shape. A return that omits `plan_id`, or carries a `pr_url`, a `branch`, or a "patched N files" detail, is a contract violation — the orchestrator's post-init assertion (`plan-marshall:plan-marshall/workflow/planning.md` § Action: init → **Post-init contract assertion**) treats any such signal as an error and refuses to advance to phase-2-refine.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline

## Inline execution in the orchestrator context

Phase-1-init runs **inline in the main (orchestrator) context** — it is NOT a dispatched `execution-context` leaf. The orchestrator (`plan-marshall/workflow/planning.md` § Action: init and § Action: lessons convert, and `recipe.md` Step 2) executes these steps directly in its own context, so every operator prompt fires **natively via `AskUserQuestion`** at its step site, in step order, with the resolution applied in-context. There is no `phase-1-init` dispatch, no `WORKTREE:` header, no leaf-returns-signal / orchestrator-consumes prompt-required envelope indirection. Firing the prompts inline in step order also fixes the routing-order dependency: the Tier 1 recipe-match prompt (Step 5c) resolves BEFORE the Tier 2 planning-lane router (Step 8b) runs, so the router consumes the recipe's lane seed instead of routing on an unset `change_type`/`scope_estimate`.

Mechanical sub-procedures stay inline as scripts: Step 5c recipe-match (Tier 1) is registry-wide for every source — it calls `manage-config recipe-match` and `manage-config aspect-classify` (heuristic-first, zero LLM call inside the scripts; the bounded LLM fallback for ambiguous matches fires only when the heuristic is ambiguous, preserving the zero-token property), and retains the lesson-only doc-shaped predicate path; Step 6 references initialization and Step 7 domain detection (`manage-config:domain-detect`) are pure scripts. Tier 1 recipe-match (Step 5c) is sequenced ahead of Tier 2 planning-lane routing (Step 8b). For the script-over-dispatch rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 2 (Heuristic 1 — script over dispatch).

## When to Activate This Skill

Activate when:
- Starting a new plan (no existing plan_id)
- User provides task via description, lesson_id, or issue URL
- Run inline by the orchestrator (`plan-marshall/workflow/planning.md` § Action: init / § Action: lessons convert, or `recipe.md` Step 2) as the init step of the planning pipeline

---

## Phase-Entry Worktree Assertion

Phase 1-init has no preceding phase, so the Phase Entry Protocol's `phase_handshake verify` step is skipped (per [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#q-gate-check-phases-2-6) Q-Gate / handshake checks are scoped to phases 2-6). Phase-1-init persists only `metadata.use_worktree` into `status.json`. It does NOT create the worktree directory, and it records neither the feature branch nor a `worktree_path`: phase-5-execute Step 2.5 creates the worktree on first task execution, derives the feature branch `feature/{plan_id}`, and back-fills both `metadata.worktree_branch` and the resolved `metadata.worktree_path` at that point. The writer-chain detail lives in Step 3a's **Writer-chain contract**.

---

## Operation: create

**Input** (exactly ONE required):
- `description`: Free-form task description
- `lesson_id`: Lesson identifier to implement (e.g., `2025-12-02-001`)
- `issue`: GitHub issue URL or identifier
- `recipe`: Recipe key for predefined transformation (e.g., `refactor-to-standards`)

**Optional**:
- `plan_id`: Override auto-generated plan_id
- `domain`: Override auto-detection (java, javascript, plan-marshall-plugin-dev, generic)
- `base_branch`: Override the seeded merge-target branch for `references.base_branch` (default: `project.default_base_branch`, falling back to the current git branch).

### Step 1: Validate Input

Ensure exactly one input source is provided (description, lesson_id, issue, or recipe). If multiple or none provided, return error: "Provide exactly one of: description, lesson_id, issue, recipe"

### Step 2: Derive Plan ID

If `plan_id` not provided, derive from input. The non-lesson sources keep their
existing rules; the lesson source uses a deterministic title-based derivation
documented in **Step 2a** below.

- From description: first 3-5 meaningful words, kebab-cased, max 50 chars.
- From lesson: derived from the lesson **title** — see **Step 2a** below.
- From issue: issue number (e.g., `#123` → `issue-123`).
- From recipe: `recipe-{recipe_key}-{yyyy-mm-dd-hh}`, where `{yyyy-mm-dd-hh}` is the current UTC time obtained with a single `date -u +%Y-%m-%d-%H` Bash call (e.g., `recipe-refactor-to-standards-2026-06-08-16`). The timestamp suffix makes every recipe run produce a fresh `plan_id` — and therefore a fresh `feature/{plan_id}` branch — so a re-run of the same recipe never reuses a prior run's branch name. This is load-bearing: the Step 2a.3 collision check below only consults `manage-status list`, which excludes *archived* plans, so without the suffix a recipe re-run whose prior run was already archived reuses the identical branch name. A merged PR's branch-name association lingers on the remote even after the branch is deleted, so the next run's `create-pr` existence check (`ci pr view`, unfiltered by state) would resolve the stale merged PR instead of creating a fresh one.
- Description and issue rules: always kebab-case, max 50 chars. The recipe rule is kebab-case too, but its `{yyyy-mm-dd-hh}` suffix is appended after truncation, so a recipe `plan_id` may slightly exceed 50 characters — expected and acceptable, the same convention as the Step 2a.3 collision suffix.

#### Step 2a: Lesson-Source Plan ID Derivation

**Applicability**: This sub-step runs **only when `source == lesson`** and no
explicit `plan_id` was provided. For an explicit `--plan-id` override, skip
derivation entirely.

The lesson plan_id is a human-readable kebab-case slug of the lesson **title**,
not the timestamp slug. The derivation is fully deterministic — no LLM inference
is used to produce the slug.

**Sub-step 2a.1 — Fetch the lesson title early**:

Fetch the lesson record so the `title` field is available before derivation:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons get \
  --lesson-id {lesson_id}
```

Extract the `title` field from the TOON output. Retain the full lesson record
(title, category, component, content) in context — Step 4 ("From Lesson")
reuses this same result and does NOT re-fetch the lesson.

**Sub-step 2a.2 — Derive the kebab-case slug**:

Apply the following deterministic transform to the lesson `title`:

1. Lowercase the title.
2. Replace every run of non-alphanumeric characters with a single `-`.
3. Strip any leading and trailing `-`.
4. Truncate to 50 characters.
5. Strip any trailing `-` produced by the truncation in step 4.

The result is the candidate slug.

**Sub-step 2a.3 — Collision avoidance**:

Before continuing to Step 3, check whether the candidate slug already corresponds
to an existing plan directory:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list
```

Compare the candidate slug against the `plan_id` values in the returned list.

- If the candidate slug is **not** present, it is the final `plan_id`.
- If the candidate slug **is** present, append `-2`; if `{slug}-2` is also taken,
  append `-3`, and so on, incrementing the numeric suffix until a free slug is
  found. The first free suffixed form is the final `plan_id`. The suffix is
  appended after truncation, so a suffixed `plan_id` may slightly exceed 50
  characters — this is expected and acceptable.

### Step 2b: Plan-ID Derivation Guard (Phantom-ID Rejection)

**Applicability**: This guard runs **unconditionally** once Step 2 (and, for the
lesson source, Step 2a) has produced a final `plan_id` — for every source
(`description`, `lesson`, `issue`, `recipe`) and for an explicit `--plan-id`
override alike. It is the last checkpoint before Step 3 creates the plan
directory.

**Rationale**: A lesson-conversion dispatch composes the init call from values it
holds in context — and the harness's available tokens include the lesson-ID being
converted and the dispatched execution-context's own agent-id. When the wrong
token leaks into the `plan_id` slot (a lesson-ID such as `2026-05-11-08-004`, or
a UUID / execution-context agent token), Step 3 silently creates a *phantom*
plan directory keyed by that token, and the real lesson is never converted. The
failure is invisible: the dispatch reports success against an id that does not
correspond to the intended plan. This guard converts that silent miss into a
loud, structured contract violation the orchestrator can surface on the
lesson-conversion side.

**Reject when** the final `plan_id` matches **either** shape:

1. **Lesson-ID shape** — `YYYY-MM-DD-HH-NNN` (four hyphen-separated numeric
   groups: a `YYYY-MM-DD` date, a two-digit hour, and a zero-padded sequence
   number). Regex: `^\d{4}-\d{2}-\d{2}-\d{2}-\d{3,}$`. A `plan_id` of this shape
   is a lesson-ID that leaked into the plan-id slot — the caller passed the
   lesson being converted as the plan id.
2. **Agent-id shape** — any of:
   - a UUID (`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`),
   - a bare hexadecimal string of 12 or more hex characters with no hyphens
     (`^[0-9a-fA-F]{12,}$`, e.g. `aa82aa78f2414dc79` — the harness agent-id
     shape with no UUID hyphens and no prefix), or
   - an execution-context token (a value beginning case-insensitively with
     `execution-context` or `agent-`, e.g. `execution-context-level-3`,
     `agent-7f3c`).
   A `plan_id` matching any of these alternatives is the dispatched agent's own id
   that leaked into the plan-id slot.

A legitimately derived slug — kebab-case words from a description, an
`issue-{number}`, a `recipe-{key}-{yyyy-mm-dd-hh}`, or a lesson **title** slug —
never matches either shape, so the guard has no false-positive surface against
the documented Step 2 / Step 2a derivations.

**On a match**, abort the phase immediately and return the structured contract
violation (do NOT proceed to Step 3, do NOT create any plan directory). When the
plan directory does not yet exist, the work-log emit in § Error Handling is
skipped — return the TOON directly:

```toon
status: error
error: phantom_plan_id
plan_id: {derived_plan_id}
detected_shape: lesson_id | agent_id
message: "Derived plan_id '{derived_plan_id}' matches a {detected_shape} shape — a lesson-ID or agent-id leaked into the plan-id slot. Refusing to create a phantom plan directory."
recovery: "Re-dispatch init with an explicit --plan-id (a kebab-case slug), or fix the lesson-conversion call that passed the {detected_shape} as the plan_id."
```

**On no match**, the derived `plan_id` is valid — continue to Step 3.

### Step 3: Create or Reference Plan

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files create-or-reference \
  --plan-id {plan_id}
```

Parse the TOON output. The `action` field indicates:
- `action: created` - New plan directory was created, log phase start and continue to Step 3a
- `action: exists` - Plan already exists; fire the inline `AskUserQuestion` documented below and apply the operator's choice in-context

**On successful creation**, log the phase start (directory now exists):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-1-init) Starting init phase"
```

**If `action: exists`** — the plan directory already exists from a prior run. Because init runs inline in the orchestrator context, fire an `AskUserQuestion` natively at this site and apply the choice in-context:

```text
AskUserQuestion:
  question: "A plan with id '{plan_id}' already exists. How should I proceed?"
  options:
    - label: "Resume"  description: "Continue with the existing plan as-is (proceed to refine)"
    - label: "Replace" description: "Delete the existing plan and create a fresh one"
    - label: "Rename"  description: "Create the plan under a different plan_id"
```

Apply the resolution in-context:

- **Resume** — do NOT re-run init; the existing plan stands. Skip the remaining init steps and proceed straight to phase-2-refine with the existing `plan_id`.
- **Replace** — delete the existing plan and create a fresh one, then continue init normally from Step 3a:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
    --plan-id {plan_id}
  ```

  Re-run Step 3's `create-or-reference` (which now returns `action: created`), then continue. See `standards/plan-overwrite.md` for the overwrite details applied on Replace.
- **Rename** — restart init from Step 2 with a new `plan_id` (an explicit `--plan-id` override or a fresh derivation) so the collision is cleared.

### Step 3a: Create Status

Create `status.json` NOW — before any metadata write — so that every subsequent `manage-status metadata --set` and `manage-metrics start-phase` call has a real `status.json` to write into. Creating it late (after the Step 5c recipe/aspect writes) is the ordering bug this early placement fixes: a `manage-status metadata --set` issued before `status.json` exists writes into a phantom/partial file that the later create then clobbers.

Read the `use_worktree` and `branch_strategy` flags from the phase-1-init config to decide the `--use-worktree` seed:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init get --audit-plan-id {plan_id}
```

Extract `branch_strategy` (default: `feature`) and `use_worktree` (default: `true`). The title is the `{derived_title}` resolved in Step 2 — identical to the `--title` passed to `request create` in Step 5.1, so `status.json` and `request.md` carry the same title.

**When `branch_strategy == "feature"` AND `use_worktree == true`** (the default) — create status with `--use-worktree` so `metadata.use_worktree: true` is seeded:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id {plan_id} \
  --title "{derived_title}" \
  --phases 1-init,2-refine,3-outline,4-plan,5-execute,6-finalize \
  --use-worktree
```

**Otherwise** (the `use_worktree == false` opt-out, or `branch_strategy == "direct"`) — omit `--use-worktree` so `manage_status create` writes the explicit `metadata.use_worktree=false` marker:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id {plan_id} \
  --title "{derived_title}" \
  --phases 1-init,2-refine,3-outline,4-plan,5-execute,6-finalize
```

**Note**: Domain information is stored in `references.json` (as a `domains` list), not in `status.json`. All plans use the standard 6-phase model (verification is integrated into phase-5-execute).

**Writer-chain contract**: this `manage_status create` is the sole writer of `metadata.use_worktree` in phase-1-init — it writes neither `metadata.worktree_branch` nor `metadata.worktree_path`. Phase-5-execute Step 2.5 is the sole writer of both `metadata.worktree_branch` (derived as `feature/{plan_id}`) and the resolved `metadata.worktree_path` absolute value: it materializes the worktree on first task execution and persists both then. See `workflow-integration-git/standards/worktree-handling.md` for the canonical worktree contract.

### Step 3b: Seed Metrics Start-Time

Now that `status.json` exists (Step 3a), self-record `1-init.start_time` so the downstream fused `phase-boundary --prev-phase 1-init --next-phase 2-refine` call in `plan-marshall/workflow/planning.md` sees a real start timestamp rather than falling back to the structural `status.json.created` backfill:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics \
  start-phase --plan-id {plan_id} --phase 1-init
```

**Rationale**: Bootstrap phase has no preceding `phase-boundary` call to stamp `start_time` (the call requires a `plan_id`, which doesn't exist until Step 3 returns). Recording the start immediately after `status.json` is created makes the subsequent fused `phase-boundary --prev-phase 1-init` call (in `plan-marshall/workflow/planning.md`) compute a wall duration that bounds the phase duration — restoring the `Worked <= Wall` invariant. This call MUST follow Step 3a: recording the start before `status.json` exists is the ordering bug corrected here. The `_read_status_created` backfill in `manage-metrics.py` is a safety net for plans materialised under older orchestrator versions; the start-time recorded here is authoritative for current plans.

### Step 4: Get Task Content

**From Description**:
- Use description directly as original input
- No additional context

**From Lesson**:

The lesson record was already fetched in **Step 2a.1** (`manage-lessons get
--lesson-id {lesson_id}`) so that the `title` field was available for plan_id
derivation. Reuse the record retained in context from Step 2a.1.

If an explicit `--plan-id` was provided (so Step 2a was skipped and the lesson was
never fetched), fetch it now:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons get \
  --lesson-id {lesson_id}
```

Extract and use the retrieved fields: title, category, component, content.

**From Issue**:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue view \
  --issue {issue}
```

Parse TOON output to extract: title, body, labels, milestone, assignees

**From Recipe**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-recipe --recipe {recipe_key}
```

Parse TOON output to extract: recipe_name, recipe_skill, default_change_type, scope, domain.
Use recipe_name as title, recipe description as body.

### Step 4b: Pre-flight Reference Verification

**Applicability**: This step runs **only when `source == lesson`** (i.e., the input contained `lesson_id`). Skip entirely for `description`, `issue`, or `recipe` sources.

**Rationale**: Lessons can sit in the queue for arbitrary periods while unrelated work moves the underlying code. Without a pre-flight check the planner would seed outline + plan against a phantom code surface and the rot would only surface mid-execute. The check verifies that every concrete code reference cited in the lesson body still exists in the current tree before scope is locked.

See [`standards/lesson-source-premise-check.md`](standards/lesson-source-premise-check.md) for the authoritative extraction heuristics, verification helpers, the `AskUserQuestion` shape, and the per-branch persistence contract. The bullets below summarize the workflow — defer to the standard for any ambiguity.

**Sub-step 4b.1 — Extract concrete references**:

Apply the heuristics from `lesson-source-premise-check.md` to the lesson body resolved in Step 4 ("From Lesson"). Collect:

- File paths (relative or absolute paths matching the path regex)
- Function / method / subcommand names rendered in backticks
- CLI invocation shapes (e.g., `python3 .plan/execute-script.py {notation} {subcommand} ...`)
- Anti-pattern signatures (substrings the lesson explicitly calls out as wrong)

If extraction yields zero references, log a single `[ARTIFACT]` work-log entry noting "no extractable references — skipping pre-flight check" and continue to Step 5.

**Sub-step 4b.2 — Verify each reference**:

For each extracted reference:

- **File paths**: use `Read` against the current tree; missing or empty files mark the reference stale.
- **Function / pattern names**: use `Grep` (literal, then regex if literal misses) across the tree; zero matches mark the reference stale.
- **CLI shapes**: invoke the cited script with `--help` and confirm the named subcommand / flag still appears in the output; absence marks the reference stale.

Record each `(reference, status, evidence)` triple in an in-memory obsolescence report.

**Sub-step 4b.3 — Surface obsolescence via a native prompt**:

If ANY reference is stale, fire an `AskUserQuestion` natively at this site (the three options are defined in `lesson-source-premise-check.md`) and apply the choice in-context:

```text
AskUserQuestion:
  question: "Some code references cited by this lesson are stale: {stale_reference_summary}. How should I proceed?"
  options:
    - label: "Refine"   description: "Attach the obsolescence report to request.md as a clarifying note and proceed"
    - label: "Close"    description: "The problem no longer exists — delete the lesson and this plan, and abort"
    - label: "Residual" description: "Drop the stale references, keep the still-valid ones, and proceed"
```

Apply the resolution in-context:

1. **Refine** — append the obsolescence report to `request.md` under a `## Pre-flight Reference Verification` heading (via the `Write`/`Edit` tool against the plan-scoped `request.md`) so downstream phases see it as part of the request scope, then continue to Step 5.
2. **Close as resolved** — the lesson describes a problem that no longer exists; delete the lesson (`manage-lessons remove --lesson-id {lesson_id}`) and the just-created plan (`manage-status delete-plan --plan-id {plan_id}`), and abort init.
3. **Residual scope** — work-log each dropped stale reference for downstream scope audit and continue to Step 5 with the reduced reference set.

If ALL references verify cleanly, fire no prompt, log the success, and continue to Step 5.

**Sub-step 4b.4 — Log the decision**:

Emit one decision-log entry with the `(plan-marshall:phase-1-init:source-premise)` prefix, recording both what was detected and the resolution applied:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init:source-premise) {decision_summary}"
```

Where `{decision_summary}` is one of:

- `All N references verified — no obsolescence detected.`
- `Obsolescence detected (N stale of M total) — operator chose {refine|close|residual}.`

Note: on the **Close** resolution the plan directory is deleted, so emit this decision-log line BEFORE the delete (or skip it — the abort is self-evident from the delete).

### Step 5: Write request.md

Create the request document via a two-step path-allocate flow. The script allocates a metadata-only stub and returns the absolute path; the body content is then written directly to that path with the `Write` tool. This pattern keeps the verbatim lesson/issue/description body out of shell arguments, which is essential because multi-line markdown (headings, code fences, blank lines) marshalled through `--body "..."` triggers security prompts and corrupts content.

**Step 5.1 — Allocate the request stub:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request create \
  --plan-id {plan_id} \
  --title "{derived_title}" \
  --source {description|lesson|issue|recipe} \
  [--source-id "{lesson_id|issue_url|recipe_key}"]
```

Parse the TOON output and extract the `path` field — this is the absolute path of the newly allocated request.md stub.

**Step 5.2 — Write the verbatim body:**

Use the `Write` tool to write the original input content directly to `{path}` from Step 5.1. The body is the verbatim content from Step 4:
- **description**: The free-form description text
- **lesson**: The lesson body (title + detail)
- **issue**: The issue body
- **recipe**: The recipe description

```text
Write({path}, {verbatim_body_content})
```

**Parameters:**
- `--title`: Derived title from input
- `--source`: One of `description`, `lesson`, `issue`, or `recipe`
- `--source-id`: (only for traceable sources) External reference identifier:
  - For `lesson`: The lesson ID (e.g., `2025-12-02-001`)
  - For `issue`: The issue URL
  - For `recipe`: The recipe key (e.g., `refactor-to-standards`)
  - For `description`: Omit (no external reference)
- `--body-file PATH`: (optional, automated flows only) Absolute path to an existing file whose contents should become the request body. When provided, the script copies the file contents into the allocated stub atomically, replacing the two-step Write follow-up. Interactive flows driven by this skill use Step 5.2 instead.

**Note**: The skill handles template rendering and timestamps automatically. The stub returned by Step 5.1 already contains the metadata frontmatter — Step 5.2's `Write` replaces the body section only when the caller opts for the two-step pattern.

**After successful creation and body write**, log the artifact:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-1-init) Created request.md from {source_type}"
```

### Step 5b: Move Lesson File Into Plan Directory

**Applicability**: This step runs **only when `source == lesson`**. Skip entirely for `description`, `issue`, or `recipe` sources.

Convert the lesson into a plan-scoped artifact so the lesson file is moved out of the global lessons-learned directory and into the plan directory. This guarantees the lesson is owned by exactly one plan and prevents duplicate work across re-runs.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons convert-to-plan \
  --lesson-id {lesson_id} --plan-id {plan_id}
```

**Post-condition (MANDATORY)**: After the script returns, assert both of the following:

- `.plan/local/lessons-learned/{lesson_id}.md` MUST NOT exist (the source lesson file has been removed)
- `.plan/local/plans/{plan_id}/lesson-{lesson_id}.md` MUST exist (the lesson now lives inside the plan directory)

If either assertion fails, abort the phase immediately and return:

```toon
status: error
message: "Lesson convert post-condition failed"
lesson_id: {lesson_id}
```

Do not proceed to Step 6 unless both post-conditions hold.

### Step 5b.5: Seed plan_source with lesson_id

**Applicability**: This step runs **only when `source == lesson`**. Skip entirely for `description`, `issue`, or `recipe` sources.

Write the raw `lesson_id` value into `status.metadata.plan_source` so downstream phases can route lesson-derived plans to lesson-specific code paths (notably phase-2-refine Step 13.5's narrative-vs-code-validator activation guard, which fires whenever `plan_source` is set and is not the literal string `"recipe"`).

The literal value written is the raw lesson_id string (e.g., `2026-05-11-08-004`) — NOT a tag like `"lesson"`. This makes the originating lesson directly recoverable from status metadata and keeps the field's semantics aligned with the existing `recipe_key` pattern (raw id, not bucket label).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --set --plan-id {plan_id} \
  --field plan_source \
  --value {lesson_id}
```

Then emit a decision-log entry so the audit trail records the routing intent:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init) Seeded status.metadata.plan_source = {lesson_id} (lesson-derived plan)"
```

**Interaction with Step 5c-lesson (doc-shaped predicate)**: When Step 5c-lesson's doc-shaped predicate fires, it overwrites `plan_source` to the literal string `"recipe"` (and sets `recipe_key=lesson_cleanup`). That overwrite is intentional — doc-shaped lessons are routed through `recipe-lesson-cleanup` and must skip phase-2-refine Step 13.5. Code-shaped lessons retain the `lesson_id` value seeded here, which triggers Step 13.5's narrative-vs-code-validator on the next refine entry.

### Step 5c: Tier 1 Recipe-Match Routing

**Applicability**: The recipe-match scoring (Step 5c-recipe-match) and request-aspect classification (Step 5c-aspect) run for **every source other than `recipe`** (`description`, `lesson`, `issue`) — Tier 1 generalizes the former lesson-only matcher to the full recipe registry. When `source == recipe` the user has already chosen a recipe explicitly, so Tier 1 never overrides an explicit choice — skip Step 5c-recipe-match and Step 5c-aspect entirely. The lesson-only doc-shaped predicate (Step 5c-lesson) runs **only when `source == lesson`**.

This step is **Tier 1** of the routing model and is sequenced ahead of **Tier 2** planning-lane routing (Step 8b): recipe-match precedes the light/deep lane decision.

**Step 5c-recipe-match — registry-wide recipe scoring (deterministic, heuristic-first)**:

For any source other than `recipe`, score the request narrative against the live recipe registry. The request narrative is the body content resolved in Step 4 ("Get Task Content") — the description text, the lesson body, or the issue body — passed verbatim as `--request-text`. Do NOT inline-copy the recipe-match argument contract or the scoring threshold here; the enforcement-critical content lives in the central verb contract only — see [`../manage-config/SKILL.md`](../manage-config/SKILL.md) Canonical invocations → `recipe-match`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config recipe-match \
  --request-text "{request_narrative}"
```

Parse the returned TOON. The relevant fields are `matches[]` (ranked, each with `key`, `name`, `skill`, `confidence`), `top_match` (`key` + `confidence`), and `meets_auto_route_threshold`. An empty `matches` list means nothing cleared the minimum-confidence floor — log the no-match decision and continue to Step 5c-aspect (no routing).

The verb is **heuristic-first**: it performs no LLM call. The bounded LLM fallback for genuinely ambiguous matches is **orchestrator-driven** — it fires only when the heuristic result is ambiguous (e.g. two top matches with near-identical confidence below the auto-route threshold), preserving the zero-token property of the deterministic path. An always-on LLM router is explicitly NOT introduced.

**Read the auto-route gate** — `auto_route_recipe` (bool, default `true`) decides auto-route vs prompt, and `auto_route_recipe_threshold` (float, default `0.6`) is the confidence floor for auto-routing. Both are flat phase-1-init config knobs; their declaration and semantics live in the central config contract — see [`../manage-config/SKILL.md`](../manage-config/SKILL.md) Canonical invocations → `recipe-match` and the phase-1-init recipe-match knob table.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init get --field auto_route_recipe --audit-plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init get --field auto_route_recipe_threshold --audit-plan-id {plan_id}
```

**Routing decision** (only when `matches[]` is non-empty):

- **Auto-route** — when `auto_route_recipe == true` AND `top_match.confidence >= auto_route_recipe_threshold` (the `meets_auto_route_threshold` boolean already reflects the verb's own `--threshold`; gate on `auto_route_recipe_threshold` here for the config-driven floor): persist the matched recipe without prompting. Write `status.metadata.recipe_key = top_match.key`:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
    --set --plan-id {plan_id} \
    --field recipe_key \
    --value {top_match_key}
  ```

  Emit the auto-route decision-log entry:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-1-init) Tier 1 recipe-match auto-routed: recipe_key={top_match_key} (confidence={top_match_confidence} >= auto_route_recipe_threshold)"
  ```

- **Propose** — when `auto_route_recipe == false`, OR `top_match.confidence < auto_route_recipe_threshold` (a match exists but does not clear the auto-route floor): fire an `AskUserQuestion` natively at this site, enumerating each ranked match (`key`, `name`, `confidence`) as a selectable option plus a "No recipe" option:

  ```text
  AskUserQuestion:
    question: "This request may match a predefined recipe. Which should I use?"
    options:
      - label: "{match_1_name}" description: "confidence {match_1_confidence} — {match_1_key}"
      - label: "{match_2_name}" description: "confidence {match_2_confidence} — {match_2_key}"
      - label: "No recipe"      description: "Proceed with the standard refine/outline pipeline"
  ```

  Apply the choice in-context: on a recipe selection, persist `status.metadata.recipe_key = {selected_key}` (`manage-status metadata --set --plan-id {plan_id} --field recipe_key --value {selected_key}`); on "No recipe", persist nothing. Emit a decision-log entry recording the resolution:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-1-init) Tier 1 recipe-match proposed {match_count} matches below the auto-route floor — operator chose {selected_key|no_recipe}"
  ```

When `matches[]` is empty, log the no-match decision and skip routing:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init) Tier 1 recipe-match found no recipe above the confidence floor — proceeding with the standard refine/outline pipeline"
```

**Step 5c-aspect — request-aspect classification (deterministic, heuristic-first)**:

For any source other than `recipe`, classify the request aspect so the execution-manifest composer can drop build / quality-gate / test steps for analysis/planning requests. Pass the same request narrative verbatim. Do NOT inline-copy the aspect-classify threshold contract; it lives in the central verb contract — see [`../manage-config/SKILL.md`](../manage-config/SKILL.md) Canonical invocations → `aspect-classify` (its `0.7` threshold is independent of the recipe-match / auto-route thresholds — do not conflate them).

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config aspect-classify \
  --request-text "{request_narrative}"
```

Parse `aspect` (`analysis` | `planning` | `implementation`) and `drops_build_steps` from the returned TOON. Persist the resolved aspect into status metadata so the manifest composer (phase-4-plan) reads it when composing the phase-5 verification steps:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --set --plan-id {plan_id} \
  --field request_aspect \
  --value {aspect}
```

Emit the aspect decision-log entry:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init) Request aspect classified: {aspect} (drops_build_steps={drops_build_steps})"
```

The classifier defaults to `implementation` below its threshold — the safe fallback that keeps build/verify gates. No prompt is shown for the aspect; it is silent metadata.

**Step 5c-lesson — doc-shaped predicate (lesson-source only)**:

Inspect the lesson body (now at `.plan/local/plans/{plan_id}/lesson-{lesson_id}.md` after Step 5b) and decide whether to auto-suggest the `lesson_cleanup` recipe. The goal is to route doc-shaped lessons (small, prescriptive, no code refactor required) through `recipe-lesson-cleanup` so they get a slim surgical manifest instead of going through the full refine/outline/Q-Gate pipeline.

**Heuristic — "doc-shaped" predicate**:

A lesson body is doc-shaped when ALL of the following hold:

1. **No code-touching fences**: the body contains no fenced code blocks tagged with `python`, `py`, `java`, `js`, `javascript`, `ts`, or `typescript`. Markdown/text/bash fences (or no fences at all) are fine — those describe the directive, not new code.
2. **No primary code-action verb**: the first non-empty line of each `## Directive` (or `## Actions`) section does NOT begin (case-insensitive) with `test`, `refactor`, `implement`, `add code`, `write code`, or `migrate`. Verbs like `update`, `document`, `clarify`, `record`, `note`, `mention`, `link` are doc-shaped.
3. **Has at least one directive**: the body contains at least one `## Directive` or `## Actions` heading. A lesson with no directives cannot be auto-suggested — fall through to the normal flow so the user sees the empty-lesson case explicitly.

If ALL three conditions hold, set `plan_source=recipe` and `recipe_key=lesson_cleanup` in status metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --set --plan-id {plan_id} \
  --field plan_source \
  --value recipe
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --set --plan-id {plan_id} \
  --field recipe_key \
  --value lesson_cleanup
```

Emit the `Recipe auto-suggested` decision log entry:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init) Recipe auto-suggested: lesson_cleanup (lesson body is doc-shaped)"
```

**If ANY condition fails** — the lesson is code-shaped — do NOT set the metadata fields. Log the negative decision so the audit trail reflects that auto-suggest considered the lesson and declined:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init) Auto-suggest declined: lesson body is code-shaped — proceeding with full refine/outline pipeline"
```

**No prompt** — auto-suggest is silent metadata. The user can override on a subsequent run by passing `--recipe lesson_cleanup` (explicit) or by editing status metadata. The downstream phases read `plan_source` and `recipe_key` to decide whether to load the recipe path.

### Step 6: Initialize References

**IMPORTANT**: Get the branch name first, then pass it as a plain string. Do NOT use shell expansion `$(...)` in the command as it triggers permission prompts.

First, get the current branch:
```bash
git branch --show-current
```

Then create references with the branch value (domain is added after detection in Step 7):
```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references create \
  --plan-id {plan_id} \
  --branch {branch_name}
```

If issue source, also include:
```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references create \
  --plan-id {plan_id} \
  --branch {branch_name} \
  --issue-url {issue_url}
```

**Branch Strategy** — read `branch_strategy` and `use_worktree` from marshal.json phase-1-init config:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init get --audit-plan-id {plan_id}
```

Extract `branch_strategy` (default: `feature`) and `use_worktree` (default: `true`).

**IF `branch_strategy == "feature"`** (default — covers both `use_worktree == true` and `use_worktree == false`):

Phase-1-init persists only the `use_worktree` flag. It does NOT materialize the worktree or the feature branch: the feature branch is not checked out, the worktree directory is not created, and neither `worktree_branch` nor `worktree_path` is recorded. Phase-5-execute (see phase-5-execute Step 2.5) performs the actual `git worktree add` + branch checkout on first task execution, deriving the feature branch `feature/{plan_id}` and persisting both `worktree_branch` and the resolved `worktree_path` there. No on-disk side effects in this phase beyond `status.json` and `references.json` writes.

1. Update references.json with the intended feature branch name:
```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field branch \
  --value feature/{plan_id}
```

`references.base_branch` is the per-plan override — operators MAY override per-plan via `manage-references set --field base_branch` after init. Resolve `{resolved_base_branch}` by the following precedence.

**Precedence — operator `base_branch` init input wins.** When a `base_branch` init input was supplied to init (forwarded from the `/plan-marshall base_branch=` command parameter — see [`plan-marshall/workflow/planning.md`](../plan-marshall/workflow/planning.md) § Action: init → **1-Init Phase (inline)**), use it verbatim as `{resolved_base_branch}`, SKIP the `project.default_base_branch` read below, and set the base-branch source to `operator_param`. Otherwise apply the existing seed logic below.

The seed source is `project.default_base_branch` (project-level setting, populated by marshall-steward first-run wizard at Step 5a). Read the project's default base branch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  project get --field default_base_branch
```

Parse the `value` field and capture it as `{resolved_base_branch}` (base-branch source `project_default`). On `field_not_found` (legacy marshal.json that predates the `project.default_base_branch` field — the operator has not yet run `marshall-steward` to seed the new field), fall back to the current git branch (`{branch_name}` resolved from `git branch --show-current` above), preserving the legacy behaviour (base-branch source `git_fallback`). Otherwise use the `project.default_base_branch` value verbatim.

Out-of-scope reminder: aligning `_cmd_baseline_reconcile.py:_resolve_base_branch` (which currently reads from `marshal.json plan.phase-2-refine.base_branch`) to read from `references.json` is a separate plumbing concern, not part of this change.

Write the resolved value to `references.base_branch`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field base_branch \
  --value {resolved_base_branch}
```

2. **`use_worktree` was already consumed at Step 3a**: `metadata.use_worktree` is seeded by the `manage_status create` call in Step 3a (the sole writer of that field in phase-1-init), so nothing is carried forward here. The feature branch is NOT recorded here either — phase-5-execute derives `feature/{plan_id}` at materialization.

3. Log the decision:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-1-init) Recorded feature branch intent: feature/{plan_id} (base: {resolved_base_branch}, base_branch_source={operator_param|project_default|git_fallback}, use_worktree={use_worktree}) — materialization deferred to phase-5-execute Step 2.5"
```

4. **Current-checkout cwd directive for subsequent phases**: Emit the following Bucket A/B-aware instruction verbatim in the phase completion output (see Step 12). It reflects that materialization is deferred, so phases 2-4 run on the current branch / main checkout:

   > _"This plan currently runs on the main checkout / current branch. Worktree + feature-branch materialization is deferred to phase-5-execute Step 2.5; phases 2-4 operate against the current working tree. For `.plan/execute-script.py` calls, follow `plan-marshall:tools-script-executor/standards/cwd-policy.md`: `manage-*` scripts (Bucket A) are cwd-agnostic. Build / CI / Sonar scripts (Bucket B) identify the worktree via `--plan-id {plan_id}` (auto-resolves through `manage-status get-worktree-path` — returns the current checkout while `worktree_path` is unset, and switches to the materialized worktree once phase-5 creates it). Edit/Write/Read operations target the current working tree until phase-5-execute materializes the worktree."_

**IF `branch_strategy == "direct"`**: Keep current branch — no action needed. `use_worktree` is ignored in direct mode.

**Note — no drift-sync at init time**: Materialization is deferred, so no branch checkout, fetch, or rebase happens here. Baseline reconciliation against `origin/{base_branch}` happens at refine time (phase-2-refine Step 3d); phase-5-execute Step 3 is a fast-path "still clean?" check that performs no merge or rebase.

### Step 7: Detect Domain

Run the deterministic detector; on the ambiguous branch fire a native `AskUserQuestion` inline. There is no LLM dispatch on this code path — multi-match cases are genuinely human-input territory, resolved in-context.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  domain-detect --plan-id {plan_id} [--domain-override {domain}]
```

The script reads `request.md` (clarified_request → original_input fallback; lesson-{id}.md takes precedence when present), scans every configured non-system domain in `marshal.json` plus its bundle / skill aliases, and returns one of:

- **Single-domain auto-select** (`source=single_domain_configured`): only one non-system domain is configured → that domain wins regardless of narrative.
- **Unambiguous narrative match** (`source` = lesson body or request section): exactly one domain's alias set intersects the narrative tokens.
- **Explicit override** (`source=cli_override`): `--domain-override` resolved to a known domain.
- **Ambiguous** (`ambiguous: true`): multi-match OR zero-match. Do NOT auto-select. Fire a native `AskUserQuestion` at this site, offering the `candidates` list (when present) as the options:

  ```text
  AskUserQuestion:
    question: "The domain for this plan is ambiguous. Which domain applies?"
    options:
      - label: "{candidate_1}" description: "Detected candidate domain"
      - label: "{candidate_2}" description: "Detected candidate domain"
      # ... one option per candidate; when zero-match, offer the configured non-system domains
  ```

  Persist the operator's chosen domain in-context via Step 9's `manage-references set-list --field domains` and carry it forward as `{domain}` for the rest of the phase. On this branch the resolved domain comes from the operator's answer, not the detector.

**After resolving the domain** (any non-ambiguous branch), log the decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-1-init) Detected domain: {domain} - {reasoning}"
```

### Step 8: Resolve Session, Lane, Sibling & Posture

`status.json` was already created at Step 3a, so this step performs no create. It runs the remaining status-dependent resolutions in order: the session_id early-warning check (8a), the planning-lane routing (8b), the sibling-dedup collision gate (8c), and the execution-profile posture dialogue (8d).

### Step 8a: session_id Early-Warning Check

Verify that `status.metadata.session_id` was captured when `status.json` was created (Step 3a). The platform-runtime `SessionStart` hook (`session capture`) normally writes this field at plan-init time, but if the hook never ran or stored nothing, the gap stays invisible until phase-6-finalize aborts with an opaque hard-block. This sub-step surfaces the gap early — it does NOT abort init.

Read the field back:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field session_id
```

If `value` is empty OR the call returns `status: error`, emit a `[WARNING]` work-log entry noting the gap:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-1-init) session_id not captured at plan-init — phase-6-finalize will attempt a late session capture before its hard-block abort"
```

If `value` is present and non-empty, no log entry is required — continue to Step 8b. This check only surfaces the gap; it never aborts the phase and never renumbers existing steps.

### Step 8b: Route Planning Lane

Invoke the deterministic planning-lane router (D4) to resolve `planning_lane ∈ {light, deep}` and persist it into `status.metadata.planning_lane`. The router runs with **zero codebase discovery** — every signal is a cheap field read (`status.metadata`, `references.json`, a `request.md` regex) plus the `plan.phase-1-init.deep_lane` short-circuit. It reads the signal proxies available at init (`change_type` / `scope_estimate` may still be unset this early — the router treats an unknown signal as its deep-biasing default per the DQ1 signal set, biasing the first-pass routing conservatively toward deep; the light lane is confirmed once the orchestrator re-routes with the full signal set):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane route \
  --plan-id {plan_id} --persist
```

Parse `planning_lane` from the returned TOON (`light` or `deep`) and carry it into the Step 12 return TOON. The router emits its own decision-log line naming every signal value and the winning predicate, so no separate `manage-logging decision` call is required here. The orchestrator dispatches the planning pipeline structurally by lane — see [`plan-marshall/workflow/planning.md`](../plan-marshall/workflow/planning.md) for the lane-dispatch contract.

**Classification-validation gate (runs automatically inside `route`).** `planning-lane route` runs the deterministic classification-validation gate as a pre-route pass before resolving the lane. The gate cross-checks the plan's `change_type` and `scope_estimate` against cheap request signals and, on a mismatch, records a phase-1-init Q-Gate finding (against the `2-refine` phase). It is **flag-not-block** — it never changes the resolved lane and never halts initialization; a flagged mismatch only surfaces a finding the refine phase acts on. Two classes are flagged: `feature_as_bug_fix` (a `bug_fix` stamp over a non-ambiguous feature narrative) and `non_empty_affected_files_with_null_scope`. The `route` return carries the gate result under `classification_validation` (`mismatch_count`, `mismatches`, `findings_emitted`); no separate invocation is required at init. To run the gate standalone (e.g. a re-check after metadata changes), invoke `manage-status classification-validate --plan-id {plan_id}`.

See `manage-status` Canonical invocations → `planning-lane` and `manage-status` § `classification-validate` for the full subcommand contracts (signal table, the one-way escalate verb, the two mismatch classes, and the decision-log shape).

### Step 8c: Sibling-Dedup Collision Gate

Before the plan leaves init, check it against every concurrently-active sibling plan for a duplication collision. The same audit source fanning out across multiple plans, or two plans targeting the same files, is caught here — when it is cheapest to re-scope — rather than surfacing at finalize.

Run the deterministic, read-only collision verb. It is heuristic-free — no LLM dispatch, no writes — and mirrors `planning-lane route`'s zero-discovery cheap-read model:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status sibling-collision-check \
  --plan-id {plan_id}
```

Parse the returned TOON. The relevant fields are `collision_detected` (bool), `source_origin_matches[]` (each `{plan_id, source, source_id}` — a sibling backed by the same audit / lesson / issue `source_id`), and `file_overlap_matches[]` (each `{plan_id, overlap_count, overlapping_files}` — a sibling whose `references.json` `affected_files` intersect concrete paths named in this plan's `request.md` body). The two checks are ordered: source-origin is primary, file-overlap secondary. See `manage-status` § `sibling-collision-check` and `manage-status` Canonical invocations → `sibling-collision-check` for the full subcommand contract.

**No collision** (`collision_detected == false`): log the clean result and continue to Step 8d.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init) Sibling-collision check clean: no source-origin or file-overlap match against {active_sibling_count} active sibling(s)"
```

**Collision detected** (`collision_detected == true`): fire a native `AskUserQuestion` at this site and apply the choice in-context. Log the detection first:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING \
  --message "(plan-marshall:phase-1-init) Sibling-collision detected against {comma_separated_sibling_ids}"
```

```text
AskUserQuestion:
  question: "This plan collides with active sibling(s) {comma_separated_sibling_ids} ({collision_classes}). How should I proceed?"
  options:
    - label: "Proceed" description: "Accept the overlap — the sibling and this plan are intentionally distinct"
    - label: "Rename"  description: "Delete this plan and re-create it with updated source/files (and a new plan_id if needed)"
    - label: "Abort"   description: "This plan duplicates an active sibling — delete it and stop plan creation"
```

Apply the resolution in-context:

- **Proceed** — accept the overlap; continue init through Step 8d and Step 9 normally.
- **Rename** — delete this plan (`manage-status delete-plan --plan-id {plan_id}`) and restart init from Step 2 with updated source/files (and a new `plan_id` if needed) so the sibling-collision check passes.
- **Abort** — delete this plan (`manage-status delete-plan --plan-id {plan_id}`) and stop plan creation.

### Step 8d: Execution-Profile Posture Dialogue

Resolve the operator-facing execution-profile posture (`minimal` / `auto` / `full`) — the cost-visible lane decision (D9). This mirrors the Step 5c recipe-match prompt pattern (read knob → preview → AskUserQuestion → persist). Step 8b's `planning-lane route --persist` has already projected and persisted a recommended posture into `status.metadata.execution_profile`; this step shows the operator its consequences and lets them override it. The lane lattice, the class→default-tier table, and the posture decision rules are owned by [`../extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md) — do NOT inline-copy them here.

**Read the prompt gate** — `lane_selection` (`ask` | `auto`, default `ask`) decides whether to prompt or take the projection silently:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-1-init get --field lane_selection
```

**Resolve the three-posture preview** — call `lanes preview` for ONE TOON carrying every posture's resolved phase-6 step set, per-posture step counts, and summed `cost_size` token estimates. This is the SAME projection the phase-4 `compose` applies, so the dialogue preview cannot diverge from the executed flow:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest lanes preview \
  --plan-id {plan_id}
```

Parse `lanes.{minimal,auto,full}.phase_6_steps`, `phase_6_steps_count`, and `cost_sum_tokens`. The recipe lane seed (when Tier 1 recipe-match surfaced a `lane_seed` in Step 5c) is the lowest-precedence default — the recommended posture from Step 8b's projection already composes with it; an explicit operator choice here overrides both.

**When `lane_selection: ask`** — fire a native `AskUserQuestion` at this site. Step 8b's `planning-lane route --persist` has ALREADY persisted the projected posture into `status.metadata.execution_profile`, so the projection is the pre-selected default; the three options are the per-posture previews resolved from `lanes preview` above, each labeled with its concrete consequences (the kept/dropped step set and the summed token estimate):

```text
AskUserQuestion:
  question: "Which execution posture should this plan use? (recommended: {projected_posture})"
  options:
    - label: "full"    description: "{full_count} steps · ≈{full_tokens} tok — full security audit + retrospectives"
    - label: "auto"    description: "{auto_count} steps · ≈{auto_tokens} tok — skips sonar / lessons-housekeeping"
    - label: "minimal" description: "{minimal_count} steps · ≈{minimal_tokens} tok — no security audit, no retrospectives; appropriate for docs / mechanical changes"
```

Persist the operator's choice in-context, overwriting Step 8b's projection:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --set --plan-id {plan_id} --field execution_profile --value {chosen_posture}
```

Emit one decision-log line recording the resolution:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init) Execution-profile posture: {chosen_posture} (projected={projected_posture}, lane_selection=ask)"
```

**Surgical-class recommendation.** When the classified request fits the **surgical class** — narrow scope with concrete anchors, the same narrow-and-concrete predicate `project_profile_pure` applies in [`../manage-status/scripts/_cmd_planning_lane.py`](../manage-status/scripts/_cmd_planning_lane.py) — AND Step 5c auto-routed no recipe, the recommended (pre-selected) posture is `minimal` rather than `auto`. This is not a separate computation here: Step 8b's `planning-lane route --persist` already projected `minimal` for the surgical class via `project_profile_pure` and persisted it into `status.metadata.execution_profile`, so the pre-selected recommendation IS that projection. When Step 5c DID auto-route a recipe, the recipe's `lane_seed` supplies the lowest-precedence default instead (per the recipe-lane-seed note above), so the surgical-class `minimal` pre-selection applies only in the no-recipe case. **Operator override wins** — the pre-selection is only the default surfaced in the prompt; the operator's explicit posture choice overrides it and is persisted above. The lane lattice and the class→default-tier table stay owned by [`../extension-api/standards/ext-point-lane-element.md`](../extension-api/standards/ext-point-lane-element.md) and are not restated here.

**When `lane_selection: auto`** — take the projection silently. Step 8b already persisted the projected posture into `status.metadata.execution_profile`; do NOT prompt. Emit one decision-log line recording the silent projection:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init) Execution-profile posture: {projected_posture} (lane_selection=auto, silent projection — no prompt)"
```

**Manifest timing.** The persisted posture is consumed by the phase-4 Step 7b `compose`, which resolves the lane-pruned `execution.toon` with the firm `change_type` / `affected_files` signals — see [`../manage-execution-manifest/standards/decision-rules.md`](../manage-execution-manifest/standards/decision-rules.md) § "Execution-profile lane resolution" (twice-compose timing) and `manage-execution-manifest` Canonical invocations → `compose`. The `lanes preview` projection shown here and that composed manifest share one resolver, so the preview cannot diverge from the executed finalize flow; the posture is fixed here and never re-prompted at phase-4.

### Step 9: Store Domains in References

Store the detected domain(s) in references.json:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set-list \
  --plan-id {plan_id} \
  --field domains \
  --values {domain}
```

**Ambiguous-domain case**: when Step 7 resolved `ambiguous: true`, the operator's chosen domain (from the inline `AskUserQuestion`) is the `{domain}` stored here — this write is the persistence point for that choice. Every non-ambiguous branch stores the detector-resolved domain here as normal.

Project-level settings (compatibility, commit_and_push, branch_strategy, verification steps, finalize steps) are read directly from `marshal.json` by each phase skill at runtime.

### Step 10: Log Creation

Log the plan creation as an artifact:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-1-init) Created plan: {derived_title} (source: {source_type}, domain: {domain})"
```

### Step 11: Transition Phase

The phase transitions from init → refine after configuration completes:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id {plan_id} \
  --completed 1-init
```

**After successful transition**, log phase completion:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-1-init) Init phase complete - plan created with {domain} domain"
```

**Add visual separator** after END log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```

### Step 12: Complete Init and Yield to the Refine Phase

Init runs inline in the orchestrator context, so there is no dispatched-leaf return envelope. Any applicable operator prompts have already fired natively at their sites (Step 3 `action: exists`, Step 4b.3 obsolescence, Step 5c recipe-match propose, Step 7 ambiguous domain, Step 8c sibling collision, Step 8d posture — several are branch-dependent and do not fire on every run), and their resolutions were applied and persisted in-context. Init has persisted `request.md`, `status.json`, and `references.json`, and the orchestrator now holds the resolved values needed to dispatch phase-2-refine.

The values carried forward into the orchestrator context are:

```toon
status: success
plan_id: {plan_id}
domain: {domain}
next_phase: 2-refine
use_worktree: {true|false}
planning_lane: {light|deep}

source:
  type: {description|lesson|issue|recipe}
  id: {source_id}

artifacts:
  request_md: request.md
  status: status.json
  references: references.json
```

`domain` is the domain persisted at Step 9 (from the detector, or from the operator's inline `AskUserQuestion` answer on the ambiguous branch — never `unresolved`, since the prompt resolved it in-context). `planning_lane` is the value resolved by Step 8b's `manage-status planning-lane route`; the orchestrator dispatches the planning pipeline by this lane. The `recipe_key`, `request_aspect`, and `execution_profile` metadata resolved inline are already persisted to `status.metadata`, so no return block re-carries them.

**Current-checkout cwd directive.** Phases 2-4 run on the current working tree because worktree materialization is deferred to phase-5-execute Step 2.5. Carry the Step 6 point 4 directive forward so the orchestrating LLM decides, per call, whether a `.plan/execute-script.py` invocation is Bucket A (cwd-agnostic, no routing flags) or Bucket B (pass `--plan-id {plan_id}`, which auto-resolves the current working tree now and the materialized worktree once phase-5 creates it).

---

## Output

Init runs inline, so it does not return a dispatched-agent envelope — Step 12 (above) is the single source of truth for the values it yields into the orchestrator context. The orchestrator's post-init contract assertion checks that init produced a `plan_id` + `domain` and no rogue source-mutation signal (`pr_url` / `branch` / files-patched); a short human-readable completion summary of the shape `"plan {plan_id} created, domain {domain}"` (e.g. `"plan 2026-05-11-15-007 created, domain plan-marshall"`) is the natural rendering for logs.

All values (`plan_id`, `domain`, `next_phase`, `use_worktree`, `planning_lane`, `source`, `artifacts`) are documented in Step 12 above. Any applicable operator prompts fire inline at their step sites and their resolutions are persisted in-context — there are no prompt-required return blocks.

---

## Error Handling

On any error, **first log the error** to work-log (if plan directory exists):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-1-init) {error_type}: {full error context and message}"
```

### Invalid Lesson ID

```toon
status: error
error: invalid_lesson
message: Lesson not found: {lesson_id}
recovery: Check lesson ID with manage-lessons list
```

### Invalid Issue

```toon
status: error
error: invalid_issue
message: Issue not found or inaccessible: {issue}
recovery: Verify URL, check permissions
```

### Existing Plan (Not Resumed)

```toon
status: error
error: plan_exists
message: Plan already exists: {plan_id}
recovery: Use --plan-id to specify different ID, or resume existing
```

### Phantom Plan ID (Step 2b Guard)

Raised by **Step 2b: Plan-ID Derivation Guard** when the final derived `plan_id`
matches a lesson-ID shape (`YYYY-MM-DD-HH-NNN`) or an agent-id shape (UUID,
bare hex string of 12 or more characters such as `aa82aa78f2414dc79`, or
`execution-context` / `agent-` token). This is a **contract violation on the
lesson-conversion dispatch side** — a lesson-ID or the dispatched agent's own id
leaked into the plan-id slot, which would otherwise create a phantom plan
directory keyed by that token while the intended lesson is never converted. The
guard fires before Step 3, so no plan directory exists yet and the work-log emit
above is skipped.

```toon
status: error
error: phantom_plan_id
plan_id: {derived_plan_id}
detected_shape: lesson_id | agent_id
message: Derived plan_id '{derived_plan_id}' matches a {detected_shape} shape — a lesson-ID or agent-id leaked into the plan-id slot. Refusing to create a phantom plan directory.
recovery: Re-dispatch init with an explicit --plan-id (a kebab-case slug), or fix the lesson-conversion call that passed the {detected_shape} as the plan_id.
```

The orchestrator's post-init contract assertion (`plan-marshall:plan-marshall/workflow/planning.md` § Action: init → **Post-init contract assertion**) treats this `error: phantom_plan_id` return as a hard failure and refuses to advance to phase-2-refine, surfacing the violation to the lesson-conversion caller.

---

## Integration

### Orchestrator Integration

This skill runs **inline in the orchestrator context** — the orchestrator (`plan-marshall/workflow/planning.md` § Action: init and § Action: lessons convert, and `recipe.md` Step 2) executes these steps directly, completing the full init phase in-context and firing every operator prompt natively via `AskUserQuestion`. It is not dispatched as an `execution-context` workflow body.

### Command Integration

- **/plan-marshall action=init** - Orchestrates the init phase inline

### Related Skills

- **solution-outline** - Next phase after init completes (outline phase)
- **Domain skills** - Loaded by thin agents via marshal.json skill_domains (resolved at runtime)

### Phase-boundary metric bookkeeping

Apart from the Step 3b bootstrap `start-phase` call, this skill does not invoke
`manage-metrics` — phase boundary metric recording happens in the orchestrator
(`plan-marshall:plan-marshall` workflows). Because init runs inline (no agent
`<usage>` envelope), when the orchestrator transitions out of `1-init` it MUST
use the fused `manage-metrics phase-boundary --prev-phase 1-init --next-phase
2-refine` call with the `<usage>`-derived flags (`--total-tokens` /
`--duration-ms` / `--tool-uses`) OMITTED — the inline-phase (timestamps-only)
recording mode. See `manage-metrics` Canonical invocations → `phase-boundary`
for the API. `1-init` is the only phase that self-records its
own `start_time` (Step 3b); all other phases inherit it from the prior fused
`phase-boundary` call.

---

## Templates

| Template | Purpose |
|----------|---------|
| `templates/request.md` | request.md file format |

