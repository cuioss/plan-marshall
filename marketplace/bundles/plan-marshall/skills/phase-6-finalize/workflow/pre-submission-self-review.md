---
lane:
  class: adversarial
  cost_size: L
name: default:pre-submission-self-review
description: Pre-submission structural self-review (symmetric pairs, regex over-fit, wording, duplication, contract drift, producer-without-consumer, source-of-truth drift, same-document contradiction, description-vs-body drift, unguarded boundary, stale count-prose, touched-claim re-check, ordinal-reference re-check, unreachable guard behind a scan-derived key, worked-example clause mismatch) before push
order: 7
mutates_source: false
head_dependent: true
default_on: true
presets: []
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Pre-Submission Self-Review

Pure executor for the `pre-submission-self-review` finalize step. Catches the class of structural defects that PR-review bots reliably surface but local quality gates systematically miss: missing initialization in symmetric save/restore pairs, regex/glob over-fit, ambiguous user-facing wording, duplicate prose sections covering the same contract, and schema/contract drift.

Outcome bookkeeping (Step 4) now includes finding persistence: every returned finding is written to the plan's `qgate-6-finalize.jsonl` finding store before the step's `--outcome failed` is recorded.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The step combines a deterministic helper that surfaces concrete candidates from the staged diff (Step 1 below) with an LLM cognitive review applied only to those candidates (Steps 2–3 below). Step 1 (deterministic surface) and Step 4 (outcome bookkeeping) run inline in the manifest dispatcher's context; Steps 2–3 (contract cross-reference setup + the fifteen LLM cognitive checks) run in the dispatched envelope under `--phase phase-6-finalize` (no `--role` — pre-submission-self-review tracks `phase-6-finalize.default`). On any finding the LLM returns, the step hard-fails and halts the phase, mirroring the gating-step convention established by `pre-push-quality-gate`.

This document carries NO step-activation logic. Activation is controlled by the manifest composer in `manage-execution-manifest/scripts/manage-execution-manifest.py` (see `manage-execution-manifest/standards/decision-rules.md`). No footprint-gated pre-filter drops this step: the fifteen cognitive checks it targets apply to any code or doc change, so there is no glob gate to fail. More than one compose-time subtraction can drop it. The `commit_push_disabled` pre-filter drops it transitively when `commit_and_push == false`, because both push-only gates are meaningless with no downstream push. The `scope_gated_finalize` pre-filter also drops it when `scope_estimate == 'surgical'` — independently of `commit_and_push` — unless the step carries a declared lane override, which grants it immunity from that gate. For the authoritative set of compose-time subtractions and what each one reads, see [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md); do not treat the two named here as exhaustive. When the dispatcher runs this step the executor always runs to completion: a clean run records `outcome=done`; a non-empty findings list records `outcome=failed` and halts the phase.

## Domain-Aware Candidate Surfacing

The deterministic surfacer is pluggable via the `plan-marshall:extension-api/standards/ext-point-self-review-surfacing` extension point — see [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) for the contract; `ext-self-review-{domain}` is the implementor skill naming pattern, not the extension point itself. Each implementor exposes a `surface --plan-id {plan_id}` script that emits the candidate sub-lists as TOON. Some are line-level heuristic lists summed into the `counts.total` gate contract Step 1b consumes; the rest are review-anchor/index lists excluded from that count. Which is which is declared by the ext-point's Output Schema and derived from the implementor's registry — this document reads the emitted `counts` block rather than carrying its own copy of the membership. The plan-marshall-domain implementor is the `ext-self-review-plan-marshall` skill, homed in the `pm-plugin-development` bundle; its script notation is `pm-plugin-development:ext-self-review-plan-marshall:self_review`. Because this step now ships `default_on: true` to consumer projects that may not carry a domain surfacer, Step 1 discovers the surfacing implementors via `find_implementors(ext-point-self-review-surfacing)` and invokes the resolvable domain implementor (in the meta-project, `pm-plugin-development:ext-self-review-plan-marshall:self_review`, preserving current behavior bit-for-bit). When NO implementor resolves in the current executor, Step 1 takes the **zero-generator fallback** — an empty candidate set, no LLM dispatch, and a clean `done` outcome.

## Inputs (inline step — Step 1)

- The change footprint — the deterministic helper derives it live from the worktree (the union of the `{base}...HEAD` diff and the porcelain working-tree state), not from any persisted ledger.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). The deterministic helper invocation MUST identify the worktree via `--plan-id {plan_id}` alone (preferred — the implementor auto-resolves the worktree path through `manage-status get-worktree-path`) or by additionally supplying `--project-dir {worktree_path}` as an explicit override. The footprint and diff are computed against the worktree's base branch.

## Inputs (dispatched envelope — Steps 2–3)

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier. |
| `WORKTREE` | Yes | Repo-relative working-directory path. |
| `candidates` | Yes | TOON envelope from the resolved `ext-self-review-{domain}` surface helper — carries the candidate sub-lists and the emitted `counts` block. The orchestrator runs the surface helper in Step 1 and forwards its output verbatim; the workflow body does NOT re-invoke the surface helper. |

**The candidate sub-list vocabulary is NOT restated here.** Each sub-list's key, entry schema, and the check that consumes it are declared once, authoritatively, in [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) § Output Schema and § Required Candidate Sub-Lists — derived in turn from the implementor's `CANDIDATE_LISTS` registry, which is the single code-side source of the emitted key set. Read the emitted `counts` block for what this round actually surfaced, and that document for what each key means.

A hand-maintained copy of the row set used to live here. It is removed rather than corrected: a second enumeration of a registry-derived vocabulary has to be re-edited on every registry change, states a cardinality that goes stale the moment one is added, and gives a reader two lists to reconcile with no way to tell which is authoritative. Removing it deletes that drift class instead of re-fixing one instance of it.

