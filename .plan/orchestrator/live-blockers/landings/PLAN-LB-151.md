# Landing Analysis: PLAN-LB-151 — handle-open-verb

epic: live-blockers
workstream: WS-03
pr: #1987

> Landing record for one shipped plan. Merged as `2f0630bc02f69b5681f76756980a714016239357` (parent `aaa06bf44`) through the merge queue; twenty files, +1212 −59. Lane: runbook, OpenCode harness, `rb-lb-151-handle-open-verb`. Source: the lane's inbox message `rb-lb-151-handle-open-verb-001.md`, corroborated against the merge commit's diff, the PR's review state and the merged code. `complete: false` for `total_tokens` alone (`unknown`), which is no defect under the operator's ruling of 2026-10-23.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — contract, persona exception, enumerations | shipped-modified | `## Handle-Open Contract` in `persona-plan-orchestrator/standards/orchestration-model.md`, attribute 9, the Terminal-Title list gained `handle-open` with the count word `thirteen`, and the Dispatch index grew to nine. One file outside the declared surface, `test_cleanup_contract.py` (`_NUMBER_WORDS += 'thirteen'`, `:149`, re-read via the leaf), which the standard's own pin requires. |
| D2 — workflow document and routing | shipped-as-specified | `plan-orchestrator/workflow/handle-open.md` (150 lines, nine steps, Inputs, Dispatch, Idempotence, Output — read in full here), the router row and Usage line (`plan-orchestrator/SKILL.md`, +2). |
| D3 — the knob | shipped-as-specified | `_cmd_orchestrator.py` (`_coerce_decision_confidence_threshold`, `_is_stored_threshold_valid`, derived `ORCHESTRATOR_SCALAR_FIELDS`), `_config_defaults.py` (`DEFAULT_ORCHESTRATOR` seeded 90, `validate_orchestrator_block`), the six knob documents (diff read). The Done-when's "fresh seed returns `set: false`" is unsatisfiable (L1-3); the lane implemented the deliverable body's "unset field" wording. |
| D4 — pins | shipped-modified | `test_handle_open_contract.py` (598 lines, 20 live pins, 11 controls), four manage-config modules, the dispatch pin brought to nine. Two overclaims (L2-1, L2-2). |

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`), and the orchestrator re-read the points recorded below as re-read. By reading, no build, no test run, no write. The leaf had no Grep or Glob and used `git show`/`git ls-tree` and whole-file reads; every tree-wide negative it could not sweep is listed as not checked.

- **Dispatch:** one read-only leaf for this landing — reason: the rule dispatches every full ship, and one landing's read does not share context with another's.
- **Verdict:** layer 1 findings (3 minor); layer 2 findings (2 minor); layer 3 findings (1 major, 6 minor). No blocker.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | D1 says `test_cleanup_contract.py` group (b) holds against the edited standard, and the declared surface omits that file; with the edited standard on base, (b) fails on the count word | checked | refutes | `test_cleanup_contract.py:326-338` (leaf only) |
| L1-2 | D1 says the Terminal-Title list entry "fails at base"; no pin can fail there, because the only pin is agreement with a router row that does not exist at base | checked | refutes | `orchestration-model.md:187` (leaf only) |
| L1-3 | D3 says `get` on a fresh seed returns `set: false`; the seed materialises the key | checked | refutes | `test_config_defaults.py:1116` (leaf only); the seeded-block comment in `_config_defaults.py` states every knob appears in the seeded file |

All three are authoring defects of this orchestrator's spec; the lane disclosed L1-1 and L1-3 and implemented the deliverable body's wording. The spec of a shipped plan is not a staged spec, so no `corpus set-verdict` call is made.

**Layer 1 verdict:** findings — 3 minor (spec-owned).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | the standard, persona, `test_cleanup_contract.py` | `TestContractPresence`, `TestVerbEnumerationAgreement` | `test_cleanup_contract.py` (disclosed) | checked |
| D2 | `handle-open.md`, `plan-orchestrator/SKILL.md` | groups (a)-(f) | none | checked |
| D3 | `_cmd_orchestrator.py`, `_config_defaults.py`, `manage-config.py` | the four manage-config modules | none | checked |
| D4 | the new module and the dispatch pin | the controls | two overclaims below | checked |

Unborne claims: L2-1 the PR says the module pins "per-source and per-kind populations", but `_POPULATION_LINE_RE` matches `sources[…]` only (`test_handle_open_contract.py:118`, re-read) and nothing pins `kinds[]`; L2-2 the spec's "carries the eight prohibitions" is not pinned as a count — the population is read from the contract and only checked non-empty and unique (`:389-393`, re-read), so a prohibition dropped from both the standard and the workflow leaves every pin green. The test-first failing runs are run claims and cannot be shown by reading. The leaf found every other claim of the lane's report borne out, including that no `.plan/` path is in the diff.

**Layer 2 verdict:** findings — 2 minor.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `handle-open.md:20` and `:117-146`; `test_handle_open_contract.py:60` | the Dispatch bullet says the leaf loads this document and the test pins `--workflow` to it | that document is the whole verb: Step 1 title push, Step 6 decisions and writes, Step 7 operator turns, Step 8 log/anchor/commit, and an `## Output` that is the verb report, not `proposals[N]`; a leaf that follows the loaded document gets write steps and the wrong return shape, and only the prompt's read-only instruction holds it back; the analyze leaf has a dedicated document (`three-layer-analysis.md`) and this one has no leaf document or leaf section | major (the leaf's grade; re-read here: the bullet and the Output block are as described; whether the prompt's read-only text suffices is a design judgement, not shown by reading) |
| L3-2 | `_cmd_orchestrator.py:296` | `marshal.json` with `"orchestrator": null` | `orch_block is not None` treats a present null block as absent, so `get` answers `success` with the seeded default and `set: false`; `set` on the same file errors (`:371-373`); the verb then records the threshold as "unset default" and decides against the seeded figure instead of failing closed to 100; the comment "Only an ABSENT block takes the default path" does not hold | minor (re-read) |
| L3-3 | `_cmd_orchestrator.py:355-363` | a future key added to `ORCHESTRATOR_KNOWN_KEYS` without its own coercion branch | the derived whitelist makes the final `else: coerced = raw_value` reachable, and its comment still says "Unreachable"; the key becomes settable as an unvalidated raw string, and `set` never calls `validate_orchestrator_block`; the old comment in `_config_defaults.py` kept the scalar set deliberately not derived as that gate | minor (re-read) |
| L3-4 | `_cmd_orchestrator.py:296` | a non-dict `orchestrator` block read for `auto_emit` or `parallelization_scope` | `get` changes from `success` (default, `set: false`) to `error`; fail-closed and consistent with `set`, but undocumented in `api-reference.md` and `SKILL.md`; `use_worktree` still answers `success` (its early return at `:279-288` precedes the check); whether callers of `get --field auto_emit|parallelization_scope` handle the error was not checked | minor |
| L3-5 | `handle-open.md:72` | Step 6 reads "an item whose decision changes another item's analysis is re-analysed" | names the wrong subject (the OTHER item needs re-analysis, which Step 7 `:82` says correctly); read literally the item being decided is re-analysed and the stale neighbour is presented as it is | minor (re-read) |
| L3-6 | `handle-open.md:98-100`, Steps 6/7 | an unresolved question that lives in the anchor itself | the word-diff guard needs the BEFORE value, only implied by "read it first"; Steps 6/7 "mark the item in place" for an anchor-sourced question with no defined write path (the anchor is written only by Step 8), so the Idempotence marker has no defined form there | minor |
| L3-7 | `test_sync_defaults.py` | an operator-set `0` | `_deep_merge_missing` backfills on key presence, so `0` survives (code is right); the test that claims two arms uses `100` and never `0` | info |

