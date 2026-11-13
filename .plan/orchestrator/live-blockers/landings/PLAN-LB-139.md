# Landing Analysis: PLAN-LB-139 — the review-contract scanners take the preceding paragraph and read the `=` form

epic: live-blockers
workstream: WS-05
pr: #1962 (merge commit `152c913532f2b4fb8eed506f4d55d0470bfbdd92`, one parent `280e6c4040f1b6120984834a99b76afc137dc697`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

One message from the runbook lane (sender `rb-lb-139-review-contract-scanners`, `merge_state=merged`, `deliverables 1/1`). It is `complete: false` on `total_tokens` alone (out of scope, as for every runbook landing in this epic). The squash commit has one parent and touches exactly two files: `test/plan-marshall/phase-6-finalize/_review_contract_scanners.py` and `test/plan-marshall/phase-6-finalize/test_code_review_contract.py` (read with `git show --stat`, 127 insertions, 17 deletions).

The facts block agrees with ground truth: `unresolved_review_threads=0` and `review_body_findings_total=4` equal the provider's numbers from `runbook_lane review-gate --pr-number 1962` (4 ids: `nitpick-1`, `inline-1`…`inline-3`). `review_body_findings_handled=4` was re-read from the run's progress file: four `finding:` lines. The bare `review-gate` re-run reports `handled: 0` and `merge_allowed: false` because it holds no dispositions input, which is not a difference. `sonar_open_new_issues=n/a`. No false claim found.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the lead-in is the preceding paragraph only, and the quoted-placeholder patterns read the `=` form | shipped-as-specified | `bash_blocks_with_lead_in` resets at a blank line, an ATX heading and a block open (`_review_contract_scanners.py:66-89`, re-read); both patterns carry `(?:\s+|=)` (`:27-28`, re-read) against `\s+` at `280e6c404` (re-read); tests `test_code_review_contract.py:462-566` (re-read) |

Spec sub-points: the two documents were not edited, which the spec allows ("or the documents are corrected where the stricter scanner now finds a real defect"); the lane's HYPOTHESIS that the stricter scanner finds a document defect is refuted and said so. `test_functional_review_contract.py` is on the Expected Surface and was not touched: it reads the same shared scanner. The HYPOTHESIS file `test_review_contract_scanners.py` was not created.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface), and the orchestrator re-read the points marked as re-read. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for; a second full-ship landing (PLAN-LB-137) was drained in the same firing and got its own leaf.
- **Verdict:** layer 1 clean; layer 2 findings (3: all minor); layer 3 findings (1 minor, 1 minor, 2 info). The layer-3 defects are reported to the operator in the same turn; none is major.

Re-read: the whole of `_review_contract_scanners.py` at `152c91353` and at `280e6c404`, and `test_code_review_contract.py` lines 455-566 at `152c91353`; the progress file's `finding:` lines; the provider through `review-gate`; the changed path list through git. **Not re-read** (unverified leads, recorded as such): the document-side trace that every governed template in `code-review.md` and `functional-review.md` has its citation in the paragraph directly above (the leaf lists the line numbers), `functional-review.md:90` and `:559` (the two inline templates), the squash commit's trailer wording, and the claim that `test_every_free_text_template_names_the_quoting_rule` was rewritten without a docstring.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | Premises hold at `280e6c404`: the lead-in collected every prose line since the previous block, the first block's lead-in was the whole document's prose (`after_block=False` at start), and both quoted-placeholder patterns needed `\s+` | checked | confirms | `_review_contract_scanners.py` at `280e6c404` lines 27-28 and the `lead_in = [line] if after_block else [*lead_in, line]` line (re-read) |
| L1-2 | "fails at `9cd644892`": the scanner and both contract modules are byte-identical at `9cd644892` and `280e6c404` (`git diff --stat` over `test/plan-marshall/phase-6-finalize/` lists none of them), so the lane's failing runs at `280e6c404` ground the `9cd644892` clause | checked (leaf; not re-run) | confirms | leaf |
| L1-3 | The spec says "only the immediately preceding paragraph counts" and is silent on a run of blocks separated only by blank lines; the scanner keeps the older carve-out that such a run shares the paragraph before its first block | checked | none | `:52-58` (re-read) |

No finding names a corpus claim of a staged spec of this epic, so no re-grounding verdict is persisted.

