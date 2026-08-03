---
name: ext-self-review-plan-marshall
description: Plan-marshall-domain implementor of the ext-self-review-{domain} extension point. Surfaces deterministic candidates (regexes, user-facing strings, markdown sections, symmetric-pair functions, flag-guard pairs, contract sources, schema-bearing files, keep markers, producer-consumer pairs, source-of-truth duplicates, same-document normative directives, description-vs-body frontmatter, lone-unguarded-boundary calls, stale count-prose, near-identical-hunk touched claims, advertised-form help strings, same-document ordinal references, scan-derived keys, worked-example clause pairs) for pre-submission structural self-review.
user-invocable: false
mode: script-executor
implements: plan-marshall:extension-api/standards/ext-point-self-review-surfacing
---

# Self-Review Candidate Surfacing — plan-marshall domain

**Role**: Plan-marshall-domain implementor of the `ext-self-review-{domain}` extension point (see [`../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`](../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md)). Surfaces concrete candidates from the worktree's staged diff so the LLM cognitive review pass in [`../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`](../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md) can apply the fifteen structural-defect checks (symmetric pair, regex over-fit, wording disambiguation, duplication, contract drift, producer-without-consumer, source-of-truth drift, same-document contradiction, description-vs-body drift, unguarded boundary, stale count-prose, touched-claim re-check, ordinal-reference re-check, scan-derived-key reachability, worked-example clause mismatch) against a bounded surface, not an unbounded read of the whole diff.

## Finding-authoring contract (cognitive review pass)

When the cognitive review pass files a finding for a confirmed structural defect, it MUST honor two rules so the finding flows cleanly through the consolidated find → ingest → one-triage → one-respond pipeline:

1. **Title = defect class + subject, never a bare defect class.** The finding title MUST carry both the defect class AND a content-distinguishing subject (the specific file / symbol / passage the defect is about) — e.g. `symmetric-pair-missing-test: save_state has no test surface`, NOT a bare `symmetric-pair-missing-test`. A bare-class title is a content collision: the discriminator-aware Q-Gate dedup keys on the title plus a content discriminator, and two unrelated same-class defects sharing a bare-class title erode the discriminator's distinguishing power. A class + subject title keeps each distinct defect its own finding and prevents an unrelated resolved same-class finding from being reopened.

2. **File find-only; defer triage.** The cognitive review pass FILES findings (`manage-findings add`) for confirmed defects and STOPS there — it does NOT triage them (no FIX / SUPPRESS / ACCEPT decision, no source edit, no respond). Disposition is owned by the single consolidated triage pass that runs later in finalize (`verification-feedback` → `triage.md`), which reads the promoted top-level fields and decides each finding once. Filing find-only keeps the self-review generator a pure producer on the FIND side of the pipeline.

## Enforcement

**Execution mode**: Library script; invoked via the standard 3-part executor notation by `plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md` Step 1.

**Prohibited actions:**
- Do not modify any source files; the helper is read-only against the worktree
- Do not invoke `git` without `git -C {project_dir}` (per persona-plan-marshall-agent)
- Do not write to `/tmp/` or any path outside `.plan/temp/` when staging intermediate state

**Constraints:**
- stdlib-only (no third-party Python dependencies)
- Output is TOON to stdout; errors are TOON with `status: error` and a non-zero exit code
- Every candidate entry MUST carry `file` (repo-relative path) and `line` (1-based line number in the post-diff file content) — these are the only fields the LLM cognitive review consumes for navigation

## When to Use

The `surface` subcommand is invoked exclusively by `default:pre-submission-self-review` (see `plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md` Step 1); no other caller of `surface` is supported. The sibling `scan-worked-examples` subcommand is the population-sweep entry point for a one-off audit of worked examples across a supplied file set, and carries no finalize-step caller. The script is registered as `pm-plugin-development:ext-self-review-plan-marshall:self_review` and is NOT user-invocable from a slash command — `user-invocable: false` per the script-only registration convention; this skill is intentionally absent from `pm-plugin-development/.claude-plugin/plugin.json`.

## Keep-Identifier Markers

Authors can flag identifiers that are load-bearing for grep-based external tests, downstream parsers, or any other consumer that asserts a token's literal presence in the source. The marker tells the LLM cognitive review pass that the identifier MUST remain grep-able in the post-image — prose consolidation, rename, or refactor MUST NOT remove it.

**Syntax**: `<!-- self-review: keep <identifier> -->`

- `<identifier>` is a single whitespace-free token (e.g. `phase_breakdown_override_content`, `--body`, `triage_helpers`). Whitespace inside the identifier is not supported — use one marker per identifier.
- Whitespace around `self-review:`, around `keep`, and between `keep` and the identifier is tolerant.
- The marker is an HTML comment, so it is invisible in rendered Markdown but visible to the deterministic surface scan.

**Placement**: any line within the file or section that authoritatively owns the identifier. The detector scans the diff's added/post-image lines for marker matches — placing the marker on or near the line that defines or references the protected token gives the LLM review the strongest navigational anchor. Multiple markers on the same file are allowed and each emit an independent candidate.

**Semantics**: for each recognized marker in an added hunk, the surface scan checks whether the protected identifier still appears anywhere in the file's post-image OUTSIDE the marker line itself (the marker comment's own copy of the identifier is excluded from the grep so it cannot mask a removal):

