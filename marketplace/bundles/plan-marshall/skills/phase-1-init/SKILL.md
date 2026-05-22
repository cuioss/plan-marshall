---
name: phase-1-init
description: Init phase skill. Creates plan directory, request.md, references, and status. Complete initialization in a single agent call.
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Phase Init Skill

**Role**: Complete init phase. Creates plan directory, request.md, detects domain, and creates configuration. Single-agent initialization pattern.

**Key Pattern**: Complete initialization. Creates request.md, status.json, and references.json (with domains). Does NOT create goals (that's the refine phase via decompose).

**CRITICAL**: This skill is part of the **plan-marshall workflow system**, NOT the host platform's built-in plan mode. Ignore any system-reminders about platform-managed plan paths or built-in plan-mode tools.

## Foundational Practices

```
Skill: plan-marshall:dev-agent-behavior-rules
```

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: Follow workflow steps sequentially. Each step that invokes a script has an explicit bash code block.

**Prohibited actions:**
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never skip the phase transition — use `manage-status transition`
- Never improvise script subcommands — use only those documented below

**Constraints:**
- Strictly comply with all rules from dev-agent-behavior-rules, especially tool usage and workflow step discipline

## Dispatched workflows vs inline steps

This phase dispatches under one role key: **`phase-1-init`** (flat — single workflow). Step 4b reference verification bundles into the `phase-1-init` envelope (it shares the same `manage-architecture` / `manage-references` context the rest of the phase needs). Mechanical sub-procedures stay inline as scripts: Step 5c lesson auto-suggest uses `manage-lessons:lesson-auto-suggest` (heuristic-first, dispatches the existing lesson-cleanup workflow only when ambiguous); Step 6 references initialisation and Step 7 domain detection (`manage-config:domain-detect`) are pure scripts. For the rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 2 (Heuristic 1 — script over dispatch).

## When to Activate This Skill

Activate when:
- Starting a new plan (no existing plan_id)
- User provides task via description, lesson_id, or issue URL
- Dispatched via `plan-marshall:execution-context-{level}` with `workflow: plan-marshall:phase-1-init/SKILL.md`

---

## Phase-Entry Worktree Assertion

Phase 1-init has no preceding phase, so the Phase Entry Protocol's `phase_handshake verify` step is skipped (per [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#q-gate-check-phases-2-6) Q-Gate / handshake checks are scoped to phases 2-6). The worktree-materialization contract is deferred: phase-1-init persists only the *intent* — `metadata.use_worktree` and `metadata.worktree_branch` — into `status.json`. It does NOT create the worktree directory and does NOT write `metadata.worktree_path` (that field stays absent until phase-5-execute materializes the worktree on first task execution; see phase-5-execute Step 2.5). The writer-chain contract for this phase is therefore narrower: Step 6 holds `use_worktree` and `worktree_branch` in orchestrator context, Step 8's `manage_status create` writes that pair atomically, and `worktree_path` is written later by phase-5-execute. Downstream phase-handshake assertions tolerate the absent `worktree_path` until phase-5 materialization.

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
- From recipe: `recipe-{recipe_key}` (e.g., `recipe-refactor-to-standards`).
- Description, issue, and recipe rules: always kebab-case, max 50 chars.

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
  python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons delete \
    --lesson-id {lesson_id}
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

```
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

**Interaction with Step 5c (auto-suggest)**: When Step 5c's doc-shaped predicate fires, it overwrites `plan_source` to the literal string `"recipe"` (and sets `recipe_key=lesson_cleanup`). That overwrite is intentional — doc-shaped lessons are routed through `recipe-lesson-cleanup` and must skip phase-2-refine Step 13.5. Code-shaped lessons retain the `lesson_id` value seeded here, which triggers Step 13.5's narrative-vs-code-validator on the next refine entry.

### Step 5c: Lesson Auto-Suggest Recipe

**Applicability**: This step runs **only when `source == lesson`**. Skip entirely for `description`, `issue`, or `recipe` sources. (When `source == recipe`, the user has already chosen a recipe explicitly — auto-suggest never overrides an explicit choice.)

**Step 5c-pre — registry-wide auto-suggest (deterministic, no envelope)**:

For any source other than `recipe`, optionally run the registry matcher to surface candidate recipes:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons \
  auto-suggest --plan-id {plan_id}
```

The script scans the live recipe registry, blends keyword overlap with domain/scope alignment, and returns the top 3 recipes ordered by confidence. Each suggestion is also written as an info-severity Q-Gate finding so the orchestrator can surface the list in the audit log. When `suggestions[0].confidence` clears the auto-accept floor (caller-side, typically 0.7) the orchestrator MAY persist `status.metadata.recipe_key = suggestions[0].key` without prompting; below that floor the list is surfaced for user selection (no auto-persist).

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

Phase-1-init persists only the *intent* to use a worktree / feature branch. It does NOT materialize either: the feature branch is not checked out, the worktree directory is not created, and `references.worktree_path` is not set. Materialization is deferred to phase-5-execute (see phase-5-execute Step 2.5), which performs the actual `git worktree add` + branch checkout on first task execution. Deferred materialization in effect — no on-disk side effects in this phase beyond `status.json` and `references.json` writes.

1. Update references.json with the intended feature branch name and base branch:
```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field branch \
  --value feature/{plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field base_branch \
  --value {branch_name}
```

2. **Carry `use_worktree` and `worktree_branch` forward to Step 8**: hold the `use_worktree` flag (from marshal.json — `true` or `false`) and the literal feature branch name `feature/{plan_id}` in the orchestrator's local context and pass them as `--use-worktree` / `--no-use-worktree` and `--worktree-branch` flags into Step 8's `manage_status create` invocation. Do NOT pass `--worktree-path` — the path is unknown at this phase and is written by phase-5-execute when it materializes the worktree. Step 8 is the sole writer of `metadata.use_worktree` and `metadata.worktree_branch` in phase-1-init.

3. Log the decision:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-1-init) Recorded feature branch intent: feature/{plan_id} (base: {branch_name}, use_worktree={use_worktree}) — materialization deferred to phase-5-execute Step 2.5"
```

4. **Current-checkout cwd directive for subsequent phases**: Emit the following Bucket A/B-aware instruction verbatim in the phase completion output (see Step 12). It reflects that materialization is deferred, so phases 2-4 run on the current branch / main checkout:

   > _"This plan currently runs on the main checkout / current branch. Worktree + feature-branch materialization is deferred to phase-5-execute Step 2.5; phases 2-4 operate against the current working tree. For `.plan/execute-script.py` calls, follow `plan-marshall:tools-script-executor/standards/cwd-policy.md`: `manage-*` scripts (Bucket A) are cwd-agnostic. Build / CI / Sonar scripts (Bucket B) identify the worktree via `--plan-id {plan_id}` (auto-resolves through `manage-status get-worktree-path` — returns the current checkout while `worktree_path` is unset, and switches to the materialized worktree once phase-5 creates it). Edit/Write/Read operations target the current working tree until phase-5-execute materializes the worktree."_

**IF `branch_strategy == "direct"`**: Keep current branch — no action needed. `use_worktree` is ignored in direct mode.

**Note — no drift-sync at init time**: Materialization is deferred, so no branch checkout, fetch, or rebase happens here. When phase-5-execute Step 2.5 materializes the worktree and feature branch, it handles drift-sync against `origin/{base_branch}` per the `rebase_on_execute_start` config (default `true`).

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

Create status.json with phases (6-phase model). When Step 6 recorded worktree intent (the `branch_strategy == "feature" AND use_worktree == true` branch ran), pass the intent pair as flags so `metadata.use_worktree` and `metadata.worktree_branch` are seeded atomically. `--worktree-path` is omitted — the path is unknown until phase-5-execute Step 2.5 materializes the worktree.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id {plan_id} \
  --title "{title_from_task_md}" \
  --phases 1-init,2-refine,3-outline,4-plan,5-execute,6-finalize \
  --use-worktree \
  --worktree-branch feature/{plan_id}
```

