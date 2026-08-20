> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Every participation credit is anchored to the commit being merged, and an unanchorable credit says so

**Epic:** review-apparatus
**Branch prefix:** fix — bug fix

## Problem

The pre-merge review barrier asks whether each required review bot reviewed **the tree being
merged**. The producer that answers it is `cmd_fetch_findings` in
`marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`. For a bot
that re-reviews by editing one persistent comment in place (`participation_requires_update: true`,
today PR-Agent), the credit is qualified by `_reviewed_at_merge_candidate`, which compares a
plan-scoped **currency ledger** row — the `(reviewed_commit_sha, updated_at)` recorded when that
comment was last credited — against the current PR HEAD. That machinery works for a bot with exactly
one evidence comment, degenerate inputs excluded. It is defeated by everything else.

**The headline defect: a second evidence comment bypasses the currency test entirely.** The
participation loop opens with `if not _bot_kind or _bot_kind in participated: continue`
(`github_pr.py:943`), and only the comment that was *credited* gets a ledger row (the
`currency_updates` staging at `github_pr.py:~968-974`). PR-Agent declares **two** publish shapes —
`issue_comment` (the persistent Reviewer Guide) and `inline` (`/improve` suggestions, one comment
each) — in `automatic-review/standards/pr-agent.md` § `participation_evidence`. So on a later fetch at
an advanced HEAD, the bot's first evidence comment fails the currency test and hits the `continue` at
`github_pr.py:967`; the loop then reaches the bot's **second** evidence comment, which has no ledger
row at all, so `_reviewed_at_merge_candidate` takes `if record is None: return bool(merge_candidate_sha)`
(`github_pr.py:701-702`) and credits the bot at the new HEAD. The emission subtraction
(`if bot not in participated` in the `stale_participation_bots[]` comprehension, `github_pr.py:~1266-1270`)
then also removes the bot from the stale set, so the barrier sees a clean `participated` for a commit
the bot never saw. Nothing narrows the reachable comment set first: participation is derived from
`raw_comments` before any filtering, and the fetch runs with `unresolved_only=False`
(`github_pr.py:881`), so even an already-resolved `/improve` suggestion supplies the bypassing credit.

Four further mechanisms in the same path make a credit, or its absence, unreliable. The
**first-observation arm** credits any comment absent from the ledger regardless of which commit the
bot actually reviewed, and `bot-participation-contract.md` § "Evidence for a bot that edits one
comment in place" states this as fact — "which is **by definition** an observation at the merge
candidate" — rather than as the bounded fail-open heuristic it is. The **fresh-edit arm**
(`return bool(updated_at) and updated_at != recorded_updated_at`, `github_pr.py:708`) is not guarded
on a resolvable merge-candidate SHA, and the credit path writes a ledger row whose
`reviewed_commit_sha` is the empty string when the head read failed — poisoning the row so
`recorded_sha == merge_candidate_sha` can never again be true. `_recorded_currency_records`
(`github_pr.py:600-624`) coerces a missing `reviewed_commit_sha` to `''` with no schema guard, so a
**pre-upgrade key-only row** reads as `('', '')` and falls through to the edit arm, which is true for
essentially any real comment — crediting a stale unchanged Guide once on the migration path. And when
`fetch_pr_head_sha` returns `''` on a provider hiccup (`_github_ci.py` § `fetch_pr_head_sha`:
"Returns the SHA on success or an empty string on any failure path"), an already-credited bot is
demoted into `stale_participation_bots[]` — a **blocking** state whose prescribed remedy is
"re-trigger a re-review", which cannot fix a read failure — while the `fetch_findings` return carries
no field at all reporting whether the SHA resolved.

Two adjacent mechanisms complete the picture. The cross-iteration filing dedup keys on
`(bot_kind, comment_id)` alone (`github_pr.py:1102`), with no content or edit term, so when PR-Agent
edits its one persistent Guide to carry a **real finding**, the currency test's fresh-edit arm credits
the bot as participating while the dedup drops the comment as a duplicate: the reviewer reads present
and clean, and its actual feedback never becomes a `pr-comment` finding. And the currency rule's
stated reach does not match its implemented reach — `bot-participation-contract.md` § "The currency
rule" says "This one rule governs every site that credits participation", while the code gates the
whole test on `bot_registry.participation_requires_update(_bot_kind)` (`github_pr.py:955`), and both
CodeRabbit and Sourcery declare that flag `false`.

Finally, none of this is pinned by a derived population. The site set that credits participation, or
that decides whether a comment is new information, is enumerated nowhere: a new crediting site can be
added and no test notices.

## Goal

