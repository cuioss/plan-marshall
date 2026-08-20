# Verification — 010-participation-credited-from-a-superseded-commit

**Landed as:** PR #1141, squash commit `50f67ed2`
**Verdict:** verified-with-gaps

The two headline defects the plan names — the dead anchor and the observer effect — are genuinely
closed for the single-evidence-comment path, with discriminating tests that exist and pass. Three
material holes remain in what landed: a second evidence comment of the same bot bypasses the currency
test entirely (a live false positive of the exact class the plan exists to close, reproduced against
the shipped producer); the stated rule is applied to one of the three registered bots only; and eight
prose sites still restate the removed two-arm predicate or its abandoned two-source anchor as if
either were current. `report-01.md` additionally names three symbols/tests that do not exist in the
landed tree.

## Method

Read in full:

- `plan.md` and `report-01.md` in this directory.
- `git show --stat 50f67ed2`, `git show 50f67ed2 -- <path>` for every changed path.
- The current tree at `HEAD` = `61a43e53` (branch `claude/review-apparatus-analysis-mcf8md`):
  `github_pr.py` lines 555–1010 and 1255–1280, `review_completeness.py` lines 225–345 and 500–600 and
  1355–1541, `bot-participation-contract.md` §§ "The currency rule", "Evidence for a bot that edits
  one comment in place", "Detecting a decline", "Surviving the drop…", "Recorded exclusions",
  `branch-cleanup.md` §§ 812/833/862, `branch-cleanup-rereview.md` steps 50–70,
  `automatic-review/SKILL.md` lines 24, 243–254, 652–700, 725–740, 960–1010,
  `pr-agent.md` lines 48–90 and 355–370, `bot_registry.py` line 480–492.

Searches run (all with `grep -rn` over `marketplace/bundles/`, `test/`, or both):

- `_reviewed_at_merge_candidate|_has_update_movement|reviewed_commit_sha|observed_keys|currency`
- `_existing_pr_comment_shas|_recorded_dropped_comment_shas` (repo-wide, `--include=*.py`, and against
  `git show 50f67ed2:…/github_pr.py`) — zero hits.
