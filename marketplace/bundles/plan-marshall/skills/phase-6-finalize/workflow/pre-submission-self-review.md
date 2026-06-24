---
name: default:pre-submission-self-review
description: Pre-submission structural self-review (symmetric pairs, regex over-fit, wording, duplication, contract drift, producer-without-consumer, source-of-truth drift, same-document contradiction, description-vs-body drift, unguarded boundary, stale count-prose, touched-claim re-check, ordinal-reference re-check) before push
order: 7
mutates_source: false
default_on: false
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

The step combines a deterministic helper that surfaces concrete candidates from the staged diff (Step 1 below) with an LLM cognitive review applied only to those candidates (Steps 2–3 below). Step 1 (deterministic surface) and Step 4 (outcome bookkeeping) run inline in the manifest dispatcher's context; Steps 2–3 (contract cross-reference setup + the thirteen LLM cognitive checks) run in the dispatched envelope under `--phase phase-6-finalize` (no `--role` — pre-submission-self-review tracks `phase-6-finalize.default`). On any finding the LLM returns, the step hard-fails and halts the phase, mirroring the gating-step convention established by `pre-push-quality-gate`.

This document carries NO step-activation logic. Activation is controlled by the manifest composer in `manage-execution-manifest/scripts/manage-execution-manifest.py` via the `pre_submission_self_review_inactive` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`). The composer drops the step when `commit_and_push == false` (transitively, via `commit_push_disabled`) OR the plan's live footprint is empty. When the dispatcher runs this step the executor always runs to completion: a clean run records `outcome=done`; a non-empty findings list records `outcome=failed` and halts the phase.

## Domain-Aware Candidate Surfacing

The deterministic surfacer is pluggable via the `ext-self-review-{domain}` extension point — see [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) for the contract. Each implementor exposes a `surface --plan-id {plan_id}` script that emits the eighteen candidate sub-lists below as TOON. The plan-marshall-domain implementor is the `ext-self-review-plan-marshall` skill, homed in the `pm-plugin-development` bundle; its script notation is `pm-plugin-development:ext-self-review-plan-marshall:self_review`. Step 1 calls this implementor directly — the plan-marshall surfacer notation is the single canonical implementor, so no `get-extensions` registration lookup is needed.

## Inputs (inline step — Step 1)

- The change footprint — the deterministic helper derives it live from the worktree (the union of the `{base}...HEAD` diff and the porcelain working-tree state), not from any persisted ledger.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). The deterministic helper invocation MUST identify the worktree via `--plan-id {plan_id}` alone (preferred — the implementor auto-resolves the worktree path through `manage-status get-worktree-path`) or by additionally supplying `--project-dir {worktree_path}` as an explicit override. The footprint and diff are computed against the worktree's base branch.

## Inputs (dispatched envelope — Steps 2–3)

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier. |
| `WORKTREE` | Yes | Repo-relative working-directory path. |
| `candidates` | Yes | TOON envelope from the resolved `ext-self-review-{domain}` surface helper — carries the eighteen candidate sub-lists below. The orchestrator runs the surface helper in Step 1 and forwards its output verbatim; the workflow body does NOT re-invoke the surface helper. |

| `candidates` sub-list | Schema | Purpose |
|-----------------------|--------|---------|
| `regexes[N]{file,line,pattern}` | Added regex literals and fnmatch globs in `.py`/`.md` hunks | Boundary check for regex over-fit |
| `user_facing_strings[N]{file,line,context,text}` | Added strings in skill prose, error messages, CLI help | Wording disambiguation |
| `markdown_sections[N]{file,line,heading,siblings}` | Added/edited markdown sections per file with sibling-section list | Duplication scanning |
| `symmetric_pairs[N]{file,line,name,partner}` | Functions whose names match save/load, init/restore, push/pop, acquire/release, open/close, start/stop pairings | Symmetric pair test-coverage check |
| `flag_guard_pairs[N]{file,line,flag,forms_covered}` | Argument-presence guards over a `--flag` token, with the flag forms each guard covers (`space` / `equals` / `both`) | Flag-form-coverage comparison (part of check #1) |
| `contract_sources[N]{file,sources}` | Per modified file: nearby `SKILL.md` and `standards/*.md` paths | Contract cross-reference anchor |
| `schema_bearing_files[N]{file,format}` | Markdown files within the contract radius whose content contains a fenced JSON or TOON block | Contract drift detection |
| `advertised_form_help_strings[N]{file,line,arg,help_text,raw_pass_line}` | argparse `help=` strings advertising more than one accepted input form paired with a raw `args.<dest>` pass-through that does no normalization | Advertised-form drift (sub-check of check #5) |
| `keep_markers[N]{file,line,identifier,kind}` + `protected_identifiers[M]` | `<!-- self-review: keep <id> -->` markers in the post-image; the top-level `protected_identifiers` set mirrors the identifier values for fast membership checks | Duplication scan refuses to drop any protected identifier |
| `producer_consumer[N]{file,line,key,consumed}` | Produced output-dict keys (`output['key'] = ...`) with no consumer (`foo['key']` / `.get('key')`) anywhere in the diff | Dangling-producer check (check #6) |
| `source_of_truth[N]{name,files,values}` | UPPER_SNAKE_CASE constants assigned divergent literals across two diff files | Source-of-truth drift check (check #7) |
| `same_document_consistency[N]{file,line,keyword,text}` | Added `.md` normative directives (MUST/NEVER/etc.) for sibling-contradiction review | Same-document consistency check (check #8) |
| `description_vs_body[N]{file,line,key,description}` | Modified `.md` files carrying a frontmatter `description`/`summary` whose body the diff also changed | Description-vs-body consistency check (check #9) |
| `unguarded_boundaries[N]{file,line,boundary,guarded}` | Added `subprocess.*` / file-I/O calls with no `check=True` and no enclosing `try/except` in the same function | Lone-unguarded-boundary check (check #10) |
| `count_prose[N]{file,line,text}` | Count-prose (a digit or number word adjacent to a cardinality noun) in every `SKILL.md` of a modified file's skill directory | Stale-count-prose re-check (check #11) |
| `touched_claims[N]{file,line,text}` | The `+` line of a `-`/`+` hunk pair differing by exactly one token | Touched-claim whole-line re-check (check #12) |
| `ordinal_references[N]{file,line,text,list_line}` | Added same-document ordinal references (`item N` / `step N` / bare `(N)`) pointing into an ordered-list block the same diff touched; `list_line` is the post-image line of the referenced item | Same-document ordinal-reference re-check (check #13) |

Skills the caller MUST forward in `skills[]`: none (the workflow reads files with the `Read` tool and emits no script calls).

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

Invoke the plan-marshall-domain surfacer's `surface` subcommand directly. The implementor derives the plan footprint live from the worktree (`{base}...HEAD` ∪ porcelain), computes the staged diff against the worktree's base branch, and emits the eighteen candidate sub-lists in a single TOON document on stdout.

The implementor notation is fixed — `pm-plugin-development:ext-self-review-plan-marshall:self_review` — so it is called directly with no registration lookup. Forward `--contract-radius {N}` derived from `{cov_scope}` (`change-set` → `1`; `artifact`/`inherit` → `3`; `component`/`module`/`overall` → `5`):

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-self-review-plan-marshall:self_review \
  surface --plan-id {plan_id} --contract-radius {N}
```

(Auto-resolves the worktree from `--plan-id`. Add `--project-dir {worktree_path}` only when the explicit override is required. The `inherit`/default radius of `3` reproduces today's surfacer breadth.)

If the helper exits non-zero, halt and proceed to **Step 4 — Mark Step Complete (Failure)**, surfacing the helper error in the `display_detail` payload. Do NOT dispatch the LLM cognitive phase below.

Capture the helper's TOON output as `{candidates_toon}` for forwarding to the cognitive-phase dispatch.

### Step 1b: Candidate-count gate (inline vs dispatch) — B5

Parse the candidate sub-lists from `{candidates_toon}` and read `total_candidates` from the surfacer's `counts.total` field, which sums the thirteen line-level heuristic lists (`regexes`, `user_facing_strings`, `markdown_sections`, `symmetric_pairs`, `flag_guard_pairs`, `keep_markers`, `producer_consumer`, `source_of_truth`, `same_document_consistency`, `description_vs_body`, `unguarded_boundaries`, `touched_claims`, `ordinal_references`). The review-anchor lists (`contract_sources`, `schema_bearing_files`, `count_prose`, `advertised_form_help_strings`) and the derived `protected_identifiers` index are excluded from `total_candidates` for the same reason they are excluded from `counts.total` (see the surfacing skill's § Output note).

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

**Return-TOON shape invariant**: BOTH branches MUST produce the IDENTICAL return-TOON shape documented in `## Dispatched-envelope output` below (`status`, `display_detail`, `findings[N]{file,line,defect_class,rationale}`). The inline branch produces the same TOON-shaped result in dispatcher context — `display_detail` follows the same `"self-review clean: {N} candidates examined"` / `"self-review found {K} issues"` rule, and `findings[]` carries the same entry shape. Downstream consumers (Step 4 bookkeeping, output-template rendering) MUST NOT need to differentiate which branch produced the result. The gate is a pure dispatch-cost optimization — semantics are preserved bit-for-bit.

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

```
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

The dispatched workflow body executes Step 2a (cross-reference setup) followed by Step 3 (thirteen cognitive checks).

#### Step 2a: Cross-reference setup (in-context — MUST run before any check)

Before scanning the line-level candidate lists, load the contract sources surfaced by the deterministic phase. This step is the workflow-shape fix for the failure mode where the LLM reviews each surfaced hunk in isolation and overlooks contract drift.

1. For every entry in `candidates.contract_sources`, read every path listed in the `sources` field. These are the `SKILL.md` and `standards/*.md` files governing the changed code. Read them in full — not excerpts.
2. For every entry in `candidates.schema_bearing_files`, read the file. These are nearby markdown documents that declare a fenced JSON or TOON schema; they govern the post-image of any hunk that touches the same schema.
3. Hold the loaded contract content in working memory for the rest of the cognitive phase. The thirteen checks below cross-reference hunks against this content; do not re-discover contracts on demand.

### Step 3: Apply thirteen checks (in-context)

For each non-empty candidate list, apply the corresponding cognitive check to the surfaced items only — never expand the review to candidates the helper did not surface.

> **Coverage contract**: the per-candidate lens depth is governed by the coverage instruction resolved in Step 0 (`{cov_instruction}`). The surface-only rule above caps the scope to what the surfacer surfaced at every rung — never widen the candidate set past it. The thoroughness rung sets the depth: `inherit`/`T1`/`T2` → run the thirteen checks below as today (face-value per candidate); `T3`+ → additionally trace each surfaced candidate's siblings and cross-references before adjudicating it (the contract cross-references in Step 2a already supply the anchors). `inherit/inherit` reproduces today's behavior bit-for-bit. See the two-dial scope × thoroughness contract in [`../../persona-plan-marshall-agent/standards/thoroughness.md`](../../persona-plan-marshall-agent/standards/thoroughness.md) and the gather/expand/consume obligation in [`../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md`](../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md).

#### Present-state grounding precondition (gates contract_drift and its variants on confirmed absence)

The "absence-class" checks — contract drift (check 5) and its variant labels near-identical-hunk (check 12 → `touched_claim_unverified`), count-prose (check 11 → `stale_count_prose`), unguarded-boundary (check 10 → `unguarded_boundary`), and ordinal-reference (check 13 → `ordinal_reference_stale`) — adjudicate a candidate by claiming that some flagged content is *missing*, *stale*, or *drifted* relative to the current contract. Each of these checks operates on a surfaced hunk or sibling line rather than on the live file, so it can fire a false positive when the flagged content is *already present and correct in the current worktree doc state* — for example, a contract source whose schema the diff actually updated to agree with the code, a count-prose number the same change already corrected, or a touched-claim line whose surviving claims are all still accurate in the saved file. The surfaced candidate is a snapshot of the diff, not proof that the defect survives in the committed-to-disk document.

**Precondition (MUST run before recording any finding from check 5, 10, 11, 12, or 13)**: before emitting a finding whose defect class is `contract_drift`, `touched_claim_unverified`, `stale_count_prose`, `unguarded_boundary`, or `ordinal_reference_stale`, re-read the flagged content from the CURRENT worktree file state (use the `Read` tool against the file path under the pinned cwd / `WORKTREE`) and confirm the defect is genuinely present in the live document. Emit the finding ONLY when the flagged content is confirmed absent, stale, or unguarded in the current file state — i.e. the contract source still disagrees with the live code, the count-prose number still mismatches the live count, or the boundary call is still unguarded on disk. When the current file state already reflects the corrected content (the flagged drift/staleness/gap is no longer present on disk), the candidate is a stale diff-snapshot artefact — record NO finding. This grounding step is the single guard that prevents these five checks from emitting false-positive findings against content that already exists, corrected, in the file.

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

### Dispatched-envelope output (returned from Steps 2–3 to Step 4)

```toon
status: success | error
display_detail: "<≤80 char ASCII summary>"
findings[N]{file,line,defect_class,rationale}:
  - ...
```

`status: success` regardless of findings count — the workflow itself succeeds at producing the structural-review verdict; the caller's manifest-step orchestration translates a non-empty `findings` list into the manifest step's `--outcome failed` per the gating-step convention. Empty `findings` → caller marks `--outcome done`.

`display_detail` shape:
- Empty `findings` → `"self-review clean: {N} candidates examined"` where `{N}` is the surfacer's `counts.total` (the thirteen line-level heuristic lists: `regexes`, `user_facing_strings`, `markdown_sections`, `symmetric_pairs`, `flag_guard_pairs`, `keep_markers`, `producer_consumer`, `source_of_truth`, `same_document_consistency`, `description_vs_body`, `unguarded_boundaries`, `touched_claims`, `ordinal_references`).
- Non-empty `findings` → `"self-review found {K} issues"`.

### Step 4: Mark Step Complete (inline)

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

**Branch A — findings list is empty**: read the `display_detail` returned by the workflow verbatim (the workflow computes the candidate count for the human-readable message).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-pre-submission-self-review --outcome done \
  --display-detail "{display_detail_from_workflow}"
```

**Branch B — findings list is non-empty**: first persist every finding to the plan's `qgate-6-finalize.jsonl` finding store, then surface the findings in the finalize TOON output (consumed by `output-template.md`) so the operator sees `file:line` and `defect_class` per finding.

For every entry in the returned `findings[N]{file,line,defect_class,rationale}` list, emit one `manage-findings qgate add` call. This loop runs in the inline dispatcher context (the same context as the `mark-step-done` call below). `--phase 6-finalize` and `--source qgate` are mandatory; `--type bug` is the canonical finding type for a structural self-review defect:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title "{defect_class}" --detail "{rationale}" --file-path "{file}" \
  --component pm-plugin-development:ext-self-review-plan-marshall --severity warning
```

Then record the failed outcome:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step project:finalize-step-pre-submission-self-review --outcome failed \
  --display-detail "{display_detail_from_workflow}"
```

Branch A (empty findings) persists nothing — there are no findings to write.

The dispatcher's existing failure handling halts the phase on `outcome=failed`, matching the gating-step contract used by `pre-push-quality-gate`. The operator must address every finding (amend the diff: rename, tighten regex, rewrite wording, delete duplicate section, fix contract drift), re-run the step, and only then advance to `push`.

## Worked example: the lesson that drove this workflow

Both defect classes were missed in the dogfood run that drove this workflow's introduction; the LLM pass was reviewing surfaced hunks one at a time without consulting the contracts that lived in the same diff:

- **Missing schema field**: a helper emitted `markdown_sections[N]{file,heading,siblings}` while the consumer's documented schema declared `markdown_sections[N]{file,line,heading,siblings}` (the `line` field anchors findings). Cross-checking the emitted dict against the schema declared in the same change set catches the omission.
- **Loosened detection heuristic**: a CI-provider detection routine matched on a substring (`'github' in url`) where the contract section documented a structured project marker (`.github/workflows/*.yml`). Cross-checking the new heuristic against the documented marker catches the over-broad match before it produces false positives in production.

The Step 2a cross-reference setup plus Step 3 check 5 close that gap.