A participation credit is evaluated for **every** evidence comment a currency-subject bot published,
never only the first, so no comment can arrive at an advanced HEAD without a history; each arm of the
currency predicate fails closed on degenerate input — an unreadable head SHA, a poisoned or
pre-upgrade ledger row, a comment older than the commit it is credited against; an unresolvable merge
candidate is reported as its own undecidable outcome and routed to UNKNOWN rather than silently
demoting a proven reviewer into a blocking stale state with the wrong remedy; an in-place edit that
carries new content is filed rather than deduped away; the contract's stated reach and the code's
implemented reach agree, and the ledger is named for what it holds. The population of sites this rule
governs is derived from the tree and asserted, so the next site added cannot escape it.

## Deliverables

Six deliverables. **D0 is a gate** — it derives the populations every later deliverable's tests
parametrize over, and it halts the run if that derivation is not possible. D1 is the blocker.

Each deliverable names the gap ids it discharges. Those ids refer to entries in two git-tracked files
that will be present in the clone —
`doc/plans/review-apparatus/010-participation-credited-from-a-superseded-commit/gaps.md` and
`doc/plans/review-apparatus/110-participation-derived-from-a-lossy-view/gaps.md` — which carry the
original evidence and the reproduction notes. **This plan is self-contained**; those files are
corroboration, not required reading, and the run is not blocked if it chooses not to open them.

1. **D0 (GATE) — Derive the participation-site population, or halt** — discharges `010 G9`,
   `110 G9`, `110 G10`.

   Derive two populations from the tree, in the pattern `test/_shared/_dispatch_roster.py` already
   uses (read it as the pattern; do not modify it):

   - **The currency-subject bot population** — `bot_registry.bot_kinds()` filtered on
     `bot_registry.participation_requires_update(bot)`. An equivalent derivation already exists as
     `_UPDATE_REQUIRING_BOTS` near `test/plan-marshall/workflow-integration-github/test_github_pr.py:2313`;
     reuse or lift it, do not re-hand-list it.
   - **The participation-site population** — scan `marketplace/bundles/**` for the sites that credit
     participation or decide whether a comment is NEW INFORMATION. The symbol family
     `_reviewed_at_merge_candidate`, `participation_requires_update`, `participation_evidence`,
     `head_sha_verified`, `stale_participation`, `existing_comment_keys`,
     `_is_self_authored_response` is a **seed, not the population**. A hand-maintained seed is the
     defect class this deliverable exists to close, so it is protected in **both** directions by a
     drift check living in the same test module:

     - **No stale member.** Every seed symbol must resolve to at least one occurrence under
       `marketplace/bundles/**`. A seed symbol with zero hits **fails the test** — a rename that
       silently narrows the scan is exactly how the population goes quietly incomplete.
     - **No missed member.** Derive a candidate set **independently of the seed**: AST-walk
       `github_pr.py`, `_github_pr.py` and `bot_registry.py`, collect the module-level and
       class-level names they define, and keep those whose name carries any of the participation
       vocabulary stems `particip`, `reviewed`, `stale`, `head_sha`, `comment_key`,
       `merge_candidate`. Assert every candidate is **either** in the seed **or** carries a written
       exclusion reason recorded in the same module. A newly added crediting symbol therefore either
       joins the population or fails the test; it cannot be absent from both.

     Guard the population non-empty **at import**, and publish its size.

   Give each discovered site a per-site **expectation record** stating three things: what it reads
   (the live scan / the durable currency ledger / a deduped projection), what it anchors on (a commit
   SHA or a timestamp), and whether its verdict is idempotent. Two members must be classified
   explicitly, because the tree classifies them nowhere today:

   - the `pr wait-for-comments` two-arm completion predicate (its movement arm is described at
     `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/api-contract.md:159`
     and `workflow-integration-github/SKILL.md` § the comment-path matcher) — timestamp-anchored.
     Record in `bot-participation-contract.md` whether a timestamp-anchored completion arm is
     **correct for a wait**, on the stated ground that a wait asks "did anything move since I
     started?", which is a different question from "did this review the merge candidate?". State the
     answer; do not file a follow-up from within this run.
   - `_is_self_authored_response` (`github_pr.py:368`, called at `:1069`) — record it as the third
     comment-identity in force, and state whether D4's widened dedup identity subsumes it.

   Then remove the hand-listed bot names at
   `test/plan-marshall/workflow-integration-github/test_github_pr.py:195`
   (`assert first_bots == ['coderabbit', 'pr-agent', 'sourcery']`) by deriving the expected
   participant list from the registry intersected with the bots represented in the module's
   `_COMMENTS` fixture.

   ⛔ **HALT condition — executable, and readable from this plan alone.** If either population cannot
   be derived from the tree — the scan yields an empty site set, the seed's two-way drift check
   cannot be run, or the registry accessor is unavailable — the run **STOPS at D0**: it reverts any
   partial D0 edit, makes **no** change to any file named in § Expected surface, starts **none** of
   D1–D5, and writes a run report whose first line records the plan as **BLOCKED AT D0**, naming
   which derivation failed and what was tried. Do **not** substitute a hand-maintained roster: a
   hand-maintained list is the exact defect class this deliverable exists to close, so a fallback
   would reproduce the defect inside the fix.

   ⛔ **Precondition for D1–D5.** Each of D1, D2, D3, D4 and D5 begins **only** after D0 has reported
   PASS — both populations derived, non-empty, and their sizes published. A run that reaches any
   later deliverable without that report has violated the gate; there is no partial-credit path in
   which some deliverables ship after a failed derivation. This precondition is restated at the head
   of each later deliverable so it binds wherever the run resumes reading.

   *Done when:* adding a new participation-crediting site under `marketplace/bundles/**` without a
   matching expectation record fails a test **at import**; both populations publish their size and
   fail when empty; the seed's drift check fails both when a seed symbol resolves nowhere and when a
   vocabulary-matching symbol is neither seeded nor given a written exclusion reason; and
   `test_a_deduped_comment_is_still_credited_as_participating` contains no bot-name literal while
   still failing if participation is re-coupled to `existing_comment_keys`. If instead D0 halted, the
   report carries the BLOCKED AT D0 line and the diff carries no change to any deliverable's surface.