- **Identifier still grep-able** → candidate kind `keep_protected`. The identifier joins the surface's `protected_identifiers` set so the LLM review knows to refuse any consolidation that would drop the token in a subsequent revision.
- **Identifier no longer grep-able** → candidate kind `keep_violation`. The marker is orphaned — the consolidation under review has already removed the protected token. The LLM review surfaces this as a refusal-grade defect.

The marker is a pure structural signal — no LLM call is added to the surface scan; the detector emits a `keep_markers` candidate list and a `protected_identifiers` set alongside the other heuristic lists. See the `keep_markers[]` and `protected_identifiers[]` shapes under § Output below.

## Subcommand: `surface`

Surfaces twenty candidate lists from the worktree's staged diff against the base branch.

### Inputs

| Argument | Required | Description |
|----------|----------|-------------|
| `--plan-id PLAN_ID` | Yes | Plan identifier (kebab-case). Used to derive the plan footprint on demand from the worktree (`{base}...HEAD` ∪ porcelain) and (when `--project-dir` is omitted) to auto-resolve the worktree path via `manage-status get-worktree-path`. |
| `--project-dir PROJECT_DIR` | No | Absolute path to the active git worktree (escape hatch). When omitted, the path is auto-resolved from `--plan-id`. All `git` calls run as `git -C {project_dir} ...`. |
| `--base-branch BRANCH` | No | Base branch for diff computation. Defaults to `main`. |
| `--contract-radius N` | No | Directory levels to walk up when collecting schema-bearing markdown files (default: 3). |

### Output

TOON to stdout. The candidate-list keys are always present (possibly empty):

```toon
status: success
plan_id: {plan_id}
project_dir: {project_dir}
base_branch: {base_branch}
counts:
  regexes: N1
  user_facing_strings: N2
  markdown_sections: N3
  symmetric_pairs: N4
  flag_guard_pairs: N5
  contract_sources: N6
  schema_bearing_files: N7
  keep_markers: N8
  protected_identifiers: N9
  producer_consumer: N10
  source_of_truth: N11
  same_document_consistency: N12
  description_vs_body: N13
  unguarded_boundaries: N14
  count_prose: N15
  touched_claims: N16
  advertised_form_help_strings: N17
  ordinal_references: N18
  scan_derived_keys: N19
  worked_example_pairs: N20
  total: N1+N2+N3+N4+N5+N8+N10+N11+N12+N13+N14+N16+N18+N19+N20

regexes[N1]{file,line,pattern}:
  {repo-relative-path},{line},{regex-pattern-string}

user_facing_strings[N2]{file,line,context,text}:
  {repo-relative-path},{line},{context-tag},{string-text}

markdown_sections[N3]{file,line,heading,siblings}:
  {repo-relative-path},{line},{heading},{semicolon-joined-sibling-headings}

symmetric_pairs[N4]{file,line,name,partner,test_present}:
  {repo-relative-path},{line},{function-name},{inferred-partner-name},{true|false}

flag_guard_pairs[N5]{file,line,flag,forms_covered}:
  {repo-relative-path},{line},{--flag},{space|equals|both}

contract_sources[N6]{file,sources}:
  {repo-relative-path},{semicolon-joined-contract-source-paths}

schema_bearing_files[N7]{file,format}:
  {repo-relative-path},{json|toon}

keep_markers[N8]{file,line,identifier,kind}:
  {repo-relative-path},{line},{identifier},{keep_protected|keep_violation}

protected_identifiers[N9]:
  {identifier}

producer_consumer[N10]{file,line,key,consumed}:
  {repo-relative-path},{line},{produced-key},false

source_of_truth[N11]{name,files,values}:
  {constant-name},{semicolon-joined-declaring-files},{semicolon-joined-distinct-values}

same_document_consistency[N12]{file,line,keyword,text}:
  {repo-relative-path},{line},{normative-keyword},{directive-line-text}

description_vs_body[N13]{file,line,key,description}:
  {repo-relative-path},{line},{description|summary},{frontmatter-description-text}

unguarded_boundaries[N14]{file,line,boundary,guarded}:
  {repo-relative-path},{line},{boundary-call-kind},false

count_prose[N15]{file,line,text}:
  {repo-relative-skill-md-path},{line},{matched-count-prose-line}

touched_claims[N16]{file,line,text}:
  {repo-relative-path},{line},{added-line-text}

advertised_form_help_strings[N17]{file,line,arg,help_text,raw_pass_line}:
  {repo-relative-py-path},{line},{argparse-dest},{multi-form-help-text},{raw-pass-line}

ordinal_references[N18]{file,line,text,list_line}:
  {repo-relative-md-path},{line},{ordinal-reference-line-text},{referenced-ordered-list-line}

scan_derived_keys[N19]{file,line,name,sequence,key_consumed}:
  {repo-relative-py-path},{line},{deriving-function-name},{decomposed-sequence-name},{true|false}

worked_example_pairs[N20]{file,line,clause,required_predicate,example_predicate,agrees}:
  {repo-relative-md-path},{line},{clause-heading},{predicate-the-clause-requires},{predicate-the-GOOD-example-branches-on},false
```

