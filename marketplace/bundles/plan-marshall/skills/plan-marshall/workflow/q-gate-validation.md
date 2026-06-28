---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Q-Gate Validation Workflow

Verify solution outline deliverables against request intent and assessments — catch false positives, missing coverage, and scope drift. Dispatched under `--phase phase-N` (no `--role`) — q-gate-validation tracks the calling phase's default level via the bubbling resolver.

Three call sites: phase-2-refine lesson-derived narrative validation (Step 13.5), phase-3-outline outline-time Q-Gate (Complex Track Step 11) and phase-4-plan plan-time Q-Gate (Step 9b). Each call site activates a different validator subset via runtime `activation_context` / `validators` parameters; the workflow body stays shared and the dispatch passes only `--phase phase-N` so the level tracks whatever the caller phase configures.

## Role boundaries

This workflow is a SPECIALIST for Q-Gate verification only. When dispatched, execute the steps below immediately — do NOT describe or summarize this document.

Stay in your lane:
- Do NOT create outlines (that's `phase-3-outline` skill).
- Do NOT create tasks (that's `phase-4-plan` skill).
- Verify deliverables by executing the workflow steps below.

## Inputs

```toon
plan_id: {plan_id}
WORKTREE: {repo-relative-path}
```

Skills the caller MUST forward in `skills[]`: `plan-marshall:manage-solution-outline`, `plan-marshall:manage-findings`, `plan-marshall:manage-plan-documents`, `plan-marshall:manage-status`, `plan-marshall:manage-architecture`, `plan-marshall:manage-logging`.

**Worktree binding**: every grep, file-existence check, Read/Write/Edit, and shell command issued below MUST resolve against the `WORKTREE` value provided by the orchestrator, never the main checkout. Do NOT re-resolve via `manage-status get-worktree-path` — the orchestrator did that once before dispatch.

## Workflow

### Step 2: Log Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (execution-context.q-gate-validation) Starting"
```

### Step 3: Load Context from Sinks

#### 1.1 Read Solution Outline

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline read \
  --plan-id {plan_id} \
  --audit-plan-id {plan_id}
```

Parse the deliverables from the solution outline. Extract:
- Deliverable numbers and titles
- Affected files per deliverable
- Metadata (change_type, domain, module)

#### 1.2 Read Assessments

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment \
  list --plan-id {plan_id} --certainty CERTAIN_INCLUDE
```

Parse to get the list of files that were assessed as CERTAIN_INCLUDE.

**CRITICAL: Deduplicate by file_path** — If multiple assessments exist for the same `file_path` (from agent retries or re-runs), use only the assessment with the **latest timestamp**. Discard earlier assessments for the same file. This prevents stale assessments from prior runs causing false missing-coverage flags.

#### 1.3 Read Request

Read request (clarified_request falls back to original_input automatically):

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request read \
  --plan-id {plan_id} \
  --section clarified_request \
  --audit-plan-id {plan_id}
```

#### 1.4 Log Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(execution-context.q-gate-validation) Starting verification: {deliverable_count} deliverables, {assessment_count} assessments" \
  --audit-plan-id {plan_id}
```

---

### Step 3.5: Per-Deliverable Content-Hash Skip on Re-validation (FIX 4-lite)

> **HARD DEPENDENCY on FIX 3 (the Step 4 full-coverage guarantee)**: this skip is only safe because the full-coverage guarantee ensures that any *prior* full validation pass already ran AND recorded EVERY applicable validator against each deliverable. Therefore "deliverable D has zero pending findings after the prior full pass" reliably means "D passed everything" — not merely "D passed the validators that happened to run before a short-circuit". If FIX 3's guarantee is ever removed, this skip becomes unsound and MUST be removed with it.

This step lets a re-entry (the orchestrator's auto-loop re-dispatches q-gate-validation after a re-outline) SKIP the full validator battery for deliverables that are both **unchanged** and **clean**, so untouched deliverables are not re-validated wholesale. The skip is **deliverable-level**, NOT validator-level — there is no edit→invalidation dependency map; a deliverable is either fully re-validated or fully skipped.

**On entry — read the prior content-hash artifact** (a small plan-scoped TOON file persisted by this same step on the previous pass; absent on the first pass):

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
  --plan-id {plan_id} --file work/deliverable-hashes.toon
```

Parse the prior `hashes[]{deliverable,hash}` rows into a `stored_hash(D)` lookup. When the file does not exist (first pass / `exists: false`), treat `stored_hash(D)` as empty for every deliverable — nothing is skipped on the first pass.

**Per-deliverable skip predicate** — for each deliverable D parsed from solution_outline.md (Step 3 §1.1), compute `hash(D)` over D's current deliverable text (the full markdown block from its `### {N}.` heading through the line before the next deliverable heading; SHA-256 of the UTF-8 bytes, hex digest). Then query D's pending findings — pending = recorded but not yet resolved:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate list \
  --plan-id {plan_id} --phase {phase} --resolution pending
```

Filter the returned rows to those whose finding targets deliverable D (by deliverable number / affected-file membership). Then apply the skip predicate exactly:

> **SKIP full re-validation of D iff `hash(D) == stored_hash(D)` AND D has zero pending findings.** Otherwise (hash changed, OR D has ≥1 pending finding, OR D is new / has no stored hash) D is **fully re-validated** in Step 4.

When D is skipped, log the decision and do NOT run any §2.x validator against D:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(execution-context.q-gate-validation:hash-skip) Skipped re-validation of deliverable {N}: content hash unchanged and zero pending findings" \
  --audit-plan-id {plan_id}
```

**After the Step 4 pass — write the current hash set back to the artifact** (covers both validated and skipped deliverables, so the next re-entry has a complete fingerprint set). Author the TOON body via the Write tool to a plan-id-scoped `.plan/temp/{plan_id}/` file (scoping the path to `{plan_id}` prevents collisions under concurrent plan execution), then persist it through `manage-files write` (never assemble multi-line content inside a shell argument):

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write \
  --plan-id {plan_id} --file work/deliverable-hashes.toon --content-file {temp_hashes_file}
```

The artifact uses existing `manage-files` read/write I/O only — **no validator-result cache subsystem and no new script surface are introduced**. The persisted fingerprint is per-deliverable content only; it carries no validator-result state.

---

### Step 4: Verify Deliverables

> **FULL-COVERAGE GUARANTEE (anti-short-circuit) — MANDATORY**: You MUST execute AND record findings from EVERY applicable validator (§2.1 through §2.17, scoped to the active phase's validator subset) before returning — even when an error-level / blocking finding is already present. Do NOT stop at the first failing validator class. Encountering a blocking §2.17 finding does NOT permit skipping a later §2.12 under-coverage warning: run the remaining applicable validators and record their findings in the SAME pass. The goal is that a single validation pass surfaces ALL finding classes at once, collapsing what would otherwise be N sequential re-validation round-trips (one per finding class discovered) into 1. **This full-coverage guarantee is the precondition that FIX 4-lite (per-deliverable content-hash skip) relies on**: "zero pending findings for deliverable D after a full pass" is only a trustworthy "D passed everything" signal because this guarantee ensures every applicable validator actually ran and recorded against D.

For each deliverable in solution_outline.md that was NOT skipped by [Step 3.5](#step-35-per-deliverable-content-hash-skip-on-re-validation-fix-4-lite) (unchanged-and-clean deliverables are skipped wholesale on re-entry), run every applicable validator (do not short-circuit on the first failure):

#### 2.1 Request Alignment Check

Does the deliverable directly address a request requirement?

**Pass criteria**:
- Deliverable description maps to specific request intent
- Affected files are relevant to the request

**Fail criteria**:
- Deliverable scope doesn't match any request requirement
- Files seem unrelated to request intent

#### 2.2 Assessment Coverage Check

Are all affected files in the deliverable backed by assessments?

```text
FOR each file in deliverable.affected_files:
  IF file NOT IN assessed_files (CERTAIN_INCLUDE):
    FLAG: Missing assessment for file
```

**Pass criteria**:
- Every affected file has a CERTAIN_INCLUDE assessment

**Fail criteria**:
- Files in deliverable without corresponding assessment

#### 2.3 False Positive Check

Verify files in the deliverable should actually be modified:

**Criteria to check**:
- **Output Ownership**: Does the file produce the content in question, or just document it?
- **Consumer vs Producer**: Is the file a consumer or producer of the relevant content?
- **Duplicate Detection**: Is the same logical change already covered elsewhere?

#### 2.4 Architecture Constraints Check

Does the deliverable respect domain architecture?

**Pass criteria**:
- Module is valid for the domain
- Change type is appropriate for the files

#### 2.5 File Existence Validation

Verify every path in `Affected files` exists on disk (except for `verification` profile deliverables where affected files may be empty).

```bash
ls {file_path}
```

**Pass criteria**:
- Every listed file exists on disk
- OR deliverable has `change_type: feature` and file is explicitly marked as "to be created"

**Fail criteria**:
- File path does not exist and deliverable is not creating it
- Path structure doesn't match project conventions (e.g., flat `test/bundle/test_foo.py` when actual layout uses subdirectories `test/bundle/skill-name/test_foo.py`)

**FLAG**: `"File not found: {path} in deliverable {N}"` — include the actual file listing from the parent directory to help identify the correct path.

#### 2.6 Profile Overlap Detection

Check for redundant test coverage across deliverables. A separate test deliverable is redundant when other deliverables already have `module_testing` profile covering the same test files.

```text
FOR each deliverable D with profile=module_testing AND change_type != verification:
  FOR each file F in D.affected_files:
    FOR each OTHER deliverable D2 where D2.profiles contains module_testing:
      IF F would be the test file for any source file in D2.affected_files:
        FLAG: "Profile overlap: {F} in deliverable {D.number} already covered by deliverable {D2.number}'s module_testing profile"
```

**Heuristic for matching test files to source files**: A test file under `test/{bundle}/{skill-name}/test_foo.py` corresponds to a source file named `foo.py` inside that skill's script subdirectory. If a deliverable has `module_testing` profile and its source files have corresponding test files that appear in another deliverable, flag the overlap.

**Pass criteria**:
- No deliverable's test files overlap with another deliverable's module_testing scope

**Fail criteria**:
- A dedicated test deliverable covers files already implied by module_testing profiles on other deliverables

#### 2.7 Log Verification Result

For each deliverable:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(execution-context.q-gate-validation:qgate) Deliverable {N}: {pass|fail} - {reason}" \
  --audit-plan-id {plan_id}
```

#### 2.8 Downstream Consumer Check

Detect downstream consumers of a skill that is being deleted but that remain hard-coded elsewhere in the repo. A deletion deliverable that lists every file under a skill directory still fails in practice when pytest `conftest.py` files, test path references, script notations, or `Skill:` directives continue to point at the deleted paths — the failure surfaces only during a holistic `module-tests` run, long after the outline should have self-corrected.

**Activation condition**: Runs only when the deliverable's `affected_files` contains at least one path matching `marketplace/bundles/*/skills/{name}/**` or `.claude/skills/{name}/**` AND the deliverable is a deletion (detected via `change_type: tech_debt` OR explicit deletion language in the deliverable's `Change per file` field, e.g., "delete", "remove", "drop", `git rm`). If neither condition is met, skip this check and continue to the next deliverable.

**Per-skill-directory loop**: For each deleted skill directory inferred from `affected_files`, derive:
- `{skill_dir}` — the root skill directory, e.g., `.claude/skills/{name}` or `marketplace/bundles/plan-marshall/skills/phase-3-outline`
- `{bundle}` — the bundle segment when the path is under `marketplace/bundles/{bundle}/skills/`, otherwise empty
- `{skill_name}` — the final path segment of `{skill_dir}`

Execute the four greps below against the worktree root. Each grep must be a separate Bash call (one command per call).

Pattern A — `importlib` / `spec_from_file_location` loads pointing inside the deleted skill directory (pytest conftest loaders):

```bash
rg -n "spec_from_file_location\\([^)]*\\b{skill_name}\\b" --type py test/
```

Pattern B — relative path references to `.claude/skills/{skill_name}/` or `marketplace/bundles/{bundle}/skills/{skill_name}/` anywhere under `test/` (excluding caches):

```bash
rg -n "{skill_dir}\\b" test/ --glob '!**/__pycache__/**'
```

Pattern C — three-part script notations `{bundle}:{skill_name}:` referring to the deleted skill in `marshal.json`, plan scripts, and the executor mapping:

```bash
rg -n "{bundle}:\\b{skill_name}\\b:" marshal.json .plan/
```

Pattern D — `Skill: {bundle}:{skill_name}` loader directives in markdown (SKILL.md, agent.md, command.md):

```bash
rg -n "^Skill:\\s*{bundle}:{skill_name}\\b" marketplace/ .claude/
```

**Suppression rule**: For each grep match, extract `{consumer_path}` (the file containing the match). The match is resolved (no finding emitted) when `{consumer_path}` appears in EITHER:
- the same deletion deliverable's `affected_files` list (indicating the consumer is co-deleted or updated in this deliverable), OR
- any other deliverable's `affected_files` list in the same `solution_outline.md` (indicating a sibling deliverable removes or updates the consumer)

Only emit findings for unresolved matches.

**Pass criteria**: Every grep returns no matches, OR every match is resolved per the suppression rule above.

**Fail criteria**: At least one grep match references `{skill_dir}` and its `{consumer_path}` is not listed in any deliverable's `affected_files`.

**FLAG format** — For each unresolved match, record a blocking Q-Gate finding:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 3-outline --source qgate --type triage \
  --title "Q-Gate: Downstream consumer for deletion of {skill_dir}" \
  --detail "{pattern_letter}-{pattern_name} match at {consumer_path}:{line} references deleted skill {skill_dir} but is not listed in any deliverable's affected files. Outline must either add {consumer_path} to the deletion deliverable's affected files or include a follow-up deliverable that removes/updates it." \
  --file-path "{consumer_path}" \
  --audit-plan-id {plan_id}
```

**Worked example**: A deletion deliverable lists every file under `.claude/skills/{name}/` for removal. Pattern A run against the worktree produces `test/{name}/conftest.py:12` loading `scripts/{some-script}.py` via `spec_from_file_location`. `test/{name}/` is not listed as an affected file of any deliverable in the outline, so the suppression rule does not apply and a Q-Gate finding is emitted — blocking phase-3-outline until the outline adds `test/{name}/` to the deletion deliverable (or adds a follow-up deliverable that removes it). Without this check, the orphaned conftest survives the outline and the failure surfaces only later, as a `FileNotFoundError` at pytest collection time during a holistic `module-tests` run.

#### 2.9 Consumer Sweep Completeness Check

Verify that deliverables which delete or rename a public symbol have enumerated every cross-bundle consumer in `Affected files`. This check enforces the outline-time consumer sweep documented in [`consumer-sweep.md`](../../phase-3-outline/standards/consumer-sweep.md) at Q-Gate time, catching deliverables that skipped the sweep or applied it incompletely.

**Trigger condition** — Activates when the deliverable's `Change per file`, `Refactoring`, or title text matches the same delete/rename heuristic from `consumer-sweep.md` § 1 applied to a public symbol:

| Pattern class | Match indicators |
|---------------|------------------|
| Delete language | `delete`, `remove`, `drop`, `git rm`, `eliminate`, `purge` |
| Rename language | `rename`, `replaced by`, `migrate from X to Y`, `renamed to` |
| Replacement language | `replace X with Y`, `swap X for Y` (when X is a public module-level symbol) |

The trigger applies only to module-level public symbols (top-level functions, classes, constants, exported skill notations, `Skill:` loader directives). It does NOT fire for local variables, private symbols (leading `_`), file-level renames that do not change a public symbol, or documentation-only edits.

**Extraction**: When the trigger fires, extract the affected public symbol(s) from the deliverable text. For function-level renames like "replace `load_derived_data` with `iter_modules`", extract the old symbol (`load_derived_data`) — that is the symbol whose consumers must appear in `Affected files`.

**Sweep at Q-Gate time** — Re-run the consumer-sweep grep step against the worktree to materialize the expected consumer set:

```bash
grep -rn "{symbol}" marketplace/bundles/
```

Each grep is a separate Bash invocation (one command per call). Collect every `{consumer_path}` from the matches, discard `__pycache__` paths, and discard the symbol's own owning module file (which is in scope by definition).

**Failure modes**:

**(a) Trigger language present AND `Affected files` is empty**:

```text
FAIL with finding:
  title: "Q-Gate: consumer_sweep_completeness — empty affected_files for delete/rename deliverable {N}"
  detail: "Deliverable {N} deletes/renames public symbol {symbol} but lists no Affected files. The consumer sweep documented in consumer-sweep.md is mandatory for delete/rename deliverables. Re-run the sweep and enumerate every consumer."
```

**(b) Trigger language present AND every entry in `Affected files` is under the same bundle as the symbol's owning module (no cross-bundle entries) AND the worktree grep would return cross-bundle hits**:

```text
FAIL with finding (one per unenumerated consumer):
  title: "Q-Gate: consumer_sweep_completeness — unenumerated cross-bundle consumer of {symbol} in deliverable {N}"
  detail: "Deliverable {N} deletes/renames {symbol} but Affected files only references the owning bundle. Cross-bundle consumer at {consumer_path}:{line} would break when {symbol} is removed. Add {consumer_path} to Affected files (with explicit migration text in Change per file) or add a follow-up deliverable that updates it."
  file_path: "{consumer_path}"
```

The owning-bundle determination uses the `marketplace/bundles/{bundle}/` path segment of the symbol's first match. Same-bundle entries in `Affected files` are sufficient when ALL grep matches are under that same bundle — cross-bundle hits trigger the failure.

**Pass criteria** (silent — no finding emitted):
- Trigger language is absent (deliverable does not delete or rename a public symbol), OR
- Trigger language is present AND `Affected files` includes at least one cross-bundle consumer that matches the worktree grep results, OR
- Trigger language is present AND the worktree grep returns no cross-bundle hits (the deletion is genuinely contained within the owning bundle).

**FLAG format** — For each unenumerated cross-bundle consumer (failure mode b), record one finding via `manage-findings qgate add`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 3-outline --source qgate --type triage \
  --title "Q-Gate: consumer_sweep_completeness — unenumerated cross-bundle consumer of {symbol} in deliverable {N}" \
  --detail "Deliverable {N} deletes/renames {symbol} but Affected files does not include {consumer_path}:{line}. Re-run the consumer sweep documented in consumer-sweep.md and enumerate every cross-bundle consumer." \
  --file-path "{consumer_path}" \
  --audit-plan-id {plan_id}
```

For failure mode (a) — empty `Affected files` — emit a single finding without `--file-path`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 3-outline --source qgate --type triage \
  --title "Q-Gate: consumer_sweep_completeness — empty affected_files for delete/rename deliverable {N}" \
  --detail "Deliverable {N} deletes/renames public symbol {symbol} but lists no Affected files. The consumer sweep documented in consumer-sweep.md is mandatory for delete/rename deliverables." \
  --audit-plan-id {plan_id}
```

**Cross-references**:
- [`consumer-sweep.md`](../../phase-3-outline/standards/consumer-sweep.md) — outline-time procedure this check enforces

#### 2.10 Argparse Validator

Verify that every `python3 .plan/execute-script.py {notation} {subcommand} [args...]` invocation embedded in `solution_outline.md` references a subcommand and flag set that exist in the target script's live `argparse` declaration. Catches stale or invented CLI shapes at design time, before phase-5-execute attempts the verification command and finds the flags do not exist.

**Activation condition**: Runs in the `3-outline` phase context. Activates whenever `solution_outline.md` contains at least one `python3 .plan/execute-script.py` invocation in any `Verification` block, `Change per file` block, or inline reference.

**Detection logic**:

1. Parse every `python3 .plan/execute-script.py {notation} [{subcommand}] [args...]` invocation from `solution_outline.md`. Extract `{notation}`, `{subcommand}` (when present), and every `--flag` token.
2. For each unique `{notation}`, fetch the live argparse schema:
   ```bash
   python3 .plan/execute-script.py {notation} --help
   ```
3. For each invocation that supplies a subcommand, fetch the subcommand-level help:
   ```bash
   python3 .plan/execute-script.py {notation} {subcommand} --help
   ```
4. Diff the cited subcommand and flags against the parsed help output. A flag counts as **undeclared only when it is absent from BOTH the leaf subcommand help AND every ancestor parser in the notation's command chain, AND it is not an executor-stripped flag** — argparse resolves flags up the full parser chain, so a flag declared on a parent command (or at the top level) is valid even though it does not appear in the leaf subcommand's help. Before emitting an undeclared-flag finding, probe each ancestor parser's help along the command chain, from the leaf's parent up to the top-level notation. For a multi-level invocation such as `manage-config plan phase-2-refine get`, probe — in addition to the leaf help from step 3 — the intermediate parents and the top-level parser:
   ```text
   {notation} {subcommand_prefix}   (help)
   {notation}                       (help)
   ```
   That chain expands to the phase-level, plan-level, and top-level help for the example notation. Additionally, the executor (`.plan/execute-script.py`) consumes and strips its own audit-plan-id flag BEFORE argv reaches the target script's argparse, so that flag appears in NO parser's help at any chain level yet is always valid — treat it (alongside any other executor-level flag) as a known non-finding regardless of the probe results. Emit a finding per undeclared subcommand and per flag that is missing from the leaf AND every ancestor parser AND is not an executor-stripped flag.

**Worked false-positive (full-chain resolution)**: Outline cites the invocation

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-2-refine get --field compatibility --audit-plan-id X
   ```

   A naive probe of only the leaf help shows only the field flag, so a leaf-only diff would emit a spurious undeclared-flag finding for the audit-plan-id flag. Two independent reasons make it valid. First, the audit-plan-id flag is an **executor-stripped flag** the executor removes before argparse ever sees it, so it never appears in any help output. Second, the analogous parent-chain case is a top-level flag declared on the `manage-architecture` notation rather than on its `resolve` leaf — probing only the leaf help would falsely flag a flag that the top-level help declares. In both cases: silent pass — no finding. A validator that probed only the leaf help would have produced a false positive.

**Finding emission template**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 3-outline \
  --source qgate --type triage \
  --title "Q-Gate: argparse_validator — undeclared {kind} '{token}' on {notation}" \
  --detail "solution_outline.md cites '{notation} {subcommand} {flag}' but live --help does not declare '{token}'. Either correct the cited shape, regenerate the executor (.plan/execute-script.py) if the notation was recently added, or fall back to a different verification command." \
  --audit-plan-id {plan_id}
```

`{kind}` is one of `subcommand`, `flag`. `{token}` is the offending text.

**Positive example**: Outline cites a call using notation `plan-marshall:manage-findings:manage-findings` with sub-verb `qgate filter --status pending` (invented verb `filter`; correct verb is `list`). Live help shows the subcommand list `{add,list,resolve,...}` — no `filter`. Validator emits one finding for the undeclared subcommand.

**Negative example**: Outline cites `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list --plan-id X`. Live help shows `list` is a registered subcommand and `--plan-id` is a registered flag. Silent pass — no finding.

**Rationale**: Verification commands embedded in `solution_outline.md` that reference non-existent subcommands or flags fail silently during phase-5-execute; catching the mismatch at design time avoids wasted execute iterations.

#### 2.11 Module-Mapping Validator

Verify that every `module_testing` profile task's declared test file lives in the same architecture module as the implementation file the deliverable's `implementation` profile task changes. Catches scope drift where the task author paired the right deliverable with the wrong test file (e.g., test sits in a sibling test module that pytest collects but exercises an unrelated production path).

**Activation condition**: Runs in the `4-plan` phase context. Activates for every task whose `profile` is `module_testing` AND whose deliverable also has an `implementation` profile task.

**Detection logic**:

1. For each `module_testing` task, enumerate its `step.target` test file paths.
2. Find the sibling `implementation` task for the same `deliverable` and enumerate its `step.target` implementation file paths.
3. For each pair `(test_file, impl_file)`, query architecture:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture which-module --path {test_file}
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture which-module --path {impl_file}
   ```
4. Compare the returned `module` values. If they differ, check whether both paths appear on the documented test→impl mapping list (project-local convention; absent means strict module match required). Emit a finding when modules differ AND no mapping entry covers the pair.

**Finding emission template**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 4-plan \
  --source qgate --type triage \
  --title "Q-Gate: module_mapping_validator — test/impl module mismatch for deliverable {N}" \
  --detail "module_testing task declares {test_file} (module: {test_module}) but sibling implementation task declares {impl_file} (module: {impl_module}). Test will pass without exercising the changed code path. Either re-target the test to the correct module's test directory, or document the mapping if the cross-module routing is intentional." \
  --audit-plan-id {plan_id}
```

**Positive example**: Deliverable D3's implementation task targets `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md` (module `plan-marshall`). Its module_testing sibling targets `test/pm-plugin-development/plugin-doctor/test_extension.py` (module `pm-plugin-development`). Validator emits finding — modules differ, no mapping entry.

**Negative example**: Deliverable D1's implementation targets `.../scripts/manage-tasks.py` (module `plan-marshall`). Its module_testing sibling targets `test/plan-marshall/manage-tasks/test_manage_tasks.py` (module `plan-marshall`). Silent pass — modules match.

**Rationale**: Pairing a module_testing task with a test file from a different architecture module means the test executes without exercising the changed production code path — a coverage gap that surfaces only as a missed regression, not a test failure.

#### 2.12 Scope-Criterion Validator

Verify that every deliverable's `success_criterion` is operationalized by a structured query whose result set is consistent with `affected_files`. Catches scope drift where the criterion implies a wider set of files than `affected_files` enumerates (under-coverage) or a narrower set than `affected_files` modifies (over-coverage). Distinct from Section 2.9 (consumer-sweep): 2.9 fires only on delete/rename language; this validator fires for every deliverable and covers sibling-set, find-pattern, and textual-grep criteria.

**Activation condition**: Runs in the `3-outline` and `4-plan` phase contexts. Activates for every deliverable whose `Success Criteria` block contains at least one criterion that references a code-shape (file pattern, sibling group, symbol signature, sibling enumeration, regex, etc.) — i.e., a criterion that can be operationalized as a structured query. Pure behavioral criteria ("plugin-doctor passes", "user can log in") do NOT activate the validator.

**Detection logic**:

1. For each deliverable, parse the `Success Criteria` block and extract operationalizable predicates. Map each predicate to a query type: `find_pattern` (symbol signature), `sibling_group` (e.g., `change-*.md`), `marketplace_grep` (textual pattern across bundles), or `directory_enum` (every file under a path).
2. Run the query against the worktree:
   - `find_pattern` → `architecture find --pattern {signature}`
   - `sibling_group` → architecture or directory enumeration
   - `marketplace_grep` → `grep -rn {pattern} marketplace/bundles/`
   - `directory_enum` → `architecture files --module {module}` filtered by path prefix
3. Compute the symmetric difference between the query result set and `affected_files`:
   - Files in query result but missing from `affected_files` → under-coverage
   - Files in `affected_files` but absent from query result → over-coverage (possibly intentional; flag as warning)
4. When the criterion implies marketplace-wide coverage (e.g., deleting or renaming a shared public symbol), the query MUST sweep all bundles. Bundle-scoped queries on marketplace-wide criteria emit an under-coverage finding for each consumer in a different bundle.

**Finding emission template**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase {phase} \
  --source qgate --type triage \
  --title "Q-Gate: scope_criterion_validator — {direction} for deliverable {N}" \
  --detail "Success criterion '{criterion_text}' operationalized as {query_type} returns {N_results} files. Affected files lists {N_affected}. {direction_detail}: {missing_or_extra_files}. Either expand affected_files to cover the query result, narrow the success criterion to the bundle/module actually in scope, or document the deliberate exclusion." \
  --audit-plan-id {plan_id}
```

`{direction}` is one of `under_coverage`, `over_coverage`. `{phase}` is `3-outline` or `4-plan`.

**Positive example**: Deliverable's success criterion is "all `change-*.md` standards updated" but `affected_files` lists 3 of the 4 sibling files in the directory. Validator runs `architecture files --module plan-marshall` filtered by `change-*.md`, finds 4 results, computes diff, emits under-coverage finding for the missing sibling.

**Negative example**: Deliverable's success criterion is "user can authenticate via JWT" — a behavioral criterion not operationalizable as a structured query. Silent pass — validator does not activate.

**Rationale**: A `success_criterion` whose operationalized query returns a different file set than `affected_files` indicates either under-coverage (files the plan will leave un-migrated) or over-coverage (files the criterion implies but the plan does not intend to touch). Either mismatch is a scope-specification error caught cheaply at outline time.

#### 2.13 Tier-Delta Validator

Verify that any tiered or variant-based specification in `solution_outline.md` (Tier 0 / Tier 1, Simple Track / Complex Track, fast-path / slow-path) is accompanied by a delta table that contrasts every field that differs across tiers, with an explicit rationale for each delta. Catches cross-tier rationale drift where one tier's `MUST NOT` is silently violated by another tier's `MUST`.

**Activation condition**: Runs in the `3-outline` phase context. Activates when `solution_outline.md` introduces tiered or variant-based content. Detection heuristics (any one match suffices):
- Section pairs whose titles match `Tier 0` / `Tier 1`, `Simple Track` / `Complex Track`, `fast-path` / `slow-path`, `tier-A` / `tier-B`.
- Two or more sibling sections whose headings differ only by an enumerated qualifier (`Profile X` / `Profile Y`, `Variant 1` / `Variant 2`).
- LLM-judged fallback: a section that opens with "MUST NOT do X — rationale: …" while a sibling section under a different qualifier label specifies X without acknowledging the rationale.

**Detection logic**:

1. Identify the tier sections via the heuristics above.
2. Enumerate every field/property/behavior described in each tier (commit-message body fields, return-shape keys, command flags, etc.).
3. Compute the cross-tier delta: which fields differ across tiers, and whether the outline contains a delta table that lists each delta with rationale.
4. Emit a finding when tiers are present but a delta table is absent OR the table is incomplete (omits one or more deltas).

**Finding emission template**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 3-outline \
  --source qgate --type triage \
  --title "Q-Gate: tier_delta_validator — missing/incomplete delta table for tiered spec '{tier_label}'" \
  --detail "solution_outline.md introduces tiered specs ({tier_a} vs {tier_b}) but {missing_or_incomplete}. Cross-tier rationale drift survives outline → plan → execute → tests and is only caught by reviewers reading both sections side-by-side. Add a delta table listing every field that differs across tiers along with the rationale for each delta." \
  --audit-plan-id {plan_id}
```

`{missing_or_incomplete}` is one of `the outline contains no delta table`, `the delta table omits the following fields: {field_list}`.

**Positive example**: Outline introduces "Tier 0 (small/trivial path)" and "Tier 1 (full path)" sections for commit-message format. Tier 0 explicitly states "MUST NOT embed `affected_modules_csv` in the commit body — the field is volatile, derivable, and adds noise". Tier 1 specifies the commit body with `affected_modules_csv` embedded. No delta table acknowledges the contradiction. Validator emits finding.

**Negative example**: Outline contains a single, untiered specification with no variant labels. Silent pass — validator does not activate.

**Rationale**: A tiered specification without a delta table allows cross-tier contradictions (e.g., one tier's explicit `MUST NOT` silently overridden by another tier's `MUST`) to survive outline → plan → execute undetected, surfacing only during implementation or review.

#### 2.14 Narrative-vs-Code Validator

Verify, for lesson-derived plans, that every concrete code claim in the source lesson narrative (file path, profile→target mapping, function name, argument shape, behavioral assertion) matches the current code state. Catches silent baseline drift between lesson capture and plan execution: lessons authored at one point in time may describe code that has since been renamed, refactored, or removed, and treating the narrative as authoritative produces no-ops or regressions.

**Activation condition**: Runs in the `2-refine` phase context. Activates when `status.json` reports `plan_source: lesson` (the plan was created via `phase-1-init` Step 4 from a lesson ID). Does NOT activate for free-form, issue-derived, or recipe-derived plans.

**Detection logic**:

1. Read the source lesson body from the plan directory (`lesson-{id}.md` archived alongside `request.md`).
2. Extract concrete code claims: file paths (with extensions), profile→target mappings (e.g., "implementation profile runs `module-tests`"), function/symbol names with signatures, argument shapes (CLI flags, call args), behavioral assertions ("currently hard-codes `./pw`", "is registered in plugin.json").
3. For each claim, probe the current code state:
   - File path → `manage-files exists --plan-id {plan_id} --file {path}` or `architecture find --pattern {basename}`
   - Profile→target mapping → query `manage-config plan {phase} get` or grep architecture
   - Function/symbol name → `architecture find --pattern {name}` then `Read` the matched file
   - Argument shape → resolve the flag against the **full parser chain**, not just one parser level. Probe the leaf subcommand help AND every ancestor parser in the notation's command chain (the leaf's parent up to the top-level notation), because argparse resolves flags up the full chain — a flag declared on a parent command or at the top level is valid even though it is absent from the leaf subcommand's help; additionally, executor-stripped flags (e.g. the audit-plan-id flag, which `.plan/execute-script.py` consumes before argv reaches argparse) appear in NO parser's help yet are always valid. Probe the leaf, each parent, and the top-level notation help in turn. Classify the argument-shape claim as `invalid` only when the cited flag is absent from the leaf AND every ancestor parser AND is not an executor-stripped flag.

     **Worked false-positive (full-chain resolution)**: a lesson narrative cites the invocation

     ```bash
     python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-2-refine get --field compatibility --audit-plan-id X
     ```

     Probing only the leaf help shows only the field flag, so a leaf-only check would mark the claim `invalid` spuriously for the audit-plan-id flag. That flag is an executor-stripped flag (removed before argparse sees it), so it appears in no help output yet is always valid; the analogous parent-chain case is a top-level flag declared on the `manage-architecture` notation rather than its `resolve` leaf — probing the full chain reveals it. Classify `valid`, emit no finding.
   - Behavioral assertion → `Read` the cited file/region and reason about current behavior
4. Classify each claim as: `valid` (narrative matches code), `stale` (code has moved but the underlying intent remains valid), or `invalid` (code never matched the narrative). Emit a finding per `stale` or `invalid` claim — but the two classifications carry different *severity* and *verdict semantics*, and the validator MUST preserve that distinction:

   - **`invalid`** → an outright invalid finding. The narrative was never true against any code state (e.g., the cited path matches no file, the cited mapping contradicts the configured baseline). This is a high-confidence discrepancy: the narrative is wrong, full stop. Emit at `--severity high`.
   - **`stale`** → a **low-confidence / outline-confirm-required** signal, NOT an outright invalid finding. The narrative *was* true at lesson-capture time and the underlying intent remains valid; only the surface (path, symbol name, signature) has moved under refactor/rename. The validator cannot tell from the narrative alone whether the moved surface or the lesson's original intent represents the desired end state — so a `stale` claim is a flag for the outline phase to confirm, not a blocker and not an assertion that the narrative is wrong. Emit at `--severity low` and word the finding so it reads as "confirm at outline", not "narrative is invalid".

   The STALE-vs-INVALID distinction is load-bearing: collapsing `stale` into the same outright-invalid treatment as `invalid` would over-report routine refactor drift as narrative errors, defeating the validator's purpose of surfacing genuine baseline mismatches.

**Finding emission template**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 2-refine \
  --source qgate --type triage --severity {severity} \
  --title "Q-Gate: narrative_vs_code_validator — {classification} claim in lesson {lesson_id}" \
  --detail "Lesson narrative claims '{claim_text}' but current code shows '{actual_state}' at {file_path}:{line}. {classification_detail}. Discrepancies are scope-expansion signals, not blockers — surface both readings to the user and ask which represents the desired end state before treating the narrative as authoritative." \
  --audit-plan-id {plan_id}
```

`{classification}` is one of `stale`, `invalid`. `{severity}` follows the classification per step 4: `low` for `stale` (a low-confidence, outline-confirm-required signal), `high` for `invalid` (an outright invalid finding). `{classification_detail}` adds context AND signals the verdict semantics: for `stale`, frame it as a confirm-at-outline prompt — e.g., "Lesson was authored 2026-04-08; the cited symbol was renamed in PR #199 (2026-04-15) — the intent is likely still valid, confirm at outline whether the renamed surface is the desired target"; for `invalid`, state the outright mismatch — e.g., "No file matching the cited path was found in the worktree; the narrative never matched any code state".

**Positive example**: A lesson-derived plan claims "implementation profile runs `module-tests`". Validator queries `manage-config plan phase-2-refine get --field profile_command_map`, finds `implementation` profile maps to `compile`, not `module-tests`. Validator emits `invalid` finding — the narrative was wrong about the baseline.

**Negative example**: Lesson cites `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` and the file exists with the cited Section 2.9 still present. Silent pass — narrative matches code.

**Rationale**: A lesson narrative authored against one code state and executed against a later state that has been renamed, refactored, or removed produces no-ops or regressions; validating the narrative at refine time surfaces the drift before outline and plan lock the intent.

#### 2.15 Worktree-Linter Validator

Verify that no skill, agent, or script in `solution_outline.md`'s `affected_files` (or any deliverable's `Change per file` block) reintroduces the three stale worktree-handling patterns that the centralized [`worktree-handling.md`](../../workflow-integration-git/standards/worktree-handling.md) standard explicitly forbids. The centralized file is the **single authoritative source** for worktree-handling rules — every check below cross-references it.

