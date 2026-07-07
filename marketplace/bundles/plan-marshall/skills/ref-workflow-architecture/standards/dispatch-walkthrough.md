# Dispatch Walkthrough — Worked Examples

Concrete end-to-end traces of `execution-context-{level}` dispatches at three representative call sites: a single-workflow phase entry, a finalize step that sub-dispatches `verification-feedback` (producer=pr-comment) by reference, and a per-iteration parallel fan-out. For the dispatch contract itself (prompt-body fields, role-key resolution, mandatory rules), see [`agents.md`](agents.md). For the heuristics that decide *whether* a step should dispatch, see [`../../extension-api/standards/dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md). For the holistic visual call graph covering every dispatch path (not just these three exemplars), see [`call-graph.md`](call-graph.md).

## Generic eight-step sequence

Every dispatched phase or step follows the same shape:

1. **Orchestrator: pick role key + workflow doc + skills.** From a slash-command action, a manifest step, or an inline call site.
2. **Orchestrator: resolve the level** via `python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort resolve-target --role <role_key>`. Returns the variant target name (`execution-context-{level}` or canonical `execution-context` for `inherit`).
3. **Orchestrator: construct prompt body** — five required fields (`name`, `plan_id`, `skills[]`, exactly one of `workflow`/`instructions`, `WORKTREE`) plus any workflow-specific runtime inputs. Under the cwd-pinned model the `WORKTREE` field is **path-free** — it carries `--plan-id {plan_id}` (a salience reminder), not a worktree absolute path. The subagent inherits the orchestrator's pinned cwd and resolves `.plan/` cwd-relatively; see [`../../tools-script-executor/standards/cwd-policy.md`](../../tools-script-executor/standards/cwd-policy.md).
4. **Orchestrator: dispatch** — `Task: plan-marshall:execution-context-{level}` with the prompt body.
5. **Subagent: load skills + read workflow** — `persona-plan-marshall-agent` first (implicit), then each `skills[]` entry in order, then `Read` the resolved workflow path.
6. **Subagent: execute the workflow** — runtime inputs substitute into the doc's `{placeholder}` tokens.
7. **Subagent: return TOON** — minimum shape `status` + `display_detail`; workflow-specific fields per its return contract.
8. **Orchestrator: record outcome** via `manage-status mark-step-done` and accumulate usage via `manage-metrics accumulate-agent-usage`.

The three examples below instantiate this sequence with realistic prompts and return shapes.

---

## Example A — phase-2-refine entry (single-workflow phase)

The simplest case: a phase whose role key is flat (`phase-2-refine`), one dispatched workflow, the confidence loop iterates *inside* the envelope.

### Setup
- `{plan_id}` = `lesson-2026-05-11-foo`
- `marshal.json`: `"models": {"default": "level-2", "roles": {"phase-2-refine": "level-3", ...}}`

### Trace

**Steps 1–3 (orchestrator):**
- role_key = `phase-2-refine`
- workflow = `plan-marshall:phase-2-refine/SKILL.md`
- skills = `[plan-marshall:manage-architecture, plan-marshall:manage-references, plan-marshall:manage-plan-documents]`

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-2-refine
```

Returns:
```toon
status: success
role: phase-2-refine
level: level-3
target: execution-context-level-3
```

**Post-resolve dispatch log** (between resolve and dispatch, per [`dispatch-logging.md`](dispatch-logging.md) § "Emission contract"):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id lesson-2026-05-11-foo --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target=execution-context-level-3 level=level-3 role=phase-2-refine workflow=plan-marshall:phase-2-refine/SKILL.md plan_id=lesson-2026-05-11-foo"
```

**Step 4 (orchestrator constructs prompt body):**

```text
name: phase-2-refine
plan_id: lesson-2026-05-11-foo
skills[3]:
- plan-marshall:manage-architecture
- plan-marshall:manage-references
- plan-marshall:manage-plan-documents
workflow: plan-marshall:phase-2-refine/SKILL.md
WORKTREE: --plan-id lesson-2026-05-11-foo
```

**Step 5 (dispatch):**

```text
Task: plan-marshall:execution-context-level-3
  prompt: <the block above, verbatim>
```

**Step 6 (subagent body):**

1. `Skill: plan-marshall:persona-plan-marshall-agent` (implicit)
2. `Skill: plan-marshall:manage-architecture`
3. `Skill: plan-marshall:manage-references`
4. `Skill: plan-marshall:manage-plan-documents`
5. `Read plan-marshall:phase-2-refine/SKILL.md` (notation resolved to filesystem path by the dispatcher)
6. Execute SKILL.md — the confidence loop (Steps 3b → 3c → 8 → 9 → 10 → 11 → 12) iterates inside this envelope until confidence ≥ threshold. AskUserQuestion in Step 11 propagates to the host UI directly from the subagent.

**Step 7 (subagent returns):**

```toon
status: success
display_detail: confidence 95 reached at iteration 2
plan_id: lesson-2026-05-11-foo
confidence: 95
track: complex
scope_estimate: multi_module
qgate_pending_count: 0
```

Plus `<usage>` tag with `total_tokens=38420, tool_uses=14, duration_ms=210000`.
`total_tokens` is the canonical sub-agent `<usage>` token key consumed by `manage-metrics enrich`.

**Step 8 (orchestrator records):**

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id lesson-2026-05-11-foo \
  --phase 2-refine --step refine-analyze \
  --outcome done --display-detail "confidence 95 reached at iteration 2"

python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics \
  accumulate-agent-usage --plan-id lesson-2026-05-11-foo --phase 2-refine \
  --total-tokens 38420 --tool-uses 14 --duration-ms 210000
```

One dispatch, ~210 s wall-clock, the entire confidence loop runs inside one envelope. No per-iteration dispatch.

---

## Example B — phase-6-finalize automated-review with `verification-feedback` (sub-dispatch by reference)

The most complex case. The manifest step `automated-review` runs **mostly inline as scripts** (producer fetch, finding enumeration) and **dispatches `verification-feedback` once** with `producer=pr-comment` when there are findings to triage. Findings live in the per-plan findings store; the subagent queries them as its first workflow step — they are NEVER embedded in the prompt body.

### Setup
- `{plan_id}` = `feature-jwt-auth`
- `manifest.phase_6.steps` includes `automated-review` (declares `requires: [ci-complete]` in its frontmatter, ordered before `sonar-roundtrip`)
- The phase-6-finalize dispatcher just resolved the `ci-complete` precondition for the current HEAD via `ci_complete_precondition.resolve` — the cache now records `success` for this SHA.

### Orchestrator: inline orchestration prologue

```bash
# 1. Wait for review-bot comments (CI completion already guaranteed by
#    the dispatcher's precondition resolver — no manage-status signal
#    lookup is required inside this body).
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --plan-id feature-jwt-auth pr wait-for-comments \
  --pr-number 142 --timeout 180

# 2. Producer: FIND PR comments into the ledger (untrusted body under raw_input)
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  fetch_findings --pr-number 142 --plan-id feature-jwt-auth

# 3. Gate-check: count pending findings (NOT content)
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  list --plan-id feature-jwt-auth --type pr-comment --resolution pending
```

If pending count is 0 → skip the dispatch, mark step done. If non-zero → proceed to dispatch.

### Orchestrator: dispatch `verification-feedback` by reference

**Steps 2–3 (resolve level):**

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize --role verification-feedback
```

Returns `target: execution-context-level-3`.

**Step 4 (prompt body — no findings list inline):**

```text
name: verification-feedback
plan_id: feature-jwt-auth
skills[1]:
- plan-marshall:manage-findings
workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md
producer: pr-comment
pr_number: 142
caller_phase: phase-6-finalize
WORKTREE: --plan-id feature-jwt-auth
```

**Step 5 (dispatch):** `Task: plan-marshall:execution-context-level-3` with the block above.

**Step 6 (subagent body — smart-grouping algorithm):**

1. `Skill: plan-marshall:persona-plan-marshall-agent` (implicit)
2. `Skill: plan-marshall:manage-findings`
3. `Read plan-marshall:plan-marshall/workflow/triage.md`
4. **Fetch findings from the store** (NOT from the prompt body):

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
     list --plan-id feature-jwt-auth --type pr-comment --resolution pending
   ```

   Returns 6 pending findings of mixed `(domain, rule_id)` pairs. This is the single source of truth. On loop-back re-entry the second query sees only currently-pending findings — stale-data failure mode avoided.

5. **Pre-group by `(domain, rule_id)`**. The subagent calls `architecture which-module` for each finding once to populate the `domain` field, then groups. Findings with no `rule_id` form singleton groups.

6. **Sequential between groups, batched LLM decision within a group:**
   - Per group: load `ext-triage-{domain}` once (idempotent across same-domain groups in the same envelope).
   - One LLM call decides every finding in the group, returning `decisions[N]{hash_id, outcome, rationale}`.
   - Act on each decision sequentially: `manage-findings resolve`, PR thread reply, fix-task allocation. Sequential action preserves cross-group feedback — TASK-N allocated for group 1 can be referenced when triaging group 2.

7. AskUserQuestion (within a batched decision): the LLM can flag M of N findings as `ASK_USER_QUESTION`; the subagent raises the M prompts one by one. Batching the *decision* call does not batch the user UX.

**Step 7 (subagent returns):**

```toon
status: loop_back
display_detail: 6 comments triaged, 2 fix tasks created
producer: pr-comment
findings_processed: 6
findings_resolved: 6
fix_tasks_created: 2
fix_task_numbers[2]:
- 27
- 28
```

Plus one `<usage>` tag — one envelope cost, not six.

**Step 8 (orchestrator):** `mark-step-done --outcome loop_back`. The phase-6-finalize dispatcher's loop-back continuation transitions back to phase-5-execute, dispatches the fix tasks, transitions forward, re-enters the manifest. The next `automated-review` run sees 0 pending findings and short-circuits.

### Key by-reference property

The findings list never lives in the prompt body. Passing `finding_type` plus the loaded `manage-findings` skill is all the subagent needs. Embedding inline would duplicate the store's data into the prompt for zero information gain — and would freeze the list at orchestrator-query time, defeating loop-back re-query semantics.

---

## Example C — phase-6-finalize architecture-refresh Tier-1 fan-out (per-iteration parallel)

The only per-iteration parallel dispatch in the contract. Phase-6 `architecture-refresh` Tier-0 runs inline scripts to discover the affected module set; Tier-1 dispatches one subagent per affected module, all in parallel. Per-iteration is the right shape because (a) modules are independent and (b) parallelism saves wall-time.

### Setup
- `{plan_id}` = `feature-jwt-auth`
- Tier-0 inline discovery completed; affected_modules = `[auth-core, auth-jwt, auth-tests]` (3 modules)

### Orchestrator: Tier-0 inline (scripts only)

```bash
# Discover affected modules from the worktree diff against the baseline Tier-0
# extracted from origin/main's committed .plan/project-architecture/ tree. cwd is
# pinned to the plan's worktree (the cwd-pinned model), so the diff resolves
# against the pinned worktree without a path arg. The affected set is the
# index-derived union added ∪ removed read from this call's TOON output (the
# changed bucket is noise against a derived-less git baseline) — it is held in
# memory for the dispatch fan-out, not persisted via a separate command.
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  diff-modules --pre .plan/temp/architecture-baseline/.plan/project-architecture
```

If `affected_modules` is empty → Tier-1 is skipped; the step marks done with `display_detail: "no modules affected"`.

### Orchestrator: Tier-1 inline loop (auto mode)

`architecture-refresh` is an **inline step** — Tier-1 `auto` mode runs the re-enrichment loop directly inside the current finalize envelope, with no `Task:` sub-dispatches. There is no batch verb; the orchestrator iterates `affected_modules` and calls three per-verb subcommands per module:

**For each module M in `affected_modules` (`auth-core`, `auth-jwt`, `auth-tests`):**

```bash
# Step 6 — write responsibility + purpose
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich module --name M \
  --responsibility "{1-3 sentence description}" \
  --responsibility-reasoning "{source}" \
  --purpose {purpose-value} \
  --purpose-reasoning "{signal}" \
  --project-dir {worktree_path}
```

```bash
# Step 7 — write 2-4 key packages (one call per architecturally significant package P)
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich package --module M --package P \
  --description "{1-2 sentence description}" \
  --project-dir {worktree_path}
```

```bash
# Step 8 — refresh skills-by-profile
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich skills-by-profile --module M \
  --skills-json '{"<profile>": ["<bundle:skill>", ...]}' \
  --reasoning "{why these profiles/skills apply}" \
  --project-dir {worktree_path}
```

Each `enrich` call rewrites `enriched.json` for the named module only; there is no merge step. After the full loop, the orchestrator stages and commits the updated `enriched.json` files.

### Why this shape

`architecture-refresh` is inline rather than dispatched because:
- The `prompt` mode of Tier 1 requires an `AskUserQuestion` interaction, which only works in the inline orchestrator context (a leaf subagent cannot fire `AskUserQuestion`).
- The `auto` mode iterates the affected-module loop inside the same envelope for the same reason — the step is declared inline once and both modes share the execution surface.

See [`../../extension-api/standards/dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) § 4 (Heuristic 3) for the general per-X loop rule (prefer internal iteration over sequential per-iteration dispatch).

---

## Cross-references

- The dispatch contract (prompt-body fields, mandatory rules) — [`agents.md`](agents.md)
- The standardized `[DISPATCH]` work-log emission inserted between resolve and dispatch in Example A above — [`dispatch-logging.md`](dispatch-logging.md)
- Granularity heuristics (why dispatch vs script vs inline) — [`../../extension-api/standards/dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md)
- The triage smart-grouping algorithm — [`../../plan-marshall/workflow/triage.md`](../../plan-marshall/workflow/triage.md)
- Workflow-doc implementor contract — [`../../extension-api/standards/ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md)
- Level → primitive table — [`../../plan-marshall/standards/effort-levels.md`](../../plan-marshall/standards/effort-levels.md)
- Role-key registry — [`../../plan-marshall/standards/effort-roles.md`](../../plan-marshall/standards/effort-roles.md)
