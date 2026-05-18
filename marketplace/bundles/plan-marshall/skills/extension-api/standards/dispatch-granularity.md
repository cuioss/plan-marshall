# Dispatch Granularity: When to Spawn a Subagent

Single source of truth for the granularity heuristics that govern when a step earns an LLM dispatch envelope, when it should bundle into a larger dispatch, and when it should stay a deterministic script. Every skill that adds new workflow material — whether it dispatches a subagent or contemplates one — should consult this doc.

## 1. What does a dispatch actually cost?

Spawning a subagent is not free. From `manage-metrics/standards/data-format.md`, real plan runs anchor the picture:

```
phase.1-init.total_tokens: ~25–55 K
phase.2-refine.total_tokens: ~40 K
phase.3-outline.total_tokens: ~110–200 K
phase.4-plan.total_tokens: ~110–130 K
phase.6-finalize.total_tokens: ~170–260 K
enriched.total_tokens (manage-architecture enrichment cycle): ~485 K
```

`phase-5-execute/SKILL.md` already treats ~50 000 tokens as the working unit of one dispatch (`per_task_budget_reserve` default). The `execution-context-{level}` dispatch layer also adds a small fixed cost per dispatch — skill load, Worktree Header echo, prompt envelope.

### 1.1 What the envelope contains

| Per-dispatch cost component | What it is |
|------------------------------|------------|
| Anthropic system prompt | Loaded once per subagent invocation; not shared with the parent's prompt cache. |
| Agent body | `execution-context.md` body (~50–100 LOC). |
| Implicit foundational skill load | `dev-general-practices` is loaded as the first step inside every dispatch — the entire skill body in the subagent's context. |
| Caller-specified `skills[]` loads | Each skill in `skills[]` is loaded inside the subagent at start (multi-KB each). |
| Workflow doc load | The standards doc the subagent follows — read fully into context. |
| Prompt envelope | The five required prompt-body fields (`name`, `plan_id`, `skills[]`, exactly one of `workflow`/`instructions`, `WORKTREE`) plus any workflow-specific runtime inputs and return-shape instructions. |
| Tool-use round-trips | Each subagent invocation carries coordination overhead between parent and child contexts. |
| Output → parent re-ingestion | The subagent's TOON return becomes parent input tokens. |
| Wall-time: model boot + prompt-cache miss | Subagents do not share prompt cache with the parent; cold start every time. |

### 1.2 The 10 K rule of thumb

For a *trivial* dispatch (e.g., "did this file exist? return yes/no"), the fixed envelope dominates: ~5–15 K tokens of envelope to do the equivalent of one `os.path.exists()` call. For a *substantive* dispatch (analyse a request against 5 quality dimensions, read 3 files, emit findings), the envelope is amortised.

