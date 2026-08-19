# Verification — 110-participation-derived-from-a-lossy-view

**Landed as:** PR #1219, squash commit `38548923`
**Verdict:** verified-with-gaps

The plan's headline outcome is sound and independently reproducible: both target defects were real
before `50f67ed2` (#1141) and are genuinely absent at HEAD, the one uncovered regression guard was
added, it passes, and it discriminates against a mutation no pre-existing test catches. No production
code was touched. What the report does not carry is the residue: three live defects in the surface
this plan owns, eight stale prose passages restating the retired predicate, and two ⭐ obligations
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
  created_at" marketplace/bundles/` → **6** text hits (plus two `__pycache__` binaries): five stale
  doc/docstring restatements, and `github_pr.py:578`, which is the in-source comment recording the
  closed hole (not stale). Neither the contract's *union* claim nor its
  `updated_at`-differs-from-`created_at` sentence is reachable by that grep; both were found by
  reading `bot-participation-contract.md` §§ around `:230` and `:488`. That grep alone therefore
  under-reports the population by three passages — the reason plan 010's entry runs two passes.
- `grep -rn "auto_on_push\|requires_explicit_trigger" marketplace/ test/ doc/` → hits **only** inside
  this plan's own `plan.md`, `verification.md` and `gaps.md`; **zero** in `marketplace/`, `test/`, or
  any other `doc/` file.
- `grep -rn "head_sha=''" test/plan-marshall/` → two hits, both in tracked files:
  `test_github_pr.py:2479` (the both-fetches-fail case) and an unrelated `test_ci_verify.py:339`.

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

Mutation sweep (`github_pr.py`'s bytes snapshotted to a scratch directory and restored from that
snapshot — never by a git operation; `git status --porcelain` re-checked clean after each pass). Each
mutation was run against the same three suites: `test_github_pr.py`, `test_pre_merge_barrier.py`,
`test_bot_participation_contract.py` (178 tests).

- **M1 — re-couple participation to the storage dedup for all bots** (a `continue` on
  `(bot_kind, comment_id) in existing_comment_keys` at the top of the participation loop):
  **6 fail** — `test_a_deduped_comment_is_still_credited_as_participating`, plus
  `test_second_fetch_at_the_same_head_stays_participated`,
  `test_review_predating_the_merge_candidate_is_stale`,
  `test_edit_at_one_commit_does_not_credit_a_later_commit`,
  `test_in_place_edit_credits_participation_after_a_head_advance` and
  `test_unresolvable_head_sha_fails_closed_and_stays_idempotent`, each `[pr-agent]`.
- **M2 — re-couple only the presence-credited bots** (the same guard, gated on `not
  _requires_update`): **only** `test_a_deduped_comment_is_still_credited_as_participating` fails; the
  other 177 pass.
- **M3 — the naive monotonicity fix** (`_reviewed_at_merge_candidate` returns True unconditionally):
  **3 fail** — `test_review_predating_the_merge_candidate_is_stale`,
  `test_edit_at_one_commit_does_not_credit_a_later_commit` and
  `test_unresolvable_head_sha_fails_closed_and_stays_idempotent`, each `[pr-agent]`.

M2 is what establishes the added test's unique value: the pre-existing currency suite already covers
the requires-update half of M1, so the guard this plan added is load-bearing specifically for the
presence-credited bots. M1 and M3 together discharge an obligation the run left open — the plan's
Verification demanded "every D3 case proven discriminating by mutation" and the run mutation-proved
only case (a). M1 fails D3(b)'s test; M3 is the exact shape the plan named as the risk ("case (c) is
the one a monotonicity fix most easily breaks") and it fails D3(c)'s two tests. Cases (a), (b) and (c)
are therefore now mutation-proven; case (d) is not, and its weakness is recorded as G7 and G9 rather
than as a mutation gap.

The full build was not re-run.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | Both defects re-established or refuted at HEAD, and the consumer population published with each member classified | Both REFUTED (fixed by #1141); 4-site consumer table + 8-site `participation_evidence` table published; ordering dependency is test-fixture-only; cross-plan collision resolved | Refutation CONFIRMED against `fddc4ec8` (defect present) vs HEAD (absent). Consumer table correct but **incomplete**: `workflow-integration-github/SKILL.md` — which *defines* what `participated_bots[]` credits — is not enumerated at all, and the wait-completion predicate the plan's Notes named as a population member is classified nowhere. Three plan claim-labels were never adjudicated | met-with-gaps |
| D1 | A bot proven on call 1 is still credited on call 2 at an unchanged head SHA, and advancing the SHA resets the credit | "Already satisfied at HEAD by #1141; no production change"; trigger semantics "already registry data" | Core property CONFIRMED (`test_second_fetch_at_the_same_head_stays_participated`, `test_review_predating_the_merge_candidate_is_stale`). But monotonicity **breaks on an unreadable head SHA** (P1 → G1), and the ⭐ `auto_on_push` / `requires_explicit_trigger` record **does not exist** (G5) | partially met |
| D2 | The participation predicate's input no longer passes through the storage dedup, and the identity used for "seen this review" is stated explicitly | "Already satisfied at HEAD by #1141"; identity stated as `(reviewed_commit_sha, updated_at)` vs `(bot_kind, comment_id)` | Decoupling CONFIRMED. Identity stated. But the plan's own *"the defect, verified in source"* — `comment_id` alone over-firing so an **edited-in-place review's new content is dropped** — is **still live** at `github_pr.py:1102`, reproduced by P2, and is not disclosed (G2) | met literally, incomplete substantively |
| D3 | (a) deduped bot still credited; (b) call-2 credit at unchanged HEAD; (c) SHA advance resets; (d) consumer population derived + non-empty-asserted + every member covered; ⭐ population-derived refusal fixture publishing its population size | (a) ADDED and mutation-proven; (b)(c)(d) ALREADY COVERED | (a) CONFIRMED present, passing, and uniquely discriminating (M2). (b) CONFIRMED. (c) CONFIRMED **for the single-comment shape only** — P5 shows a bot with two evidence comments keeps its credit across a HEAD advance. (d) the call-site half is partly covered by `TestCallSitePopulation`, a test the report never cites and which asserts flag quoting rather than each site's class; the three tests it *does* cite enumerate the **bot** population (G7), and two members of the population the plan's Notes defined are classified nowhere (G9). The ⭐ refusal fixture is **not** wording-derived and **does** pass over an empty pattern set (G4) | partially met |

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
  (`_github_pr.py:155–187`, its two-layer test at `:183–187`) is a `refusal_patterns` substring match
  **or** the structural `_is_rate_limit_notice`. A reworded vendor notice that matches neither falls
  through to `github_pr.py:953`, matches a declared publish shape, and is **credited as
  participation**. See G3.
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
bots (`coderabbit.md:37`, `pr-agent.md:62`, `sourcery.md:30`), so it discriminates nothing. See G5.

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
one comment per bot. Within that scope the case is genuinely discriminating: mutation M3 — the naive
"always credit" monotonicity fix the plan named as the risk — makes both D3(c) tests fail.

D3(d) is the weak half — see G4, G7 and G9.

## Report-claim audit

| # | Claim in `report-01.md` | Verdict | Evidence |
|---|---|---|---|
| 1 | "Both defects … REFUTED at HEAD — already fixed by … #1141, squash `50f67ed`" | **ACCURATE** | `50f67ed2` in `git log --follow`; defect present at `fddc4ec8`, absent at HEAD |
| 2 | Participation derived over `raw_comments` "before any noise / duplicate / resolved filtering" | **ACCURATE** | `github_pr.py:917–941` (the comment) and `:941–975` (the loop) |
| 3 | "The storage dedup … is consulted **only** in the separate finding-storage loop" | **ACCURATE** | `grep -n "existing_comment_keys"` → 3 hits: `:897`, `:911` (comment), `:1102` |
| 4 | "`_reviewed_at_merge_candidate`, a **pure SHA comparison** … identical however many times it is evaluated" | **OVERSTATED** | True for the ledger-hit path. The first-observation arm returns `bool(merge_candidate_sha)` (`:703`), so the verdict is a function of ledger state *and* of whether the SHA read succeeded — it flips after a failed read (P1 → G1) |
| 5 | Consumer table C1–C4, "None of C2–C4 reads a deduped projection" | **ACCURATE but INCOMPLETE** | `branch-cleanup.md:810` retains the producer's sets; `review_completeness.py:377` tests LIST membership. Missing from the enumeration: `workflow-integration-github/SKILL.md:129`, which *defines* the credit rule and states it wrongly (filed on `010-…/gaps.md` § G4), and the wait-completion predicate the plan's Notes named (G9) |
| 6 | "every FIRST-ELEMENT (`[0]`) reader is a test fixture; no production participation decision reads `[0]`" | **ACCURATE** | 4 test `[0]` readers, 3 production LIST readers — full grep in *Method*; the same four at `38548923` |
| 7 | "`_has_update_movement` no longer exists … nothing to port" | **ACCURATE** | `grep -rn "_has_update_movement"` → `doc/plans/` prose only |
| 8 | D1 "Already satisfied at HEAD by #1141; no production change" | **OVERSTATED** | Core property holds; the unreadable-SHA flip (G1) and the missing trigger-semantics record (G5) are unmet |
| 9 | "Per-bot trigger semantics are already registry data (`participation_requires_update`, `trigger_comment`, `rate_limit_class`)" | **FALSE** as a satisfaction of the ⭐ | `grep -rn "auto_on_push\|requires_explicit_trigger" marketplace/ test/ doc/` → nothing outside this plan's own text. None of the three fields encodes auto-on-push vs explicit-trigger; `trigger_comment` is non-empty for all three bots |
| 10 | D2 "Already satisfied at HEAD … The identity … is stated explicitly" | **PARTIALLY ACCURATE** | Decoupling and identity-statement CONFIRMED; the plan's stated over-firing half is still live at `:1102` (probe P2) and undisclosed (G2) |
| 11 | D3(a) "New test … asserting … `count_skipped_duplicate == len(_COMMENTS)` … Mutation-proven" | **ACCURATE** | Test at `test_github_pr.py:166–206`; runs green; discrimination re-proven independently by mutations M1 and M2 |
| 12 | D3(b)/(c) "ALREADY COVERED by `test_second_fetch_at_the_same_head_stays_participated` / `test_review_predating_the_merge_candidate_is_stale` / `test_edit_at_one_commit_does_not_credit_a_later_commit`" | **ACCURATE AS SCOPED** | All three exist and assert what is claimed. Each publishes one comment per bot, so the D3(c) property is pinned only for the single-comment shape — probe P5 breaks it with two (production half: `010-…/gaps.md` § G1) |
| 13 | D3(d) consumer population "ALREADY COVERED" by `test_at_least_one_registered_bot_requires_update_movement`, `test_currency_anchor_is_recorded_in_the_ledger_on_credit`, and the taxonomy sweep | **OVERSTATED** | All three exist, but each derives the **bot** population, not the consumer population. The nearest genuine coverage is `TestCallSitePopulation` (`test_bot_participation_contract.py:944–1010`), which scans `marketplace/bundles/**/*.md` via `_scan_invocation_sites()` (`:860–893`) for both invocation families with a per-family vacuity guard (`:948`) — and the report never cites it. That test asserts each site's flag count and quoting, not each site's class, so the half D3(d) asked for is pinned by no test (G7, G9) |
| 14 | D3(d) refusal fixture "population-derived … both swept over `_registered_bots()` with a non-empty guard" | **OVERSTATED** | Swept over **bots**, not over **wordings**. `_refusal_body` (`test_refusal_recovery_arming.py:61–74`) uses `declared[0]` only and **falls back to a synthetic notice** when a bot declares none, so `test_every_registered_bots_refusal_is_detected` (`:99`) passes for pr-agent while testing nothing pr-agent declares; `test_a_bots_declared_refusal_is_recognized_as_DATA` `pytest.skip`s for it (`:242–243`). Sourcery's second declared pattern is never swept. No test publishes the refusal-pattern population size (G4) |
| 15 | Population sizes: 3 registered bots; refusal patterns total 3 (coderabbit 1, sourcery 2, pr-agent 0) | **ACCURATE** | `bot_registry.bot_kinds()` → `['coderabbit', 'pr-agent', 'sourcery']`; `refusal_patterns` → 1 / 0 / 2, matching `coderabbit.md:54–55`, `pr-agent.md:128`, `sourcery.md:42–44` |
| 16 | Build gate: "`=== verify: SUCCESS ===`, 19606 passed, 14 skipped" | **UNVERIFIABLE** | The tree has moved many commits; the full build was not re-run per the task's instruction |
| 17 | Sub-agent finding 5: "No production change, no stale claims" | **ACCURATE as scoped** (to the report's own claims) — but the cold read **missed** the stale prose cluster entirely (all eight passages, filed as `010-…/gaps.md` § G4) | See *Completeness review* |
| 18 | "No production change" | **ACCURATE** | `git show --stat 38548923` → rename (0 bytes) + `report-01.md` (+311) + `test_github_pr.py` (+48) |
| 19 | Contract check row 3: "plan directory … present on arrival; no repair needed" | **ACCURATE** | The parenthetical attaches to the first-instruction block; the rename `110-….md → 110-…/plan.md` is separately disclosed |
| 20 | Residue: "None blocking … No follow-up owed" | **FALSE** | Three live defects in the surface this plan declares remain open at HEAD (G1, G2, G3), plus two unmet ⭐ obligations (G4, G5) |
| 21 | Reviewer participation table, merge-gate disposition, cost | **UNVERIFIABLE** | PR-runtime observations; not derivable from the tree |

**Line-number drift, not a finding.** Every `path:line` citation in `report-01.md` was re-opened.
Exactly two still resolve at the line given — `test_pre_merge_barrier.py:739` and
`test_legacy_bot_list_migration.py:137`. Every other one has moved: `github_pr.py:929` → `:953`,
`:917–951` → `:941–975`, `:1062` → `:1102`, `review_completeness.py:312` → `:377`,
`_github_pr.py:400` → `:506`, `branch-cleanup.md:784` → `:810`,
`test_bot_participation_contract.py:650` → `:653` and `:700` → `:703`,
`test_github_pr.py:2370` → `:2408`. All symbols resolve; the plan itself declares line numbers
navigational.

One citation is wrong about the symbol, not the line. `report-01.md`'s consumer table row C4 attributes
the `participation_evidence` membership test to `review_completeness.check_completeness`; the membership
test lives in `parse_participation` (`review_completeness.py:377`), and `check_completeness` begins at
`:708`. The behavioural claim the row makes is unaffected.

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

**Eight prose passages, in five files, still state the retired pre-#1141 currency predicate.** The
production module's own comment (`github_pr.py:576–582`) records that `updated_at != created_at` is a
closed hole — "once a comment is edited at some commit, `updated_at != created_at` stays true forever,
so every later HEAD advance would keep crediting it" — and
`test_edit_at_one_commit_does_not_credit_a_later_commit` (`test_github_pr.py:2360`) pins the fix. Yet:

| # | Site | Text | Why it is stale |
|---|---|---|---|
| 1 | `automatic-review/standards/bot-participation-contract.md:233` | "it was **edited in place** (`updated_at` differs from `created_at`) since it was posted" | States the **closed hole** as the current rule. The code compares against the **recorded** `updated_at` (`github_pr.py:707–708`) |
| 2 | `.../bot-participation-contract.md:230–232` | "the `reviewed_commit_sha` stamped on the stored finding, or … the merge-candidate SHA the noise sidecar recorded when the comment was first observed" | The code reads **one** source. `github_pr.py:909–911`: the ledger "is the SOLE currency source, so a comment stored as a finding and a comment dropped as noise are treated identically" |
| 3 | `.../bot-participation-contract.md:491–496` | "evaluates the currency rule against the **union** of the stored-finding SHAs and the recorded sidecar SHAs" | Same two-source model, stated as an explicit union. There is no union and no findings-derived SHA source |
| 4 | `workflow-integration-github/SKILL.md:129` | "the comment is first-present or its `updated_at` has moved" | Omits the SHA-currency arm entirely — the anchor #1141 introduced |
| 5 | `automatic-review/SKILL.md:652` | "only on first presence or observed `updated_at` movement" | Same omission |
| 6 | `automatic-review/standards/pr-agent.md:86` | "Evidence therefore requires first presence OR updated_at movement." | Same omission, inside the machine-readable registry block |
| 7 | `.../pr-agent.md:363–364` | "evidence requires either **first presence** … or observed **`updated_at` movement**" | Same omission, in the registry doc a reader consults first |
| 8 | `automatic-review/scripts/bot_registry.py:486–487` (docstring) | "evidence requires either first presence (the comment is newly observed) or observed `updated_at` movement" | Prose-bearing string in **production code** |

This is the plan's own thesis turned on the plan: the rule is enforced by prose, and the prose now
disagrees with the code in the direction that re-teaches the defect.

**All eight are filed on plan 010, so plan 110 files none of them.** `010-…/gaps.md` § G4 ("Sweep the
eight prose sites that still describe the deleted two-arm predicate or its abandoned two-source
anchor") enumerates the same eight paths — `workflow-integration-github/SKILL.md:129` included, as its
first entry — plus test prose in `test_pr_agent_contentless_guide_interaction.py`. It also states why
one grep is not enough and runs two passes, the second (`first.present|updated_at (has )?mov|union of
the stored|sidecar`) written specifically to reach `SKILL.md:129` and both two-source paragraphs. Each
of the eight citations was opened here and confirmed to carry the quoted text. Nothing in this cluster
is uniquely plan 110's, so per this document's own rule it stays filed on 010 rather than being
duplicated into `gaps.md` beside this file.

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
question rather than asserted.

A **fourth** member the plan's own D2 paragraph names is likewise unclassified: the start-anchored
body filter `_is_self_authored_response` (`github_pr.py:368`, called at `:1069`), whose docstring
states in full why it exists — *"the `(bot_kind, comment_id)` dedup cannot fire because each turn
posts a comment with a NEW id"* (`:374–377`). That is the under-firing direction of the plan's ⭐⭐
"the dedup key is wrong in BOTH directions", surviving in production as a third identity for "have I
seen this", and neither the report nor the previous pass placed it in the population. The contract's
§ "Recorded exclusions" (`bot-participation-contract.md:667–676`) records a deliberate exclusion for
the await predicate's *test*, but on the taxonomy-vocabulary question, not on this plan's D0 class
question. → G9.

**A stale count inside the very test that derives the call-site population.**
`test_confirmed_site_carries_its_own_flag_set_fully_quoted`'s docstring
(`test_bot_participation_contract.py:982–983`) says "the pre-merge barrier passes five flags, not the
participation guard's six", while `_CONFIRMED_SITES` (`:817–846`) declares **6** for both family-A
sites and the comment above it (`:804–810`) says six for both, naming the reason ("it forwards the
trigger-A `--declined-bots` observation"). The docstring contradicts the data it documents. → G8.

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
| "None blocking. The plan's production goal … is met at HEAD by #1141; this run added the one uncovered regression guard and verified the rest. **No follow-up owed.**" | **REFUTED.** Three live defects in this plan's declared surface remain open at HEAD (G1 at `github_pr.py:703–708`, G2 at `github_pr.py:1102`, G3 at `github_pr.py:950` + `_github_pr.py:183–187`), each reproduced here by driving the real producer, plus two unmet ⭐ obligations (G4, G5). No later commit closed any of them: `git log --oneline --follow -- .../github_pr.py` shows the last change as `9e9e9880` (#1241), which touched the size-cap path, not the currency or dedup paths |
| "Optional-bot re-review (coderabbit/sourcery rate-limited) — routine, outside our control" | **Closed by construction** — a PR-runtime condition with no tree artifact |

## Summary

**Counts by severity:** 4 major, 6 minor, 0 blockers. Ten gaps total, all actionable and recorded in
`gaps.md`. Findings that land on plan 010's surface (the second-comment bypass, the empty-SHA predicate
arms and ledger poisoning, and all eight stale prose passages) are cited above and left filed there
rather than duplicated.

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
bot with an empty pattern set. Finally, eight prose passages — including one docstring in production
code and both SKILL.md definitions of what `participated_bots[]` credits — still state the retired
pre-#1141 predicate, which is precisely the "the rule is enforced by prose, and the prose is wrong"
mechanism this plan was written to close; that cluster is filed in full on plan 010 and is named here
only so the reach of the defect is on the record.

## Adversarial review

This document and `gaps.md` have been through two independent adversarial passes, each re-deriving
every load-bearing finding from the tree rather than carrying it on citation. This section states the
finished state: what is established, what is only reproducible in a weaker form than first written, and
what remains unverifiable from a clone.

**How the findings were established.** Every citation in this document and in `gaps.md` was opened at
the line given and read. Every count was re-derived by re-running the search that produces it. Every
claim about executable behaviour was executed. Probes P1–P5 (*Method*) drive the real
`cmd_fetch_findings` through the existing `_patch_provider` / `_publish_comment` helpers and settle C1,
C2, C3, the ledger-poisoning amplifier, and the reach of D3(c); P1, P2, P3 and P5 were re-run in the
second pass and reproduce identically. Mutations M1, M2 and M3 (*Method*) establish the added test's
discrimination, its uniqueness, and the discrimination of D3(b) and D3(c). Both passes snapshotted
`github_pr.py`'s bytes to a scratch directory and restored from that snapshot — never with a git
operation — and re-checked `git status --porcelain` clean afterwards; the baseline selection re-runs
green (6 passed, 83 deselected).

**Established.** C1, C2 and C3 as live defects, each backed by a probe. The D0 refutation both ways —
the pre-fix union at `fddc4ec8:839` feeding `_has_update_movement` at `:878–879`, gated on
`participation_requires_update`, and its absence at HEAD. `_has_update_movement` absent from
production (`git grep` returns `doc/plans/` prose only). The `[0]` classification: four test readers
and three production LIST readers at HEAD, the same four `[0]` readers at the landing commit. The
trigger-semantics ⭐ unmet and the refusal-fixture ⭐ unmet. All eight stale prose passages. The
population figures (3 registered bots; declared refusal wordings 1 / 0 / 2). The added test's presence,
greenness and unique discrimination — M2 leaves it the only failure among 178 tests.

**Reproducible only in a weaker form than first written.** The plan's figure of "**seven**
registry-derived consumers" of `participation_evidence(bot)[0]` is **not reproducible**: four call
sites at HEAD and the same four at `38548923`, none of them a production verdict. What the plan counted
cannot be recovered, so this is recorded as not-reproducible rather than as refuted. Report-claim row 12
(D3(b)/(c) "ACCURATE") holds only for one comment per bot — probe P5 breaks D3(c) with two, and the
production half of that is plan 010's.

**Corrected in the second pass.** The stale-prose cluster is **eight** passages in five files, not six
and not seven: the earlier counts were table-row counts that folded the contract's two two-source
statements together and, in the first form, omitted one of them. All eight are already filed as
`010-…/gaps.md` § G4, whose two-pass search reaches `workflow-integration-github/SKILL.md:129`
explicitly — so the claim that plan 110 uniquely owns that passage is **withdrawn**, and the
stale-prose entry is removed from `gaps.md` rather than narrowed. The grep offered in *Method* as
producing that population returns **6** text hits, five of them stale, not "6 plus one". M1 fails
**six** tests, not the two first named. The `path:line` drift statement is now exhaustive: exactly two
citations in `report-01.md` still resolve, and every other has moved. `TestCallSitePopulation` asserts
each site's flag count and quoting, never each site's class — so it covers the *population* half of
D3(d) and not the *classification* half.

**Could not verify.** The build-gate figures (`19606 passed, 14 skipped`) and every PR-runtime
observation — the reviewer-participation table, the merge-gate disposition, the cost section — are not
derivable from the clone. They are not refuted.

**Citations repaired.** `TestCallSitePopulation` → `:944–1010`; `_scan_invocation_sites` → `:860–893`;
the `_CONFIRMED_SITES` preamble `:805–810` → `:804–810`; `_refusal_body` → `:61–74`;
`test_a_bots_declared_refusal_is_recognized_as_DATA` `:234–249` → `:233–249`;
`test_second_fetch_dedupes_all_bot_kinds` `:139` → `:135`; `fetch_pr_comments_data` → `:356–465`;
the `participation_evidence` membership test attributed to `check_completeness` → `parse_participation`
(`:335–379`), with `check_completeness` at `:708`; `pr-agent.md:74–78` → `:75–79` and `:85` → `:84–85`;
the taxonomy sweep → `:596–679`; `_UPDATE_REQUIRING_BOTS` `:2316` → `:2313`; `_BOT_KIND_TO_LOGIN`
`:2320` → `:2319`; `_is_refusal_notice` `:183–187` → the function at `:155–187` with its two-layer test
at `:183–187`; the `fetch_findings` return dict `:1245–1300` → `:1245–1306`; the contract's
registry-consumer table `:658–665` → § "Consumers" `:653–666`;
`_recorded_currency_records` last-row-wins `:622` → `:617–623`; `_record_currency_records` filter
`:990` → `:989`.

**Added.** A stale flag count inside `TestCallSitePopulation`'s own docstring (G8). The population the
plan's Notes redefined, left unclassified — the wait-completion predicate and, newly, the
`_is_self_authored_response` body filter, which is the surviving production evidence for the
under-firing direction of the plan's ⭐⭐ "the dedup key is wrong in BOTH directions" (G9). An
unqualified idempotence sentence in `_reviewed_at_merge_candidate`'s own docstring (`:666–667`) that
probe P1 refutes, folded into G1's task rather than filed separately. And the discharge of the plan's
"every D3 case proven discriminating by mutation" obligation for cases (a), (b) and (c), which the run
had performed for (a) only.

**`gaps.md` state.** Renumbered contiguously G1–G10 and ordered by severity: G1–G4 major, G5–G10 minor.
Ten entries, every one an open item this document establishes; nothing this document refutes or
attributes to plan 010 remains actionable here.

**Verdict.** Unchanged: **verified-with-gaps**. The headline refutation survives two independent
re-derivations; the residue is larger and better evidenced than the run recorded, and smaller than the
first pass wrote, because the stale-prose cluster belongs wholly to plan 010.