2. **D1 (BLOCKER) — Evaluate the currency test for every evidence comment, not just the first** —
   discharges `010 G1`.

   ⛔ **Precondition: D0 reported PASS.** If D0 halted, this deliverable does not start.

   In the participation loop (`github_pr.py:~941-975`), stop short-circuiting a currency-subject bot
   at its first credit. For a bot declaring `participation_requires_update`, **evaluate** every
   comment whose `kind` is one of that bot's declared publish shapes — whether or not the bot is
   already credited on this fetch. The participation verdict is unchanged: the bot is credited if
   **any** of its evidence comments passes. What changes is that no evidence comment can reach a
   later HEAD without a history.

   ⚠ **Evaluate every evidence comment; stage a ledger row only for the ones that PASS.** A
   currency-ledger row per `(bot_kind, comment_id)` is written or refreshed **only** when that
   comment passed the currency predicate on this fetch. A comment that **fails** leaves its ledger
   row exactly as it stood — unchanged if it had one, and none written if it had none. Staging a row
   for a failing comment would stamp the current HEAD onto stale evidence, and the very next fetch
   would read `recorded_sha == merge_candidate_sha` and credit the comment the previous fetch had
   just rejected — reintroducing the defect this deliverable closes, one fetch later.

   Correct the `cmd_fetch_findings` docstring sentence at `github_pr.py:~779-783` — "recorded
   uniformly whether the comment was stored as a finding or dropped as noise" is true of the storage
   axis and false of the per-comment axis — in the same change, and state the pass-only staging rule
   there so the writer's condition is documented where its reader looks.

   *Done when:* a new test in `test_github_pr.py`, parametrized over D0's currency-subject population,
   fetches at HEAD_A with **two** unchanged evidence comments of the same bot present, then fetches at
   an advanced HEAD_B with both comments unchanged, and asserts `participated_bots == []` with the bot
   present in `stale_participation_bots[]`; and a **regression test for the staging rule** performs a
   **third** fetch at the unchanged HEAD_B and asserts the identical verdict, proving the failing
   comments were not stamped with HEAD_B by the fetch that rejected them — a stale comment stays stale
   across consecutive fetches. The run records, verbatim in the report, that both tests **fail against
   the pre-change code** — a test that passes both before and after has not pinned the defect.

