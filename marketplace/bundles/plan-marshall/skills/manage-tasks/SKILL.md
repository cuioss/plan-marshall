---
name: manage-tasks
description: Manage implementation tasks with sequential sub-steps within a plan
user-invocable: false
mode: script-executor
scope: plan
---

# Manage Tasks Skill

Manage implementation tasks with sequential sub-steps within a plan. Each task references deliverables from the solution document and contains ordered steps for execution.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Do not bypass dependency checking unless explicitly using `--ignore-deps`
- Task numbering is sequential and immutable (TASK-001, TASK-002, etc.)
- Adding a task uses the three-step path-allocate pattern: `prepare-add` → write TOON file → `commit-add`. No multi-line content is marshalled through the shell boundary.
- Step finalization requires explicit `--outcome` (done, skipped, or failed)

## Storage Location

Tasks are stored in the plan directory:

```text
{plan_dir}/tasks/
  TASK-001.json
  TASK-002.json
  TASK-003.json
```

**Filename format**: `TASK-{NNN}.json` (task type is stored in the JSON `type` field)

---

## File Format (Summary)

Tasks are stored as `TASK-{NNN}.json`. Key fields for quick reference:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Task title |
| `status` | enum | `pending`, `in_progress`, `done`, `blocked`, `infeasible` |
| `domain` | string | Task domain (e.g., java, javascript) |
| `profile` | string | Workflow profile (`implementation`, `module_testing`, `integration_testing`, `quality`, `verification`) |
| `skills` | list | Pre-resolved domain skills (`{bundle}:{skill}` format) |
| `origin` | string | Task origin: `plan`, `fix`, `sonar`, `pr`, `lint`, `security`, `documentation` |
| `deliverable` | int | Referenced deliverable number (1:1 constraint) |
| `steps` | array | Ordered file-path targets with status |

See [standards/task-contract.md](standards/task-contract.md) for the complete field specification, status model, dependency format, skills inheritance, and optimization workflow.

---

## Operations

Script: `plan-marshall:manage-tasks:manage-tasks`

| Command | Parameters | Description |
|---------|------------|-------------|
| `prepare-add` | `--plan-id [--slot]` | Allocate a scratch path under `<plan>/work/pending-tasks/` (Step 1 of add flow) |
| `commit-add` | `--plan-id [--slot]` | Read the prepared TOON file, validate, create TASK-NNN.json, delete scratch (Step 3 of add flow) |
| `batch-add` | `--plan-id (--tasks-file PATH \| --tasks-json JSON \| stdin)` | Atomically create N tasks from a JSON array. Preferred form is `--tasks-file PATH` pointing at a staged plan-relative file (e.g. `work/tasks-batch.json`); `--tasks-json` and stdin remain available for trivial payloads. The two flags are mutually exclusive. All-or-nothing semantics: if any entry fails validation, no `TASK-NNN.json` is written. |
| `update` | `--plan-id --task-number [--title] [--description] [--depends-on] [--status] [--domain] [--profile] [--skills] [--deliverable] [--cost-size] [--predicted-cost-tokens] [--envelope-id]` | Update task metadata. The three cost-field flags are the sole write path for the T-shirt cost mechanism — they persist `cost_size` (`S`/`M`/`L`/`XL`), `predicted_cost_tokens` (non-negative int), and `envelope_id` (1-based positive int) onto the task record, mirroring the read shape surfaced by `next`. The `derive-cost-size` / `pack-envelopes` compute verbs stay pure; this verb is where their output lands on disk. |
| `remove` | `--plan-id --task-number` | Remove a task |
| `list` | `--plan-id [--status] [--deliverable] [--ready] [--domain] [--profile]` | List all tasks; `--domain` / `--profile` filter the result set |
| `read` | `--plan-id --task-number` | Read single task details |
| `exists` | `--plan-id --task-number` | Boolean presence probe — returns `status: success exists: true\|false`, never errors on absence (use instead of `read` for existence checks) |
| `next` | `--plan-id [--include-context] [--ignore-deps]` | Get next pending task/step |
| `next-tasks` | `--plan-id` | Get all tasks ready for parallel execution |
| `finalize-step` | `--plan-id --task-number --step --outcome [--reason] [--outcome-task-title] [--outcome-step-count] [--outcome-caller]` | Complete step with outcome (done/skipped/failed). When the call closes a task as `done`, the script emits one canonical `[OUTCOME] ({caller}) Completed TASK-NNN: {title} ({M} steps)` work-log line — see "Script-Level [OUTCOME] Emission" below for the contract and overrides. |
| `add-step` | `--plan-id --task-number --target --intent [--after]` | Add step to task |
| `update-step` | `--plan-id --task-number --step-number --intent --reason [--finding-id]` | Update step intent and reason (e.g., to record a triage finding reference) |
| `remove-step` | `--plan-id --task-number --step` | Remove step from task |
| `rename-path` | `--plan-id --old-path --new-path` | Record path rename and rewrite step targets |
| `qgate-mechanical-checks` | `--plan-id [--no-emit]` | Run the deterministic Q-Gate checks for phase-4-plan Step 8: coverage, skill-resolution, acyclic, files-exist, keyword-drift, structural-token-drift, plus the two CLOSURE checks — declared-set-closure and declared-scope-reconciliation. The first six ask whether each declared thing is well-formed and resolves; the closure pair asks whether the declared SET is complete, which none of the others can see. Pure regex + graph + filesystem; no LLM dispatch. Each failure becomes a Q-Gate finding under `--source qgate` so phase-4-plan's existing aggregate consumes it. Returns `total_failed`, per-check counts, a `population` block reporting what each closure check actually scanned (with `population_complete`), and an `ambiguous` flag the caller uses to decide whether the LLM q-gate-validation dispatch still needs to fire — `ambiguous` flips on an unparseable outline OR an incomplete closure population, since a zero over an unscanned set is not a verdict. Also returns `qgate_persist_failed` (bool) and `qgate_persist_failures` (list of `{title, message}`) — a persist the Q-Gate primitive rejected means the check failed but its finding never reached the store, so the caller MUST fail loudly on `qgate_persist_failed: true` rather than trusting `total_failed` alone. |
| `loop-exit-guard` | `--plan-id` | Script-level enforcement of the phase-5-execute "unfinished > 0 → must continue" invariant. The predicate is the union of `pending` AND `in_progress` tasks. Emits `status: continue` (with `pending_count`, `pending_ids`, `in_progress_count`, `in_progress_ids`) when EITHER bucket is non-empty — the non-success status forces the orchestrator to re-dispatch the execution-context. Emits `status: success` (with all four count/id fields present and zero-valued) only when BOTH counts are zero. See "Loop-Exit Guard" below for the contract. |
| `pre-commit-verify-freshness` | `--plan-id` | Script-level enforcement that the current working-tree state has been observed by a successful build before any pre-commit transition — but only where a build was necessary at all. Consults the command-free `build-decision` verdict first, then queries the unified change-ledger for a `kind=build` entry with `status == success` whose `worktree_sha` matches the recomputed working-tree currency hash, and finally cross-checks the matching rows on two dimensions — their notations against the build notations this project's architecture resolves, and the canonical + scope they recorded against the blast radius of the change. Emits `status: fresh` (verdict `not_necessary`, with the verdict's own `reason` forwarded verbatim, or a matching successful build entry citable on BOTH dimensions — `notation_cross_check` and `scope_cross_check` say whether each was audited or merely undetermined, and the record names the matched row and every candidate's recorded scope), `status: stale` (no successful build matches the current working-tree sha, or every one that does names a build this project never runs, or every one that does is narrower than the change — carrying a `reason` that names WHICH route: `worktree_mutated`, `build_error`, `build_timeout`, `build_killed`, `build_indeterminate`, `notation_unrelated`, `notation_absent`, `build_scope_narrow`, or `no_row_both_attributable_and_adequate`, since the routes need different remedies and a `killed` build must never be blind-retried), or `status: undecidable` (no positive proof — `no_registry` when the ledger is absent/empty, `head_unresolvable` when the working-tree sha cannot be computed). Fail-closed contract: only `fresh` permits transition. See "Pre-Commit Verify Freshness" below for the contract. |

