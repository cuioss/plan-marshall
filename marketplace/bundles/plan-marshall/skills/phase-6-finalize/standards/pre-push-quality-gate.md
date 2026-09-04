---
lane:
  class: core
  cost_size: S
name: default:pre-push-quality-gate
description: Run quality-gate per affected bundle then one whole-tree quality-gate, then whole-tree test-compile, then gate whole-tree module-tests on scoped-vs-whole-tree divergence risk, as the last gate before push
order: 5
mutates_source: false
head_dependent: true
reads:
  - worktree
default_on: true
presets:
  - full
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Pre-Push Quality Gate

Pure executor for the `pre-push-quality-gate` finalize step. Runs three guards once per plan, immediately before `default:push` (`order: 11`): (1) `quality-gate` (mypy + ruff over production sources) once per unique bundle derived from the plan's live footprint (the `compute-footprint` query against the worktree), **followed by one whole-tree `quality-gate`**, (2) a whole-tree **`test-compile`** (mypy over `test/`), and (3) a whole-tree **module-tests (pytest) gate** that escalates to a whole-tree run only when the footprint risks a scoped-green / whole-tree-red divergence. This is the deterministic last-line guard against type/lint AND cross-module test regressions reaching remote CI — converting soft "consider quality-gate" guidance into a hard precondition for push.

The three-guard order — quality-gate (per-bundle, then whole-tree) → test-compile → module-tests — is the order `build.py:cmd_verify` uses on the CI path. Matching it is the point: the gate is only a useful pre-push proxy for CI if it runs the same checks in the same sequence.

**Why guard 1 carries a whole-tree arm.** Some `quality-gate` dimensions exist ONLY at whole-tree scope, so a purely bundle-scoped sweep can never reach them and they surface first at remote CI. **The three enumerated below are this repository's** — they are what the plan-marshall marketplace repository's own `quality-gate` widens to at whole-tree scope, and the first of them exists nowhere else:

1. **The marketplace-wide plugin-doctor static-analysis pass** — it analyses the marketplace as a whole; no per-bundle invocation runs it. ⛔ **Marketplace repository only.** `plugin-doctor` is a marketplace-authoring tool that ships in this repository; it is not installed into a consumer project, and a consumer is not expected to carry an equivalent. In any other project this dimension does not exist, so it is neither gated nor un-gated there — it is simply not one of that project's dimensions, and the WARNING wording below must not assert it as a lost gate.
2. **The `.claude/` and `marketplace/targets` ruff coverage** — whole-tree scope widens the linted path set to include `.claude/` and `marketplace/targets` alongside `marketplace/bundles` and `test`; a bundle-scoped run never lints `.claude/` or `marketplace/targets`.
3. **The `marketplace/targets` SPDX-header coverage** — whole-tree scope widens the SPDX-enforced path set to include `marketplace/targets`; a bundle-scoped run never enforces headers there.

**The general rule, which is what a consumer applies.** A project's whole-tree-only dimensions are whatever its own `quality-gate` widens to beyond module scope. Derive that set from the project's build configuration; do not read the three above as a portable list, and do not conclude from their absence that a project has none. The per-bundle loop remains the precise, footprint-proportional pass that attributes a failure to its bundle; the whole-tree arm exists solely to make whichever such dimensions exist reachable.

**Recorded: the build.map-consult intent is already satisfied — and the premise that it is not is REFUTED.** A standing claim held that the per-bundle `quality-gate` arm "does not consult the footprint" and therefore "selects nothing", implying a build.map consult still had to be built. Both halves are false against the shipped document, and the evidence is in this file's own § Execution:

- The arm reads the **live footprint** (§ "Read the live footprint", `manage-references compute-footprint`), so it is footprint-driven by construction.
- It reads the **registered `build.map` globs** (§ "Read the build_map globs", `manage-config build-map read`).
- It intersects the two through the deterministic **`derive_gate_bundles`** seam (§ "Derive unique bundle set"), which returns the sorted, de-duplicated bundle set the loop then iterates.

So the derivation is exactly *live footprint ∩ registered build.map globs*, and it selects the bundles that intersection yields — not nothing. The "selects nothing" reading mistakes the seam's `unresolved` list (footprint paths that matched a glob but resolve to no real bundle, e.g. `test/marketplace/**`) for the whole result; that list is the diagnosable-WARNING branch, not the selection. No further build.map-consult work is owed here. This is recorded rather than acted on because the intent is already met, and re-implementing a satisfied intent is how a second, drifting derivation gets introduced.

### Documentation-only loop-back — the whole-tree arms still run

An open question sat behind the two unconditional whole-tree arms: after a loop-back whose diff is documentation-only, may they be skipped? Settled **per dimension**, with the evidence, rather than as one blanket answer:

**The whole-tree `quality-gate` arm MUST still run.** Its first whole-tree-only dimension — the marketplace-wide plugin-doctor static-analysis pass — **lints markdown skill bodies**, which is precisely what a documentation-only diff changes. Skipping the arm on a docs-only loop-back would therefore skip the one gate most likely to have something to say about that exact diff. The dimension that makes the arm expensive and the dimension that makes it necessary here are the same dimension, so there is no cost/benefit trade to make: a docs-only loop-back is arguably the strongest case for running it, not the weakest. (The `.claude/` ruff and `marketplace/targets` SPDX dimensions are the ones a docs-only diff may genuinely not exercise, but they ride the same single invocation — separating them would buy nothing and would split one guard into two admissible behaviours, which § "Whole-tree quality-gate arm" already forbids.)

**The whole-tree `test-compile` arm is likewise retained** — but for a different, weaker reason, stated honestly rather than borrowed from the arm above. It is a single mypy pass over the test tree, and scoping it to a docs-only diff would require a delta predicate that decides when a documentation change cannot affect test-tree typing. That predicate's safety depends on cross-module import coupling in the test tree, which this deliverable does not establish and does not attempt to. Retaining the arm is therefore the fail-closed choice under an unestablished premise, not a positive finding that the arm is load-bearing for docs-only diffs. Whoever later establishes that coupling may revisit it on evidence.

