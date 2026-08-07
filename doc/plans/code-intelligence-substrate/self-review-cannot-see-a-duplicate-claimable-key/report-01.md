# Run report — self-review-cannot-see-a-duplicate-claimable-key (run 01)

**Date (UTC):** 2026-08-07    **Branch:** claude/self-review-duplicate-key-fv7it7    **PR:** [#1107](https://github.com/cuioss/plan-marshall/pull/1107) _(review + merge gate in progress)_    **Outcome:** completed

## Skills loaded

- `cloud-plan-lane` (`.claude/skills/cloud-plan-lane/SKILL.md`) — the working contract, first action.
- `plan-marshall:ref-code-quality` — read by path (`marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`).
- `pm-plugin-development:plugin-script-architecture` — read by path.
- The plan's surface is Python production code + Python tests + a `SKILL.md`; `pm-dev-python:python-core` / `pm-dev-python:pytest-testing` / `pm-plugin-development:plugin-architecture` were not separately loaded because the change extends an existing, well-patterned detector module and its existing test file — the governing patterns were read directly from the neighbouring detectors and tests, which is the stronger source for a bounded extension. Recorded here rather than silently skipped.

## Deliverables

All five landed in commit `35ecf3f` (`feat(ext-self-review): add duplicate-claimable-key and discard-without-report detectors`).

### D1 — candidate class: duplicate-claimable key — DONE
- **What:** new detector `_detect_duplicate_claimable_keys` in `_self_review_detectors.py`, regexes in `_self_review_patterns.py` (`_LOOP_HEADER`, `_EMPTY_COLLECTION_BINDING`, `_IDENTITY_APPEND`, `_IDENTITY_KEY_VALUE`, `_SUBSCRIPT_CLAIM`), registry entry `CandidateList('duplicate_claimable_keys', 'duplicate-claimable keys', True)`, dispatch wired in `self_review.py::_cmd_surface`.
- **Shape:** an identity claimed into a NEW keyed collection inside a loop — either `.append({... 'id': VALUE ...})` (single-line dict literal, identity key) or `COLL[KEY] = ...` (subscript claim) — raised at the **insertion site**. Fires ONLY on the conjunction of a presence/type validation of the identity (`if not X` / `X is None` / `isinstance(X)`) AND the ABSENCE of a membership/uniqueness guard (`X in` / `.get(X)` / `.setdefault(X)` / `coll[X]` / `X ==`).
- **The validation-guard discriminator was a design correction forced by D3** (see Findings). A naïve "identity-append with no dedup" fired on `merge_resolver_edges`'s own `reports.append({'id': resolver_id})` — a benign per-iteration accumulator. Requiring the loop to *validate* the identity (the exact #1067 defect signature: presence checked, uniqueness forgotten) removes that false positive while still firing on the real defect.
- **Verification:** fires on the D4(a) fixture (`discover_derivation_resolvers()` pre-fix); silent on post-fix and on `merge_resolver_edges` pre-fix. Unit coverage in `test_self_review.py::TestDetectDuplicateClaimableKeys` (both forms + six negative controls).

### D2 — candidate class: discard path with no report path — DONE
- **What:** detector `_detect_discard_without_report`, regexes `_REPORT_CHANNEL_EMISSION` / `_IF_BLOCK_OPENER` / `_IF_INLINE_DISCARD` / `_DISCARD_STATEMENT`, registry entry `CandidateList('discard_without_report', 'discard paths without a report path', True)`, dispatch wired.
- **Shape:** a function that owns a report channel (a `'notes': notes` self-named emission for a suppression-report noun, AND that name assigned as a local variable) that drops an item on a BARE `if`-guarded `continue`/`break` (whole branch body is only the discard). A branch that records the drop first — appends to the channel, routes to a sibling disposition list, logs it — is not bare and surfaces nothing.
- **Two narrowings forced by D3** (see Findings): the channel must be an *assigned local* (not merely prose that shows `'notes': notes`, which the detector's own docstring does), and the discard must be *bare* (a multi-disposition dispatch loop records every drop somewhere and is not the defect).
- **Verification:** fires on the D4(b) fixture (`merge_resolver_edges()` pre-fix, all three unreported drops); silent on post-fix and on `discover_derivation_resolvers` (no report channel). Unit coverage in `test_self_review.py::TestDetectDiscardWithoutReport` (bare/inline positives + five negative controls).

### D3 — GATE: population both classes fire on, hits reported SEPARATELY from files examined — DONE
Derived by running each detector in post-image mode over the project's `.py` files. The two numbers are reported **separately**, as the plan requires:

- **Files examined: 1154** — the project tree. The sweep prunes `.git`/`node_modules`/`target`/`.plan`/`__pycache__`/`.venv`/`.pytest_cache`/`.pyprojectx` and scopes out `test_self_review_defect_regression.py` (its literal carries the pre-fix defect on purpose). Over the raw tree WITH the pyprojectx-managed virtualenv populated and the fixture file included, the counts are 21 D1 / 6 D2 over 1972 files; the extra eight over the project figure are vendored third-party site-packages (D1) and the fixture's three D2 hits.
- **D1 `duplicate_claimable_keys` hits: 14** — each a *validated-but-not-deduped* insertion the reviewer glances at. **Not all 14 are defects**, and that is expected: like all twenty sibling lists, D1 is a *surfacing* detector feeding the cognitive-review pass, not a verdict. `manage-findings.py:106` (`result[field] = value`, a benign last-write-wins `FIELD=VALUE` parser) and `merge_lock.py:375` (a FIFO rebuild) both pass the validation narrowing yet are legitimate; the value of the surface is that a reader adjudicates 14 readable candidates rather than a firehose. (The count was **13** before a review-bot-driven fix to `_identity_deduped` — see § Findings → CI / PR review — un-hid one genuinely-suppressed candidate at `manage-status/scripts/_status_query.py:679`.)
- **D2 `discard_without_report` hits: 3** — `workflow-integration-github/scripts/github_pr.py:1329`, `workflow-integration-gitlab/scripts/gitlab_pr.py:382`, `workflow-integration-sonar/scripts/sonar.py:742` — each a bare pre-filter `continue` in a `post_responses`-style loop that owns a `skipped` channel and records its other skips.

The command that produced the numbers (stdlib only, no third-party deps):

```python
# From the repo root. os.walk with the prune set below; for each .py file:
#   added = [(rel, i, line) for i, line in enumerate(text.splitlines(), start=1)]
#   d1 += _detect_duplicate_claimable_keys(added)   # post-image mode: added IS the scan surface
#   d2 += _detect_discard_without_report(added)
# prune = {.git, node_modules, target, .plan, __pycache__, .venv, .pytest_cache, .pyprojectx}
# then scope out test_self_review_defect_regression.py (its literal carries the pre-fix defect on purpose)
```

14 and 3 over 1154 is narrow — not the "hundreds of sites" the plan flags as mis-specification, and the narrowness was reproduced by an independent re-sweep.

### D4 — tests, each verified to FAIL pre-fix — DONE
- Reached the real pre-fix revisions via `git fetch origin refs/pull/1067/head`. The #1067 branch introduced both functions in `2896e18`, fixed them in `c4ff227`; `14d4e3d` (= `c4ff227^`) is the last commit carrying the defect; the merge `c6b501e` already contains the fix (the findings were fixed *within* the PR before the squash merge).
- `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_defect_regression.py` carries the pre-fix and post-fix bodies of both functions as **checked-in literals** transcribed from those revisions (every executable line verbatim; long docstrings elided). Never git-resolved at test time — the squash-merged intermediate commits are garbage-collection candidates, the same discipline the rule-19 worked-example fixtures use.
- Case (a): D1 flags `discover_derivation_resolvers()` pre-fix (the `resolvers.append` insertion) and is silent on the shipped post-fix. Case (b): D2 flags the three unreported drops in `merge_resolver_edges()` pre-fix and is silent post-fix. Each class is silent on the sibling function (disjoint shapes). The failing direction is proven by the paired positive/negative over the same real code.

### D5 — documentation — DONE
`SKILL.md` § Detection Rules gains rules 20 and 21, each stating the detection shape AND the false-positive posture (what is deliberately out of scope, and why the narrowing keeps the surface low-noise). Frontmatter description, the "twenty-two candidate lists" count, the `counts` block, the two list-shape declarations, the `total`-formula and its explanation paragraph, and the Tests section were all updated in lock-step. `plugin-doctor`'s `literal-count-drift` rule passes, confirming the count updates are internally consistent.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (detectors, patterns, dispatch, tests), so the full gate ran.

- `./pw quality-gate` → `total_issues: 0` (ruff + SPDX + all 31 plugin-doctor rules, whole-tree).
- `./pw module-tests` (all bundles) → **17767 passed, 14 skipped, 0 failed**. The 14 skips are pre-existing environment guards, none introduced by this change.
- One existing test (`test_self_review_reachability_regression.py::...covers_every_key_the_surfacer_emits`) failed on the first run because it hand-maintains the sibling-candidate-list vocabulary; adding the two keys to its `_SIBLING_LISTS` tuple (the maintenance the test exists to force) fixed it. That test's whole purpose is to catch a new list that was not registered in the sweep — it did its job.

## Findings

### Verification sub-agent (Step 6)
An independent `general-purpose` sub-agent verified the pushed diff against the plan. **Verdict: all five deliverables landed and are correct; D4 independently proven against real git history (it re-extracted `14d4e3d`/`c6b501e` and diffed them against the fixtures — verbatim); no undeclared collateral in the deliverable commit `35ecf3f`.** It ran both detectors against the fixtures itself and reproduced D1=1/D2=3 on the pre-fix forms and silence on post-fix. Its findings were nuances, not deliverable failures:

1. **D1 is narrower than a literal reading of the plan** (it adds a *validated* conjunct on top of "no membership test"). Disposition: **accepted, by design** — this is the D3-forced narrowing the plan's main-risk clause explicitly authorizes, disclosed in the SKILL.md false-positive posture. Recorded consequence: un-validated duplicate-claimable insertions are out of scope (recall traded for a low-noise surface).
2. **D3 prune-set / reproducibility accuracy** — the report's prune list omitted `.pyprojectx` and the fixture file, so a naïve re-derivation gets 1972/19/6. Disposition: **fixed** — the D3 section now states the vendored + fixture exclusion and carries the reproducible command.
3. **"None an un-validated accumulator" oversells narrowness** — some of the 13 D1 hits are benign. Disposition: **fixed** — the D3 section now says so explicitly and frames D1 as a surfacing detector, not a verdict.
4. **Registry hypothesis not explicitly recorded as refuted.** Disposition: **fixed** — recorded below.

No code changed as a result of this pass (the verification found no code defect), so no re-dispatch was warranted; the fixes are report-accuracy improvements.

### Claim-label settlement (the plan's two HYPOTHESES)
- **"The candidate classes live in one registry a new class can be added to WITHOUT touching the dispatch path" — REFUTED against the implementing source.** `CANDIDATE_LISTS` (`_self_review_patterns.py`) is the single source of truth for the emitted *vocabulary*, the `counts.total` formula, and the help prose — and the `_compose_candidate_output` guard enforces that the emitted key set matches the registry. But each detector is still **hand-wired into the dispatch**: adding a class required editing `self_review.py::_cmd_surface` (2 imports + 2 detector calls + 2 `detected`-dict entries), plus a `_detect_*` function and its regexes. The cost was modest and did not change scoping materially — but the hypothesis as stated ("without touching the dispatch path") is false, and D1/D2 were scoped and built on that corrected understanding.
- **"D1's shape is narrow enough not to fire on ordinary accumulator code" — settled by D3 as CONFIRMED-with-nuance.** The validation-guard narrowing keeps D1 off un-validated accumulators (the noisiest class), holding the tree-wide population to 13; a minority of those 13 are benign validated maps, which is acceptable for a surfacing detector.

### D3-driven self-review findings (design corrections before shipping)
The plan's main risk — "a detector that fires everywhere is worse than no detector" — was met by running D3 first and narrowing:
1. **D1 false positive on `merge_resolver_edges.reports.append({'id': resolver_id})`** — a benign per-iteration accumulator. Fixed by requiring the identity be *validated* in the loop (the #1067 defect validates presence but not uniqueness). Disposition: fixed before first commit.
2. **D2 self-hit on the detector's own docstring** (`'notes': notes` shown as prose) — fixed by requiring the channel be an *assigned local*. Disposition: fixed before first commit.
3. **D2 over-firing on `github_pr` multi-disposition dispatch** (branches routing to `untransmitted` / `batch`) — fixed by flagging only *bare* discards. Dropped D2 from 15 hits to 3. Disposition: fixed before first commit.

### CI / PR review
- **`cuioss-review-bot` — "False Negative Bug" in `_identity_deduped`.** The bot correctly found two over-broad suppression patterns: `\b{esc}\s+in\b` matched `for KEY in items:` loop headers, and `\[{esc}\]` matched unrelated input reads like `data[key]` — both causing D1 to falsely *suppress* real duplicate-claimable defects (false negatives). Disposition: **fixed.** The plain `in` guard is now scoped to a conditional (`if`/`elif`/`while`, which also covers a comprehension's `if`) plus the unconditional `X not in`; the bare-subscript pattern is removed (a genuine subscript dedup uses `not in`/`.get`/`.setdefault`, which the remaining patterns still catch, and post-fix `discover_derivation_resolvers` is still suppressed via its `.get(resolver_id)`). Re-ran D3: the fix un-hid exactly one genuinely-suppressed candidate (`_status_query.py:679`), moving the D1 population 13 → 14 — still narrow, no balloon. Three unit tests pin the fix (loop-variable identity fires; unrelated input read does not suppress; a genuine `if X in reg` guard still suppresses).
- **CI `verify / conclusion` failure on `9d2444f` — NOT a real failure.** The job log shows `verify job failed or was cancelled` with the verify job status `cancelled`: rapid successive report commits superseded the in-flight run and GitHub's concurrency cancelled it. The run on the latest SHA is authoritative; `verify / gate` passed there. Lesson recorded: batch report/doc pushes to avoid superseding CI runs.
- **CodeRabbit — review failed / rate-limited.** Its review aborted because the head commit changed mid-review (same rapid-push cause), then it hit its OSS review rate limit (~55 min). Not a required check and not actionable now; the substantive review coverage came from `cuioss-review-bot` and the independent pre-PR sub-agent.

## Contract check (Step 9)
_Pending — completed as the last action of the run._

## What have we learned (Step 9)
_Pending._

## Residue

- **Consumer integration is out of this plan's bundle boundary and is deferred.** The plan scopes the change to `pm-plugin-development` (Expected surface + the "this is pm-plugin-development" note). The consumer workflow `plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` (a different bundle) was deliberately not edited. Two consequences to hand off:
  1. Its prose "the twenty candidate sub-lists" / "sums the fifteen line-level heuristic lists" is now stale (22 lists, 17 in `total`). It is functionally correct — the consumer reads `counts.total` from the field, not from the prose — but the enumeration should be refreshed by whoever next touches that file. It was NOT flagged by CI: the `count_prose` self-review rule only scans skill dirs of files the diff modified, and this diff modifies nothing in `phase-6-finalize`.
  2. The consumer's Step 3 applies fifteen cognitive checks by name; it has no dedicated check for the two new deterministic lists. The lists are surfaced in the TOON and contribute to the gate count, but a follow-up that adds two light cognitive-adjudication steps (checks 16/17) would close the loop so a fired D1/D2 candidate becomes a filed finding. This is a separate, cross-bundle change.
- **`marketplace/bundles/` was edited, so a local `/sync-plugin-cache` is owed** on whatever developer machine picks this up — the cloud lane cannot run it (`/sync-plugin-cache` reads git-ignored `target/` and writes `~/.claude/`).