**Layer 1 verdict:** clean.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_review_contract_scanners.py:27-28, 66-89` | `test_the_lead_in_is_the_immediately_preceding_paragraph_only` (L515), `test_a_heading_between_the_citation_and_the_block_ends_the_lead_in` (L535), `test_a_heading_without_blank_line_boundaries_ends_the_lead_in` (L545), `test_an_empty_heading_ends_the_lead_in` (L551), the two `=`-form tests (L462, L467); controls L472, L526 | none (two files, both explained by D1) | checked |

- **L2-1 (minor):** `test_a_block_clears_the_paragraph_it_interrupts` (L557) cannot fail against the unfixed scanner. At `280e6c404` the first block's lead-in is the citation, `after_block` then resets the lead-in to the next prose line, so exactly one template is unreferenced and `len == 1` already holds (re-read, traced through both versions). It guards the new `paragraph = []` at fence open (`:71`) and the lane's narrative does not claim it fail-first. Recorded as a guard test, not a Done-when test.
- **L2-2 (minor):** no fixture covers a run of blocks sharing one lead-in; the real-document test is the only coverage of that carve-out, so the scanner-side branch has no isolated control. A CodeRabbit summary embedded in the squash commit body says shared lead-ins are covered; the diff does not bear that out (third-party text, treated as data).
- **L2-3 (info):** the control at L526 asserts only that the unreferenced list is empty and never that the fixture block was detected as governed, so it can pass vacuously on its own; its siblings assert non-empty results on the same fixture, which closes the gap at suite level.
- The PR body's `test_code_review_contract.py:514` failing-run reference lands on a blank line in the merged file (numbered before the split) and cannot be checked by reading — recorded as not shown by reading.

**Layer 2 verdict:** findings — 3 (2 minor, 1 info)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_review_contract_scanners.py:70-71` (re-read, traced) | `Cite (#shell-safe-free-text-in-command-templates).`, blank line, `No citation.` directly on a `bash` block with `--message '{a}'`, blank line, a second `bash` block with `--message '{b}'` | At fence open the code sets `lead_in = paragraph or introducing` and clears `paragraph`, but never moves the consumed paragraph into `introducing`. Block 1's lead-in is `No citation.`; block 2 falls back to `introducing`, which still holds `Cite …`, a citation two paragraphs above block 1, so block 2 passes the names-the-rule check. The mirror case (citation in the abutting paragraph, none above it) flags block 2 wrongly. The docstring at `:57-58` ("the paragraph before the first of them introduces the whole run") is false for this shape. Neither governed document triggers it (every governed fence follows a blank line), and it is not looser than the `280e6c404` behaviour | minor |
| L3-2 | `_review_contract_scanners.py:34, 68-77` (re-read) | a `~~~` or four-backtick fence, or a ```` ```bash ```` line inside a ```` ```text ```` block | `ANY_FENCE_RE` matches three backticks only and a block closes on any line matching it, including one with an info string. Lines inside an unrecognised fence become prose, so a blank line or a `#` line inside it acts as a paragraph break or heading and its text can become the next block's lead-in; a ```` ```bash ```` line inside a block flips block and prose to the end of the document, leaving later templates unscanned. Pre-existing grammar, shared with `unhalted_advisory_templates`; no governed document uses another fence form, but the new paragraph logic makes the gap bite on lead-ins | minor |
| L3-3 | `_review_contract_scanners.py:37, 88` (re-read) | a setext heading (`Title` over `=====`) above a block; list items or table rows with no blank line between them | `HEADING_RE` is ATX only, so a setext heading and its underline become the lead-in of the block below; consecutive list items or rows form one paragraph, so a citation in an earlier sibling item introduces a block under a later one. Neither document uses a setext heading | info |
| L3-4 | `_review_contract_scanners.py:27-28` (re-read) | `x--message "{a}"` | The two quoted-placeholder patterns carry no `(?<![\w-])` lookbehind that `FREE_TEXT_ARGUMENT_RE` (`:30`) has, so a contrived `x--message "{a}"` matches; the practical effect is that a template of that shape would be selected as governed. The double-quote `=` form was already flagged by `unquoted_free_text_arguments`, so the real gain of the fix is that a `--message='{x}'` template is now selected as governed for the names-the-rule check | info |

