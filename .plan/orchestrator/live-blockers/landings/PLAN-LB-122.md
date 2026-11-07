# Landing Analysis: PLAN-LB-122 — the verdict mapping covers a finding that confirms a premise, and `verify-links` names every link it hides

epic: live-blockers
workstream: WS-03
pr: #1931

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-122.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `bb4c39221444537672ea0ddf56bb3541c452d3c2`, a squash commit with ONE parent, `8f61ab6cd760b607bccbee6af875cceb5df02b86` (the docs-only merge of PR 1930, read with git and named in the leaf prompt). Landing message `rb-lb-122-landing-analysis-and-link-checker-gaps-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; out of scope); its surface delta is `unmeasured`, so the surface was read from the diff: 19 files, +726/−100 (`git show --stat bb4c39221`). The lane reports 4 of 4 deliverables, `self-review: clear` after one round, the standing authorization applied for CodeRabbit, a spec read from the ledger copy. No verb or flag was added (`git diff 8f61ab6cd bb4c39221 -G'add_parser|add_argument' --stat` is empty, leaf), so no executor regeneration is owed. A harness sync is, and it ran on 2026-11-07. The checkout HEAD had moved on (a steward land touching only `.opencode/rules/plan-marshall-standing-rules.md` and `.plan/marshal.json`), so every cited file reads the same as at the merge.

Surface against the spec's Expected Surface: five files outside it. The lane names two (`doc_references.py`, `test_orchestrator_dispatch_workflow_pin.py`) and `uv.lock`; the diff also carries `test_doc_references.py` and `test_execution_context_workflow_resolution.py`, and `doc_references.py` had its code-span regex changed, beyond the docstring the spec's hypothesis named. The spec's hypothesis path for `test_domain_content_rules.py` was wrong (the file is under `test/pm-dev-java/doc-contracts/`). `uv.lock`: all 8 lines are the types-pyyaml pin (the dev specifier plus the resolved version, sdist and wheel); the lane says the spec's Write-Boundary excludes it, but that boundary covers only `.plan/orchestrator/` writes, so it is an Expected-Surface deviation, not a Write-Boundary one.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the Step 4 mapping is total, a confirming finding is never a contradiction | shipped; text rule only, with a reading gap (L3-2) | A `polarity` field (`confirms` / `refutes` / `none`) was added; the table has a `checked`/`confirms` row; one persistence rule; never-downgrade names `contradicted`, `corroborated`, `unverifiable`; a precedence is stated (`analyze.md:182-192`, `three-layer-analysis.md:39-43`; re-read). The outline chose the text arm: no script refusal, no verb (`orchestrator.py:5012-5075,5188-5194`; leaf). |
| D2 — `verify-links` counts or names every masked form | shipped-modified; **a mask in the middle of a target is still silent (L3-1, major)** | The five fixture forms are counted under their mask classes (`_cmd_verify_links.py:144-149,176-179`; leaf). `SKILL.md:221` overstates the guarantee (L1-4). |
| D3 — the secure-logging owner states the narrowed claim | shipped | The narrowed claim is correct (the JSON string grammar escapes the quote, the backslash and U+0000–U+001F; DEL, C1 and U+2028/U+2029 may appear unescaped); the Java leaf points at the owner (`secure-logging.md:54-55`, `java-security-patterns.md:69`; leaf). |
| D4 — the remaining edges and the guide texts | shipped | Absolute xref, xref percent-decoding, a symlink loop, a double-backtick span, an unterminated or mismatched block, the "outermost first" comment, the dangling references and the `WORKTREE` pin (leaf, cited lines). An unreadable-only run still reports `broken_links 0` and adds `unreadable_issues`. |
| executor regeneration | not owed | The argparse diff is empty. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing at the merge commit. It reported its tool deviations (no logging writes, a direct read of the spec and the narrative under `.plan/`, which the leaf standard says a leaf never does, here by instruction) and no write. The orchestrator re-read the points marked `re-read`. It was a reading only: no build, no test run, no write.

- **Dispatch:** one read-only leaf — the read crosses 19 files, with 10 narrative claims passed one by one.
- **Verdict:** layer 1 findings (one major shared with layer 3, minor); layer 2 findings (minor, info); layer 3 findings (**one major**, minor, info). No blocker.
- **Orchestrator re-read:** L3-1 (the probe and the link regex), L3-2 (the Step 4 table and the precedence text). Every other row is a lead the leaf checked and I did not re-read.
- **Prompt check.** The 10 claims went into the prompt as separate items.
- **Not read by the leaf:** the PLAN-LB-114 landing report (the finding ids came from the spec), `cleanup.md`, CI and job logs, the interpreter behaviour at runtime, `orchestration-model.md`.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line at bb4c39221) |
|---------|-------|---------|-----------------------------------|
| L1-3 (major, shared with L3-1; re-read) | D2: every masked form is counted or named; fail closed | met for the five fixture forms; **not met for a mask that sits mid-target** | `_cmd_verify_links.py:135-152` |
| L1-4 (minor, leaf) | D2: `SKILL.md` states the guarantee "and no more" | overstated: it says a macro whose target is wrapped in a mask is always counted, which L3-1 refutes for a mid-target mask | `ref-asciidoc/SKILL.md:221` |
| L1-1 (minor, leaf) | D1: the "total" test | met with a deviation: it checks only the `verdict` values, never polarity or layer (L3-4) | `analyze.md:182-192` |
| L1-2 (info, leaf) | D1: "refused by the stated rule" | met in text only; the spec allowed a script refusal and the outline chose the text rule | `analyze.md:192`; spec L123-125,147 |
| L1-6 (info, leaf) | D4: an unreadable-only run | met with a deviation: it still reports 0 and adds `unreadable_issues`; the log line names the count | `_cmd_verify_links.py:784,795-796,816` |
| L1-8 (minor, leaf) | Expected Surface | five files outside it, see above | diff stat |
| L1-9 (minor, leaf) | Standing constraint: counts come from an enumeration, not a hand list | violated: the class counts are hard-coded | `test_asciidoc.py:1122-1127` |
| L1-5, L1-7 (leaf) | D3, D4 other bullets | met | see the fidelity table |

**Layer 1 verdict:** findings — one major shared with layer 3, five minor.

### Layer 2 — Implemented

- **Confirmed (leaf):** C1 (the five tests exist; weaker than stated, L3-4), C2, C3 for the five fixture forms (the mutation run itself is unverifiable), C4, C5, C6 for the three parent-green tests (the anchor decode at `:633`, the fragment decode at `:452` and the `OSError` catch at `:510` existed at the parent), C8.
- **C7 contradicted:** the surface list is incomplete (above).
- **C9:** (a) a real, low gap: `cmd_corpus_set_verdict` still replaces a settled verdict unconditionally (L3-3); (b) `xref:https://…` is still joined onto the file's directory and reported broken, unchanged by the new absolute arm, which handles only `/` and `\`; (c) the `skip-bot-review` label on the merged PR is the lane's account, unverifiable by reading.
- **C10:** the process claims (one self-review round clear, the CodeRabbit rounds and quota refusals, CI on the heads, four guard refusals, two operator questions, the job-id evidence table) are unverifiable and are the lane's account. The second operator question had no option selected; the lane applied a label the operator asked for twice and still obtained the required review.