3. **D2 — Make every arm of the currency predicate fail closed on degenerate input** — discharges
   `010 G3`, `010 G7`, `010 G8`.

   ⛔ **Precondition: D0 reported PASS.** If D0 halted, this deliverable does not start.

   Three changes to `_reviewed_at_merge_candidate` (`github_pr.py:652-708`) and its writer:

   - **First-observation arm** (`if record is None: return bool(merge_candidate_sha)`): obtain the
     merge-candidate commit's own timestamp alongside the head SHA, and withhold the first-observation
     credit when the comment's `created_at`/`updated_at` **predate** that commit. **Decided here, so
     the run does not decide:** if the commit timestamp cannot be read, the arm keeps today's
     behaviour (credit on a resolvable SHA) and the unresolved read is reported through D3's signal —
     a failed timestamp read introduces no new blocking. Then rewrite the contract sentence in
     `bot-participation-contract.md` § "Evidence for a bot that edits one comment in place" that
     calls this arm a definition, so it states a **bounded assumption**: what it cannot verify (a
     fetched comment carries no reviewed SHA), why, and which direction it errs in.
   - **Fresh-edit arm**: guard it on a resolvable `merge_candidate_sha`, so an unreadable head fails
     closed on **every** arm; and never call `_record_currency_records` with an empty
     `reviewed_commit_sha`, so no ledger row is written that can never again match a head.
   - **Ledger reader**: treat a row whose `reviewed_commit_sha` is missing or empty as **no usable
     record** when building the map, so the comment takes the guarded first-observation arm instead of
     falling through to the edit arm. This is the pre-upgrade key-only row the earlier artifact wrote.

   *Done when:* three tests pass and each is recorded as failing against the pre-change code — (a) a
   comment whose timestamps predate the merge-candidate commit resolves to `participated_stale` on
   its first observation; (b) ledger row present + fresh edit + empty head SHA returns the same
   blocking answer on both consecutive fetches, and no ledger row with an empty
   `reviewed_commit_sha` is written; (c) a ledger holding only key-only rows produces the same verdict
   as an empty ledger.