Boundaries that hold (re-read): a heading or `#` line inside a recognised ``` block is ignored because the block-content branch runs first (`:78-80`); `splitlines` strips CRLF; a whitespace-only line counts as blank; a trailing space on a fence line is tolerated; the first block with no prose above it gets an empty lead-in; the patterns are linear (no catastrophic backtracking).

**Layer 3 not shown by reading:** that both contract modules pass on the real documents and the gate result (`quality-gate`, `module-tests` green at `d3ee523ff`) are run results; the document-side trace is consistent with both passing but a reading cannot show it.

**Layer 3 verdict:** findings — 4 (2 minor, 2 info) plus 1 not shown by reading

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | no version history, no timestamps | conforms | leaf: no dates or change history in the new docstrings, comments or tests |
| CLAUDE.md § Documentation Standards / spec standing constraint | current state only | deviates | the docstring at `_review_contract_scanners.py:57-58` states a shared lead-in that L3-1 shows false for an abutting paragraph (re-read) |
| spec standing constraint | a stricter scanner is not loosened to keep a document passing | conforms | no document edited; both patterns only widen; the lead-in only narrows |
| spec standing constraint | tests state their purpose | conforms | every new test and helper carries a docstring (leaf); one rewritten pre-existing test, `test_every_free_text_template_names_the_quoting_rule`, still has none (not re-read) |
| spec standing constraint | tests use the `PLAN_MARSHALL_HOME` fixture | conforms | the new tests use in-memory strings only and touch no plan or home state |
| CLAUDE.md § Commit Trailer | `Co-Authored-By: plan-marshall <noreply@cuioss.de>` | conforms | leaf: the squash commit ends with the trailer (not re-read) |
| CLAUDE.md § Workflow Discipline | one command per Bash call; no shell file operations | not_shown_by_reading | these govern the lane session's behaviour, which the diff does not record; the lane reports a guard with no line for this run |

## Metrics and Anomalies

- Tokens: `unknown` (the lane measured none; out of scope).
- Duration: not recorded in the message.
- Anomalies: none. 21 build dispatches, every one `daemon_longpoll`, `in_process_fallback: 0`; one `verify` bound expiry (`timeout_used_seconds 1242`, `timeout_source explicit`) continued with the split form (`quality-gate`, then `module-tests`), both green; no killed job; no restart or re-dispatch; three CLI-surface refusals reissued in the documented shape.

## Routing and Merge Behavior

- Review: `coderabbit` (required) reviewed once at `d3ee523ff` (a qualifying `final_review_risk_coverage` marker, `kind=reviewed`, naming that head) and raised 4 findings. Two were fixed at `9d48fc10b` (`inline-2` empty heading, `inline-3` paragraph not cleared at a block open), `nitpick-1` was fixed there too, and `inline-1` (fence grammar) was answered with a stated reason: pre-existing grammar shared with another scanner, out of this plan's surface, no such fence in either guarded document. That answer is the same hole recorded as L3-2 above; the reason is honest as to the governed documents and the lane did not claim the hole absent. The later head `9d48fc10b` was not re-reviewed: the PLAN-LB-142 rule applied (one handled review is the review). `sourcery` (optional) was refused on quota at first, then reviewed the later head and approved. The three review numbers read back against the provider: threads 0 and findings total 4 equal the landing; handled 4 was re-read from the four `finding:` lines. No false claim.
- CI/merge: merge queue, squash with one parent (`280e6c404`); no rebase conflict reported.
- Sonar: `n/a` — the project has no Sonar; nothing to compare.
- Parallelization: the pairing with PLAN-LB-144 was predicted to share `functional-review.md`; this plan did not edit it, so no collision occurred and no declared surface was wrong. PLAN-LB-137 (same firing) merged right behind it with no overlap.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-139 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-139 --field pr --value 1962`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-139 --field landing --value landings/PLAN-LB-139.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-139-review-contract-scanners` (from the `rb-` sender)
- [x] epic.md narrative reconciled (queue annotation, watches, the L3-1 and L3-2 note)
- [x] resume anchor updated and `queue-view.md` regenerated

## Follow-Ups

- L3-1 (abutting-paragraph lead-in, `:70-71`), L3-2 (fence grammar), L3-3 (setext and list paragraphs) and the two inline templates `functional-review.md:90` and `:559` that the scanner cannot see are all one surface: the review-contract scanner and its documents. All minor or info, none blocks. Carried as a Watch in `epic.md`; a fix plan is staged only on the operator's word, and by the operator rule of 2026-11-11 it would be one plan for the scanner surface, not one per defect.