**Rule of thumb derived from the 25–50 K phase totals**: a dispatch needs to do **at least ~10 K tokens worth of LLM-judgement work** to justify its envelope. Below that, it is cheaper and faster to do the work as a script (or inline in the parent's context if the parent is already there).

## 2. Heuristic 1 — Script over dispatch when work is deterministic

If the step's logic can be expressed as code without LLM judgement, **make it a script**. Examples of work that masquerades as dispatchable but is really deterministic:

- File-existence checks (`ls -la {target}`).
- Regex / keyword scans against an outline-text haystack (e.g., phase-4-plan keyword-drift, structural-token-drift).
- Graph algorithms (dependency-graph build, topological sort for execution order).
- TOON / JSON read-write loops.
- Boolean predicate evaluations (Q-Gate surgical bypass: `scope==surgical AND change_type IN {...} AND count==1`).
- File-stat reads (porcelain status, branch detection).
- Schema validation.

The repo already does this well in most places — `manage-tasks`, `manage-references`, `manage-architecture`, etc., are scripts.

### 2.1 Hybrid script + LLM fallback

When the deterministic check resolves the majority case but a small ambiguous tail needs LLM judgement, build a **hybrid**: the script does the work it can; only the residue escalates to a dispatch resolved against `effort` (no role key — the fallback uses the plan-wide default level). Examples shipped under this pattern: `manage-status:change-type-heuristic`, `manage-lessons:lesson-auto-suggest`, `manage-config:domain-detect`. The pattern is:

1. Script computes its deterministic answer.
2. If `ambiguous=true`, the script computes `(workflow, skills, plan_id, payload)`, resolves the level via `manage-config effort read --default`, and issues `Task: plan-marshall:execution-context-{level}` with the prompt body.
3. Two envelopes total when the fallback fires; one envelope when the heuristic resolves.

## 3. Heuristic 2 — Bundle into one dispatch when steps share context

If multiple steps run sequentially, read the same files, and have similar model needs, **they belong in one dispatch**. The envelope is paid once. Examples:

- `phase-2-refine`'s confidence loop (Steps 3b → 3c → 8 → 9 → 10 → 11 → 12 → back to 8) is *one* logical activity ("refine the request until confident"). Bundling all those steps into a single `phase-2-refine` dispatch pays one envelope, runs the loop inside the subagent's context, returns the final state.
- `phase-3-outline` Complex Track Step 10 is one substantive activity (discovery → analysis → write solution). Steps 9c and 10b are tightly coupled to it. Bundle as one `phase-3-outline` Complex Track dispatch.
- `phase-4-plan` Steps 5+6+7 form one logical task-creation activity over the deliverable set. Bundle into `phase-4-plan` (plan-all-tasks).

The four pre-existing finalize dispatches (`create-pr`, `automated-review`, `sonar-roundtrip`, `lessons-capture`) are good examples of well-bundled scope: each carries multi-step work; `automated-review` itself iterates N comments inside one context rather than spawning per-comment subagents.

## 4. Heuristic 3 — Per-iteration dispatch only when models differ OR iterations parallelise

For loops over N items (per-deliverable, per-module, per-aspect, per-finding), the default should be **one dispatch that iterates internally** — the shape today's `automated-review` triage workflow uses for N PR comments. Per-iteration dispatch only wins when:

- **(a)** Each iteration would use a meaningfully different model (rare in practice), OR
- **(b)** Iterations are independent and can run in parallel — wall-time savings outweigh envelope cost.

Per-iteration dispatch in a sequential loop is the **worst** shape: linear envelope cost × N with no parallelism payoff.

The only per-iteration parallel case in the post-refactor scope is `enrich-module` (one dispatch per affected module under `--phase phase-6-finalize`, all parallel — see [`ref-workflow-architecture/standards/dispatch-walkthrough.md`](../../ref-workflow-architecture/standards/dispatch-walkthrough.md) for the worked trace). Everything else either dispatches once with internal iteration, or stays inline as a script.

## 5. Find the LLM core, not the wrapping step

The step-level verdict ("dispatch" or "inline") is not the end of the analysis. Apply the same principle one level deeper: even steps that earn a dispatch are **not** monolithic LLM work. Each has an orchestration shell (scripts) wrapping an LLM-judgement core. **The role key should name the core, not the wrapping step.**

Concrete decomposition for finalize dispatches:

| Manifest step | Orchestration (stays inline in the dispatcher) | LLM-judgement core (the actual dispatch) |
|----------------|------------------------------------------------|------------------------------------------|
| `automated-review` | Read CI completion signal from `manage-status`; `ci pr wait-for-comments`; `github_pr comments-stage`; `manage-findings query` enumerate pending; loop-back handling; `mark-step-done`. **All scripts.** | **`verification-feedback` (`producer=pr-comment`)** under `--phase phase-6-finalize --role verification-feedback` — for each pending `pr-comment` finding: detect domain, resolve `ext-triage-{domain}`, load it, decide FIX/SUPPRESS/ACCEPT/AskUserQuestion. Iterated inside one dispatch. |
| `sonar-roundtrip` | `sonar fetch-and-store`; `manage-findings query`; `mark-step-done`. **All scripts.** | **`verification-feedback` (`producer=sonar`)** — same envelope, `sonar-issue` findings using `severity.md` + `suppression.md`. Iterated inside one dispatch. |
| `pre-submission-self-review` | `ext-self-review-plan-marshall:self_review` (deterministic candidate-surface script; resolved via `ext-self-review-{domain}` ext-point). | **`--phase phase-6-finalize`** (no `--role`; tracks `phase-6-finalize.default`) — LLM applies five structural-review checks against the surfaced candidates + loaded contract sources. |
| `create-pr` | Load `tools-integration-ci`; `ci pr prepare-body` (allocate body file path); various `manage-*` reads; `ci pr create` (post). | **`--phase phase-6-finalize`** (no `--role`; tracks `phase-6-finalize.default`) — LLM composes the PR body from plan context into the allocated body file. |
| `lessons-capture` | Load `manage-lessons`; `manage-lessons add` + `set-body` (scripts; LLM-driven inputs). | **`phase-6-finalize.post-run-review`** — LLM analyses the plan's history, decides which lessons are worth recording, composes each body. Shares level with retrospective. |
| `q-gate-validation` | `manage-plan-documents` reads (deliverables / request / solution outline); `manage-architecture` queries; `manage-status` reads; `manage-findings qgate add`; `mark-step-done`. **All scripts.** | **`--phase phase-N`** (no `--role`; tracks the calling phase default) — LLM validates the deliverable set against request intent + loaded assessment checks. Inside a single envelope. |

### 5.1 Phase-scoped resolution + producer-mode bundling

When the same LLM workflow fires from multiple phases (e.g., `q-gate-validation` from phase-2-refine/3/4, or `research` from any phase), the resolver bubbles up from the caller phase's sub-key to that phase's default to `effort`. The workflow body lives in one doc; each caller passes `--phase phase-N` and the level resolves under whichever phase fired the dispatch. There is no `cross.*` group — the per-phase configuration is the routing mechanism.

When one workflow has multiple producer sources, bundle them under one workflow with `producer` as the runtime axis. `verification-feedback` is the canonical example: five producers (`build-runner` from phase-5-execute; `sonar` / `pr-comment` / `plugin-doctor` / `pr-state` from phase-6-finalize) share the triage core but differ only in Step 1 (the producer-side data fetch). One workflow doc, one role-key sub-key, five runtime modes.

This is the **role-key-names-the-LLM-judgement-type principle** made structural: manifest steps may run several scripts and dispatch zero, one, or several LLM cores; the role-key registry lists only the cores, scoped to the phase that invokes them.

### 5.2 Smart grouping inside one dispatch

Inside one `verification-feedback` dispatch envelope, the legacy "process findings sequentially — never batch the per-finding decision through a single LLM call" rule is relaxed to a **smart-grouping** shape. The dispatch input carries `producer` only (not the findings content); the subagent **queries the per-plan findings store** as its first workflow step.

The algorithm pre-groups findings by `(domain, rule_id)`, runs one batched LLM decision per group, and acts on each finding sequentially between groups for cross-group feedback. Findings with no `rule_id` form single-finding groups; per-finding `AskUserQuestion` UX is preserved inside batched decisions; overflow / timeout captures unprocessed groups as a `triage-overflow` finding and loops back.

**Canonical home for the algorithm:** [`plan-marshall:plan-marshall/workflow/triage.md`](../../plan-marshall/workflow/triage.md) § Step 2 (smart grouping) — Steps 3a–3d cover the batched decision, sequential action, AskUserQuestion deferrals, and overflow handling. Skill authors writing new dispatches should cross-reference that doc rather than re-document the algorithm.

## 6. Applying the heuristics — quick decision flow

When designing a new workflow step or considering whether existing inline work should become a dispatch:

1. **Deterministic check?** If the step's logic is regex / graph / filesystem / arithmetic / boolean predicate — make it a script. See Heuristic 1.
2. **Shares context with neighbours?** If the step is one link in a chain that reads the same files and shares an LLM judgement type — bundle into the chain's dispatch. See Heuristic 2.
3. **Loops over N items?** Iterate internally inside one dispatch unless the iterations parallelise meaningfully or use different models. See Heuristic 3.
4. **Found a genuine LLM core?** Name it. The role key in `effort-roles.md` names the core's LLM-judgement type, not the wrapping manifest step. See § 5.

The wrong shape — per-iteration sequential dispatch into separate envelopes — appears nowhere in the post-refactor scope. If a new candidate lands there, re-apply the heuristics before locking it in.

## Cross-references

- The execution-context dispatch contract — [`ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md)
- Worked dispatch traces (phase-2-refine entry, finalize automated-review with `verification-feedback`, architecture-refresh Tier-1 fan-out) — [`ref-workflow-architecture/standards/dispatch-walkthrough.md`](../../ref-workflow-architecture/standards/dispatch-walkthrough.md)
- Holistic visual call graph — [`ref-workflow-architecture/standards/call-graph.md`](../../ref-workflow-architecture/standards/call-graph.md)
- The role-key registry — [`plan-marshall/standards/effort-roles.md`](../../plan-marshall/standards/effort-roles.md)
- The triage smart-grouping algorithm in full — [`plan-marshall:plan-marshall/workflow/triage.md`](../../plan-marshall/workflow/triage.md)
- Level → primitive table — [`plan-marshall/standards/effort-levels.md`](../../plan-marshall/standards/effort-levels.md)
- Per-phase / per-workflow "iterate-in-context" callouts (the load-bearing application of Heuristics 2 and 3):
  - [`phase-2-refine/SKILL.md`](../../phase-2-refine/SKILL.md) § Dispatched workflows vs inline steps — confidence loop runs inside one envelope.
  - [`phase-3-outline/SKILL.md`](../../phase-3-outline/SKILL.md) § Dispatched workflows vs inline steps — per-deliverable Complex Track loop runs inside one envelope.
  - [`phase-4-plan/SKILL.md`](../../phase-4-plan/SKILL.md) § Dispatched workflows vs inline steps — Steps 5+6+7 task-creation loop runs inside one envelope.
  - [`plan-retrospective/SKILL.md`](../../plan-retrospective/SKILL.md) § Dispatch shape — 8 aspects iterate inside one envelope.
  - [`workflow-pr-doctor/SKILL.md`](../../workflow-pr-doctor/SKILL.md) — thin redirect to `verification-feedback.md` (`producer=pr-state`); per-finding loop iterates inside one envelope. A sub-dispatch of `verification-feedback` is the documented exception when iteration crosses the wrapper budget (see verification-feedback.md § Sub-dispatch from inside this envelope).
  - [`pm-plugin-development:plugin-doctor/SKILL.md`](../../../../pm-plugin-development/skills/plugin-doctor/SKILL.md) § Dispatch shape — per-rule analyses run inside one envelope; `scope` selects the rule subset.
  - [`plan-marshall:plan-marshall/workflow/enrich-module.md`](../../plan-marshall/workflow/enrich-module.md) — the documented per-iteration-parallel exception (`enrich-module` under `--phase phase-6-finalize`, one envelope per affected module, all parallel).
