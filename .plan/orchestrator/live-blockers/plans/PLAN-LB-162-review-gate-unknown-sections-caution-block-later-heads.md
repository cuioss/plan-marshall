# PLAN-LB-162: The review gate never stops on a section name it has not seen, reads the CAUTION-shape block, and carries an operator selection to later heads

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Plan A of the module regrouping of 2026-11-18: everything here lives in the review gate and the runbook lane, so the plan runs in parallel with plans in other modules.

## Objective

`runbook_lane review-gate` decides from a CodeRabbit review body by recognising its sections. Three defects share that parser and its documents, and the operator wants them closed in one plan, the first of them first because it blocks merges now:

1. **An unseen section name stops the gate for good.** The gate knows a closed set of findings sections and a closed allow-list of eight non-finding titles; a `<summary>` title that declares a count and is in neither is refused as `unreadable review-body section` (`undecidable_read`), and the review body never changes, so every re-run answers the same. A consumer repository (pm-mcp-core, PR #496) was left open on a `<picture>`-prefixed `Minor comments: 25` heading, and the same stop already happened for two other titles (#1952, #1971), each cured by one more allow-list entry. The fix is the design, not a ninth entry: an unrecognised counted title counts as findings that must be disposed of.
2. **A CAUTION-shape block reads as zero findings.** A review body whose outside-diff finding rides a `[!CAUTION]` block under a BOLD heading, with the finding itself as a `<summary>` row that declares no count, is counted as nothing (#1983: one Major finding read as `0`; the same shape on #1984). A review whose findings all ride in such a block reads `all_handled` and the gate admits the merge with them undisposed.
3. **A selection the operator made at one head has no stated reach.** The operator ruled on 2026-11-18 that such a selection covers the heads pushed after it as long as they add no new logic, and the lane skill does not say so.

The minors of the PLAN-LB-152 landing in the same two files ride along, by the operator's rule that minors ride only a plan already editing their files.

## Deliverables

1. An unrecognised counted section title no longer refuses the gate. In `runbook_lane.py` the review-body parser branch that returns `unreadable review-body section` for a `<summary>` title that declares a count and matches neither a findings section nor a non-finding label instead counts that title's declared count as findings of kind `unclassified`, numbered per reviewer like every other section (`unclassified-1`, `unclassified-2`, …), so the gate answers `merge_allowed: false` with reason `body_findings_undisposed` until each is disposed of through the same disposition ledger every other finding uses, and `all_handled` once they are. `minor comments` joins the findings table as its own kind (`minor`), so a `<picture>`-prefixed `Minor comments: 25` is read as 25 findings of that kind and not as unclassified. The allow-list of non-finding titles is unchanged, a title that declares no count is ignored exactly as today, and every other `undecidable_read` cause (a failed read, a truncated read, an entry that cannot be flattened) is unchanged. The verdict list in `runbook-lane/SKILL.md` that names the refused title as a stop and the module's own docstring state the new reading.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
2. The CAUTION-shape block is read. A section heading carried by a BOLD line (`**⚠️ Outside diff range comments (1)**`) is read as a heading, and the finding rows of the `<details>` that follows it, whose `<summary>` titles read `Major · … · <code>file:line</code>` and declare no count, are counted as findings of that heading's section. A body in the ordinary `<summary>`-heading shape is read exactly as before. Against the captured bodies of #1983 and #1984 the outside-diff finding is counted (#1983: one finding where the gate read zero; #1984: the seven inline findings plus the outside-diff one), and a review whose findings all ride in such a block no longer reads `all_handled` without dispositions.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core
   - Persona: implementer
3. The reach of an operator selection is stated in the lane's merge gate. `runbook-lane/SKILL.md` section 7 states that a selection the operator made at one head (for example "merge without reviewer X") covers the heads pushed after it provided those heads add no new logic, and that a later head the lane cannot classify as free of new logic is put to the operator again (the default fails closed). The outline defines "no new logic" operationally, from what the lane can read (the diff between the selected head and the merge head), names its test and the reason for it, and adds a lane-side check only if the document alone cannot state a testable rule; the standing-authorization paths (a qualifying CodeRabbit review on record, every finding handled, one re-trigger after the last push) are unchanged and never asked about. The two earlier rulings are inputs, restated here because the lane does not read the ledger: on 2026-10-23 the operator ruled "keep the standing authorization as written; the plan tries to get a re-review of the later head and asks the operator when the quota prevents it", and on 2026-10-25 that a last head that changed logic after the qualifying review is covered by the standing authorization and nothing is asked.
   - Skills: plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture
   - Persona: documenter
4. The minors of the PLAN-LB-152 landing in these files are closed. (a) The module docstring of `github_re_review.py` says both discriminators "append every refusal they skip" while its own later paragraph says a skip ahead of the refusal test is dropped with no record; the first statement is corrected to agree. (b) `runbook_lane.py` gives a read whose `complete` key is absent its own detail instead of "the review surface read was truncated: not every connection was drained", a cause that did not happen, and the test that pins `'truncated'` follows. (c) The reason-list pin in `test_runbook_lane_review_gate.py` reads only the paragraph after "It answers `merge_allowed: false`", so a stale reason in the provider paragraph of `SKILL.md` would pass; the pin covers both. (d) The refusal-record ordering CodeRabbit raised on PR #1992 is closed only if the outline can name it from that thread (verify-at-outline); otherwise it is dropped with the reason recorded.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
5. Tests pin deliverables 1 to 4, each written against the unfixed tree first. A body with a `<picture>`-prefixed counted `Minor comments: 25` title reads 25 findings of kind `minor`; a body with a counted title in neither table reads that count as `unclassified` and answers `body_findings_undisposed`, then `all_handled` once each is disposed; a counted allow-listed boilerplate title still contributes nothing; the CAUTION-shape fixtures built from the real #1983 and #1984 bodies are counted as deliverable 2 states; the section-7 text pins the selection rule; the docstring correction, the missing-`complete` detail and the two-paragraph reason pin are tested. Fixtures follow the existing `_github_pr_fixtures.py` convention and are captured from real bodies where reachable, hand-built only where not, and a hand-built one says so.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester

## Standing Constraints

- The gate stays fail-closed everywhere it is today. Deliverable 1 turns a stop into a count of findings that still block until disposed; no change makes an unreadable review pass, and `undecidable_read` stays for a failed, truncated or unflattenable read.
- Deliverable 1 mints `unclassified` findings only for a title that declares a count; a title with no declared count is ignored exactly as today, and the boilerplate allow-list gains no entry unless a captured body shows a title that is boilerplate.
- Order inside the plan: deliverable 1 first, because it unblocks consumer merges; deliverables 1 and 2 edit the same parser function, so they are sequential.
- No file outside the review gate and the runbook lane is touched: `plan-orchestrator/workflow/analyze.md` (which still says `review-gate` reads `ci pr comments`) belongs to another module's plan and stays as recorded.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Recorded and not changed by this plan: the `bot_registry` summary patterns, the other findings-section kinds, and the minors of the PLAN-LB-136 and PLAN-LB-148 landings.
- Scope-bloat note: five deliverables, under the presumptive-split guard; deliverable 4(d) is dropped, not widened, when the outline cannot name it.

## Claim Labels

- OBSERVED (re-read at `48a72b527`): the findings section table holds `actionable comments`, `inline comments`, `duplicate comments`, `outside diff range comments`, `outside-diff comments`, `nitpick comments`, `nitpicks`, `follow-ups`, `followups` and `additional comments`, and no `minor comments` — `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` § `_REVIEW_BODY_SECTIONS`, lines 2120-2131.
- OBSERVED (re-read at `48a72b527`): `_SUMMARY_RE` matches `<summary>` tags only (line 2189) and `_COUNT_SUFFIX_RE` reads a trailing `: N` only when whitespace follows the colon (line 2195).
- OBSERVED (re-read at `48a72b527`): `_NON_FINDING_SECTION_LABELS` is a closed list of eight titles, two of them observed on #1952 and #1971 as counted `<details>` blocks with a `<picture>` icon wrapper — `runbook_lane.py` lines 2149-2167; its comment says a counted title that is none of these "is refused rather than declared away".
- OBSERVED (re-read at `48a72b527`): the parser returns `[], 'unreadable review-body section: …'` for a counted title that is neither a findings section nor a non-finding label — `runbook_lane.py` lines 2464-2467.
- OBSERVED (re-read at `48a72b527`): `github_re_review.py` line 98-99 says both discriminators "append every refusal they skip", and lines 121-123 say a skip that a gate ahead of the refusal test drops "is skipped with no record".
- OBSERVED (re-read at `48a72b527`): a read whose `complete` is not `True` returns detail "the review surface read was truncated: not every connection was drained" — `runbook_lane.py` lines 2765-2771.
- OBSERVED (ledger, reproduced on #1983 by the PLAN-LB-148 landing, re-read here only at the code): the section table and `_SUMMARY_RE` read a section by a `<summary>` title only, so a section heading carried by a bold line is not read.
- HYPOTHESIS: the pm-mcp-core report that `Minor comments: 25` is the title the gate cannot map is accurate — it comes from another repository's orchestrator through the operator and the body was not read here; confirm against a capture of PR #496 if reachable, otherwise against a hand-built body that says so (verify-at-outline).
- HYPOTHESIS: a `Minor comments (N)` section holds findings and is not boilerplate — confirm from the captured body (verify-at-outline); a refutation moves the title to the allow-list instead and deliverable 1's `unclassified` rule is unchanged.
- HYPOTHESIS: the captured bodies of #1983 and #1984 are still readable through the CI abstraction's read verbs — confirm at outline; a refutation makes the fixtures hand-built and the spec says so.
- HYPOTHESIS: a lane can read the diff between a selected head and the merge head and classify "adds no new logic" from it — confirm at the lane's read seam (verify-at-outline).
- Verify-first clause: the outline settles (a) the real shape of the `Minor comments` title and whether it holds findings; (b) how the disposition ledger names an `unclassified` finding so a disposition discharges exactly one; (c) the operational test of "no new logic" for deliverable 3 and why; (d) whether the CodeRabbit ordering point of 4(d) can be named.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py`
- OBSERVED: `test/plan-marshall/workflow-integration-github/_github_pr_fixtures.py`

## Dependencies and Sequencing

- Depends on: none (PLAN-LB-148, -152, -160 and -161 are shipped).
- Overlaps with: none staged or running; the other plans of the 2026-11-18 regrouping (functional-review verdicts, build-server logs, project hygiene) touch other modules and no path of this surface.
- Adjacent to: `plan-orchestrator/workflow/analyze.md` line 155 (the stale "from `ci pr comments`" statement), left to the project-hygiene plan, and `runbook-lane/SKILL.md` line 710 ("Open the `log_file` it names"), which the build-server plan does not need to change.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-162-review-gate-unknown-sections-caution-block-later-heads.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