- `def <name>` for each of the ten tests `report-01.md` names.
- `head_sha_verified` across all bundles.
- `declined|STATE_DECLINED` across `review_completeness.py`, the workflow docs, and the tests.
- `seven-member|eight-member|nine-member|ten-member|eleventh|ninth member`
- Stale-predicate prose, in **two** passes over `marketplace/bundles/` and `test/`, because one pass
  does not find them all: `first presence|first-presence|updated_at movement|updated_at.*created_at`
  finds the arm-wording sites, and `first.present|updated_at (has )?mov|observation (history|ledger)|union of the stored|sidecar`
  additionally finds `workflow-integration-github/SKILL.md:129` ("first-present … `updated_at` has
  moved") and the two-source-anchor paragraphs, which the first pattern misses. The site table under
  § K2 is the union.
- `_UPDATE_REQUIRING_BOTS|_DERIVED_NON_PARTICIPATION|_scan_invocation_sites` across `test/`.
- `_dispatch_roster` across `test/`, and `site population|participation sites`.
- `git log --all --oneline -S'<symbol>'` for each symbol claimed but not found.
- `git log --oneline 50f67ed2..HEAD -- github_pr.py review_completeness.py`, plus an AST-level
  comparison of `_reviewed_at_merge_candidate`, `_recorded_currency_records`,
  `_record_currency_records` and `_dropped_comment_keys_path` between
  `git show 50f67ed2:…/github_pr.py` and the working tree (all four **byte-identical**) and
  `git diff 50f67ed2 HEAD -- github_pr.py | grep -iE 'participat|currency|merge_candidate'` (no hits).
  The currency machinery and the participation loop are **unchanged since the landing**, so the landed
  diff and the current tree agree on this plan's subject.

Ran:

- `uv run python -m pytest test/plan-marshall/workflow-integration-github/test_github_pr.py
  test/plan-marshall/workflow-integration-github/test_pr_agent_contentless_guide_interaction.py
  test/plan-marshall/automatic-review/test_review_completeness.py
  test/plan-marshall/automatic-review/test_bot_participation_contract.py
  test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py -o addopts="" -q`
  → **344 passed** (exit 0). Those five files hold all nine of the ten tests `report-01.md` names that
  exist. `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py`, the sixth surface
  cited below, is a separate run → **11 passed**.
- A temporary probe module inside `test/plan-marshall/workflow-integration-github/` (created, run, and
  deleted; no tracked file was modified) that drives the real `github_pr.cmd_fetch_findings` through
  the existing `_patch_provider` / `_run_fetch` harness for the three executable claims under
  § Correctness review — the two-evidence-comment bypass (C1), the empty-merge-candidate-SHA flip and
  ledger poisoning (C3), and the pre-upgrade key-only ledger row (C4). Outcomes are quoted there.
- `grep -n required_bots .plan/marshal.json` → line 117, `"required_bots": "pr-agent"` (confirms the
  report's claim that PR-Agent is this repository's sole required bot).

Not run: the full `./pw verify` (out of remit).

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | a table naming every site, its anchor, its idempotence verdict, and the enumeration method | 8-site table S1–S8, grep + call-graph + registry method stated | The table is in `report-01.md` §D0; each named site exists and each anchor claim re-derives correctly against the tree | **met** |
| D1 | the rule stated in `bot-participation-contract.md` | § "The currency rule" added | Present at `bot-participation-contract.md:207-220`, states exactly the plan's rule | **met in text, not in reach** — the rule says it "governs every site that credits participation"; the code applies it only to `participation_requires_update` bots |
| D2 | predicate idempotent on unchanged inputs, proven by a test; no participation path reads `observed_keys` | `_has_update_movement` → `_reviewed_at_merge_candidate`; ledger-anchored | `github_pr.py:652-708` implements the SHA + fresh-edit ledger predicate; `observed_keys` survives only as two prose mentions; two idempotence tests exist and pass | **met with residuals** — one non-idempotent path remains (empty merge-candidate SHA + fresh edit) and one bypass (a bot's second evidence comment) |
| D3 | a distinct `declined` state the quorum excludes, with a test for each of the two refusal shapes | `STATE_DECLINED`, `--declined-bots`, trigger-A consumer wired | `review_completeness.py:237,261,571-572`; `branch-cleanup-rereview.md:66`; `branch-cleanup.md:833`; tests at `test_review_completeness.py:597,636` | **met at trigger A only** — the FIND-step and `not_triggered`-remediation consumers still read `matched` alone |
| D4 | four test families, each mutation-proven | six named tests + population derivations | Nine of ten named tests exist and pass; one (`test_currency_anchor_is_derived_from_both_sha_sources`) never existed; D4(d)'s **site**-population derivation is not present | **partially met** |

### D0 — site population and anchor per site

**Verdict: met.** `report-01.md` § D0 carries an eight-row table, reports per site (never one global
answer, as the ⛔ demanded), and states a re-runnable enumeration method (grep over six participation
symbols + producer→consumer call graph + the registry). Spot-checking three rows against the tree:

- **S1** — `github_pr.py` participation loop. Pre-fix anchor "NONE / not idempotent" is confirmed by
  the removed code in `git show 50f67ed2 -- …/github_pr.py` (`-def _has_update_movement(comment, observed_keys, bot_kind)`).
- **S3/S4** — `github_re_review.py:263` `'head_sha_verified': matched_signal == 'review'` confirms the
  review path is SHA-anchored and the comment path is not.
- **S7** — the "recorded-but-ignored bit". Confirmed: pre-fix `branch-cleanup-rereview.md` read
  `matched` alone; the landing changed that (`branch-cleanup-rereview.md:50`).

The gate's own ⛔ ("do not hand-write the site list") is honoured for the derivation, but see D4(d):
the derived site list was never turned into a test-enforced population.

One of the plan's own HYPOTHESIS claim labels is settled here, and it is **refuted**: *"the barrier
inherits a findings read from an earlier step rather than re-reading at the barrier, so a review
arriving between the last fetch and the merge is invisible."* It does not inherit —
`branch-cleanup.md:732` ("Re-run the `github_pr fetch_findings` producer") is inside the barrier, and
Predicate 2's *"retain … from the `fetch_findings` return above"* (`:810`) refers to that re-fetch,
not to a FIND-step result. S6's anchor claim ("the live HEAD") is therefore correct as written.

### D1 — the stated rule

**Verdict: met in text.** `bot-participation-contract.md:209-211`:

> **A participation credit is valid only against the merge candidate: a review counts iff the commit it
> reviewed is the merge candidate's HEAD, and that verdict is a pure comparison that consumes no
> observation state, so it is identical however many times it is evaluated.** This one rule governs
> every site that credits participation.

The final sentence is the problem. `github_pr.py:955` gates the whole currency test on
`_requires_update = bot_registry.participation_requires_update(_bot_kind)`, so S2 (coderabbit,
sourcery) credits presence with no SHA consulted. The rule as written is contradicted by the code it
governs. See § Completeness review.

### D2 — re-key the currency test onto HEAD identity

**Verdict: met with residuals.** `github_pr.py:652-708`:

```python
record = currency_records.get((bot_kind, comment_id))
if record is None:
    # First observation — credit only when the merge candidate is resolvable.
    return bool(merge_candidate_sha)
recorded_sha, recorded_updated_at = record
if merge_candidate_sha and recorded_sha == merge_candidate_sha:
    return True
updated_at = str(comment.get('updated_at') or '')
return bool(updated_at) and updated_at != recorded_updated_at
```

`observed_keys` no longer exists as a variable anywhere (`grep -rn observed_keys marketplace/ test/`
returns exactly two prose mentions, `github_pr.py:679` and `bot-participation-contract.md:241`), so
that half of the *Done when* is discharged. The idempotence half is discharged for the main path and
proven by `test_second_fetch_at_the_same_head_stays_participated`
(`test_github_pr.py:2431`) and `test_second_fetch_of_an_unchanged_guide_at_the_same_head_stays_credited`
(`test_pr_agent_contentless_guide_interaction.py:412`). Both are genuinely discriminating: pre-fix,
arm 1 was `(bot_kind, comment_id) not in observed_keys`, which the first fetch consumed, so the second
fetch at the same HEAD returned `False` — the assertion `second == first == participated` therefore
fails against the pre-fix predicate. Residuals are in § Correctness review.

### D3 — `declined`, excluded from quorum

**Verdict: met at trigger A only.** The state exists (`review_completeness.py:237`), is in
`_UNPROVEN_STATES` (line 261), is classified after the refusal branches and before
`participated_stale` (lines 567-574), has its own summary bucket (line 306), its own CLI flag on both
the `check` and `deficit` parsers (via the shared `_add_bot_observation_flags`, lines 1396-1397 and
1487/1525) which **both handlers consume** (`cmd_check` line 1258, `cmd_deficit` line 1288 — parsed
*and* forwarded, not accepted-and-ignored), and blocks byte-identically to `absent`
(`test_pre_merge_barrier.py:679-683`, the `declined` entry in the widened-member parity
parametrization; that file passes, 11 tests).

The obtain-side wiring is only half done. `branch-cleanup-rereview.md:50,66` consumes
`head_sha_verified` and accumulates `{declined_bots}`; `branch-cleanup.md:833` forwards
`--declined-bots "{declined_bots}"`. But `automatic-review/SKILL.md:250` (trigger B) and
`automatic-review/SKILL.md:729` (the `not_triggered` remediation) both still say *"When `matched:
true`, the fresh review is now on the PR"* with no mention of `head_sha_verified`
(`grep -c head_sha_verified automatic-review/SKILL.md` → **0**), and `SKILL.md:679`, the FIND-step
`review_completeness check` invocation, does not interpolate `--declined-bots`. The landing baked that
in deliberately: `test_bot_participation_contract.py:806-807` (the `_CONFIRMED_SITES` header comment,
the roster itself at `:817`) reads *"the participation guard passes six (``--declined-bots`` is
documented in the canonical block but not interpolated at the FIND-step site)"*.

The plan's D3 *Done when* also asks for "a test for each of the two refusal shapes". Present:
`test_refusal_and_incremental_decline_are_both_excluded_from_quorum`
(`test_review_completeness.py:636`) asserts shape A (explicit refusal → a refusal member, quorum
unsatisfied) and shape B (incremental decline → `declined`, quorum unsatisfied). The plan asked for
"a test for each"; one test carries both shapes as separate arms, which discharges the intent.

The one test guarding the obtain-side wiring, `test_rereview_consumer_honors_head_sha_verified_as_a_decline`
(`test_branch_cleanup_merge_queue_routing.py:345-372`), is a **bare substring-presence** check over
the two markdown files (`'head_sha_verified' in doc`, `'declined' in doc`, `'{declined_bots}' in doc`,
`'--declined-bots "{declined_bots}"' in barrier`). It discriminates against the pre-fix state, which
carried none of those strings, but it cannot tell a doc that *routes* the bit from one that merely
*mentions* it, and it says nothing about the two unwired `SKILL.md` consumers. See § Completeness
review K3 and gap G14.

### D4 — mutation-proven tests

**Verdict: partially met.**

- (a) advanced-HEAD staleness — `test_review_predating_the_merge_candidate_is_stale`
  (`test_github_pr.py:2496`) and `test_dropped_guide_goes_stale_once_head_advances`
  (`test_pr_agent_contentless_guide_interaction.py:453`). **Present.**
- (b) reviewed-the-merge-candidate credits — covered by the first fetch of the same pair. **Present.**
- (c) idempotence at unchanged HEAD with the ledger written between — **present** (both paths, cited
  under D2) and genuinely fails pre-fix.
- (d) *"The site set D0 enumerated is population-derived, non-empty, and every member asserted"* —
  **not met.** What exists is a registry-derived **bot** population (`_UPDATE_REQUIRING_BOTS`,
  `test_github_pr.py:2313`, guarded non-empty at line 2322), a derived **taxonomy-member** population
  (`_DERIVED_NON_PARTICIPATION`, `test_bot_participation_contract.py:145`), and a derived
  **doc-invocation-site** population for two command families (`_scan_invocation_sites`,
  `test_bot_participation_contract.py:860`). None of the three is the S1–S8 site set: S3, S4, S7 and
  S8 are members of no asserted population. Searched `grep -rn "_dispatch_roster" test/` and
  `grep -rn "site population|participation sites" test/` — no roster over the participation sites
  exists.

The ⛔ "prove discrimination by mutation" is discharged for (c) by construction (the pre-fix predicate
returns the opposite answer, verifiable from the removed code in the diff). (a) is a *matched control*
that passes both before and after — correctly labelled as such in its own docstring at
`test_github_pr.py:2501`, so it is not a vacuous test masquerading as evidence.

## Report-claim audit

| # | Claim in `report-01.md` | Verdict | Evidence |
|---|---|---|---|
| 1 | D0's eight-site table with per-site anchor and idempotence | **ACCURATE** | Every named site exists; three re-derived above |
| 2 | "PR-Agent is today the sole bot subject to the S1 currency test" | **ACCURATE** | `coderabbit.md:43` `participation_requires_update: false`; `pr-agent.md:84` `true`; `sourcery.md` likewise false |
| 3 | D1: rule stated in `bot-participation-contract.md` § "The currency rule" | **ACCURATE** | `bot-participation-contract.md:207-220` |
| 4 | D2: "`_has_update_movement` … replaced by `_reviewed_at_merge_candidate`" | **ACCURATE** | `github_pr.py:652`; `_has_update_movement` absent from the tree |
| 5 | D2: "the reviewed SHA per comment is the union of `_existing_pr_comment_shas` (stored-finding stamps) and `_recorded_dropped_comment_shas`" | **FALSE** | Neither symbol exists in `HEAD` nor in `git show 50f67ed2:…/github_pr.py` (grep count 0). The landed code reads one source, `_recorded_currency_records` (`github_pr.py:600`). The report's own Finding 4 says the two-source design was dropped, but § D2 was never corrected |
| 6 | D4(d): "`test_currency_anchor_is_derived_from_both_sha_sources` (both SHA sources are the SUT's own readers)" | **FALSE** | `grep -rn "def test_currency_anchor_is_derived_from_both_sha_sources" test/` → no match; `git log --all -S'currency_anchor_is_derived'` → only the squash (which contains this report). The real test is `test_currency_anchor_is_recorded_in_the_ledger_on_credit` (`test_github_pr.py:2335`), and it asserts one ledger source, not two |
| 7 | The other nine named tests exist | **ACCURATE** | All nine located by `grep -rn "def <name>" test/`; all pass in the 344-test run |
| 8 | Finding 1: four stale "seven-member" sites fixed | **ACCURATE, understated** | Five *files* were updated in the landing — the two `automatic-review/SKILL.md` sites, `review_completeness.py` (three count-bearing lines, not one), `create-pr.md:201`, **and** `workflow-pr-doctor/standards/automated-review-lifecycle.md:56`, which the report does not name. Re-derived from `git show 50f67ed2 --format="" -- <path> \| grep -E "^[+-].*(seven\|eight)"` |
| 9 | Finding 2: empty-SHA path "fixed … fails closed on both fetches" | **OVERSTATED** | True for the first-observation arm only. With a ledger row present and a fresh edit, an empty merge-candidate SHA still flips `participated` → stale between two fetches (demonstrated below) |
| 10 | Finding 4: the edit arm now measures against the recorded `updated_at` | **ACCURATE in code, not propagated** | `github_pr.py:707-708` is correct; `bot-participation-contract.md:233` still states the superseded `updated_at` vs `created_at` form |
| 11 | Residue: "`declined` wired end-to-end only on the trigger-A path" | **ACCURATE but incomplete** | Trigger B (`SKILL.md:250`) is named; the `not_triggered`-remediation consumer (`SKILL.md:729`), which has the identical defect, is not |
| 12 | Build gate: `./pw verify` SUCCESS, 18689 passed / 14 skipped | **UNVERIFIABLE** | Not re-run (out of remit). The landing touched **six** test files (`git show --stat 50f67ed2`); all pass today — 344 across five of them plus 11 in `test_pre_merge_barrier.py` = **355** |
| 13 | Intermediate commits `4e93870`, `d194d60`, `ddd486c` | **UNVERIFIABLE** | Squashed away; the PR branch is not in this clone |
| 14 | Reviewer-participation table and the CLA post-mortem | **UNVERIFIABLE** | PR-side facts, not re-derivable offline. Internally coherent |
| 15 | Contract check row "Local sync owed: yes" | **SUPERSEDED** | `CLAUDE.md` now rules that a lane plan "neither performs a sync nor records one as owed" — landed later, in `cd11d46b` (#1267). The report was correct when written |
| 16 | Plan's Verification § ⭐ "Cold read of the contract text … Report the reading verbatim" | **NOT DISCHARGED** | `report-01.md` § "Verification sub-agent (Step 6)" records three findings but carries no verbatim cold reading of (a) which commit a credit is evaluated against or (b) whether a `declined` bot blocks/is disclosed/is ignored |

## Correctness review

### C1 — A bot's second evidence comment bypasses the currency test entirely (blocker-class)

`github_pr.py:941-975`:

```python
for _comment in raw_comments:
    _bot_kind = bot_kind_for_author(_comment.get('author') or 'unknown')
    if not _bot_kind or _bot_kind in participated:
        continue
    ...
    if _requires_update and not _reviewed_at_merge_candidate(...):
        stale_participation[_bot_kind] = _kind
        continue
    if _requires_update:
        currency_updates[(_bot_kind, str(_comment.get('id') or 'unknown'))] = (...)
    participated[_bot_kind] = _kind
```

Two consequences compose into a live false positive:

1. The short-circuit at line 943 means **only the first credited comment per bot ever gets a ledger
   row**. A bot's second, third, … evidence comment is never evaluated on the fetch where the first
   one credits, so it never enters the currency ledger.
2. On a later fetch at an advanced HEAD, the first comment now fails the currency test and hits the
   `continue` at line 967 — and the loop then reaches the second comment, which has **no ledger row**,
   so `_reviewed_at_merge_candidate` takes the first-observation arm (`record is None →
   return bool(merge_candidate_sha)`) and **credits it at the new HEAD**. The subtraction at
   `github_pr.py:1270` (`if bot not in participated`) then removes the bot from
   `stale_participation_bots[]` as well, so the barrier sees a clean `participated`.

This is reachable for the only bot the currency test applies to: `pr-agent.md:80-83` declares **two**
publish shapes, `issue_comment` (the Guide) and `inline` (`/improve` code suggestions, one comment
each). A `/improve` suggestion posted at commit N therefore credits participation at commit N+1
without any re-review — the exact defect the plan's Problem statement describes. Reachability is not
narrowed by the pre-filters: participation is derived from `raw_comments` before filtering, and
`cmd_fetch_findings` fetches with `unresolved_only=False` (`github_pr.py:881`), so an already-resolved
inline comment still supplies the bypassing credit.

**CONFIRMED, and reproduced end-to-end** against the shipped producer. A probe drove the real
`github_pr.cmd_fetch_findings` twice through the existing test harness: two unchanged evidence
comments of `pr-agent` present at both fetches, `head_sha` advanced `_HEAD_A` → `_HEAD_B` between
them. Fetch 1 → `participated_bots = [{pr-agent, issue_comment}]`; fetch 2 →
`participated_bots = [{pr-agent, issue_comment}]`, `stale_participation_bots = []`. Neither comment
was re-reviewed and HEAD moved, yet the barrier sees a clean `participated`.

No test covers it: the only two-comment case,
`test_a_fresh_comment_outranks_a_stale_one_through_the_subtraction` (`test_github_pr.py:2553`),
introduces its second comment only on the *second* fetch, so it exercises a genuinely new comment and
pins the same code path that produces the false positive when the comment is not new.

The module docstring at `github_pr.py:779-782` describes the ledger as recording each currency-subject
comment's credit "uniformly whether the comment was stored as a finding or dropped as noise". That is
true of the *storage* axis and false of the *per-comment* axis — only the first credited comment per
bot per fetch gets a row at all.

### C2 — The first-observation arm asserts something the code cannot know

`bot-participation-contract.md:235-236` states the arm as fact:

> - this fetch is the **first observation** of the comment, which is by definition an observation at the
>   merge candidate.

It is not. `github_pr.py:701-703` credits any comment absent from the plan's ledger, whatever commit
the bot actually reviewed. A bot that finishes reviewing commit N and posts its comment after commit
N+1 has landed is credited at N+1 on the first fetch that sees it. The plan's own § D0 "Data
constraint discovered" records why the anchor is unavailable (a fetched comment carries no reviewed
SHA), but the contract turns a fail-open heuristic into a stated definition rather than disclosing it
as a bounded assumption. **CONFIRMED** by reading both the code and the contract text.

### C3 — Residual non-idempotence and ledger poisoning on an unresolvable head SHA

`report-01.md` Finding 2 claims the empty-SHA path "fails closed on both fetches". That holds only
for the first-observation arm. Driving the real `cmd_fetch_findings` — credit the comment at a real
`_HEAD_A`, then edit it in place while `fetch_pr_head_sha` returns `''`:

```
fetch at _HEAD_A, unchanged comment      -> participated              # ledger ('AAA…','u1')
empty-sha fetch, comment edited to u2    -> participated              # ledger now ('', 'u2')
empty-sha fetch again, nothing changed   -> participated_stale        # FLIP at the same HEAD
fetch at real _HEAD_B, nothing changed   -> participated_stale        # stale until a further edit
```

Two defects: the verdict flips between two evaluations at the same (unreadable) HEAD — the observer
effect the plan exists to remove, surviving on one path — and the credit written with an empty SHA
**poisons the ledger** (read back through the SUT's own `_recorded_currency_records`:
`{('pr-agent','guide-1'): ('', '2026-07-29T10:09:00Z')}`), because `recorded_sha ==
merge_candidate_sha` can never again be true for that comment, so it stays stale until the bot edits
again. Combined with the plan's own "Detect and obtain are one pair" note, that is a path to a
permanent hard block. `test_unresolvable_head_sha_fails_closed_and_stays_idempotent`
(`test_github_pr.py:2462`) covers only the no-record case. The module docstring at
`github_pr.py:782-784` states the idempotence property unqualified ("re-running the fetch at the same
HEAD returns the same answer"), which this path contradicts. **CONFIRMED, reproduced end-to-end.**

### C4 — Pre-existing ledger rows read as `('', '')` and fail open once

`_recorded_currency_records` (`github_pr.py:600-624`) defaults both fields to `''`. Before this
landing the same artifact (`pr-noise-dropped-comments.jsonl`) held rows carrying only `bot_kind` and
`comment_id`. Such a row reads as `('', '')`, so `recorded_sha == merge_candidate_sha` is false and
the predicate falls to `bool(updated_at) and updated_at != ''` — true for essentially every real
GitHub comment. A plan mid-flight across the upgrade therefore **credits a stale unchanged Guide once**
before the ledger self-heals. There is no schema-version guard. **CONFIRMED, reproduced end-to-end**:
seeding `{'bot_kind': 'pr-agent', 'comment_id': 'guide-1'}` into the ledger and fetching an unchanged
comment at `_HEAD_B` yields `participated_bots = [{pr-agent, issue_comment}]`,
`stale_participation_bots = []`. The removed writer is visible in the landing —
`git show 50f67ed2 -- …/github_pr.py` deletes `_record_dropped_comment_keys`, which wrote exactly
those key-only rows.

### C5 — Colliding ledger key for id-less comments

`github_pr.py:699` and `:971` both key on `str(comment.get('id') or 'unknown')`. Two id-less comments
from the same bot collide on `('pr-agent', 'unknown')`, so one comment's credit answers for the other.
**CONFIRMED** by reading; low reachability (the provider supplies ids), listed for completeness.

### Non-findings (checked and clean)

- The stale/proven subtraction at `github_pr.py:1263-1271` is correct and tested.
- `classify_bot`'s branch order (`review_completeness.py:565-583`) places `declined` after the refusal
  branches and before `participated_stale`, matching both the docstring and
  `bot-participation-contract.md:263`; the ordering is pinned by `test_a_refusal_outranks_a_decline`
  and `test_proven_participation_outranks_a_decline`.
- `read_jsonl` (`tools-file-ops/scripts/jsonl_store.py:62-72`) calls `json.loads` per non-blank line
  with no `try`, so a malformed ledger line raises rather than being swallowed — fail-loud, not
  fail-open.
- Both the `check` and `deficit` parsers receive `--declined-bots` through the shared
  `_add_bot_observation_flags`, **and both handlers forward it** (`review_completeness.py:1258`,
  `:1288`), so it is neither half-wired at the CLI nor accepted-and-ignored.
- The shared adder's docstring count ("the nine list flags", `review_completeness.py:1301`) matches the
  nine list flags it registers, and the per-site counts stated in prose are each correct for their
  site: `automatic-review/SKILL.md:686,691` say eight for the FIND-step call (eight list flags,
  no `--declined-bots`), `branch-cleanup.md:844-845` says eight for Predicate 2 (eight, no
  `--in-progress-bots`), and `automatic-review/SKILL.md:980` says nine for the canonical block.
- The plan's asserted-absence claim label — *"no consumer depends on per-PR participation semantics in
  a way D2 would break"* — holds for every consumer the tree exposes.
  `grep -rn "participated_bots|stale_participation_bots" --include=*.py --include=*.md marketplace/`
  returns nine files: the producer (`github_pr.py`), exactly **one** code consumer
  (`review_completeness.py`, which takes the verdict sets verbatim and never recomputes currency), and
  seven documentation surfaces (`bot-participation-contract.md`, `branch-cleanup.md`, the two
  `SKILL.md`s, `pr-review-operations.md`, `pr-agent.md`, `automated-review-lifecycle.md`). No GitLab
  producer emits either key.

## Completeness review

### K1 — The stated rule reaches one bot of three

`bot-participation-contract.md:211-212` says the currency rule "governs every site that credits
participation". `github_pr.py:955-958` runs it only when
`bot_registry.participation_requires_update(_bot_kind)` is true — today, PR-Agent alone. For
coderabbit and sourcery the participation credit is still *presence of a declared publish shape*,
computed from `raw_comments` **before** any filtering, so a review comment posted at commit N is still
present and still credits at commit N+1. `report-01.md` § D0 row S2 records this precisely ("no
currency test runs at all for these bots … currency-blind") — and then neither D1, D2 nor the Residue
section disposes of it.

The shipped contract does disclose the *scope* twice, in passing: `bot-participation-contract.md:478-479`
("For a bot declaring `participation_requires_update` (today, only PR-Agent …)") and `:674` ("neither
bot declares `participation_requires_update`, so neither can reach `participated_stale`"). Both sit
inside sections about something else — the contentless drop and the doc-consumer sweep — and neither
states the consequence the scope sentence at `:211-212` denies: that for the other two bots a credit
is still granted on presence alone, at any HEAD. So the defect is a **contradiction between the rule's
stated reach and the code's**, not an entirely undisclosed restriction.

Blast radius is config-dependent: `.plan/marshal.json` makes `pr-agent` this repository's sole
required bot, so the hole does not gate merges here — but `required_bots` is an operator knob, and a
consumer project requiring coderabbit gets the plan's original false positive unchanged.
**CONFIRMED.**

### K2 — Eight prose sites still state the removed two-arm predicate or its abandoned two-source anchor

One grep does not find them all, and that is itself part of the defect: the arm wording is paraphrased
differently at different sites. Two passes over `marketplace/bundles/plan-marshall/skills/` are needed —
`first presence|first-presence|updated_at movement|updated_at.*created_at` for the arm-wording family,
and `first.present|updated_at (has )?mov|union of the stored|sidecar` for the rest. The
`wait-for-comments` completion predicate (S8) and the `github_re_review` matchers (S3/S4) are excluded
from both: they are legitimately timestamp-keyed and are not the currency test.

| Site | Surviving stale text |
|---|---|
| `workflow-integration-github/SKILL.md:129` | "for a bot declaring `participation_requires_update` — the comment is **first-present or its `updated_at` has moved**" — the deleted two-arm predicate, restated in the canonical `fetch_findings` step body of the skill that *owns* `github_pr.py`. Found only by the second pattern |
| `automatic-review/standards/bot-participation-contract.md:230-232` | the SHA arm read as two sources: "the `reviewed_commit_sha` stamped on the stored finding, or … the merge-candidate SHA the noise sidecar recorded when the comment was **first observed**". The shipped ledger is one source, covers stored and dropped comments alike, and is refreshed on every credit rather than frozen at first observation |
| `automatic-review/standards/bot-participation-contract.md:233` | "it was **edited in place** (`updated_at` differs from `created_at`) since it was posted" — superseded inside the same landing by the recorded-`updated_at` comparison |
| `automatic-review/standards/bot-participation-contract.md:491-498` | "the SHA a comment was reviewed against is normally read from the `reviewed_commit_sha` stamped on the `pr-comment` finding … evaluates the currency rule against the **union** of the stored-finding SHAs and the recorded sidecar SHAs" — there is no union; `github_pr.py:915` reads one ledger |
| `automatic-review/SKILL.md:652` | "(and, for a bot declaring `participation_requires_update`, only on first presence or observed `updated_at` movement)" — a verbatim restatement of the deleted predicate, in the workflow body an executing agent reads |
| `automatic-review/standards/pr-agent.md:86` | "Evidence therefore requires first presence OR updated_at movement." — inside the machine-readable registry record |
| `automatic-review/standards/pr-agent.md:363` | "evidence requires either **first presence** (the comment is newly observed) or observed **`updated_at` movement**" |
| `automatic-review/scripts/bot_registry.py:486-487` | production docstring: "evidence requires either first presence (the comment is newly observed) or observed ``updated_at`` movement" |

Test prose carries the same abandoned framing at
`test/plan-marshall/workflow-integration-github/test_pr_agent_contentless_guide_interaction.py:38-45`
(module docstring, arm 6), `:396-404` and `:423-426` — each calling the currency ledger "the noise
sidecar the fix extends", which understates what it now records.

Three of these (`bot-participation-contract.md:230-232`, `:233`, `:491-498`) were **written by this
landing** and then invalidated by its own late review-fix; the other five predate it and were missed
by the sweep. **CONFIRMED.**

### K3 — Two more `matched`-alone consumers of `head_sha_verified`

`bot-participation-contract.md:267-270` now states the rule:

> The deciding bit … is **computed and must be consumed**: a `matched: true` with `head_sha_verified:
> false` is a decline, never a completed re-review, and a consumer that reads `matched` alone credits a
> review that never named the commit it matched.

`automatic-review/SKILL.md:250` (trigger B) and `automatic-review/SKILL.md:729` (the `not_triggered`
remediation) both violate it verbatim, and `grep -c head_sha_verified automatic-review/SKILL.md`
returns 0. The shipped state therefore contains a contract and two consumers that contradict it. The
report discloses one of the two. **CONFIRMED.**

### K4 — D4(d)'s site population

Covered under § Deliverables → D4. No test asserts the D0 site set; S3, S4, S7 and S8 are unguarded.
**CONFIRMED** (searches stated in § Method).

### K5 — Artifact name no longer matches its contents

`github_pr.py:590` keeps `_DROPPED_COMMENT_KEYS_ARTIFACT = 'pr-noise-dropped-comments.jsonl'` while
the file now records currency rows for **every** credited `participation_requires_update` comment,
stored-as-finding ones included — comments that were never noise-dropped. The helper names
(`_dropped_comment_keys_path`) and the contract's "observation sidecar" wording carry the same stale
framing. **CONFIRMED**; cosmetic but actively misleading when reading the code.

### K6 — Rotted ordinal in a test comment

`test_bot_participation_contract.py:139`: "not a ninth member". The landing changed "eighth" → "ninth"
correctly at the time; later plans grew `_NON_PARTICIPATION_MEMBERS` (`:114-125`) to ten members, so
the correct word is now "eleventh". The same landing converted the *asserted* counts to derived
(`_NUMBER_WORDS[taxonomy_size]`, line 581) but left this prose ordinal a literal.
**CONFIRMED** (`grep -rn "seven-member|eight-member|nine-member|ten-member|eleventh|ninth member"` —
every other restatement in the tree is consistent at ten).

### K7 — Line-wrap artifact from the taxonomy edit

`phase-6-finalize/workflow/create-pr.md:205-207` now reads "… whose complement" / "> is `participated`.
It" / "> is the ONLY member … lands there", a stranded four-word line followed by an over-long one.
The landing introduced it directly — `git show 50f67ed2 -- …/create-pr.md` shows the rewrap — and the
later eight→ten edits never repaired it. **CONFIRMED**; cosmetic.

## Out-of-scope compliance

**Clean.** The plan declared five exclusions; each was checked against `git show --stat 50f67ed2` and
the diffs:

- *Re-reviewing on every commit* — no trigger frequency changed; the diff adds no trigger site.
- *Widening what counts as participation* — the change strictly narrows the credit and adds a
  **blocking** taxonomy member. `_UNPROVEN_STATES` gained `STATE_DECLINED`; nothing left it.
- *Flipping `re_review_on_loopback`* — `git show 50f67ed2 --format="" -- automatic-review/SKILL.md |
  grep -c "^[+-].*re_review_on_loopback"` returns **0** on both polarities: the knob appears only on an
  unchanged context line. No default changed.
- *The landing-message composition site* — `create-pr.md` was touched, but only at lines 198-205, the
  "What this section is NOT" note about the Intent section, and only to keep the taxonomy count in
  lock-step. Composition logic untouched.
- *The cloud lane's own merge gate* — `.claude/skills/cloud-plan-lane/` is absent from the changed-file
  list.

## Residue status

| Report residue item | Status today | Evidence |
|---|---|---|
| Local `/sync-plugin-cache` owed | **Moot / superseded** | `CLAUDE.md` § Standalone Plan Lane now states a lane plan "neither performs a sync nor records one as owed"; that clause landed in `cd11d46b` (#1267), after this run |
| D3 trigger-B wiring — a FIND-step decline is not fed into `--declined-bots` | **Still open**, and larger than recorded | `automatic-review/SKILL.md:250` and `:729` both read `matched` alone; `SKILL.md:679` does not interpolate `--declined-bots`; `test_bot_participation_contract.py:775` records the omission as intentional |
| PR-Agent re-review of the fix commit `ddd486c` | **Closed by the merge** | `50f67ed2` is on `main`; nothing outstanding in the tree |

## Summary

**By severity:** 1 blocker, 5 major, 8 minor — 14 gaps, itemized in `gaps.md`.

The plan did real work and most of it holds. `_has_update_movement` is gone, the credit is a pure
comparison against a recorded merge-candidate SHA, `observed_keys` survives only as prose, `declined`
is a genuine blocking taxonomy member wired from the trigger-A re-review through to the pre-merge
barrier, and the idempotence regressions are real tests that genuinely fail against the pre-fix
predicate — 355 tests across the six affected surfaces pass today, and the currency machinery and the
participation loop are unchanged since the landing. What it did not do is close the class. A
`participation_requires_update` bot's second evidence comment still slips past the currency test and
credits an advanced HEAD, because the participation loop short-circuits per bot and so never gives that
comment a ledger row — reproduced end-to-end against the shipped producer, not merely read; the stated
rule reaches one of the three registered bots while claiming to govern every site; the first-observation
arm is documented as a definitional truth rather than the fail-open assumption it is; eight prose sites
across three skills still describe the predicate that was deleted or the two-source anchor that was
abandoned, three of them written by this very landing; and `report-01.md` names three symbols and a test
that were never in the tree. The verdict is **verified-with-gaps**: all four deliverables landed as
executable change with discriminating tests, the headline defects are closed on the path those tests
exercise, and the residual holes — including the blocker — are specific enough to be closed by a
follow-up plan rather than by re-doing the work.

## Adversarial review

An independent reviewer with no prior context re-derived every load-bearing finding above against the
tree at `HEAD` = `61a43e53`, treating written citations as claims to check rather than as evidence.

**Method, re-runnable.** (1) Every `path:line` citation in both documents was opened and compared
against the text quoted. (2) Every count and enumeration was re-derived: the taxonomy cardinality
(`_NON_PARTICIPATION_MEMBERS`, ten members), the per-site list-flag counts, the "N of M" test tallies,
the stale-prose site count, and the gap totals. (3) The three claims about executable behaviour were
settled by **running** them, not by reading: a probe module was created inside
`test/plan-marshall/workflow-integration-github/`, driven through the existing `_patch_provider` /
`_run_fetch` harness against the real `github_pr.cmd_fetch_findings`, then deleted; no tracked file was
modified and `git status --porcelain` was re-checked afterwards. (4) The plan's *Done when* clauses and
its claim-label table were re-walked independently, and the stale-prose sweep was re-run with a second
grep pattern because the first one provably misses sites.

**Outcome.** Upheld: C1, C2, C3, C4, C5, K3, K4, K5, K7, the deliverable verdicts D0–D4, the
out-of-scope compliance findings, and all sixteen report-claim rows. Three of those were upgraded from
*confirmed by reading* to *reproduced end-to-end* (C1, C3, C4). Overstated and now downgraded: K1's
sub-claim that nothing in the shipped tree discloses the currency rule's restricted reach — two contract
passages (`:478-479`, `:674`) do disclose the scope, so the defect is a contradiction with the rule's
stated reach rather than silence. Refuted: nothing in either document was found false; the one thing
refuted is a *plan hypothesis* the verification had not settled — the barrier does re-read findings at
the barrier (`branch-cleanup.md:732`), so it does not inherit a stale FIND-step result. Unverifiable
(unchanged): the `./pw verify` figures, the three intermediate commits, and the PR-side reviewer facts.

**Corrections applied.** Three drifted citations repaired
(`test_bot_participation_contract.py:775`→`:806-807`, `_NUMBER_WORDS[taxonomy_size]` line
`572`→`581`, `create-pr.md:201-204`→`:205-207`); the "five test surfaces / 344 tests" figure corrected
to six surfaces / 355; K2 raised from six sites to eight after a second grep pass surfaced
`workflow-integration-github/SKILL.md:129` — the deleted two-arm predicate restated in the canonical
`fetch_findings` step body of the skill that owns the code — and
`bot-participation-contract.md:230-232`, the abandoned two-source anchor; one gap added (the
decline-consumer doc test asserts bare substring presence); and the gap total moved from 13 to 14.

**Verdict unchanged.** `verified-with-gaps` remains right: every deliverable landed as real code with
tests that genuinely discriminate, and G1 — though blocker-class and live — is a reachable residual
hole in a shipped mechanism, not an unimplemented deliverable.