When Step 6 did NOT record worktree intent (the `use_worktree == false` opt-out branch, or the `branch_strategy == "direct"` branch), omit the worktree flags so `manage_status create` writes the explicit `metadata.use_worktree=false` marker:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id {plan_id} \
  --title "{title_from_task_md}" \
  --phases 1-init,2-refine,3-outline,4-plan,5-execute,6-finalize
```

**Note**: Domain information is stored in `references.json` (as a `domains` list), not in `status.json`. All plans use the standard 6-phase model (verification is integrated into phase-5-execute).

**Writer-chain contract**: `manage_status create` is the sole writer of `metadata.use_worktree` and `metadata.worktree_branch` in phase-1-init; `metadata.worktree_path` is never written by this phase. Phase-5-execute Step 2.5 is the sole writer of `metadata.worktree_path` (it materializes the worktree on first task execution and persists the resolved absolute path then). The inverse-direction `_worktree_orphan` invariant in `_invariants.py` (registered in `INVARIANTS`) tolerates an absent `worktree_path` until phase-5 materialization. See `workflow-integration-git/standards/worktree-handling.md` for the canonical worktree contract.

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

If `value` is present and non-empty, no log entry is required — continue to Step 9. This check only surfaces the gap; it never aborts the phase and never renumbers existing steps.

### Step 9: Store Domains in References

Store the detected domain(s) in references.json:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set-list \
  --plan-id {plan_id} \
  --field domains \
  --values {domain}
```