**Layer 2 verdict:** findings — one claim contradicted (C7), one misframed note (the Write-Boundary), the rest confirmed.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read) | `_cmd_verify_links.py:17,135-152` | `link:docs/+v1+/missing.adoc[x]` or `link:https://x/?q=+foo+&r=1[y]`: a passthrough or code-span mask in the MIDDLE of the target | The spanning probe matches the label only when `[` immediately follows the mask (`re.match` at `:147`). With text between the mask and the `[`, no label is found and the probe returns `None`; the masked line has a blank inside a target whose grammar admits no whitespace, so `_LINK_MACRO_RE` matches nowhere. The link is in no total, issue or unchecked class: silent, the class PLAN-LB-114 L3-1 named and this plan was written to close. | major |
| L3-2 (re-read) | `analyze.md:187,189,192` | A claim Step 2b settled `contradicted`, then a layer-1 `checked`/`confirms` finding on it | The `confirms` row carries no "only when the claim carries no settled verdict" qualifier (the `unverifiable` row does); never-downgrade names only a `not_shown_by_reading` finding; the precedence sentence speaks of "two findings". Read one way, two runs persist different values; read the other way, a wrong `contradicted` can never be lifted, which is the prep-ready blocking the spec's ruling cites. | minor |
| L3-3 (leaf) | `orchestrator.py:5188-5207`; `analyze.md:68` | A misapplied Step 4 or `cleanup.md` re-grounding call | `corpus set-verdict` overwrites a settled verdict; the change is visible only after the fact (`previous_line`), recoverable from ledger git history. The lane answered CodeRabbit's write-boundary finding as out of scope although the spec offered `orchestrator.py` for exactly that refusal. | minor |
| L3-4 (leaf) | `test_analyze_three_layer_contract.py:637-654` | Deleting the layer-2/3 rows; a duplicate combination with another verdict; a reworded contradiction | The doc tests stay green: the polarity vocabulary is never used, `..._statements_agree` guards only the exact retired phrase, and the never-downgrade test checks that words are present, not that the rule refuses. | minor |
| L3-5 (leaf) | `_cmd_verify_links.py:523` | Python 3.13 or later; a recursion depth failure | Non-strict `resolve()` raises no `RuntimeError` there, so the symlink test is green either way; catching `RuntimeError` also swallows `RecursionError` as "unreadable". Which Python CI runs was not read. | info |
| L3-6 (leaf) | `doc_references.py:190` against `_cmd_verify_links.py:67` | the "kept in step" twin regexes | They already differ: the doc_references regex lacks the checker's closer guard. | info |
| L3-7 (leaf) | `_cmd_verify_links.py:462,607-610` | an absolute xref target | It is named under `absolute-path`, but `status` stays `success`, so a broken `/docs/x.adoc` passes a consumer that gates on status. `xref://host/x` is now classed absolute-path rather than external. | info |
| L3-8 (leaf) | `_cmd_verify_links.py:108,302` | `` <<`anchor`>> `` | silent: the prefix regex knows only `link` and `xref`; the second clause of `_target_was_masked` is effectively unreachable. | info |
| L3-9 (leaf) | `_cmd_verify_links.py:381,607,807` | percent-encoded targets; regex cost | Decoding happens before the absolute test; a decoded `..` reaches only what a literal `../` reaches; no nested quantifiers (the code-span regex is quadratic in a run of backticks, the probe linear per mask, both bounded by the line); an unreadable-only run reports `failure`. | info |
| L3-10 (leaf) | `templates/landing-analysis.md:39-45,55-57` | the new polarity field | The layer-2 and layer-3 tables have no polarity column and the layer-1 prose still says "what contradicts it". | info |