Skills the caller MUST forward in `skills[]`: none (the workflow reads files with the `Read` tool and emits no script calls).

## HEAD-dependency

`pre-submission-self-review` declares `head_dependent: true` in its frontmatter — that fact IS the membership declaration the dispatcher's re-entry check reads (see [`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"). Its verdict is a **structural review of the plan's diff**, so the verdict is a function of that diff: a loop-back fix task that advances HEAD past the recorded `head_at_completion` produces a diff this step never examined, and a `done` record carried across that advance would stand as green for a diff no check ever ran against. The dispatcher MUST therefore re-fire this step against the newer HEAD. Capture `git rev-parse HEAD` immediately before EVERY terminal `mark-step-done` call — Branch A and Branch B alike — and forward it via `--head-at-completion {sha}`.

The recorded SHA carries a **second, independent** load: it is the **delta anchor** the next round scopes itself against (Step 1 reads it back and passes it as `--since-ref`). That is why it is written on the `failed` branch too, where the dispatcher's retry decision does not need it, and why its absence on a `done` record is now REFUSED rather than tolerated — `manage-status mark-step-done` returns `error: missing_head_at_completion` and writes nothing when a `head_dependent: true` step records `done` without it. An unanchored record would leave the following round unable to define its delta, silently degrading it to a full re-sweep.

## Execution

This step implements the [coverage-gathering contract](../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md) as a runtime CONSUMER (not a gatherer — the cell is gathered upstream by the recipe / plan that produced the plan, or defaults to `inherit/inherit`). The expanded instruction governs the surfacer `--contract-radius`, the candidate-count gate threshold, and the per-candidate lens depth. `inherit/inherit` reproduces today's behavior bit-for-bit.

### Step 0: Resolve the coverage instruction (inline)

Read the per-invocation coverage cell from status metadata, falling back through the contract's runtime path: `coverage_instruction` (the expanded block) → re-expand the identifier via `coverage expand` → `coverage resolve --phase phase-6-finalize` (project default) → `inherit/inherit` (behavior-preserving).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field coverage_scope

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field coverage_instruction
```

Capture `{cov_scope}` and `{cov_instruction}` (when absent, treat as `inherit`). When `coverage_instruction` is absent but `coverage_scope`/`coverage_thoroughness` are present, re-expand via `coverage expand --thoroughness {cov_thoroughness} --scope {cov_scope}`; when neither is present, resolve the project default via `coverage resolve --phase phase-6-finalize`. The resolved `{cov_scope}` drives the radius/gate dials below; `inherit` keeps today's hardcoded values.

### Step 1: Deterministic surface (inline)

Because this step ships `default_on: true` to consumer projects that may carry no domain self-review surfacer, Step 1 discovers the surfacing implementors rather than calling a fixed notation. Discover them via the `ext-point-self-review-surfacing` extension point:

```bash
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery implementors \
  --ext-point plan-marshall:extension-api/standards/ext-point-self-review-surfacing
```

Parse the discovered implementors' `self_review` script notations from the returned TOON. Select the first implementor whose notation **resolves in the current executor** (in the meta-project this is `pm-plugin-development:ext-self-review-plan-marshall:self_review`, preserving current behavior bit-for-bit).

**Resolve the delta anchor first.** This step re-fires on every loop-back, and without an anchor each round re-surfaces the entire plan diff — including every file the preceding round already examined and no fix has touched since. Read this step's OWN prior record and take its `head_at_completion` as the anchor:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

Locate `metadata.phase_steps.6-finalize.pre-submission-self-review.head_at_completion` and capture it as `{since_ref}`. Exactly one of two cases holds:

- **A prior record carries a non-empty SHA** → this is a **delta round**. Pass `--since-ref {since_ref}` on the surface call below. The surfacer narrows the file set to the footprint intersected with the paths changed since that SHA.
- **No prior record, or its `head_at_completion` is absent/empty** → this is a **full round** (round 1, or a first run after a record that carried no anchor). Do NOT pass `--since-ref` at all. Never substitute the base branch, `HEAD`, or any other ref for a missing anchor — a fabricated anchor would silently scope the round against a boundary no round ever completed at.

Passing `--since-ref` narrows WHICH FILES are surfaced, never how deeply a surfaced file is reviewed: hunks are still computed against the base branch, so every surviving file is still reviewed against its full plan diff.

**Resolvable implementor path**: invoke the resolved implementor's `surface` subcommand. The implementor derives the plan footprint live from the worktree (`{base}...HEAD` ∪ porcelain), computes the staged diff against the worktree's base branch, and emits the candidate sub-lists in a single TOON document on stdout. Forward `--contract-radius {N}` derived from `{cov_scope}` (`change-set` → `1`; `artifact`/`inherit` → `3`; `component`/`module`/`overall` → `5`):

```bash
python3 .plan/execute-script.py {resolved_implementor_notation} \
  surface --plan-id {plan_id} --contract-radius {N}
```

On a delta round, append `--since-ref {since_ref}`:

```bash
python3 .plan/execute-script.py {resolved_implementor_notation} \
  surface --plan-id {plan_id} --contract-radius {N} --since-ref {since_ref}