### Loop-Exit Guard (`loop-exit-guard`)

`loop-exit-guard` is the script-level enforcement of the phase-5-execute
dispatch loop's "unfinished > 0 → must continue" invariant. The predicate
is the union of two unfinished terminal-state buckets: `pending` (task
never started) AND `in_progress` (task started but not finalized — e.g.,
the dispatch that began it terminated mid-flight). The orchestrator
(`plan-marshall:plan-marshall:execution.md`) consults this verb on every
loop-exit decision before classifying a dispatch as a clean exit; the
phase-5-execute SKILL.md § Step 12a (Pending-tasks transition guard) is a
thin pointer to this verb — the authoritative unfinished-count is here,
not in skill prose.

**Blocking states (resumability):**

| Status | Blocks clean exit? |
|--------|--------------------|
| `pending` | Yes — task never started |
| `in_progress` | Yes — task started but not finalized (mid-flight) |
| `done` | No — terminal success |
| `failed` | No — terminal failure |
| `blocked` | No — explicit triage outcome |
| `infeasible` | No — terminal explicit-triage outcome (deliverable cannot be built as scoped) |

Both `pending` and `in_progress` are unfinished terminal states by the
broadened predicate. Either non-empty bucket forces `status: continue`.

**TOON return contract:**

Both `continue` and `success` branches emit all four count/id fields so
callers can read either axis without conditional presence checks:

```toon
status: continue | success
plan_id: {plan_id}
pending_count: N
pending_ids[N]: [task_numbers]
in_progress_count: M
in_progress_ids[M]: [task_numbers]
message: "..."
```

- `status: continue` with `pending_count > 0` OR `in_progress_count > 0` —
  at least one unfinished task remains. The orchestrator MUST re-dispatch
  the execution-context and MUST NOT classify the return as
  `clean_exit_queue_empty`. The `message` field names which axis was
  non-empty so the orchestrator's log surfaces the reason.
- `status: success` with `pending_count: 0` AND `in_progress_count: 0` —
  queue empty by the broadened predicate, clean exit permitted. The
  boundary-call fence in `plan-marshall/workflow/execution.md` may now
  record `termination-cause == clean_exit_queue_empty`.

**Rationale:** before this verb, the loop-exit decision was driven by the
dispatched agent's terminal payload, which the agent could echo verbatim
(e.g. `task_complete`) without the orchestrator distinguishing "one task
done out of three" from "the queue is empty". Moving the decision to a
script-level read of disk state — the same `get_all_tasks` machinery as
`list --status pending` — closes the control-flow gap. The original
predicate considered only `pending`, which left a residual seam: a task
that flipped to `in_progress` and was abandoned mid-dispatch would leave
the queue "empty by the pending bucket" while the task itself was still
unfinished. Broadening the predicate to `pending OR in_progress` closes
that residual seam.

### Pre-Commit Verify Freshness (`pre-commit-verify-freshness`)