Both settlements are scoping decisions only. The existing **honest-degradation branch** (the whole-tree invocation cannot run at all in this project) and its mandatory **per-dimension WARNING** are unchanged by this section — they remain the only sanctioned path on which the whole-tree `quality-gate` arm does not run.

The module-tests gate consults the callable scope-resolution seam — the `resolve-test-scope` verb of whichever `build-{tool}` skill the project's `module-tests` canonical resolves to (in this repository `build-pyproject`, backed by the pure `_test_scope_divergence.resolve_test_scope`) — and runs a real whole-tree `module-tests` only when divergence is possible — mirroring the escalate-only-on-trigger discipline of the `finalize-step-plugin-doctor` reference behavior (PLAN-02), so whole-tree cost is paid only where a scoped run could miss a cross-module regression.

## Coverage parity with CI, freshness, and honest coverage

This gate is a proxy for whatever the project's CI runs as its full `verify`, and is only useful while
it stays a *truthful* proxy. In this repository that is `./pw verify` (`build.py:cmd_verify`, reading
the one shared `pyproject.toml` tool config), and the two properties below are enforced in `build.py`
and its pure `_gate_coverage` seam (`script-shared/scripts/build/_gate_coverage.py`). Another project's
`verify` is its own build tool's, enforced wherever that tool enforces it — the properties are the
requirement on the proxy; the pyprojectx implementation named here is how this repository meets it. The
arms below all obtain their invocation from `architecture resolve`, so they run the project's own tool
either way:

- **Freshness (cold, like CI).** Every mypy invocation runs with the incremental cache disabled
  (`--no-incremental`), so the verdict is computed against the current tree rather than a possibly-
  stale cache. A fresh CI clone runs cold; a developer machine keeps a `.mypy_cache` across runs, and
  a stale cache answering *"nothing I have cached changed"* is exactly how a clean local verdict once
  diverged from a red CI. A mypy that then reports success in a wall-time no real analysis of its file
  set could achieve is treated as **suspect, not reassurance** — `classify_check_duration` flags it
  and the gate fails closed rather than certifying the tree from a cache.
- **Honest coverage boundary.** A run that could not fully check a footprint is **distinguishable**
  from one that genuinely passed — and so is a run that established nothing at all. `verify` /
  `quality-gate` print one of **three** verdicts. COMPLETE requires an *affirmative* signal: at least
  one dimension checked over its full scope, and nothing degraded. PARTIAL names the un-certified
  dimension. UNKNOWN is the empty boundary, which certifies nothing — *"no dimension was degraded"* is
  vacuously true of a run that checked nothing, so an empty boundary must not render under the same
  word as a run that checked everything. The same discipline governs this step's own
  `--display-detail`: see the degraded detail variant under **Mark Step Complete** below, which never
  reports an un-run arm as green.

The local-gate-vs-CI parity population these properties defend is **recorded, not derived**
(`_gate_coverage.parity_population`): each cell's verdict and note was established by reading both
sides by hand at plan 160 and re-verified against `origin/main` at `61a43e5`, and nothing recomputes
them. A test asserts the population is non-empty — a parity table computed over an empty population is
indistinguishable from perfect parity, which is the confident-but-empty signal this gate exists to
prevent — but non-emptiness over a hand-written tuple is a weak guarantee: every cell can be stale and
still pass. One cell (`spdx-paths`) is therefore bound to the substrate it describes, so a note that
drifts from `build.py`'s actual SPDX scope fails the build. The rest stay recorded-only, and that
asymmetry is stated rather than implied away.

## A gate states what its green does not evaluate

The two properties above make this gate honest about **coverage** — whether it checked everything it
set out to. They say nothing about a third question, and it is the one a COMPLETE verdict most needs
answered: *what can these checks never see, however wide their scope?*

The distinction is load-bearing, and the two axes must not be collapsed:

| | Cured by | Reported as |
|---|---|---|
| **Coverage boundary** — a dimension the run could not fully check | re-running it at full scope | the PARTIAL verdict, naming the degraded dimension |
| **Structural scope limit** — a defect class the analysis cannot reach at all | nothing. Not a wider sweep, not another round, not a re-run | a per-analysis block on **both** the COMPLETE and PARTIAL verdicts |
| **Out-of-scope analysis** — one this gate performs, but not at the scope this invocation ran | re-running at a wider scope (whole-tree rather than module-scoped) | a `not performed at this scope: …` line |
| **Un-run analysis** — one no invocation of this gate performs, at any scope | running the gate that does perform it (`verify`, not `quality-gate`) | a `not performed by this gate at all: …` line |
| **Empty-scope analysis** — one the gate reached, whose scope held nothing to analyse | nothing — there is nothing to check, so nothing to cure | an `attempted, nothing in scope — …` line |

**The defect is not that a gate is narrow — it is that a narrow gate's green reads as whole-tree
assurance.** Each analysis this gate runs decides one specific question and is silent on the rest:
mypy decides type *consistency*, so a binary read of a three-valued observable type-checks exactly as
the correct three-way read does; ruff matches the rule families that are enabled, so a family absent
from the select list is an un-asked question rather than a clean answer; plugin-doctor lints document
*shape*, so it cannot check whether a documented remedy is reachable or whether a prose claim is true;
pytest executes the tests that exist, so it cannot tell "correct" from "never exercised". Those are
precisely the classes an external reviewer keeps finding on a diff whose every in-house gate is green.

The limits therefore ride the verdict itself rather than living in documentation a reader of the
output never sees. `_gate_coverage.structural_limits` derives them **from the dimensions the run
actually recorded**, so a gate that analysed less states fewer limits, and the registry is keyed by
analysis kind (`_gate_coverage.dimension_stem` strips the per-run scope suffix). A dimension with no
registered limit renders as an explicit **UNKNOWN** rather than being omitted: omitting it would make
the block read as exhaustive over a run that included an analysis nobody characterised, which is the
same absence-read-as-coverage defect in miniature.