**Layer 3 not shown by reading:** callers of the changed `get`; the argv of the `manage-logging` and `manage-status` calls in Step 8 against their parsers (the same form is in `decompose.md`); whether `get_default_config()` deep-copies `DEFAULT_ORCHESTRATOR` before `sync-defaults` assigns it; a tree-wide sweep for another document restating 90 or the cap rule (the leaf read only the twenty changed files).

**Layer 3 verdict:** findings — 7 (1 major judgement, 5 minor, 1 info). The three validators (CLI coercion, stored-value check, block validation) agree on every input the leaf tried (`+5`, `-0`, `0090`, `1_0`, non-ASCII digits are accepted and normalise to an int in 0..100; bool, float, over-range and over-long strings are refused).

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| `CLAUDE.md` Documentation Standards | no timestamps | deviates | `handle-open.md:142`, the Output example carries `## Decisions entry of 2026-11-10` (re-read) |
| `CLAUDE.md` Documentation Standards | current state only; no duplication | conforms | the threshold semantics are stated once in `data-model.md`, the cap rule once in the standard |
| spec | one definition per concept (the default 90 in `DEFAULT_ORCHESTRATOR`) | conforms | `data-model.md` restates the figure four times (two examples, the default table, the seeded shape), one more than the comment in `_config_defaults.py` names |
| spec | fail closed | deviates | L3-2 |
| spec | the verb decides nothing about work | conforms | the eight prohibitions are named in the standard and in Step 6; no step stages, emits, transitions, lands |
| execution-context dispatcher contract | a leaf runs only the loaded document's steps and returns its declared TOON | deviates | L3-1 |
| spec | the PR states executor and harness-sync status | conforms | "no executor regeneration is owed", "a harness sync is owed" |

