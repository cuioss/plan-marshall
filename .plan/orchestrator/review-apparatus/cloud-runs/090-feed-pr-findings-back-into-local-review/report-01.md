# Run report — feed-pr-findings-back-into-local-review (run 01)

**Date (UTC):** 2026-08-13  **Branch:** `claude/feed-pr-findings-local-review-3589nc` (harness-assigned)  **PR:** [#1204](https://github.com/cuioss/plan-marshall/pull/1204)  **Outcome:** completed — all deliverables landed; every review comment dispositioned; auto-merge armed (SQUASH) at the gate. The squash landing is confirmed to the operator from the PR merge event, not embedded here (the report is the last pre-merge commit).

## Skills loaded

Loaded by path from the bundle source (the `plan-marshall` plugin is not installed in this cloud session):

- `plan-marshall:ref-code-quality` (+ `standards/code-organization.md`) — always.
- `pm-plugin-development:plugin-script-architecture` (+ `standards/test-scaffolding.md`) — always.
- `cloud-plan-lane` — the governing contract, loaded first.

Conditionally, by surface (Python production code + tests + a `SKILL.md`): the standards above cover the Python/test surface; no additional domain skill was required because the change is a narrow detector-predicate edit plus tests, and the `SKILL.md` edit is a one-line noun-set restatement.

## Deliverables

The plan has four deliverables (D0 gate, D1, D2, D3). Net code yield is **one widening + one documentation fix**, matching the plan's stated expectation of a small yield.

### D0 — GATE: ask "could we have found it ourselves?" over the answered-finding corpus

**The gate's environmental precondition is satisfied:** posted answers ARE readable in this run's environment (GitHub MCP; confirmed by reading review/thread/issue-comment surfaces on real PRs). The plan HALTS only if they cannot be read — they can, so the plan proceeds. The corpus was built from the **posted answers** (the observable), never from the findings ledger's internal resolutions (the forbidden substitution).

**Corpus scope (stated transparently):** the automated-review findings on a bounded recent window — PRs #1158–#1203 (the anchor-adjacent + recent-window set: 1167, 1168, 1170, 1165, 1182, 1191, 1187, 1189, 1158, 1203, 1201, 1200, 1199, 1198, 1197, 1195, 1196, 1188, 1186, 1181, 1180, 1173, 1174, 1164) — read across all three comment surfaces (review summaries, inline threads, issue comments). Registered reviewers: `coderabbitai` (coderabbit), `cuioss-review-bot` (pr-agent), `sourcery-ai` (sourcery).

**Published counts:**

| Metric | Count |
|---|---|
| PRs swept | 24 |
| PRs that produced any reviewer finding | 11 (13 produced none — dominated by CodeRabbit's per-dev review limit and Sourcery's weekly rate limit) |
| Total findings observed | 43 |
| **Answered-finding corpus** (a posted answer exists) | **30** (25 accepted/fixed · 2 rejected · 2 acknowledged · 1 other) |
| — of those, **yes** (a deterministic diff-scoped local detector could have caught it) | **3** |
| — of those, **no** (needed reading code / reasoning about intent — the reviewer's job) | **27** |
| **Unanswered findings** (a posted answer is MISSING) | **13** — reported separately below as response-path defects, not dropped |

**The three "yes" answers, and why none produced a new in-scope detector:**

1. **PR #1170 finding #8 — MD040 fenced-block language identifier** (accepted/fixed). Named detector: **markdownlint MD040** — an existing linter, not the ext-self-review registry. "We already had it," not a gap.
2. **PR #1195 finding #30 — run-report left with `Outcome: in progress` and `TBD` sections at merge** (accepted/fixed).
3. **PR #1180 finding #38 — run-report `Outcome: completed` with placeholder bodies still present** (accepted/fixed). Recurs UNANSWERED on PR #1198 finding #23.

Findings #30/#38 are a genuine, mechanically-detectable, accepted pattern — a **run-report placeholder scan** (`_pending_` / `TBD` / `Outcome: in progress`-with-real-siblings). But it is **routed out, not absorbed** (see Findings → routed-out), because these are `doc/plans/*/report-NN.md` artifacts of the **cloud-plan-lane**, and ext-self-review does **not** run in that lane — a detector added here would never fire on the very artifact that motivated it. Its correct owner is the cloud-plan-lane contract's own report-completeness gate. This is the plan's "route it out rather than absorb it because this is the file already open" discipline applied literally.

**The count-prose back-feed case is corroborated by the corpus.** PR #1167 finding #3 flagged a stale "six/seven **list flags**" count after a flag was added — a `count_prose`-archetype finding whose noun (`list flags`) sits OUTSIDE the detector's registered noun set. It is UNANSWERED (so it is also in the response-path-defect set), but it independently confirms what the plan names as "the first real back-feed case": the count-prose predicate is too narrow. This corroborates D2's widening (below).

**Anchor findings — both ABSENT from the window (reported, not hidden).** Neither named anchor was posted by any bot on any PR in the swept window:

- *Negative `--max-per-component` producing a spuriously truncated result* — not found. Confirmed from git: the flag AND its `if args.max_per_component < 0: … invalid_cap` guard were introduced together in the **same** squash-merged PR #1153 (`_lessons_query.py:232`), whose review threads are empty (Sourcery rate-limited, zero inline threads). So the fix shipped with the flag; there is **no posted PR answer** accepting it as a review finding. Under D0's evidence standard (the posted answer is the signal), it is not part of the answered corpus.
- *Duplicated disposition table* — not found. The nearest neighbours in-window are a different shape (duplicated `_pending_` headings, a duplicated finding-type *list*, stale duplicated *wording*), none a duplicated markdown *table*.

*Done-when satisfied:* every answered finding has a yes/no with a named detector for each yes; the unanswered set is reported with its size (13).

### D1 — the third answer: "yes, but it was not running" (security-shaped candidates)

**One security-shaped candidate in the corpus:** PR #1201 finding #18 — a **path-traversal / host-file-read** in `doc_references.py` `_resolve_one` (`except ValueError` set `rel` but did not return, falling through to `.exists()`/`.read_text()` on `../../../../etc/passwd`), accepted and fixed.

**Classification: activation question, NOT a detector gap.** The local review's **security audit** (`finalize-step-security-audit`, `persona: persona-security-expert`, `order: 9`) is conditionally active, and both drop paths were verified against the composer source in this clone:

- **Path A — lane-tier drop.** The step carries `lane.tier: full` (`phase-6-finalize/standards/finalize-step-security-audit.md`). Lane resolution keeps an element only when `_TIER_RANK[effective] <= _TIER_RANK[posture]` (`_manifest_lanes.py`); with `full` = rank 2, a `standard`/`minimal` posture **drops** it, recorded as `lane_dropped` (`{step, reason}`) alongside `execution_profile` (`manage-execution-manifest.py:2293-2294`). *(Framing note: the plan says "the `auto` lane drops it." The code's lane axis is the posture enum `minimal/standard/full`; `auto` is a separate axis — the ceremony-gate default `_CEREMONY_FINALIZE_DEFAULT = 'auto'`, which defers to Path B. The plan's "auto lane drops it" maps onto "any resolved posture below `full` drops it.")*
- **Path B — ceremony pre-filter drop.** `_apply_security_class_inactive` (`_manifest_rules.py:343-396`) drops the security-class step when `affected_files_count == 0` AND the live footprint is resolvably empty, recorded as `security_class_omitted` = `{step, reason}` (`manage-execution-manifest.py:2286`), reason `'no declared affected files and empty live footprint'`.

Both paths named. A path-traversal finding is exactly the security audit's remit, so it is an **activation** question (the check exists but was conditionally off), not a missing detector — and the structural detector `unguarded_boundaries` would NOT have caught it anyway (a `try` already enclosed the call, so the boundary reads as guarded).

**Per-run lane verification was NOT available** (stated explicitly, not inferred): determining what PR #1201's run actually resolved its lane to requires that run's execution manifest, which lives in the git-ignored `.plan/` tree and is absent from this clone. D1 therefore answers the **current-configuration** question (is the check active in this repo's resolved lane, and via which of the two paths could it be dropped) from the composer source, which IS in the clone.

*Done-when satisfied:* the security-shaped candidate is classified (activation-question), both drop paths named, per-run lane verification stated unavailable.

### D2 — add the detectors for the yes answers (and the widening arm)

**No new detector added.** The three "yes" answers resolve to: already-covered (markdownlint MD040), or routed-out-to-a-different-owner (run-report placeholder scan → cloud-plan-lane). Adding either to the ext-self-review registry would duplicate an existing gate or place a detector where it cannot fire on its motivating artifact.

**The widening arm — count-prose noun set + docstring contradiction (the plan's designated case).** The count-prose detector's file-scope narrowness (`SKILL.md`-only) was already fixed upstream in PR #1189 (`_collect_skill_contract_sources` now resolves `SKILL.md` + every `standards/*.md`; re-derived and confirmed at HEAD). The remaining narrowness — the **closed noun set** and the **self-contradicting docstring** — is fixed here:

- **Docstring contradiction (verified against source, then fixed).** `_self_review_patterns.py` carried the comment *"``twelve fields``, ``5 rules``, ``nine checks`` are matched"* while `_CARDINALITY_NOUNS` was `operations?|fields?|steps?|rules?|commands?` — so `nine checks` was **not** matched. The count-prose detector's own documentation was itself an unverified count claim contradicted by its own code.
- **Widening — DERIVED, not guessed.** A first-party scan of the detector's actual domain (510 skill `SKILL.md` + `standards/*.md` files, `scratchpad/derive_nouns.py`) showed the "N-<word>" following-word distribution is overwhelmingly **non-structural** (units `px`/`char`/`s`/`min`, prepositions/filler `of`/`and`/`or`/`is`, and "a single X" usages) — which is precisely why widening to "any noun" is wrong and the set must stay curated. `check` is added because it is (a) the plan's cited evidence, (b) a genuine stale-able structural-cardinality noun present in real contract sources (`phase-1-init/SKILL.md:857` — *"The two checks are ordered…"* goes stale if a third is added), and (c) the same kind of countable contract element as the existing five. The set stays **closed at six**: `operation, field, step, rule, command, check`. Adding `check` makes the `nine checks` claim TRUE — resolving the contradiction the right way ("widen the existing one and say so") rather than deleting the claim.
- Consumer sites updated in lock-step, across **four** restatement kinds: the pattern comment (`_self_review_patterns.py`), the `_detect_count_prose` docstring (`_self_review_detectors.py`), Detection Rule 14 (`ext-self-review-plan-marshall/SKILL.md`), and — caught by the verification sub-agent, one level out — the **Check 11** cognitive-review instruction that consumes the `count_prose` surface (`phase-6-finalize/workflow/pre-submission-self-review.md:301`), which enumerated the referent noun set as the old five. That fourth site is the exact beyond-diff-consumer drift this plan is about: the widening added `check` to the detector but not initially to the reviewer instruction that re-counts the referent, so a surfaced `nine checks` would have pointed the reviewer at a list omitting `check`. Fixed.

Commit: _see Deliverables → commits below._

*Done-when satisfied:* the one yes-that-produces-code has a justified widening; the docstring contradiction is fixed; the other yes-answers are recorded and routed (no new detector written where it does not belong).

### D3 — tests, each verified to FAIL pre-fix

Two cases added to `TestDetectCountProse` (`test_self_review.py`):

- **Positive** — `test_count_prose_surfaces_check_noun`: a skill doc carrying `nine checks` (the exact false-claim example), `two checks` (the real corpus shape), and `one check` (the singular form, added in response to CodeRabbit F3 to pin the singular branch of `checks?`) must all surface. Drawn from the motivating finding (the docstring contradiction) and the real `phase-1-init` instance.
- **Negative** — `test_count_prose_does_not_fire_on_nouns_outside_closed_set`: `5 deliverables`, `3 modules`, `5 checkpoints` must surface nothing — proving the set stayed closed (not "any noun") and the word boundary holds (`checks?` ≠ `checkpoint`).

**Proven discriminating by mutation** (`scratchpad/mutation_proof.py`, run and passing):

- pre-fix five-noun set → `nine checks`/`two checks` do NOT match → the positive test fails pre-fix.
- any-noun over-widening → `5 deliverables` matches → the negative test fails under over-widening.

*Done-when satisfied:* both cases exist per widened detector, each proven discriminating by mutation. (The authoritative `pytest` run is the build gate below.)

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (the two detector-source modules and the test file), so the gate is **Python** and `./pw verify pm-plugin-development` was run (scoped to the touched bundle; `UV_HTTP_TIMEOUT=600`).

**Result: SUCCESS (read from the output, not the exit code).** `2234 passed in 165.80s`, `0 failed`; coverage COMPLETE over full scope — `mypy(production)` [97 files] clean, `ruff` clean, `SPDX headers` clean, `mypy(test)` [93 files] clean; `=== verify: SUCCESS ===`. The two new count-prose tests are in the passing set (`test_count_prose_surfaces_check_noun`, `test_count_prose_does_not_fire_on_nouns_outside_closed_set`).

## Findings

### Verification sub-agent (Step 6)

An independent read-only sub-agent verified the committed diff against the plan, swept beyond the diff for stale noun-set restatements, and performed the plan's mandated cold read.

- **One real finding, fixed:** the stale **Check 11** consumer at `phase-6-finalize/workflow/pre-submission-self-review.md:301` (see D2 above). Disposition: **fixed** (commit adds `check` to the enumeration). This was a genuine miss — the in-skill restatements were updated but the downstream reviewer instruction was not — and it is precisely the beyond-diff-consumer archetype the plan targets.
- **Cold read — documentation and code AGREE within the skill directory.** From the three in-skill doc sites alone the sub-agent derived: matches `(digit|one..twenty)` immediately before `operation(s)/field(s)/step(s)/rule(s)/command(s)/check(s)` (e.g. `twelve fields`, `5 rules`, `nine checks`, `two checks`); does not match `version 3`, `5 deliverables`, `3 modules`, `5 checkpoints`. That matches the regex exactly. So the fix did **not** reproduce the docstring-vs-code defect inside the skill — the disagreement surfaced only at the Check 11 consumer one level out, now fixed.
- **All other categories clean** (named by the sub-agent): the regex and both new tests correct by inspection; the count_prose N15 schema is noun-agnostic and unaffected; no pre-existing `TestDetectCountProse` case contradicts the widening; no undeclared code collateral.
- **Stated non-verifiable-from-diff (honest bound):** D0's corpus counts and D1's manifest line anchors are analysis from evidence outside the clone; the D3 mutation harness lives in scratch (not committed) — the sub-agent confirmed D3 discrimination by regex inspection instead.

Re-verification: the single finding was a one-line documentation enumeration; the fix is self-evidently complete (the enumeration now contains all six nouns the regex matches), and a repo-wide sweep for the five-noun enumeration confirmed no other consumer site remained stale. The corrected state is re-checked against the code in the cold-read section above.

### Routed out (recorded, deliberately not absorbed)

- **Run-report placeholder scan** (D0 yes-answers #30/#38, recurs unanswered #23). Mechanically detectable and accepted, but its artifact (`doc/plans/*/report-NN.md`) belongs to the **cloud-plan-lane**, which does not run ext-self-review — so a detector here cannot catch it. **Owner: the cloud-plan-lane report-completeness gate** (a separate plan / a Step-9 "what have we learned" candidate), not the self-review registry.
- **Authoritative-set → doc-prose-list mirror drift** (D0 #20/#39, borderline). A Python `frozenset` whose members must mirror a markdown enumeration. `source_of_truth` (constant duplicated across files) and `scan_derived_keys` are adjacent but too narrow to span code-set ↔ prose-list, and a clean diff-scoped detector needs the set↔list pairing supplied (e.g. a keep-marker) — i.e. an annotation/extension point, which the stop rule puts out of scope. Recorded for a future plan.

### Response-path defects (unanswered findings — 13)

Per the plan, an unanswered finding is a defect in the response path, reported not dropped. 13 findings across PR #1167 (×4), #1158 (×2), #1198 (×6), #1195 (×1) received **no** posted answer on any surface. This is a finding of *this* exercise: the review workflow's guarantee that every finding gets a posted answer did not hold on these PRs (threads left unresolved with no triage reply, and no batched PR-level comment). It is recorded here as evidence, per instance count, for the review-apparatus epic.

### Disposition-flow evidence asymmetry (Notes — confirmed, carried)

The plan's HYPOTHESIS is **confirmed against source**: the disposition record requires **neither** a rationale nor a source at write time (`resolve_finding` validates only `resolution in RESOLUTIONS`; `--detail` is optional at the CLI — contrast `add`'s `required=True`). A rationale becomes *de-facto* required only at transmit-back (`github_pr.py cmd_post_responses` skips a `rejected` finding with no `resolution_detail` as `no_resolution_detail`), while **no `source`/citation field exists on the disposition at all** — the citation, when guidance recommends one, lives inside the free-text rationale and is never validated. This asymmetry (rationale required to transmit, source never required) is recorded for the epic's standing remedy; it is not fixed here (out of this plan's ext-self-review scope).

### CI / PR review

**CI (required contexts).** On the initial head `d8bf721` every required GitHub Actions context concluded `success` — `verify / conclusion`, `verify / verify`, `verify / gate`, `review / review`, `dependency-review`, `generate-check` — and `mergeable_state` read `clean`. Finalizing this report plus the singular-`check` test (F3, below) adds two commits; the same required set re-runs on the new head and is confirmed green before auto-merge is armed (merge gate condition 1).

**CodeRabbit (`coderabbitai`) — five actionable findings, each dispositioned:**

1. **F1 — report-01.md carried `_pending`/`_filled` placeholders and `Outcome: in progress`** (inline thread, Major). **Fixed** — this finalization commit replaces every placeholder (PR number, this CI/PR-review section, the reviewer-participation table, the Step 9 contract check, and the learnings section) and sets the final Outcome. This is exactly the Step 8 condition-3 finalization the lane mandates as the last pre-merge commit; the finding fired because the PR is opened (Step 7) before the report can be finalized — the reviewer-participation verdicts do not exist until the reviewers report.
2. **F2 — `_CARDINALITY_NOUNS` is mirrored by four documentation consumers; use one source of truth or add consumer-consistency validation** (inline thread, Major / Heavy-lift). **Deferred with reason (routed out).** The four consumers are currently *consistent* — the one drift (Check 11) was caught by the pre-PR sub-agent and fixed in this PR — so this is future-drift prevention, not a present defect. Deriving markdown prose enumerations from a Python set, or building a cross-bundle set↔prose validator, is precisely the "authoritative-set → doc-prose-list mirror drift" this plan analyses and **explicitly routes out of scope** (see Findings → routed out, and Residue): it needs an annotation/pairing mechanism the plan's stop rule places out of bounds. Recorded as residue for a follow-up review-apparatus plan.
3. **F3 — the positive fixture proves only plural `checks`; test singular `check` explicitly** (inline thread, Minor). **Fixed** — `test_count_prose_surfaces_check_noun` now carries `one check` and asserts it surfaces (commit `380e02d`), pinning the singular branch of `checks?`.
4. **F4 — plan.md D1 describes `auto` as the lane that drops the `full` security audit; use the resolved posture axis and reserve `auto` for Path B** (review-summary "failed to post", Major). **Answered — the deliverable is already correct.** D1's actual output (report §D1: the two drop-path paragraphs plus the explicit framing note) reconciles this against the composer source — Path A is the posture axis `minimal/standard/full` (`lane_dropped`), Path B is the `auto` ceremony pre-filter (`security_class_omitted`). No misclassification occurred in the deliverable; `plan.md` is the historical input brief and its looser phrasing is superseded by the report's source-verified classification, so the brief is left as authored.
5. **F5 — the mutation proof lives only in untracked `scratchpad/`, so D3 is not reproducible from the repo; add a tracked mutation check** (review-summary "failed to post", Minor). **Answered — out of scope, durable artifact already committed.** The *committed* tests encode the discrimination directly: the positive case fails against the pre-widening five-noun set and the negative case fails under any-noun over-widening. The mutation harness was the design-time method used to *prove* those cases discriminate; a standing mutation-testing job across the suite is scope creep well beyond a one-noun widening and is not added. Recorded as residue.

**pr-agent (`cuioss-review-bot`) — reviewed, no findings.** Its "PR Reviewer Guide" reports "No security concerns identified" and "No major issues detected".

**Sourcery (`sourcery-ai`) — did not review: weekly rate limit.** It posted only "you have reached your weekly rate limit of 500000 diff characters" in place of a review; its `Sourcery review` check concluded `skipped`. Disclosed at the merge gate (Reviewer participation, below).

## Reviewer participation

Expected population, derived from the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc (cross-named by `.github/workflows/pr-agent.yml`): `coderabbitai`, `cuioss-review-bot`, `sourcery-ai` — three reviewers. Each verdict is read from the stored comment bodies on the PR, not from a check state.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `coderabbitai` | `reviewed` | Full review against the diff: a walkthrough issue comment, two review-summary bodies ("Actionable comments posted: 5"), and three inline review threads. Five findings, all dispositioned above. |
| `cuioss-review-bot` | `reviewed` | "PR Reviewer Guide" review body over the diff: "No security concerns identified", "No major issues detected". |
| `sourcery-ai` | `rate-limited` | Published only a refusal in place of a review: "you have reached your weekly rate limit of 500000 diff characters". It engaged but did not review this diff. |

**Coverage: 2 of 3 reviewed.** The § Step 8 condition-4 shortfall disclosure **fired**: *"Review coverage: 2 of 3 — `coderabbitai` reviewed; `cuioss-review-bot` reviewed; `sourcery-ai` rate-limited (weekly 500 000 diff-character quota, outside our control). Proceeding to arm auto-merge on 2-of-3 coverage — the shortfall is a disclosure, not a block."*

No reviewer was aborted by a mid-cycle push: CodeRabbit and pr-agent had **completed** their reviews on `d8bf721` before this finalization, so nothing was in-flight. The finalization push re-triggers fresh reviews on the new head; their verdicts here are read from the bodies already on the PR, and any re-review that lands after the queue admits the PR is the accepted merge-queue limitation the disclosure covers.

## Cost

- **Tokens:** not separately metered by the agent in this session; the harness counts total session usage but does not expose a per-run figure to the agent.
- **Wall-clock:** single interactive cloud session on 2026-08-13 (UTC).
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ NOT comparable to a plan-marshall `metrics.toon` total (which counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary — a boundary this interactive session does not share).

## Contract check (Step 9)

Re-read against what actually happened. **GitHub access path:** the GitHub MCP server (cloud session — no `gh`, Bash egress-blocked to `api.github.com`). **Branch form:** harness-assigned `claude/feed-pr-findings-local-review-3589nc`, kept as-is. A cloud run owes **no** `/sync-plugin-cache` — a machine-local build step, not a debt this run records.

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named in § Skills loaded (loaded by bundle path; the `plan-marshall` plugin is not installed in this cloud session). |
| 2 Branch on `origin` | Done — harness-assigned branch, published and current on `origin`. |
| 3 Plan directory | Done — `doc/plans/review-apparatus/090-.../plan.md` exists and opens with the first-instruction block. |
| 4 Implement + trailer | Done — commits carry `Co-Authored-By: Claude <noreply@anthropic.com>`; deliverables D0–D3 addressed. |
| 4 Per-commit gate | Done — each `*.py`-touching commit (the D2/D3 detector+tests, and the F3 singular-`check` test) was preceded by a clean `./pw verify` — `ruff`/`mypy`/SPDX clean, tests green. |
| 4 Pushed | Done — no unpushed commit remains after the finalization push. |
| 5 Build gate | Done — `git diff --name-only origin/main...HEAD` includes `*.py`; `./pw verify pm-plugin-development` = SUCCESS (`2234 passed`, `mypy`/`ruff`/SPDX clean), covering both the detector work and the F3 addition. |
| 6 Verification sub-agent | Done — one real finding (the Check 11 consumer drift) fixed and re-verified; findings and dispositions in § Findings. |
| 7 PR cycle | Done — PR #1204 open; all three comment surfaces read (`get_reviews`, `get_review_comments`, `get_comments`); every comment dispositioned (§ CI / PR review). |
| 8 Merge gate | Conditions 1–3 met at this commit (required contexts green on the prior head and re-confirmed on the new head; every comment handled; this report finalized as the last pre-merge commit). Auto-merge armed **SQUASH** as the immediately-following gate action. Condition-4 shortfall (2-of-3) disclosed. The landing is delegated to the merge queue and confirmed to the operator from the PR merge event. |
| 8 Bridge | Done — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome the orchestrator collects. |
| 9 This check | Done — this table. |
| 9 What have we learned | Recorded below (none proposed, with reason). |

## What have we learned (Step 9)

**None proposed.** This run exercised the contract end to end and produced no evidence of a gap the contract does not already cover. Three observations, each confirming an existing rule rather than exposing a gap:

- **The report-placeholder finding (CodeRabbit F1) is the contract working, not a gap.** The lane opens the PR at Step 7 before the report can be finalized (reviewer-participation verdicts do not exist until reviewers report), so a reviewer reliably sees `_pending` sections and flags them. Step 8 condition 3 already mandates finalization as the last pre-merge commit — which is what resolved F1 — so no change is warranted; the placeholders are load-bearing.
- **Two findings (F4, F5) arrived only in the review-summary body** (CodeRabbit's "Comments failed to post"), never as inline threads. This **corroborates** the existing § Step 7 rule that `get_reviews` MUST be read alongside `get_review_comments` and `get_comments`: a run reading only the inline-thread surface would have missed both. Existing rule confirmed.
- **`send_later` returned "requires approval"** at the merge gate, exactly as § Cloud session affordances predicts; the run proceeded by manual read-polling on the un-gated GitHub read surface — the documented in-session alternative. Existing rule confirmed.

A run that examined the contract and found it sufficient is a different fact from a run that never looked; this is the former.

## Residue

- **Run-report placeholder scan** — a real, accepted, mechanically-detectable pattern with the wrong owner for this plan. Route to a cloud-plan-lane report-completeness gate. (See Findings → routed out.)
- **Authoritative-set → doc-list mirror drift** — recurrent CodeRabbit theme; needs an annotation/pairing to be cleanly diff-scoped. Out of scope here; a candidate for a future review-apparatus plan.
- **Disposition-flow evidence asymmetry** — confirmed; the epic's standing remedy (a rejection must cite the artifact that settles it) is unbuilt and belongs to `manage-findings` / the triage contract, not ext-self-review.
- **Unanswered-finding rate** — 13 of 43 observed findings had no posted answer; a response-path reliability signal for the epic.