**An analysis the gate never ran leaves no trace at all** — not checked, not degraded, simply absent
from every list — so a reader cannot tell *"this gate does not execute tests"* from *"tests were
fine"*. That is the same defect one level up, so the block closes with derived lines naming the
absence. Naming it with a *single* reason, however, is how the first form of this went wrong: it
subtracted the attempted dimensions from the registry and labelled the remainder *"not run in this
gate at all"*, which reads a per-**invocation** absence as a statement about the **command**. A
module-scoped `quality-gate` printed that the gate never performs `plugin-doctor` — false; it
performs it whole-tree — and, over a bundle whose mypy scope was empty, that it never performs
`mypy(production)` either.

`_gate_coverage.coverage_gaps` therefore splits the absence into the three rows tabulated above, and
the caller states the two facts the boundary cannot supply: which dimensions **this invocation** could
run at its scope, and which the **gate** performs at any scope. A caller that leaves EITHER of the two
undeclared gets an explicit `uncovered dimensions: UNKNOWN` line, with both derived sets empty — an
undeclared scope must not render as a confident empty list. Degraded dimensions are excluded from every clause: those were attempted, and PARTIAL
already reports them; listing them again would report one gap twice under two names and wrongly imply
the gate cannot perform that analysis.

This makes `_ANALYSIS_LIMITS` serve two purposes at once — the per-analysis limit registry, and the
catalogue of analyses that exist for the gap derivation to subtract from. That dual role is
deliberate and worth naming, because it bounds the guarantee: an analysis that is neither run nor
registered is invisible to both halves. Registering every analysis the build performs is therefore
the precondition for the gap lines meaning what they say.

This is the build-gate arm of a rule that binds every in-house gate. Its self-review counterpart is
[`../workflow/pre-submission-self-review.md`](../workflow/pre-submission-self-review.md) § "A clean
verdict carries the structural limit of the analysis"; the participation guard's counterpart is the
`proves: participation_only` field that
[`../../automatic-review/standards/bot-participation-contract.md`](../../automatic-review/standards/bot-participation-contract.md)
§ "Participation is not review quality" already requires. **A gate whose green is scope-limited says
so in its verdict** — read each gate's own limit there rather than from a copy here.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes non-`manage-*` scripts too, and a `manage-*`-scoped convention left exactly those calls uncovered — the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than looking for a fixed field list: beyond `status` and `error` the diagnostic fields vary by verb — `ci` verbs carry `operation`, `error_cause`, and `context`, the plan-resolution envelopes carry `message` and `plan_id` instead, and neither list is exhaustive. `error` is sometimes a hard-coded generic string whose real cause sits in one of the other fields, so dropping them can discard the cause entirely. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return — the envelope's diagnostic fields are not success payload, and dropping any of them leaves the step reporting a failure with no cause. A malformed or truncated stdout that carries **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause. There is no envelope to preserve on that sub-path — synthesize the error TOON instead, naming the call (notation, subcommand, and arguments) and carrying the raw stdout verbatim as the only account of the cause that exists. The build wrapper is the standing example: it exits 0 even on a failed gate, so the verdict is read from the result TOON's `status` / `errors[]`, never from the exit code — and `errors[]` is diagnostic, carried forward with the envelope rather than discarded as success payload.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the manifest composer in `manage-execution-manifest/scripts/manage-execution-manifest.py` via the `pre_push_quality_gate_inactive` pre-filter, which is a pure consumer of the command-free `build-decision` verdict — the sole build/no-build authority (see `manage-execution-manifest/standards/decision-rules.md` and ADR-004 § "Amendment: `build-decision` is the sole build/no-build authority").

**This gate is dropped on exactly ONE verdict.** The verdict vocabulary has three values, and only the positive answer removes the gate:

- `not_necessary` — nothing in this footprint needs building, so the gate is **dropped**.
- `unknown` — the footprint is unresolvable (the normal state at `phase-4-plan` compose, before `phase-5-execute` Step 2.5 materialises the worktree), so there is no evidence either way and the gate is **kept**, with a `[STATUS]` decision-log line naming the verdict's reason.
- `build` — the gate is **kept**.

Failing toward inclusion on `unknown` is required, not cautious: ADR-009 forbids reading an unsubstantiated verdict as a positive one, and ADR-004 forbids the pre-filter from re-deriving build necessity from any other signal to fill the gap. A consumer project without a ceremony `always` pin on this gate therefore keeps its pre-push build gate on every compose. When the dispatcher runs this step the executor always runs to completion: a clean run records `outcome=done`; a failed bundle invocation records `outcome=failed` and halts the phase. The `commit_and_push == false` case is also filtered at composition time (the `commit_push_disabled` pre-filter strips `push`, `pre-push-quality-gate`, AND `pre-submission-self-review`), so this step is never dispatched without a downstream push.

## Inputs

