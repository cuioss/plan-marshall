# Landing Analysis: PLAN-LB-138 — orchestrator staging and landing-read hygiene

epic: live-blockers
workstream: WS-04
pr: #1957 (merge commit `27f4e4b96d367d03809869ed8ed6820d642066a2`, one parent `eacede16c`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Corroborated against git: the merge is a merge-queue squash with one parent (`eacede16c`, the #1958 ledger land, read with git before the leaf prompt named it); eighteen changed paths (+2032/-272), read with `git diff --name-only`. The facts block (`pr=#1957`, `merge_state=merged`, `deliverables 3/3`) agrees with git. `total_tokens=unknown` is an unobserved fact, not a defect. `self-review:budget-exhausted` is a lane state: three rounds, 31 findings, the operator chose to proceed to the PR with six residue items recorded.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — a spaced `landing-facts` fence is read | shipped-as-specified | `_orchestrator_inbox.py:1523-1526` (leaf): the fence regex allows spaces or tabs between the backticks and `landing-facts`; `json`, `landing-factsX`, an indented fence and a fourth backtick still do not match; the facts parser is the only source that mentions `landing-facts`, so there is one reader. The lane's refusal to reuse `markdown_fence.fence_marker` is correct (`markdown_fence.py:26-28` admits up to three spaces of indentation; a landing block must start at column zero; leaf). Tests call the real `parse_landing_facts` (leaf). |
| D2 — the Done-when and Expected Surface rules, and the dropped bare filename | shipped-as-specified | the template and `decompose.md` state three rules, pinned by phrase (leaf); `epic_spec_parser.py:511-595, 756-762` (leaf) reports a bare filename with a listed suffix that is not at the repository root as `unresolved`; `marketplace/x/a.py` and `b.py` yields `('b.py',)`; the lint ships as `corpus lint-done-whens`. **The lane's "1 finding earns its keep" is not demonstrated:** the leaf re-ran the verb (142 specs, 127 with a Done-when, 1 finding) and the one finding, PLAN-LB-119, is a false positive ("keeps its tail" names the NEW behaviour that must fail at the sha). |
| D3 — the declaration is authored, filled and gated | shipped-as-specified, one undisclosed behaviour change | `Skills:` and `Persona:` child lines are in the template's `## Deliverables`; `corpus spec-skills` exists and maps paths to domain skills (live on PLAN-LB-135 to 142, leaf); the `excluded_skills` veto is applied (leaf); the reader is lifted to `script-shared/scripts/spec_skills.py` and is the SINGLE reader (below); the `next` workflow wires the check (`orchestrate.md:141-155`, re-read): admit iff `emit_allowed: true`, refuse with `missing skill: {notation}`, a spec that declares nothing passes. |

**The single-reader question (the check the anchor carried for this landing): answered, yes.** A content search finds no parser of the `Skills:` or `Persona:` lines in the bundles outside `spec_skills.py` (leaf). `runbook_lane.py` imports `spec_skills` (`:65`) and its former regex constants and helpers are gone; the two names that remain, `_skill_probe_paths` and `_skill_exists` (`:441, :446`, re-read), are one-line delegations to the shared module and have no non-test caller (leaf: only their own definitions and six matches in `test_runbook_lane.py`).

**The key emit question: a spec with no `Skills:` line is NOT refused.** `resolve_deliverable_skills` reports `none named` and `emit_allowed` is true (leaf, live: PLAN-LB-135, 136, 137, 139, 140, 141 and 142 all return `declaration: none named`, `emit_allowed: true`, an empty `missing_skills`). The workflow text says the same (`orchestrate.md:153`, re-read), so PLAN-LB-135 to 142 can still be emitted.

**Surface drift, and the report never mentions it.** Five changed paths are outside the Expected Surface: `standards/landing-payload-spec.md`, `runbook-lane/SKILL.md`, the new `script-shared/scripts/spec_skills.py` (implied by "lifted into script-shared" but not a named path), `test_orchestrator_corpus.py` and `test_flat_install_call_sites.py` (needed by the new module). Six named paths were not changed: `markdown_fence.py` (a refuted hypothesis, explained), `test_expected_surface_single_reader.py`, `test_cleanup_contract.py`, `test_orchestrator.py`, `test_runbook_lane.py` (explained by the retained wrappers) and `test_orchestrator_spec_skills.py` (its tests went into `test_orchestrator_corpus.py`; no dedicated test file exists for `spec_skills.py`). "skills: none named" is honest: the spec carries no declaration lines.

