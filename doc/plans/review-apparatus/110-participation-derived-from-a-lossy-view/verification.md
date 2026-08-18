# Verification — 110-participation-derived-from-a-lossy-view

**Landed as:** PR #1219, squash commit `38548923`
**Verdict:** verified-with-gaps

The plan's headline outcome is sound and independently reproducible: both target defects were real
before `50f67ed2` (#1141) and are genuinely absent at HEAD, the one uncovered regression guard was
added and it passes, and no production code was touched. What the report does not carry is the
residue: three live defects in the surface this plan owns, six prose sites still restating the
retired predicate, and two ⭐ obligations recorded as "already satisfied" that the tree does not
satisfy.

## Method

Ground truth is the current tree at `61a43e53` on `claude/review-apparatus-analysis-mcf8md`.

Read in full: `plan.md`, `report-01.md`, `git show 38548923` (message + full diff), `git show --stat
38548923`.

Read in the current tree:

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
  — `_recorded_currency_records`, `_record_currency_records`, `_reviewed_at_merge_candidate`,
  `cmd_fetch_findings` (the participation loop, the storage-dedup site, the return dict).
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  — `_is_refusal_notice`, `_is_rate_limit_notice`, the `detector_answerable` derivation.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py`
  — `fetch_pr_comments_data` (which comment surfaces are walked).
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`,
  `review_completeness.py`.
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot-participation-contract,
  coderabbit,pr-agent,sourcery}.md`, `automatic-review/SKILL.md`,
  `workflow-integration-github/SKILL.md`,
  `phase-6-finalize/standards/branch-cleanup.md` § "Predicate 2".
- `test/plan-marshall/workflow-integration-github/test_github_pr.py`,
  `test_refusal_recovery_arming.py`,
  `test/plan-marshall/automatic-review/test_bot_participation_contract.py`.

History checks:

- `git log --oneline --follow -- .../github_pr.py` → located `50f67ed2` (#1141) and its predecessor
  `fddc4ec8` (#1118).
- `git show fddc4ec8:.../github_pr.py` → read the **pre-#1141** participation loop, which proves the
  defect was real (`observed_comment_keys = existing_comment_keys | recorded_dropped_keys`, fed
  straight into `_has_update_movement`).
- `git log -L 166,207:test/.../test_github_pr.py` → the added test's only later change is a docstring
  shortening in `d3ba81fd` (#1259); the body is intact.

Greps run (all repository-relative, all reported by count and by site):

- `grep -rn "participation_evidence" --include=*.py --include=*.md marketplace test` → 3 production
  readers, 5 test readers, plus registry/doc mentions.
- `grep -rn "participated_bots|participated-bots" marketplace test doc/developer` → the full consumer
  and restatement population.
- `grep -rn "_has_update_movement" --include=*.py --include=*.md .` → zero production hits; only
  `doc/plans/` prose.
- `grep -rn "first presence|first-present|updated_at movement|updated_at\` has moved|updated_at !=
  created_at" marketplace/bundles/` → the six stale prose sites listed under *Completeness review*.
- `grep -rn "auto_on_push|requires_explicit_trigger" marketplace test doc` → **zero hits anywhere in
  the tree.**
- `grep -rn "refusal_patterns" test/` → the refusal-fixture surface.
- `grep -rn "head_sha=''" test/plan-marshall/` → exactly two hits, one of them in
  `test_github_pr.py:2479`.
- `for t in <the seven test names the report claims>; do grep -rn "def $t" test/; done` → all seven
  exist.

Test run (no repository file modified):

```
UV_HTTP_TIMEOUT=600 uv run python -m pytest \
  test/plan-marshall/workflow-integration-github/test_github_pr.py -o addopts="" -q \
  -k "deduped_comment_is_still_credited or second_fetch_at_the_same_head or review_predating \
      or edit_at_one_commit or currency_anchor or at_least_one_registered_bot"
→ 6 passed, 83 deselected
```