- `git working-tree state` — the live footprint, computed on demand from the worktree by the `manage-references compute-footprint` query (below): the union of the three-dot diff (`git diff --name-only {base_ref}...HEAD`) and the porcelain working-tree state (`git status --porcelain`). There is no persisted ledger; the footprint is always derived live from the worktree, which is the single source of truth.
- `build.map` globs — the fnmatch globs collected from every `{glob, role, build_class}` entry in `build.map`. The composer already gated activation on the `build-decision` verdict; the executor re-reads the globs to scope which live-and-intended entries should contribute to bundle derivation (defense-in-depth — only entries that match a registered build_map glob feed bundle derivation). This is a build_map READ for bundle scoping, NOT a re-derivation of build necessity.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). The `quality-gate` build invocation below identifies the worktree via `--plan-id {plan_id}` (which auto-resolves through `manage-status get-worktree-path`); the `--project-dir {worktree_path}` escape hatch remains available as the explicit override (the two flags are mutually exclusive — Bucket B two-state contract). The immediately-following `default:push` (`order: 11`) step runs the `pre-commit-verify-freshness` gate, which is tier-agnostic and build-tool-agnostic: it scans the unified change-ledger for a `kind=build` entry whose `worktree_sha` matches the current working-tree state, regardless of which execution-log tier the build's audit line landed in, and then cross-checks the `notation` of every matching row against the build notations this project's architecture resolves (any resolved tool corroborates, and one corroborated row is enough; only a set in which no row's notation is resolved by any module is refused). Routing via `--plan-id` or `--project-dir` therefore does not affect the freshness verdict — both feed the same ledger. See `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md` for the ledger and `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness" for the gate that consumes it.

## Execution

### Read the live footprint

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references \
  compute-footprint --plan-id {plan_id} --worktree-path {worktree_path}
```

Extract the `files` array from the TOON output. This is the live footprint derived from the worktree — the union of the three-dot `{base_ref}...HEAD` diff and the porcelain working-tree state — so it already reflects only what is actually modified now. A file that was touched then reverted does not appear, so it forces no redundant `quality-gate` run against a bundle with no actual changes.

### Read the build_map globs

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  build-map read --audit-plan-id {plan_id}
```

Extract `build_map` (the domain-keyed `{glob, role, build_class}` map) from the TOON output and collect the set of `glob` values across every domain entry. The composer's `build-decision` consult guarantees the footprint matches at least one of these globs when this step is dispatched, but the executor reads them again for defense-in-depth.

### Derive unique bundle set

The derivation rule lives in exactly one place — the deterministic `derive_gate_bundles` seam. Do NOT restate it here. Pass the live footprint `files`, the collected build_map `globs`, and the worktree root; the seam returns the sorted, de-duplicated `bundles` set plus an `unresolved` list of footprint paths that matched a build_map glob but resolved to no real bundle (e.g. a `test/marketplace/**` path, which is never a bundle and never a silent drop):

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:derive_gate_bundles \
  derive --files "{comma_separated_files}" --globs "{comma_separated_globs}" \
  --marketplace-root {worktree_path}
```

Parse `bundles` and `unresolved` from the TOON output. Let `N = len(bundles)`.

**Diagnosable-WARNING branch** — when `unresolved` is non-empty, emit exactly one `[WARNING]` naming the unresolved paths and continue. An unresolvable derivation is never a silent drop and never a hard fail; the gate hard-fails only on a real `quality-gate` red (ADR-009 fail-closed, unchanged):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[WARNING] (plan-marshall:pre-push-quality-gate) Footprint paths matched a build_map glob but resolved to no bundle: {unresolved} — proceeding; these are not gated as a bundle."
```

### Run quality-gate per bundle

For each `bundle` in `bundles` (in sorted order), resolve the canonical **module-scoped to that bundle** and invoke what the resolver returned. The resolver is the authority for which build tool runs and under what bound; this loop never names one:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command quality-gate --module {bundle} --audit-plan-id {plan_id}
```

Capture `executable`, `execution_tier` and `bash_timeout_seconds` from the returned TOON, then run the captured `executable` with the Bash timeout set to `bash_timeout_seconds * 1000` milliseconds. When `execution_tier` is `orchestrator` the invocation exceeds the Bash ceiling and MUST NOT be run here — hand it to the orchestrator's `await-long-running` seam and resume this loop on its result. A `status: error` from the resolve is handled exactly as the whole-tree arm's availability probe below prescribes: only the exact `error: architecture_error` + `message: Command not found` + `available[]`-omits-`quality-gate` shape proves the bundle exposes no `quality-gate` target (skip that bundle and record it in the same `[WARNING]` idiom § "Derive unique bundle set" uses); every other error shape did not answer, so STOP the step per § "Exit-code convention for every script call".

Inspect the invocation's TOON output. On `status: error`, halt: stop iterating, record the failing bundle, and proceed to **Mark Step Complete (Failure)** below. The build wrapper's TOON already carries `errors[N]{file,line,message,category}` — surface the offending file/line via the standard finalize TOON. Read the verdict from that `status` / `errors[]`, never from the exit code, which is `0` even on a red gate.

If every bundle succeeds (`status: success` for all `N` invocations), proceed to the **Whole-tree quality-gate arm** below.

### Whole-tree quality-gate arm

The per-bundle loop above cannot reach the whole-tree-only dimensions named in the opening section. Run one whole-tree `quality-gate` — no bundle argument, so the whole tree is the authority.

**Availability probe — runs BEFORE the invocation.** Resolve the canonical at default scope first, so the invocation below is only ever reached on a target that exists. Probing separates the two outcomes that would otherwise arrive in the same envelope, and keeps a build-wrapper `status: error` meaning exactly one thing — a real gate red:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command quality-gate --audit-plan-id {plan_id}
```

Branch on the **probe's** TOON, not on the build wrapper's — and on the probe's **exact shape**, not on a bare `status: error`. The resolver (`manage-architecture`'s `cmd_resolve`) returns `status: error` from four distinct paths, and only one of them says anything about whether the target exists: a missing project architecture (nothing was ever discovered), a module that does not exist, the command not being registered at the resolved module, and a catch-all for any other resolver failure. Only the third is proof of unavailability. Branching on the bare status would let an un-crawled project, a resolver IO error, or a malformed command entry downgrade a merge-gating check to a WARNING on evidence that proves nothing about availability — an unknown collapsing into a positive answer, which is the fail-open class ADR-009 forbids:

- **`status: success`** → the whole-tree target exists, and the return carries the invocation itself. Capture `executable`, `execution_tier` and `bash_timeout_seconds`, then run the captured `executable` and read its result as a gate verdict. The probe is not merely a yes/no oracle whose answer is then discarded for a pinned wrapper — the executable it returned IS the arm's invocation.
- **`status: error` carrying ALL THREE of `error: architecture_error`, `message: Command not found`, and an `available[]` list that omits `quality-gate`** → this exact shape, and only this shape, proves the whole-tree `quality-gate` cannot run at all in this project; `available[]` names the commands the `default` module *does* expose. Take the **honest-degradation branch** below and do NOT run the invocation. The third conjunct is **"`available[]` omits `quality-gate`"**, deliberately NOT "`available[]` is non-empty": the resolver's own inner fallback on this path yields an EMPTY list when the module's derived command set cannot be read, so an empty `available[]` is a legitimate instance of the shape rather than a reason to reject it.
- **`status: error` in ANY other shape** → the probe did not establish unavailability; it failed to answer. An unreadable probe is not evidence that the target is absent, so do NOT degrade — STOP the step: proceed to **Mark Step Complete (Failure)** below, preserving the probe's stdout error envelope verbatim, exactly as § "Exit-code convention for every script call" middle clause requires of any zero-exit non-`success` return. The honest-degradation branch is a narrow carve-out from that clause for the one shape that proves the target does not exist; every other probe error keeps the clause's default STOP disposition.