## Three-Layer Analysis

One read-only leaf (`execution-context-level-3`) read the landing with the lane's six claims passed one by one; it ran four READ-ONLY orchestrator verbs (`corpus lint-done-whens`, `corpus spec-skills` on seven specs, `corpus surfaces`, `corpus read`) against the live store; the orchestrator re-read the points marked re-read. **By reading and read-only verbs, no build, no test run, no write.**

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for.
- **Verdict:** no blocker, no major. Layer 3: four minor and several watches.

Re-read: `orchestrate.md:139-158`, the `spec_skills` call sites in `runbook_lane.py` (`:65, :436-446, :747-755, :2800-2850`), the `spec_unreadable` raise site in `spec_skills.py` (`:91-100`) and the change path list. **Not re-read** (unverified leads): the fence regex and its tests, the parser and lint code, the verb's payload code, the test bodies, the Java fixture, every job log and per-head run, the 31 self-review findings and the CodeRabbit and Sourcery histories.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D2 offers the lint's value as one live finding in 141 specs; that finding is a false positive, so the lint has no demonstrated true positive. | checked (leaf, re-ran the verb) | refutes | `corpus lint-done-whens`, PLAN-LB-119 |
| L1-2 | The spec said the lane's use of the declaration is unchanged; the lift changed it (below). | checked (leaf) | refutes | `spec_skills.py:91-100`, `runbook_lane.py:2839` |