4. **D3 — An unresolvable merge candidate is undecidable, not stale** — discharges `110 G1`.

   ⛔ **Precondition: D0 reported PASS.** If D0 halted, this deliverable does not start.

   `cmd_fetch_findings` emits `merge_candidate_sha_resolved: bool`, derived from
   `bool(reviewed_commit_sha)` (`github_pr.py:904`). When it is `false`, a currency-subject bot whose
   comment already matched a declared publish shape is reported in a **new**
   `undecidable_participation_bots[]` field — same `{bot_kind, evidence_kind}` record shape as the
   existing sets — and is reported in **neither** `participated_bots[]` (no credit on an unreadable
   head) nor `stale_participation_bots[]` (its remedy, re-trigger a re-review, cannot fix a read
   failure). Document both new fields in `workflow-integration-github/SKILL.md`
   § `github_pr fetch_findings` and in `bot-participation-contract.md` § "Consumers". Add to
   `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
   § "UNKNOWN — the re-fetch itself failed" that a `fetch_findings` return carrying
   `merge_candidate_sha_resolved: false` is one of the shapes routing to UNKNOWN — consistent with
   that section's existing positive-validation rule and its "an absent input is an UNKNOWN verdict,
   never a `false` the operator can act on". Finally, qualify the unconditional sentence in
   `_reviewed_at_merge_candidate`'s docstring — "the verdict is a PURE COMPARISON that consumes no
   observation state — so it is identical however many times it is evaluated" — to the scope the code
   actually has, since a resolved-then-unresolved sequence refutes it as written.

   *Done when:* a test parametrized over D0's currency-subject population performs fetch 1 at a real
   head (bot credited), then fetch 2 with `head_sha=''`, and asserts the bot is **absent** from
   `stale_participation_bots[]`, **present** in `undecidable_participation_bots[]`, and that the
   return carries `merge_candidate_sha_resolved: false`; the test is recorded as failing against the
   pre-change code; and no docstring in `github_pr.py` claims an idempotence the mixed sequence
   refutes.

5. **D4 — Give the cross-iteration dedup an edit term** — discharges `110 G2`.

   ⛔ **Precondition: D0 reported PASS.** If D0 halted, this deliverable does not start.

   Widen the filing dedup identity at `github_pr.py:1102` from `(bot_kind, comment_id)` to
   `(bot_kind, comment_id, updated_at)`, falling back to a body digest where `updated_at` is absent,
   so an in-place-edited review presents as new information while an unchanged re-fetch still
   dedupes. This requires the third term to survive into the stored finding and back out again:
   `detail_lines` (`github_pr.py:~1113-1118`) carries `pr_number`, `kind`, `author`, `thread_id`,
   `comment_id` and no `updated_at` today, and `_existing_pr_comment_keys` reads only the comment id
   — both need the new term. **Decided here, so the run does not decide:** a stored finding carrying
   **no** `updated_at` term is a pre-upgrade row and dedupes on the two-term key for that
   `(bot_kind, comment_id)`, matching any `updated_at`; otherwise the upgrade would re-file a PR's
   entire comment history once. State the new identity in the in-source rationale block above the
   dedup (`github_pr.py:~1095-1101`) and in `workflow-integration-github/SKILL.md`
   § `github_pr fetch_findings`.

   *Done when:* a test proves a comment re-fetched with a **moved** `updated_at` and a changed body is
   filed as a new `pr-comment` finding (`count_stored == 1`, `count_skipped_duplicate == 0`) while the
   identical unchanged comment still dedupes; `test_second_fetch_dedupes_all_bot_kinds`
   (`test_github_pr.py:135`) and `test_same_comment_id_distinct_bots_not_collided` (`:209`) both still
   pass; and a test covers the pre-upgrade row that carries no `updated_at`.

6. **D5 — Name the ledger what it holds, and make the contract's stated reach match the code's** —
   discharges `010 G11`, `010 G2`.

   ⛔ **Precondition: D0 reported PASS.** If D0 halted, this deliverable does not start.

   - **Rename.** `_DROPPED_COMMENT_KEYS_ARTIFACT` (`github_pr.py:590`, value
     `'pr-noise-dropped-comments.jsonl'`) and `_dropped_comment_keys_path` (`:593`) name a noise-drop
     sidecar, but the artifact records `(reviewed_commit_sha, updated_at)` for **every** credited
     currency-subject comment, stored-as-finding and noise-dropped alike — the module's own comment at
     `:569-574` says so. Rename to `_CURRENCY_LEDGER_ARTIFACT` / `_currency_ledger_path` with a
     filename that says currency ledger, and make the reader **read both names** (old filename when
     the new one is absent) while writing only the new one. **The "observation sidecar" paragraphs in
     `bot-participation-contract.md` are not this deliverable's, per the README table** — it assigns
     them elsewhere. Report their state as a cross-plan dependency rather than editing them.
   - **Scope.** The contract says the currency rule "governs every site that credits participation";
     the code gates it on `participation_requires_update`. **This plan decides the disposition; the
     run implements it and does not re-open it.** Implement the contract-narrowing disposition:
     rewrite the scope sentence to the reach the code has, and add an explicit § naming the
     currency-blind path for append-per-review bots (`participation_requires_update: false`) as an
     **accepted, bounded gap**, stating its reason and the condition under which it is revisited.
     Separately, **record in the run report — as a proposal for the operator, not as work done** —
     the alternative disposition of extending the currency ledger to every bot declaring
     `participation_evidence`, together with its blast radius: it changes the barrier verdict for
     every consumer project whose `required_bots` includes an append-per-review bot, which this run
     can neither observe nor obtain sign-off for.

   *Done when:* no identifier, filename or docstring **in the code this plan changes** calls the
   currency ledger a noise-dropped-comment record — the contract's "observation sidecar" paragraphs
   are the sibling plan's per the README table, so their wording neither satisfies nor blocks this
   clause, and the run reports their state instead; a ledger written under the old filename is still read after the
   rename, pinned by a test; the contract's scope sentence and the `_requires_update` guard at
   `github_pr.py:955` agree; a test asserts the documented (still-credited) behaviour for a
   `participation_requires_update: false` bot after a HEAD advance; and the run report carries the
   alternative disposition as a written proposal.

## Out of scope

Every entry states why, because with no operator watching mid-run the written boundary is the only
thing holding it.

- **The stale-prose sweep** (`010 G4`) — restatements of the deleted two-arm predicate and its
  abandoned two-source anchor across `workflow-integration-github/SKILL.md`,
  `automatic-review/SKILL.md`, `pr-agent.md`, `bot_registry.py` and the contract passages that are
  not this plan's, per the README table. Re-derive the site set from `010 G4` § Where; it is not counted
  here, because a count in this position goes stale the moment either plan is edited.
  Excluded because a documentation sweep across two skills would dwarf the behaviour change in the
  diff and make the currency fix unreviewable by the PR's reviewers. D2 and D5 rewrite **only** the
  specific sentences they name and open no sweep, even where an adjacent line is also stale.
- **Decline accounting** (`010 G6`) — making the trigger-B and `not_triggered`-remediation consumers
  honour `head_sha_verified`. Excluded because it is about whether a bot *declined* a re-review, not
  about whether a credit is current; it touches `automatic-review/SKILL.md`'s workflow bodies and a
  separate flag-count assertion, neither of which any deliverable here goes near.
- **Refusal-pattern drift and the refusal fixture** (`110 G3`, `110 G4`) — excluded because refusal
  detection decides whether a bot reviewed *at all*, a different question from whether its review is
  current, and it lives in a different surface (`_github_pr.py`'s matchers, the registry's
  `refusal_patterns`, `test_refusal_recovery_arming.py`).
- **Per-bot trigger semantics** (`110 G5`) — excluded because it is registry-schema work about how a
  review is *requested*, changing the await/trigger path, which no deliverable here touches.
- **Report and docstring corrections in landed plan directories** (`010 G5`, `010 G10`, `010 G12`,
  `010 G13`, `110 G6`, `110 G7`, `110 G8`) — excluded because they are record-keeping about earlier
  runs rather than currency defects, and folding a report amendment into a behaviour PR makes the
  merge gate's reviewers read two unrelated diffs.
- **A new taxonomy member in `review_completeness` for the undecidable verdict** — excluded because
  the participation taxonomy is the contract's and is restated by every consumer doc; widening the
  classifier is a plan of its own. D3 lands the producer-side signal and the UNKNOWN routing, which
  is the prerequisite for it.
- **Implementing disposition (a) of `010 G2`** (currency-testing append-per-review bots) — excluded
  from implementation and recorded as a proposal instead, because it changes the merge verdict for
  every consumer project whose `required_bots` includes CodeRabbit or Sourcery, and a cloud run can
  neither observe those bots' real publishing behaviour nor obtain the sign-off such a change needs.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — the
  currency ledger constants and helpers, `_reviewed_at_merge_candidate`, the participation loop, the
  filing dedup, the finding `detail`, and the `fetch_findings` return dict. Every deliverable but D0
  touches it.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — the
  `github_pr fetch_findings` step body: the two new return fields (D3) and the widened dedup identity
  (D4).
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  — exactly the rows the README table (§ "The shared-document split") assigns to `500`, and nothing
  else: the currency-rule scope sentence and the bounded-gap § (D5), the first-observation arm's
  wording (D2), the § "Consumers" rows (D3), and D0's recorded answer on the wait predicate.
  **D0's NEW-INFORMATION site classification is recorded in the expectation records, not in this
  document** — do not write it here.
  **The "observation sidecar" paragraphs are NOT in this plan's surface, per the README table** — it
  assigns them elsewhere, and D5 defers them. If the branch diff touches them, that is collateral to
  report, not scope.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` —
  § "UNKNOWN — the re-fetch itself failed" gains the unresolved-head shape (D3).
