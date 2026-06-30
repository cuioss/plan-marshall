---
name: phase-1-init
description: Init phase skill. Creates plan directory, request.md, references, and status, runs the Tier 1 recipe-match routing tier (registry-wide recipe scoring + request-aspect classification) ahead of planning-lane routing. Complete initialization in a single agent call.
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Phase Init Skill

**Role**: Complete init phase. Creates plan directory, request.md, detects domain, and creates configuration. Single-agent initialization pattern.

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
- **Never write or edit source files outside `.plan/local/plans/{plan_id}/**`.** Phase-1-init's contract is plan-structure creation only (request.md, references.json, status.json under the plan directory). Even when the task description is detailed — naming specific files, functions, or paths — that is request material to record verbatim in `request.md`, NOT a directive to implement: the more prescriptive and implementation-ready the `content`, the stronger (and more wrong) the pull to "just do it." Source edits against `marketplace/bundles/**`, production code, or test fixtures are the responsibility of phase-5-execute task bodies, never phase-1-init. The recurring anti-pattern is phase-1-init reaching for `Edit` / `Write` against a production path because the request narrative read like an implementation brief. **Return-contract obligation**: this phase's contract output is `plan_id` + `domains` (+ `next_phase`) and nothing else of substance. A return that omits `plan_id`, or carries a `pr_url`, a `branch`, or a "patched N files" detail, is a contract violation — the orchestrator's post-init assertion (`plan-marshall:plan-marshall/workflow/planning.md` § Action: init → **Post-init contract assertion**) treats any such signal as an error and refuses to advance to phase-2-refine.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline

## Dispatched workflows vs inline steps

This phase dispatches under one role key: **`phase-1-init`** (flat — single workflow). Step 4b reference verification bundles into the `phase-1-init` envelope (it shares the same `manage-architecture` / `manage-references` context the rest of the phase needs). Mechanical sub-procedures stay inline as scripts: Step 5c recipe-match (Tier 1) is registry-wide for every source — it calls `manage-config recipe-match` and `manage-config aspect-classify` (heuristic-first, zero LLM call inside the scripts; the bounded LLM fallback for ambiguous matches is orchestrator-driven and fires only when the heuristic is ambiguous, preserving the zero-token property), and retains the lesson-only doc-shaped predicate path; Step 6 references initialization and Step 7 domain detection (`manage-config:domain-detect`) are pure scripts. Tier 1 recipe-match (Step 5c) is sequenced ahead of Tier 2 planning-lane routing (Step 8b). For the rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 2 (Heuristic 1 — script over dispatch).

## When to Activate This Skill

Activate when:
- Starting a new plan (no existing plan_id)
- User provides task via description, lesson_id, or issue URL
- Dispatched via `plan-marshall:execution-context-{level}` with `workflow: plan-marshall:phase-1-init/SKILL.md`

---

## Phase-Entry Worktree Assertion

Phase 1-init has no preceding phase, so the Phase Entry Protocol's `phase_handshake verify` step is skipped (per [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#q-gate-check-phases-2-6) Q-Gate / handshake checks are scoped to phases 2-6). Phase-1-init persists only `metadata.use_worktree` into `status.json`. It does NOT create the worktree directory, and it records neither the feature branch nor a `worktree_path`: phase-5-execute Step 2.5 creates the worktree on first task execution, derives the feature branch `feature/{plan_id}`, and back-fills both `metadata.worktree_branch` and the resolved `metadata.worktree_path` at that point. The writer-chain detail lives in Step 8's **Writer-chain contract**.

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
- `action: created` - New plan directory was created, log phase start and continue to Step 4
- `action: exists` - Plan already exists, prompt user

**On successful creation**, log the phase start (directory now exists):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-1-init) Starting init phase"
```

### Step 3a: Seed Metrics Start-Time

Immediately after Step 3 creates the plan directory and emits the `[STATUS] Starting init phase` log line, self-record `1-init.start_time` so the downstream fused `phase-boundary --prev-phase 1-init --next-phase 2-refine` call in `plan-marshall/workflow/planning.md` sees a real start timestamp rather than falling back to the structural `status.json.created` backfill:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics \
  start-phase --plan-id {plan_id} --phase 1-init
```