Project-level settings (compatibility, commit_strategy, branch_strategy, verification steps, finalize steps) are read directly from `marshal.json` by each phase skill at runtime.

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
worktree_branch: {feature/{plan_id}|null}

source:
  type: {description|lesson|issue}
  id: {source_id}

artifacts:
  request_md: request.md
  status: status.json
  references: references.json
```

**Always append the current-checkout cwd directive from Step 6 point 4 verbatim after the TOON output.** Phases 2-4 run on the current working tree because worktree materialization is deferred to phase-5-execute Step 2.5. The orchestrating LLM uses the directive to decide, per call, whether a `.plan/execute-script.py` invocation is Bucket A (cwd-agnostic, no routing flags) or Bucket B (pass `--plan-id {plan_id}`, which auto-resolves the current working tree now and the materialized worktree once phase-5 creates it).

---

## Output

Step 12 (above) is the single source of truth for the return TOON. The summary of the contract — the two fields every workflow doc that implements `ext-point-execution-context-workflow` MUST return — is:

```toon
status: success | error
display_detail: "<plan {plan_id} created, domain {domain}>"
```

`display_detail` shape on success: `"plan {plan_id} created, domain {domain}"` (e.g. `"plan 2026-05-11-15-007 created, domain plan-marshall"`); ≤80 chars, ASCII, no trailing period. On error, `display_detail` carries the short error label (see § Error Handling for the structured envelope).

All other fields (`plan_id`, `domain`, `next_phase`, `use_worktree`, `worktree_branch`, `source`, `artifacts`) are documented in Step 12 above and form the rest of the return payload.

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

This skill does not invoke `manage-metrics` itself — phase boundary metric
recording happens in the orchestrator (`plan-marshall:plan-marshall`
workflows). When the orchestrator transitions out of `1-init`, it MUST use
the fused `manage-metrics phase-boundary --prev-phase 1-init --next-phase
2-refine` call. See
`marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` §
`phase-boundary` for the API.

---

## Templates

| Template | Purpose |
|----------|---------|
| `templates/request.md` | request.md file format |