- `test/plan-marshall/workflow-integration-github/test_github_pr.py` — the new currency tests (D1,
  D2, D3, D4, D5) and the de-hand-listed assertion at `:195` (D0).
- `test/plan-marshall/automatic-review/test_bot_participation_contract.py` — the derived
  participation-site roster and its expectation records may live here or in a new sibling module;
  either is acceptable, the run states which it chose.
- `test/_shared/_dispatch_roster.py` — **read as the derivation pattern, not modified.**

## Claim labels

Every claim below was checked by reading the named file in the tree at the branch this plan was
authored from. Line numbers are **leads**: re-derive each by symbol or by quoted phrase before relying
on it, because an unrelated edit shifts them.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The participation loop short-circuits a bot at its first credit | OBSERVED | `github_pr.py:943` — `if not _bot_kind or _bot_kind in participated: continue` |
| Only the credited comment gets a currency-ledger row | OBSERVED | `github_pr.py:~968-974` — the `currency_updates[...]` staging inside the credited branch |
| A record-less comment is credited whenever the head SHA is readable | OBSERVED | `github_pr.py:701-702` — `if record is None: return bool(merge_candidate_sha)` |
| PR-Agent declares two publish shapes, so a second evidence comment exists | OBSERVED | `automatic-review/standards/pr-agent.md` § `participation_evidence` — `issue_comment` then `inline` |
| The fetch is unfiltered and resolution-blind, so a resolved `inline` comment still reaches the loop | OBSERVED | `github_pr.py:881` — `fetch_comments(pr_number, unresolved_only=False)` |
| The stale set subtracts the participated set before emitting | OBSERVED | `github_pr.py:~1266-1270` — `if bot not in participated` in the `stale_participation_bots[]` comprehension |
| The fresh-edit arm is unguarded on a resolvable head SHA | OBSERVED | `github_pr.py:708` — `return bool(updated_at) and updated_at != recorded_updated_at` |
| The ledger reader coerces a missing SHA to `''` with no schema guard | OBSERVED | `github_pr.py:600-624` — `str(record.get('reviewed_commit_sha') or '')` |
| `fetch_pr_head_sha` returns `''` on any failure path | OBSERVED | `_github_ci.py` § `fetch_pr_head_sha` docstring |
| The `fetch_findings` return carries no head-SHA resolution field | OBSERVED (asserted **absence**) | The `result` dict literal in `cmd_fetch_findings` (`github_pr.py:~1245-1305`) — read the whole literal and both conditional `result[...]` additions; the absence is refuted by finding any resolution-status key |
| The filing dedup has no content or edit term | OBSERVED | `github_pr.py:1102` — `if (bot_kind or '', comment_id) in existing_comment_keys` |
| The stored finding's `detail` carries no `updated_at` | OBSERVED (asserted **absence**) | `github_pr.py:~1113-1118` — the `detail_lines` list literal |
| The contract claims the rule governs every crediting site, while the code gates it on `participation_requires_update` | OBSERVED | `bot-participation-contract.md` § "The currency rule" vs `github_pr.py:955` |
| CodeRabbit and Sourcery both declare `participation_requires_update: false` | OBSERVED | `automatic-review/standards/coderabbit.md` and `.../sourcery.md`, the YAML registry blocks |
| The contract states the first-observation arm as a definition | OBSERVED | `bot-participation-contract.md` § "Evidence for a bot that edits one comment in place" — "which is by definition an observation at the merge candidate" |
| The ledger constant and path helper are named for noise-dropped comments | OBSERVED | `github_pr.py:590` and `:593` |
| No test derives or asserts a participation-**site** population | OBSERVED (asserted **absence**) | Search `marketplace/bundles/**` symbol names and `_dispatch_roster` across `test/`; the nearest existing rosters are `_UPDATE_REQUIRING_BOTS` (`test_github_pr.py:~2313`, a **bot** population) and `TestCallSitePopulation` / `_scan_invocation_sites` (`test_bot_participation_contract.py:~860-1010`, a **doc-invocation** population). Refuted by finding any test that scans for `_reviewed_at_merge_candidate` or `stale_participation` across the bundles |
| `test_github_pr.py:195` hard-codes the three bot kinds | OBSERVED | `assert first_bots == ['coderabbit', 'pr-agent', 'sourcery']` |
| The wait-for-comments movement arm is timestamp-anchored, not SHA-anchored | OBSERVED | `tools-integration-ci/standards/api-contract.md:159` — "the LATER of that comment's `updated_at` / `created_at` moving strictly past the wait-start" |
| `branch-cleanup.md` has an UNKNOWN section D3 can extend | OBSERVED | `phase-6-finalize/standards/branch-cleanup.md` § "UNKNOWN — the re-fetch itself failed" |
| The named existing tests exist and can be regression-checked | OBSERVED | `test_github_pr.py` — `test_second_fetch_dedupes_all_bot_kinds:135`, `test_a_deduped_comment_is_still_credited_as_participating:166`, `test_same_comment_id_distinct_bots_not_collided:209`, `test_unresolvable_head_sha_fails_closed_and_stays_idempotent:2462`, `test_a_fresh_comment_outranks_a_stale_one_through_the_subtraction:2553` |
| The three asserted absences above are true of the tree the run clones | HYPOTHESIS | Re-run each named read at the run's own HEAD before building against it. An absence asserted at authoring time is the highest-risk claim here: if any of the three already exists, the corresponding deliverable is a modification, not an addition, and the run says so in its report |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.

