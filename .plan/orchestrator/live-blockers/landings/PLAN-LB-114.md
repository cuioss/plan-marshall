# Landing Analysis: PLAN-LB-114 — the landing template, the link checker and the secure-logging text corrected

epic: live-blockers
workstream: WS-03
pr: #1915

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-114.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `3404d904c8500c9ef0a6f2f301bff33a64fc3152`, a squash commit with ONE parent, `5fd240a5e993bcac32afe93043e52fb97da13b54` (the merge of PLAN-LB-106, read with git and named in the leaf prompt). Landing message `rb-lb-114-landing-and-link-checker-corrections-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; `unknown` is an unobserved fact and not a zero; out of scope under the focus rule); its surface delta is `unmeasured`, so the surface was read from the diff: 19 files, +770/−107 (`git show --stat 3404d904c`). The lane reports 3 of 3 deliverables done and 22 Done-when clauses met, `self-review: clear` after four rounds (the fourth operator-authorized), a spec read from the ledger copy. The lane's own account is that CodeRabbit's 13 findings over three heads were all fixed; git confirms the squash commit and its subject, and nothing else about the review or CI history was re-read.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — template and Step 4 say "not shown by reading" at every layer, write the report once, map a finding to a corpus verdict | shipped-modified | The slots, the single report write, the two-valued Dispatch line, `conformance[M]` and the cross-repo field are in the diff (`analyze.md`, `landing-analysis.md`, `three-layer-analysis.md`; leaf, hunks re-read in part). The verdict mapping is not total (L1-1, re-read), so "two runs persist the same value" is not delivered for a finding that confirms a premise. |
| D2 — `verify-links` verifies or names every `link:` form; a bad target cannot abort the run | shipped-modified | Absolute target, `attribute-reference` order, the nested-block close, percent-decoding and the unreadable-fragment issue are in the code (`_cmd_verify_links.py:80-136, 313-343`, re-read). The masking that D2c adds erases some live links without naming them (L3-1, L3-2, re-read), against the spec's own fail-closed constraint. |
| D3 — the secure-logging text states one rule in one home | shipped, residue | The Java `neutralise` example escapes (`java-security-patterns.md:57-60`, re-read) and the JSON statement is narrowed (`:69`, re-read). The owning standard still states the broad JSON claim (L3-3). |
| surface | files outside the declared surface | The lane names `extension-api/standards/ext-point-execution-context-workflow.md` and `agents/execution-context.md`, both needed for the cross-repo field (the leaf agrees; whether the spec's declared surface excluded them is not shown by reading, since the declaration is in the ledger). |
| `%00` hypothesis | corroborated in code, run not shown | The target resolution catches `(OSError, ValueError)` (`_cmd_verify_links.py:403-405`, re-read); that CPython raises for a NUL byte needs a run. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing; the orchestrator re-read the points marked `re-read` at their `file:line` in the merged tree. It was a reading only: no build, no test run, no write. The leaf had no Grep or Glob; it used `git log -S` pickaxe for tree-wide checks and did not read `plan-orchestrator/SKILL.md` or `orchestration-model.md` in full.

- **Dispatch:** one read-only leaf per landing — the read crosses 19 files and must not share context with the other landing read in the same firing.
- **Verdict:** layer 1 findings (**one major**, minor, info); layer 2 findings (minor and info); layer 3 findings (**two major**, minor, info), no blocker.
- **Orchestrator re-read:** L1-1 to L1-3, L2-1, L2-2, L3-1, L3-2, L3-3, the java example and the `%00` catch. Every other row is a lead the leaf checked and I did not re-read.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 (major, re-read) | The routing table's `checked` row reads "the reading settled the point and found it wrong", but a leaf finding carries no polarity (`three-layer-analysis.md:39-43`: layer, severity, file, line, claim, verdict). A `checked` finding that confirms a premise (the leaf returned several, e.g. "all five premises hold") maps to `contradicted` or to no row. A wrong `contradicted` on a staged spec's claim would block the spec's admission at the prep-ready test. | checked | `analyze.md:184-187` |
| L1-2 (minor, re-read) | The routing bullet contradicts itself: "A claim this layer corroborates is persisted by `corpus set-verdict`" against "a layer-1 finding never yields [`corroborated`]". | checked | `analyze.md:182, 189` |
| L1-3 (minor, re-read) | The never-downgrade rule names only a claim that already carries `corroborated`. A `not_shown_by_reading` finding on a claim Step 2b settled as `contradicted` maps to `unverifiable` and overwrites it; two findings on one claim with different leaf verdicts have no stated precedence. | checked | `analyze.md:189` |
| L1-4 (minor, leaf) | D2c names only a `link:` macro inside a mask; the fail-closed constraint is wider (`xref:`, `<<anchor>>`, a macro in a listing block that re-enables macros, a macro spanning lines). The spec's scope is narrower than its own constraint, which is the root of L3-2. | checked, root re-read | `_cmd_verify_links.py:105` |
| L1-5 (info, leaf) | D3 requires naming the Java release while the standing constraint forbids "version numbers in a bundle document"; read literally the two clash, and the spec says which wins nowhere. | checked | `java-17-features.md:116` |
| L1-6 (info, leaf) | The five premise leads of the earlier landings (`conformance[N]` vs `[M]`, `WORKTREE` repo-relative, the repeated example, two owners in `logging-standards.md`, the javadoc scope) all hold at the parent. | checked | diff hunks |

**Layer 1 verdict:** findings — 1 major, 3 minor, 2 info.

### Layer 2 — Implemented

- **L2-1 (minor, re-read):** `test_the_inline_only_index_names_only_the_item_one_write` passes at the parent: the Inline-only index is untouched by the diff (no hunk in `analyze.md` near it, `git diff 5fd240a5e 3404d904c -U0`), so it is a guard, not a red-first test. The lane did not claim it red; it names `test_step_four_hands_the_analysis_to_the_single_report_write` for that clause, and that test asserts text the parent lacked. Not a fault of the lane.
- **L2-2 (minor, re-read):** the D1c test checks token and phrase presence only (`test_analyze_three_layer_contract.py:546-560`); a text that swapped the mapping would still pass, and it hard-codes the corpus verdicts where the module header asks for them to be derived. It cannot catch L1-1.
- **L2-3 (minor, leaf, not re-read):** D2f is tested for an internal anchor only; the cross-file fragment decode and the xref anchor decode have no test, and the test anchor carries a space that Asciidoctor does not register. D2d is tested for the directory-named-`x.adoc` case only (a permission error and a non-UTF-8 file are untested). One D3 assertion (`'escapes' in s or 'escape' in s`) holds at the parent; the test is red only through its other line.
- **L2-4 (info, leaf):** D1a, D1b, D1d, D1e, D1f and D2a, D2b, D2c, D2e trace to code and to a test that is red at the parent by absence of a string or by behaviour; `git log -S` shows `conformance[N]` was only ever in `analyze.md`, the test (as a negative) and ledger copies, so the single spelling holds tree-wide.
- **L2-5 (info, leaf):** the "38 pre-existing tests stayed green unchanged" claim is borne out by the diff (one appended hunk, no changed fixture), but their count and result need a run; `not_shown_by_reading`. The lane's red-first evidence and the per-head test and verify runs are its own claim, not re-read.

**Layer 2 verdict:** findings — 4 minor, 3 info.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read) | `_cmd_verify_links.py:14-17, 74, 105-106, 293` | `link:++https://example.org/a_b++[x]` (Asciidoctor's form for a target with special characters), or `link:https://x/?q=+foo+[y]` | `_PASSTHROUGH_RE` matches the target; the mask counts only a `link:` macro wholly inside the masked text (`:105`), and the `link:` prefix lies outside it, so nothing is hidden and nothing is counted. The text is blanked, and `_LINK_MACRO_RE` needs a non-blank target (`:17`), so the macro matches nowhere. The link is in neither `total_links`, `issues` nor `unchecked_link_classes`: an unexamined form is reported nowhere. The ref-asciidoc `SKILL.md:221` ("a macro the checker skipped … is counted", leaf, line not re-read) is false for it. At the parent the `++` target was extracted and examined (as a relative file, so likely a false `broken`); now it vanishes. | major |
| L3-2 (re-read, root in the spec) | `_cmd_verify_links.py:105, 255-292` | `++xref:missing.adoc[x]++`, `pass:[<<a>>]`, or a code span carrying `xref:a.adoc[b]` | The masks hide `xref:` and `<<anchor>>` as well as `link:`, but only `_LINK_MACRO_RE` is counted. For `++` and `pass:[` this is a coverage regression: the parent extracted and checked those forms. The spec scoped the naming to `link:` (L1-4), so the code does what D2c says and the spec does not meet its own fail-closed constraint. | major |
| L3-3 (re-read) | `secure-logging.md:54-55`; `java-security-patterns.md:69` | A reader of the owning standard | The owner still says JSON "automatically escape[s] CRLF and special characters, so forged entries cannot be injected" (`:54`); the Java leaf now narrows it to quote, backslash and C0, and says DEL, C1 and U+2028/U+2029 still need neutralising (`patterns:69`). State-once runs the wrong way: the narrowed statement lives in the leaf, not the owner. The regex arm of `:55` ("add an explicit C1 range test — together they cover the set") read alone omits U+2028/U+2029. | minor |
| L3-4 (leaf, not re-read) | `_cmd_verify_links.py:474, 496, 403, 63, 654` | `xref:/etc/hostname[x]`; a self-referencing symlink under Python 3.12; ``` ``link:missing.adoc[x]`` ```; a run whose only failures are unreadable targets | The xref path still joins an absolute target onto the file's directory and its target is not percent-decoded while its anchor is; a symlink loop raises `RuntimeError` from `Path.resolve`, which the `(OSError, ValueError)` guard does not catch, aborting the run (the interpreter behaviour is external); a double-backtick span pairs as two empty spans so a syntax example stays live; an unreadable-only run reports `broken_links 0, format_violations 0` with `status: failure`, so a consumer that gates on the counts passes. | minor |
| L3-5 (leaf, not re-read) | `_cmd_verify_links.py:80, 232, 124, 633, 458, 282` | — | The comment "outermost first" is false (the code span is applied first); an unterminated or mismatched-length block silently skips the rest of the file with no name or count; an indented `----` is accepted as a delimiter (pre-existing); a directory named `x.adoc` is a file-level failure; `_extract_from_file` re-reads outside the guard; `<<file.adoc#a>>` yields two issues. | info |
| L3-6 (leaf, not re-read) | `execution-context.md:37`; `ext-point-execution-context-workflow.md:67`; `java-17-features.md:115-116`; `logging-standards.md:319`; `doc_references.py:23` | — | A dangling "§ Worktree-Resolution Root" (the heading is "Workflow-Resolution Root"); the ext-point text names a field "under § Input Contract" that section does not declare; "Java 21, the release that introduced pattern switches" misstates preview in 17 (external fact); `logging-standards.md:319` restates part of the owner's check set; `doc_references.py` drifts further from the checker it says it mirrors. | minor / info |
| L3-7 (leaf) | `three-layer-analysis.md:12` | — | The leaf document allows "the sanctioned corpus read" for the spec while the dispatch prompt forbids any corpus call; the two give different instructions. Prompts should pass the spec body as data, which this firing did. | info |