Run the captured `executable` verbatim, with the Bash timeout set to `bash_timeout_seconds * 1000` milliseconds. When `execution_tier` is `orchestrator` the invocation exceeds the Bash ceiling and MUST NOT be run here — hand it to the orchestrator's `await-long-running` seam and read the verdict from its result. Because the executable comes from the probe, this arm names no build tool and runs whatever the project resolves; a pyprojectx project gets its wrapper, a Maven or npm project gets its own.

Inspect the TOON output. On `status: error`, halt: record the failure and proceed to **Mark Step Complete (Failure)** below. The probe above already routed a non-resolving target away from this invocation, so a `status: error` here is a real gate red and nothing else — do not weaken the check or fall back to the per-bundle result to get past it; a finding that only whole-tree scope can see is exactly what this arm exists for. On `status: success`, proceed to the **Whole-tree test-compile gate** below.

**Honest-degradation branch — whole-tree `quality-gate` unavailable.** Reached ONLY from the availability probe's exact-unavailability arm above (`error: architecture_error` **and** `message: Command not found` **and** an `available[]` omitting `quality-gate`) — never from a probe error of any other shape, which STOPs the step instead, and never from the invocation's own result, which by then can only be a gate verdict. When the whole-tree invocation cannot run at all (the canonical does not resolve at default scope in this project, or the project exposes no whole-tree `quality-gate` target), do NOT silently skip it. Emit one loud WARNING naming **each** un-gated dimension explicitly — never a silent skip and never a singular "the whole-tree dimension" — then proceed to the **Whole-tree test-compile gate**. The dimensions to name are **the project's own**, derived as § "Why guard 1 carries a whole-tree arm" directs. The message below is this repository's instance, carrying its three; a project with a different set names that set, and a project that cannot enumerate its whole-tree-only dimensions says exactly that rather than naming none — an unenumerated set must not render as an empty one. Mirror the wording shape of the module-tests `whole_tree_available == false` branch below:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[WARNING] (plan-marshall:pre-push-quality-gate) Whole-tree quality-gate unavailable — three whole-tree-only dimensions are UN-GATED at finalize for this push: the marketplace-wide plugin-doctor static-analysis pass, the .claude/ ruff path coverage, and the marketplace/targets SPDX-header coverage. Proceeding on honest degradation."
```

The whole-tree arm is **unconditional**. The honest-degradation branch above — the invocation cannot run at all in this project, proven by the probe's exact unavailability shape — is the ONLY sanctioned path that proceeds past this arm without running it. A probe error of any other shape is not a second such path: it does not proceed at all, it halts the step. There is no trigger-gated variant of this arm, and a project MUST NOT gate it on a trigger to save cost: two admissible behaviours for the same guard make Branch A's "clean whole-tree `quality-gate`" precondition mean different things across runs, which is precisely the divergence this arm exists to prevent. (The escalate-only-on-trigger discipline the module-tests gate applies below governs a different gate with a different cost profile; it does not extend here.) The per-dimension WARNING is mandatory on the honest-degradation path — the degradation must be legible in the work-log, never inferred from its absence.

**Sibling branch, checked and left alone.** The module-tests `whole_tree_available == false` branch this one mirrors (§ "Whole-tree module-tests divergence gate", branch 3) carries no equivalent reachability defect: it is selected by a genuine boolean the `resolve-test-scope` seam returns in its own `status: success` payload, not inferred from a build wrapper's error. Its predicate can match the scenario it was written for, so it is unchanged. Only this arm needed the probe, because only this arm had to tell "the target does not exist" from "the gate went red" inside one `status: error`.

### Whole-tree test-compile gate

The per-bundle `quality-gate` loop above type-checks **production sources only** — it never runs mypy over `test/`. A type error confined to the test tree therefore slips this gate and surfaces first at remote CI, where `build.py:cmd_verify` does run `test-compile`. This section closes that gap.

Run it **whole-tree, not per-bundle**. The gap being closed is specifically a whole-tree one: the two errors that escaped to CI were an invalid dashed package name and a contract change left un-propagated to a test file *outside the plan's footprint*. A footprint-scoped `test-compile` would have missed the second, which is the whole reason this guard exists.

In **this** repository `test-compile` does not resolve at default (whole-tree) scope — see the recorded caveat below, and note that the caveat's evidence is this repository's, not every project's — so the arm obtains the invocation from a **module-scoped** resolve and widens it. Pick any module the derivation above yielded (`bundles[0]` in sorted order; when `bundles` is empty, any module the project exposes):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command test-compile --module {module} --audit-plan-id {plan_id}
```