> The `total` count covers the fifteen line-level heuristics (`regexes`, `user_facing_strings`, `markdown_sections`, `symmetric_pairs`, `flag_guard_pairs`, `keep_markers`, `producer_consumer`, `source_of_truth`, `same_document_consistency`, `description_vs_body`, `unguarded_boundaries`, `touched_claims`, `ordinal_references`, `scan_derived_keys`, `worked_example_pairs`) only. `contract_sources`, `schema_bearing_files`, `count_prose`, and `advertised_form_help_strings` are review-anchor categories with their own counts; they are not summed into `total` — `contract_sources` and `schema_bearing_files` because each modified file contributes at most one entry whose payload is references rather than candidates, `count_prose` because it anchors a sibling-SKILL.md re-check rather than flagging an added line, and `advertised_form_help_strings` because it anchors a contract-drift sub-check rather than flagging a standalone line-level defect. `ordinal_references` IS summed into `total` because it flags a specific added line (the ordinal cross-reference whose referenced list the same change touched), `scan_derived_keys` IS summed for the same reason (it flags the scan loop's own line), and `worked_example_pairs` IS summed for the same reason (it flags the GOOD marker's own line), like the other line-level heuristics. `protected_identifiers` is a derived index over `keep_markers` entries with `kind: keep_protected` — it does not contribute to `total` either.

### Detection Rules