**Layer 3 verdict:** findings — one major (L3-1), minor L3-2 to L3-4, the rest info.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing `4847f4e05` and `f9af868ed` (marker `kind=reviewed`, risk Low), refusing on quota for `fca7cd593` and the merge head `8ee756b21`, and the standing authorization applied; Sourcery (optional) refused on its own budget. The lane did not apply the 90-minute floor, because a qualifying review already existed. I read no review body, no PR body and no CI output: the review history, the CI result and the merge-queue path are the lane's claim and are `not_shown_by_reading`. Git confirms the squash commit `bb4c39221` and its subject.

## Residue and Watches

- One major layer-3 finding (L3-1) wants a fix; it is staged on the operator's word only. The surface is `_cmd_verify_links.py` (the probe), `ref-asciidoc/SKILL.md:221`, a fixture and its test. L3-2 to L3-4 and L1-9 (the step 4 qualifier, the test strength, the hand-counted classes) ride on files that plan touches or on the analyze documents. It sits on files no running plan declares.
- Settle first at that plan's outline: whether the probe should match a label anywhere after a mask on the line (the macro regex has no whitespace in the target, so the next `[…]` after the mask ends it), and whether a mid-target mask should be named when no label is found at all.
- **Reconcile at the next touch:** parked PLAN-LB-69 D1 against what this plan left in `analyze.md` Step 4 and the template (the polarity field is not in the template tables, L3-10).
- Owed outside this plan, operator-run: the harness sync, done 2026-11-07. No executor regeneration.
- The `landing-check` gap on `total_tokens` is out of scope.
- The lane's rule check (four guard refusals, all complied with; the `skip-bot-review` label) is its own account and is not re-read.