Capture `executable`, `execution_tier` and `bash_timeout_seconds`. Take the captured `executable` and **remove its module argument** to obtain the whole-tree form. How the module is carried is the build tool's own convention — a trailing positional in the pyprojectx `run --command-args "test-compile {module}"` shape, `-pl {module}` under Maven, `--workspace {module}` under npm, a fused task path under Gradle — so remove whichever form the returned `executable` actually carries rather than assuming a trailing token. The notation and the verb still come from the resolver, so this arm names no build tool; only the module-argument removal is tool-shaped, and it is derived from the resolved string rather than pinned. Run that form with the Bash timeout set to `bash_timeout_seconds * 1000` milliseconds, handing an `orchestrator`-tier invocation to the `await-long-running` seam rather than running it here. When the module-scoped resolve returns the exact `error: architecture_error` + `message: Command not found` + `available[]`-omits-`test-compile` shape, the module this arm probed exposes no `test-compile` target. **That is not yet grounds to degrade** — it says nothing about the default scope, and asserting the default scope is empty because THIS repository's is would degrade a project (Maven, where `test-compile` IS a first-class default-scope target) that has a perfectly good whole-tree invocation available. Probe the default scope before concluding anything:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command test-compile --audit-plan-id {plan_id}
```

Branch on that probe with the same exact-shape discipline the whole-tree `quality-gate` availability probe uses:

- **`status: success`** → the project DOES expose a whole-tree `test-compile`. There is nothing to widen: run the returned `executable` directly (same timeout and `orchestrator`-tier hand-off rules) and read its result as this arm's verdict.
- **`status: error` carrying ALL THREE of `error: architecture_error`, `message: Command not found`, and an `available[]` that omits `test-compile`** → neither scope exposes the target, so this arm genuinely has no resolved invocation. Emit one `[WARNING]` naming the test-tree type-checking dimension as un-gated for this push and proceed to the **Whole-tree module-tests divergence gate**, exactly as the whole-tree `quality-gate` arm's honest-degradation branch does for its own dimension set.
- **`status: error` in ANY other shape** → the probe did not answer; STOP the step per § "Exit-code convention for every script call".

Any other error shape from the module-scoped resolve likewise did not answer — STOP the step.

On `status: error`, halt: record the failure and proceed to **Mark Step Complete (Failure)** below. Do not weaken or skip the check to get past a red — a genuine test-tree type error is exactly what this guard is for, so fix the underlying cause. On `status: success`, proceed to the **Whole-tree module-tests divergence gate** below.

**Recorded caveat — `test-compile` does not resolve at default scope.** The procedure above resolves `test-compile` **module-scoped** and widens the returned executable, rather than resolving it at default scope, because the default-scope call fails:

```text
status: error
error: architecture_error
message: Command not found
available[6]: clean, compile, quality-gate, verify, module-tests, coverage
```

Only the module-scoped form resolves. The observation was recorded against this repository, whose build tool is pyprojectx: `architecture resolve --command test-compile --module plan-marshall` returned `pyproject_build run --command-args "test-compile plan-marshall"`. That literal is the evidence for the caveat, not the arm's invocation — the arm runs whatever the resolve returns for *this* project. **The omission is scope-shaped, not global**, and this caveat claims only what the two observations support. The `default` (whole-tree) scope's command set is exactly the six listed above: `_pyproject_cmd_discover._build_commands` builds its `cmd_map` from `clean`, `compile`, `quality-gate` and `verify`, adding `module-tests` and `coverage` when the module has tests, and contributes no `test-compile` entry at any scope. A per-module scope nonetheless exposes one — `architecture commands --module plan-marshall` returns seven commands with `test-compile` among them, which is why the module-scoped resolve above succeeds — so `test-compile` reaches a module scope from a discoverer other than pyprojectx module discovery. The claim here is therefore the narrow one the evidence carries: no `test-compile` at default scope, and no inference from that about the per-module scopes.

The whole-tree invocation is therefore obtained by taking the architecture-resolved module-scoped `executable` and dropping its module argument — the executable, the notation, and the `run --command-args` shape all still come from the resolver, so this is **not** a hard-coded build command. This is a deliberate, recorded bypass of the default-scope resolve, not an oversight. The unblocking condition is registering `test-compile` in `_build_commands` plus an `architecture discover` refresh so the persisted inventory picks it up; that registration is deliberately NOT done here, being a production change to build-system discovery and outside a gate-document change.

**Adjacent item deliberately not covered.** `build.py` registers the `verify` subparser with `help='Full verification (quality-gate + module-tests)'`, while `cmd_verify` chains quality-gate → **test-compile** → module-tests. The help text denies exactly the behaviour this gate now achieves parity with. It is not fixed here purely as a scope boundary — correcting a build-system help string is a production change to `build.py`, not a gate-document change. The former blocker no longer applies: `build.py` now matches a `_CLASSIFY_PATTERNS` entry in `build-pyproject`'s `classify_paths()`, so a deliverable declaring it resolves to `production` rather than the `unknown` file-type bucket.

### Whole-tree module-tests divergence gate

The guards above run mypy + ruff over production sources and mypy over `test/` — neither runs **any pytest**. A scoped-green / whole-tree-red regression (the PLAN-08 class: a change that passes a scoped run but fails when the whole tree is tested) therefore slips them and surfaces first at remote CI. This section closes that gap by running a real `module-tests` (pytest) gate, escalating to a whole-tree run only when the footprint provably risks divergence.

0. **Resolve the canonical once, and derive both the seam notation and the invocations from it.** Every invocation in this arm comes from one resolve rather than from a pinned wrapper:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
     resolve --command module-tests --audit-plan-id {plan_id}
   ```

   Capture `executable`, `execution_tier` and `bash_timeout_seconds`. The captured `executable` IS branch 4's whole-tree invocation; appending the module argument to it gives branch 6's scoped invocation; and its **build-skill notation** (the `{bundle}:{skill}:{script}` prefix of the executable) is the notation branch 1 calls `resolve-test-scope` on. A project whose build skill exposes no `resolve-test-scope` verb cannot answer the divergence question at all — treat that as `whole_tree_available: false` and take branch 3's honest-degradation path. Branch on the resolve's error shapes exactly as the whole-tree `quality-gate` probe prescribes: only the `Command not found` + `available[]`-omits-`module-tests` shape proves absence (branch 3); any other error shape did not answer, so STOP the step.

1. **Resolve the scope** — call the callable seam on the notation captured above and parse its resolution:

   ```bash
   python3 .plan/execute-script.py {resolved_build_notation} \
     resolve-test-scope --plan-id {plan_id}
   ```

   Parse `scoped_modules`, `divergence_possible`, `recommended_target`, `unresolved_paths`, and `whole_tree_available` from the TOON output. For this repository the notation resolves to `plan-marshall:build-pyproject:pyproject_build`; see [`build-pyproject/SKILL.md`](../../build-pyproject/SKILL.md) § "Canonical invocations" → `resolve-test-scope` for that seam's argument surface and output contract, and the corresponding section of whichever `build-{tool}` skill a different project resolves to.