1. **Regexes** — added lines (`+` hunks) in `.py` and `.md` files containing one of:
   - `re.compile(...)`, `re.match(...)`, `re.search(...)`, `re.findall(...)`, `re.sub(...)`, `re.fullmatch(...)`
   - `fnmatch.fnmatch(...)`, `fnmatch.filter(...)`
   - Raw-string regex literals: `r"..."` or `r'...'` containing regex metacharacters (`^$.*+?[](){}|\`)
   - Glob patterns embedded in argparse `choices=[...]` or `--*-globs` config arrays
   The `pattern` field captures the literal string between the function call's first quote pair (or the raw-string body), truncated to 120 characters.

2. **User-facing strings** — added lines containing one of:
   - Docstring opening: triple-quoted strings on a line by themselves following `def `/`class `
   - `print(...)` first positional argument
   - argparse `description=`, `help=`, `epilog=` (any string literal directly assigned)
   - `raise XxxError("...")`, `raise XxxError(f"...")` first argument
   - Markdown heading (`^#+\s+`)
   - Markdown bullet (`^[-*]\s+`)
   The `context` field is one of `docstring`, `print`, `argparse_description`, `argparse_help`, `argparse_epilog`, `raise_message`, `markdown_heading`, `markdown_bullet`. The `text` field is the captured string, truncated to 200 characters.

3. **Markdown sections** — for each `.md` file appearing in the diff:
   - Parse all `^#+\s+` headings in the post-diff file content
   - Group siblings: headings with the same depth AND the same nearest-ancestor heading at depth-1
   - Emit one entry per heading whose line falls within an added/edited diff hunk
   - The `siblings` field is a semicolon-joined list of sibling heading texts (peer headings under the same parent), excluding the entry's own heading

4. **Symmetric-pair candidates** — added lines in `.py` files matching `^def\s+(\w+)`. The captured function name is split on `_` and inspected for any of the 6 pair tokens: `save/load`, `init/restore`, `push/pop`, `acquire/release`, `open/close`, `start/stop`. When a match is found, the `partner` field is the same function name with the matched token swapped to its pair (e.g., `save_state` → `load_state`). Each entry also carries a deterministic `test_present` flag (Tier-2 missing-test heuristic): the `test/` tree under `--project-dir` is searched for a word-boundary occurrence of the function name (same `(?<![a-zA-Z0-9_-])` / `(?![a-zA-Z0-9_-])` lookaround discipline used for keep-identifier markers). `test_present=false` is the Tier-2 missing-test signal — a newly added symmetric function with no test surface. The LLM half of the check (deciding whether the missing coverage is a real defect) lives in the consumer's Step 3 check 1; see [`../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`](../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md).

5. **Flag-guard pairs** — added lines in `.py` files containing an argument-presence guard over a `--flag` token. Two guard shapes are recognized: membership/substring tests where a quoted `--flag` literal is the left operand of an `in` test (e.g., `'--project-dir' in args`, `'--plan-id=' in argv`) and `startswith` checks over a quoted `--flag` literal (e.g., `arg.startswith('--project-dir')`). For each guarded flag the detector classifies which flag *forms* the guard covers: the bare `--flag` token guards the **space-separated** form (`--flag value`), and the `--flag=` prefix guards the **equals** form (`--flag=value`). Coverage is aggregated per `(file, flag)` across all guards in the file — `space` when only the bare token appears, `equals` when only the `--flag=` prefix appears, and `both` when both appear. The `line` field records the first guard occurrence for the flag in the file. The list anchors the cognitive review's flag-form-coverage comparison: when one guard in a symmetric pair covers `both` forms while its sibling covers only one, the uncovered form is a defect (e.g., a `--project-dir` guard covering only the space form risks double-injection that violates the mutually-exclusive-arguments contract).

6. **Contract sources** — each modified file's `sources` field is the **union** of two origins:
   - **Directory-structural**: walk up the directory tree (bounded by `--project-dir`) looking for the nearest ancestor containing `SKILL.md`. When found, that `SKILL.md` plus every `*.md` under the same skill's `standards/` subdirectory are sources.
   - **Doc-prose script reference** (`.md` files only): when a modified workflow/standards `.md` doc's added lines contain BOTH an `execute-script.py` invocation via `{bundle}:{skill}:{script}` notation AND a TOON-field reference (a `{field}` interpolation token, e.g. `{status}` or `{error}`), the referenced script's `SKILL.md` — resolved to `marketplace/bundles/{bundle}/skills/{skill}/SKILL.md` — is added as a source. The two signals need not share a line; the doc's added hunk content as a whole must satisfy both. A notation whose `SKILL.md` does not exist on disk surfaces nothing. This surfaces a sibling script's output-contract document on the doc that interpolates its TOON fields, even when the doc lives outside that script's skill directory.

   The `sources` field is a `; `-joined, sorted, deduplicated list of the unioned repo-relative paths. A modified file with neither origin contributes no entry. The list anchors the LLM cognitive review on the contract documents that govern the changed code.

7. **Schema-bearing files** — `*.md` files within `--contract-radius` directory levels of any modified file (default 3 levels up, bounded by `--project-dir`) whose content contains a fenced JSON or TOON block (`` ``` ``json` or `` ``` ``toon`). The list is deduplicated; the `format` field reports the first fence type found. Schema-bearing files surface schema/contract documents the LLM pass must cross-reference against hunks that touch the same schema (e.g., a helper output schema declared in a markdown reference).

8. **Keep-identifier markers** — added lines containing `<!-- self-review: keep <identifier> -->` (see § Keep-Identifier Markers above for the marker contract). For each match the detector emits an entry with `identifier`, `file`, `line`, and `kind`. The `kind` is `keep_protected` when the identifier is still present elsewhere in the file's post-image (the marker line itself is excluded from the grep) and `keep_violation` when the identifier is no longer present — the second case is an orphaned marker that signals the consolidation removed a protected token. The deduplicated, sorted set of every identifier whose marker resolved to `keep_protected` is emitted as `protected_identifiers` so the LLM cognitive review can refuse a consolidation that would drop one of them.

9. **Producer-consumer pairs** — added `.py` lines that *produce* a value into a dict-keyed output slot (`output['key'] = ...`, `output["key"] = ...`) with NO matching *consumer* anywhere in the diff's added lines. A consumer is a subscript read (`foo['key']` not on the LHS of an assignment) or a `.get('key'...)` call; the producer line's own LHS key never counts as a consumption of itself. The producer-consumer relation is diff-global (a key produced in one file and consumed in another counts as consumed). Each entry carries `file`, `line` (the producer line), `key` (the produced slot), and `consumed` (always `false` — only unconsumed producers are surfaced). A dangling producer surfaces a value emitted but never read by any downstream branch; the cognitive review's check 6 decides whether the missing consumer is a real defect.

10. **Source-of-truth duplicates** — added `.py` lines binding the SAME UPPER_SNAKE_CASE constant (`NAME = <literal>`) in two or more distinct diff files with NON-identical literal values. This is the source-of-truth drift signal: the diff changed the value in one declared SoT location but not the other. Each entry carries `name` (the constant), `files` (a `; `-joined sorted list of the declaring files), and `values` (a `; `-joined sorted list of the distinct literal RHS values, each truncated to 80 characters). A constant assigned the same value in two files, or a constant declared in a single file, surfaces nothing. The cognitive review's check 7 adjudicates which declaration is stale.

11. **Same-document normative directives** — added `.md` lines carrying an RFC-2119-style normative keyword (`MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, `NEVER`, `ALWAYS`, `REQUIRED`, `FORBIDDEN`). Each added normative directive is surfaced so the cognitive review can compare it against sibling normative statements ALREADY in the same document — a new normative rule that contradicts an existing one is the same-document-consistency defect. By construction this is a Mode-2 guard: an added normative line MUST surface a candidate, never an empty surface. Each entry carries `file`, `line`, `keyword` (the normative keyword that fired), and `text` (the directive line, truncated to 200 characters). The cognitive review's check 8 reads the surfaced directive against its document siblings.

12. **Description-vs-body frontmatter** — surfaces one candidate per modified `.md` file that carries a frontmatter `description:` (or `summary:`) key in its post-image AND has at least one added line in the document body (any added line below the closing frontmatter `---` delimiter). A pure frontmatter-only edit, or a `.md` with no frontmatter description, surfaces nothing. The frontmatter description summarizes the document's model; when the body changes, the description may now describe a model the body no longer implements. Each entry carries `file`, `line` (the frontmatter description line in the post-image), `key` (`description` or `summary`), and `description` (the description value, truncated to 200 characters). The cognitive review's check 9 reads the description against the changed body and surfaces a drift when they diverge.

13. **Lone unguarded boundaries** — added `.py` lines opening a `subprocess.*` call (`run`, `Popen`, `check_output`, `call`, `check_call`) or a file-I/O call (`open(`, `Path.read_text`/`write_text`/`read_bytes`/`write_bytes`) that is **unguarded**. A `subprocess.*` call is unguarded when `check=True` is absent on the same line; a file-I/O call has no `check` kwarg and is always unguarded by that criterion. The second condition is that there is no enclosing `try:` block in the same function — tracked by a per-file walk that opens an "inside try" window at a `try:` opener and closes it at the next `def`/`class` header (a `try` cannot span a function boundary). Network calls (`socket.`, `urllib.`, `http.client.`) are out of scope and never matched, and the existing sibling-envelope unguarded-pair detection is a separate concern not re-implemented here. Each entry carries `file`, `line`, `boundary` (the matched call kind, e.g. `subprocess.run` or `open`), and `guarded` (always `false` for a surfaced entry). The cognitive review's check 10 decides whether the missing guard is a real defect.

14. **Stale count-prose** — for each modified file nested inside a skill directory (the nearest ancestor containing `SKILL.md`), every `SKILL.md` in that same skill directory is scanned for count-prose: a digit OR an English number word (`one`..`twenty`) immediately adjacent to one of the cardinality nouns `operation`, `field`, `step`, `rule`, `command`. The list is a **review anchor** (excluded from `total`), not a line-level defect flag — it surfaces every count phrase that may have gone stale because a sibling file in the directory changed. Each entry carries `file` (the SKILL.md path), `line` (the matched line, 1-based), and `text` (the truncated matched line), deduplicated per `(file, line)`. The cognitive review's check 11 re-counts the referent and surfaces a drift when the prose number no longer matches.

15. **Near-identical-hunk touched claims** — for each adjacent removed/added (`-`/`+`) line pair within a hunk, both lines are tokenized; the pair fires when the two token sequences are equal in length AND differ in exactly one position (a single-token swap). The `+` line is surfaced so the cognitive pass re-verifies the REST of the line's claims, not just the swapped token. A whitespace-only difference (identical token sequences) and a multi-token difference are both excluded. Each entry carries `file`, `line` (the `+` line's post-image line number), and `text` (the truncated `+` line). The cognitive review's check 12 re-checks the surfaced line's surviving claims.

16. **Advertised-form help strings** — added `.py` lines on an `add_argument` call whose `help=` string advertises MORE THAN ONE accepted input form (e.g. "Issue number or URL"), paired with a raw-value pass-through of that argument in the SAME handler. The detector resolves the argparse destination (from an explicit `dest=` kwarg, else from the long `--flag` with dashes mapped to underscores) and searches the same file's added lines for a raw pass-through of `args.<dest>` — `str(args.<dest>)`, a bare `args.<dest>` read, or an f-string interpolation of it — that carries NO normalization call. A candidate is surfaced only when both the multi-form help AND a raw-pass site are present in the diff. The advertised contract ("this argument accepts every advertised form") drifts from the handler behaviour when only the form the raw value happens to be in actually works. Each entry carries `file`, `line` (the help-string line), `arg` (the resolved destination), `help_text` (the truncated help string), and `raw_pass_line` (the post-image line number of the raw pass-through). The list is a **review anchor** excluded from `total` (alongside `contract_sources`, `schema_bearing_files`, and `count_prose`). The cognitive review's check 5 (contract drift) reads the `help_text` and `raw_pass_line` site in context to decide whether the advertised-form promise is a real defect.

17. **Same-document ordinal references** — added `.md` lines carrying an ordinal cross-reference into a numbered list BY ITS POSITION: an `item N` / `step N` / `point N` form-noun reference, or a bare parenthesized ordinal `(N)`. The reference is surfaced only when, in the same document's post-image, the ordered-list block containing item `N` was ITSELF touched by the diff (at least one of the block's lines is among the file's added lines). That conjunction is the staleness signal: inserting or reordering a numbered-list item shifts the ordinals its positional cross-references point at, so any ordinal reference into a list the same change just edited is a re-verification candidate. Word-boundary discipline excludes `itemize`/`stepwise` and decimal `(1.5)` tokens; a reference whose ordinal resolves to no ordered-list block, or to an untouched block, surfaces nothing. Each entry carries `file`, `line` (the reference's post-image line), `text` (the truncated reference line), and `list_line` (the 1-based post-image line of the referenced ordered-list block — the line of item `N` when it resolves, else the block's first item line), deduplicated per `(file, line, ordinal)`. Unlike the review-anchor lists, this list IS summed into `total` because it flags a specific added line. The cognitive review's check 13 re-checks the surfaced ordinal against the touched list and surfaces a drift when the position no longer matches.

18. **Scan-derived keys** — an added-to `.py` function that derives an identity key by **scanning** an unbounded decomposition for a first pattern match instead of by **indexing** that decomposition at a position anchored on a known root. Two conjuncts fire the candidate: the function binds a sequence by decomposing a value (`Path(...).parts`, `.split(...)`), and it iterates THAT sequence in a loop whose body both applies a compiled-pattern match (`re.match`/`re.search`/`re.fullmatch`, or the same method on a module-level pattern constant) and exits on the first hit (`return` / `break`). A full traversal with no first-match exit, and a loop over a sequence that was never decomposed, are both excluded. Only functions the diff touched are considered; when the post-image is available the whole file is walked so a decomposition binding or enclosing `def` outside the diff still resolves. Each entry carries `file`, `line` (the scan loop's line), `name` (the deriving function), `sequence` (the decomposed sequence the loop iterates), and `key_consumed` — a Tier-2 flag that is `true` when some other function in the surfaced diff calls the deriving function AND consumes its result as an identity (grouping via `setdefault`, testing cardinality via `len`, or comparing with `==`/`!=`). Identity consumption is deliberately a flag and NOT a firing condition, because the consuming caller frequently lives outside the diff; `key_consumed: false` narrows what the adjudication must look for and never suppresses the candidate. The defect this anchors: a scanning derivation collapses every input carrying an out-of-domain leading match to the SAME key, so a guard fed by that key can never observe a difference and its refusal path is unreachable while its tests stay green. The cognitive review's check 14 decides whether the scanned domain genuinely admits only one match. See [`standards/unreachable-guard-detection.md`](standards/unreachable-guard-detection.md) for the gate verdict that selected this framing, the two rejected framings, the sees/misses discriminator, and the PR #1013 worked example — that rationale is NOT restated here.

19. **Worked-example clause pairs** — a clause section in an added-to `.md` file whose GOOD worked example branches on a DIFFERENT predicate than the one its own clause requires. A clause states a normative rule and then demonstrates it with a BAD/GOOD contrast; the rule is only demonstrated when the GOOD half branches on the predicate the clause names. When it branches on a different field, the contrast silently demonstrates the very shape the clause forbids — one field over — while reading as a correct example, and a later reader who cites the clause's title inherits the contradiction.

    The comparison is **predicate versus predicate**, never a surface-every-pair sweep:

    - **Pair recognition** — within a clause section (the nearest preceding ATX heading; heading detection is suppressed inside fences so a `# GOOD` marker never opens a spurious section), a fenced block carrying BOTH a `BAD` and a `GOOD` marker comment is a pair. Recognized marker leaders are `//`, `#`, and `<!--`, with optional non-alphanumeric decoration before the UPPERCASE marker word (`// ✅ GOOD` resolves; prose "good" never does). Each `GOOD` marker opens a region running to the next marker or to the end of the block.
    - **Required predicate** — extracted from the clause's normative prose (the lines between the heading and the block's opening fence, which is where the document's rule-then-example shape always places the rule). Two directive forms are read: the explicit `branch on X`, and a normative `Read X` / `check X` (sentence-initial or `MUST`-prefixed). The first directive whose object resolves to a non-empty token set wins. When every directive object is anaphoric (`branch on that`), the clause **heading's required half** — everything before a `, never` / `, not` / `, rather than` / `, instead of` contrast pivot — is the fallback, because the heading is the clause's own condensed statement of what it requires and the only available resolution for the anaphor. The `-ing` participle is deliberately NOT a directive form: `Branching on \`outcome.applied\` instead would reinstate the defect` names the *rejected* predicate, so admitting it would read the forbidden field as the required one.
    - **Example predicate** — the expression the GOOD region actually tests: the brace form (`if (expr)` / `while (expr)`, extracted by a balanced-paren scan so a predicate carrying its own call parentheses is not truncated), the colon form (`if expr:`), or a parenthesized ternary condition (`(expr) ? a : b`). Line comments are stripped first, so an explanatory annotation is never read as code.
    - **Comparison** — both phrases are tokenized (identifier runs split on camelCase, lowercased, dropped below four characters and against a function-word list). The pair AGREES when the two token sets share a term under a prefix relation (`persist` ↔ `persisted`), and DISAGREES otherwise. Only the disagreeing case is surfaced, following the `producer_consumer` precedent — so an empty list is a real "every adjudicable pair agrees" signal rather than "the class did not run", and a surfaced entry always carries `agrees: false`.

    **Relational cases, each with a decided disposition** (the class's silence on a case is a decision on the record, not an accident):

    | Case | Disposition |
    |------|-------------|
    | Clause section with no worked example | Surface nothing — there is no pair to adjudicate. |
    | Fenced block with a GOOD marker but no BAD counterpart | Surface nothing — a lone GOOD example is not a contrast pair, and the class adjudicates pairs. |
    | Clause carrying multiple GOOD blocks | Adjudicate each GOOD region independently; one entry per disagreeing region. |
    | Clause naming no normative predicate (no `branch on` / `Read` / `check` directive) | Surface nothing — the required predicate is unrecoverable, so no comparison is defined. |
    | GOOD example branching on nothing recoverable (no `if`/`while`/parenthesized-ternary predicate) | Surface nothing — the example predicate is unrecoverable, so no comparison is defined. |
    | GOOD marker comment naming a mechanism the body does not perform | Surface nothing — this is a comment-versus-body claim, NOT a predicate-versus-predicate disagreement. Every deterministic formulation of it fired on correct sibling examples in the audited population (a clause whose GOOD comment says "the last resort" or "is reported" while the body legitimately names neither), so it is a broader net rather than a better extractor. The LLM consumer's check 15 adjudicates the surfaced pairs; a comment-mechanism mismatch is left to ordinary review. |

    Each entry carries `file`, `line` (the GOOD marker's post-image line), `clause` (the enclosing heading), `required_predicate`, `example_predicate`, and `agrees` (always `false` for a surfaced entry). The cognitive review's check 15 adjudicates whether the disagreement is a real contradiction. Restricted to clause sections the diff touched; the `scan-worked-examples` subcommand runs the same adjudication over an arbitrary supplied file population.

### Errors

| Condition | Output |
|-----------|--------|
| Live footprint empty (no `{base}...HEAD` ∪ porcelain changes) | `status: success` with empty candidate lists (no diff scope) |
| `git -C {project_dir}` fails | `status: error\nerror: git_unavailable\nmessage: ...` (exit 1) |
| Base branch not found | `status: error\nerror: base_branch_not_found\nbase_branch: {base}` (exit 1) |
| Plan not found | `status: error\nerror: plan_not_found` (exit 1) |

## Subcommand: `scan-worked-examples`

Runs the rule-19 adjudication over a **supplied file population** rather than over the diff, and reports the population size the verdict was drawn against. The sweep case this serves is population-derived by construction: a zero-contradiction result over a real population of N pairs is a meaningfully different finding from a zero produced by an empty or mis-scoped population, and without the published denominator the two are indistinguishable.

### Inputs

| Argument | Required | Description |
|----------|----------|-------------|
| `--plan-id PLAN_ID` | Yes | Plan identifier (kebab-case). Used to auto-resolve the worktree path via `manage-status get-worktree-path` when `--project-dir` is omitted. |
| `--project-dir PROJECT_DIR` | No | Absolute path to the active git worktree (escape hatch). |
| `--paths-glob GLOB` | Yes | Relative glob selecting the population, resolved against the working tree (e.g. `marketplace/bundles/*/skills/*/standards/*.md`). Must be relative and carry no `..` segment; matches escaping the working tree are dropped. Echoed back as the boundary the counts were drawn against. |
| `--include-unadjudicated` | No | Also emit the `unadjudicated_pairs` list. Off by default — the `population` block always reports their count. |

### Output

```toon
status: success
plan_id: {plan_id}
project_dir: {project_dir}
paths_glob: {paths_glob}
boundary: {human-readable statement of the population boundary}
population:
  distinct_paths: {count of files matching the glob, deduplicated by resolved path}
  unreadable_paths: {count of matched files whose read failed}
  pair_bearing_files: {count of matched files carrying at least one GOOD/BAD pair}
  pairs_total: {count of pairs found}
  pairs_agreeing: {pairs whose predicates agree}
  pairs_unadjudicated: {pairs with no recoverable required or example predicate}
  pairs_contradicting: {pairs whose predicates disagree}

worked_example_pairs[N]{file,line,clause,required_predicate,example_predicate,agrees}:
  {repo-relative-md-path},{line},{clause-heading},{required},{example},false

unadjudicated_pairs[M]{file,line,clause,required_predicate,example_predicate,agrees}:
  {repo-relative-md-path},{line},{clause-heading},{required},{example},
```

Deduplication is on the RESOLVED path, which is what makes `distinct_paths` a count of distinct files rather than of match rows. `unreadable_paths` is reported rather than swallowed, so a read failure narrows the denominator visibly instead of silently.

### Errors

| Condition | Output |
|-----------|--------|
| `--paths-glob` absolute or carrying a `..` segment | `status: error\nerror: paths_glob_invalid\nmessage: ...` (exit 1) |
| Resolved project dir missing or not a directory | `status: error\nerror: project_dir_invalid\nmessage: ...` (exit 1) |
| Plan not found | `status: error\nerror: plan_not_found` (exit 1) |

## Cwd Policy

This script is a **worktree-scoped (Bucket B)** script (per `tools-script-executor/standards/cwd-policy.md`): callers MAY identify the working tree via either `--plan-id {plan_id}` (auto-resolved through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (explicit override / escape hatch). The script does NOT reintroduce a sideways main-anchored resolver to discover its own root — the resolved path from those flags, or the uniform cwd walk-up (ADR-002), is the only authoritative source.

`manage-references` and `manage-status` reads inside this script do NOT receive `--project-dir`; they discover `.plan/` via the uniform cwd walk-up (ADR-002) from the script's own cwd — main in phases 1-4, the pinned worktree in phase-5+.

## Tests

`test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py` covers:

- Regex detection across `.py` and `.md` hunks (positive + negative)
- User-facing string detection in docstrings, `print()`, and argparse `help=`
- Markdown section enumeration with sibling-list correctness
- Symmetric-pair detection across all 6 pairings
- Symmetric-pair test-presence (`test_present`): `true` when the `test/` tree references the function name, `false` (Tier-2 missing-test signal) when it does not, and word-boundary discipline (no substring false positives, missing `test/` directory → `false`)
- Flag-guard-pair detection: a guard covering both forms (`both`), a guard covering only the space form (`space`), a guard covering only the equals form (`equals`), the asymmetric-pair case (one `both` guard + one single-form sibling), and the negative case (no flag guard → empty list)
- Contract-source doc-prose augmentation: an `.md` doc whose added lines reference a sibling script (`execute-script.py {bundle}:{skill}:{script}`) AND a TOON field (`{status}`) surfaces that script's `SKILL.md`; the doc-referenced source is unioned with any directory-structural sources; a dangling notation (no `SKILL.md` on disk) surfaces nothing; a notation without a TOON-field token surfaces nothing; a TOON-field token without a notation surfaces nothing
- Empty-diff edge case (empty live footprint → empty candidate lists)
- `--project-dir` honoring (script does not discover root from cwd)
- Keep-identifier marker detection: `keep_protected` when the identifier is still grep-able in the post-image; `keep_violation` when the consolidation removed the token; marker syntax variations (whitespace tolerance, multiple markers per file) all recognized
- Producer-consumer detection: an `output['key'] = ...` producer with no consumer surfaces a candidate (positive); the same key read back via subscript or `.get()` (in the same or another file) suppresses it (negative); the producer line's own LHS key never self-consumes
- Source-of-truth duplicate detection: the same UPPER_SNAKE_CASE constant assigned divergent literals across two files surfaces a candidate (positive); the same constant assigned identical values, or declared in a single file, surfaces nothing (negative)
- Same-document normative-directive detection: an added `.md` line carrying a normative keyword (MUST/NEVER/etc.) surfaces a candidate (positive); a non-normative added line, or an added `.py` line, surfaces nothing (negative)
- Description-vs-body detection: a modified `.md` with a frontmatter `description`/`summary` key AND an added body line surfaces a candidate (positive); a pure frontmatter-only edit, or a `.md` with no frontmatter description, surfaces nothing (negative)
- Lone-unguarded-boundary detection: a `subprocess.run(...)` with no `check=True` outside a `try`, and a file-I/O call (`open(...)`, `Path.read_text(...)`) outside a `try`, each surface a candidate (positive); the same calls with `check=True` or inside a `try/except` in the same function surface nothing; a `def` header resets the try-window across functions; network calls (`urllib`, `socket`) surface nothing (out of scope)
- Stale count-prose detection: a modified sibling file plus a SKILL.md whose prose carries `twelve fields` / `5 rules` surfaces those count-prose lines (positive); a digit NOT adjacent to a cardinality noun surfaces nothing; a modified file outside any skill directory surfaces nothing; the same skill dir reached via two modified siblings deduplicates per `(file, line)`
- Near-identical-hunk touched-claim detection: the diff-pair walk (`_iter_changed_line_pairs`) yields `(file, post_line, removed, added)` for adjacent `-`/`+` pairs and ignores unpaired lines and context-broken pairs; a `-`/`+` pair differing by exactly one token surfaces the `+` line as a `touched_claim` (positive); a many-token difference, an identical pair, and a differing-token-count pair each surface nothing (negative)
- Advertised-form help-string detection: a multi-form `help=` string (e.g. "Issue number or URL") paired with a raw `args.<dest>` pass-through surfaces a candidate (positive); `dest=` kwarg override and dash-to-underscore dest derivation resolve correctly; single-form help, an already-normalized handler, no diff'd raw-pass site, and non-Python files each surface nothing (negative); identifier word-boundary discipline (`args.issue` does not match `args.issue_url`); and the `counts.total` review-anchor exclusion invariant holds end-to-end (the new list is excluded from `total` whether or not it fires)
- Same-document ordinal-reference detection: an `item N` / `step N` / `(N)` reference into an ordered-list block the diff touched surfaces a candidate with correct `{file, line, text, list_line}` (positive); a reference into an untouched list, a reference to a non-existent ordinal, a non-ordinal numeric token (`version 2`, `2026`), and a non-`.md` file each surface nothing (negative); word-boundary discipline excludes `itemize`/`stepwise`/`(1.5)`; references dedupe per `(file, line, ordinal)`; and the `counts.total` inclusion invariant holds end-to-end (the new list IS summed into `total`, distinguishing it from the review-anchor lists)
- Scan-derived-key detection: a function that decomposes a value and selects a segment by first-match of a compiled pattern with a `return`/`break` exit surfaces a candidate with correct `{file, line, name, sequence, key_consumed}` (positive); the anchored form that indexes the decomposition at a fixed position, a full traversal with no first-match exit, a loop over a sequence that was never decomposed, and a non-Python file each surface nothing (negative); the `key_consumed` flag resolves `true` when a sibling function calls the deriver and groups/counts/compares its result and `false` when no such caller is in the diff; and the `counts.total` inclusion invariant holds end-to-end (the list IS summed into `total`)
- Worked-example clause-pair detection: the **matched control pair** on the checked-in literal clause-(d) fixtures — the class FIRES on the pre-fix text (whose GOOD example branches on `outcome.applied` while the clause requires an affirmative success signal) and is SILENT on the post-fix text now live on `main` (whose GOOD example branches on `outcome.status == "success"`). Both fixture texts are checked-in literal content, never resolved from a git object at test time: the pre-fix text lives only on a squash-merged branch commit and is a garbage-collection candidate, so a git-resolving fixture would pass today and silently stop testing anything once the object is pruned. Generality is exercised on pairs the extractor was NOT authored against — a clause whose `Read the producer's own status field first` directive agrees with a `result.status != "success"` example, and a clause whose ternary-only predicate agrees with its `Read the wrapper's reported outcome` directive. Each relational case carries its own case: no worked example, a GOOD block with no BAD counterpart, multiple GOOD blocks in one clause, a clause with no normative directive, a GOOD example with no recoverable branch predicate, and the comment-versus-body mechanism claim (all six surface nothing except the multiple-GOOD case, which adjudicates each region). The `counts.total` inclusion invariant holds end-to-end (the list IS summed into `total`), and the `scan-worked-examples` population verb reports `distinct_paths` deduplicated by resolved path, the pair-bearing subset size, and rejects an absolute or `..`-bearing `--paths-glob`

`test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_reachability_regression.py` pins the PR #1013 pre-fix scanning and post-fix anchored forms end-to-end through the composed `surface` path.

## Canonical invocations

The canonical argparse surface for `self_review.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### surface

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-self-review-plan-marshall:self_review surface \
  --plan-id PLAN_ID [--project-dir PROJECT_DIR] [--base-branch BASE_BRANCH] [--contract-radius CONTRACT_RADIUS]
```

`--project-dir` is optional: when omitted, the worktree path is auto-resolved from `--plan-id`. Supplying both is allowed because `--plan-id` also drives modified-files lookup.

### scan-worked-examples

```bash
python3 .plan/execute-script.py pm-plugin-development:ext-self-review-plan-marshall:self_review scan-worked-examples \
  --plan-id PLAN_ID --paths-glob PATHS_GLOB [--project-dir PROJECT_DIR] [--include-unadjudicated]
```

`--paths-glob` is required and must be relative to the working tree — the population boundary is always stated explicitly rather than defaulted, because the reported counts are only interpretable against a named denominator.

## Related

- [`standards/unreachable-guard-detection.md`](standards/unreachable-guard-detection.md) — the gate verdict behind detection rule 18: the selected and rejected framings, the sees/misses discriminator, the PR #1013 worked example, and the two adjacent surfaces ruled out of scope
- [`../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`](../../../plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md) — extension-point contract this skill implements
- [`../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`](../../../plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md) — sole consumer of this script's output
- [`../../../plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md`](../../../plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md) — the `commit_push_disabled` and `scope_gated_finalize` pre-filters, both of which can drop the consumer step at compose time
- [`../../../plan-marshall/skills/tools-script-executor/standards/cwd-policy.md`](../../../plan-marshall/skills/tools-script-executor/standards/cwd-policy.md) — Bucket B cwd contract this script obeys