**Activation condition**: Runs in the `3-outline` and `4-plan` phase contexts. Activates whenever a deliverable's `affected_files` contains at least one path matching `marketplace/bundles/*/skills/**/*.md`, `marketplace/bundles/*/agents/*.md`, `marketplace/bundles/*/skills/**/scripts/*.py`, or `marketplace/bundles/*/skills/**/scripts/*.sh`. Skips deliverables whose only affected files are tests, fixtures, or non-skill documentation.

**Detection logic**: For each in-scope `{affected_path}`, run the three pattern sweeps below as **separate Bash invocations** (one command per call). Every match becomes a candidate finding unless the suppression rule applies.

**Pattern WL-A — Direct `cd <worktree_path>` shell compounds**:

The centralized standard forbids `cd {worktree_path} && <command>` shell compounds; all worktree-rooted operations MUST use the path-flag form documented in `worktree-handling.md` (e.g., `git -C`, `mvn -f`, `pytest --rootdir`, `--project-dir` for Bucket B notations).

```bash
rg -n "cd\s+[^\s]*worktree[^\s]*\s*&&" {affected_path}
```

Match also accepts the literal `cd "$WORKTREE"` / `cd ${worktree_path}` shapes. Any positive match is a violation.

**Pattern WL-B — Hard-coded `.claude/worktrees/` references**:

The forbidden substring is named in the heading above and matched by the regex below. Worktree storage lives under `.plan/local/worktrees/`; hits in skill / agent prose, script literals, or examples are stale and MUST be rewritten.

```bash
rg -n "\.claude/worktrees/" {affected_path}
```

The centralized [`worktree-handling.md`](../../workflow-integration-git/standards/worktree-handling.md) is the only legitimate location to discuss the historical path, and only inside an explicit "Migration history" subsection. Matches outside that file are violations.

**Pattern WL-C — Missing `--plan-id` on auto-routing scripts**:

Worktree-aware `manage-*` scripts auto-route to the correct worktree when `--plan-id` is supplied. Skills and agents that invoke an auto-routing script without passing `--plan-id` will silently target the main checkout — defeating worktree isolation.

```bash
rg -n "execute-script\.py\s+plan-marshall:(manage-files|manage-tasks|manage-findings|manage-references|manage-solution-outline|manage-plan-documents|manage-logging|manage-status):[^\s]+\s+[^\s]+\s+(?!.*--plan-id)" {affected_path}
```

The whitelist of auto-routing notations is the authoritative list at [`worktree-handling.md`](../../workflow-integration-git/standards/worktree-handling.md) "Auto-routing scripts" subsection. Matches indicate a manage-* invocation that omits `--plan-id`.