`pre-commit-verify-freshness` is the script-level enforcement of the
necessary-vs-sufficient gap between `loop-exit-guard` (queue-empty proof) and
the pre-push state (worktree-actually-verified proof). `loop-exit-guard`
answers a structurally narrower question ("is the task queue empty?") than
what the pre-commit gate needs ("has the codebase actually been verified
against its current on-disk state?"). This verb closes the gap by querying the
unified change-ledger for a `kind=build` entry with `status == success` whose
`worktree_sha` matches the recomputed working-tree currency hash. The two
guards are complementary, not redundant: queue-emptiness and verify-freshness
must BOTH be true before any pre-commit transition.

The gap this closes: the orchestrator can dispatch `push` against a tree
that no successful build has observed if the loop-exit guard is the only gate
checked.

**Question answered:** *given that a build was necessary at all*, does a
successful `kind=build` ledger entry exist that was stamped against the CURRENT
working-tree state?

The necessity half is never re-derived here. The gate consults the single
build/no-build authority through the **command-free** verdict — it asks the
plan-wide "does anything in this footprint need a build?" question with no
canonical command, and MUST NOT pick a representative one. A `not_necessary`
verdict short-circuits to `fresh` carrying the verdict's own `reason` verbatim,
because no `kind=build` entry could ever legally be stamped for a footprint that
needs no build, so demanding one is an impossible demand rather than a gate. A
`build` verdict falls through to the ledger scan unchanged. The verdict's
predicate is owned by
[`doc/adr/004`](../../../../../../doc/adr/004-The_file-to-build_contract_is_owned_by_build-system_extensions_not_languagecontent_domains.adoc)
§ "Amendment: `build-decision` is the sole build/no-build authority" — it is not
restated here.

The `worktree_sha` is the working-tree currency hash (staged + unstaged +
untracked-not-ignored), NOT the committed `HEAD`. This is deliberate: at
gate time the plan's edits are still uncommitted, so a `HEAD`-based primitive
would match trivially regardless of any uncommitted change between build and
gate (a false-positive `fresh`). Folding the uncommitted state into the sha
means an edit after a clean-tree build changes the sha, and the gate correctly
reports `stale`.

The ledger query's **primary predicate** filters on `kind`, `status`, and
`worktree_sha` only — never `exit_code` or `plan_id` — so it stays
tier-agnostic: an orchestrator-driven global-tier build recorded under the
`NO_PLAN` sentinel satisfies the gate exactly as a plan-scoped build does.
Requiring `status == success` rather than
`exit_code == 0` is load-bearing: the build wrapper exits 0 on timeout (the
outcome lives in its stdout TOON, not the exit code), so an exit-code
predicate would launder a build that never finished into a false `fresh`. A
row lacking `status` never matches — the gate fails closed to `stale` — and
neither does a row carrying the boundary-derived `unknown` (an exit-0 dispatch
whose stdout payload the boundary could not read), so an unreadable build report
fails closed exactly as a missing one does. The
`kind=build` entry is stamped by the executor dispatch boundary after every
build-class invocation that runs to completion. See
[`../manage-change-ledger/SKILL.md`](../manage-change-ledger/SKILL.md) for the
ledger API (entry schema, `query` verb, and the `kind=build` writer) — the
ledger query semantics are not inline-copied here.

#### The notation cross-check

A row matching the primary predicate proves a row EXISTS; it does not prove the
row is evidence of a build **this project performs**. The gate has been
satisfied by a row naming a package-manager build the project has no module
for — the verdict was right, the evidence did not support it, and nothing in
the output said so. A gate that is right for the wrong reason produces no
failure to learn from, so it can stay wrong indefinitely.

Every row that clears the primary predicate is therefore cross-checked against
the build notations this project's architecture actually resolves to
(`manage-architecture`'s `resolve_project_build_notations`, which classifies
every module's resolved command map). The comparison target is the
**architecture**, deliberately not the ledger: comparing ledger rows against
other ledger rows would let a polluted ledger corroborate itself. The check
stays build-TOOL-agnostic — a Maven/Gradle/npm build satisfies the gate whenever
the architecture resolves that notation for this project — and it stays
plan-agnostic, because the notation set is the union over every module rather
than a per-plan subset.

The verdict is three-valued and is **never** collapsed to two:

| `notation_cross_check` | Meaning | Gate effect |
|---|---|---|
| `corroborated` | The row's notation is one the architecture resolves | `fresh` |
| `refuted` | The architecture resolved a non-empty set and **no** candidate row's notation is in it — including the case where no candidate carries a `notation` at all | `stale` (`notation_unrelated` / `notation_absent`) |
| `unverified` | The notation set could not be established | `fresh`, with the inability stated in the record |

The split fail-direction is deliberate. A **refutation is positive knowledge**
("the architecture resolves pyproject and nothing else; this row says npm"), so
it fails closed — that is the defect class the gate exists to close, and
admitting it with a warning would leave the false-green in place while merely
annotating it. An **inability to resolve is the absence of knowledge**, so it
passes with `notation_cross_check: unverified` and a
`notation_cross_check_reason` in the record: failing closed there would block
every legitimate pre-commit transition in a tree whose architecture has not been
discovered — a project mid-onboarding, a fresh clone, a fixture tree — none of
which is evidence of anything wrong, and the primary predicate has already been
satisfied at that point. `unverified` is a stated sentinel, never a quiet
`corroborated`, so "passed uncross-checked" stays legible to a reader (ADR-015).

The three inabilities behind `unverified` are named apart for the same reason,
even though all three pass the gate identically — the distinction is for the
reader asking why nothing ever corroborates, and it has different owners:

| `notation_cross_check_reason` | What it means | Who owns it |
|---|---|---|
| `architecture_resolver_unimportable` | The resolver module could not be imported at all | **This check is broken.** A deployment or `PYTHONPATH` fault; it will report `unverified` on every row forever, so it is not a quiet pass but a silent outage. |
| `architecture_resolution_failed` | The resolver was reached and raised while running | The architecture query — a crawl that failed against this tree. |
| `architecture_resolved_no_build_notations` | The resolver ran and found no build notation anywhere | Nobody: the ordinary un-crawled or greenfield project. This is the legitimately quiet case. |

⛔ An empty resolved set is an **inability**, never a refutation. Reading it as
"this project builds with nothing" would refuse every real build row the ledger
holds — a false-red manufactured from an absence of data.

Every candidate row is examined, not just the first match. A project that
legitimately builds with several notations can carry an unrelated row ahead of a
related one in ledger file order, and a first-match return would refuse evidence
two lines further down.

**A doc-only carve-out is refused**, and the refusal is recorded in the shipped
source (`_freshness_crosscheck` module docstring) rather than only in a run
report, because an unexplained absence invites its re-introduction. Markdown
under the bundle tree **is a build input in this repository** — tests read and
assert on the bodies of bundle documents — so a doc-only freshness exemption
would hand back `fresh` for a tree whose tests were never run against it, which
is this very defect class re-entering through the exemption. Build necessity is
in any case owned by the `build-decision` authority the gate consults first, not
by a suffix list here.

#### The scope cross-check

Attribution answers *"was this row written by a build of this project?"*. It
cannot answer *"did that build cover this change?"*, and the two are not the same
question: **every `pyproject_build` invocation carries the identical notation**,
so a zero-test `compile` and a whole-tree `verify` are indistinguishable on the
attribution dimension alone.

That gap produced its own false-green. At worktree sha `858061bc` the ledger held
three `kind=build` rows for the SAME tree — a whole-tree `module-tests` that
TIMED OUT, a module-scoped `module-tests` that FAILED, and a single-directory
573-test run that SUCCEEDED. The gate returned `fresh` on the third and reported
its evidence `corroborated`.

The scope needed to catch that was already in the substrate: every row records
`args` (the executor argv) and `outcome` (the wrapper's own stdout TOON). This is
a gap in the PREDICATE, not in the data. Each candidate row is therefore also
compared on **blast radius**:

| Side | Source | What it yields |
|---|---|---|
| The row | `args`, at `--command-args` | The canonical it ran and the scope tokens that followed — no tokens means whole-tree |
| The row | `outcome.tests_run` + `outcome.tests_population` | Whether it MEASURED that it executed zero tests |
| The change | the live plan footprint via `_test_scope_divergence.resolve_test_scope` | The module set a scoped run must cover, and whether only a whole-tree run will do |

`args` is the scope source rather than `command` because it is *our* argv shape,
uniform across build tools: the canonical and its scope always follow
`--command-args`. `command` is the wrapper's own resolved line, so its shape is
build-tool-specific — `mvn -pl mod verify` carries the module in a flag that
*precedes* the goal, and a generic reader scanning for the first canonical token
would see `verify` with nothing after it and conclude *whole-tree*. That is the
false-green direction, so `command` is **not** used as a fallback: a row whose
`args` carries no `--command-args` is reported undetermined rather than guessed
at.

**What the change requires is DERIVED, not fixed.** A non-empty footprint
requires the `test` analysis unconditionally (markdown under the bundle tree is a
build input — the same reasoning that refuses the doc-only carve-out above), and
additionally requires `compile` + `lint` only when the footprint contains a `.py`
path. Whether a scoped row suffices is `resolve_test_scope`'s
`divergence_possible` verbatim — the single existing authority on whether a
scoped run could pass while a whole-tree run fails. So the gate demands a
whole-tree `verify` only of a change whose blast radius is whole-tree, and
demands no type-check at all of a change that altered no source.

| `scope_cross_check` | Meaning | Gate effect |
|---|---|---|
| `covered` | At least one row's canonical performs every required analysis, its scope covers the required modules, and it did not measure zero tests | `fresh` |
| `narrow` | Every readable row is provably narrower than the change — a weaker canonical, a narrower scope, or a measured zero tests | `stale` (`build_scope_narrow`) |
| `undetermined` | The comparison could not be performed on one side or the other | `fresh`, with the inability stated in the record |

The split fail-direction is the same one the attribution dimension takes, for the
same reason: only a positive refutation fails closed. `row_scopes` publishes what
each candidate actually recorded (`'{canonical} {scope}: {covered|refusal}'`), so
a refusal names *which* row was narrow and *how*, rather than only that one was.

The `undetermined` reasons are named apart, again because they have different
owners:

| `scope_cross_check_reason` | What it means | Who owns it |
|---|---|---|
| `analysis_vocabulary_unimportable` | The canonical→analyses map (`_build_examined`) could not be imported | **This check is broken** — a deployment or `PYTHONPATH` fault, not a quiet pass. |
| `required_coverage_unknown` | The live footprint or the registered-module set could not be resolved | The plan state — a worktree not yet materialised, or an unreadable marketplace root. |
| `build_scope_unreadable` | Rows were read, but none carries a usable `--command-args` or names a canonical in the vocabulary | The producer — something wrote rows the dispatch boundary would not have written. |

⛔ An unresolvable footprint is an **inability**, never an empty one. Rendering it
as "the change requires nothing" would make every row cover it, re-opening the
exact false-green this dimension closes.

#### Joint selection

The two dimensions are reported separately and **never folded**, but selection
across them is **joint**: a row may be cited as the gate's evidence only when it
is admissible on both — endorsed by a dimension, or unjudged by it. Per-dimension
selection is what let the 573-test directory row be cited as `corroborated`: it
was perfectly attributable, and nothing asked whether it covered the change.

Where the two admissible sets are disjoint — every attributable row was narrow
AND every covering row was unattributable — neither dimension refused, yet
nothing is citable. That state carries its own reason,
`no_row_both_attributable_and_adequate`, rather than borrowing either
dimension's: a reader told `build_scope_narrow` there would go looking for a
refusal the coverage check never made.

**Return statuses (fail-closed contract):**

- `status: fresh`, `reason: <verdict reason>` — the command-free `build-decision`
  verdict is `not_necessary` for the plan's live footprint, so no build was
  required and no `kind=build` ledger entry could exist. The gate short-circuits
  to `fresh` BEFORE the ledger scan and forwards the verdict's own `reason` text
  verbatim; the gate invents no exemption vocabulary of its own.
- `status: fresh` — a `kind=build` entry with `status == success` and a matching
  `worktree_sha` exists AND one such entry is citable on BOTH cross-check
  dimensions, so the gate is permitted to pass. The record **names its
  evidence**: `worktree_sha`, `matched_notation`, `matched_entry_index` (the
  row's position among the ledger's *parsed* entries — `read_entries` skips blank
  lines, unparseable lines, and valid-JSON-non-object lines, so this is not a
  physical line number and a divergence between the two is not by itself evidence
  of corruption), `matched_plan_id`, `timestamp_iso`, `notation_cross_check`
  (`corroborated` or `unverified`), `scope_cross_check` (`covered` or
  `undetermined`), `expected_notations` (the resolved set), `row_scopes` (what
  each candidate recorded), `worktree_root`, and `ledger_path`. A pass that a
  dimension could not audit additionally carries that dimension's
  `notation_cross_check_reason` / `scope_cross_check_reason`. Naming the row is
  what converts a silent wrong-reason pass into a visible one, and it holds even
  where a cross-check itself could not run.
- `status: stale` — the ledger has entries but none is citable: either none is a
  successful build against the current working-tree sha, or every such build
  names a notation this project does not resolve, or every such build is narrower
  than the change, or the attributable and covering rows are disjoint. The gate
  MUST fail closed. Carries `worktree_sha`, `worktree_root`, `ledger_path`, and a
  **`reason` naming which route to `stale` was taken** — plus `observed_status`
  (the offending row's own build status) whenever a row carried a readable status
  string, and `notation_cross_check` / `scope_cross_check` /
  `expected_notations` / `candidate_notations` / `row_scopes` on every
  cross-check route. `observed_status` is absent on `worktree_mutated` (no row
  was observed), on the `build_indeterminate` sub-case where the row carried no
  readable `status` at all, and on every cross-check route (where every candidate
  was `success`, so reporting it would say nothing); supplying one where none was
  read would mean inventing it, so its absence is the honest answer and `reason`
  still separates the routes. The pass/fail behaviour is identical on every
  route; what differs is the remedy, and the gate must not assert a cause it did
  not establish:

  | `reason` | Ledger evidence | Remedy the caller owes |
  |---|---|---|
  | `worktree_mutated` | NO `kind=build` row of any status carries this sha | The tree really did move past every observed build — re-dispatch a build. |
  | `build_error` | Latest row for this sha is `status: error` | The build ran and reported failures — fix them, then re-build. |
  | `build_timeout` | Latest row for this sha is `status: timeout` | The build exceeded its own outer budget; no verdict was reported. Not a code defect. Re-run, and diagnose the budget if it recurs. |
  | `build_killed` | Latest row for this sha is `status: killed` | Externally killed — **not flaky, do not blind-retry.** No budget fired and no verdict was reported. Establish why before re-running. |
  | `build_indeterminate` | Latest row for this sha is `status: unknown`, or a status outside the vocabulary | The outcome could not be read. It supports no conclusion either way; re-run to obtain a readable verdict. |
  | `notation_unrelated` | Successful rows carry this sha, but every notation they name is one the architecture does not resolve | The rows are evidence of some other project's build. Dispatch a real build of THIS project — and establish where the unrelated row came from before trusting the ledger again. |
  | `notation_absent` | Successful rows carry this sha, but **none** carries a usable `notation` — the key is missing, empty, or not a string | `build_record` always emits a non-empty `notation` for a dispatched build, so no such row came from the dispatch boundary. Something other than a build of this project is writing to the ledger; find it. |
  | `build_scope_narrow` | Successful, attributable rows carry this sha, but every readable one records a build narrower than the change — a canonical performing too few analyses, a scope not covering the change's modules, or a measured zero tests | Re-run a build whose canonical and scope cover this change. `row_scopes` names what each row actually ran, so it says which of the three routes each took. |
  | `no_row_both_attributable_and_adequate` | Neither dimension refused, yet no single row satisfies both — every attributable row was narrow AND every covering row was unattributable | Both remedies at once: re-run an adequate build, AND establish where the unattributable covering row came from. |

  The two `notation_*` routes are mutually exclusive and `notation_unrelated`
  wins a mixed set: a candidate list holding one notation-less row and one
  unresolved-notation row reports `notation_unrelated`, because
  `candidate_notations` is non-empty. `notation_absent` therefore means *every*
  candidate lacked a notation, not *some* did — read `candidate_notations` to see
  which notations were actually present, and treat an empty list under
  `notation_unrelated` as impossible by construction.

  `worktree_mutated` is the only route on which the tree is known to have
  changed. On the `build_*` routes a build **was** observed against exactly this
  tree and did not produce a green — reporting those as a mutation would name a
  cause that did not occur, and prescribing the mutation remedy (re-dispatch) is
  precisely the blind retry a `killed` build forbids. On the two `notation_*`
  routes a green **was** recorded against this tree, but by something the
  architecture cannot attribute to this project, so the remedy is an
  investigation and not only a re-build. On `build_scope_narrow` a green was
  recorded by a build this project really does perform — it simply did not look
  at enough of the tree, so the remedy is a wider build and nothing else.
- `status: undecidable` — no positive freshness proof can be established. Two
  sub-reasons: (a) `reason: no_registry` — the change-ledger file is absent or
  empty; (b) `reason: head_unresolvable` — the working-tree sha cannot be
  computed (a non-git directory or a repo with no commit). Both sub-reasons
  MUST be treated as gate failure.

**Canonical invocation:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  pre-commit-verify-freshness --plan-id {plan_id}
```

**Wired-in gates:** the dispatcher prose lives at:

- `phase-5-execute/SKILL.md` § Step 12a — Pending-tasks transition guard
  (now a co-equal gate alongside `loop-exit-guard`).
- `phase-6-finalize/SKILL.md` and `phase-6-finalize/standards/push.md`
  § "Freshness precondition" — fires BEFORE the clean-tree assertion of
  `push`.

Both gates fail closed on any non-`fresh` status and emit a `[BLOCKED]` work-log
line carrying the reason and the working-tree sha. The `--force` orchestrator
escape mirrors the existing pending-tasks-guard escape — deliberate,
log-recorded override for triage-driven aborts. Never invoked programmatically
from inside the loop.

**Algorithm (deterministic; no LLM dispatch):**

1. Consult the single build/no-build authority with NO canonical command
   (`should_execute_build(None, plan_id)` — the same verdict
   `manage-config build-decision --plan-id {plan_id}` returns without
   `--command`). That verdict has **three** values, and only one of them
   short-circuits this gate:

   - `not_necessary` — the positive answer that nothing here needs building.
     Return `fresh` and forward the verdict's `reason` verbatim. This is the
     ONLY value that short-circuits.
   - `unknown` — the footprint is unresolvable, so there is no evidence either
     way. **Do NOT short-circuit to `fresh`.** Fall through to the ledger scan,
     which decides on real evidence and returns `stale` / `undecidable` when it
     finds none. Treating an unsubstantiated verdict as a positive one would let
     an unverified worktree pass the gate — exactly the fail-closed discipline
     ADR-009 requires.
   - `build` — fall through to the ledger-scan steps below.

   A verdict that cannot be obtained at all degrades to the fall-through path in
   the same fail-closed direction.
2. Resolve the worktree root via `status.metadata.worktree_path`; fall back to
   the current working directory when no worktree is materialised.
3. Recompute the current working-tree sha (`compute_worktree_sha` — staged +
   unstaged + untracked-not-ignored). When it cannot be computed (non-git
   directory or a repo with no commit), return `undecidable` with
   `reason: head_unresolvable`.
4. Read the change-ledger entries. When the ledger file is absent or empty,
   return `undecidable` with `reason: no_registry`.
5. Collect **every** entry with `kind == build`, `status == success`, and
   `worktree_sha` equal to the current working-tree sha, in ledger file order.
   A row lacking `status` never matches (fail-closed for pre-existing rows).
6. No candidate → `stale`, with the route derived from what the ledger holds.
7. Candidates exist → cross-check them on **both** dimensions and select
   **jointly**. Per dimension, compute the set of candidates it admits — the rows
   it endorsed, or *every* row when it could not judge:

   - **Attribution.** Resolve this project's build-notation set from the
     architecture. The *attributable* rows are those whose `notation` is in that
     set (`notation_cross_check: corroborated`). When the set cannot be resolved
     the dimension judges nothing and admits **every** row, recording
     `notation_cross_check: unverified` with its reason. When the set resolved and
     no row is in it the dimension REFUTES, and no row is citable.
   - **Coverage.** Derive what the change needs to be covered (§ "The scope
     cross-check"). The *coverable* rows are those whose canonical performs every
     required analysis, whose scope covers the required modules, and which did not
     measure zero tests (`scope_cross_check: covered`). When the comparison could
     not be performed on either side the dimension judges nothing and admits
     **every** row, recording `scope_cross_check: undetermined` with its reason.
     When every readable row is provably narrower the dimension REFUSES
     (`scope_cross_check: narrow`), and no row is citable.

   The gate cites the **first row in file order that both dimensions admit** →
   `fresh`. Nothing citable → `stale`, with the reason decided in this order:

   | Condition | `reason` |
   |---|---|
   | Attribution refuted | `notation_unrelated` (some candidate carried a notation) or `notation_absent` (none did) |
   | Coverage refused | `build_scope_narrow` |
   | Neither refused, yet the two admissible sets are disjoint | `no_row_both_attributable_and_adequate` |

   ⛔ **Selection is joint, never per-dimension.** A row endorsed by one
   dimension is not citable unless the other also admits it. Letting attribution
   pick on its own is precisely how the 573-test single-directory row was cited as
   `corroborated` for a whole-tree change — perfectly attributable, and nothing
   asked whether it covered the change. See § "Joint selection".

   ⚠ **Step 7 costs a live architecture crawl, and the consuming site should
   budget for it.** The resolution runs the same crawl `architecture resolve`
   runs — memoized per process, but the gate is a one-shot process, so the memo
   never carries between invocations and each of the gate's two wiring points
   (phase-5 Step 12a, phase-6 `push`) pays it once. It shells out: `git` on every
   project, plus each build tool's own discovery verbs on a Maven/Gradle/npm one
   (`crawl_all_modules` documents `help:all-profiles dependency:tree` per Maven
   module). Measured on this repository — Python-only — the first crawl took
   roughly 1 to 5 seconds, across four independent measurements in different
   sessions and filesystem-cache states; the spread is the honest answer and a
   point estimate would not be. No figure exists for a Maven, Gradle or npm
   project, so treat that range as a floor there rather than an estimate. Two
   properties bound the cost: it is paid only on the path where the primary
   predicate ALREADY matched (a `stale` refusal never crawls), and the
   short-circuit ahead of it means a footprint needing no build never reaches
   Step 4, let alone Step 7.

The algorithm never raises uncaught exceptions on a degenerate input, but it
does **not** refuse on all of them, and the difference matters more than the
absence of a crash:

| Degenerate input | Outcome | Why |
|---|---|---|
| Ledger absent or empty | `undecidable` / `no_registry` | No evidence exists at all. |
| Working-tree sha uncomputable | `undecidable` / `head_unresolvable` | The primitive the whole gate compares on is undefined. |
| Worktree unresolvable | **Not a refusal.** `WorktreeResolutionError` is caught and the root falls back to the process cwd; the sha and the ledger scan proceed against *that* tree | Preserves the pre-existing non-fatal behaviour for a plan running against the main checkout. ⚠ It means the gate can answer about a tree other than the one the caller had in mind, which is a real limitation and is recorded rather than papered over. |
| Status metadata missing | Irrelevant | The gate does not read it — the worktree root resolves through `resolve_plan_context`, and `status.metadata.worktree_path` is a decoy the tests pin as ignored. |
| Architecture unresolvable | **Not a refusal on this dimension.** Attribution records `notation_cross_check: unverified` with the inability named and admits every candidate; the verdict is then whatever the coverage dimension leaves — `fresh` when a row is still citable, `build_scope_narrow` when coverage positively refutes every row | An inability to *audit* evidence the primary predicate already accepted. Failing closed would refuse every transition in an un-crawled tree on strictly less evidence than the primary predicate supplied — see § "The notation cross-check". An unjudged dimension abstains; it does not overrule the other one's refusal. |
| Coverage underivable | **Not a refusal on this dimension.** Coverage records `scope_cross_check: undetermined` with the inability named and admits every candidate; the verdict is then whatever attribution leaves | The mirror of the row above, for the same reason and with the same abstention semantics — see § "The scope cross-check". |

⛔ "The gate never raises" must never be read as "the gate always refuses on bad
input" — the `Outcome` column above is the authority on which inputs refuse.

### Script-Level `[OUTCOME]` Emission (`finalize-step`)

When a `finalize-step --outcome done` call closes the targeted task (i.e. all
steps are `done` AND no step is `failed`), the script emits exactly one
canonical work-log entry **before returning**:

```text
[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-NNN: {task_title} ({M} steps)
```

This emission is **unconditional and lives inside the script boundary** — it
fires for every task completion regardless of which orchestrator dispatched
the closing call. The emission lives inside the script boundary so it fires for every task completion
regardless of which orchestrator dispatched the closing call — a caller-side emission
is lost whenever the caller envelope is re-fired and its working context is discarded
before the `[OUTCOME]` line can be written.

**Defaults** (used when the optional overrides below are omitted):

| Field | Default |
|-------|---------|
| `caller` | `plan-marshall:phase-5-execute` |
| `task_title` | The `title` field of the task on disk |
| `step_count` | `len(task.steps)` |

**Optional overrides** (rarely needed; mainly for tests and non-default callers):

| Flag | Effect |
|------|--------|
| `--outcome-task-title TEXT` | Override `{task_title}` in the rendered line. |
| `--outcome-step-count N` | Override `{M}` (the step count) in the rendered line. |
| `--outcome-caller BUNDLE:SKILL` | Override the `({caller})` marker in the rendered line. |

The emission only fires for the *task-closing* call (the final step that
flips the task to `done`). It does NOT fire for `--outcome skipped`,
`--outcome failed`, or for intermediate `--outcome done` calls that leave the
task `in_progress`. Caller-side `[OUTCOME]` emissions in skills MUST NOT
duplicate this line — the script-level guard is the single source of truth.

### Add Flow — Three-Step Path-Allocate Pattern

Adding a task uses the same path-allocate pattern as every other content-passing
surface in the bundle. The script allocates a scratch path; the main context
writes the TOON definition directly with its native Write/Edit tools; a second
subcommand reads the file, validates it, creates `TASK-NNN.json`, and deletes
the scratch. No multi-line content ever crosses the shell boundary.

```bash
# Step 1: script allocates a scratch path under <plan>/work/pending-tasks/
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id {plan_id}
# → returns {path: /abs/.../work/pending-tasks/default.toon}

# Step 2: main context writes the TOON task definition to that path with Write/Edit.
# (No shell marshalling, no escaped \n. The Write tool does the work.)

# Step 3: script reads the file, validates it, and creates the task
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id {plan_id}
# → returns {status: success, file: TASK-003.json, ...}
```

**Concurrent adds**: pass `--slot <name>` to `prepare-add` and `commit-add` to
run multiple pending tasks side-by-side. Slot names must match
`[a-z0-9][a-z0-9-]{0,63}`. Omitting `--slot` uses the reserved slot `default`.

**TOON file format** (written to the path returned by `prepare-add`):

```toon
title: My Task Title
deliverable: 1
domain: plan-marshall-plugin-dev
profile: implementation
origin: plan
description: |
  Multi-line task description here.
  Can include any characters.

skills:
  - pm-plugin-development:plugin-maintain
  - pm-plugin-development:plugin-architecture

steps:
  - marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md (write-replace)
  - marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py (write-replace)
  - test/plan-marshall/manage-tasks/test_manage_tasks_crud.py (write-new)

depends_on: none

verification:
  commands:
    - python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate plan-marshall"
  criteria: Quality gate passes with no findings
  manual: false
```

**Required fields**: `title`, `deliverable`, `domain`, `profile`, `skills`, `steps`

**Optional fields**: `description`, `depends_on`, `verification`, `origin` (default: plan)

**Field values**:
- `deliverable`: Single positive integer (one deliverable per task, 1:1 constraint)
- `domain`: Domain from references.json (e.g., `java`, `javascript`, `plan-marshall-plugin-dev`)
- `profile`: Profile key from marshal.json. Standard profiles: `implementation`, `module_testing`, `integration_testing`, `quality`, `verification`, `standalone`
- `skills`: Array of `bundle:skill` format strings
- `steps`: Array of repo-relative file paths, each carrying a required trailing `(intent)` marker — `path/to/file.ext (intent)`, where intent is one of `read`, `write-new`, `write-replace`, `delete`. A step without the marker, or one that is not a file path, is rejected.
- `depends_on`: `none` or task references like `TASK-1, TASK-2`
- `origin`: `plan` (from task-plan), `fix` (from verify), `sonar`, `pr`, `lint`, `security`, or `documentation`

**List field forms**: structural parsing is delegated to the canonical
`plan-marshall:ref-toon-format` parser, so `steps`, `skills` and
`verification.commands` each accept three interchangeable shapes:

| Form | Shape |
|------|-------|
| Bare block | `steps:` followed by `  - path (intent)` rows |
| Length-declared | `steps[2]:` followed by the same `  - path (intent)` rows |
| Uniform array | `steps[2]{target,intent}:` followed by CSV rows `path,intent` — the shape `serialize_toon` emits for a stored task record |

Because the uniform-array form is accepted, a task record round-trips:
`parse_stdin_task(serialize_toon(task))` reproduces `steps`, `skills` and
`verification.commands` without loss.

**Outer quotes**: do not hand-quote list items. A value the serializer must
quote (one containing `:`, `,` or an embedded `"`) is accepted and unquoted
automatically; an outer quote on a value that needed none is rejected as an
anti-pattern.

### List/Next Filters

| Parameter | Description |
|-----------|-------------|
| `--deliverable` | Filter by deliverable number |
| `--ready` | Only tasks with satisfied dependencies |
| `--ignore-deps` | (next only) Ignore dependency constraints |

---

## Quick Examples

### Add a task

```bash
# Step 1: allocate scratch path
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id my-feature

# Step 2: Write tool writes TOON content to the returned path, e.g.:
#   title: Update misc agents to TOON
#   deliverable: 1
#   domain: plan-marshall-plugin-dev
#   profile: implementation
#   skills:
#     - pm-plugin-development:plugin-maintain
#   description: Migrate miscellaneous agents from JSON to TOON output format.
#   steps:
#     - marketplace/bundles/plan-marshall/agents/execution-context.md (write-replace)
#     - marketplace/bundles/plan-marshall/skills/ref-toon-format/SKILL.md (write-replace)
#   verification:
#     commands:
#       - python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate plan-marshall"
#     criteria: Quality gate passes with no findings

# Step 3: commit
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id my-feature
```

### Add a task with dependencies

Same three-step flow. The TOON definition written in Step 2 simply adds:

```toon
depends_on: TASK-1, TASK-2
```

### Concurrent adds with slots

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id my-feature --slot impl

python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id my-feature --slot tests

# ... Write TOON to both returned paths ...

python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id my-feature --slot impl

python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id my-feature --slot tests
```

### Atomic batch add (many tasks in one call)

`batch-add` accepts a JSON array of task records and atomically appends every
task in a single invocation. It is the recommended path when the caller already
has a structured task plan (e.g. `phase-4-plan` creating multiple tasks per
deliverable) and would otherwise run N×(`prepare-add` + Write + `commit-add`).

Semantics:

- **All-or-nothing**: every entry is validated before any file is written. On
  any validation failure the whole batch is rejected and no `TASK-NNN.json`
  file is created.
- **Sequential numbering**: numbers are assigned starting at the next
  available slot at call time and increment in array order.
- **Empty array** (`"[]"`) is a documented no-op that returns
  `tasks_created: 0`.
- The JSON array shape is documented in
  `standards/task-contract.md` § "Atomic Batch Insertion (`batch-add`)".

**Canonical form — `--tasks-file PATH` (path-allocate flow)**: stage the JSON
array under the plan's `work/` tree via `manage-files write`, then point
`batch-add` at the staged file. This keeps large batches off the shell
argument boundary, makes the input auditable as a plan artifact, and is the
form used by `phase-4-plan`:

```bash
# Step 1: stage the JSON array as a plan-relative file under work/
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files \
  write --plan-id my-feature --file work/tasks-batch.json \
  --content '[{"title":"Task A","deliverable":1,"domain":"java","profile":"implementation","skills":[],"steps":[{"target":"src/main/java/A.java","intent":"write-replace"}]},{"title":"Task B","deliverable":1,"domain":"java","profile":"module_testing","skills":[],"steps":[{"target":"src/test/java/ATest.java","intent":"write-new"}],"depends_on":["TASK-1"]}]'

# Step 2: persist the batch atomically by pointing batch-add at the staged file
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks batch-add \
  --plan-id my-feature \
  --tasks-file .plan/local/plans/my-feature/work/tasks-batch.json
```

**Secondary form — inline `--tasks-json` (trivial payloads only)**: provide
the array directly on the command line. This form is mutually exclusive with
`--tasks-file` and is intended for small, hand-written payloads where the
shell escaping cost is negligible. Phase-4-plan does NOT use this form.

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks batch-add \
  --plan-id my-feature \
  --tasks-json '[{"title":"Task A","deliverable":1,"domain":"java","profile":"implementation","skills":[],"steps":[{"target":"src/main/java/A.java","intent":"write-replace"}]}]'
```

The batch path replaces the per-task `prepare-add` + Write + `commit-add`
sequence in callers that produce many tasks at once. Single ad-hoc adds may
keep using the path-allocate flow.

### Probe whether a task exists (boolean — never errors on absence)

Use `exists` instead of `read` whenever the call is a presence check rather
than a data fetch. `read` returns exit code 1 (with an error TOON record)
when the task is absent — every such call shows up as a `[ERROR]` row in
`script-execution.log`, even when the caller intended to handle absence.
`exists` returns `status: success exists: true|false` for any task number,
so absence stays silent.

```bash
# Probe — always returns status: success
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks exists \
  --plan-id my-feature \
  --task-number 7
# → status: success
#   plan_id: my-feature
#   task: 7
#   exists: true|false
```

Pair `exists` with `read` when the caller needs the task body only after
confirming presence — the two-call pattern keeps the failure logs clean
without changing observable behavior.

### Get next task/step (respects dependencies)

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next \
  --plan-id my-feature
```

### List ready tasks only

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
  --plan-id my-feature \
  --ready
```

### Finalize step (mark done, skipped, or failed)

```bash
# Mark step as done
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id my-feature \
  --task-number 2 \
  --step 3 \
  --outcome done

# Skip step with reason
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id my-feature \
  --task-number 2 \
  --step 3 \
  --outcome skipped \
  --reason "File already exists"

# Mark step as failed with reason
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id my-feature \
  --task-number 2 \
  --step 3 \
  --outcome failed \
  --reason "Verification failed: test suite has 3 failures"
```

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-4-plan` | `prepare-add`, `commit-add`, `update` | Create tasks from deliverables; `update` stamps the derived cost fields (`--cost-size` / `--predicted-cost-tokens` at Step 6, `--envelope-id` at Step 7a) |
| `phase-5-execute` | `update`, `finalize-step` | Update task/step status during execution |
| Q-Gate iteration | `prepare-add`, `commit-add` | Create fix tasks from verification findings |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-5-execute` | `next`, `next-tasks`, `read` | Retrieve tasks for execution |
| `phase-6-finalize` | `list` | Query task completion for PR summary |
| Task executors | `read`, `finalize-step` | Read task details and mark steps done |

### With phase-4-plan dispatch

The `phase-4-plan` task-planning dispatch creates tasks during plan refinement using the three-step flow:

```bash
# Step 1
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  prepare-add --plan-id {plan_id}

# Step 2: Write TOON definition to the returned path via the Write tool
#   title: {task_title}
#   deliverable: {deliverable_number}
#   domain: {domain}
#   profile: {profile}
#   steps:
#     - {step1_path} ({step1_intent})
#     - {step2_path} ({step2_intent})
#   depends_on: none
#
# Each {stepN_path} is a repo-relative file path and each {stepN_intent} is one
# of read / write-new / write-replace / delete — the trailing marker is required.

# Step 3
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  commit-add --plan-id {plan_id}
```

### With plan-execute

Plan-execute iterates through tasks:
```text
LOOP:
  1. manage-tasks next --plan-id {plan_id}
  2. IF no next: DONE
  3. SPAWN implement agent
  4. CONTINUE
```

### With implement-agent

Implement agents execute steps:
```text
1. manage-tasks read --plan-id {plan_id} --task-number {N}
2. FOR EACH step: execute → finalize-step --outcome done|failed
3. RUN verification
```

---

## Deliverable-to-Task Relationship

Tasks reference deliverables from `solution_outline.md` using the `deliverable` field in stdin.

**Constraint**: Each task maps to exactly **one** deliverable (the `deliverable` field is a single integer, not a list). However, one deliverable can produce multiple tasks.

| Pattern | Description | Example |
|---------|-------------|---------|
| Simple | One task per deliverable | TASK-1 has `deliverable: 1`, TASK-2 has `deliverable: 2` |
| Multi-profile | One deliverable, multiple tasks | TASK-1 (implementation) and TASK-2 (module_testing) both have `deliverable: 1` |

**Multi-profile pattern**: When a deliverable needs both implementation and testing, phase-4-plan creates separate tasks per profile. Each task gets its own skill set and executor.

---

## Dependency Management

Tasks can depend on other tasks using the `depends_on` field in stdin:

```yaml
# Task 3 waits for Task 1 and Task 2 to complete
depends_on: TASK-1, TASK-2

# No dependencies
depends_on: none
```

**Dependency enforcement**:
- `next` command only returns tasks with satisfied dependencies
- Use `--ignore-deps` to bypass dependency checking
- Use `--ready` filter to list only ready tasks

**Blocked output**: When tasks are blocked by dependencies, `next` returns:

```toon
next: null
blocked_tasks[2]{number,title,waiting_for}:
1,Write tests,TASK-3
2,Deploy,TASK-3, TASK-4
```

---

## Status Model

**Task Status**: `pending` → `in_progress` → `done` | `failed` (or `blocked` | `infeasible`)

**Step Status**: `pending` → `in_progress` → `done` | `skipped` | `failed`

---

## Verification

The `verification` field is optional. When present:
- `commands`: List of shell commands to run after implementation (copied verbatim from deliverable's Verification field by phase-4-plan)
- `criteria`: Human-readable success criteria
- `manual`: If `true`, verification requires human judgment (automated commands may still run but results need review)

If a deliverable has no Verification section, the task is created without `verification`.

---

## Canonical invocations

The canonical argparse surface for `manage-tasks.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT,
matching its heading only — the body is never read; `manage-invocation-invalid` derives
its accept-set from a live `--help` walk rather than from this section. Consuming skills xref this section by
name (e.g., "see `manage-tasks` Canonical invocations → `finalize-step`") instead
of restating the command inline.

### prepare-add

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks prepare-add \
  --plan-id PLAN_ID [--slot SLOT]
```

### commit-add

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks commit-add \
  --plan-id PLAN_ID [--slot SLOT]
```

### batch-add

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks batch-add \
  --plan-id PLAN_ID \
  [--tasks-json JSON | --tasks-file PATH]
```

`--tasks-json` and `--tasks-file` are mutually exclusive. When neither flag is
supplied the array is read from stdin.

### update

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update \
  --plan-id PLAN_ID --task-number N \
  [--title TEXT] [--description TEXT] [--depends-on REFS ...] \
  [--status {pending|in_progress|done|blocked|infeasible}] \
  [--domain DOMAIN] [--profile PROFILE] [--skills CSV] [--deliverable N] \
  [--cost-size {S|M|L|XL}] [--predicted-cost-tokens N] [--envelope-id N]
```

The `--cost-size` / `--predicted-cost-tokens` / `--envelope-id` flags are the **only**
write path for the cost-sizing fields. The pure compute verbs `derive-cost-size` and
`pack-envelopes` never mutate task records (their unit tests assert purity); their
output is persisted onto the task record by this `update` verb. The persisted values
round-trip back out through `next` (`cost_size`, `predicted_cost_tokens`, `envelope_id`).
Validation: `--cost-size` must be one of `S`/`M`/`L`/`XL`; `--predicted-cost-tokens` must be
non-negative; `--envelope-id` must be a positive (1-based) integer. Each flag is independent —
supply only the field(s) being written. phase-4-plan Step 6 calls this verb to stamp the
derived cost, and Step 7a calls it to stamp the packed `envelope_id`. The size vocabulary,
signal weights, and size→token mapping are owned by the central rubric — see
[`../phase-4-plan/standards/cost-sizing.md`](../phase-4-plan/standards/cost-sizing.md) and the
Cost-Sizing Fields section of [`standards/task-contract.md`](standards/task-contract.md).

### remove

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks remove \
  --plan-id PLAN_ID --task-number N
```

### list

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
  --plan-id PLAN_ID \
  [--status {pending|in_progress|done|blocked|infeasible|all}] \
  [--deliverable N] [--ready] [--domain DOMAIN] [--profile PROFILE]
```

`--domain` and `--profile` are filter dimensions on `list` — there is no separate
`tasks-by-domain` / `tasks-by-profile` subcommand.

### read

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read \
  --plan-id PLAN_ID --task-number N
```

### exists

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks exists \
  --plan-id PLAN_ID --task-number N
```

### next

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next \
  --plan-id PLAN_ID \
  [--include-context] [--ignore-deps]
```

The `next` block surfaces three plan-time cost-sizing fields when they are present on the resolved task record — `cost_size` (T-shirt label `S`/`M`/`L`/`XL`), `predicted_cost_tokens` (predicted token magnitude), and `envelope_id` (bin-packer group identifier). They appear as `null` on tasks created before sizing ran. These fields are an integration surface only; the size label vocabulary, signal weights, and size→token mapping are owned by the central rubric — see [`../phase-4-plan/standards/cost-sizing.md`](../phase-4-plan/standards/cost-sizing.md) and the Cost-Sizing Fields section of [`standards/task-contract.md`](standards/task-contract.md). The phase-5-execute budget-bounded task loop consumes `envelope_id` to run only its assigned envelope group.

### next-tasks

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next-tasks \
  --plan-id PLAN_ID
```

### finalize-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id PLAN_ID --task-number N --step N \
  --outcome {done|skipped|failed} \
  [--reason TEXT] \
  [--outcome-task-title TEXT] [--outcome-step-count N] [--outcome-caller TEXT]
```

### add-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add-step \
  --plan-id PLAN_ID --task-number N --target TEXT --intent INTENT [--after N]
```

### update-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks update-step \
  --plan-id PLAN_ID --task-number N --step-number M \
  --intent INTENT --reason TEXT [--finding-id FINDING_ID]
```

### remove-step

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks remove-step \
  --plan-id PLAN_ID --task-number N --step N
```

### rename-path

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks rename-path \
  --plan-id PLAN_ID --old-path PATH --new-path PATH
```

### qgate-mechanical-checks

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks qgate-mechanical-checks \
  --plan-id PLAN_ID [--no-emit]
```

### pre-commit-verify-freshness

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks pre-commit-verify-freshness \
  --plan-id PLAN_ID
```

### pack-envelopes

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks pack-envelopes \
  --plan-id PLAN_ID --per-envelope-budget-tokens N
```

Deterministically packs the plan's tasks (number order) into budget-bounded execution **envelope groups** under `--per-envelope-budget-tokens`, assigning each task a 1-based `envelope_id`. The packer is a pure Next-Fit-in-task-order bin-packer (`scripts/_tasks_envelope.py`): it sums each task's pre-stamped `predicted_cost_tokens` (from `derive-cost-size`) and never re-derives a cost — the size→token mapping is owned by the central rubric, see [`../phase-4-plan/standards/cost-sizing.md`](../phase-4-plan/standards/cost-sizing.md). A task whose cost alone exceeds the budget lands alone in its envelope (the rubric's "~1 per envelope" XL case). The budget is config-sourced from `plan.phase-5-execute.per_envelope_budget_tokens` by the caller. The output carries `assignments_table` (one `{number, predicted_cost_tokens, envelope_id}` row per task in execution order) and `envelopes_table` (one `{envelope_id, task_count, total_cost_tokens}` row per envelope). The phase-5-execute budget-bounded task loop consumes each task's `envelope_id` to run only its assigned envelope group.

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `task_not_found` | Task number doesn't exist |
| `step_not_found` | Step number doesn't exist in task |
| `invalid_content` | TOON content parsing failed or missing required fields |
| `missing_required` | Required field missing (title, deliverable, domain, profile, skills, steps) |
| `circular_dependency` | Task dependency creates a cycle (detected during `next`) |
| `invalid_outcome` | Step outcome not `done`, `skipped`, or `failed` |
| `plan_dir_not_found` | Plan directory doesn't exist |

---

## Related

- `manage-solution-outline` — Source of deliverables that tasks reference
- `manage-status` — Plan lifecycle tracking; phase transitions gate task execution
- `manage-config` — Skill domain resolution for task profiles
- `manage-findings` — Q-Gate findings may trigger fix tasks during execution