**Rationale**: Bootstrap phase has no preceding `phase-boundary` call to stamp `start_time` (the call requires a `plan_id`, which doesn't exist until Step 3 returns). Recording the start as early as the plan directory permits makes the subsequent fused `phase-boundary --prev-phase 1-init` call (in `plan-marshall/workflow/planning.md`) compute a wall duration that bounds the agent's `<usage>` duration — restoring the `Worked <= Wall` invariant. The `_read_status_created` backfill in `manage-metrics.py` is a safety net for plans materialised under older orchestrator versions; the start-time recorded here is authoritative for current plans.

If `action: exists`, use AskUserQuestion:
- **Resume**: Continue with existing plan (skip to Step 9 with existing data)
- **Replace**: Delete existing plan and create new (see below)
- **Rename**: Ask for new plan_id and re-run from Step 2

**Replace Flow** (see `standards/plan-overwrite.md` for details):

1. Delete the existing plan:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status delete-plan \
  --plan-id {plan_id}
```

2. Re-run create-or-reference (should now return `action: created`):
```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files create-or-reference \
  --plan-id {plan_id}
```

3. Log the replacement (directory now exists for logging):
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ACTION] (plan-marshall:phase-1-init) Replaced existing plan - deleted previous version"
```

4. Continue with Step 4 (Get Task Content)

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

**Sub-step 4b.3 — Surface obsolescence to the user**:

If ANY reference is stale, present the obsolescence report to the user via `AskUserQuestion` using the 3-option menu defined in `lesson-source-premise-check.md`:

1. **Refine** — adapt the lesson scope to the current code surface and continue with a clarifying note attached.
2. **Close as resolved** — the lesson describes a problem that no longer exists; delete the lesson and abort plan creation.
3. **Residual scope** — keep only the references that are still valid; drop the stale ones and continue.

If ALL references verify cleanly, log the success and continue to Step 5 — no prompt is shown.

**Sub-step 4b.4 — Persist the decision**:

For every branch (including the all-clean branch), emit a decision-log entry with the `(plan-marshall:phase-1-init:source-premise)` prefix:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init:source-premise) {decision_summary}"
```

Where `{decision_summary}` is one of:

- `All N references verified — no obsolescence detected.`
- `User chose refine — attaching obsolescence report (N stale of M total) as clarifying note.`
- `User chose close-as-resolved — lesson {lesson_id} deleted, aborting plan creation.`
- `User chose residual-scope — dropping N stale references, continuing with M-N valid references.`

**Sub-step 4b.5 — Branch-specific actions**:

- **Refine branch**: Append the obsolescence report (a short bulleted markdown section listing each stale reference plus its evidence) to the body content that Step 5.2 will write into request.md. The report MUST appear under a `## Pre-flight Reference Verification` heading so downstream phases see it as part of the request scope. Continue to Step 5.
- **Close-as-resolved branch**: Delete the lesson and abort plan creation:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
    --lesson-id {lesson_id} --reason "Closed as resolved during phase-1-init premise check"
  ```

  Then return the close-out TOON without proceeding to Step 5:

  ```toon
  status: aborted
  reason: lesson_already_resolved
  plan_id: {plan_id}
  lesson_id: {lesson_id}
  message: "Lesson deleted; plan creation aborted because every cited reference is obsolete."
  ```

- **Residual-scope branch**: Record each dropped reference via a separate work-log entry so downstream phases can audit which scope items were removed:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level INFO \
    --message "[ARTIFACT] (plan-marshall:phase-1-init:source-premise) Dropped stale reference: {reference} ({evidence})"
  ```

  Then continue to Step 5 with the reduced reference set.

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

- **Propose** — when `auto_route_recipe == false`, OR `top_match.confidence < auto_route_recipe_threshold` (a match exists but does not clear the auto-route floor): surface the ranked `matches[]` to the user via `AskUserQuestion`. Offer each match (`name` + `confidence`) as a selectable option plus a "No recipe — proceed with the standard refine/outline pipeline" option. On a recipe selection, persist `status.metadata.recipe_key = {selected_key}` via the same `manage-status metadata` call above; on the no-recipe option, persist nothing. Emit a decision-log entry recording the user's choice:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-1-init) Tier 1 recipe-match proposed {match_count} matches; user selected: {selection}"
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

`references.base_branch` is the per-plan override — operators MAY override per-plan via `manage-references set --field base_branch` after init. The seed source is `project.default_base_branch` (project-level setting, populated by marshall-steward first-run wizard at Step 5a). Read the project's default base branch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  project get --field default_base_branch
```

Parse the `value` field and capture it as `{project_base_branch}`. On `field_not_found` (legacy marshal.json that predates the `project.default_base_branch` field — the operator has not yet run `marshall-steward` to seed the new field), fall back to the current git branch (`{branch_name}` resolved from `git branch --show-current` above), preserving the legacy behaviour. Otherwise use `{project_base_branch}` verbatim.

Out-of-scope reminder: aligning `_cmd_baseline_reconcile.py:_resolve_base_branch` (which currently reads from `marshal.json plan.phase-2-refine.base_branch`) to read from `references.json` is a separate plumbing concern, not part of this change.

Write the resolved value to `references.base_branch`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field base_branch \
  --value {project_base_branch}
```

