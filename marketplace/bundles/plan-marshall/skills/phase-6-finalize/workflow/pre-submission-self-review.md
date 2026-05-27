---
name: default:pre-submission-self-review
description: Pre-submission structural self-review (symmetric pairs, regex over-fit, wording, duplication, contract drift) before commit-push
order: 7
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Pre-Submission Self-Review

Pure executor for the `pre-submission-self-review` finalize step. Catches the class of structural defects that PR-review bots reliably surface but local quality gates systematically miss: missing initialization in symmetric save/restore pairs, regex/glob over-fit, ambiguous user-facing wording, duplicate prose sections covering the same contract, and schema/contract drift.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The step combines a deterministic helper that surfaces concrete candidates from the staged diff (Step 1 below) with an LLM cognitive review applied only to those candidates (Steps 2–3 below). Step 1 (deterministic surface) and Step 4 (outcome bookkeeping) run inline in the manifest dispatcher's context; Steps 2–3 (contract cross-reference setup + the five LLM cognitive checks) run in the dispatched envelope under `--phase phase-6-finalize` (no `--role` — pre-submission-self-review tracks `phase-6-finalize.default`). On any finding the LLM returns, the step hard-fails and halts the phase, mirroring the gating-step convention established by `pre-push-quality-gate`.

This document carries NO step-activation logic. Activation is controlled by the manifest composer in `manage-execution-manifest/scripts/manage-execution-manifest.py` via the `pre_submission_self_review_inactive` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`). The composer drops the step when `commit_strategy == none` (transitively, via `commit_strategy_none`) OR `references.modified_files` is empty. When the dispatcher runs this step the executor always runs to completion: a clean run records `outcome=done`; a non-empty findings list records `outcome=failed` and halts the phase.

## Domain-Aware Candidate Surfacing

The deterministic surfacer is pluggable via the `ext-self-review-{domain}` extension point — see [`../../extension-api/standards/ext-point-self-review-surfacing.md`](../../extension-api/standards/ext-point-self-review-surfacing.md) for the contract. Each implementor exposes a `surface --plan-id {plan_id}` script that emits the seven candidate sub-lists below as TOON. The plan-marshall-domain implementor is the renamed skill `ext-self-review-plan-marshall`; its script notation is `plan-marshall:ext-self-review-plan-marshall:self_review`. Step 1 resolves the implementor via `manage-config skill-domains` against the plan's declared domain.

## Inputs (inline step — Step 1)

- `references.modified_files` — list[string] of repo-relative paths recorded by Phase 5. Defines the change footprint the deterministic helper inspects.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). The deterministic helper invocation MUST identify the worktree via `--plan-id {plan_id}` alone (preferred — the implementor auto-resolves the worktree path through `manage-status get-worktree-path`; `--plan-id` is also used for the modified-files lookup, so it is required either way) or by additionally supplying `--project-dir {worktree_path}` as an explicit override. The staged diff is computed against the worktree's base branch.

## Inputs (dispatched envelope — Steps 2–3)

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier. |
| `WORKTREE` | Yes | Repo-relative working-directory path. |
| `candidates` | Yes | TOON envelope from the resolved `ext-self-review-{domain}` surface helper — carries the seven candidate sub-lists below. The orchestrator runs the surface helper in Step 1 and forwards its output verbatim; the workflow body does NOT re-invoke the surface helper. |

| `candidates` sub-list | Schema | Purpose |
|-----------------------|--------|---------|
| `regexes[N]{file,line,pattern}` | Added regex literals and fnmatch globs in `.py`/`.md` hunks | Boundary check for regex over-fit |
| `user_facing_strings[N]{file,line,context,text}` | Added strings in skill prose, error messages, CLI help | Wording disambiguation |
| `markdown_sections[N]{file,line,heading,siblings}` | Added/edited markdown sections per file with sibling-section list | Duplication scanning |
| `symmetric_pairs[N]{file,line,name,partner}` | Functions whose names match save/load, init/restore, push/pop, acquire/release, open/close, start/stop pairings | Symmetric pair test-coverage check |
| `contract_sources[N]{file,sources}` | Per modified file: nearby `SKILL.md` and `standards/*.md` paths | Contract cross-reference anchor |
| `schema_bearing_files[N]{file,format}` | Markdown files within the contract radius whose content contains a fenced JSON or TOON block | Contract drift detection |
| `keep_markers[N]{file,line,identifier,kind}` + `protected_identifiers[M]` | `<!-- self-review: keep <id> -->` markers in the post-image; the top-level `protected_identifiers` set mirrors the identifier values for fast membership checks | Duplication scan refuses to drop any protected identifier |

Skills the caller MUST forward in `skills[]`: none (the workflow reads files with the `Read` tool and emits no script calls).

## Execution

### Step 1: Deterministic surface (inline)

Resolve the domain implementor via `manage-config skill-domains`, then invoke its `surface` subcommand. The implementor reads `references.modified_files` for the active plan, computes the staged diff against the worktree's base branch, and emits the seven candidate sub-lists in a single TOON document on stdout.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get-extensions --domain {plan_domain}
```

Read the `extensions.self-review` field from the TOON output to get the implementor skill notation (e.g., `plan-marshall:ext-self-review-plan-marshall`). The plan-marshall-domain default — recorded under `skill_domains.plan-marshall-plugin-dev.workflow_skill_extensions.self-review` — is `plan-marshall:ext-self-review-plan-marshall`. Then invoke the surface helper:

```bash
python3 .plan/execute-script.py plan-marshall:ext-self-review-plan-marshall:self_review \
  surface --plan-id {plan_id}
```

(Auto-resolves the worktree from `--plan-id`. Add `--project-dir {worktree_path}` only when the explicit override is required.)

If the helper exits non-zero, halt and proceed to **Step 4 — Mark Step Complete (Failure)**, surfacing the helper error in the `display_detail` payload. Do NOT dispatch the LLM cognitive phase below.

Capture the helper's TOON output as `{candidates_toon}` for forwarding to the cognitive-phase dispatch.

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

The dispatched workflow body executes Step 2a (cross-reference setup) followed by Step 3 (five cognitive checks).

#### Step 2a: Cross-reference setup (in-context — MUST run before any check)

Before scanning the line-level candidate lists, load the contract sources surfaced by the deterministic phase. This step is the workflow-shape fix for the failure mode where the LLM reviews each surfaced hunk in isolation and overlooks contract drift.

1. For every entry in `candidates.contract_sources`, read every path listed in the `sources` field. These are the `SKILL.md` and `standards/*.md` files governing the changed code. Read them in full — not excerpts.
2. For every entry in `candidates.schema_bearing_files`, read the file. These are nearby markdown documents that declare a fenced JSON or TOON schema; they govern the post-image of any hunk that touches the same schema.
3. Hold the loaded contract content in working memory for the rest of the cognitive phase. The five checks below cross-reference hunks against this content; do not re-discover contracts on demand.

### Step 3: Apply five checks (in-context)

For each non-empty candidate list, apply the corresponding cognitive check to the surfaced items only — never expand the review to candidates the helper did not surface.

1. **Symmetric pair test-coverage check** — for each `symmetric_pairs` entry, search the test directory for a test that exercises BOTH `name` and `partner` and asserts the post-state of the partner without first invoking `name` in the same test. A symmetric pair where one half is silently skipped is the canonical defect class. Defect → record finding `{file, line, defect_class: symmetric_pair_uncovered, rationale: <which half is unexercised and why it matters>}`.

2. **Regex over-fit boundary check** — for each `regexes` entry, construct one synthetic example that SHOULD match (positive) and one that SHOULD NOT match (negative), and verify the regex/glob's behavior on each. If the boundary is wrong, record finding `{file, line, defect_class: regex_overfit, rationale: <example that fails the intended boundary>}`.

3. **Wording disambiguation check** — for each `user_facing_strings` entry, read the string out of the surrounding context and ask "could this mean two things?". If the answer is yes (an operator could plausibly take the wrong action based on the wording alone), record finding `{file, line, defect_class: ambiguous_wording, rationale: <the two readings, and which one was intended>}`.

4. **Duplication scan** — for each `markdown_sections` entry, compare the new/edited section's contract against its sibling sections (provided in the `siblings` field) within the same file. Two sections that describe the same check, table, or rule with subtly different wording are a defect — operators do not know which to follow. Record finding `{file, heading, defect_class: duplicate_prose, rationale: <which sibling overlaps and where they diverge>}`.

5. **Contract drift cross-check** — for every modified file that appears in `contract_sources`, AND every hunk in the diff that touches a schema declared in any `schema_bearing_files` entry, verify the post-image of the change against the documented contract:
   - For every `markdown_sections` entry whose `file` equals (or shares a parent skill with) a `contract_sources` entry, verify that the new/edited section's documented schema, table fields, or detection heuristic agrees with what the code under that skill actually emits or enforces.
   - For every code hunk that adds or modifies a function emitting a schema (e.g., `output_toon({...})`, `print(json.dumps({...}))`), verify that the emitted field set matches the schema declared in the corresponding `schema_bearing_files` entry. Missing fields, renamed fields, or extra undocumented fields are all drift.
   - For every detection heuristic added or modified (e.g., regex over a project marker, glob over a path category), verify that the heuristic agrees with the contract section that documents the same detection rule. A loosened heuristic (substring where the contract specifies a structured marker) is drift.

   Defect → record finding `{file, line, defect_class: contract_drift, rationale: <which contract source disagrees with the hunk, and what the drift is>}`.

### Dispatched-envelope output (returned from Steps 2–3 to Step 4)

```toon
status: success | error
display_detail: "<≤80 char ASCII summary>"
findings[N]{file,line,defect_class,rationale}:
  - ...
```

`status: success` regardless of findings count — the workflow itself succeeds at producing the structural-review verdict; the caller's manifest-step orchestration translates a non-empty `findings` list into the manifest step's `--outcome failed` per the gating-step convention. Empty `findings` → caller marks `--outcome done`.

`display_detail` shape:
- Empty `findings` → `"self-review clean: {N} candidates examined"` (sum of the six list lengths).
- Non-empty `findings` → `"self-review found {K} issues"`.

### Step 4: Mark Step Complete (inline)

Record the outcome on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

**Branch A — findings list is empty**: read the `display_detail` returned by the workflow verbatim (the workflow computes the candidate count for the human-readable message).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-submission-self-review --outcome done \
  --display-detail "{display_detail_from_workflow}"
```

**Branch B — findings list is non-empty**: surface the findings in the finalize TOON output (consumed by `output-template.md`) so the operator sees `file:line` and `defect_class` per finding:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step pre-submission-self-review --outcome failed \
  --display-detail "{display_detail_from_workflow}"
```

The dispatcher's existing failure handling halts the phase on `outcome=failed`, matching the gating-step contract used by `pre-push-quality-gate`. The operator must address every finding (amend the diff: rename, tighten regex, rewrite wording, delete duplicate section, fix contract drift), re-run the step, and only then advance to `commit-push`.

## Worked example: the lesson that drove this workflow

Both defect classes were missed in the dogfood run that drove this workflow's introduction; the LLM pass was reviewing surfaced hunks one at a time without consulting the contracts that lived in the same diff:

- **Missing schema field**: a helper emitted `markdown_sections[N]{file,heading,siblings}` while the consumer's documented schema declared `markdown_sections[N]{file,line,heading,siblings}` (the `line` field anchors findings). Cross-checking the emitted dict against the schema declared in the same change set catches the omission.
- **Loosened detection heuristic**: a CI-provider detection routine matched on a substring (`'github' in url`) where the contract section documented a structured project marker (`.github/workflows/*.yml`). Cross-checking the new heuristic against the documented marker catches the over-broad match before it produces false positives in production.

The Step 2a cross-reference setup plus Step 3 check 5 close that gap.
