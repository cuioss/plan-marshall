# Verification — 110-participation-derived-from-a-lossy-view

**Landed as:** PR #1219, squash commit `38548923`
**Verdict:** verified-with-gaps

The plan's headline outcome is sound and independently reproducible: both target defects were real
before `50f67ed2` (#1141) and are genuinely absent at HEAD, the one uncovered regression guard was
added, it passes, and it discriminates against a mutation no pre-existing test catches. No production
code was touched. What the report does not carry is the residue: three live defects in the surface
this plan owns, seven stale prose passages restating the retired predicate, and two ⭐ obligations
recorded as "already satisfied" that the tree does not satisfy.

Plan `010-participation-credited-from-a-superseded-commit` owns the currency predicate itself and is
verified separately. Where a finding here lands on that surface it is recorded with a pointer to
`doc/plans/review-apparatus/010-participation-credited-from-a-superseded-commit/gaps.md` rather than
re-filed; `gaps.md` beside this file carries only what plan 110 uniquely owns.

## Method

Ground truth is the current tree on `claude/review-apparatus-analysis-mcf8md`. Every finding below was
re-derived from the tree; nothing is carried on citation alone.

Read in full: `plan.md`, `report-01.md`, `git show 38548923` (message + full diff), `git show --stat
38548923`.

Read in the current tree:

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
  — `_recorded_currency_records`, `_record_currency_records`, `_reviewed_at_merge_candidate`,
  `cmd_fetch_findings` (the participation loop, the storage-dedup site, the return dict).
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  — `_is_refusal_notice`, `_is_rate_limit_notice`.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_ci.py`
  — `fetch_pr_head_sha`.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py`
  — `fetch_pr_comments_data` (which comment surfaces are walked).
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`,
  `review_completeness.py`.
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot-participation-contract,
  coderabbit,pr-agent,sourcery}.md`, `automatic-review/SKILL.md`,
  `workflow-integration-github/SKILL.md`,
  `phase-6-finalize/standards/branch-cleanup.md` §§ "Predicate 2", "UNKNOWN — the re-fetch itself
  failed".
- `test/plan-marshall/workflow-integration-github/test_github_pr.py`,
  `test_refusal_recovery_arming.py`,
  `test/plan-marshall/automatic-review/test_bot_participation_contract.py`.

History checks:

- `git log --oneline --follow -- .../github_pr.py` → `50f67ed2` (#1141), its predecessor `fddc4ec8`
  (#1118), and the most recent touch `9e9e9880` (#1241).
- `git show fddc4ec8:.../github_pr.py` → the **pre-#1141** participation loop, which proves the defect
  was real (`observed_comment_keys = existing_comment_keys | recorded_dropped_keys` at `:839`, fed
  into `_has_update_movement` at `:878–879`).
- `git grep -n "participation_evidence(" 38548923 -- '*.py'` → the `[0]` reader population at the
  landing commit, for comparison with HEAD.
- `git log --oneline -L 166,207:test/.../test_github_pr.py` → two commits touch the added test:
  `38548923` (the landing) and `d3ba81fd` (#1259), a docstring shortening; the body is intact.

Greps run (repository-relative; each reported with the count it actually returns):

- `grep -n "existing_comment_keys" .../github_pr.py` → **3** hits: `:897` (construction), `:911` (a
  comment naming it), `:1102` (the filing dedup). **None inside the participation loop.**
- `grep -rn "participation_evidence(" --include=*.py --include=*.md .` (excluding `__pycache__` and
  `doc/plans`) → 3 production readers, 5 test readers, of which **4** are `[0]` readers.
- `grep -rn "_has_update_movement" --include=*.py --include=*.md .` → zero production hits; only
  `doc/plans/` prose (plans 010 and 110).
- `grep -rn "first presence\|first-present\|updated_at movement\|updated_at\` has moved\|updated_at !=
  created_at" marketplace/bundles/` → 6 doc/docstring hits plus `github_pr.py:578`, which is the
  in-source comment recording the closed hole (not stale). The contract's *union* claim is **not**
  reachable by that grep and was found separately by reading
  `bot-participation-contract.md` §§ around `:230` and `:488`.
- `grep -rn "auto_on_push\|requires_explicit_trigger" marketplace/ test/ doc/` → hits **only** inside
  this plan's own `plan.md`, `verification.md` and `gaps.md`; **zero** in `marketplace/`, `test/`, or
  any other `doc/` file.
- `grep -rn "head_sha=''" test/plan-marshall/` → two hits in tracked files:
  `test_github_pr.py:2479` (the both-fetches-fail case) and an unrelated `test_ci_verify.py:339`.
  (A third hit belongs to an untracked scratch probe left in the working tree by another review; it is
  not part of the repository.)

Tests run (no repository file left modified):

```
UV_HTTP_TIMEOUT=600 uv run python -m pytest \
  test/plan-marshall/workflow-integration-github/test_github_pr.py -o addopts="" -q \
  -k "deduped_comment_is_still_credited or second_fetch_at_the_same_head or review_predating \
      or edit_at_one_commit or currency_anchor or at_least_one_registered_bot"
→ 6 passed, 83 deselected
```

Behavioural probes (temporary test modules, deleted afterwards; `git status --porcelain` clean apart
from the untracked scratch file noted above). Each drives the real `cmd_fetch_findings` through the
existing `_patch_provider` / `_publish_comment` helpers:

- **P1 — credit at `_HEAD_A`, then a fetch with `head_sha=''`.** Observed
  `participated_bots == [pr-agent]` then `[]` with `stale_participation_bots == [pr-agent]`, and the
  return carries no head-SHA-resolution key. → C1.
- **P2 — comment filed at `_HEAD_A`, edited in place with new content at `_HEAD_B`.** Observed
  `count_stored 1 → 0`, `count_skipped_duplicate 0 → 1`, `participated_bots` unchanged. → C2.
- **P3 — a reworded refusal matching neither recognition layer.** `_is_refusal_notice(body,
  'pr-agent')` returns `False` and the bot is credited in `participated_bots` with `refused_bots ==
  []`. → C3.
- **P4 — credit, then an edit observed at `head_sha=''`.** The ledger row is written with an empty
  `reviewed_commit_sha`, and the next fetch at a real HEAD reports the bot stale. → C1 (amplifier).
- **P5 — two evidence comments of one currency-subject bot, HEAD advanced, neither edited.** The bot
  stays `participated`. → the D3(c) coverage limit below; the production half is plan 010's.

Mutation sweep (bytes snapshotted to `$TMPDIR/adv-110-mutsweep/` and restored from the snapshot;
`git status --porcelain` re-checked clean afterwards):

- **M1 — re-couple participation to the storage dedup for all bots** (a `continue` on
  `(bot_kind, comment_id) in existing_comment_keys` at the top of the participation loop):
  `test_a_deduped_comment_is_still_credited_as_participating` **and**
  `test_second_fetch_at_the_same_head_stays_participated[pr-agent]` both fail.
- **M2 — re-couple only the presence-credited bots** (the same guard, gated on `not
  _requires_update`): **only** `test_a_deduped_comment_is_still_credited_as_participating` fails; 177
  other tests across `test_github_pr.py`, `test_pre_merge_barrier.py` and
  `test_bot_participation_contract.py` pass.

M2 is what establishes the added test's unique value: the pre-existing currency suite already covers
the requires-update half of M1, so the guard this plan added is load-bearing specifically for the
presence-credited bots.

The full build was not re-run.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | Both defects re-established or refuted at HEAD, and the consumer population published with each member classified | Both REFUTED (fixed by #1141); 4-site consumer table + 8-site `participation_evidence` table published; ordering dependency is test-fixture-only; cross-plan collision resolved | Refutation CONFIRMED against `fddc4ec8` (defect present) vs HEAD (absent). Consumer table correct but **incomplete**: `workflow-integration-github/SKILL.md` — which *defines* what `participated_bots[]` credits — is not enumerated at all, and the wait-completion predicate the plan's Notes named as a population member is classified nowhere. Three plan claim-labels were never adjudicated | met-with-gaps |
| D1 | A bot proven on call 1 is still credited on call 2 at an unchanged head SHA, and advancing the SHA resets the credit | "Already satisfied at HEAD by #1141; no production change"; trigger semantics "already registry data" | Core property CONFIRMED (`test_second_fetch_at_the_same_head_stays_participated`, `test_review_predating_the_merge_candidate_is_stale`). But monotonicity **breaks on an unreadable head SHA** (P1 → G1), and the ⭐ `auto_on_push` / `requires_explicit_trigger` record **does not exist** (G6) | partially met |
| D2 | The participation predicate's input no longer passes through the storage dedup, and the identity used for "seen this review" is stated explicitly | "Already satisfied at HEAD by #1141"; identity stated as `(reviewed_commit_sha, updated_at)` vs `(bot_kind, comment_id)` | Decoupling CONFIRMED. Identity stated. But the plan's own *"the defect, verified in source"* — `comment_id` alone over-firing so an **edited-in-place review's new content is dropped** — is **still live** at `github_pr.py:1102`, reproduced by P2, and is not disclosed (G2) | met literally, incomplete substantively |
| D3 | (a) deduped bot still credited; (b) call-2 credit at unchanged HEAD; (c) SHA advance resets; (d) consumer population derived + non-empty-asserted + every member covered; ⭐ population-derived refusal fixture publishing its population size | (a) ADDED and mutation-proven; (b)(c)(d) ALREADY COVERED | (a) CONFIRMED present, passing, and uniquely discriminating (M2). (b) CONFIRMED. (c) CONFIRMED **for the single-comment shape only** — P5 shows a bot with two evidence comments keeps its credit across a HEAD advance. (d) the consumer half is covered by `TestCallSitePopulation`, a test the report never cites; the three tests it *does* cite enumerate the **bot** population (G8). The ⭐ refusal fixture is **not** wording-derived and **does** pass over an empty pattern set (G4) | partially met |

### D0 — the gate

**Defect 1 was real, and is refuted at HEAD. CONFIRMED both ways.**

Pre-fix, at `fddc4ec8`, `github_pr.py` read:

```python
recorded_dropped_keys = _recorded_dropped_comment_keys(plan_id)
observed_comment_keys = existing_comment_keys | recorded_dropped_keys
...
if bot_registry.participation_requires_update(_bot_kind) and not _has_update_movement(
    _comment, observed_comment_keys, _bot_kind
):
```

`existing_comment_keys` is the storage-dedup input, and it was unioned into the participation
predicate's input. That is exactly the plan's Defect 1.

At HEAD the participation loop (`github_pr.py:941–975`) reads only `raw_comments` and
`currency_records`; `existing_comment_keys` appears at three places — `:897` (construction), `:911`
(a comment naming it) and `:1102` (the filing dedup) — none of them inside the participation loop.

One nuance the report does not record: the pre-fix coupling bit **only** `participation_requires_update`
bots (the `git show fddc4ec8` excerpt above gates on it). The plan's narrative that the dedup
"emptied `participated_bots`" is therefore true for pr-agent and false for the presence-credited bots.
This does not change the refutation.

**Defect 2 was real, and is refuted at HEAD. CONFIRMED.** `_reviewed_at_merge_candidate`
(`github_pr.py:652–708`) reads the ledger written by *prior* fetches and compares
`recorded_sha == merge_candidate_sha` (`:705`). `test_second_fetch_at_the_same_head_stays_participated`
(`test_github_pr.py:2431`) pins the call-2 credit; it passes.

**`_has_update_movement` is gone.** The grep in *Method* returns only `doc/plans/` prose. The report's
cross-plan-collision resolution is CONFIRMED.

**The `[0]` ordering classification is CONFIRMED; the plan's count is not reproducible.** Production
readers, all LIST-valued: `github_pr.py:953` (`_kind not in participation_evidence(_bot_kind)`),
`review_completeness.py:377` (`evidence_kind in ...`), `_github_pr.py:506` (`all(not ...)`).
`[0]` readers, all test fixtures: `test_github_pr.py:2408`, `test_pre_merge_barrier.py:739`,
`test_bot_participation_contract.py:653`, `test_legacy_bot_list_migration.py:137`. The plan's figure of
"**seven** registry-derived consumers" is not reproducible — there are **four** `[0]` call sites at
HEAD and the same four at the landing commit `38548923`, and none is a production verdict. The plan's
*shape* claim stands: the ordering dependency is real, and `pr-agent.md:75–79` independently documents
it ("ORDERING IS LOAD-BEARING … `test_bot_participation_contract.py` reads element `[0]`").

**Three claim-labels the plan tabled were never adjudicated by the report.** Each is answered here:

- *"An unmatched refusal notice reaches the participation credit in our classifier"* — **CONFIRMED
  TRUE**, by reading and by probe P3. `github_pr.py:950` calls `_is_refusal_notice`; that function
  (`_github_pr.py:183–187`) is a `refusal_patterns` substring match **or** the structural
  `_is_rate_limit_notice`. A reworded vendor notice that matches neither falls through to
  `github_pr.py:953`, matches a declared publish shape, and is **credited as participation**. See G3.
- *"Inline-comment enumeration under-collects body-level findings"* — **REFUTED for
  `fetch_findings`.** `github_ops.fetch_pr_comments_data` (`github_ops.py:356–465`) walks three
  surfaces: `reviewThreads` → `inline`, `reviews` → `review_body`, `comments` → `issue_comment`. The
  producer does not read an inline-only endpoint.
- *"The completeness script computes no timestamp; the determination happens upstream"* — **CONFIRMED
  behaviourally.** `review_completeness.check_completeness` (`review_completeness.py:708`) consumes
  `--participated-bots` through `parse_participation` (`:335–379`), which re-tests membership in
  `participation_evidence` at `:377`; no currency arithmetic occurs anywhere in that module.

### D1 — monotonicity at a fixed head SHA

The Done-when is met on the happy path. It is **not** met when `fetch_pr_head_sha` fails.
`_github_ci.fetch_pr_head_sha` (`_github_ci.py:55–64`) returns `''` "on any failure path". Then, for a
comment already credited with `recorded_sha = A`:

```python
705:    if merge_candidate_sha and recorded_sha == merge_candidate_sha:   # False — sha is ''
706:        return True
707:    updated_at = str(comment.get('updated_at') or '')
708:    return bool(updated_at) and updated_at != recorded_updated_at      # False — unchanged
```

⇒ `participated_stale`, which is **blocking** (`bot-participation-contract.md:64`), on a head SHA that
never actually moved. Probe P1 reproduces it end-to-end through `cmd_fetch_findings`. The docstring's
idempotence claim (`:684–686`) is scoped to two *consecutive failed* reads, and
`test_unresolvable_head_sha_fails_closed_and_stays_idempotent` (`test_github_pr.py:2462`) tests exactly
that scoped case (`head_sha=''` on both fetches, `:2479`). The mixed case — credit, then a failed read
— is untested. See G1.

The ⭐ "record per-bot trigger semantics explicitly (`auto_on_push` versus
`requires_explicit_trigger`, with the trigger command for the latter)" is **not** satisfied. The grep
in *Method* returns nothing outside this plan's own text. The three fields the report offers instead do
not encode the distinction: `participation_requires_update` is about *how a review is published*,
`rate_limit_class` is about *awaitability*, and `trigger_comment` is non-empty for all three registered
bots (`coderabbit.md:37`, `pr-agent.md:62`, `sourcery.md:30`), so it discriminates nothing. See G6.

### D2 — decoupling, and the identity

Decoupling CONFIRMED (above). Identity stated CONFIRMED (`github_pr.py:906–914`: the currency ledger
is "the SOLE currency source"; the dedup "asks a different question").

What is **not** closed is the plan's own D2 paragraph, quoted verbatim:

> The cross-iteration dedup is keyed on `(bot_kind, comment_id)` **alone — no content or timestamp
> term.** A bot that edits **one persistent comment in place** never changes its id, so an *updated*
> review is dropped as a duplicate.

At HEAD, `github_pr.py:1102` is still:

```python
if (bot_kind or '', comment_id) in existing_comment_keys:
    skipped_duplicate += 1
    continue
```

No content term, no `updated_at` term. pr-agent declares `participation_requires_update: true` —
"a re-review EDITS that same comment in place" (`pr-agent.md:84–85`). Probe P2 drives the consequence
through the real producer: a pr-agent re-review that adds a real finding to its persistent Guide is
**credited as participation** (the fresh-edit arm fires) while its **new content is dropped from
filing** (`count_stored == 0`, `count_skipped_duplicate == 1`) and never reaches triage or the
pre-merge barrier's pending-findings gate. The report reframes this as "a different question" and does
not record it as residue. See G2.

### D3 — the tests

The added test is `test_a_deduped_comment_is_still_credited_as_participating`
(`test/plan-marshall/workflow-integration-github/test_github_pr.py:166–206`). It exists, it passes,
and it is genuinely discriminating: the assertion `second['participated_bots'] ==
first['participated_bots']` (`:205`) is preceded by `second['count_skipped_duplicate'] ==
len(_COMMENTS)` (`:201`), so the deduped-and-still-credited conjunction is pinned on one fetch.
Mutation M1 makes it fail; mutation M2 — the same coupling restricted to the presence-credited bots —
makes it the **only** failing test in the three suites exercised, which is what establishes that it is
not redundant with the pre-existing currency suite. It is likewise not redundant with its neighbour
`test_second_fetch_dedupes_all_bot_kinds` (`:135`), which asserts nothing about participation. The
`_COMMENTS` fixture (`:38–75`) carries no `updated_at`, so on the second fetch pr-agent's credit comes
from the SHA-currency arm (its ledger row was written by the first fetch) rather than from an edit —
the conjunction therefore covers both participation shapes.

D3(b) coverage is real: `test_second_fetch_at_the_same_head_stays_participated` (`:2431`).

D3(c) coverage is real **for the single-comment shape**:
`test_review_predating_the_merge_candidate_is_stale` (`:2496`) and
`test_edit_at_one_commit_does_not_credit_a_later_commit` (`:2360`) each publish exactly one comment
(`'guide-1'`). Probe P5 shows the property does not hold generally: with **two** evidence comments of
one currency-subject bot present at both fetches and neither edited, advancing the head SHA leaves the
bot `participated`, because the second comment has no ledger row and takes the unguarded
first-observation arm (`github_pr.py:701–703`) after the loop's short-circuit at `:943` prevented it
from being recorded on the first fetch. That production defect is **plan 010's**, filed there as
`010-…/gaps.md` § G1 (severity blocker) with the two-comment test in its Task; it is not re-filed here.
What belongs to plan 110 is the scope of its own claim: "D3(c) ALREADY COVERED" is accurate only for
one comment per bot.

D3(d) is the weak half — see G4 and G8.

## Report-claim audit

| # | Claim in `report-01.md` | Verdict | Evidence |
|---|---|---|---|
| 1 | "Both defects … REFUTED at HEAD — already fixed by … #1141, squash `50f67ed`" | **ACCURATE** | `50f67ed2` in `git log --follow`; defect present at `fddc4ec8`, absent at HEAD |
| 2 | Participation derived over `raw_comments` "before any noise / duplicate / resolved filtering" | **ACCURATE** | `github_pr.py:917–941` (the comment) and `:941–975` (the loop) |
| 3 | "The storage dedup … is consulted **only** in the separate finding-storage loop" | **ACCURATE** | `grep -n "existing_comment_keys"` → 3 hits: `:897`, `:911` (comment), `:1102` |
| 4 | "`_reviewed_at_merge_candidate`, a **pure SHA comparison** … identical however many times it is evaluated" | **OVERSTATED** | True for the ledger-hit path. The first-observation arm returns `bool(merge_candidate_sha)` (`:703`), so the verdict is a function of ledger state *and* of whether the SHA read succeeded — it flips after a failed read (P1 → G1) |
| 5 | Consumer table C1–C4, "None of C2–C4 reads a deduped projection" | **ACCURATE but INCOMPLETE** | `branch-cleanup.md:810` retains the producer's sets; `review_completeness.py:377` tests LIST membership. Missing from the enumeration: `workflow-integration-github/SKILL.md:129`, which *defines* the credit rule and states it wrongly (G5), and the wait-completion predicate the plan's Notes named (G10) |
| 6 | "every FIRST-ELEMENT (`[0]`) reader is a test fixture; no production participation decision reads `[0]`" | **ACCURATE** | 4 test `[0]` readers, 3 production LIST readers — full grep in *Method*; the same four at `38548923` |
| 7 | "`_has_update_movement` no longer exists … nothing to port" | **ACCURATE** | `grep -rn "_has_update_movement"` → `doc/plans/` prose only |
| 8 | D1 "Already satisfied at HEAD by #1141; no production change" | **OVERSTATED** | Core property holds; the unreadable-SHA flip (G1) and the missing trigger-semantics record (G6) are unmet |
| 9 | "Per-bot trigger semantics are already registry data (`participation_requires_update`, `trigger_comment`, `rate_limit_class`)" | **FALSE** as a satisfaction of the ⭐ | `grep -rn "auto_on_push\|requires_explicit_trigger" marketplace/ test/ doc/` → nothing outside this plan's own text. None of the three fields encodes auto-on-push vs explicit-trigger; `trigger_comment` is non-empty for all three bots |
| 10 | D2 "Already satisfied at HEAD … The identity … is stated explicitly" | **PARTIALLY ACCURATE** | Decoupling and identity-statement CONFIRMED; the plan's stated over-firing half is still live at `:1102` (probe P2) and undisclosed (G2) |
| 11 | D3(a) "New test … asserting … `count_skipped_duplicate == len(_COMMENTS)` … Mutation-proven" | **ACCURATE** | Test at `test_github_pr.py:166–206`; runs green; discrimination re-proven independently by mutations M1 and M2 |
| 12 | D3(b)/(c) "ALREADY COVERED by `test_second_fetch_at_the_same_head_stays_participated` / `test_review_predating_the_merge_candidate_is_stale` / `test_edit_at_one_commit_does_not_credit_a_later_commit`" | **ACCURATE AS SCOPED** | All three exist and assert what is claimed. Each publishes one comment per bot, so the D3(c) property is pinned only for the single-comment shape — probe P5 breaks it with two (production half: `010-…/gaps.md` § G1) |
| 13 | D3(d) consumer population "ALREADY COVERED" by `test_at_least_one_registered_bot_requires_update_movement`, `test_currency_anchor_is_recorded_in_the_ledger_on_credit`, and the taxonomy sweep | **OVERSTATED** | All three exist, but each derives the **bot** population, not the consumer population. The nearest genuine coverage is `TestCallSitePopulation` (`test_bot_participation_contract.py:944–1010`), which scans `marketplace/bundles/**/*.md` via `_scan_invocation_sites()` (`:860–893`) for both invocation families with a per-family vacuity guard (`:948`) — and the report never cites it (G8) |
| 14 | D3(d) refusal fixture "population-derived … both swept over `_registered_bots()` with a non-empty guard" | **OVERSTATED** | Swept over **bots**, not over **wordings**. `_refusal_body` (`test_refusal_recovery_arming.py:61–74`) uses `declared[0]` only and **falls back to a synthetic notice** when a bot declares none, so `test_every_registered_bots_refusal_is_detected` (`:99`) passes for pr-agent while testing nothing pr-agent declares; `test_a_bots_declared_refusal_is_recognized_as_DATA` `pytest.skip`s for it (`:242–243`). Sourcery's second declared pattern is never swept. No test publishes the refusal-pattern population size (G4) |
| 15 | Population sizes: 3 registered bots; refusal patterns total 3 (coderabbit 1, sourcery 2, pr-agent 0) | **ACCURATE** | `bot_registry.bot_kinds()` → `['coderabbit', 'pr-agent', 'sourcery']`; `refusal_patterns` → 1 / 0 / 2, matching `coderabbit.md:54–55`, `pr-agent.md:128`, `sourcery.md:42–44` |
| 16 | Build gate: "`=== verify: SUCCESS ===`, 19606 passed, 14 skipped" | **UNVERIFIABLE** | The tree has moved many commits; the full build was not re-run per the task's instruction |
| 17 | Sub-agent finding 5: "No production change, no stale claims" | **ACCURATE as scoped** (to the report's own claims) — but the cold read **missed** the stale prose cluster (G5 here, `010-…/gaps.md` § G4 for the rest) | See *Completeness review* |
| 18 | "No production change" | **ACCURATE** | `git show --stat 38548923` → rename (0 bytes) + `report-01.md` (+311) + `test_github_pr.py` (+48) |
| 19 | Contract check row 3: "plan directory … present on arrival; no repair needed" | **ACCURATE** | The parenthetical attaches to the first-instruction block; the rename `110-….md → 110-…/plan.md` is separately disclosed |
| 20 | Residue: "None blocking … No follow-up owed" | **FALSE** | Three live defects in the surface this plan declares remain open at HEAD (G1, G2, G3), plus two unmet ⭐ obligations (G4, G6) |
| 21 | Reviewer participation table, merge-gate disposition, cost | **UNVERIFIABLE** | PR-runtime observations; not derivable from the tree |

**Line-number drift, not a finding.** Most `path:line` citations in `report-01.md` have moved
(`github_pr.py:929` → `:953`, `review_completeness.py:312` → `:377`, `_github_pr.py:400` → `:506`,
`branch-cleanup.md:784` → `:810`, `test_bot_participation_contract.py:650` → `:653`,
`test_github_pr.py:2370` → `:2408`). Two have not: `test_pre_merge_barrier.py:739` and
`test_legacy_bot_list_migration.py:137` still resolve exactly. All symbols resolve; the plan itself
declares line numbers navigational.

## Correctness review

**C1 — an unreadable head SHA silently converts a proven credit into a blocking stale verdict.
CONFIRMED, by reading and by probe.** `github_pr.py:904` reads the SHA; `_github_ci.fetch_pr_head_sha`
returns `''` on any failure. With `merge_candidate_sha == ''` and a ledger record present, `:705`
short-circuits on the falsy SHA and `:708` returns False for an unedited comment ⇒ `participated_stale`
(probe P1). The plan's Verification demanded the SHA-advance reset "is the one a monotonicity fix most
easily breaks"; the inverse — the reset firing when the SHA did **not** advance — is what happens here.
The `fetch_findings` return (`github_pr.py:1245–…`) carries **no** field reporting whether the SHA
resolved — the probe printed the full key set to confirm — so the caller cannot tell "stale because
HEAD moved" from "stale because the read failed", and `branch-cleanup.md`'s own UNKNOWN discipline
(`:774`: "An absent input is an UNKNOWN verdict, never a `false` the operator can act on") never fires,
because the return is `status: success`. Probe P4 adds the amplifier: the same fetch writes a ledger
row with an empty `reviewed_commit_sha` (`github_pr.py:970–974`), which keeps the bot stale at the next
real HEAD. The predicate-arm half of this is plan 010's `010-…/gaps.md` § G7; the missing resolution
signal is plan 110's. → G1.

**C2 — the filing dedup over-fires on an in-place edit, dropping real review content. CONFIRMED, by
reading and by probe P2.** `github_pr.py:1102`, keyed `(bot_kind, comment_id)` with no content or
timestamp term. This is the plan's own D2 defect statement, verbatim, and it survives the landing.
→ G2.

**C3 — a drifted refusal wording is credited as participation. CONFIRMED, by reading and by probe P3.**
`github_pr.py:950` → `_github_pr.py:183–187`. The registry layer is a substring match over
`refusal_patterns`; the structural layer requires **both** a limit-exceeded statement **and** a notice
shape (`_github_pr.py:150–152`). A vendor notice that satisfies neither reaches `:953`, matches a
declared publish shape (a refusal *is* published in one), and is credited. The plan flagged exactly this
as "a false credit with no signal"; the report never adjudicated it. → G3.

**Not defects, checked and cleared:**

- `_record_currency_records` writes only changed rows (the comprehension at `github_pr.py:989`), and
  `_recorded_currency_records` takes last-row-wins (`:617–623`), so the ledger is idempotent across
  repeated fetches at one SHA.
- The added test is not vacuous: it asserts a *conjunction* of two observables on one fetch, and
  mutation M2 shows it is the only test in the three exercised suites that catches a dedup coupling
  confined to the presence-credited bots.

**Checked and NOT cleared, contrary to a first reading:** the participation loop's
`if not _bot_kind or _bot_kind in participated: continue` (`:943`) does not strand a bot in
`stale_participation` — the return filters `if bot not in participated` (`:1270`) — but that same
short-circuit plus subtraction is the mechanism by which a bot's *second* evidence comment bypasses the
currency test and hides the bypass from `stale_participation_bots[]` (probe P5). It is a defect, owned
by `010-…/gaps.md` § G1.

## Completeness review

**Seven prose passages, in five files, still state the retired pre-#1141 currency predicate.** The
production module's own comment (`github_pr.py:576–582`) records that `updated_at != created_at` is a
closed hole — "once a comment is edited at some commit, `updated_at != created_at` stays true forever,
so every later HEAD advance would keep crediting it" — and
`test_edit_at_one_commit_does_not_credit_a_later_commit` (`test_github_pr.py:2360`) pins the fix. Yet:

| # | Site | Text | Why it is stale |
|---|---|---|---|
| 1 | `automatic-review/standards/bot-participation-contract.md:233` | "it was **edited in place** (`updated_at` differs from `created_at`) since it was posted" | States the **closed hole** as the current rule. The code compares against the **recorded** `updated_at` (`github_pr.py:707–708`) |
| 2 | `.../bot-participation-contract.md:230–232` and `:491–496` | "the `reviewed_commit_sha` stamped on the stored finding, or … the noise sidecar" … "evaluates the currency rule against the **union** of the stored-finding SHAs and the recorded sidecar SHAs" | The code reads **one** source. `github_pr.py:909–911`: the ledger "is the SOLE currency source, so a comment stored as a finding and a comment dropped as noise are treated identically." There is no union |
| 3 | `workflow-integration-github/SKILL.md:129` | "the comment is first-present or its `updated_at` has moved" | Omits the SHA-currency arm entirely — the anchor #1141 introduced |
| 4 | `automatic-review/SKILL.md:652` | "only on first presence or observed `updated_at` movement" | Same omission |
| 5 | `automatic-review/standards/pr-agent.md:86` | "Evidence therefore requires first presence OR updated_at movement." | Same omission, inside the machine-readable registry block |
| 6 | `.../pr-agent.md:363–364` | "evidence requires either **first presence** … or observed **`updated_at` movement**" | Same omission, in the registry doc a reader consults first |
| 7 | `automatic-review/scripts/bot_registry.py:486–487` (docstring) | "evidence requires either first presence (the comment is newly observed) or observed `updated_at` movement" | Prose-bearing string in **production code** |

This is the plan's own thesis turned on the plan: the rule is enforced by prose, and the prose now
disagrees with the code in the direction that re-teaches the defect.

Passages 1, 2 and 4–7 are already filed, with the same reading, as `010-…/gaps.md` § G4 (which also
picks up test prose in `test_pr_agent_contentless_guide_interaction.py`). Passage **3** —
`workflow-integration-github/SKILL.md:129` — is **not** in that entry and is **not** reachable by the
search that entry states (`"first presence|first-presence|updated_at movement|updated_at.*created_at"`
does not match "first-present or its `updated_at` has moved"). It is therefore the one passage plan 110
carries as its own gap. → G5.

**The refusal fixture is bot-derived, not wording-derived, and is vacuous on an empty pattern set.**
The plan wrote: "assert that each registered bot's known refusal **wordings** classify as refusals.
⛔ Not a hand-list — the fixture must publish the **population size it ranged over**; a check that can
pass over an empty pattern set is the vacuous-guard archetype again." `_refusal_body`
(`test_refusal_recovery_arming.py:61–74`) returns `declared[0]` — one wording — and, for a bot with
none, a synthetic structural notice. Consequences, all CONFIRMED by reading:

- pr-agent (`refusal_patterns` EMPTY, confirmed by calling `bot_registry.refusal_patterns('pr-agent')`)
  passes `test_every_registered_bots_refusal_is_detected` by exercising the **structural fallback**,
  not any declared wording.
- sourcery's second declared pattern (`"reached your weekly rate limit of"`, `sourcery.md:44` — the
  one the run's own PR observed live) is never swept by the arming suite.
- No test publishes the refusal-pattern population size. The declared-wording population is 3 pairs
  (coderabbit 1, pr-agent 0, sourcery 2). → G4.

**`workflow-integration-github/SKILL.md` is a consumer of the `participated_bots` claim that D0 did not
enumerate.** `SKILL.md:129` *defines* the credit rule for readers and agents; D0's table does not list
it at all (`automatic-review/SKILL.md:652` is listed, but as a call site rather than as a restatement
to check). Both are stale — see the table above.

**The plan's Notes redefined the population and the report used the narrower one.** The Notes state the
population is "every site that decides whether a comment represents NEW INFORMATION … Three members are
known: the wait completion predicate, the movement predicate, and this dedup." The report's tables
enumerate `participated_bots` consumers and `participation_evidence` readers instead. Of the three
named members, the movement predicate is gone (replaced by `_reviewed_at_merge_candidate`) and the dedup
is covered, but the **wait completion predicate** — whose arm keys on "the LATER of that comment's
`updated_at` / `created_at` moving strictly past the wait-start"
(`tools-integration-ci/standards/api-contract.md:159`, restated at
`workflow-integration-github/SKILL.md:355–364`) — is classified nowhere. It remains timestamp-anchored
rather than SHA-anchored; whether that is a defect is *not* established here and is left as an open
question rather than asserted. → G10.

**A stale count inside the very test that derives the call-site population.**
`test_confirmed_site_carries_its_own_flag_set_fully_quoted`'s docstring
(`test_bot_participation_contract.py:982–983`) says "the pre-merge barrier passes five flags, not the
participation guard's six", while `_CONFIRMED_SITES` (`:817–846`) declares **6** for both family-A
sites and the comment above it (`:805–810`) says six for both. The docstring contradicts the data it
documents. → G9.

## Out-of-scope compliance

Clean. `git show --stat 38548923` is exactly three paths: the plan rename (0 bytes changed),
`report-01.md`, and one test file.

- "Authoring another prose rule" — not violated; no standards document was touched.
- "A retry loop against a vendor's range-consumption behaviour" — not violated; no retry logic added.
- "Absorbing the naming defect a shipped sibling plan owns" — not violated.
- "Re-deriving why an earlier `responded_bots` union was retired" — not violated; the report does not
  re-derive it.

The `test(...)` commit type matches the content (test-only). The branch was the harness-assigned
`claude/participation-lossy-view-sqtb8u`, which the lane permits and the report discloses.

## Residue status

The report records exactly two residue items.

| Residue item | Status in the tree |
|---|---|
| "None blocking. The plan's production goal … is met at HEAD by #1141; this run added the one uncovered regression guard and verified the rest. **No follow-up owed.**" | **REFUTED.** Three live defects in this plan's declared surface remain open at HEAD (G1 at `github_pr.py:703–708`, G2 at `github_pr.py:1102`, G3 at `github_pr.py:950` + `_github_pr.py:183–187`), plus two unmet ⭐ obligations (G4, G6). No later commit closed any of them: `git log --oneline --follow -- .../github_pr.py` shows the last change as `9e9e9880` (#1241), which touched the size-cap path, not the currency or dedup paths |
| "Optional-bot re-review (coderabbit/sourcery rate-limited) — routine, outside our control" | **Closed by construction** — a PR-runtime condition with no tree artifact |

## Summary

**Counts by severity:** 4 major, 7 minor, 0 blockers. Eleven gaps total, all actionable and recorded in
`gaps.md`. Findings that land on plan 010's surface (the second-comment bypass, the empty-SHA predicate
arms, six of the seven stale prose passages) are cited above and left filed there rather than
duplicated.

**Bottom line.** The plan's central finding is correct and independently reproducible: both target
defects were real before #1141 and are genuinely gone at HEAD, the added regression guard exists,
passes, and is the only test in three suites that catches a dedup coupling confined to the
presence-credited bots, and the landing respected every out-of-scope boundary. Where the run falls short
is on the obligations the plan marked ⭐ and ⛔ around the edges of the refutation. It recorded "no
follow-up owed" over a surface that still contains three live defects, each reproduced here by driving
the real producer: a transient head-SHA read failure silently converting a proven reviewer into a
*blocking* `participated_stale` with no distinguishing signal in the return; the filing dedup still
keyed on `comment_id` alone, so an in-place-edited review's new content is credited as participation but
dropped before triage (the plan's own D2 defect, verbatim); and a drifted vendor refusal wording still
reaching the participation credit as a false positive. It also declared two ⭐ obligations satisfied
that the tree does not satisfy — the `auto_on_push` / `requires_explicit_trigger` record exists nowhere,
and the "population-derived refusal fixture" sweeps bots rather than wordings and passes over the one
bot with an empty pattern set. Finally, seven prose passages — including one docstring in production
code and both SKILL.md definitions of what `participated_bots[]` credits — still state the retired
pre-#1141 predicate, which is precisely the "the rule is enforced by prose, and the prose is wrong"
mechanism this plan was written to close.

## Adversarial review

This document and `gaps.md` were re-derived from scratch against the tree by a second, independent
reviewer working without the first reviewer's context. Method and outcome:

**What was re-derived.** Every load-bearing finding, by opening the cited file and reading the lines;
every count, by re-running the search that produces it; every claim about executable behaviour, by
running it. Five probes (P1–P5 in *Method*) drove the real `cmd_fetch_findings` through the existing
test helpers to settle C1, C2, C3, the ledger-poisoning amplifier, and the reach of D3(c). Two
mutations (M1, M2 in *Method*) established the added test's discrimination and its uniqueness, with the
file's bytes snapshotted to `$TMPDIR/adv-110-mutsweep/` and restored from that snapshot, never by a git
operation. `git status --porcelain` was re-checked clean afterwards.

**Upheld.** C1, C2 and C3 as live defects — each now backed by a probe rather than by code reading
alone. The D0 refutation both ways (defect present at `fddc4ec8`, absent at HEAD). `_has_update_movement`
absent from production. The `[0]` classification (four test readers, three production LIST readers).
The trigger-semantics ⭐ unmet. The refusal-fixture ⭐ unmet. All seven stale prose passages, each
citation opened and confirmed. The population figures (3 bots, 3 declared refusal wordings). The added
test's presence, greenness and discrimination.

**Overstated, corrected here.** "Six prose sites" was a table-row count that omitted the contract's
second union statement — it is seven passages in five files, six of which plan 010 already owns.
"`existing_comment_keys` … → 4 hits" — the grep returns 3. "Every `path:line` in `report-01.md` has
moved" — two do not (`test_pre_merge_barrier.py:739`, `test_legacy_bot_list_migration.py:137`). The grep
offered as producing the stale-prose population does not reach the contract's union claim, and the
Done-when grep proposed in the old G4 would have reached zero while three passages stayed stale.
`TestCallSitePopulation` derives the **documented call-site** population and asserts flag quoting, not
each site's class — the old G8 called it "the test that actually derives the consumer population".
Report-claim row 12 (D3(b)/(c) "ACCURATE") is accurate only for one comment per bot.

**Refuted.** Nothing in the previous document was found false in substance. The plan's own figure of
"seven registry-derived consumers" of `participation_evidence(bot)[0]` is not reproducible — four call
sites at HEAD and the same four at the landing commit — and the previous document's flat "refuted" is
softened to "not reproducible", since what the plan counted cannot be recovered.

**Could not verify.** The build-gate figures (`19606 passed, 14 skipped`) and every PR-runtime
observation — the reviewer-participation table, the merge-gate disposition, the cost section — remain
unverifiable from the clone. They are not refuted.

**Citations repaired.** `TestCallSitePopulation` `:829–960` → `:944–1010`; `_refusal_body` `:62–74` /
`:64–74` → `:61–74`; `test_second_fetch_dedupes_all_bot_kinds` `:139` → `:135`;
`fetch_pr_comments_data` `github_ops.py:388–460` → `:356–465`; the `participation_evidence` membership
test attributed to `check_completeness` → `parse_participation` (`:335–379`), with `check_completeness`
at `:708`; `pr-agent.md:74–78` → `:75–79`; the taxonomy sweep `:600–680` → `:596–679`;
`_UPDATE_REQUIRING_BOTS` `:2316` → `:2313`; `_BOT_KIND_TO_LOGIN` `:2320` → `:2319`;
`_recorded_currency_records` last-row-wins `:622` → `:617–623`; `_record_currency_records` filter
`:990` → `:989`.

**Added.** Two findings the previous pass missed: a stale flag count inside
`TestCallSitePopulation`'s own docstring (G9), and the wait-completion predicate left unclassified
against the population the plan's Notes redefined (G10). One coverage limit was added to D3(c) —
the SHA-advance reset is pinned only for the single-comment shape — recorded here and left filed on
plan 010 rather than duplicated. `gaps.md` was renumbered contiguously and re-ordered by severity;
the previous G4 (the stale-prose cluster) was narrowed to the one passage plan 010's sweep does not
reach, and the previous G8's characterisation of `TestCallSitePopulation` was corrected.

**Verdict.** Unchanged: **verified-with-gaps**. The headline refutation survives independent
re-derivation; the residue is larger and better evidenced than the run recorded.