**Layer 1 verdict:** findings — 2 (minor)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_orchestrator_inbox.py:1523-1526` (leaf) | real `parse_landing_facts` / `check_landing_completeness`, including the three bad info strings and an indented fence (leaf) | the `emit-landing.md` test only asserts the line appears in Step 2's prose, not that it is stated as the opening line (leaf) | checked |
| D2 | `epic_spec_parser.py`, `cmd_corpus_lint_done_whens` | real `classify_spec` and real fixtures; the template and decompose test pins phrases, which proves the text exists and not that it is followed; the `Skills:` template test passes on the prose mention alone, not on child lines inside the list (leaf) | none | checked, weak |
| D3 | `spec_skills.py`, `orchestrate.md:141-155` | the Python test runs the real verb against this repository's live configuration (couples the test to the repository's own data); **the Java arm monkeypatches `_configured_domains` wholesale with a hand-built dict**, bypassing the `skill-domains` parsing and the real payload shape; `TestNextConsumesTheDeclarationGate` asserts only that three words appear in Step 4 (leaf) | the new module has no dedicated test file | checked, fixture-based |

- **L2-1 (minor):** the report does not disclose that the lift changed the lane's behaviour: an unreadable spec now raises `spec_unreadable` instead of resolving to `[]`; `Skills: none` is an answered absence and is not probed; `skills_note` reads "a declaration line is present" instead of "a non-empty skill or persona list"; fences use the CommonMark mask (leaf). **The unreadable-spec change fails closed:** the lane's `resolve` catches the `ValueError` at `runbook_lane.py:2839` and returns `status: error` with that code (re-read). The leaf could not locate that handler and listed it as a watch; it is handled.
- **L2-2 (minor):** the report does not mention surface drift (above).

**Layer 2 verdict:** findings — 2 (minor)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `corpus lint-done-whens` (leaf, run read-only) | `PLAN-LB-119-review-gate-truth-fixes.md` | `fails_at_beside_preservation` flags a clause where "keeps" names the new behaviour; the heuristic cannot tell new from preserved behaviour, and misses "continues to hold", "remains" and "already"; it is report-only (`cleanup.md` Step 5), so it cannot block staging | minor |
| L3-2 | `epic_spec_parser.py` `_is_bare_file_name` (leaf, read) | `threading.Lock`, `asyncio.Lock` in an Expected Surface bullet | `casefold()` matches `.lock`, so a dotted symbol lands in `unresolved` as a fake bare filename; noise, does not change the spec's class | minor |
| L3-3 | `orchestrate.md:193, :209` and the Output section (leaf) | the `auto_emit` text and the shortfall derivation | still say "both admission tests" and list only disjointness and prep-readiness; only Step 4 carries the third (declaration) test, and the paragraph at `:157` does name it | minor |
| L3-4 | `spec_skills.py` (leaf, read) | `Persona: implementer, module-tester`, or `Skills: pm-dev-python:python-core (parser)`, or `Skills: none (...)` | `Skills:` splits on commas and `Persona:` is one token, so a comma-separated persona list becomes `persona-implementer, module-tester`, which does not exist, and an annotated value is refused; the refusal names a malformed token as a missing skill. The lane's own report lists two personas per deliverable, a likely authoring pattern. **Practical consequence for the next specs this orchestrator writes: one persona per `Persona:` line, no annotations** | minor |
| L3-5 | `_BARE_FILE_SUFFIXES` (leaf) | a bare name with `.toon`, `.jsx`, `.cjs`, `.scss`, `.proto` or no extension | dropped silently; in a spec with other claimed paths this shrinks the claimed set, so disjointness could read disjoint when it should not; the original defect in a narrower form; the template states the full-path authoring rule | minor |
| L3-6 | `parse_landing_facts` (leaf) | a quoted `landing-facts` fence at column 0 BEFORE the real block; CRLF text | the leftmost match wins; a CRLF block is unreadable; pre-existing, only a hand-built hazard because the producer puts the facts block right after a one-line headline | watch |
| L3-7 | `cleanup.md` Step 5 (leaf) | every spec with `declaration: none named` | the text says to flag them, which includes all older specs; noisy, no code enforces it | watch |
| L3-8 | `spec-skills` cost (leaf) | a spec with 49 paths (PLAN-LB-142) | one `which-module` subprocess per path plus five or six configuration reads; a timeout degrades to `unmapped`, not a gate failure | watch |
| L3-9 | suggestion (leaf) | PLAN-LB-142 | the suggestion is spec-wide: every deliverable gets the same seven skills, including SVG and narrative-style skills on a Python deliverable | watch (cosmetic) |

**Layer 3 verdict:** findings — 5 (minor), 4 (watch)

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec Expected Surface | touched paths within the surface | deviates | five paths outside it, six named paths untouched, none disclosed |
| spec standing | a fixture answer is one the real verb can give | deviates for the Java arm | wholesale `_configured_domains` stand-in (leaf) |
| spec standing | the lane's use is unchanged | deviates | L2-1, failing closed |
| lane rules | files read with the file tools | not shown | the lane reports none issued |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope. `landing-check` on this message is incomplete on `total_tokens` alone.
- Anomalies: one `module-tests` job hit the daemon's 1800 s supervisory bound and was re-run with a raised `--timeout`; no launch fault, no `killed` job. CodeRabbit reviewed `1c9f9f645` and `dd2dc7c38`, and the final head `51133025d` was rate-limited, so the merge rested on a qualifying review of an earlier head under the standing authorization (the situation PLAN-LB-142 removes).

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited), four inline findings, one nitpick and one additional, all handled with the threads resolved (lane). Sourcery (optional) refused on its own budget. Review numbers re-read with `runbook_lane review-gate --pr-number 1957`: `unresolved_review_threads` 0 (agrees) and `review_body_findings_total` 6 (agrees: four inline, one nitpick, one additional); `review_body_findings_handled` is **not re-verified** (no progress file was passed, so the verb reports 0).
- CI/merge: merge queue, squash with one parent (git); the lane's CI claims were not re-read.
- Sonar: `n/a`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-138 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-138 --field pr --value 1957`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-138 --field landing --value landings/PLAN-LB-138.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-138 --field plan_marshall_plan_id --value rb-lb-138-orchestrator-staging-and-landing-read-hygiene`
- [x] epic.md narrative reconciled against the queue rows
- [x] defect/watch opened or retired
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

(Each box is ticked only after the call it names has returned.)

## Follow-Ups

- No fix plan: no blocker and no major. **No emit is blocked by the new declaration gate.**
- **Sequencing:** PLAN-LB-137 shared `orchestrator.py` and `test_runbook_lane.py` with this plan and is now admissible.
- **Watch:** L3-1 to L3-9. L3-4 changes how the orchestrator authors `Persona:` lines from now on.