The full build was not re-run.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | Both defects re-established or refuted at HEAD, and the consumer population published with each member classified | Both REFUTED (fixed by #1141); 4-site consumer table + 8-site `participation_evidence` table published; ordering dependency is test-fixture-only; cross-plan collision resolved | Refutation CONFIRMED against `fddc4ec8` (defect present) vs HEAD (absent). Consumer table correct but **incomplete**: the two SKILL.md sites that *define* what `participated_bots[]` credits are enumerated as call sites, not as claim restatements, and both restate the retired rule. Three plan claim-labels were never adjudicated | met-with-gaps |
| D1 | A bot proven on call 1 is still credited on call 2 at an unchanged head SHA, and advancing the SHA resets the credit | "Already satisfied at HEAD by #1141; no production change"; trigger semantics "already registry data" | Core property CONFIRMED (`test_second_fetch_at_the_same_head_stays_participated`, `test_review_predating_the_merge_candidate_is_stale`). But monotonicity **breaks on an unreadable head SHA** (G1), and the ⭐ `auto_on_push` / `requires_explicit_trigger` record **does not exist** (G6) | partially met |
| D2 | The participation predicate's input no longer passes through the storage dedup, and the identity used for "seen this review" is stated explicitly | "Already satisfied at HEAD by #1141"; identity stated as `(reviewed_commit_sha, updated_at)` vs `(bot_kind, comment_id)` | Decoupling CONFIRMED. Identity stated. But the plan's own *"the defect, verified in source"* — `comment_id` alone over-firing so an **edited-in-place review's new content is dropped** — is **still live** at `github_pr.py:1102` and is not disclosed (G2) | met literally, incomplete substantively |
| D3 | (a) deduped bot still credited; (b) call-2 credit at unchanged HEAD; (c) SHA advance resets; (d) consumer population derived + non-empty-asserted + every member covered; ⭐ population-derived refusal fixture publishing its population size | (a) ADDED and mutation-proven; (b)(c)(d) ALREADY COVERED | (a) CONFIRMED present and passing. (b)(c) CONFIRMED. (d) consumer half is covered — but by `TestCallSitePopulation`, a test the report never cites; the three tests it *does* cite enumerate the **bot** population, not the consumer population (G8). The ⭐ refusal fixture is **not** wording-derived and **does** pass vacuously over an empty pattern set (G5) | partially met |

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
`currency_records`; `existing_comment_keys` appears at exactly two places —
`github_pr.py:897` (construction) and `github_pr.py:1102` (the filing dedup). Search:
`grep -n "existing_comment_keys" .../github_pr.py` → 4 hits, none inside the participation loop.

One nuance the report does not record: the pre-fix coupling bit **only** `participation_requires_update`
bots. The plan's narrative that the dedup "emptied `participated_bots`" is therefore true for
pr-agent and false for the presence-credited bots. This does not change the refutation.

**Defect 2 was real, and is refuted at HEAD. CONFIRMED.** `_reviewed_at_merge_candidate`
(`github_pr.py:652–708`) reads the ledger written by *prior* fetches and compares
`recorded_sha == merge_candidate_sha`. `test_second_fetch_at_the_same_head_stays_participated`
(`test_github_pr.py:2431`) pins the call-2 credit; it passes.

**`_has_update_movement` is gone.** `grep -rn "_has_update_movement"` over `*.py`/`*.md` returns
only `doc/plans/` prose. The report's cross-plan-collision resolution is CONFIRMED.

**The `[0]` ordering classification is CONFIRMED and the plan's premise is corrected.** Production
readers, all LIST-valued: `github_pr.py:953` (`_kind not in participation_evidence(_bot_kind)`),
`review_completeness.py:377` (`evidence_kind in ...`), `_github_pr.py:506` (`all(not ...)`).
`[0]` readers, all test fixtures: `test_github_pr.py:2408`, `test_pre_merge_barrier.py:739`,
`test_bot_participation_contract.py:653`, `test_legacy_bot_list_migration.py:137`. The plan's claim
that "**seven** registry-derived consumers" read `[0]` is refuted — there are four, and none is a
production verdict. `pr-agent.md:74–78` independently documents the convention
("ORDERING IS LOAD-BEARING … `test_bot_participation_contract.py` reads element `[0]`").

**Three claim-labels the plan tabled were never adjudicated by the report.** Each is answered here:

- *"An unmatched refusal notice reaches the participation credit in our classifier"* — **CONFIRMED
  TRUE.** `github_pr.py:950` calls `_is_refusal_notice`; that function
  (`_github_pr.py:183–187`) is `refusal_patterns` substring-match **or** the structural
  `_is_rate_limit_notice`. A reworded vendor notice that matches neither falls through to
  `github_pr.py:953`, matches a declared publish shape, and is **credited as participation**. See G3.
- *"Inline-comment enumeration under-collects body-level findings"* — **REFUTED for
  `fetch_findings`.** `github_ops.fetch_pr_comments_data` (`github_ops.py:388–460`) walks three
  surfaces: `reviewThreads` → `inline`, `reviews` → `review_body`, `comments` → `issue_comment`. The
  producer does not read an inline-only endpoint.
- *"The completeness script computes no timestamp; the determination happens upstream"* — **CONFIRMED
  behaviourally.** `review_completeness.py` consumes `--participated-bots` and re-tests membership in
  `participation_evidence` (`:377`); no currency arithmetic occurs there.

### D1 — monotonicity at a fixed head SHA

The Done-when is met on the happy path. It is **not** met when `fetch_pr_head_sha` fails.
`_github_ci.fetch_pr_head_sha` returns `''` "on any failure path". Then, for a comment already
credited with `recorded_sha = A`:

```python
705:    if merge_candidate_sha and recorded_sha == merge_candidate_sha:   # False — sha is ''
706:        return True
707:    updated_at = str(comment.get('updated_at') or '')
708:    return bool(updated_at) and updated_at != recorded_updated_at      # False — unchanged
```

⇒ `participated_stale`, which is **blocking**, on a head SHA that never actually moved. The
docstring's idempotence claim is scoped to two *consecutive failed* reads, and
`test_unresolvable_head_sha_fails_closed_and_stays_idempotent` (`test_github_pr.py:2462`) tests
exactly that scoped case (`head_sha=''` on both fetches). The mixed case — credit, then a failed read
— is untested. Search backing the absence: `grep -rn "head_sha=''" test/plan-marshall/` → two hits
total, one in `test_github_pr.py:2479` (the both-fail case) and one in an unrelated
`test_ci_verify.py`. See G1.

The ⭐ "record per-bot trigger semantics explicitly (`auto_on_push` versus
`requires_explicit_trigger`, with the trigger command for the latter)" is **not** satisfied.
`grep -rn "auto_on_push|requires_explicit_trigger" marketplace/ test/ doc/` returns **zero hits**
outside this plan's own text. The three fields the report offers instead do not encode the
distinction: `participation_requires_update` is about *how a review is published*,
`rate_limit_class` is about *awaitability*, and `trigger_comment` is non-empty for every registered
bot, so it discriminates nothing. See G6.