## Metrics and Anomalies

- Tokens: `unknown`.
- Duration: not supplied.
- Anomalies: one earlier `verify` failed on a parallel-only race in `test_target_tree_foundational_skill_freshness.py` (its module-scoped fixture runs `pw generate --target all` per xdist worker into the same `target/`); the lane reports it passes standalone and no file it exercises is in the diff. That race is pre-existing and was not analysed here. Guard refusals: two (a shell `cp --parents`, a `grep -rn`), both redone with the sanctioned tool. The lane asked the operator twice (the dirty `uv.lock`; one more self-review round at the three-round limit) and was answered.

## Routing and Merge Behavior

- Review: CodeRabbit (required) reviewed two to three times, 10 body findings, 10 fixed and every thread replied to and resolved; four quota refusals with the 90-minute wait before each re-trigger and one escalated `full review`, accepted. Sourcery (optional) refused on its quota. Self-review ended `budget-exhausted` after four rounds, the fourth on the operator's word; the two remaining items are spec-owned (L1-1, L1-3).
- Re-read against the provider on the merged head: `runbook_lane review-gate --pr-number 1987` returns `unresolved_review_threads: 0` and `review_body_findings_total: 10`, both equal to the landing's. `review_body_findings_handled` is **not re-verified** (the gate without the run's dispositions reports 0 handled, which is the absence of its input).
- CI/merge: green on every pushed head; merge queue run `43664413631` success; `2f0630bc0`.
- Sonar: `n/a`.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1987`
- [x] row `landing` stamped `landings/PLAN-LB-151.md`
- [x] row `plan_marshall_plan_id` stamped `rb-lb-151-handle-open-verb`
- [x] epic.md narrative reconciled (the Watch for the minors, a Decisions entry)
- [x] inbox message archived
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- The verb is not in the loaded plugin cache (0.1.2123); `/apply-changes` is how this machine gets it, and the knob reaches an existing `marshal.json` through the steward's `upgrade` (`sync-defaults`). No executor regeneration is owed.
- L3-1 is the one item worth an operator decision; L3-2 to L3-6 are one Watch with the minors of PR 1986. No plan is staged without the operator's word; if the operator wants one, its natural content is: a leaf section or leaf document for `handle-open`, the null-block case in `get`, the stale comment and the guard on the raw branch, the Step 6 subject, the anchor-question marker, and the two pins (`kinds[]`, the prohibition count). It overlaps no file of PLAN-LB-152.
- L1-1 to L1-3 are authoring lessons for this orchestrator: a Done-when that says "holds at base" must name the file the pin needs, and a "fails at base" clause needs a pin that can fail there.
