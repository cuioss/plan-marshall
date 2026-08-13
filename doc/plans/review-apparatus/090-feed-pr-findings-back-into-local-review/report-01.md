# Run report — feed-pr-findings-back-into-local-review (run 01)

**Date (UTC):** 2026-08-13  **Branch:** `claude/feed-pr-findings-local-review-3589nc` (harness-assigned)  **PR:** (opened this run — see Findings)  **Outcome:** in progress (finalized at the merge gate)

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

- **Positive** — `test_count_prose_surfaces_check_noun`: a skill doc carrying `nine checks` (the exact false-claim example) and `two checks` (the real corpus shape) must surface. Drawn from the motivating finding (the docstring contradiction) and the real `phase-1-init` instance.
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

_pending — filled during the PR review cycle._

## Reviewer participation

_pending — filled after the PR is opened and reviewers report. Expected population (from the registry `author_login` of each `automatic-review/standards/{bot_kind}.md`): `coderabbitai`, `cuioss-review-bot`, `sourcery-ai`._

## Cost

- **Tokens:** not separately metered by the agent in this session; the harness counts total session usage but does not expose a per-run figure to the agent.
- **Wall-clock:** single interactive cloud session on 2026-08-13 (UTC).
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ NOT comparable to a plan-marshall `metrics.toon` total (which counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary — a boundary this interactive session does not share).

## Contract check (Step 9)

_filled at Step 8 condition 3, as the final pre-merge commit._

## What have we learned (Step 9)

_filled at Step 8 condition 3._

## Residue

- **Run-report placeholder scan** — a real, accepted, mechanically-detectable pattern with the wrong owner for this plan. Route to a cloud-plan-lane report-completeness gate. (See Findings → routed out.)
- **Authoritative-set → doc-list mirror drift** — recurrent CodeRabbit theme; needs an annotation/pairing to be cleanly diff-scoped. Out of scope here; a candidate for a future review-apparatus plan.
- **Disposition-flow evidence asymmetry** — confirmed; the epic's standing remedy (a rejection must cite the artifact that settles it) is unbuilt and belongs to `manage-findings` / the triage contract, not ext-self-review.
- **Unanswered-finding rate** — 13 of 43 observed findings had no posted answer; a response-path reliability signal for the epic.