## Verification

Beyond each deliverable's *Done when*:

- **Build gate.** This plan changes Python, so run the repository build (`./pw verify`) per the lane
  contract's build gate and report its result. Do not treat a wrapper exit code as the verdict — read
  the reported status and errors.
- **Every new test must discriminate.** For D1, D2, D3, D4 and D5, record in the run report — per
  test, not as a summary — that the test **fails against the pre-change code**. A test that passes
  before and after has pinned nothing. This is the plan's primary evidence, so state it explicitly
  even where it seems obvious.
- **No regression in the existing currency and dedup suites.** Run at minimum
  `test/plan-marshall/workflow-integration-github/test_github_pr.py`,
  `test/plan-marshall/workflow-integration-github/test_pr_agent_contentless_guide_interaction.py`,
  `test/plan-marshall/automatic-review/test_bot_participation_contract.py` and
  `test/plan-marshall/automatic-review/test_review_completeness.py`, and report the counts. The
  counts are leads — re-derive them from the run's own output, never from this plan.
- **⭐ Cold read of the contract text** — required, because D2, D3 and D5 are text whose whole value is
  what a later reader does with it, and "implemented as specified" cannot verify that. Have the pre-PR
  verification sub-agent read the **changed** text of `bot-participation-contract.md` §§ "The currency
  rule", "Evidence for a bot that edits one comment in place" and the new bounded-gap section, plus
  the changed `branch-cleanup.md` UNKNOWN paragraph, **cold — without this plan** — and report, in its
  own words:
  (a) which commit a participation credit is evaluated against;
  (b) for a bot that publishes a new comment per review, whether the credit is currency-tested at
  all — and whether the contract *says so*, or whether the reader had to infer it;
  (c) when the merge-candidate SHA cannot be read, whether the affected bot **blocks**, is
  **disclosed**, or is **ignored**;
  (d) for a comment the ledger has never seen, whether the contract presents the credit as something
  it **verified** or as something it **assumes**, and which way the assumption errs. This question is
  **this plan's**, because D2 rewrites that sentence; plan `510`'s cold read is instructed not to ask
  it, so it is asked here or nowhere.
  **Record the reading verbatim in the run report.** The intended answers are (a) the merge candidate,
  (b) no, and the contract says so explicitly, (c) it blocks as UNKNOWN and is never authorizable,
  (d) a bounded assumption — a fetched comment carries no reviewed SHA, so the arm errs toward
  crediting, and the contract says so rather than calling it a definition. A
  divergence means the *wording* failed, however complete the change looks — fix the wording and
  re-read, do not argue the reading away.