2. **Carry `use_worktree` forward to Step 8**: hold the `use_worktree` flag (from marshal.json — `true` or `false`) in the orchestrator's local context and pass it as `--use-worktree` (or omit for the opt-out) into Step 8's `manage_status create` invocation. The feature branch is NOT recorded here — phase-5-execute derives `feature/{plan_id}` at materialization. Step 8 is the sole writer of `metadata.use_worktree` in phase-1-init.

3. Log the decision:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-1-init) Recorded feature branch intent: feature/{plan_id} (base: {project_base_branch}, use_worktree={use_worktree}) — materialization deferred to phase-5-execute Step 2.5"
```

4. **Current-checkout cwd directive for subsequent phases**: Emit the following Bucket A/B-aware instruction verbatim in the phase completion output (see Step 12). It reflects that materialization is deferred, so phases 2-4 run on the current branch / main checkout:

   > _"This plan currently runs on the main checkout / current branch. Worktree + feature-branch materialization is deferred to phase-5-execute Step 2.5; phases 2-4 operate against the current working tree. For `.plan/execute-script.py` calls, follow `plan-marshall:tools-script-executor/standards/cwd-policy.md`: `manage-*` scripts (Bucket A) are cwd-agnostic. Build / CI / Sonar scripts (Bucket B) identify the worktree via `--plan-id {plan_id}` (auto-resolves through `manage-status get-worktree-path` — returns the current checkout while `worktree_path` is unset, and switches to the materialized worktree once phase-5 creates it). Edit/Write/Read operations target the current working tree until phase-5-execute materializes the worktree."_

**IF `branch_strategy == "direct"`**: Keep current branch — no action needed. `use_worktree` is ignored in direct mode.

**Note — no drift-sync at init time**: Materialization is deferred, so no branch checkout, fetch, or rebase happens here. Baseline reconciliation against `origin/{base_branch}` happens at refine time (phase-2-refine Step 3d); phase-5-execute Step 3 is a fast-path "still clean?" check that performs no merge or rebase.

### Step 7: Detect Domain

Run the deterministic detector; only raise `AskUserQuestion` on the ambiguous branch. There is no LLM dispatch on this code path — multi-match cases are genuinely human-input territory.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  domain-detect --plan-id {plan_id} [--domain-override {domain}]
```

The script reads `request.md` (clarified_request → original_input fallback; lesson-{id}.md takes precedence when present), scans every configured non-system domain in `marshal.json` plus its bundle / skill aliases, and returns one of:

- **Single-domain auto-select** (`source=single_domain_configured`): only one non-system domain is configured → that domain wins regardless of narrative.
- **Unambiguous narrative match** (`source` = lesson body or request section): exactly one domain's alias set intersects the narrative tokens.
- **Explicit override** (`source=cli_override`): `--domain-override` resolved to a known domain.
- **Ambiguous** (`ambiguous: true`): multi-match OR zero-match. The caller MUST raise `AskUserQuestion` with the `candidates` list (when present) so the user picks the right domain; no auto-selection in this branch.

**After resolving the domain**, log the decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-1-init) Detected domain: {domain} - {reasoning}"
```

### Step 8: Create Status

Create status.json with phases (6-phase model). When Step 6 recorded worktree intent (the `branch_strategy == "feature" AND use_worktree == true` branch ran), pass `--use-worktree` so `metadata.use_worktree: true` is seeded. No branch or path flag is passed — phase-5-execute Step 2.5 derives `feature/{plan_id}` and persists `worktree_branch` / `worktree_path` at materialization.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id {plan_id} \
  --title "{title_from_task_md}" \
  --phases 1-init,2-refine,3-outline,4-plan,5-execute,6-finalize \
  --use-worktree
```

When Step 6 did NOT record worktree intent (the `use_worktree == false` opt-out branch, or the `branch_strategy == "direct"` branch), omit the `--use-worktree` flag so `manage_status create` writes the explicit `metadata.use_worktree=false` marker:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id {plan_id} \
  --title "{title_from_task_md}" \
  --phases 1-init,2-refine,3-outline,4-plan,5-execute,6-finalize
```

**Note**: Domain information is stored in `references.json` (as a `domains` list), not in `status.json`. All plans use the standard 6-phase model (verification is integrated into phase-5-execute).

**Writer-chain contract**: `manage_status create` is the sole writer of `metadata.use_worktree` in phase-1-init — it writes neither `metadata.worktree_branch` nor `metadata.worktree_path`. Phase-5-execute Step 2.5 is the sole writer of both `metadata.worktree_branch` (derived as `feature/{plan_id}`) and the resolved `metadata.worktree_path` absolute value: it materializes the worktree on first task execution and persists both then. See `workflow-integration-git/standards/worktree-handling.md` for the canonical worktree contract.

### Step 8a: session_id Early-Warning Check

Immediately after `manage_status create` writes `status.json`, verify that `status.metadata.session_id` was captured. The platform-runtime `SessionStart` hook (`session capture`) normally writes this field at plan-init time, but if the hook never ran or stored nothing, the gap stays invisible until phase-6-finalize aborts with an opaque hard-block. This sub-step surfaces the gap early — it does NOT abort init.

Read the field back:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
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

**No collision** (`collision_detected == false`): log the clean result and continue to Step 9.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-1-init) Sibling-collision check clean: no source-origin or file-overlap match against {active_sibling_count} active sibling(s)"
```