**Suppression rule**: A match in `{affected_path}` is suppressed (no finding emitted) when EITHER:
- `{affected_path}` is the centralized `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md` itself (the standard quotes the forbidden patterns to define them), OR
- The match line contains a fenced-off "Anti-pattern" / "Forbidden" / "Do NOT" marker on the same line or the immediately preceding line (the standard quotes the pattern to forbid it).

Apply the suppression rule per match, not per file. Unsuppressed matches are violations.

**Finding emission template**:

For each unsuppressed match across patterns WL-A, WL-B, and WL-C:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase {phase} \
  --source qgate --type triage \
  --title "Q-Gate: worktree_linter — {pattern_letter} violation in {affected_path}" \
  --detail "{affected_path}:{line} contains a stale worktree-handling pattern that violates the centralized standard at marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md. {pattern_explanation}. Either rewrite the cited line per the centralized standard, or — if the pattern is genuinely required (e.g., a quoted anti-pattern in another standard) — wrap it in an explicit 'Anti-pattern' / 'Forbidden' / 'Do NOT' marker on the same line so the linter suppresses it." \
  --file-path "{affected_path}" \
  --audit-plan-id {plan_id}
```

`{pattern_letter}` is `WL-A`, `WL-B`, or `WL-C`. `{pattern_explanation}` is the fixed string for each pattern:

| Pattern | `{pattern_explanation}` |
|---------|-------------------------|
| WL-A | "Direct `cd <worktree_path>` shell compounds are forbidden — use `git -C`, `mvn -f`, `pytest --rootdir`, or the appropriate path-flag form documented in worktree-handling.md" |
| WL-B | "Hard-coded `.claude/worktrees/` references are stale — worktree storage lives under `.plan/local/worktrees/`; update the reference per worktree-handling.md" |
| WL-C | "manage-* invocation omits `--plan-id`; auto-routing scripts silently target the main checkout when `--plan-id` is missing — see worktree-handling.md 'Auto-routing scripts' subsection" |

**Pass criteria** (silent — no finding emitted):
- Every grep returns no matches across the three patterns, OR
- Every match is suppressed per the suppression rule (centralized file or explicit anti-pattern marker).

**Fail criteria**: At least one unsuppressed match exists across patterns WL-A, WL-B, or WL-C — emit one finding per unsuppressed match.

**Positive example (WL-A)**: Outline deliverable modifies `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` and the diff introduces `cd /Users/foo/.claude/worktrees/EXAMPLE-PLAN && git status`. WL-A grep matches; line is not under an "Anti-pattern" marker; finding emitted citing `worktree-handling.md`.

**Positive example (WL-B)**: Outline deliverable modifies an agent file that contains `worktree_path: /Users/oliver/git/plan-marshall/.claude/worktrees/foo`. WL-B grep matches; finding emitted citing the TASK-4 migration.

**Positive example (WL-C)**: Outline deliverable modifies a skill that contains `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read --task-number 5` (no `--plan-id`). WL-C grep matches; finding emitted citing the TASK-10 auto-routing contract.

**Negative example**: The centralized `worktree-handling.md` itself contains the forbidden patterns inside an "Anti-pattern" subsection ("Do NOT use `cd $WORKTREE && git status`"). Suppression rule applies — silent pass.

**Cross-references**:
- Authoritative source: [`worktree-handling.md`](../../workflow-integration-git/standards/worktree-handling.md)
- WL-B migration: `.claude/worktrees/` → `.plan/local/worktrees/`
- WL-C contract: auto-routing `--plan-id` extension
- Rationale: Worktree-handling rules duplicated across skill files drift independently; the centralized standard is the single authoritative source and this validator enforces it at Q-Gate time so per-skill drift is caught before execute.

#### 2.17 Architecture-Mismatch Validator

Verify that every deliverable in `solution_outline.md` that adds capability to an existing skill carries a `**Design notes:**` block whose declared design model matches the target skill's documented design intent. Without this validator, plans regularly propose script-side check evaluators for LLM-driven aspects (or vice versa), and the mismatch surfaces only at phase-5-execute when the implementation task agent finds itself extending the wrong surface. This validator catches the mismatch at outline time, where the cheap fix is a re-outline pass.

**Activation condition**: Runs in the `3-outline` phase context. Activates for every deliverable whose `**Affected files:**` list contains at least one path under `marketplace/bundles/{bundle}/skills/{skill}/**` for an EXISTING skill (path resolves to a real directory at validation time). Brand-new skill creations (where the target skill directory does not yet exist) skip the check — there is no documented design model to compare against. Deliverables that do not touch existing skills skip the check.

**Detection logic**: For each activated deliverable:

1. Resolve the target skill from the deliverable's affected files. When multiple skills are touched, the deliverable triggers the check separately for each touched skill; a single deliverable may emit multiple findings.
2. Read the target skill's design model from its SKILL.md / `standards/design-intent.md` / `standards/architecture.md` per the heuristic documented in [`phase-3-outline/standards/outline-workflow-detail.md` § Step 9c](../../phase-3-outline/standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent). Classify as `script-deterministic`, `LLM-driven`, or `hybrid`.
3. Extract the deliverable's `**Design notes:**` block. The block satisfies the contract when ALL of the following hold:
   - The block exists.
   - The block names a specific design model (`script-deterministic`, `LLM-driven`, or `hybrid`).
   - The named model **matches** the target skill's classification from step 2 (allowing the `Diverges from` form documented in Step 9c when the deliverable explicitly declares a divergence and includes the "documented going forward" half).
   - The block carries a one-sentence rationale that names a specific element of the design model (generic phrases like "matches the existing model" or "fits the architecture" fail this check — the rationale has to identify the specific extension point).
4. Missing block, mismatched model, generic rationale, OR a `Diverges from` form without the "documented going forward" half is a violation.

**Recurrence signal**: the most common shape of this failure is a deliverable that proposes script-side check evaluators for an LLM-driven aspect, OR proposes LLM-driven narrative steps that re-do work the target script already does. Both shapes contradict the target skill's design model. Step 9c catches them at outline time when the outline follows the procedure; this validator catches them at Q-Gate time when it does not.

**Finding emission template**:

For each triggered deliverable that fails the contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 3-outline \
  --source qgate --type triage \
  --severity error \
  --title "Q-Gate: architecture-mismatch — deliverable {N} ({title}) {missing|mismatched|generic} Design notes" \
  --detail "Deliverable {N} touches existing skill `{bundle}:{skill}` whose documented design model is {target_model}. {Specific defect — one of: 'Design notes block is absent', 'Design notes declares {declared_model} but target is {target_model}', 'Design notes rationale is generic — no specific extension point named', 'Design notes declares Diverges from but omits the documented-going-forward half'.} Follow the procedure in phase-3-outline/standards/outline-workflow-detail.md § Step 9c — read the target skill's SKILL.md / standards/design-intent.md, classify the design model, and record a Design notes block that either extends the existing model with a specific rationale OR documents the divergence with the matching skill-design-intent update task." \
  --audit-plan-id {plan_id}
```

`{target_model}` is the classification computed in step 2. `{declared_model}` is the value parsed from the deliverable's `**Design notes:**` block (empty when the block is missing). `severity: error` so phase-3-outline auto-loops to address the finding before phase transition.

**Pass criteria** (silent — no finding emitted):
- The deliverable does not touch an existing skill (no path under `marketplace/bundles/{bundle}/skills/{skill}/**` with a real directory at validation time), OR
- The deliverable's `**Design notes:**` block satisfies all four contract points above.

**Fail criteria**: At least one triggered deliverable has a missing, mismatched, or generic `**Design notes:**` block — emit one finding per (deliverable, target-skill) pair.

**Positive example (LLM-driven mismatch)**: A plan touches `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md` (LLM-driven) and proposes a new Python script under `scripts/check_outline.py` that walks SKILL.md for a regex match. The deliverable's `**Design notes:**` block reads "Extends the existing script-deterministic design model of plan-marshall:phase-3-outline". Validator emits a finding: declared model `script-deterministic` does not match target model `LLM-driven`; the proposed check belongs in `plan-marshall/workflow/q-gate-validation.md` (LLM-driven) as a new validator subsection.

**Positive example (generic rationale)**: A plan touches `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` (script-deterministic) and adds a new subcommand. The `**Design notes:**` block reads "Extends the existing script-deterministic design model of plan-marshall:manage-execution-manifest — matches the existing model". Validator emits a finding: rationale is generic; the block has to name a specific extension point (e.g., "adds a new `validate-loadable` CLI subcommand alongside the existing `compose` / `read` / `validate` subcommands").

**Negative example (clean extension)**: A plan adds a new validator subsection to `plan-marshall/workflow/q-gate-validation.md` (LLM-driven). The `**Design notes:**` block reads "Extends the existing LLM-driven design model of q-gate-validation — adds a new validator subsection §N.NN with detection logic, finding emission template, and pass/fail criteria following the existing §2.x pattern". Validator passes silently.

**Cross-references**:
- Authoritative source: [`phase-3-outline/standards/outline-workflow-detail.md` § Step 9c](../../phase-3-outline/standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent) (the procedure this validator enforces)
- Companion validator: § 2.10 Argparse Validator (script-shape compliance)
- Companion rule: phase-4-plan SKILL.md § "Integration Deliverable Narrative Constraint" (xref-vs-inline) — operates on a different axis but compose with this validator when a single deliverable both integrates a central standard AND adds capability to an existing skill
- Rationale: Deliverables that propose a design model inconsistent with the target skill's documented design intent produce implementation conflicts that are cheap to fix at outline time but expensive after plan and task creation lock the approach.

---

### Step 5: Check Missing Coverage

Compare assessed files (CERTAIN_INCLUDE) against deliverable affected files:

```text
FOR each file IN assessed_files:
  IF file NOT IN any deliverable.affected_files:
    FLAG: Assessed file not covered in deliverables
```

**Log missing coverage**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(execution-context.q-gate-validation:qgate) Missing coverage: {file} assessed but not in deliverables" \
  --audit-plan-id {plan_id}
```

---

### Step 6: Record Findings

For each issue found (false positive, missing coverage, alignment issue), record it using `manage-findings` with the **`qgate add`** subcommand (NOT `add` alone):

**Note**: The `qgate add` command deduplicates by title within each phase:
- Same title + pending → `status: deduplicated` (no duplicate created)
- Same title + resolved → `status: reopened` (finding reactivated)

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} \
  --phase 3-outline \
  --source qgate \
  --type triage \
  --title "Q-Gate: {issue_title}" \
  --detail "{detailed_reason}"
```

Optional parameters (add when applicable):
- `--file-path "{affected_file}"` — path of the affected file
- `--component "{deliverable_reference}"` — deliverable reference

---

### Step 7: Update Affected Files

Persist the verified affected files to references.json.

**CRITICAL**: The `--values` parameter requires a **single comma-separated string** with NO spaces between items:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set-list \
  --plan-id {plan_id} \
  --field affected_files \
  --values "file1.py,file2.py,file3.md" \
  --audit-plan-id {plan_id}
```

**Example** (correct):
```bash
--values "src/foo.py,src/bar.py,test/test_foo.py"
```

**Example** (WRONG - will fail):
```bash
--values src/foo.py src/bar.py test/test_foo.py
```

Only include files from deliverables that passed verification.

---

### Step 8: Count Pending Findings

Query the pending findings count for the return output:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate list --plan-id {plan_id} --phase 3-outline --resolution pending
```

Extract `filtered_count` from the output — this becomes `qgate_pending_count` in the return value.

---

### Step 9: Log Summary

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(execution-context.q-gate-validation) Summary: {passed} passed, {flagged} flagged, {missing} missing coverage" \
  --audit-plan-id {plan_id}
```

### Step 10: Log Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (execution-context.q-gate-validation) Complete"
```

---

## Output

Return verification results - detailed findings in sinks:

```toon
status: success | error
display_detail: "<{flagged}/{N} flagged, {qgate_pending_count} pending>"
plan_id: {plan_id}
deliverables_verified: {N}
passed: {count}
flagged: {count}
missing_coverage: {count}
findings_recorded: {count}
qgate_pending_count: {count}
```

`display_detail` shape: `"{flagged}/{N} flagged, {qgate_pending_count} pending"` (e.g. `"2/7 flagged, 3 pending"`); ≤80 chars, ASCII, no trailing period.

**OUTPUT RULE**: Do NOT output verbose text. All verification details are logged to decision.log and findings to artifacts/qgate-3-outline.jsonl. Only output the final TOON summary block. The summary block MUST reflect a FULL pass — every applicable validator (§2.1–§2.17, scoped to the active phase) must have run and recorded its findings before this block is emitted, even when blocking findings are already present (see the full-coverage guarantee in Step 4). `qgate_pending_count` is only trustworthy as a complete tally because of that guarantee; FIX 4-lite's per-deliverable skip depends on it.

---

## Verification Criteria Matrix

| Check | Pass | Flag |
|-------|------|------|
| Request Alignment | Deliverable addresses request intent | Scope doesn't match request |
| Assessment Coverage | All files have CERTAIN_INCLUDE | Files without assessment |
| False Positives | Files should be modified | Files document, don't produce |
| Architecture | Module/domain valid | Invalid module or domain |
| File Existence | All affected file paths exist on disk | Path not found or wrong convention |
| Profile Overlap | No redundant test coverage across deliverables | Test deliverable duplicates module_testing scope |
| Consumer Sweep Completeness | Cross-bundle consumers of deleted/renamed public symbols enumerated in Affected files | Trigger language present AND (empty affected_files OR no cross-bundle entries when grep returns cross-bundle hits) |
| Argparse Validator (3-outline) | Every `python3 .plan/execute-script.py` invocation in solution_outline.md cites a subcommand and flags declared by live `--help` | Cited subcommand or `--flag` is undeclared in the live argparse schema |
| Module-Mapping Validator (4-plan) | `module_testing` task's test files share an `architecture which-module` result with the sibling implementation task's impl files | Test/impl modules differ AND no documented test→impl mapping covers the pair |
| Scope-Criterion Validator (3-outline / 4-plan) | Every operationalizable `success_criterion` agrees with `affected_files` after the structured query is run | Symmetric difference between query result set and affected_files (under-coverage or over-coverage), or marketplace-wide criterion paired with bundle-scoped query |
| Tier-Delta Validator (3-outline) | Tiered/variant specs include a delta table contrasting every cross-tier field with rationale | Tiered sections present AND delta table missing or incomplete |
| Narrative-vs-Code Validator (2-refine, lesson plans) | Every concrete code claim in the source lesson narrative matches current code state | Claim is `stale` (code moved) or `invalid` (cited path/symbol/shape never matched) |
| Worktree-Linter Validator (3-outline / 4-plan) | Skills/agents/scripts touched by deliverables contain none of the three forbidden worktree-handling patterns documented in `worktree-handling.md` (direct `cd <worktree_path>`, hard-coded `.claude/worktrees/`, manage-* invocations missing `--plan-id`) | Any unsuppressed match for patterns WL-A, WL-B, or WL-C |
| Missing Coverage | All assessed files in deliverables | Assessed files missing |

---

## Error Handling

```toon
status: error
error: {solution_read_failed|assessment_read_failed|request_read_failed}
message: {human readable error}
context:
  plan_id: {plan_id}
  operation: {what was being attempted}
```

---

## CONSTRAINTS

### MUST NOT
- Skip verification on any deliverable
- Proceed without logging each verification decision
- Approve deliverables with missing assessments

### MUST DO
- Verify every deliverable individually
- **Run AND record findings from EVERY applicable validator (§2.1–§2.17, scoped to the active phase's subset) before returning — never short-circuit on the first failing validator class. A single pass MUST surface all finding classes at once, collapsing N sequential round-trips into 1. This full-coverage guarantee is the precondition FIX 4-lite (per-deliverable content-hash skip) relies on.**
- Log each verification decision
- Record findings for any issues
- Persist only verified affected_files
