---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Pre-Submission Self-Review Workflow

LLM-judgement structural review applied to the candidates surfaced by `tools-self-review:self_review surface` — symmetric pair test coverage, regex over-fit, ambiguous user-facing wording, duplicate prose sections, and contract drift. Dispatched under `--phase phase-6-finalize` (no `--role` — pre-submission-self-review tracks the phase-6-finalize default).

The orchestration prose for the manifest step itself (running the deterministic helper, parsing the candidate lists, recording the step outcome) lives in [`../standards/pre-submission-self-review.md`](../standards/pre-submission-self-review.md); this workflow body covers only the LLM cognitive phase the dispatcher hands off to.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier. |
| `WORKTREE` | Yes | Repo-relative working-directory path. |
| `candidates` | Yes | TOON envelope from `tools-self-review:self_review surface --plan-id {plan_id}` — carries the six candidate lists below. The orchestrator runs the surface helper and forwards its output verbatim; the workflow body does NOT re-invoke the surface helper. |

| `candidates` sub-list | Schema | Purpose |
|-----------------------|--------|---------|
| `regexes[N]{file,line,pattern}` | Added regex literals and fnmatch globs in `.py`/`.md` hunks | Boundary check for regex over-fit |
| `user_facing_strings[N]{file,line,context,text}` | Added strings in skill prose, error messages, CLI help | Wording disambiguation |
| `markdown_sections[N]{file,line,heading,siblings}` | Added/edited markdown sections per file with sibling-section list | Duplication scanning |
| `symmetric_pairs[N]{file,line,name,partner}` | Functions whose names match save/load, init/restore, push/pop, acquire/release, open/close, start/stop pairings | Symmetric pair test-coverage check |
| `contract_sources[N]{file,sources}` | Per modified file: nearby `SKILL.md` and `standards/*.md` paths | Contract cross-reference anchor |
| `schema_bearing_files[N]{file,format}` | Markdown files within the contract radius whose content contains a fenced JSON or TOON block | Contract drift detection |

Skills the caller MUST forward in `skills[]`: none (the workflow reads files with the `Read` tool and emits no script calls).

## Step 1: Cross-reference setup (MUST run before any check)

Before scanning the line-level candidate lists, load the contract sources surfaced by the deterministic phase. This step is the workflow-shape fix for the failure mode where the LLM reviews each surfaced hunk in isolation and overlooks contract drift.

1. For every entry in `candidates.contract_sources`, read every path listed in the `sources` field. These are the `SKILL.md` and `standards/*.md` files governing the changed code. Read them in full — not excerpts.
2. For every entry in `candidates.schema_bearing_files`, read the file. These are nearby markdown documents that declare a fenced JSON or TOON schema; they govern the post-image of any hunk that touches the same schema.
3. Hold the loaded contract content in working memory for the rest of the cognitive phase. The five checks below cross-reference hunks against this content; do not re-discover contracts on demand.

## Step 2: Apply five checks

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

## Output

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

## Worked example: the lesson that drove this workflow

Both defect classes were missed in the dogfood run that drove this workflow's introduction; the LLM pass was reviewing surfaced hunks one at a time without consulting the contracts that lived in the same diff:

- **Missing schema field**: a helper emitted `markdown_sections[N]{file,heading,siblings}` while the consumer's documented schema declared `markdown_sections[N]{file,line,heading,siblings}` (the `line` field anchors findings). Cross-checking the emitted dict against the schema declared in the same change set catches the omission.
- **Loosened detection heuristic**: a CI-provider detection routine matched on a substring (`'github' in url`) where the contract section documented a structured project marker (`.github/workflows/*.yml`). Cross-checking the new heuristic against the documented marker catches the over-broad match before it produces false positives in production.

The Step 1 cross-reference setup plus check 5 close that gap.