```

`{resolved_implementor_notation}` is the notation selected above — in the meta-project this resolves to `pm-plugin-development:ext-self-review-plan-marshall:self_review`, preserving current behavior bit-for-bit; a consumer project resolving a different domain implementor invokes that implementor's notation instead. Auto-resolves the worktree from `--plan-id`. Add `--project-dir {worktree_path}` only when the explicit override is required. The `inherit`/default radius of `3` reproduces today's surfacer breadth.

The surfacer echoes `surface_scope` (`delta` or `full`), `since_ref`, and `files_in_scope`, so the round variant that produced a verdict is legible from the returned TOON without reconstructing it. A `--since-ref` that does not resolve is refused by the surfacer with `since_ref_unresolvable` — that is a helper non-zero exit and takes the halt path below; it is never silently widened into a full sweep.

**A delta round cannot close the step on its own evidence.** A delta-scoped round examined only the files that changed since the previous round, so a clean result from it is a *filter* result, not a closing verdict: it says nothing about the files it did not look at. When a delta round returns zero findings, re-run this step ONCE at full scope — repeat the surface call WITHOUT `--since-ref` and carry that full candidate set through Steps 1b–3 — and record the outcome from that full-surface pass. Only a full-surface clean pass may record `done` (see Step 4 Branch A). A delta round that DOES return findings needs no confirmation sweep: it has already found the work that sends the step round the loop again.

If the resolved implementor exits non-zero, halt and proceed to **Step 4 — Mark Step Complete (Failure)**, surfacing the helper error in the `display_detail` payload. Do NOT dispatch the LLM cognitive phase below.

Capture the helper's TOON output as `{candidates_toon}` for forwarding to the cognitive-phase dispatch.

**Zero-generator fallback path**: when NO discovered implementor resolves in the current executor (a consumer project shipping no domain self-review surfacer), treat the candidate set as empty — skip the LLM cognitive dispatch (Steps 1b–3) entirely and proceed directly to **Step 4 — Mark Step Complete**, recording `--outcome done` with the **nothing-to-check** verdict `"self-review: nothing to check - no candidates surfaced"` (see § Dispatched-envelope output for the two disjoint clean verdicts). This path surfaced no candidates at all, so it takes the nothing-to-check verdict and never the no-check-matched one. This zero-candidate clean run lets the promoted default step ship safely to consumers without a domain surfacer.

### Step 1b: Candidate-count gate (inline vs dispatch) — B5

Parse the candidate sub-lists from `{candidates_toon}` and read `total_candidates` from the surfacer's emitted `counts.total` field. Which lists feed that sum is the surfacer's contract, not this document's: read the emitted `counts` block and take `total` from it. The authoritative membership — which lists are summed, which are review-anchor categories excluded from the sum, and why — lives in [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) § Output Schema.

This document deliberately does NOT restate that enumeration. A hand-maintained copy of the summed-list names here would have to be re-edited every time the registry gained or lost a list, and a copy that fell behind would state a `total` formula the surfacer does not compute — the drift class this replacement removes rather than re-fixes.

**Read the per-round detector mix too.** The surfacer emits `counts.by_family` alongside `counts.total`: `structural` (detectors reading code shape) and `prose_contract` (detectors reading prose or contract consistency), summing exactly to `total` over the same population. Report both figures with the candidate count, including a zero — a round whose candidates are entirely `prose_contract` says something specific about the change under review, and reading its total alone would present a lopsided round as ordinary thoroughness.

Evaluate the gate, with the threshold `{gate}` indexed by `{cov_scope}` (`inherit`/`change-set` → `5`; `artifact` → `8`; `component`/`module`/`overall` → `12`). The `inherit` path preserves the `<= 5` threshold verbatim:

> `total_candidates <= {gate}`

When the gate holds (the typical small-diff case): execute the LLM cognitive checks (Step 2a + Step 3) INLINE in the dispatcher context. Do NOT compute the variant target, do NOT emit a `[DISPATCH]` log line, do NOT issue the `Task: plan-marshall:{target}` invocation in Step 2. Skip directly to Step 2a (cross-reference setup) and continue through Step 3 in the dispatcher's own context. The boundary is INCLUSIVE: `total_candidates == {gate}` is inline; `total_candidates == {gate} + 1` falls through to dispatch.

Log the gate decision once:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:pre-submission-self-review) Candidate-count gate INLINE — total_candidates={N} (<={gate} threshold, cov_scope={cov_scope})"
```

When `total_candidates > {gate}`: fall through to Step 2 (dispatch) as documented. Log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:pre-submission-self-review) Candidate-count gate DISPATCH — total_candidates={N} (>{gate} threshold, cov_scope={cov_scope})"
```

**Return-TOON shape invariant**: BOTH branches MUST produce the IDENTICAL return-TOON shape documented in `## Dispatched-envelope output` below (`status`, `display_detail`, `findings[N]{file,line,defect_class,rationale,cohort_size}`). The inline branch produces the same TOON-shaped result in dispatcher context — `display_detail` follows the same three-verdict rule bit-for-bit (`"self-review: nothing to check - no candidates surfaced"` / `"self-review clean: {N} candidates examined, no check matched"` / `"self-review found {K} issues in {C} classes"`), and `findings[]` carries the same entry shape, `cohort_size` included. In particular the inline branch MUST pick between the two clean verdicts on the same `total_candidates == 0` predicate the dispatch branch uses; a branch that collapses them back to one undifferentiated clean string violates this invariant. Downstream consumers (Step 4 bookkeeping, output-template rendering) MUST NOT need to differentiate which branch produced the result. The gate is a pure dispatch-cost optimization — semantics are preserved bit-for-bit.

### Step 2: LLM cognitive phase (dispatch)