**Layer 3 verdict:** findings — two major (L3-1, L3-2), L3-3 and L3-4 minor, the rest minor and info.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing three heads (`389e17be1`, `cb70a319c`, `c009ac1b5`), all 13 findings fixed, and the standing authorization applied for the merge head `e0055ff57` with the `final_review_risk_coverage` marker `kind=reviewed` naming `c009ac1b5`; Sourcery (optional) approved four heads. I read no review body, no PR body and no CI output: the review history, the CI result, the one reported `verify` flake and the merge-queue path are the lane's claim and are `not_shown_by_reading`. The merge was on the lane's standing-authorization claim, and the barrier that ran for it was the pre-change one (PLAN-LB-106 reached `main` just before; see its report for L3-1 there). Git confirms the squash commit `3404d904c` and its subject.

## Residue and Watches

- The two major layer-3 findings and the layer-1 routing gap want a fix plan; it is staged on the operator's word only. They share the surface of this plan (`_cmd_verify_links.py` and its tests, `analyze.md` Step 4, `secure-logging.md`), so the fix plan is a candidate for the plans that touch the same files. Parked PLAN-LB-69 edits the same Step 4 and the same template and must be reconciled against this result.
- Landing residue the lane names: `cmd_corpus_set_verdict` does not refuse a downgrade of a corroborated verdict (procedural rule only; the script was not read); `verify-links` does not examine a `link:` macro inside a listing block that re-enables macros; the `WORKTREE`/`OTHER_REPO_PATH` paragraph is unpinned by any test (the leaf adds `execution-context.md:37` to that).
- Build-serialization: the lane reports one overlap of two daemon-routed builds, re-run serially; its own account, not re-read.
- The `landing-check` gap on `total_tokens` is out of scope.