- **Cold read of the halt condition** — have the same sub-agent read D0's expectation-record scheme
  cold and state what happens when a new participation-crediting site is added with no record. If the
  answer is anything other than "a test fails at import", D0 is not done.
- **Read for collateral change.** Diff the branch against its base and confirm every changed path
  appears in § Expected surface. Any path outside it is reported in the run report with the reason it
  was touched.

## Notes

- **`.plan/` is all but invisible to this run, and nothing here requires it.** The orchestrator
  ledger, the plan specs and the landing records are git-ignored and absent from the clone. **Do not
  go looking for any of them.** `.plan/` carries exactly two tracked exceptions
  (`.plan/marshal.json` and `.plan/project-architecture/`, per `.gitignore:45-47`), so
  `marshal.json` *is* readable in the clone — re-derive that from `.gitignore` rather than trusting
  this sentence. Reading it is still not required: it records this repository's `required_bots` as
  PR-Agent only, which is why the `010 G2` scope defect is inert *here*, and that is an operator
  knob rather than an invariant. **Report whatever value you observe; never transcribe one from this
  plan or from a gaps file**, and let no deliverable's outcome depend on the value.
- **Sequencing against plan `510`.** `510-a-refusal-is-recorded-as-a-refusal-and-the-contract-says-so`
  edits two surfaces this plan also edits — `github_pr.py`'s participation path and
  `bot-participation-contract.md` — so **the two MUST NOT run concurrently.** (`510` also edits
  `automatic-review/SKILL.md`; this plan does not — see § Out of scope.) The boundary: this plan owns the **currency mechanics** — the per-comment ledger,
  the SHA anchor, the dedup identity — and `510` owns **refusal and decline accounting**: the refusal
  `cause`/`cap` producers, wording drift, the registry, and the decline consumers.
  **`bot-participation-contract.md` is shared.** Do not resolve ownership from this plan: read
  the table in [`doc/plans/review-apparatus/README.md`](../README.md) § "The shared-document
  split", which is the **single authority** for who writes which passage. Nothing in this plan
  assigns a passage; where a deliverable names one, it does so to identify a site it edits or defers,
  never to state who owns it — because a split written down twice goes stale in one copy, which is
  the failure this pointer exists to prevent. Read the table, write only the rows
  it assigns to `500`, **report** any passage it does not name rather than choosing, and never revert
  or rewrite a passage the other plan has already written.

- **Corroborating evidence lives in git**, in the two `gaps.md` files named under § Deliverables and
  the `verification.md` beside each. They carry the original reproduction notes, including an
  end-to-end reproduction of D1's defect driven through the real `cmd_fetch_findings`. They are
  optional reading; this plan restates everything the run needs.
- **Sequencing.** D0 gates everything — its populations are what D1–D5's tests parametrize over. Do
  D1 before D2 and D3: all three edit the same predicate and the same loop, and landing the blocker's
  structural change first keeps the later diffs small. D4 is independent of D1–D3 and may be done at
  any point after D0. Do **D5's rename last**, after the behaviour changes: renaming the ledger
  symbols first would churn every other deliverable's diff and make review harder.
- **D2 and D3 interact, and both apply.** D2 makes every predicate arm fail closed when the head SHA
  is unreadable — no credit. D3 decides where that non-credit is *reported* — `undecidable`, not
  `stale`. Neither supersedes the other; implementing only one leaves either a false credit (D2
  alone missing) or a false blocking-stale with the wrong remedy (D3 alone missing).
- **The blocker's reproduction, restated so the run need not re-derive it.** Two evidence comments of
  a `participation_requires_update` bot, both present and unchanged at both fetches; fetch once at
  HEAD_A, advance HEAD, fetch again. Today the second fetch returns the bot in `participated_bots[]`
  with `stale_participation_bots[] == []`. It must return `participated_bots[] == []` with the bot in
  `stale_participation_bots[]`.
- **Counts in this plan are leads.** Six deliverables, eleven gap ids, three registered review bots,
  one of them currency-subject, three asserted absences. Re-derive every one of these against the
  clone before relying on it — a bot added or a symbol renamed between authoring and execution
  silently invalidates a baked-in number.
- **No plugin-cache sync is owed.** This plan edits `marketplace/bundles/`, but the standalone plan
  lane neither performs a sync nor records one as owed; the merged bundle source is authoritative.
