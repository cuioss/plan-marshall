---
lane:
  class: adversarial
  cost_size: L
name: default:pre-submission-self-review
description: Pre-submission structural self-review (symmetric pairs, regex over-fit, wording, duplication, contract drift, producer-without-consumer, source-of-truth drift, same-document contradiction, description-vs-body drift, unguarded boundary, stale count-prose, touched-claim re-check, ordinal-reference re-check, unreachable guard behind a scan-derived key, worked-example clause mismatch, duplicate-claimable key, discard-without-report, hoisted-binding-shadow) before push
order: 8
mutates_source: false
head_dependent: true
default_on: true
presets: []
records_facts:
  - acceptance
  - may_close
  - work_performed
requires_prompt_fields:
  - candidates
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Pre-Submission Self-Review

Pure executor for the `pre-submission-self-review` finalize step. Catches the class of structural defects that PR-review bots reliably surface but local quality gates systematically miss: missing initialization in symmetric save/restore pairs, regex/glob over-fit, ambiguous user-facing wording, duplicate prose sections covering the same contract, and schema/contract drift.

Outcome bookkeeping (Step 4) now includes finding persistence: every returned finding is written to the plan's `qgate-6-finalize.jsonl` finding store before the step's `--outcome loop_back` is recorded.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

The step combines a deterministic helper that surfaces concrete candidates from the staged diff (Step 1 below) with an LLM cognitive review applied only to those candidates (Steps 2–3 below), and a second, non-authoring reader that accepts or refuses the verdict that review produced (Step 3b below). Step 1 (deterministic surface), Step 3b's dispatch, and Step 4 (outcome bookkeeping) run inline in the manifest dispatcher's context. When `total_candidates <= {gate}`, Steps 2–3 (contract cross-reference setup + the eighteen LLM cognitive checks) execute inline in the dispatcher context; when `total_candidates > {gate}`, they execute in a dispatched envelope under `--phase phase-6-finalize` (no `--role` — pre-submission-self-review tracks `phase-6-finalize.default`). Step 3b remains a separate dispatched verifier on both branches, issued from the inline dispatcher context. The two dispatches are separate firings and separately audited; § "Author and verifier are different parties" below owns why the second one exists and why the inline dispatcher is the only context it can be issued from. On any finding the LLM returns, the step records `outcome=loop_back` with `loop_back_target: 6-finalize` and the dispatcher's continuation hook admits the round — a PRODUCTIVE non-completion, not a failure. This is deliberately NOT the convention `pre-push-quality-gate` follows: that step records `failed`, because a red build gate ran cleanly and returned a negative verdict, whereas this step hands back findings for amendment on the branch in hand. The two being different is the point — see [`../../manage-execution-manifest/standards/manifest-schema.md`](../../manage-execution-manifest/standards/manifest-schema.md) § "Which situation each `outcome` value means".

This document carries NO step-activation logic. Activation is controlled by the manifest composer in `manage-execution-manifest/scripts/manage-execution-manifest.py` (see `manage-execution-manifest/standards/decision-rules.md`). No footprint-gated pre-filter drops this step: the eighteen cognitive checks it targets apply to any code or doc change, so there is no glob gate to fail. More than one compose-time subtraction can drop it. The `commit_push_disabled` pre-filter drops it transitively when `commit_and_push == false`, because both push-only gates are meaningless with no downstream push. The `scope_gated_finalize` pre-filter also drops it when `scope_estimate == 'surgical'` — independently of `commit_and_push` — unless the step carries a declared lane override, which grants it immunity from that gate. For the authoritative set of compose-time subtractions and what each one reads, see [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md); do not treat the two named here as exhaustive. When the dispatcher runs this step the executor always runs to completion; which outcome a given round records is Step 4's own precondition set (§ "Step 4: Mark Step Complete"), not restated here — a non-empty findings list records `outcome=loop_back` with `loop_back_target: 6-finalize` and the dispatcher re-enters the finalize step loop rather than halting the phase.

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

`candidates` is this step's one **step-specific required prompt-body field** — a field beyond the exempt set (the generic dispatch contract, the `caller_phase` extension, and the dispatcher-supplied runtime inputs). It is declared machine-readably in this step's `requires_prompt_fields` frontmatter, marked `Required` in the table above, and carried in the Step 2 dispatch body below. A three-scope guard, `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py`, fails the build if those surfaces disagree. This step keeps its **own** dispatch body, so it is responsible for carrying every field it declares there; a step dispatched through the generic template instead lets the template's declared-field slot carry them, which is equally supported. See [`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md) § "Step-specific prompt-body fields".

**The candidate sub-list vocabulary is NOT restated here.** Each sub-list's key, entry schema, and the check that consumes it are declared once, authoritatively, in [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) § Output Schema and § Required Candidate Sub-Lists — derived in turn from the implementor's `CANDIDATE_LISTS` registry, which is the single code-side source of the emitted key set. Read the emitted `counts` block for what this round actually surfaced, and that document for what each key means.

A hand-maintained copy of the row set used to live here. It is removed rather than corrected: a second enumeration of a registry-derived vocabulary has to be re-edited on every registry change, states a cardinality that goes stale the moment one is added, and gives a reader two lists to reconcile with no way to tell which is authoritative. Removing it deletes that drift class instead of re-fixing one instance of it.

Skills the caller MUST forward in `skills[]`: none (the workflow reads files with the `Read` tool and emits no script calls).

## HEAD-dependency

`pre-submission-self-review` declares `head_dependent: true` in its frontmatter — that fact IS the membership declaration the dispatcher's re-entry check reads (see [`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"). Its verdict is a **structural review of the plan's diff**, so the verdict is a function of that diff: a loop-back fix task that advances HEAD past the recorded `head_at_completion` produces a diff this step never examined, and a `done` record carried across that advance would stand as green for a diff no check ever ran against. The dispatcher MUST therefore re-fire this step against the newer HEAD. Capture `git rev-parse HEAD` immediately before EVERY terminal `mark-step-done` call — every branch of Step 4 without exception — and forward it via `--head-at-completion {sha}`. Naming the branches individually here is what let a later-added branch fall outside the rule while still reading as covered by it.

The only thing that releases a branch from FORWARDING the value is the capture itself failing. Branch C is reached by `git_unavailable` among others, so its `rev-parse` can return no SHA; it then omits the flag rather than passing an unresolved placeholder (§ Step 4 Branch C). That is not a branch exempted from the rule — it is the rule with nothing to hand it, and it is available only because the `missing_head_at_completion` refusal is scoped to the `done` outcome.

The recorded SHA carries a **second, independent** load: it is the **delta anchor** the next round scopes itself against (Step 1 reads it back and passes it as `--since-ref`). That is why its absence on a `done` record is now REFUSED rather than tolerated — `manage-status mark-step-done` returns `error: missing_head_at_completion` and writes nothing when a `head_dependent: true` step records `done` without it. An unanchored record would leave the following round unable to define its delta, silently degrading it to a full re-sweep.

## Settle-band position — review runs after the mutators

This step sorts AFTER the code-mutating settle steps (`order: 8`, behind `finalize-step-simplify` at 5 and `finalize-step-security-audit` at 7) and BEFORE the derived-state refresh (9) and the quality gate (10). That position resolves the simplify-placement question: the review examines the post-simplification, post-hardening tree rather than a diff a later simplify pass rewrites. It does NOT cover what the two later steps commit — the refreshed descriptors and any gate auto-fix edits: the descriptors are certified by the quality gate that runs after them, and the gate's own trailing commit is covered by the push reconciliation record, never by this review. A loop-back fix commit still advances HEAD past the recorded `head_at_completion`, and the re-fire then scopes itself as a delta round via `--since-ref`, so only the fix's own paths are re-examined rather than the whole diff re-swept. This step declares `mutates_source: false`, so its position after the mutators adds no commit of its own and moves no SHA the gate must then cover.

## Author and verifier are different parties

The party that AUTHORS this step's verdict is not the party that ACCEPTS it. Before this separation existed one party did both: whichever context ran the eighteen checks produced the findings list, and Step 4 then selected its branch by reading that same list — so the round closed on the author's own reading of its own output, and no second party ever had to agree with it.

Three roles, and the context each one runs in:

| Role | What it does | Where it runs |
|------|--------------|---------------|
| **Surfacer** | Produces the candidate set. Deterministic, read-only, no judgement of its own. | A script call in the inline dispatcher context (Step 1). |
| **Author** | Applies the eighteen checks to the surfaced candidates and produces the findings list and the verdict. | The dispatched envelope (Step 2) — or, under the Step 1b gate, the inline dispatcher context. |
| **Verifier** | Answers the two questions Step 3b poses about the author's verdict. Files no finding and edits no file. | A SEPARATE dispatched envelope (Step 3b), always issued from the inline dispatcher context. |