Compute the variant target via the role resolver:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized post-resolve dispatch log line — see [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role=default workflow=plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md plan_id={plan_id}"
```

Dispatch the LLM workflow with the candidate envelope:

```text
Task: plan-marshall:{target}
  prompt: |
    name: pre-submission-self-review
    plan_id: {plan_id}
    skills: []
    workflow: plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md

    candidates: |
      {candidates_toon}

    WORKTREE: {worktree_path}
```

The dispatched workflow body executes Step 2a (cross-reference setup) followed by Step 3 (fifteen cognitive checks).

#### Step 2a: Cross-reference setup (in-context — MUST run before any check)

Before scanning the line-level candidate lists, load the contract sources surfaced by the deterministic phase. This step is the workflow-shape fix for the failure mode where the LLM reviews each surfaced hunk in isolation and overlooks contract drift.

1. For every entry in `candidates.contract_sources`, read every path listed in the `sources` field. These are the `SKILL.md` and `standards/*.md` files governing the changed code. Read them in full — not excerpts.
2. For every entry in `candidates.schema_bearing_files`, read the file. These are nearby markdown documents that declare a fenced JSON or TOON schema; they govern the post-image of any hunk that touches the same schema.
3. Hold the loaded contract content in working memory for the rest of the cognitive phase. The fifteen checks below cross-reference hunks against this content; do not re-discover contracts on demand.

### Step 3: Apply fifteen checks (in-context)

For each non-empty candidate list, apply the corresponding cognitive check to the surfaced items only — never expand the review to candidates the helper did not surface.

#### Class-closure obligation (fix the class, not the instance)

A defect that appears once in a change almost never appears only once: the same misreading applied to one site was usually applied to its siblings in the same edit. Filing one member per round makes the step loop back once per member, and each loop-back round pays a full step dispatch to find the next instance of a defect already understood.

**The obligation**: when a check fires on a surfaced candidate and you record a finding whose `defect_class` is D, you MUST — before composing the findings list — re-scan every OTHER surfaced candidate **of the same candidate list** for D, and file every member you find in the SAME round.

`defect_class` is the machine-readable discriminator this sweep groups on. It is the same token Step 4 Branch B files as the finding `--title`, so no new taxonomy is introduced.

**The bound**: the sweep is bounded by the surface-only rule stated immediately above — it re-examines candidates the surfacer already surfaced and NEVER widens past them. It is a re-scan of the existing candidate set for one more discriminator, not a licence to read files the surfacer did not surface.

**Consequence of the bound, stated so it cannot be misread as a coverage claim**: because the surfaced set is round-dependent (a delta round surfaces only the files changed since the previous round — see Step 1), a delta round's class sweep reaches only the delta surface. A member of class D sitting in a file unchanged since the previous round is NOT swept during a delta round. The class is still closed as a class, because the closing **full-surface confirmation pass** (Step 1, Step 4 Branch A) runs this same sweep over the whole plan diff before the step may record `done`. That confirmation pass — not any intermediate round, and not round 1 — is what closes the class. Round 1's clean result is deliberately not treated as standing evidence for a class first discovered in a later round: the discriminator was never applied to round 1's surface.

**Every finding carries its cohort size.** Each entry in the returned `findings[]` gains a `cohort_size` field: the number of findings sharing that entry's `defect_class` in this round. A cohort of one is then distinguishable from a cohort whose remaining members were never looked for — without the field, both render as a single finding and the difference is invisible.

> **Coverage contract**: the per-candidate lens depth is governed by the coverage instruction resolved in Step 0 (`{cov_instruction}`). The surface-only rule above caps the scope to what the surfacer surfaced at every rung — never widen the candidate set past it. The thoroughness rung sets the depth: `inherit`/`T1`/`T2` → run the fifteen checks below as today (face-value per candidate); `T3`+ → additionally trace each surfaced candidate's siblings and cross-references before adjudicating it (the contract cross-references in Step 2a already supply the anchors). `inherit/inherit` reproduces today's behavior bit-for-bit. See the two-dial scope × thoroughness contract in [`../../persona-plan-marshall-agent/standards/thoroughness.md`](../../persona-plan-marshall-agent/standards/thoroughness.md) and the gather/expand/consume obligation in [`../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md`](../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md).

#### Present-state grounding precondition (gates contract_drift and its variants on confirmed absence)

The "absence-class" checks — contract drift (check 5) and its variant labels near-identical-hunk (check 12 → `touched_claim_unverified`), count-prose (check 11 → `stale_count_prose`), unguarded-boundary (check 10 → `unguarded_boundary`), ordinal-reference (check 13 → `ordinal_reference_stale`), unreachable-guard (check 14 → `unreachable_guard`), and worked-example clause mismatch (check 15 → `worked_example_clause_mismatch`) — adjudicate a candidate by claiming that some flagged content is *missing*, *stale*, *drifted*, *unreachable*, or *not demonstrated* relative to the current contract. Check 14 joins this set because its verdict is an absence claim of exactly the same shape: it asserts that a downstream guard's refusal path can never be taken, which the surfaced diff snapshot alone cannot establish. Check 15 joins it for the same reason: it asserts that the clause's required predicate is ABSENT from what its GOOD example branches on, and the surfaced diff snapshot cannot establish that the live document still reads that way. Each of these checks operates on a surfaced hunk or sibling line rather than on the live file, so it can fire a false positive when the flagged content is *already present and correct in the current worktree doc state* — for example, a contract source whose schema the diff actually updated to agree with the code, a count-prose number the same change already corrected, or a touched-claim line whose surviving claims are all still accurate in the saved file. The surfaced candidate is a snapshot of the diff, not proof that the defect survives in the committed-to-disk document.

**Precondition (MUST run before recording any finding from check 5, 10, 11, 12, 13, 14, or 15)**: before emitting a finding whose defect class is `contract_drift`, `touched_claim_unverified`, `stale_count_prose`, `unguarded_boundary`, `ordinal_reference_stale`, `unreachable_guard`, or `worked_example_clause_mismatch`, re-read the flagged content from the CURRENT worktree file state (use the `Read` tool against the file path under the pinned cwd / `WORKTREE`) and confirm the defect is genuinely present in the live document. Emit the finding ONLY when the flagged content is confirmed absent, stale, unguarded, unreachable, or undemonstrated in the current file state — i.e. the contract source still disagrees with the live code, the count-prose number still mismatches the live count, the boundary call is still unguarded on disk, the derivation on disk still scans rather than anchors, or the live GOOD example still branches on a predicate its clause does not require. When the current file state already reflects the corrected content (the flagged drift/staleness/gap is no longer present on disk), the candidate is a stale diff-snapshot artefact — record NO finding. This grounding step is the single guard that prevents these seven checks from emitting false-positive findings against content that already exists, corrected, in the file.

1. **Symmetric pair test-coverage check** — for each `symmetric_pairs` entry, search the test directory for a test that exercises BOTH `name` and `partner` and asserts the post-state of the partner without first invoking `name` in the same test. A symmetric pair where one half is silently skipped is the canonical defect class. Defect → record finding `{file, line, defect_class: symmetric_pair_uncovered, rationale: <which half is unexercised and why it matters>}`.

   **Flag-form-coverage comparison** — also compare the flag *forms* covered across paired argument guards using the `flag_guard_pairs` candidate list. Group the `flag_guard_pairs` entries that participate in the same mutually-exclusive (or otherwise paired) argument contract — typically two sibling guards in the same change that gate a `--flag` and its alternative. For each such pair, compare the `forms_covered` value of each guard:

   - When one guard covers `both` forms (`--flag value` AND `--flag=value`) and its sibling covers only `space` or only `equals`, the sibling's uncovered form is a defect. Record finding `{file, line, defect_class: flag_form_asymmetry, rationale: <which flag, which form is uncovered, and the contract it risks>}`. The `line` is the under-covering guard's first-occurrence line from its `flag_guard_pairs` entry.
   - When both guards in a pair cover the same form set (`both`/`both`, `space`/`space`, or `equals`/`equals`), there is no asymmetry — record no finding.
   - A lone `flag_guard_pairs` entry with no sibling in the change carries no comparison; record a `flag_form_asymmetry` finding for the lone entry only when the surrounding code makes the missing form a real risk (e.g., the guard feeds a mutually-exclusive injection decision).

   **Worked example** (the lesson that drove this check — PR #508, pr-comment hash_id `d9c3c7`): a Bucket B injection helper guarded its two arguments asymmetrically. The `--plan-id` guard covered `both` forms (`'--plan-id' in args` AND `'--plan-id=' in args`), while the `--project-dir` guard covered only the `space` form (`'--project-dir' in args` with no `'--project-dir=' in args` sibling). The `flag_guard_pairs` list surfaces two entries — `{flag: --plan-id, forms_covered: both}` and `{flag: --project-dir, forms_covered: space}` — and the comparison above records a `flag_form_asymmetry` finding: the `--project-dir=value` (equals) form slips past the guard, so a command already carrying `--project-dir=...` would receive a second injected `--project-dir`, violating the mutually-exclusive-arguments contract on the target Bucket B script. The local self-review reported "clean" before this check existed; the strengthened check reproduces the defect the PR-review bot caught.

2. **Regex over-fit boundary check** — for each `regexes` entry, construct one synthetic example that SHOULD match (positive) and one that SHOULD NOT match (negative), and verify the regex/glob's behavior on each. If the boundary is wrong, record finding `{file, line, defect_class: regex_overfit, rationale: <example that fails the intended boundary>}`.

3. **Wording disambiguation check** — for each `user_facing_strings` entry, read the string out of the surrounding context and ask "could this mean two things?". If the answer is yes (an operator could plausibly take the wrong action based on the wording alone), record finding `{file, line, defect_class: ambiguous_wording, rationale: <the two readings, and which one was intended>}`.

4. **Duplication scan** — for each `markdown_sections` entry, compare the new/edited section's contract against its sibling sections (provided in the `siblings` field) within the same file. Two sections that describe the same check, table, or rule with subtly different wording are a defect — operators do not know which to follow. Record finding `{file, heading, defect_class: duplicate_prose, rationale: <which sibling overlaps and where they diverge>}`.

5. **Contract drift cross-check** — for every modified file that appears in `contract_sources`, AND every hunk in the diff that touches a schema declared in any `schema_bearing_files` entry, verify the post-image of the change against the documented contract:
   - For every `markdown_sections` entry whose `file` equals (or shares a parent skill with) a `contract_sources` entry, verify that the new/edited section's documented schema, table fields, or detection heuristic agrees with what the code under that skill actually emits or enforces.
   - For every code hunk that adds or modifies a function emitting a schema (e.g., `output_toon({...})`, `print(json.dumps({...}))`), verify that the emitted field set matches the schema declared in the corresponding `schema_bearing_files` entry. Missing fields, renamed fields, or extra undocumented fields are all drift.
   - For every detection heuristic added or modified (e.g., regex over a project marker, glob over a path category), verify that the heuristic agrees with the contract section that documents the same detection rule. A loosened heuristic (substring where the contract specifies a structured marker) is drift.
   - **Advertised-form sub-check** — for each `advertised_form_help_strings` entry, the helper has surfaced an argparse `help=` string (`help_text`, on `line`) that advertises more than one accepted input form for the destination `arg` AND a raw `args.<arg>` pass-through (at `raw_pass_line`) that forwards the externally-supplied value with no intervening normalization. The advertised contract — "this argument accepts every advertised form" — drifts from the handler behaviour when only the form the raw value happens to be in actually works. Read both the `help_text` and the `raw_pass_line` site in context: a help string that promises e.g. "Issue number or URL" while the handler passes `args.issue` raw (never normalizing the URL form to a number, or vice versa) is advertised-form drift. When the handler DOES normalize the value before use (the surfacer would not have surfaced the candidate, but re-confirm on the live file), or the multiple "forms" are genuinely interchangeable downstream, record no finding.

   Defect → record finding `{file, line, defect_class: contract_drift, rationale: <which contract source disagrees with the hunk, and what the drift is>}` — but ONLY after the **Present-state grounding precondition** above confirms the drift survives in the CURRENT worktree file state. Re-read the flagged content from the live document with the `Read` tool; when the current file already reflects the corrected schema/field-set/heuristic (the drift the hunk snapshot suggested is no longer present on disk), the candidate is a stale diff-snapshot — record NO finding.

6. **Producer-consumer check** — for each `producer_consumer` entry, the helper has already established that the produced output key has no consumer in the diff. Confirm the dangling producer is a real defect: read the producer line and decide whether the emitted value is genuinely meant to be read downstream (a contract field a consumer must dispatch on) or is a legitimate write-only output (e.g., a TOON field the script emits for the caller, never re-read inside the script). A value emitted into a control-flow contract with no branch reading it is a defect. Defect → record finding `{file, line, defect_class: producer_without_consumer, rationale: <which key is produced, and the downstream branch that should consume it but does not>}`.

7. **Source-of-truth consistency check** — for each `source_of_truth` entry, the helper has surfaced a constant declared with divergent literals across two files. Read both declarations in context and decide which is the authoritative source of truth and whether the divergence is an intentional per-file value or a drift (the diff updated one declaration and forgot the sibling). A genuine drift — two declarations that are meant to agree but no longer do — is a defect. Defect → record finding `{file, line, defect_class: source_of_truth_drift, rationale: <the constant, the two divergent values, and which declaration is stale>}`. Use the first declaring file/line from the entry's `files` field as the finding anchor.

8. **Same-document consistency check** — for each `same_document_consistency` entry, read the added normative directive (`text`) and compare it against the sibling normative statements ALREADY present in the same document. A new `MUST`/`NEVER`/`ALWAYS` rule that contradicts, narrows, or widens an existing normative statement in the same file leaves operators unable to know which rule governs. Defect → record finding `{file, line, defect_class: same_document_contradiction, rationale: <the new directive, the sibling directive it contradicts, and the conflict>}`. When the added directive is consistent with (or orthogonal to) its document siblings, record no finding.

9. **Description-vs-body consistency check** — for each `description_vs_body` entry, read the frontmatter `description`/`summary` (`description` field) against the document body the diff changed. When the body now implements a model the description no longer matches — a deleted machinery the description still advertises, a renamed concept, a removed track/mode the summary still names — the description is stale. Defect → record finding `{file, line, defect_class: description_body_drift, rationale: <which part of the description the body no longer implements>}`. When the description still accurately summarizes the changed body, record no finding.

10. **Lone-unguarded-boundary check** — for each `unguarded_boundaries` entry, the helper has surfaced an added `subprocess.*` / file-I/O call with no `check=True` and no enclosing `try/except` in the same function. Read the call in context and decide whether the missing guard is a real defect: a boundary call whose failure (a non-zero subprocess exit or an I/O exception) would corrupt downstream state or silently produce a wrong result must be guarded; a call whose failure is already handled by the caller, or where a silent failure is the intended behavior, is not. Defect → record finding `{file, line, defect_class: unguarded_boundary, rationale: <which boundary call is unguarded and the failure it would swallow>}` — but ONLY after the **Present-state grounding precondition** above confirms the call is still unguarded in the CURRENT worktree file state (re-read the surrounding context of the flagged line with the `Read` tool; when the live document already wraps the call in `check=True` or a `try/except`, record NO finding). When the unguarded call is legitimately fire-and-forget, record no finding.

11. **Stale-count-prose check** — for each `count_prose` entry, the helper has surfaced a count phrase (a digit or number word adjacent to a cardinality noun) in a `SKILL.md` sibling of a modified file. Re-count the referent the prose claims — the number of operations, fields, steps, rules, or commands the prose enumerates — against the actual count in the post-image of the change. When the diff changed the count (added or removed an item) but the prose number was not updated, the prose is stale. Defect → record finding `{file, line, defect_class: stale_count_prose, rationale: <the prose number, the actual post-image count, and what the diff changed>}` — but ONLY after the **Present-state grounding precondition** above confirms the mismatch survives in the CURRENT worktree file state (re-read the prose line and the relevant sections of the live document with the `Read` tool to re-count its referent; when the current file already carries the corrected number, record NO finding). When the surfaced number still matches the actual count, record no finding.

12. **Touched-claim whole-line re-check** — for each `touched_claims` entry, the helper has surfaced the `+` line of a near-identical hunk pair that differs from its `-` predecessor by exactly one token. The single-token swap is the obvious edit; the risk is that the REST of the line still carries a claim that the swap invalidated. Read the surfaced `+` line and verify every OTHER claim it makes (a count, a name, a reference, a condition) is still correct after the swap — not just the swapped token. When a surviving claim on the line is now wrong because of the swap, it is a defect. Defect → record finding `{file, line, defect_class: touched_claim_unverified, rationale: <the swapped token, and the surviving claim on the line that the swap invalidated>}` — but ONLY after the **Present-state grounding precondition** above confirms the invalidated claim survives in the CURRENT worktree file state (re-read the surfaced line in the live document with the `Read` tool; when the current file already carries the corrected line, record NO finding). When the rest of the line remains correct, record no finding.

13. **Same-document ordinal-reference re-check** — for each `ordinal_references` entry, the helper has surfaced an added same-document ordinal reference (`item N` / `step N` / bare `(N)`, on `line`) that points into an ordered-list block the same diff touched (the referenced item's post-image line is `list_line`). Inserting, deleting, or reordering a numbered-list item renumbers every later item, but an ordinal reference elsewhere in the same document is a hard-coded position the edit does NOT update — so it silently retargets to whatever item now occupies the old ordinal, or dangles past the end of the list. Read the referenced ordered-list block in the CURRENT worktree document and confirm the item now sitting at ordinal `N` is the item the reference intends. When the ordinal now resolves to the wrong item (or past the list end), it is a defect. Defect → record finding `{file, line, defect_class: ordinal_reference_stale, rationale: <the ordinal reference, the item it now resolves to, and the item it was meant to name>}` — but ONLY after the **Present-state grounding precondition** above confirms the mis-resolution survives in the CURRENT worktree file state (re-read both the reference line and the referenced list in the live document with the `Read` tool; when the current file already re-points the reference, or it was rephrased to a content anchor, record NO finding). Prefer recommending a content-anchored rephrase ("see the X step") over a renumbered ordinal so a future renumber cannot re-strand it. When the ordinal still resolves to its intended item, record no finding.

14. **Unreachable-guard check (scan-derived key)** — for each `scan_derived_keys` entry, the helper has surfaced a function (`name`) that decomposes a value into `sequence` and then selects a key by first-match of a compiled pattern over that sequence (the scan loop is on `line`), instead of indexing the decomposition at a position anchored on a known root. Every input whose out-of-domain leading segments happen to match collapses to the SAME key, so a downstream guard fed by that key can never observe a difference — its refusal path is unreachable while its tests stay green, because the tests only ever supply inputs whose first match is the intended one. Read the deriving function and its callers in context and decide whether the collapse is real: does an input the caller can actually receive carry an out-of-domain leading match, and does some downstream branch treat the derived value as an identity (grouping, cardinality, or equality)? The `key_consumed` flag narrows this — `true` means the surfaced diff already contains such an identity consumer, `false` means none was visible in the diff and the caller must be located before adjudicating (it does NOT mean the candidate is benign). Defect → record finding `{file, line, defect_class: unreachable_guard, rationale: <the scanned sequence, the input that collapses to the wrong key, and the guard whose refusal path becomes unreachable>}` — but ONLY after the **Present-state grounding precondition** above confirms the scanning derivation survives in the CURRENT worktree file state (re-read the deriving function in the live document with the `Read` tool; when the live code already anchors the decomposition at a fixed position relative to a known root, record NO finding). Prefer recommending the anchored form (relativize against the known root, then index a fixed position) over widening the pattern, which only moves the collapse. When the sequence is bounded and every element is in-domain by construction, record no finding.

15. **Worked-example clause-mismatch check** — for each `worked_example_pairs` entry, the helper has surfaced a clause section (`clause`) whose GOOD worked example (its marker is on `line`) branches on `example_predicate` while the clause's own normative prose requires `required_predicate`. **The surfacer emits ONLY the disagreeing case** — every surfaced entry carries `agrees: false`, and a pair whose predicates agree, whose clause names no normative predicate, or whose GOOD example branches on nothing recoverable never reaches this check. So this check does not re-decide whether a pair is worth looking at; it decides whether the surfaced disagreement is a real contradiction.

    Read the clause's normative statement and its GOOD example together and adjudicate: state the concrete input on which the GOOD example produces the verdict the clause requires. When that sentence cannot be written — the example branches on a field that answers a DIFFERENT question than the clause's rule, so a reader following the example would reproduce the shape the clause forbids — the worked contrast contradicts its own clause. The token-level disagreement the surfacer found is evidence, not the verdict: a clause and its example can legitimately use different vocabulary for the same predicate, and that case is a false positive to be dismissed rather than filed.

    Defect → record finding `{file, line, defect_class: worked_example_clause_mismatch, rationale: <the predicate the clause requires, the predicate the example branches on, and the concrete input on which they diverge>}` — but ONLY after the **Present-state grounding precondition** above confirms the mismatch survives in the CURRENT worktree file state (re-read the whole clause section in the live document with the `Read` tool; when the live example already branches on the required predicate, record NO finding). Prefer recommending a correction to the EXAMPLE over a weakening of the clause: the clause is the normative statement, and an example that disagrees with it is the thing that is wrong.

### Dispatched-envelope output (returned from Steps 2–3 to Step 4)

```toon
status: success | error
display_detail: "<≤80 char ASCII summary>"
findings[N]{file,line,defect_class,rationale,cohort_size}:
  - ...
```

`cohort_size` is the number of findings in this round sharing that entry's `defect_class` (see § Class-closure obligation). Every entry carries it, including a genuine cohort of one — an omitted field would be indistinguishable from a cohort whose other members were never looked for.

`status: success` regardless of findings count — the workflow itself succeeds at producing the structural-review verdict; the caller's manifest-step orchestration translates a non-empty `findings` list into the manifest step's `--outcome failed` per the gating-step convention. Empty `findings` → caller marks `--outcome done`.

`display_detail` shape. A clean run has TWO disjoint verdicts — an undifferentiated single clean string is prohibited, because "nothing was there to check" and "everything checked passed" are different pieces of information and an operator reading one as the other draws the wrong conclusion about review coverage. Let `{N}` be the surfacer's emitted `counts.total`. Which lists that sum covers is the surfacer's contract — see [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) § Output Schema — and is deliberately not restated here:

- Empty `findings` AND `{N} == 0` (**nothing-to-check** verdict) → `"self-review: nothing to check - no candidates surfaced"`. No candidate was surfaced at all, so no check ever ran. The zero-generator fallback path (Step 1) reports this verdict.
- Empty `findings` AND `{N} > 0` (**no-check-matched** verdict) → `"self-review clean: {N} candidates examined, no check matched"`. Candidates were surfaced and every check was applied to them without firing.
- Non-empty `findings` → `"self-review found {K} issues in {C} classes"`, where `{C}` is the number of DISTINCT `defect_class` values across those `{K}` findings. The class count rides this verdict rather than a clean one because it is the widest of the three: it renders to 45 characters at `{K}={C}=9999`, leaving 35 characters of headroom against the 80-character budget, whereas the no-check-matched verdict already spends 61 of its 80. Reporting both figures is what makes a round of nine findings in one class legible as one swept cohort rather than as nine unrelated defects.

All three are ≤80-char ASCII with no trailing period, and no verdict is a prefix of another — so a consumer matching a whole verdict string can never mistake one verdict for another, and the two clean verdicts in particular diverge at their second word (`nothing` vs `clean`).

### Step 4: Mark Step Complete (inline)

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

**Branch A — findings list is empty**: read the `display_detail` returned by the workflow verbatim (the workflow computes the candidate count for the human-readable message).

**Precondition — the clean result MUST come from a full-surface pass.** Before recording `done`, confirm the returned verdict was produced by a run that carried NO `--since-ref` (the surfacer echoes `surface_scope: full`). A `done` recorded off a delta-scoped clean result would close the step on evidence covering only the files that changed since the previous round. When the clean result came from a delta round, do NOT record `done` here — go back to Step 1, re-run the surface call at full scope, and record the outcome from that pass instead.

Immediately before invoking `mark-step-done`, resolve the worktree HEAD SHA so the dispatcher can detect a stale completion record after a downstream loop-back commit advances HEAD (see § HEAD-dependency above):

```bash
git -C {worktree_path} rev-parse HEAD
```

The `{worktree_path}` value is the path resolved by `phase-6-finalize` Step 0 (Resolve Worktree and Main Checkout Paths); do NOT re-resolve it from any other cwd or shell context. Capture the stdout as `{sha}` (a 40-character hex SHA) and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome done \
  --display-detail "{display_detail_from_workflow}" \
  --head-at-completion {sha}
```

**Branch B — findings list is non-empty**: first persist every finding to the plan's `qgate-6-finalize.jsonl` finding store, then surface the findings in the finalize TOON output (consumed by `output-template.md`) so the operator sees `file:line` and `defect_class` per finding.

For every entry in the returned `findings[N]{file,line,defect_class,rationale,cohort_size}` list, emit one `manage-findings qgate add` call. This loop runs in the inline dispatcher context (the same context as the `mark-step-done` call below). `--phase 6-finalize` and `--source qgate` are mandatory; `--type bug` is the canonical finding type for a structural self-review defect. The `--detail` body carries the entry's `cohort_size` so the loop-back fix task addresses the CLASS rather than the instance — a fix task that reads "1 of 4 in this class" is told, at the point of work, that three siblings are waiting.

`{subject}` is what distinguishes the finding from its class siblings — the specific site or claim at fault, not a restatement of the class. The title MUST NOT be the bare `{defect_class}`: a round that finds several members of one class is the normal case (that is precisely what `cohort_size` counts), and identical titles collapse the cohort into a single deduped finding, destroying the class sweep the `cohort_size` field exists to drive. This restates, at the point of use, the finding-authoring contract owned by [`ext-self-review-plan-marshall/SKILL.md`](../../../../pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md) § Finding-authoring contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title "{defect_class}: {subject}" --detail "{rationale} [defect_class {defect_class}: {cohort_size} finding(s) in this class this round]" \
  --file-path "{file}" \
  --component pm-plugin-development:ext-self-review-plan-marshall --severity warning
```

Then resolve the worktree HEAD SHA — the same call and the same `{worktree_path}` as Branch A — and record the failed outcome carrying it:

```bash
git -C {worktree_path} rev-parse HEAD
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome failed \
  --display-detail "{display_detail_from_workflow}" \
  --head-at-completion {sha}
```

Branch A (empty findings) persists nothing — there are no findings to write. Branch B forwards `--head-at-completion` even though the dispatcher retries `failed` records unconditionally: the SHA carries no *retry* decision value, but it IS the delta anchor the NEXT round reads in Step 1. A `failed` record written without it leaves the following round with no anchor, which silently degrades that round to a full sweep — the exact re-sweep this scoping exists to remove. The anchor is written on both terminal branches for that reason, not for the dispatcher's benefit.

The dispatcher's existing failure handling halts the phase on `outcome=failed`, matching the gating-step contract used by `pre-push-quality-gate`. The operator must address every finding (amend the diff: rename, tighten regex, rewrite wording, delete duplicate section, fix contract drift), re-run the step, and only then advance to `push`.

## Worked example: the lesson that drove this workflow

Both defect classes were missed in the dogfood run that drove this workflow's introduction; the LLM pass was reviewing surfaced hunks one at a time without consulting the contracts that lived in the same diff:

- **Missing schema field**: a helper emitted `markdown_sections[N]{file,heading,siblings}` while the consumer's documented schema declared `markdown_sections[N]{file,line,heading,siblings}` (the `line` field anchors findings). Cross-checking the emitted dict against the schema declared in the same change set catches the omission.
- **Loosened detection heuristic**: a CI-provider detection routine matched on a substring (`'github' in url`) where the contract section documented a structured project marker (`.github/workflows/*.yml`). Cross-checking the new heuristic against the documented marker catches the over-broad match before it produces false positives in production.

The Step 2a cross-reference setup plus Step 3 check 5 close that gap.
