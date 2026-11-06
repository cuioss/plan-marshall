# Landing Analysis: PLAN-LB-107 — the merge gate accepts what the finalize dispatcher accepted, and the push gate reads a build's real scope

epic: live-blockers
workstream: WS-01
pr: #1920

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-107.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `1d2b559fd1a3f56a1a755788d7e144c4914dbd7f`, a squash commit with ONE parent, `75b5780d0b70361415b0d5373a17b731c8f623d2` (the merge of PLAN-LB-118, read with git and named in the leaf prompt). Landing message `rb-lb-107-finalize-gate-waiver-and-step-truth-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; `unknown` is an unobserved fact and not a zero; out of scope under the focus rule); its surface delta is `unmeasured` (neither surface supplied), so the surface was read from the diff: 9 files, +1042/−79 (`git show --stat 1d2b559fd`). The lane reports 5 of 5 deliverables met, `self-review: clear` after three rounds, a spec read from the ledger copy. The merge is the lane's claim for CI and reviews; git confirms the squash commit and its subject.

Surface against the spec's Expected Surface: every touched path is declared except `manage-tasks/SKILL.md` (a documentation edit the lane disclosed and I read as justified by D4). Two declared paths were not touched: `_cmd_merge_authorization.py` (declared read-only) and `_cmd_pre_commit_verify_freshness.py` (a hypothesis the lane refuted). No verb or flag was added (`git diff 75b5780d0 1d2b559fd -G 'add_parser|add_argument' --stat` is empty, orchestrator), so no executor regeneration is owed.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the merge gate honours the re-fire waiver at the candidate head | shipped | The waiver row requires `outcome == done` and `waiver_head == head` (full SHA, the candidate resolved once), is judged per step, and the dispatched payload carries `waived_steps` with the waiver head and `basis` (`pre_merge_gate.py:452-463, :1628-1629`, leaf; `:452-463` re-read). The abbreviated-SHA test case cannot detect a regression of the full-SHA check (L2-1). |
| D2 — head-dependence from the dispatcher's source | shipped-modified, with a fail-open lead (L3-1, L1-2) | The gate delegates to `_cmd_mark_step._derive_head_dependence` (`pre_merge_gate.py:313-338`, re-read) and lists an undeclared stale step instead of refusing it (`:445-451`, re-read). A step that discovery cannot see reads as undeclared and is admitted (L3-1). |
| D3 — the prompt is built from the labels the grant accepts | shipped | `override_options = list(BARRIER_OVERRIDE_LABELS)`, imported and not copied (`pre_merge_gate.py:1109-1120`, re-read); the import fault is swallowed silently (L3-3). |
| D4 — a build row is whole-tree only when its scope is | shipped-modified, with a regression lead (L1-1) | A known scope flag is read as scope and any other flag makes the row unreadable (`_freshness_crosscheck.py:630-669`, re-read). The Done-when shape `module-tests -pl` is never emitted by the Maven resolver (L1-4). |
| D5 — a doc-side producer guard | shipped | The guard asserts a non-empty producer set and the mutated copy turns it red (leaf, `test_verification_feedback_producer_vocab.py`); green at HEAD is not shown by reading. |
| not a deliverable | not measurable | `landing-check` surface delta `unmeasured`; read from the diff as above. |
| executor regeneration | corroborated | The `add_parser|add_argument` diff is empty. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing at the merge commit (its `HEAD` equalled the merge); the orchestrator re-read the points marked `re-read` at their `file:line` in the same tree. It was a reading only: no build, no test run, no write. The leaf skipped the dispatcher's logging writes on the no-write rule.

- **Dispatch:** one read-only leaf per landing — the read crosses 9 files and four large test files, with 15 narrative claims passed one by one.
- **Verdict:** layer 1 findings (two major, one carried as lead; minor, info); layer 2 findings (one claim partly refuted, two claims confirmed as worded but not in effect, minor); layer 3 findings (**one major**, minor, info). No blocker.
- **Orchestrator re-read:** L1-1 (parser and the verdict classification), L1-2 and L3-1 (both readers and the gate loop), L2-1 (test line; the value of `HEAD_MERGED` was not read), L2-3, L3-3, and C1. Every other row is a lead the leaf checked and I did not re-read.
- **Regrades.** The leaf graded L1-2 `major` as its own finding; I carry it with L3-1 as one defect, because L1-2 is the cause (the spec orders a reader that cannot tell "undeclared" from "not discovered") and L3-1 is the effect.
- **Prompt check.** The 15 narrative claims went into the prompt as separate items; nothing here rests on a merged clause.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 (major lead, code re-read; reach not settled) | D4 says "any other flag after the canonical command makes the row's scope unreadable", and the standing constraint says an inability passes and a refutation fails closed. A row `run --command-args verify plan-marshall --format json` was read by the old parser as scope `plan-marshall` and could refute a whole-tree change; now an unknown flag returns `None` (`:634-638`), the row is `ROW_ARGS_UNREADABLE`, and a list in which every row is an inability is `UNDETERMINED` with reason scope-unreadable (`:950-960`). The leaf reads that as a push-gate pass, and also reads the reverse (a whole-tree `verify --timeout 900` beside a narrow row used to be covered and is now narrow). Whether the push gate passes `UNDETERMINED` is the module's documented direction and I did not re-read the consumer. How often a real row carries a trailing executor flag is the open question: the leaf cites `extension-api/standards/build-execution.md:400` (`--command-args "verify" --format json`) as a documented call shape, not re-read. The spec ordered this reading, so the root is the spec's pair of rules. | checked (parser, classification); consumer and reach not read | `_freshness_crosscheck.py:634-638, 695-729, 950-960` |
| L1-2 (major, with L3-1, re-read) | D2 requires the reader `_derive_head_dependence` AND that "an underivable declaration never widens". That reader returns `(False, None)`, "resolved, undeclared", for a step absent from the discovered population (`:240`; the docstring at `:205-209` says this is deliberate because phase-5 steps legitimately match no finalize-step implementor), so the fail-closed fallback fires only when the machinery could not run at all. The sibling reader in `verdict_currency.py:362` returns `REASON_STEP_UNRESOLVED` for the same input (leaf, not re-read). | checked | `_cmd_mark_step.py:203-240` |
| L1-3 (minor, leaf) | D1(a) and D2(a) are `mutation-after` in the narrative; the spec says "Red at HEAD". By reading, both tests are red against the parent (its `merge()` already accepted the seams the tests pass, and its field-presence logic refuses). The actual red run is not shown by reading. | checked (leaf) | `test_lb55_merge_head_binding.py` (`_merge_pre_seam`, D1(a), D2(a)) |
| L1-4 (info, leaf) | The Maven resolver emits `test -pl X -am` or `package -pl X -am` for module-tests and `verify -pl X -am` for verify and quality-gate, never `module-tests -pl`. The false green that is real is `verify -pl X -am`; no test runs that row through `cross_check_candidates`. | checked (leaf) | `_maven_cmd_discover.py:917, 925-926, 938-943` |

**Layer 1 verdict:** findings — two major (one lead on its reach, one confirmed with L3-1), one minor, one info.

### Layer 2 — Implemented

- **Confirmed (leaf):** C1 (re-read at `pre_merge_gate.py:452-463`), C3, C6 (the classifier admits only `status == success` and `verdict == preserved`, `:464-466`, re-read), C8 (re-read), C9, C10, C11, C15 (the `verdict_inputs:` search covers the inventoried tree; project-local `.claude/skills/finalize-step-*` is outside it and was not searched).
- **C2 confirmed in code, one test case proves less than it claims (L2-1, minor, test line re-read).** The `abbreviated` case uses `'abc1234'` (`test_lb55_merge_head_binding.py:225`); the leaf reads `HEAD_MERGED` as `'b' * 40` (not re-read), so it is refused by plain inequality. Removing the full-SHA predicate or turning the comparison into a prefix match would leave every parameter green. A distinguishing input is `HEAD_MERGED[:7]`.
- **C4 and C5 hold as worded and not in effect for an undiscovered step.** "Same discovery path" is true; "cannot disagree with the dispatcher" and "never widens" are false for a step discovery cannot see (L3-1). The matched control D2(b) goes through a stub, not the production reader.
- **C7 code confirmed, the defect premise is not shown by reading.** `_read_plan_status` now calls the JSON resolver (`pre_merge_gate.py:217-239`, leaf). Nobody read the TOON parser's key splitting; the namespaced-key test monkeypatches the resolver, so it proves the JSON passes through and not that the TOON defect existed.
- **C12 partly refuted.** The unchanged-files claims hold (no change to `_cmd_loop_back.py`, `_cmd_mark_step.py`, `_cmd_merge_authorization.py`, `phase-6-finalize/SKILL.md`, `required_coverage`). "The new reads are bounded by `_VERB_TIMEOUT_SECONDS`" holds for the classifier only (`:348`, default 300). The status read and the discovery read run in process and are not bounded by it; one classifier call per stale declared step means up to N×300 s while the merge mutex is held (leaf, not re-read).
- **C13 partly satisfied.** All five tests can fail against the parent by reading; `mutation-after` is evidence of a different kind from the spec's "red at HEAD" (L1-3).
- **C14 (the lane's residue):** (a) leaf-only, the "outside the vocabulary" fact was not read; a narrow Maven `test`/`package` row is then an inability that passes, as before this change; (b) a trailing executor flag turns a formerly narrow row into an unreadable one, which is L1-1 and a regression for that shape, and the claim "never credited as whole-tree" holds (`:634-638`, re-read); (c) the `-am` reading is stricter than the spec's literal text and stricter than before (`_freshness_crosscheck.py:353-366, 662-668`, `:662-668` re-read); (d) `manage-tasks/SKILL.md` is a documentation sync for D4 (leaf).
- **L2-2 (minor, leaf):** `test_pre_merge_gate.py:1658` hand-lists a count (`== 2`) beside a list-equality assert that already proves it.
- **L2-3 (minor, re-read):** an existing control was inverted (`verify --timeout 900` from `('verify', ())` to `None`, `test_freshness_notation_crosscheck.py:699`). It carries a comment, but the comment says "fail-closed" (`:698`), and the code path is an inability (`:950-960`).
- **L2-4 (minor, leaf):** the classifier's error, timeout and unknown-verdict arms have no test; only `preserved` and `invalidated` are parametrized. The code fails closed by reading.
- **L2-5 (info, leaf):** the lane added a `records_facts: head_binding_waived` fact and fact-table rows beyond D1; no test shows `record-merge` accepts it (`_fact_map` not read).
- Red-at-base and green-at-merge per test were established by reading, not by a run; the lane's per-head runs are its claim, `not_shown_by_reading`.

**Layer 2 verdict:** findings — one claim partly refuted (C12), two confirmed as worded and not in effect (C4, C5), one premise not shown (C7), four minor, one info.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read; how often discovery misses is leaf-only) | `_cmd_mark_step.py:234-240`; `pre_merge_gate.py:445-451` | A stale record in `phase-6-finalize` for a head-dependent step that `find_implementors` does not return in the gate's process (a `project:finalize-step-*` whose project root does not resolve from the gate's cwd, an opt-in bundle step missing from the cache, a step renamed since the record was written) | `records` is non-empty, no name matches, the reader returns `(False, None)`; the gate files the step under `unconsulted_stamps` and the merge DISPATCHES. Before this change that record was refused as `merge_candidate_not_gated`. This is the widening D2 forbids ("an underivable declaration never widens"); the cause is the spec's choice of reader (L1-2). The anti-vacuity tests pin `functional-review` and `finalize-step-sync-baseline` only; no project-tier or bundle-tier declared step is pinned. Leaf, not read: if `_read_frontmatter_fields` returns `{}` for an unreadable doc instead of raising, a corrupt head-dependent doc also reads as undeclared. | major |
| L3-2 (leaf, not re-read) | `pre_merge_gate.py:393-395, 437-441`; `branch-cleanup.md:838` | A declared step with `outcome == done` and no `head_at_completion`; a declared step with a failed or loop-back outcome whose head equals the candidate | The new sentence says the offending set equals the steps the dispatcher would re-fire. The dispatcher re-fires the first and retries the second (`phase-6-finalize/SKILL.md:612-614`); the gate skips the first (`:437-439`) and admits the second at `:441`, before any outcome check. Both behaviours predate this change; the sentence asserts the equality anyway. | minor |
| L3-3 (re-read) | `pre_merge_gate.py:1115-1118` | The `BARRIER_OVERRIDE_LABELS` import fails | `except Exception: pass` drops `override_options` without a word, and the document tells the agent to build the prompt from that field, so the agent falls back to prose, the drift D3 closes. A silent swallow against the code rules. | minor |
| L3-4 (leaf, not re-read) | `branch-cleanup.md:1659` | A merge that passed with `unconsulted_stamps` or `head_dependence_fallback` | The text says the step record must keep all three visible, but only `waived_steps` gets a recorded fact, and that one depends on the agent following prose. After the merge nothing persistent shows a pass on an unconsulted stamp or a fallback. | minor |
| L3-5 (leaf, not re-read) | `pre_merge_gate.py:230-237` | An import or resolution fault in the in-process status read | `None` is returned, the head binding admits with an empty evidence payload, and nothing records that the status was unreadable. The unknown-passes design predates this change; the in-process import surface is larger. | minor |
| L3-6 (leaf, not re-read) | `pre_merge_gate.py:445, 464` | Several stale steps under the merge mutex | Each stale step re-runs a full discovery scan, uncached and not bounded by a timeout, and each declared one spawns a classifier call of up to 300 s that, with no shipped `verdict_inputs`, can only answer `invalidated` (C15). | minor |
| L3-7 (leaf, not re-read) | the four test files; `branch-cleanup.md:838`; `pre_merge_gate.py:225-226, 401` | — | Plan-id headers (`PLAN-LB-107 D1–D5`) and history wording ("used to ignore the waiver", "which is how a head-dependent step could be missed") in current-state text, against the epic's documentation rule. | minor |
| L3-8 (leaf) | `manage-status/SKILL.md:504` | A third reader of the waiver | "There are exactly two readers … No other reader exists" is an absolute claim no guard enforces; accurate at HEAD. | info |

**Layer 3 verdict:** findings — one major (L3-1), L3-2 to L3-7 minor, L3-8 info.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing `fab8940ea` (two inline findings and one nitpick, fixed in `68afe7605`) and `226417602` (one major outside-diff finding, namespaced step keys lost in the TOON status read, fixed in `c50854071`, and one trivial note), refusing on quota after the last push, and the standing authorization applied. Sourcery (optional) refused on its budget. I read no review body, no PR body and no CI output: the review history, the CI result and the merge-queue path are the lane's claim and are `not_shown_by_reading`; so is the premise of the outside-diff finding (C7). Git confirms the squash commit `1d2b559fd` and its subject. The lane's account of one `verify` that hit the daemon's supervisory bound and one load-induced module-tests timeout is its own.

## Residue and Watches

- L3-1 and L1-1 want a fix plan; it is staged on the operator's word only. They sit on `pre_merge_gate.py`, `_cmd_mark_step.py`, `_freshness_crosscheck.py` and their tests; whether a running or staged plan declares any of them was not checked, and `corpus cross-check` reads it when a plan is cut.
- Settle first at that plan's outline: whether the push gate passes an `UNDETERMINED` freshness verdict (L1-1), how often a real build row carries a trailing executor flag, and whether discovery misses a head-dependent step in a real finalize run (L3-1). The ordering matters: if discovery never misses, L3-1 closes to a documentation line.
- The fix chain: this is the fourth landing in a row (PLAN-LB-114, 117, 118, 107) with a layer-3 fix owed. The shape repeats from PLAN-LB-118: a spec rule ("never widens", "an inability passes") is stated and a second rule in the same spec makes it unreachable.
- Parked PLAN-LB-46 declares `branch-cleanup.md` and `manage-status/SKILL.md`, and parked PLAN-LB-75 declares `test/plan-marshall/phase-6-finalize/`; both are on this merge's surface, so re-ground them before either is un-parked.
- The running PLAN-LB-110 (Maven consumer test truth) shares the Maven build row shape with D4 (`-pl X -am` rows); whether its deliverables interact with the new reading is not checked.
- Harness sync is owed outside this plan, operator-run.
- The `landing-check` gap on `total_tokens` is out of scope.
- The lane's rule check (no shell file operations, one misplaced router flag refused by the executor, one `worktree-create` retried after a shell timeout, the guard's audit log unreadable after cleanup so the guard-refusal count of zero is the lane's own account) is its own and is not re-read.