**The harness decides where a verifier can live, and it admits exactly one origin.** A dispatched subagent is a leaf: it cannot spawn another subagent, and every cross-envelope dispatch originates from a context that is not itself dispatched — see [`../../ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md). A verifier spawned from INSIDE the Step 2 author envelope is therefore unreachable, and no amount of prompt authoring makes it reachable. What IS reachable is a second dispatch from the inline dispatcher context: that context already issues the Step 2 author dispatch, and a context that can issue one dispatch can issue two. Step 3b is that second dispatch, and it is the only place the verifier may be spawned from.

**The arrangement is identical on both author branches**, which is what keeps the Step 1b gate a pure cost optimization. When the gate sends the author INLINE, the dispatcher context IS the author — so the verifier must still be Step 3b's dispatched envelope, and that is precisely the branch on which running the verifier inline would collapse the two roles back into one party. When the gate DISPATCHES the author, the two already occupy different envelopes and Step 3b adds the second, non-authoring reader. Either way Step 4 reads answers that neither role could grant itself — see § "Step 3b" for what those answers are and what closing on them requires.

**What the verifier deliberately cannot do.** It is a leaf, so it cannot escalate to the operator and cannot dispatch further — see § "Step 3b" for its return contract. It files no finding and edits no file either: the surfacer stays a read-only deterministic script and the author stays the single filer, so the independence is expressed as role separation across the dispatch boundary and NOT as new judgement added inside either of the other two roles.

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

Locate `metadata.phase_steps.6-finalize.pre-submission-self-review` and read BOTH its `outcome` and its `head_at_completion`. Exactly one of two cases holds:

- **The prior record's `outcome` is `done` or `loop_back` AND its `head_at_completion` is a non-empty SHA** → this is a **delta round**. Capture that SHA as `{since_ref}` and pass `--since-ref {since_ref}` on the surface call below. The surfacer narrows the file set to the footprint intersected with the paths changed since that SHA.
- **Anything else** — no prior record, an absent/empty `head_at_completion`, or an `outcome` outside `{done, loop_back}` — → this is a **full round** (round 1, a first run after a record that carried no anchor, or the round after a Branch C infrastructure failure). Do NOT pass `--since-ref` at all. Never substitute the base branch, `HEAD`, or any other ref for an inadmissible anchor — a fabricated anchor would silently scope the round against a boundary no round ever completed at.

⛔ **The outcome test is what makes the SHA an anchor rather than a timestamp.** An anchor asserts *everything up to here has been reviewed*, and only a round that actually ran the review can assert it. Branch C records `failed` after the surfacer aborted on an infrastructure error — carrying a HEAD whenever one could be resolved, for the reasons stated there — so that round examined nothing; `phase_steps` keeps one record per step, so the `failed` write also REPLACES the last reviewing round's anchor. Reading `head_at_completion` without the outcome test therefore hands the next round a `--since-ref` at which no file was ever examined — and because `failed` records are re-fired, the very next round scopes its delta past the un-reviewed fix commits, so nothing it surfaces is drawn from them. A full re-sweep is the correct fallback: it costs a round, whereas the narrowed one reviews the wrong file set.

Passing `--since-ref` narrows WHICH FILES are surfaced, never how deeply a surfaced file is reviewed: hunks are still computed against the base branch, so every surviving file is still reviewed against its full plan diff.

**Resolve the prior round's evidenced findings first (delta rounds only).** On a delta round a `{since_ref}` is present, which means a loop-back fix has landed since the previous round. Before re-surfacing, transition the prior round's Q-Gate findings whose file that fix ACTUALLY touched to `fixed`. This is the loop-back resolution the step otherwise lacks: the self-review files a finding per defect (Step 4 Branch B) but resolves none of its own, so a genuinely-landed fix used to leave the finding RECORD stuck at `pending` — the record accumulates while the code is green, which is the exact defect this step now closes. Compute the landed-fix file set from the delta the anchor defines, capturing the newline-separated paths as `{changed_paths}` and the current HEAD as `{evidence_sha}`:

```bash
git -C {worktree_path} diff --name-only {since_ref}..HEAD
```

```bash
git -C {worktree_path} rev-parse HEAD
```

Then resolve by evidence (see [manage-findings SKILL.md](../../manage-findings/SKILL.md) § "qgate resolve-evidenced"):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve-evidenced \
  --plan-id {plan_id} --phase 6-finalize \
  --changed-path {path} [--changed-path {path} ...] --evidence-sha {evidence_sha}
```

Only a finding whose `file_path` is in `{changed_paths}` is resolved `fixed`; a finding whose file the fix did NOT touch is LEFT `pending` — an unevidenced fix is never auto-resolved, because a record marked `fixed` without a landed change touching its file is strictly worse than one left `pending`. A resolution the fix did not actually earn (the file was touched but the defect survives) is self-correcting: the re-surface below re-detects the defect and `add_qgate_finding` REOPENS the record to `pending`. On a **full round** (no `{since_ref}`), skip this sub-step — there is no landed delta to evidence a resolution against, and round 1 filed no prior findings to resolve.

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

The surfacer echoes `surface_scope` (`delta` or `full`), `since_ref`, `files_in_scope`, `scope_statement`, and `structural_limit`, and computes `delta_coverage` from the round's own result, so the round variant that produced a verdict — and all three of the boundaries any claim it produces must publish (see § "Absence claims state the scope they were drawn against", § "A clean verdict carries the structural limit of the analysis", and § "A clean verdict states what the round observed") — is legible from the returned TOON without reconstructing it. A `--since-ref` that does not resolve is refused by the surfacer with `since_ref_unresolvable` — that is a helper non-zero exit and takes the halt path below; it is never silently widened into a full sweep.

**A delta round cannot close the step on its own evidence.** A delta-scoped round examined only the files that changed since the previous round, so a clean result from it is a *filter* result, not a closing verdict: it says nothing about the files it did not look at. When a delta round returns zero findings, re-run this step ONCE at full scope — repeat the surface call WITHOUT `--since-ref` and carry that full candidate set through Steps 1b–3 — and record the outcome from that full-surface pass. Only a full-surface clean pass may record `done` (see Step 4 Branch A). A delta round that DOES return findings needs no confirmation sweep: it has already found the work that sends the step round the loop again.

If the resolved implementor exits non-zero, halt and proceed to **Step 4 Branch C — helper failure**, surfacing the helper error in the `display_detail` payload. Do NOT dispatch the LLM cognitive phase below. A helper non-zero exit is an INFRASTRUCTURE failure, not a review verdict, and it must reach neither of the other two branches: Branch A would record a clean `done` for a round that never ran, and Branch B would re-fire the round loop over an error no amendment to the diff can fix.

Capture the helper's TOON output as `{candidates_toon}` for forwarding to the cognitive-phase dispatch.

**Zero-generator fallback path**: when NO discovered implementor resolves in the current executor (a consumer project shipping no domain self-review surfacer), treat the candidate set as empty — skip the LLM cognitive dispatch (Steps 1b–3) entirely and proceed directly to **Step 4 — Mark Step Complete**, recording `--outcome done` with the **not-run** verdict `"self-review not run: no surfacer implementor resolved"` (see § Dispatched-envelope output for the disjoint verdict set).

⛔ **This path performed NO analysis, and its verdict says so rather than reporting an absence of defects.** No surfacer ran, so no file was searched and no check executed; the outcome is `done` only because a consumer without a domain surfacer must not be blocked from pushing, NOT because the diff was reviewed and found clean. This is exactly why the not-run verdict is a distinct string from the nothing-to-check one: that verdict reports a surfacer that RAN — over whatever population its echoed `files_in_scope` names — and produced no candidate, whereas this one is a statement about the executor and makes no claim about the diff at all. Recording both under one string would let an un-run analysis read as a clean review — the un-run-versus-un-observed collapse this step's verdict vocabulary exists to prevent. Recording `done` on this path is what lets the promoted default step ship safely to consumers without a domain surfacer, with the un-run dimension named in the record rather than only in a log line; the outcome is `done`, but the verdict is not a clean one.

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

**Return-TOON shape invariant**: BOTH branches MUST produce the IDENTICAL return-TOON shape documented in `## Dispatched-envelope output` below (`status`, `display_detail`, `findings[N]{file,line,defect_class,rationale,cohort_size}`). The inline branch produces the same TOON-shaped result in dispatcher context — `display_detail` follows the same five-verdict rule bit-for-bit (`"self-review not run: no surfacer implementor resolved"` / `"self-review clean: surfacer ran, zero candidates surfaced"` / `"self-review clean: {N} candidates examined, no check matched"` / `"self-review clean: no observation drawn from the files searched"` / `"self-review found {K} issues in {C} classes"`), and `findings[]` carries the same entry shape, `cohort_size` included. Both branches are reached only after a surfacer HAS run, so neither may emit the not-run verdict — that one belongs to the zero-generator fallback alone. In particular the inline branch MUST pick between the clean verdicts on the same predicates the dispatch branch uses (`total_candidates == 0` for nothing-to-check, and `delta_coverage.files_with_candidates == 0` over non-zero `files_in_scope` for zero-observation); a branch that collapses any of them back to one undifferentiated clean string violates this invariant. Downstream consumers (Step 4 bookkeeping, output-template rendering) MUST NOT need to differentiate which branch produced the result. The gate is a pure dispatch-cost optimization — semantics are preserved bit-for-bit.

**The verifier arrangement is identical on both branches too.** Whichever branch produced the author's verdict, Step 3b dispatches the verifier from the inline dispatcher context and Step 4 reads the same verifier answers either way. The INLINE branch is where this matters most: there the dispatcher context is itself the author, so a verifier run inline would put author and verifier in one party and silently undo the separation § "Author and verifier are different parties" establishes. A branch that skips Step 3b, or runs its adjudication in the author's own context, breaks this invariant exactly as a branch that collapsed the verdict vocabulary would.

### Step 2: LLM cognitive phase (dispatch)

Compute the variant target via the role resolver:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize \
  --workflow plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md \
  --plan-id {plan_id} --caller plan-marshall:phase-6-finalize
```

The resolve carries the dispatch context (`--workflow`/`--plan-id`/`--caller`), so the seam emits the standardized `[DISPATCH]` work-log line and its paired decision-log record itself — see [`dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract. Do NOT hand-write a separate `[DISPATCH]` line; every firing re-runs the resolve, so the record is re-emitted per firing. This resolve passes no `--role`, so the seam emits the phase key it did resolve against (`role=phase-6-finalize`). The hand-written line this replaced claimed `role=default`, which no resolve here ever passed.

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch below.

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

The dispatched workflow body executes Step 2a (cross-reference setup) followed by Step 3 (eighteen cognitive checks).

#### Step 2a: Cross-reference setup (in-context — MUST run before any check)

Before scanning the line-level candidate lists, load the contract sources surfaced by the deterministic phase. This step is the workflow-shape fix for the failure mode where the LLM reviews each surfaced hunk in isolation and overlooks contract drift.

1. For every entry in `candidates.contract_sources`, read every path listed in the `sources` field. These are the `SKILL.md` and `standards/*.md` files governing the changed code. Read them in full — not excerpts.
2. For every entry in `candidates.schema_bearing_files`, read the file. These are nearby markdown documents that declare a fenced JSON or TOON schema; they govern the post-image of any hunk that touches the same schema.
3. Hold the loaded contract content in working memory for the rest of the cognitive phase. The eighteen checks below cross-reference hunks against this content; do not re-discover contracts on demand.

### Step 3: Apply eighteen checks (in-context)

For each non-empty candidate list, apply the corresponding cognitive check to the surfaced items only — never expand the review to candidates the helper did not surface.

#### Class-closure obligation (fix the class, not the instance)

A defect that appears once in a change almost never appears only once: the same misreading applied to one site was usually applied to its siblings in the same edit. Filing one member per round makes the step loop back once per member, and each loop-back round pays a full step dispatch to find the next instance of a defect already understood.

**The obligation**: when a check fires on a surfaced candidate and you record a finding whose `defect_class` is D, you MUST — before composing the findings list — re-scan every OTHER surfaced candidate **of the same candidate list** for D, and file every member you find in the SAME round.

`defect_class` is the machine-readable discriminator this sweep groups on. It is the same token Step 4 Branch B files as the finding `--title`, so no new taxonomy is introduced.

**The bound**: the sweep is bounded by the surface-only rule stated immediately above — it re-examines candidates the surfacer already surfaced and NEVER widens past them. It is a re-scan of the existing candidate set for one more discriminator, not a licence to read files the surfacer did not surface.

**Consequence of the bound, stated so it cannot be misread as a coverage claim**: because the surfaced set is round-dependent (a delta round surfaces only the files changed since the previous round — see Step 1), a delta round's class sweep reaches only the delta surface. A member of class D sitting in a file unchanged since the previous round is NOT swept during a delta round. The class is still closed as a class, because the closing **full-surface confirmation pass** (Step 1, Step 4 Branch A) runs this same sweep over the whole plan diff before the step may record `done`. That confirmation pass — not any intermediate round, and not round 1 — is what closes the class. Round 1's clean result is deliberately not treated as standing evidence for a class first discovered in a later round: the discriminator was never applied to round 1's surface.

**Every finding carries its cohort size.** Each entry in the returned `findings[]` gains a `cohort_size` field: the number of findings sharing that entry's `defect_class` in this round. A cohort of one is then distinguishable from a cohort whose remaining members were never looked for — without the field, both render as a single finding and the difference is invisible.

> **Coverage contract**: the per-candidate lens depth is governed by the coverage instruction resolved in Step 0 (`{cov_instruction}`). The surface-only rule above caps the scope to what the surfacer surfaced at every rung — never widen the candidate set past it. The thoroughness rung sets the depth: `inherit`/`T1`/`T2` → run the eighteen checks below as today (face-value per candidate); `T3`+ → additionally trace each surfaced candidate's siblings and cross-references before adjudicating it (the contract cross-references in Step 2a already supply the anchors). `inherit/inherit` reproduces today's behavior bit-for-bit. See the two-dial scope × thoroughness contract in [`../../persona-plan-marshall-agent/standards/thoroughness.md`](../../persona-plan-marshall-agent/standards/thoroughness.md) and the gather/expand/consume obligation in [`../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md`](../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md).

#### Absence claims state the scope they were drawn against

The surfacer publishes the scope this round searched on every surface — `surface_scope` (`delta` or `full`), `files_in_scope`, and the ready-to-quote `scope_statement` — INCLUDING on an empty surface, so an absence surface never arrives without the scope it was drawn against (see [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) § Output Schema). A **delta** round searches a NARROWER file set than a full round, so any claim of ABSENCE the review makes from a round is true only within `files_in_scope`. Two producers of absence claims are bound by this rule:

- **A finding's rationale.** When a check's rationale asserts an ABSENCE — a literal appears in no file, a symbol has no caller, an identifier is defined nowhere — it MUST state the searched scope and file count it was drawn against (quote the round's `scope_statement`), and MUST NOT phrase the claim more widely than `files_in_scope`. The observed failure this prevents: a round asserted a literal appeared in "zero test and source files" while three survivors sat in merged `main`, because the sweep was scoped to one directory tree while the CLAIM said "test and source" — the claim was wider than the scope searched. Adopt the positive shape a sibling demonstrated: **search the CLAIM, not the string** — enumerate the literals the claim names and match each against the live source symbol — and report the file set that search actually covered.

- **The clean verdict.** Each clean `display_detail` verdict that a surfacer round produces ("surfacer ran, zero candidates surfaced", "{N} candidates examined, no check matched", "no observation drawn from the files searched") is an absence claim over the surfaced candidate set, and is bound by this rule. The **not-run** verdict is not: it is a statement about the executor rather than a claim over any file set, which is precisely why it is a separate string. A DELTA round's clean result is a filter over `files_in_scope`, not a whole-surface verdict — which is why only a FULL-surface clean pass may record `done` (Step 4 Branch A), so the step's closing clean verdict is always drawn against `surface_scope: full`. The round's `scope_statement` is its own record of which of the two it is; the 80-character `display_detail` budget carries none of it (the same reason `counts.by_family` rides the return TOON rather than `display_detail`), so read the scope from the surfacer's echoed fields, never from the verdict string alone.

#### A clean verdict carries the structural limit of the analysis

The scope rule above bounds a claim by the **file set** this round searched, and widening the sweep cures it — which is exactly why a FULL-surface clean pass is what closes the step. The surfacer publishes a second boundary that widening does NOT cure, as the separate `structural_limit` field: what this analysis can never evaluate, however many files it reads.

This pass matches patterns over the diff's added lines and adjudicates the statements it finds against each other. Its reach is therefore **internal consistency between statements present in the diff** — a claim narrower than the code it describes, a sentence contradicting an instruction above it, a count restated in three places and retired in one. What it structurally cannot reach is **the behaviour of the code under inputs the diff does not contain**: a fallible three-valued observable read as a binary, a documented remedy with no reachable invocation, an observable scoped per-branch whose meaning is per-PR. Those are a different search problem, and an external reviewer routinely finds them on a diff this pass called clean.

Two obligations follow, and they bind on the CLEAN verdict above all — a clean full-surface pass is the verdict most likely to be misread as evidence the diff is sound:

- **Never render a clean pass as a reviewed diff.** "Clean: {N} candidates examined, no check matched" is a statement about the candidate set this analysis can construct, and `{N}` is a VOLUME, not a coverage number. A large `{N}` says the surface was rich, never that the diff was covered.
- **Read the limit from the surface, do not re-derive it.** `structural_limit` rides the surfacer's TOON, exactly as `scope_statement` does, and for the same reason the section above gives: the `--display-detail` budget (owned by [`../standards/external-step-contract.md`](../standards/external-step-contract.md) § "Required termination") carries neither, and the dispatched-envelope schema below has no field for either. So a consumer that needs the boundary reads it off the surfacer's output — never from the verdict string, and never by restating it in its own words, which is how it drifts into the scope claim it is not.

The asymmetry with the scope rule is deliberate and worth naming: a delta round's scope claim is **repairable** by re-running at full scope, and Step 4 Branch A requires exactly that before `done`. The structural limit is not repairable by any round, so there is nothing for the step to do about it — it is published, not discharged.

This is the self-review arm of the whole-tree honesty rule the build gate applies to its own dimensions (`_gate_coverage.structural_limits`); both exist because a narrow gate's green reads as whole-tree assurance.

#### A clean verdict states what the round observed

The two sections above bound a claim by the round's INPUTS — which files were searched, and what this analysis class can reach at all. Neither says whether the round surfaced anything over the files it did search, and that is a third, separable fact: a delta whose whole content is of a kind this pass produces no candidate for re-surfaces the previous round's candidates unchanged and returns clean. Read from `surface_scope`, `files_in_scope` and `scope_statement` alone, such a round is indistinguishable from one that looked at the same files and genuinely found nothing.

The surfacer publishes that fact as `delta_coverage`, computed from the round's own result (see [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) § `delta_coverage`). Read it off the returned TOON — never re-derive it from the candidate lists, for the same reason the section above gives for `structural_limit`.

Both obligations below presuppose a returned `delta_coverage` block, so both are scoped to a round that actually ran a surfacer. The **zero-generator fallback path** (Step 1 — no domain implementor resolves) invokes none, returns no such block, and records `done` directly with the **not-run** verdict; neither obligation applies there, and neither may be satisfied from an absent block.

Two obligations follow:

- **Report the coverage figures wherever the round's candidate count is reported.** Alongside the detector mix Step 1b already requires (`counts.by_family`), carry `delta_coverage.files_with_candidates` of `files_in_scope` and `classes_present_without_candidates` of `classes_present` from the same round. `{N}` is a VOLUME over the whole surface; the coverage figures say over how many of the round's own files the surfacer produced ANY candidate, so a rich-looking count drawn from a fraction of the scope is legible as such. ⛔ They are NOT `counts.total`'s provenance: `files_with_candidates` credits a file for a candidate on ANY surfaced list, including the review-anchor lists `counts.total` excludes, so a file can be counted here while contributing zero to `{N}`. The 80-character `display_detail` budget carries none of it, which is why the figures ride the returned TOON exactly as `counts.by_family` does.
- **A round whose `files_with_candidates` is 0 does not close the step as an ordinary clean pass.** ⚠ This branch is RARE by construction, and its rarity is not evidence of health: `contract_sources` credits a modified file on path structure alone — the nearest-ancestor `SKILL.md` walk, with no defect signal required — so any delta whose files sit under a skill directory credits every one of them and can never reach zero. Read a non-zero `files_with_candidates` accordingly; it does not by itself mean the round observed anything. When a full-surface round returns empty `findings` AND `delta_coverage.files_with_candidates == 0` over a non-zero `files_in_scope`, the round surfaced no observation of its own — its clean verdict rests on no evidence drawn from the files it searched. Record the outcome as Step 4 Branch A still prescribes (it IS a clean full-surface pass, and no further round would improve it) — but record it under the **zero-observation** verdict `"self-review clean: no observation drawn from the files searched"` rather than whichever verdict the counts alone would select, and log the observation as a deviation as well, quoting `delta_coverage.statement` verbatim. The verdict substitution is what makes the deviation survive: the WARNING below reaches the work log, which no consumer of the step record reads, so a dimension recorded only there is un-observed AND invisible. Both are emitted; neither replaces the other.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level WARNING \
  --message "(plan-marshall:phase-6-finalize:pre-submission-self-review) Zero-observation clean pass — {delta_coverage.statement}"
```

⛔ A zero `files_with_candidates` for a content class is NOT a verdict that the class is sound, and NOT proof that no detector covers it — a covered class legitimately surfaces nothing when there is nothing to surface. State only what the round supports: it produced no candidate over those files. Do not upgrade that into either a soundness claim or a detector-gap claim.

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

4. **Duplication scan** — for each `markdown_sections` entry, compare the new/edited section's contract against its sibling sections (provided in the `siblings` field) within the same file. Two sections that describe the same check, table, or rule with subtly different wording are a defect — operators do not know which to follow. Record finding `{file, heading, defect_class: duplicate_prose, rationale: <which sibling overlaps and where they diverge>}`. This scan is also the consumer of the surfaced `keep_markers` list and its derived `protected_identifiers` set: a consolidation that drops an identifier the surfacer flagged as protected (a `keep_markers` entry mirrored into `protected_identifiers`, or one already carrying `kind: keep_violation`) is refused as a `duplicate_prose` defect naming the dropped token — the refusal set the keep-marker contract exists to enforce.

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

11. **Stale-count-prose check** — for each `count_prose` entry, the helper has surfaced a count phrase (a digit or number word adjacent to a cardinality noun) in a contract source (`SKILL.md` or a `standards/*.md`) of a modified file's skill directory. Re-count the referent the prose claims — the number of operations, fields, steps, rules, commands, or checks the prose enumerates — against the actual count in the post-image of the change. When the diff changed the count (added or removed an item) but the prose number was not updated, the prose is stale. Defect → record finding `{file, line, defect_class: stale_count_prose, rationale: <the prose number, the actual post-image count, and what the diff changed>}` — but ONLY after the **Present-state grounding precondition** above confirms the mismatch survives in the CURRENT worktree file state (re-read the prose line and the relevant sections of the live document with the `Read` tool to re-count its referent; when the current file already carries the corrected number, record NO finding). When the surfaced number still matches the actual count, record no finding.

12. **Touched-claim whole-line re-check** — for each `touched_claims` entry, the helper has surfaced the `+` line of a near-identical hunk pair that differs from its `-` predecessor by exactly one token. The single-token swap is the obvious edit; the risk is that the REST of the line still carries a claim that the swap invalidated. Read the surfaced `+` line and verify every OTHER claim it makes (a count, a name, a reference, a condition) is still correct after the swap — not just the swapped token. When a surviving claim on the line is now wrong because of the swap, it is a defect. Defect → record finding `{file, line, defect_class: touched_claim_unverified, rationale: <the swapped token, and the surviving claim on the line that the swap invalidated>}` — but ONLY after the **Present-state grounding precondition** above confirms the invalidated claim survives in the CURRENT worktree file state (re-read the surfaced line in the live document with the `Read` tool; when the current file already carries the corrected line, record NO finding). When the rest of the line remains correct, record no finding.

13. **Same-document ordinal-reference re-check** — for each `ordinal_references` entry, the helper has surfaced an added same-document ordinal reference (`item N` / `step N` / bare `(N)`, on `line`) that points into an ordered-list block the same diff touched (the referenced item's post-image line is `list_line`). Inserting, deleting, or reordering a numbered-list item renumbers every later item, but an ordinal reference elsewhere in the same document is a hard-coded position the edit does NOT update — so it silently retargets to whatever item now occupies the old ordinal, or dangles past the end of the list. Read the referenced ordered-list block in the CURRENT worktree document and confirm the item now sitting at ordinal `N` is the item the reference intends. When the ordinal now resolves to the wrong item (or past the list end), it is a defect. Defect → record finding `{file, line, defect_class: ordinal_reference_stale, rationale: <the ordinal reference, the item it now resolves to, and the item it was meant to name>}` — but ONLY after the **Present-state grounding precondition** above confirms the mis-resolution survives in the CURRENT worktree file state (re-read both the reference line and the referenced list in the live document with the `Read` tool; when the current file already re-points the reference, or it was rephrased to a content anchor, record NO finding). Prefer recommending a content-anchored rephrase ("see the X step") over a renumbered ordinal so a future renumber cannot re-strand it. When the ordinal still resolves to its intended item, record no finding.

14. **Unreachable-guard check (scan-derived key)** — for each `scan_derived_keys` entry, the helper has surfaced a function (`name`) that decomposes a value into `sequence` and then selects a key by first-match of a compiled pattern over that sequence (the scan loop is on `line`), instead of indexing the decomposition at a position anchored on a known root. Every input whose out-of-domain leading segments happen to match collapses to the SAME key, so a downstream guard fed by that key can never observe a difference — its refusal path is unreachable while its tests stay green, because the tests only ever supply inputs whose first match is the intended one. Read the deriving function and its callers in context and decide whether the collapse is real: does an input the caller can actually receive carry an out-of-domain leading match, and does some downstream branch treat the derived value as an identity (grouping, cardinality, or equality)? The `key_consumed` flag narrows this — `true` means the surfaced diff already contains such an identity consumer, `false` means none was visible in the diff and the caller must be located before adjudicating (it does NOT mean the candidate is benign). Defect → record finding `{file, line, defect_class: unreachable_guard, rationale: <the scanned sequence, the input that collapses to the wrong key, and the guard whose refusal path becomes unreachable>}` — but ONLY after the **Present-state grounding precondition** above confirms the scanning derivation survives in the CURRENT worktree file state (re-read the deriving function in the live document with the `Read` tool; when the live code already anchors the decomposition at a fixed position relative to a known root, record NO finding). Prefer recommending the anchored form (relativize against the known root, then index a fixed position) over widening the pattern, which only moves the collapse. When the sequence is bounded and every element is in-domain by construction, record no finding.

15. **Worked-example clause-mismatch check** — for each `worked_example_pairs` entry, the helper has surfaced a clause section (`clause`) whose GOOD worked example (its marker is on `line`) branches on `example_predicate` while the clause's own normative prose requires `required_predicate`. **The surfacer emits ONLY the disagreeing case** — every surfaced entry carries `agrees: false`, and a pair whose predicates agree, whose clause names no normative predicate, or whose GOOD example branches on nothing recoverable never reaches this check. So this check does not re-decide whether a pair is worth looking at; it decides whether the surfaced disagreement is a real contradiction.

    Read the clause's normative statement and its GOOD example together and adjudicate: state the concrete input on which the GOOD example produces the verdict the clause requires. When that sentence cannot be written — the example branches on a field that answers a DIFFERENT question than the clause's rule, so a reader following the example would reproduce the shape the clause forbids — the worked contrast contradicts its own clause. The token-level disagreement the surfacer found is evidence, not the verdict: a clause and its example can legitimately use different vocabulary for the same predicate, and that case is a false positive to be dismissed rather than filed.

    Defect → record finding `{file, line, defect_class: worked_example_clause_mismatch, rationale: <the predicate the clause requires, the predicate the example branches on, and the concrete input on which they diverge>}` — but ONLY after the **Present-state grounding precondition** above confirms the mismatch survives in the CURRENT worktree file state (re-read the whole clause section in the live document with the `Read` tool; when the live example already branches on the required predicate, record NO finding). Prefer recommending a correction to the EXAMPLE over a weakening of the clause: the clause is the normative statement, and an example that disagrees with it is the thing that is wrong.

16. **Duplicate-claimable-key check** — for each `duplicate_claimable_keys` entry, the helper has surfaced an insertion site (`line`, into the freshly-initialized `collection`, via `form` = `append`/`subscript`) that claims a caller-supplied identity (`key`) into a new keyed collection while validating the identity but omitting any duplicate-key disposition. Read the insertion site and the surrounding function in context and decide whether the missing dedup is a real defect: does the collection use the claimed identity AS an identity — a keyed map, a producer/resolver registry, a uniqueness set — such that two inputs answering the same `key` collapse into a single entry and one silently wins? That collapse is the provenance archetype the pinned pre-fix `discover_derivation_resolvers()` (finding `8da924`) exhibited: a resolver id appended behind a bare falsiness check with no dedup, so two resolvers answering one id became one producer identity. Defect → record finding `{file, line, defect_class: duplicate_claimable_key, rationale: <the collection, the claimed identity, and the two inputs that collapse to one entry, plus the disposition the insertion should carry>}`. When the collection genuinely tolerates duplicates — an ordinary accumulator that never treats the value as a unique identity — record no finding.

17. **Discard-without-report check** — for each `discard_without_report` entry, the helper has surfaced a bare `if`-guarded `continue`/`break` (`discard`, on `line`) that drops an item inside a function owning a suppression report channel (`channel`) without recording the drop. Read the discard branch and the channel in context and decide whether the silent drop is a real defect: a function that can report `status: ok` with an empty `channel` while having discarded candidates on that branch is a vacuous confident zero — a suppression that is never reported. That is the shape the pinned pre-fix `merge_resolver_edges()` (finding `3e04a8`) exhibited: three `continue` branches dropped self-edges and unknown endpoints without appending to `notes`, so a resolver whose every candidate the merge discarded reported ok, zero edges, and empty notes. Defect → record finding `{file, line, defect_class: discard_without_report, rationale: <the channel, the discard branch, and the suppressed item that goes unreported>}`. When the drop is genuinely not a suppression the caller needs to know about — a routine loop skip the channel is not meant to record — record no finding.

18. **Hoisted-binding-shadow check** — for each `hoisted_binding_shadows` entry, the helper has surfaced an added binding (`line`) that rebinds a name the file imports at top level (`shadowed`). Read the binding site and the import in context and decide whether the shadow is a real defect: does the rebinding hide the imported binding on a path where later code still expects the import — a loop variable or assignment that shadows a module import used elsewhere in the same scope? Defect → record finding `{file, line, defect_class: hoisted_binding_shadow, rationale: <the shadowed import, the rebinding site, and the later use that observes the shadow instead of the import>}`. When the shadow is intentional and locally scoped — the import is unused past the rebinding or the rebinding is confined where the import is not read — record no finding.

### Dispatched-envelope output (returned from Steps 2–3 to Step 4)

```toon
status: success | error
display_detail: "<≤80 char ASCII summary>"
findings[N]{file,line,defect_class,rationale,cohort_size}:
  - ...
```

`cohort_size` is the number of findings in this round sharing that entry's `defect_class` (see § Class-closure obligation). Every entry carries it, including a genuine cohort of one — an omitted field would be indistinguishable from a cohort whose other members were never looked for.

`status: success` regardless of findings count — the workflow itself succeeds at producing the structural-review verdict; the caller's manifest-step orchestration translates a non-empty `findings` list into the manifest step's `--outcome loop_back --loop-back-target 6-finalize`. An empty `findings` list does NOT by itself select `--outcome done` — see Step 4, where the verifier's `may_close` answer is the selecting predicate.

⚠ **A findings-bearing return is a loop-back, not a failure.** This step examined its surface, filed real findings and handed control back — a PRODUCTIVE non-completion. Recording it as `failed` made every archive-wide analysis that counts failures mis-grade a thorough round as a defect, so *the more findings this gate legitimately raised, the worse its plan looked*. `loop_back` is also what makes the dispatch ledger's `returned_with_findings` stamp correct **by construction** rather than by coincidence — that stamp's documented trigger is precisely a `mark-step-done` recording `outcome: loop_back`. The contrast to keep is `pre-push-quality-gate`, which records `failed`: a red build gate RAN CLEANLY and self-assessed not-clean, which is a negative verdict rather than a productive hand-back. See [`../../manage-execution-manifest/standards/manifest-schema.md`](../../manage-execution-manifest/standards/manifest-schema.md) § "Which situation each `outcome` value means".

`display_detail` shape. A run that produced no finding has FOUR disjoint **non-finding** verdicts, only THREE of which are `clean:` verdicts — the fourth reports that no analysis ran at all, and a not-run outcome is not a clean one. [`ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) is the authority on that boundary and states it outright: the fallback's outcome is `done`; its verdict is not "clean". An undifferentiated clean string is prohibited, because "no analysis was performed", "the analysis ran and had nothing to check", "the analysis ran, checked things, and none matched" and "the analysis ran but drew no observation from the files it searched" are four different pieces of information, and an operator reading any one as another draws the wrong conclusion about review coverage. The split that matters most is the first: **an un-run analysis and an analysis that ran and observed nothing are not the same verdict**, and a single string covering both reports absence of analysis as absence of defects. Let `{N}` be the surfacer's emitted `counts.total`. Which lists that sum covers is the surfacer's contract — see [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) § Output Schema — and is deliberately not restated here:

- **No analysis performed** (the **not-run** verdict) → `"self-review not run: no surfacer implementor resolved"`. No implementor resolved in the current executor, so no surfacer ran, no file was searched, and no check ever executed. This verdict makes NO claim about the diff. Only the zero-generator fallback path (Step 1) reports it, and no other path may.
- Empty `findings` AND `{N} == 0`, from a round that **did** run a surfacer (the **nothing-to-check** verdict) → `"self-review clean: surfacer ran, zero candidates surfaced"`. The surfacer ran and produced no candidate, so no check had anything to run against. This verdict states only that — read the population it searched off the surfacer's echoed `files_in_scope` and `scope_statement`, never off the verdict string. The ext-point permits an empty live footprint, so a round reporting `files_in_scope: 0` reaches this verdict too, and nothing below catches that case: the zero-observation verdict requires a NON-ZERO `files_in_scope`. Over a non-empty scope this is a real, if weak, statement about the diff; over a zero-file scope it says only that there was nothing to search. Either way it is a statement about what the surfacer did — unlike the not-run verdict above, which is a statement about the executor.
- Empty `findings` AND `{N} > 0` (the **no-check-matched** verdict) → `"self-review clean: {N} candidates examined, no check matched"`. Candidates were surfaced and every check was applied to them without firing.
- Empty `findings` from a full-surface round whose `delta_coverage.files_with_candidates == 0` over a non-zero `files_in_scope` (the **zero-observation** verdict) → `"self-review clean: no observation drawn from the files searched"`. Supersedes whichever of the two verdicts above the counts alone would select; see § "A clean verdict states what the round observed" for why this one rides the recorded verdict rather than a WARNING alone.
- Non-empty `findings` → `"self-review found {K} issues in {C} classes"`, where `{C}` is the number of DISTINCT `defect_class` values across those `{K}` findings. The class count rides this verdict rather than a clean one because it is the widest: it renders to 45 characters at `{K}={C}=9999`, leaving 35 characters of headroom against the 80-character budget, whereas the no-check-matched verdict already spends 61 of its 80. Reporting both figures is what makes a round of nine findings in one class legible as one swept cohort rather than as nine unrelated defects.

All five are ≤80-char ASCII with no trailing period, and no verdict is a prefix of another — so a consumer matching a whole verdict string can never mistake one verdict for another. The not-run verdict diverges from every other at its second word (`not` vs `clean` / `found`); the three `clean:` verdicts diverge at the word after the colon (`surfacer` / a digit / `no`). Neither of the two verdicts added by the un-run-versus-un-observed split contains the substring `found`, which is the marker the clean-vs-findings split keys on.

### Step 3b: Independent verification (dispatch)

Runs in the inline dispatcher context after the author's return (Steps 2–3, or the Step 1b inline branch) and BEFORE Step 4 records anything. This is the second dispatch — the one that gives the round a reader who did not write what it is reading. It fires on every round a surfacer ran, on both author branches alike.

⛔ **Two paths do not reach this step, and neither may manufacture an acceptance.** The **zero-generator fallback** (Step 1 — no domain implementor resolved) ran no surfacer, so there is no author verdict for a verifier to accept or refuse; it records `done` with the **not-run** verdict directly, exactly as Step 1 and Step 4 already prescribe. **Branch C** (helper failure) produced no verdict either. Reading an absent verifier return as an acceptance on either path would be the same un-run-read-as-reviewed collapse the verdict vocabulary exists to prevent.

Compute the variant target via the role resolver, exactly as Step 2 does:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize \
  --workflow plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md \
  --plan-id {plan_id} --caller plan-marshall:phase-6-finalize
```

The resolve carries the dispatch context, so the seam emits the `[DISPATCH]` work-log line and its paired decision-log record for THIS firing — a record separate from Step 2's, which is how the two dispatches stay separately auditable. Do NOT hand-write a `[DISPATCH]` line. Extract the `target` field and use it as `{target}` below.

The verifier carries `instructions` rather than `workflow`: its whole task is the adjudication written inline below, and it reads no file the author did not already name, so there is no second workflow document for it to load. That choice also leaves this step's step-specific prompt-body surface unchanged — `candidates` remains the ONE field declared in `requires_prompt_fields`, because every field the verifier block carries is a generic contract field:

```text
Task: plan-marshall:{target}
  prompt: |
    name: pre-submission-self-review-verifier
    plan_id: {plan_id}
    skills: []
    instructions: |
      You are the VERIFIER for one round of the pre-submission structural self-review.
      You did not author the verdict below, and you must not re-author it: file no
      finding, edit no file, and apply no check of your own.

      The author examined {N} surfaced candidate(s) over {files_in_scope} file(s) at
      surface_scope {surface_scope} and returned this verdict:

        verdict: {display_detail_from_author}
        findings: {findings_count} finding(s) in {classes_count} class(es)
        findings_detail: {findings_rendered}

      The round's own published boundaries, quoted from the surfacer:

        scope_statement: {scope_statement}
        structural_limit: {structural_limit}
        delta_coverage: {delta_coverage_statement}

      Decide TWO questions, in this order.

      (1) Is that verdict supported by what the round actually did?
      ACCEPT when the verdict states no more than the round's scope, boundaries and
      findings support. REFUSE when it claims more than they support - an absence
      phrased wider than the file set searched, a closing verdict drawn from a
      delta-scoped round, a clean verdict that reads as a reviewed diff where the
      structural limit says this analysis class could not reach the question, or a
      findings list whose cohort sizes report a class nobody swept.

      (2) THE STOP QUESTION - may this round record done, closing the review?
      Answer yes ONLY when you accepted the verdict in (1) AND the round returned
      no finding AND nothing you were given suggests a further round would find
      something this one did not look for. Answer no otherwise, and say which of
      the three it was. A round that returned findings is always no: the findings
      are the work the next round exists to do.

      You are being asked this because the author must not answer it about its own
      verdict. Answer it on what you were given, and do not soften a no because a
      further round costs something - the cost of one more round is not evidence
      that the last one was complete.

      Return exactly this TOON and nothing else:

        status: success
        acceptance: accepted | refused
        may_close: yes | no
        rationale: "<one line, <=200 chars, naming what you checked and what decided it>"
    WORKTREE: {worktree_path}
```

The verifier's return is NOT a step verdict and carries no `display_detail`: the author's verdict string is the one that reaches the step record, and a second verdict vocabulary would be a second thing to keep in step with the first. `acceptance`, `may_close` and the one-line `rationale` that makes both auditable are the whole of its output.

**The stop question is the verifier's, and the author records the answer.** Branch A used to be selected by the bare predicate *the findings list is empty* — the author's own reading of the list it had just produced, so the party that wrote the verdict also decided the review could stop. `may_close` moves that decision to the party that did not write it. The author still composes the verdict string and still performs the bookkeeping; what it no longer does is decide that the round is over.

⛔ **`may_close` is an ADDITIONAL gate, never a substitute for the preconditions Step 4 already carries.** A `yes` does not release Branch A from the full-surface requirement, from the zero-observation verdict substitution, or from `--force` on a terminal write that lands on a differing stored outcome. All of them bind together, and a `yes` obtained over a delta-scoped round still does not close — the verifier answers the stop question, it does not waive the round's own contract. The two answers are also not interchangeable: `acceptance` judges the verdict's *wording* against the round, `may_close` judges whether *another round is owed*, and a verdict can be accurately worded about a round that should still be followed by another.

Record both answers on the decision log before Step 4 branches, so the separation is legible in the run record rather than only in the control flow:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message "(plan-marshall:phase-6-finalize:pre-submission-self-review) Verifier {acceptance} the author's verdict and answered the stop question may_close={may_close} — {rationale}"
```

**On `acceptance: accepted` AND `may_close: yes`** the round proceeds to Step 4 Branch A on the author's own verdict string, with both answers recorded above. Neither answer rewrites a verdict string — they are the preconditions Branch A carries, not a second opinion layered over the first.

**On `acceptance: accepted` AND `may_close: no`** the verdict was accurately worded and the review is nonetheless not over. The round does NOT close: route to **Step 4 Branch B** exactly as a refusal does, with the `rationale` naming what a further round is owed for. ⛔ Do NOT fold this into an acceptance on the grounds that the verdict was accepted — that reads question (1)'s answer as question (2)'s, which is the collapse the two fields exist to prevent.

**On `acceptance: refused`** the round does NOT close. The party that accepts did not accept, which is exactly the state this separation exists to make reachable. Route to **Step 4 Branch B** carrying the author's findings unchanged, plus ONE additional finding recording the non-close so it reaches the finding store rather than only the log.

The same `qgate add` serves every non-closing verifier state, with `{state}` naming which one it was — `verdict_refused` for a refusal, `further_round_owed` for an `accepted` verdict the verifier answered `may_close: no` over, `verifier_unavailable` for a dispatch that failed or returned nothing. One call, three state names, because the finding's job is to carry the `rationale` into the store and the state is what tells the next round which question it has to answer.

Every one of the three routes to the SAME recorded outcome:

| `{state}` | Verifier situation | Recorded outcome |
|---|---|---|
| `verdict_refused` | `acceptance: refused` | `loop_back` |
| `further_round_owed` | `acceptance: accepted` AND `may_close: no` | `loop_back` |
| `verifier_unavailable` | dispatch failed, or returned no parseable answer | `loop_back` |

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title "{state} at pre-submission-self-review" --detail "{rationale}" \
  --component pm-plugin-development:ext-self-review-plan-marshall --severity warning
```

⛔ **Every non-closing state above records `loop_back`, never `done` and never `failed`** — the table above is not aspirational, it is the whole outcome column. It is a productive non-completion of exactly the shape § "Dispatched-envelope output" describes — the round examined its surface and handed back something for the next round to act on. Recording any of the three `failed` would grade a working independence check as a broken step, which is the same mis-classification the loop-back convention above exists to prevent.

**When the verifier dispatch itself fails** — `status: error`, or no parseable return — the round has NO acceptance and NO answer to the stop question. Treat that as UNVERIFIED and route to Branch B exactly as a refusal does, with the rationale naming the dispatch failure. ⛔ Never read an absent verifier return as an acceptance, and never read it as a `may_close: yes`: an unanswered question is not a yes, and reading it as one restores the author-accepts-its-own-verdict arrangement silently, which is the fail-open this whole separation exists to close. The same holds for a return that carries one field and not the other — a partial answer answers only the question it names.

### Step 4: Mark Step Complete (inline)

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

**Branch A — the verifier answered the stop question `may_close: yes`**: read the `display_detail` returned by the workflow verbatim (the workflow computes the candidate count for the human-readable message).

⛔ **The selecting predicate is the verifier's answer, not the author's reading of its own findings list.** An empty findings list is a necessary input to that answer and no longer the branch selector: the verifier is what turns *this round found nothing* into *this review may stop*, and those are different claims — the first is about one round, the second is about whether another is owed. The zero-generator fallback is the one path that reaches `done` without an answer, and § "Step 3b" states why that is not a hole: it ran no surfacer, so there is no round for a stop question to be about and no verdict for a second party to accept.

**Conditional on a surfacer result having been produced**: when the round ran a surfacer, read the returned `delta_coverage` block before recording `done` and apply § "A clean verdict states what the round observed". A clean pass that surfaced nothing of its own still records `--outcome done`, but it does NOT record the same `display_detail` as a pass that observed something: when `delta_coverage.files_with_candidates == 0` over a non-zero `files_in_scope`, substitute the **zero-observation** verdict `"self-review clean: no observation drawn from the files searched"` for the workflow-returned string, and log the deviation as well. The outcome and every other flag on this branch are unchanged — only `--display-detail` differs. Promoting the deviation into the recorded verdict is the point: a WARNING in the work log is not read by anything that consumes the step record, so an un-observed dimension recorded only there is invisible at exactly the surface a reader trusts.

⛔ The **zero-generator fallback path** (Step 1 — no domain implementor resolves in the current executor) never invokes a surfacer, so neither a `delta_coverage` block nor a `surface_scope` echo exists on that path and there is nothing to read. It records `done` directly with the **not-run** verdict; NEITHER the read above, its verdict substitution and its WARNING deviation NOR the full-surface precondition below applies to it, and none may be manufactured from an absent block. Note the two are separate absences and carry separate verdicts: this path has no `delta_coverage` because no surfacer ran at all (not-run), whereas the zero-observation path has a `delta_coverage` reporting zero (a surfacer ran and observed nothing). Do not route this path to the zero-observation verdict on the grounds that both "saw nothing" — one performed no analysis and the other performed analysis that yielded nothing, and the whole point of the split is that those are different records. Requiring either unconditionally made this branch unsatisfiable — the instruction named an input the path structurally cannot produce, and the precondition's remedy prescribed re-running a surfacer that never ran. Both obligations are carved out here, in one statement, so the two cannot drift apart.

**Precondition — the clean result MUST come from a full-surface pass.** Before recording `done`, confirm the returned verdict was produced by a run that carried NO `--since-ref` (the surfacer echoes `surface_scope: full`). A `done` recorded off a delta-scoped clean result would close the step on evidence covering only the files that changed since the previous round. When the clean result came from a delta round, do NOT record `done` here — go back to Step 1, re-run the surface call at full scope, and record the outcome from that pass instead.

**Precondition — the verdict MUST carry the verifier's acceptance AND its stop answer.** Branch A is where the round closes, so it closes on a verdict a party other than its author accepted, and on that same party's answer to the stop question (§ "Author and verifier are different parties", § "Step 3b"). Before recording `done`, confirm Step 3b returned BOTH `acceptance: accepted` and `may_close: yes` for THIS round. Each of a refusal, an `accepted` paired with `may_close: no`, an errored verifier dispatch, and no verifier return at all fails this precondition on its own — every one of them routes to Branch B per Step 3b rather than recording `done`. The preconditions on this branch are independent and ALL bind: a full-surface clean pass the verifier refused does not close, an accepted delta-scoped result does not close, and an accepted full-surface result the verifier answered `may_close: no` over does not close either. ⛔ The **zero-generator fallback path** is carved out of this precondition exactly as it is carved out of the two above — no surfacer ran, so Step 3b never fired, and there is neither an acceptance nor a stop answer to look for. Do not manufacture either from its absence.

**Stop-path confirmation gate (fail-closed).** The two legs above are not advisory prose — they are a blocking checklist evaluated immediately before the `mark-step-done` call below, and EVERY leg binds. Read Step 3b's returned TOON for THIS round and the round's deterministic surface TOON, then apply in order:

1. `acceptance == accepted` for this round, else route to Branch B (do NOT mark `done`).
2. `may_close == yes` for this round, else route to Branch B (do NOT mark `done`).
3. The deterministic-evidence match below selects a clean verdict consistent with the surface TOON, else re-derive the verdict from the surface TOON rather than recording `done`.
4. The `--fact acceptance=… --fact may_close=…` pair on the mark call carries the SAME two values just checked — the record states the legs that admitted it, so a later reader can re-verify the close without re-running the round.

A `done` recorded without passing all four is a contract violation, not a judgement call: the confirmation lives at the recording boundary (this gate), not in the instructions that precede it. The zero-generator fallback path is carved out of every leg (no surfacer ran, Step 3b never fired) exactly as the preconditions above state.

- **Convergence signal** — Step 3b's `may_close: yes` IS the convergence judgement: the party that did not author the verdict answers that no further round is owed. A clean round the verifier answers `may_close: no` over has not converged, whatever its findings list holds, and routes to Branch B. The precondition above already requires the answer; this names what it proves.
- **Deterministic evidence** — the selected clean verdict must match the round's deterministic surface output, evaluated in THIS order (zero-observation first, because a non-empty scope that surfaces no candidates satisfies both predicates and the counts rule would mis-select it):
  1. `delta_coverage.files_with_candidates == 0` over non-zero `files_in_scope` selects zero-observation (with the deviation log) — regardless of what `counts.total` holds.
  2. Only when (1) does not match: `counts.total == 0` selects nothing-to-check; `counts.total > 0` with empty findings selects examined-clean.
  A verdict inconsistent with the evidence — examined-clean claimed over `total == 0`, or any clean verdict over an absent `counts` block — does not close; re-derive the verdict from the surface TOON rather than recording `done`. The zero-generator fallback is carved out (no surface ran; the not-run verdict carries no evidence claim).

Immediately before invoking `mark-step-done`, resolve the worktree HEAD SHA so the dispatcher can detect a stale completion record after a downstream loop-back commit advances HEAD (see § HEAD-dependency above):

```bash
git -C {worktree_path} rev-parse HEAD
```

The `{worktree_path}` value is the path resolved by `phase-6-finalize` Step 0 (Resolve Worktree and Main Checkout Paths); do NOT re-resolve it from any other cwd or shell context. Capture the stdout as `{sha}` (a 40-character hex SHA) and forward it via `--head-at-completion`.

**The `--fact acceptance=… --fact may_close=…` pair is conditional on this round having actually run Step 3b.** On every ordinary Branch A close a verifier answer exists and both flags are forwarded. On the **zero-generator fallback path** (§ "Step 4: Mark Step Complete" ⛔ note above) Step 3b never fired, so there is no acceptance and no stop answer to report — OMIT both `--fact` flags on that path rather than inventing a value or forwarding an unresolved placeholder, mirroring the `--head-at-completion` omission rule Branch C already applies when `{sha}` cannot be resolved.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome done \
  --display-detail "{display_detail_from_workflow}" \
  --fact acceptance={acceptance} --fact may_close={may_close} --fact work_performed=true \
  --head-at-completion {sha} \
  --force
```

On the zero-generator fallback path, omit `acceptance`/`may_close` (Step 3b never fired) and record `work_performed=false` — this `done` closes without the step having examined any file:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome done \
  --display-detail "self-review not run: no surfacer implementor resolved" \
  --fact work_performed=false \
  --head-at-completion {sha} \
  --force
```

**`--force` is REQUIRED whenever the outcome about to be written DIFFERS from the live record's, in BOTH directions.** `mark-step-done` refuses to overwrite a live record with a *differing* outcome — and only a differing one; a same-outcome overwrite lands without the flag. The multi-round shape this step is built around produces that refusal on each terminal branch, not only on the closing one:

- **`loop_back` → `done`** (Branch A): round 1 files findings and records `--outcome loop_back`, the findings are fixed, and the converged round records `done` over that live `loop_back` record. This is the state Branch A is *most often* reached from — the clean round that closes a loop-back is the whole point of re-firing this step.
- **`done` → `loop_back`** (Branch B): a round records `done`, a later settle-band step advances HEAD, § HEAD-dependency re-fires this step against the newer diff, and the re-fire finds a defect — writing `loop_back` over that live `done` record.

Both are ordinary terminal writes of the loop this document prescribes, not escape hatches for an unexpected state, and neither round can record its outcome without the flag. Omitting it returns `error: conflict`, the step records nothing, and the dispatcher's post-dispatch completion guard halts the phase reporting a missing terminal record — i.e. the round that finally came back clean is the one that cannot record itself. The trigger is therefore symmetric: add `--force` to a terminal `mark-step-done` whenever a prior round of this step recorded ANY outcome differing from the one about to be written. Branch A's forced form:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome done \
  --display-detail "{display_detail_from_workflow}" \
  --fact acceptance={acceptance} --fact may_close={may_close} --fact work_performed=true \
  --head-at-completion {sha} --force
```

⛔ **Branch B carries it for the same reason** — the mirror case is real, not hypothetical, and the "Branch B only ever re-writes `loop_back` over `loop_back`" reading is FALSE. This step is `head_dependent: true` (§ HEAD-dependency above), so the dispatcher re-fires it on any HEAD advance past the recorded `head_at_completion` — including an advance past a stored `done`. A findings-bearing round after such a re-fire runs Branch B, writes `loop_back` over that `done`, and hits the identical `error: conflict`. The governing rule is [`../standards/external-step-contract.md`](../standards/external-step-contract.md), which makes `--force` mandatory on ANY terminal branch whose write can land on a record carrying a different outcome.

The overwrite is intended and is not a loss of signal in either direction: a superseded `loop_back` record's findings are already persisted in the finding store by Branch B, a superseded `done` record's verdict was anchored to a SHA the re-fire has left behind, and `mark-step-done` returns `previous_outcome` / `previous_head_at_completion` so the transition it replaced stays legible in the return.

**Branch B — the verifier did not answer `may_close: yes`**: the round does not close. Four states reach this branch and they are not interchangeable — a findings-bearing round (the ordinary case, where `may_close` is `no` because the findings ARE the next round's work), a refused verdict, an `accepted` verdict the verifier nonetheless answered `may_close: no` over, and an unverified round whose verifier dispatch failed or returned nothing. Step 3b names which one applies and supplies the `rationale`; this branch records the same `loop_back` for all four, because the outcome enum's job is to say the round did not close, not to say why.

First persist every finding to the plan's `qgate-6-finalize.jsonl` finding store, then surface the findings in the finalize TOON output (consumed by `output-template.md`) so the operator sees `file:line` and `defect_class` per finding. On the three non-findings-bearing states the author's `findings[]` may be empty; the finding Step 3b files — `verdict_refused`, `further_round_owed`, or `verifier_unavailable` (§ "Step 3b") — is then the one this branch persists, and the loop-back still carries something for the next round to act on.

For every entry in the returned `findings[N]{file,line,defect_class,rationale,cohort_size}` list, emit one `manage-findings qgate add` call. This loop runs in the inline dispatcher context (the same context as the `mark-step-done` call below). `--phase 6-finalize` and `--source qgate` are mandatory; `--type bug` is the canonical finding type for a structural self-review defect. The `--detail` body carries the entry's `cohort_size` so the loop-back fix task addresses the CLASS rather than the instance — a fix task that reads "1 of 4 in this class" is told, at the point of work, that three siblings are waiting.

The title carries the class AND the site, `{file}:{line}`, both of which the returned entry already declares — no field beyond the returned schema is interpolated. The bare `{defect_class}` form is forbidden by the finding-authoring contract owned by [`ext-self-review-plan-marshall/SKILL.md`](../../../../pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md) § Finding-authoring contract; read the reasons there rather than here, so one statement of them cannot drift from the other:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title "{defect_class} at {file}:{line}" --detail "{rationale} [defect_class {defect_class}: {cohort_size} finding(s) in this class this round]" \
  --file-path "{file}" \
  --component pm-plugin-development:ext-self-review-plan-marshall --severity warning
```

Then resolve the worktree HEAD SHA — the same call and the same `{worktree_path}` as Branch A — and record the loop-back outcome carrying it. As on Branch A, the `--fact acceptance=… --fact may_close=…` pair is conditional: forward both on the three states where Step 3b actually returned an answer (a findings-bearing round, a refusal, or an accepted-but-`may_close: no` round). On the **`verifier_unavailable`** state — the verifier dispatch itself failed or returned nothing (§ "Step 3b") — there is no acceptance and no stop answer to report; OMIT both `--fact` flags on that state, exactly as the zero-generator fallback omits them on Branch A:

```bash
git -C {worktree_path} rev-parse HEAD
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome loop_back \
  --loop-back-target 6-finalize \
  --display-detail "{display_detail_from_workflow}" \
  --fact acceptance={acceptance} --fact may_close={may_close} --fact work_performed=true \
  --head-at-completion {sha} \
  --force
```

`--loop-back-target 6-finalize` is the inline-fixable tier: the findings are addressed on this branch and the finalize step loop is re-entered, with no phase-5-execute re-dispatch. The target is not a free choice — `5-execute` is the fix-task-required tier, and these findings are amendments to the diff in hand.

Per the symmetric `--force` rule under Branch A, add `--force` to this call whenever a prior round recorded `done` — the `done` → `loop_back` direction the HEAD-dependency re-fire produces:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome loop_back \
  --loop-back-target 6-finalize \
  --display-detail "{display_detail_from_workflow}" \
  --fact acceptance={acceptance} --fact may_close={may_close} --fact work_performed=true \
  --head-at-completion {sha} --force
```

**Branch C — the deterministic helper exited non-zero** (Step 1's halt path). This is an INFRASTRUCTURE failure — `git_unavailable`, `base_branch_not_found`, `since_ref_unresolvable`, `worktree_resolution_failed` — not a review verdict, and it must not be routed into either branch above. Branch A would record a clean `done` for a round that never examined anything, and Branch B would send the round loop back over an error no amendment to the diff can fix. Record `failed`, which `external-step-contract.md` still admits and `assert-step-recorded --require-terminal` treats as terminal, and carry the helper's own error into the detail so the operator sees which of the four it was.

Resolve the worktree HEAD SHA first, exactly as Branches A and B do — `{sha}` is not in scope here otherwise, and `--head-at-completion` applies no shape validation on a non-`done` outcome, so an unresolved placeholder would persist verbatim in the record and leave no account of the HEAD the failure happened at:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture the stdout as `{sha}`, then record:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome failed \
  --display-detail "surfacer failed: {helper_error}" \
  --head-at-completion {sha} \
  --force
```

⛔ **When `rev-parse` ITSELF fails, OMIT the flag — never forward an unresolved or empty `{sha}`.** This is not a remote case: `git_unavailable` is one of the four errors that reach Branch C, and it names the same git this resolution needs, so on that arm the `rev-parse` above is expected to fail too. `--head-at-completion` is optional on `mark-step-done`, and terminality comes from the `failed` outcome rather than from the SHA, so the record without it still satisfies `assert-step-recorded --require-terminal`. Substituting a literal `{sha}` or an empty string instead would persist the exact unresolved placeholder the paragraph above exists to prevent — and would cost the audit its honesty in the same move, because a record carrying NO HEAD says the HEAD was unobtainable, while one carrying an empty string claims a HEAD was read. Name the omission's cause in the detail so the absent field is legible rather than merely missing:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:pre-submission-self-review --outcome failed \
  --display-detail "surfacer failed: {helper_error}; HEAD unresolvable" \
  --force
```

Branch A persists nothing — there are no findings to write. Branch B always forwards `--head-at-completion`; Branch C forwards it whenever the SHA resolved and omits it when it did not. The two are forwarded for different reasons, and only ONE of the two SHAs is ever read as an anchor.

- **Branch B** — the SHA carries no *re-fire* decision value (the dispatcher re-fires `loop_back` records unconditionally), but it IS the delta anchor the NEXT round reads in Step 1. A `loop_back` record written without it leaves the following round with no anchor, which silently degrades that round to a full sweep — the exact re-sweep this scoping exists to remove.
- **Branch C** — the SHA is recorded for the audit record of where the failure happened, and because an unresolved `{sha}` placeholder would otherwise persist verbatim in its place. When git cannot resolve it at all the field is omitted rather than filled, so the record distinguishes a HEAD nobody could read from a HEAD read as blank. Either way it is **NOT** an anchor: Step 1 admits an anchor only from a `done` or `loop_back` record, because a round that aborted before surfacing anything reviewed nothing and cannot assert that everything up to its HEAD was examined. See Step 1's ⛔ note for the false-green that reading it would produce.

The dispatcher's loop-back continuation hook admits the round under `loop_back_without_asking` and the `max_iterations` ceiling, so the round loop is bounded exactly as before. The operator must address every finding (amend the diff: rename, tighten regex, rewrite wording, delete duplicate section, fix contract drift), re-run the step, and only then advance to `push`.

## Round-loop termination: converged, self-seeding, and out of budget

This step re-fires per round (§ HEAD-dependency). Two shapes close it through a non-finding round at Step 4 Branch A, and they are NOT the same verdict: a **full-surface clean pass**, where a surfacer ran and found nothing, and the **zero-generator not-run close**, where no surfacer resolved so nothing was searched — it carries no surface scope to be full because it ran no surface at all, and § "A clean verdict states what the round observed" holds it apart from a clean one for exactly that reason. Both close the step; only the first is a clean pass. A third close does NOT go through Branch A at all — *out of budget*, which records `--outcome loop_back` via Branch B; the termination criterion below carries all three. Two halves of what it reviews converge at DIFFERENT rates, and the termination criterion MUST keep them distinct — collapsing them is how a spiralling loop reads as either falsely clean or as an endless defect stream.

- **The behavioural half** — findings about SHIPPED CODE (a missing test, an unguarded boundary, a producer with no consumer, an unreachable guard behind a scan-derived key). It converges under fixing: once the code defects are corrected, later rounds find fewer, and eventually a round finds none.
- **The doc-claim half** — findings about PROSE the change authors (a duplicated section, a stale count, a drifted contract statement, a description-vs-body mismatch). It does NOT converge under *correction*: resolving a doc-claim finding by AUTHORING new prose hands the next round new prose to audit. This is the standing lesson — correction breeds the next instance of the class; only DELETION converges — now observed at the level of the round loop rather than the individual claim.

**A self-seeding round.** A round is **self-seeding** when its findings are ALL doc-claim findings (defect classes that read prose or contract consistency — `duplicate_prose`, `contract_drift`, `stale_count_prose`, `description_body_drift`, `same_document_contradiction`, `touched_claim_unverified`, `ordinal_reference_stale`, `worked_example_clause_mismatch`) located within the round's **delta scope** — the files THIS PLAN'S OWN prior rounds changed since the previous round's anchor (`surface_scope: delta`, the `files_in_scope` the round's `scope_statement` names — see § "Absence claims state the scope they were drawn against" and Step 1). A finding there is the review auditing prose the previous round's own fix just wrote; publishing the searched scope is exactly what makes a self-seeded round *identifiable* rather than indistinguishable from a fresh defect. **The delta anchor establishes candidacy, not authorship**: `--since-ref` names the paths changed since the previous round's `head_at_completion`, which in the ordinary loop are exactly the loop-back fix's own edits — but a round that also absorbed the base branch (a mid-loop merge) carries base-authored paths in that same delta. So before routing a finding to a self-seeding close, confirm the flagged prose is THIS PLAN'S OWN prior-round correction (authored by a loop-back fix on this branch), not content the branch absorbed from base; a finding on absorbed base prose is an ordinary finding, not a self-seeded one. A self-seeding round is **reported as self-seeding** — recorded as such in the round's outcome, not counted as an ordinary non-clean round. An ordinary non-clean round prescribes another correct-and-re-run cycle, which is precisely the cycle that re-seeds; naming the round self-seeding is what stops it being fed back into that cycle.

**Resolve a self-seeding finding by deletion, not correction.** The convergent action on a self-seeding finding is to DELETE the over-claiming prose — the stale count, the duplicated section, the claim phrased wider than the code — rather than rewrite it. Rewriting authors the next round's finding; deletion ends the class. This is the only resolution that lets the doc-claim half reach a clean pass, and it is the same lesson the round-loop level inherits from the individual claim.

**How this is recorded — no new outcome, an existing channel.** A self-seeding round introduces NO outcome of its own: it still has findings, so it records `--outcome loop_back` through Step 4 Branch B exactly as any non-clean round does, and the dispatcher re-fires it. The difference is entirely in RESOLUTION and REPORTING, not in the outcome enum. Resolution is deletion (above), so the re-fired round converges instead of re-seeding. Reporting is a `manage-logging decision --level WARNING` naming the round self-seeding — the same deviation-logging channel this step already uses for its gate decisions (Step 1b) — so the classification is an auditable record rather than merely narrative, and an *out of budget* close (below) is a distinct WARNING from a *converged* one. "Reported as self-seeding rather than counted as an ordinary non-clean round" is therefore precise: the round's loop-back record is unchanged, but its findings are deleted (not corrected) and its nature is logged, so it is neither mistaken for clean nor fed back into the correct-and-re-run cycle that spirals.

**The termination criterion — converged, not-run, and out of budget.** These are DIFFERENT closes and a later reader MUST NOT collapse them. The not-run close is the zero-generator path named in the section opening; it is listed here so the criterion covers every close this step can reach rather than only the two that involve a surfacer:

- **Converged** — the step closed on a clean pass (Step 4 Branch A): every counted candidate examined, no check matched, over `surface_scope: full` on a round a surfacer ran, AND the verifier answered the stop question `may_close: yes` over that round. The doc-claim half reached a fixpoint by deletion and the behavioural half found nothing — and a party other than the author agreed that no further round was owed, which is what makes *converged* a verdict rather than the author's own decision to stop.
- **Not run** — the zero-generator close: no surfacer implementor resolved, so no file was searched and no check executed. It closes the step, and it is not a clean pass — see § "A clean verdict states what the round observed".
- **Out of budget** — the loop stopped while the doc-claim half was still non-converged: a self-seeding spiral kept alive by correction-instead-of-deletion, or a round/token ceiling reached, closing on a recorded WARNING DEVIATION rather than a clean pass. This is NOT a converged close and MUST NOT be reported as one. A warning-deviation close is *out of budget*; a clean pass is *converged*.

The cap is on **convergence, not on budget**. The remedy for a spiralling doc-claim half is to recognize it as self-seeding and resolve it by deletion so it converges — NEVER to reduce the number of rounds. Rounds late in a loop have caught structurally unreachable guards on an otherwise-green suite, so the willingness to run a round is never the target; the scope of a round, and how its findings are resolved, is.

## Worked example: the lesson that drove this workflow

Both defect classes were missed in the dogfood run that drove this workflow's introduction; the LLM pass was reviewing surfaced hunks one at a time without consulting the contracts that lived in the same diff:

- **Missing schema field**: a helper emitted `markdown_sections[N]{file,heading,siblings}` while the consumer's documented schema declared `markdown_sections[N]{file,line,heading,siblings}` (the `line` field anchors findings). Cross-checking the emitted dict against the schema declared in the same change set catches the omission.
- **Loosened detection heuristic**: a CI-provider detection routine matched on a substring (`'github' in url`) where the contract section documented a structured project marker (`.github/workflows/*.yml`). Cross-checking the new heuristic against the documented marker catches the over-broad match before it produces false positives in production.

The Step 2a cross-reference setup plus Step 3 check 5 close that gap.