2. **Diagnosable-WARNING branch — `unresolved_paths` non-empty** → emit exactly one `[WARNING]` naming the paths and continue to the routing branches below. These are footprint entries the seam could not map to a registered module, so the coverage it can claim for them is *none*; the seam already reports them as `divergence_possible: true`, which routes the run through the whole-tree arm, but the suppression itself must reach a human rather than dying in the TOON (ADR-014). This is the same "an unresolvable derivation is never a silent drop and never a hard fail" contract the `derive_gate_bundles` `unresolved` branch establishes in § "Derive unique bundle set" above — same idiom, different derivation:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level WARNING \
     --message "[WARNING] (plan-marshall:pre-push-quality-gate) Footprint paths resolved to no registered module: {unresolved_paths} — proceeding whole-tree; scoped coverage for these paths is not determinable."
   ```

3. **`whole_tree_available == false`** (no discoverable pytest module set — e.g. a non-Python project) → do NOT run pytest. Emit a loud, footprint-specific WARNING naming the un-gated modules and the PLAN-08 divergence class, then proceed to **Mark Step Complete (Success)** (honest degradation, never a silent skip). Mirror the wording shape of the `finalize-step-plugin-doctor` cross-skill divergence WARNING:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level WARNING \
     --message "[WARNING] (plan-marshall:pre-push-quality-gate) Whole-tree module-tests unavailable for footprint modules {scoped_modules} — the scoped-green / whole-tree-red divergence class (PLAN-08) is UN-GATED at finalize for this push. Proceeding on honest degradation."
   ```

   On reaching Mark Step Complete (Success) from here, use the **module-tests un-gated** detail variant
   below rather than Branch A's default string — the default ends `module-tests green`, which this path
   did not earn.

4. **`divergence_possible == true` and `whole_tree_available == true`** → run whole-tree `module-tests`. The invocation is the `executable` captured at branch 0, used verbatim: it carries no module argument, so the whole tree is the authority. Run it with the Bash timeout set to `bash_timeout_seconds * 1000` milliseconds, and hand an `orchestrator`-tier invocation to the `await-long-running` seam rather than running it here — a whole-tree pytest run is the invocation most likely to exceed the Bash ceiling.

   On `status: error` (whole-tree red), the scoped-green / whole-tree-red regression is **caught here instead of at CI**: record the failing tests and proceed to **Mark Step Complete (Failure)**, which halts the phase before push. On `status: success`, proceed to **Mark Step Complete (Success)**.

5. **`scoped_modules` is empty** → run **no pytest at all**. This branch MUST be evaluated BEFORE branch 6: `divergence_possible == false` holds for *zero* scoped modules as well as for exactly one, and `recommended_target` is populated only in the one-module case — so collapsing the two lets branch 6 interpolate a null target and invoke `module-tests None`, which the build wrapper exits `0` on and the gate then reads as a pass. Reaching this branch means the seam returned the one legitimate benign verdict: an empty footprint, which genuinely has nothing to test (a non-empty footprint that resolves to no module arrives at branch 4 with `divergence_possible: true`). Record the skip attributably, then proceed to **Mark Step Complete (Success)**:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[STATUS] (plan-marshall:pre-push-quality-gate) module-tests skipped — the live footprint ({files}) resolves to zero scoped modules, so there is no pytest target to run and no whole-tree escalation is warranted."
   ```

   `{files}` is the live footprint read in § "Read the live footprint" above, so the skip names the evidence it rests on rather than being an unattributable silence.

6. **`divergence_possible == false` and exactly one scoped module** → that single isolated module cannot diverge from the whole tree (match by equivalence), and `recommended_target` is non-null precisely in this case. The `exactly one` precondition is load-bearing, not decorative: it is what branch 5 above peels off first. Run the scoped form — do NOT pay the whole-tree cost. The invocation is the branch-0 `executable` with `{recommended_target}` appended as its module argument; equivalently, re-resolve module-scoped (`architecture resolve --command module-tests --module {recommended_target} --audit-plan-id {plan_id}`) and run what that returns, which additionally gives the module's own `bash_timeout_seconds` rather than the whole-tree bound. Either way the invocation comes from the resolver, and the same `orchestrator`-tier hand-off applies.

   Gate on its result the same way: `status: error` → **Mark Step Complete (Failure)** (halt before push); `status: success` → **Mark Step Complete (Success)**.

The module-tests outcome folds into the Mark Step Complete branches below: Branch A (green) requires a clean per-bundle `quality-gate` sweep AND a clean whole-tree `quality-gate` AND a clean whole-tree `test-compile` AND a clean module-tests gate; Branch B (failure) covers a red per-bundle `quality-gate` OR a red whole-tree `quality-gate` OR a red `test-compile` OR a red module-tests run.

## Verdict-input surface — deliberately undeclared

This gate declares **no** `verdict_inputs` (see [`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"), so the dispatcher's verdict-currency classifier never narrows its re-fire: every HEAD advance re-runs it, exactly as before that mechanism existed. The absence is a **recorded refusal on evidence**, not an obligation left unwritten — and it is recorded here because the refusal is easy to mistake for an oversight and easy to "fix" wrongly.

The admissibility bar for a declaration is that the globs be a **superset** of what the gate's verdict reads. Three of this gate's arms make that unachievable as a proper subset of the tree:

- **The module-tests arm executes this repository's own pytest suite**, and that suite asserts over the *real repository tree*. Test modules read `doc/` (retired-token sweeps over `doc/**/*.md` / `*.adoc` / `*.svg`, and an `.adoc` governed-population contract that also reads root `CLAUDE.md`) and `.github/workflows/*.yml` (branch-prefix and merge-trigger contracts asserted against the live workflow). A commit confined to any of those turns this gate red, so none of them can be excluded.
- **The whole-tree `quality-gate` arm runs the marketplace-wide plugin-doctor pass**, which brings in two further disqualifiers of its own. Its build-failing agentfile analyzers walk the **repository root** and lint every `CLAUDE.md` / `AGENTS.md` at any depth. And its `broken-relative-link` rule resolves each relative link target against the linking file's own directory and stats it whenever the result falls inside the repository-root containment boundary — so renaming or deleting *any* file that a marketplace doc links to turns this arm red, and that target set is discovered at run time rather than expressible as a glob written ahead of time. Both are the same disqualifiers `project:finalize-step-plugin-doctor` records in its own refusal, inherited here because this arm invokes that pass.
- **Every arm resolves its tool versions through the lockfile**, so `uv.lock` is an input to all of them.