### D2 — decoupling, and the identity

Decoupling CONFIRMED (above). Identity stated CONFIRMED (`github_pr.py:906–913`: the currency ledger
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
"a re-review EDITS that same comment in place" (`pr-agent.md:85`). So a pr-agent re-review that adds a
real finding to its persistent Guide is **credited as participation** (the fresh-edit arm fires) while
its **new content is dropped from filing** and never reaches triage or the pre-merge barrier's
pending-findings gate. The report reframes this as "a different question" and does not record it as
residue. See G2.

### D3 — the tests

The added test is `test_a_deduped_comment_is_still_credited_as_participating`
(`test/plan-marshall/workflow-integration-github/test_github_pr.py:166–206`). It exists, it passes,
and it is genuinely discriminating: the assertion `second['participated_bots'] ==
first['participated_bots']` (`:205`) is preceded by `second['count_skipped_duplicate'] ==
len(_COMMENTS)` (`:201`), so the deduped-and-still-credited conjunction is pinned on one fetch. Any
coupling of the participation loop to `existing_comment_keys` empties `participated` on the second
fetch, and the assertion fails. It also discriminates against the **historical** defect shape
(replacing the currency arm with `key not in existing_comment_keys`): the fixture comments carry no
`updated_at`, so the edit arm cannot rescue pr-agent, and `second['participated_bots']` would drop to
two members. The test is not redundant with its neighbour
`test_second_fetch_dedupes_all_bot_kinds` (`:139`), which asserts nothing about participation.

D3(b)/(c) coverage is real: `test_second_fetch_at_the_same_head_stays_participated` (`:2431`),
`test_review_predating_the_merge_candidate_is_stale` (`:2496`),
`test_edit_at_one_commit_does_not_credit_a_later_commit` (`:2360`).

D3(d) is the weak half — see G5 and G8.

## Report-claim audit

| # | Claim in `report-01.md` | Verdict | Evidence |
|---|---|---|---|
| 1 | "Both defects … REFUTED at HEAD — already fixed by … #1141, squash `50f67ed`" | **ACCURATE** | `50f67ed2` in `git log`; defect present at `fddc4ec8`, absent at HEAD |
| 2 | Participation derived over `raw_comments` "before any noise / duplicate / resolved filtering" | **ACCURATE** | `github_pr.py:917–941` |
| 3 | "The storage dedup … is consulted **only** in the separate finding-storage loop" | **ACCURATE** | `existing_comment_keys` appears at `:897` and `:1102` only |
| 4 | "`_reviewed_at_merge_candidate`, a **pure SHA comparison** … identical however many times it is evaluated" | **OVERSTATED** | True for the ledger-hit path. The first-observation arm returns `bool(merge_candidate_sha)` (`:703`), so the verdict is a function of ledger state *and* of whether the SHA read succeeded — it flips after a failed read (G1) |
| 5 | Consumer table C1–C4, "None of C2–C4 reads a deduped projection" | **ACCURATE but INCOMPLETE** | `branch-cleanup.md:810` retains the producer's sets; `review_completeness.py:377` tests LIST membership. Missing from the enumeration: the two SKILL.md sites that *define* the credit rule and state it wrongly (G4) |
| 6 | "every FIRST-ELEMENT (`[0]`) reader is a test fixture; no production participation decision reads `[0]`" | **ACCURATE** | 4 test `[0]` readers, 3 production LIST readers — full grep in *Method* |
| 7 | "`_has_update_movement` no longer exists … nothing to port" | **ACCURATE** | `grep -rn "_has_update_movement"` → `doc/plans/` prose only |
| 8 | D1 "Already satisfied at HEAD by #1141; no production change" | **OVERSTATED** | Core property holds; the unreadable-SHA flip (G1) and the missing trigger-semantics record (G6) are unmet |
| 9 | "Per-bot trigger semantics are already registry data (`participation_requires_update`, `trigger_comment`, `rate_limit_class`)" | **FALSE** as a satisfaction of the ⭐ | `grep -rn "auto_on_push\|requires_explicit_trigger" marketplace/ test/ doc/` → **0 hits**. None of the three fields encodes auto-on-push vs explicit-trigger; `trigger_comment` is non-empty for all three bots |
| 10 | D2 "Already satisfied at HEAD … The identity … is stated explicitly" | **PARTIALLY ACCURATE** | Decoupling and identity-statement CONFIRMED; the plan's stated over-firing half is still live at `:1102` and undisclosed (G2) |
| 11 | D3(a) "New test … asserting … `count_skipped_duplicate == len(_COMMENTS)` … Mutation-proven" | **ACCURATE** | Test at `test_github_pr.py:166–206`; runs green; mutation reasoning verified by reading the loop |
| 12 | D3(b)/(c) "ALREADY COVERED by `test_second_fetch_at_the_same_head_stays_participated` / `test_review_predating_the_merge_candidate_is_stale` / `test_edit_at_one_commit_does_not_credit_a_later_commit`" | **ACCURATE** | All three exist and assert what is claimed |
| 13 | D3(d) consumer population "ALREADY COVERED" by `test_at_least_one_registered_bot_requires_update_movement`, `test_currency_anchor_is_recorded_in_the_ledger_on_credit`, and the taxonomy sweep | **OVERSTATED** | All three exist, but each derives the **bot** population, not the consumer population. The genuine consumer-population coverage is `TestCallSitePopulation` (`test_bot_participation_contract.py:829–960`), which scans `marketplace/bundles/**/*.md` for both invocation families with a per-family vacuity guard — and the report never cites it (G8) |
| 14 | D3(d) refusal fixture "population-derived … both swept over `_registered_bots()` with a non-empty guard" | **OVERSTATED** | Swept over **bots**, not over **wordings**. `_refusal_body` (`test_refusal_recovery_arming.py:64–74`) uses `declared[0]` only and **falls back to a synthetic notice** when a bot declares none, so `test_every_registered_bots_refusal_is_detected` passes for pr-agent while testing nothing pr-agent declares; `test_a_bots_declared_refusal_is_recognized_as_DATA` `pytest.skip`s for it (`:242`). Sourcery's second declared pattern is never swept. No test publishes the refusal-pattern population size (G5) |
| 15 | Population sizes: 3 registered bots; refusal patterns total 3 (coderabbit 1, sourcery 2, pr-agent 0) | **ACCURATE** | `ls automatic-review/standards/` → 3 bot docs; `coderabbit.md:54–55` (1), `sourcery.md:42–44` (2), `pr-agent.md:128` (EMPTY) |
| 16 | Build gate: "`=== verify: SUCCESS ===`, 19606 passed, 14 skipped" | **UNVERIFIABLE** | The tree has moved 80+ commits; the full build was not re-run per the task's instruction |
| 17 | Sub-agent finding 5: "No production change, no stale claims" | **ACCURATE as scoped** (to the report's own claims) — but the cold read **missed** six prose sites still stating the retired predicate (G4) | See *Completeness review* |
| 18 | "No production change" | **ACCURATE** | `git show --stat 38548923` → rename (0 bytes) + `report-01.md` (+311) + `test_github_pr.py` (+48) |
| 19 | Contract check row 3: "plan directory … present on arrival; no repair needed" | **ACCURATE** | The parenthetical attaches to the first-instruction block; the rename `110-….md → 110-…/plan.md` is separately disclosed |
| 20 | Residue: "None blocking … No follow-up owed" | **FALSE** | At least three live defects in the surface this plan owns remain open (G1, G2, G3), plus two unmet ⭐ obligations (G5, G6) |
| 21 | Reviewer participation table, merge-gate disposition, cost | **UNVERIFIABLE** | PR-runtime observations; not derivable from the tree |

**Line-number drift, not a finding.** Every `path:line` in `report-01.md` has moved (e.g.
`github_pr.py:929` → `:953`, `review_completeness.py:312` → `:377`, `_github_pr.py:400` → `:506`,
`branch-cleanup.md:784` → `:810`, `test_bot_participation_contract.py:650` → `:653`). All symbols
resolve; the plan itself declares line numbers navigational.

## Correctness review

**C1 — an unreadable head SHA silently converts a proven credit into a blocking stale verdict.
CONFIRMED.** `github_pr.py:904` reads the SHA; `_github_ci.fetch_pr_head_sha` returns `''` on any
failure. With `merge_candidate_sha == ''` and a ledger record present, `:705` short-circuits on the
falsy SHA and `:708` returns False for an unedited comment ⇒ `participated_stale`. The plan's
Verification demanded the SHA-advance reset "is the one a monotonicity fix most easily breaks"; the
inverse — the reset firing when the SHA did **not** advance — is what happens here. The `fetch_findings`
return (`github_pr.py:1245–1300`) carries **no** field reporting whether the SHA resolved, so the
caller cannot tell "stale because HEAD moved" from "stale because the read failed", and
`branch-cleanup.md`'s own UNKNOWN discipline ("An absent input is an UNKNOWN verdict, never a `false`
the operator can act on") is not applied to this input. → G1.

**C2 — the filing dedup over-fires on an in-place edit, dropping real review content. CONFIRMED.**
`github_pr.py:1102`, keyed `(bot_kind, comment_id)` with no content or timestamp term. This is the
plan's own D2 defect statement, verbatim, and it survives the landing. → G2.

**C3 — a drifted refusal wording is credited as participation. CONFIRMED.** `github_pr.py:950` →
`_github_pr.py:183–187`. The registry layer is a substring match over `refusal_patterns`; the
structural layer requires **both** a limit-exceeded statement **and** a notice shape
(`_github_pr.py:150–152`). A vendor notice that satisfies neither reaches `:953`, matches a declared
publish shape (a refusal *is* published in one), and is credited. The plan flagged exactly this as
"a false credit with no signal"; the report never adjudicated it. → G3.

**Not defects, checked and cleared:**

- The participation loop's `if not _bot_kind or _bot_kind in participated: continue` (`:943`) does not
  strand a bot in `stale_participation`: the return filters `if bot not in participated` (`:1270`).
- `_record_currency_records` writes only changed rows (`:990`), and `_recorded_currency_records`
  takes last-row-wins (`:622`), so the ledger is idempotent across repeated fetches at one SHA.
- The added test is not vacuous: it asserts a *conjunction* of two observables on one fetch, and one
  of the three credited bots (pr-agent) reaches the credit through the SHA-currency arm rather than
  by presence.

## Completeness review

**Six prose sites still state the retired pre-#1141 currency predicate.** The production module's own
comment (`github_pr.py:576–582`) records that `updated_at != created_at` is a closed hole — "once a
comment is edited at some commit, `updated_at != created_at` stays true forever, so every later HEAD
advance would keep crediting it" — and `test_edit_at_one_commit_does_not_credit_a_later_commit`
(`test_github_pr.py:2360`) pins the fix. Yet:

| Site | Text | Why it is stale |
|---|---|---|
| `automatic-review/standards/bot-participation-contract.md:233` | "it was **edited in place** (`updated_at` differs from `created_at`) since it was posted" | States the **closed hole** as the current rule. The code compares against the **recorded** `updated_at` (`github_pr.py:707–708`) |
| `automatic-review/standards/bot-participation-contract.md:491,496` | "the SHA … is normally read from the `reviewed_commit_sha` stamped on the `pr-comment` finding" … "evaluates the currency rule against the **union** of the stored-finding SHAs and the recorded sidecar SHAs" | The code reads **one** source. `github_pr.py:909–911`: the ledger "is the SOLE currency source, so a comment stored as a finding and a comment dropped as noise are treated identically." There is no union |
| `workflow-integration-github/SKILL.md:129` | "the comment is first-present or its `updated_at` has moved" | Omits the SHA-currency arm entirely — the anchor #1141 introduced |
| `automatic-review/SKILL.md:652` | "only on first presence or observed `updated_at` movement" | Same omission |
| `automatic-review/standards/pr-agent.md:86` and `:363–364` | "Evidence therefore requires first presence OR updated_at movement." / "evidence requires either **first presence** … or observed **`updated_at` movement**" | Same omission, in the registry doc a reader consults first |
| `automatic-review/scripts/bot_registry.py:486–487` (docstring) | "evidence requires either first presence (the comment is newly observed) or observed `updated_at` movement" | Prose-bearing string in **production code** |

This is the plan's own thesis turned on the plan: the rule is enforced by prose, and the prose now
disagrees with the code in the direction that re-teaches the defect. → G4.

**The refusal fixture is bot-derived, not wording-derived, and is vacuous on an empty pattern set.**
The plan wrote: "assert that each registered bot's known refusal **wordings** classify as refusals.
⛔ Not a hand-list — the fixture must publish the **population size it ranged over**; a check that can
pass over an empty pattern set is the vacuous-guard archetype again." `_refusal_body`
(`test_refusal_recovery_arming.py:62–74`) returns `declared[0]` — one wording — and, for a bot with
none, a synthetic structural notice. Consequences, all CONFIRMED by reading:

- pr-agent (`refusal_patterns` EMPTY) passes `test_every_registered_bots_refusal_is_detected` by
  exercising the **structural fallback**, not any declared wording.
- sourcery's second declared pattern (`"reached your weekly rate limit of"`, `sourcery.md:44` — the
  one the run's own PR observed live) is never swept by the arming suite. Only
  `test_bot_registry.py:226` asserts it is *present in the list*, by hand-coded literal.
- No test publishes the refusal-pattern population size. → G5.

**Two SKILL.md sites are consumers of the `participated_bots` claim that D0 did not enumerate as
such.** `workflow-integration-github/SKILL.md:129` and `automatic-review/SKILL.md:652` each *define*
the credit rule for readers and agents. D0's table lists the second only as a call site, not as a
restatement to check. Both are stale (above).

**The plan's Notes redefined the population and the report used the narrower one.** The Notes state
the population is "every site that decides whether a comment represents NEW INFORMATION … Three
members are known: the wait completion predicate, the movement predicate, and this dedup." The
report's tables enumerate `participated_bots` consumers and `participation_evidence` readers; the
wait completion predicate (`github_ops pr wait-for-comments`, whose arm keys on
"the LATER of that comment's `updated_at` / `created_at` moving strictly past the wait-start" —
`tools-integration-ci/standards/api-contract.md:159`) is not classified anywhere. That predicate
remains timestamp-anchored rather than SHA-anchored; whether that is a defect is *not* established
here and is left as an open question rather than asserted.

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
| "None blocking. The plan's production goal … is met at HEAD by #1141; this run added the one uncovered regression guard and verified the rest. **No follow-up owed.**" | **REFUTED.** Three live defects in this plan's declared surface remain open at HEAD (G1 at `github_pr.py:703–708`, G2 at `github_pr.py:1102`, G3 at `github_pr.py:950` + `_github_pr.py:185–187`), plus two unmet ⭐ obligations (G5, G6) and a six-site stale-prose cluster (G4). No later commit closed any of them: `git log --oneline --follow -- .../github_pr.py` shows the last change as `9e9e9880` (#1241), which touched the size-cap path, not the currency or dedup paths |
| "Optional-bot re-review (coderabbit/sourcery rate-limited) — routine, outside our control" | **Closed by construction** — a PR-runtime condition with no tree artifact |

## Summary

**Counts by severity:** 5 major, 4 minor, 0 blockers. Nine gaps total, all actionable and recorded in
`gaps.md`.

**Bottom line.** The plan's central finding is correct and independently reproducible: both target
defects were real before #1141 and are genuinely gone at HEAD, the added regression guard exists,
passes, and is discriminating against both the general and the historical coupling shapes, and the
landing respected every out-of-scope boundary. Where the run falls short is on the obligations the
plan marked ⭐ and ⛔ around the edges of the refutation. It recorded "no follow-up owed" over a
surface that still contains three live defects — a transient head-SHA read failure silently
converting a proven reviewer into a *blocking* `participated_stale` with no distinguishing signal; the
filing dedup still keyed on `comment_id` alone, so an in-place-edited review's new content is
credited as participation but dropped before triage (the plan's own D2 defect, verbatim); and a
drifted vendor refusal wording still reaching the participation credit as a false positive. It also
declared two ⭐ obligations satisfied that the tree does not satisfy — the `auto_on_push` /
`requires_explicit_trigger` record exists nowhere, and the "population-derived refusal fixture" sweeps
bots rather than wordings and passes vacuously over the one bot with an empty pattern set. Finally,
six prose sites — including one docstring in production code and both SKILL.md definitions of what
`participated_bots[]` credits — still state the retired pre-#1141 predicate, which is precisely the
"the rule is enforced by prose, and the prose is wrong" mechanism this plan was written to close.