**Collision detected** (`collision_detected == true`): surface the init-time collision gate to the user via `AskUserQuestion`, naming the colliding sibling plan ids and the collision class(es). Offer exactly three options:

- **Proceed** — accept the overlap and continue with this plan as-is (the sibling and this plan are intentionally distinct despite the shared source / files). Continue to Step 9.
- **Rename** — delete this plan, then restart init with updated source/files (and a new `--plan-id` if needed) so the sibling-collision check passes. Delete via `manage-status delete-plan --plan-id {plan_id}` (mirroring the Step 3 Replace flow), then restart from Step 2.
- **Abort** — this plan duplicates an already-active sibling and should not exist; delete it and stop plan creation. Delete via `manage-status delete-plan --plan-id {plan_id}` and return the abort TOON below without proceeding to Step 9.

Record the user's choice to the decision log (substitute `{decision_summary}` with the chosen option and the matched sibling ids):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING \
  --message "(plan-marshall:phase-1-init) Sibling-collision gate: {decision_summary}"
```

On the **Abort** branch, after deleting the plan, return:

```toon
status: aborted
reason: sibling_collision
plan_id: {plan_id}
colliding_siblings: {comma_separated_sibling_ids}
message: "Plan deleted; creation aborted because it duplicates an already-active sibling plan."
```

### Step 9: Store Domains in References

Store the detected domain(s) in references.json:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set-list \
  --plan-id {plan_id} \
  --field domains \
  --values {domain}
```

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

### Step 12: Return Result

**Output**:

```toon
status: success
plan_id: {plan_id}
domain: {domain}
next_phase: 2-refine
use_worktree: {true|false}
planning_lane: {light|deep}

source:
  type: {description|lesson|issue}
  id: {source_id}

artifacts:
  request_md: request.md
  status: status.json
  references: references.json
```

`planning_lane` is the value resolved by Step 8b's `manage-status planning-lane route`. The orchestrator dispatches the planning pipeline by this lane.

**Always append the current-checkout cwd directive from Step 6 point 4 verbatim after the TOON output.** Phases 2-4 run on the current working tree because worktree materialization is deferred to phase-5-execute Step 2.5. The orchestrating LLM uses the directive to decide, per call, whether a `.plan/execute-script.py` invocation is Bucket A (cwd-agnostic, no routing flags) or Bucket B (pass `--plan-id {plan_id}`, which auto-resolves the current working tree now and the materialized worktree once phase-5 creates it).

---

## Output

Step 12 (above) is the single source of truth for the return TOON. The summary of the contract — the two fields every workflow doc that implements `ext-point-execution-context-workflow` MUST return — is:

```toon
status: success | error
display_detail: "<plan {plan_id} created, domain {domain}>"
```

`display_detail` shape on success: `"plan {plan_id} created, domain {domain}"` (e.g. `"plan 2026-05-11-15-007 created, domain plan-marshall"`); ≤80 chars, ASCII, no trailing period. On error, `display_detail` carries the short error label (see § Error Handling for the structured envelope).

All other fields (`plan_id`, `domain`, `next_phase`, `use_worktree`, `planning_lane`, `source`, `artifacts`) are documented in Step 12 above and form the rest of the return payload.

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

### Agent Integration

This skill is dispatched as the workflow body of `plan-marshall:execution-context-{level}` with `workflow: plan-marshall:phase-1-init/SKILL.md`. The dispatched agent completes the full init phase in a single call.

### Command Integration

- **/plan-marshall action=init** - Orchestrates the init agent

### Related Skills

- **solution-outline** - Next phase after init completes (outline phase)
- **Domain skills** - Loaded by thin agents via marshal.json skill_domains (resolved at runtime)

### Phase-boundary metric bookkeeping

Apart from the Step 3a bootstrap `start-phase` call, this skill does not invoke
`manage-metrics` — phase boundary metric recording happens in the orchestrator
(`plan-marshall:plan-marshall` workflows). When the orchestrator transitions
out of `1-init`, it MUST use the fused `manage-metrics phase-boundary
--prev-phase 1-init --next-phase 2-refine` call. See
`marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` §
`phase-boundary` for the API. `1-init` is the only phase that self-records its
own `start_time` (Step 3a); all other phases inherit it from the prior fused
`phase-boundary` call.

---

## Templates

| Template | Purpose |
|----------|---------|
| `templates/request.md` | request.md file format |