Taken together the honest surface is "the tracked tree", and a declaration naming it would be an inert lever wearing the shape of a real one — the confident-but-untrue signal this document already refuses on the coverage-verdict and `display_detail` paths. Declaring nothing keeps the fail-closed default and says so.

**The unblocking condition, for whoever revisits this.** A sound declaration becomes possible only if the gate's arms are separated so each carries its own surface — the module-tests arm's surface is unbounded, but the per-bundle `quality-gate` sweep's is not. That is a decomposition of this step, not a declaration on it, and it is deliberately out of scope here.

## Mark Step Complete

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. Branch A requires ALL FOUR of the per-bundle `quality-gate` sweep, the whole-tree `quality-gate` arm, the whole-tree `test-compile`, and the module-tests divergence gate to be green; Branch B fires when ANY of the four failed.

**Branch A — all bundles green AND whole-tree quality-gate green AND test-compile green AND module-tests gate green**:

Immediately before invoking `mark-step-done`, resolve the worktree HEAD SHA so the dispatcher can detect a stale completion record after a downstream loop-back commit advances HEAD:

```bash
git -C {worktree_path} rev-parse HEAD
```

The `{worktree_path}` value is the path resolved by `phase-6-finalize` Step 0 (Resolve Worktree and Main Checkout Paths). Do NOT re-resolve it from any other cwd or shell context — the canonical resolution lives in Step 0 and propagates into every standards document loaded by the finalize pipeline. Capture the stdout as `{sha}` (a 40-character hex SHA) and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-push-quality-gate --outcome done \
  --display-detail "{N} bundles + whole-tree quality-gate green, test-compile + module-tests green" \
  --head-at-completion {sha}
```

**Detail variant — module-tests skipped (zero scoped modules).** When the module-tests gate concluded via branch 5 (no pytest ran because the footprint resolves to zero scoped modules), use the shorter variant below instead, so the skip is legible in the step record rather than indistinguishable from a green pytest run:

```text
--display-detail "{N} bundles + whole-tree gates green, module-tests skipped (no module)"
```

The variant is deliberately shorter than the default one. Against the `display_detail` length ceiling owned by [`external-step-contract.md`](external-step-contract.md) § "Required termination" (do not restate the number here — read it there), the default string already reaches 75 characters before `{N}` expands, leaving room for only a small bundle count; the skip variant reaches 67 before expansion and therefore stays inside the ceiling for any count this gate can produce. Size any further variant the same way — against its **worst-case placeholder expansion**, never against its literal form. A placeholder-bearing string that fits as written is not evidence that it fits once the placeholder expands.

**Detail variant — whole-tree quality-gate degraded (honest degradation).** When Branch A is reached
via the whole-tree `quality-gate` **honest-degradation path** (the whole-tree invocation could not run,
so the three whole-tree-only dimensions were UN-GATED and only a `[WARNING]` was emitted), the default
detail's "whole-tree quality-gate green" clause would **affirmatively misreport an un-run arm as
green** — the exact confident-but-untrue signal this gate exists to prevent. Use the degraded variant
below instead, so the step record names its coverage boundary rather than claiming a pass it did not
earn (`test-compile` and `module-tests` still ran on this path, so "tests green" is accurate):

```text
--display-detail "{N} bundles green, whole-tree quality-gate DEGRADED, tests green"
```

Size it the same way as the module-tests variant — against its worst-case placeholder expansion, not
its literal form — and it stays inside the same `display_detail` ceiling.

**Detail variant — module-tests un-gated (`whole_tree_available == false`).** The module-tests gate's
branch 3 routes to **Mark Step Complete (Success)** without running pytest at all, having emitted the
PLAN-08 un-gated WARNING. Branch A's default detail ends `test-compile + module-tests green`, which on
that path asserts a dimension that never ran — the same misreport the degraded variant above exists to
prevent, on the other arm. **Branch A's default string is inapplicable on this path**; use the variant
below, which contains the word "green" for no dimension it did not gate:

```text
--display-detail "{N} bundles + whole-tree gates green, module-tests UN-GATED (PLAN-08)"
```

Its worst-case expansion is 67 characters at `{N}` = one digit and 68 at two — measured from the
expanded string, not from the literal — so it stays inside the ceiling for any bundle count this gate
can produce, exactly as the two variants above do.

The two degradations are independent: a run can reach Branch A with the whole-tree `quality-gate`
degraded, with module-tests un-gated, or with both. When both fire, neither single-arm variant is
honest — compose one naming both un-gated arms, and size it the same way.

The persisted `head_at_completion` field is consumed by phase-6-finalize Step 3's resumable re-entry check: when the worktree HEAD has advanced past `{sha}` (typically because `automated-review` or `sonar-roundtrip` opened a loop-back fix-task that produced a new commit), the dispatcher re-fires this gate against the newer HEAD. See § "Verdict-input surface — deliberately undeclared" above for why the verdict-currency classifier never narrows that re-fire for THIS gate.

**Branch B — at least one bundle's quality-gate failed OR the whole-tree quality-gate failed OR test-compile failed OR the module-tests gate failed**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-push-quality-gate --outcome failed \
  --display-detail "{quality-gate failed for {bundle} | whole-tree quality-gate red | test-compile red | whole-tree module-tests red | scoped module-tests red for {recommended_target}}"
```

Use `quality-gate failed for {bundle}` when a bundle's `quality-gate` failed, `whole-tree quality-gate red` when the whole-tree `quality-gate` arm caught a finding only whole-tree scope can see (the plugin-doctor pass, the `.claude/` ruff coverage, or the `marketplace/targets` SPDX coverage), `test-compile red` when the whole-tree `test-compile` gate caught a test-tree type error, `whole-tree module-tests red` when the whole-tree module-tests divergence gate caught a scoped-green / whole-tree-red regression, or `scoped module-tests red for {recommended_target}` when the branch-6 scoped `module-tests {recommended_target}` run failed on a non-divergent single-module footprint. The failure branch does not need `--head-at-completion`: the dispatcher unconditionally retries `failed` records on re-entry regardless of HEAD, so the SHA carries no decision value here. The dispatcher's existing failure handling halts the phase on `outcome=failed` and surfaces the offending file/line (or failing test) through the finalize TOON, matching the contract used by the other gating steps.
