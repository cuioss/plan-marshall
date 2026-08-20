# Gaps — 010-participation-credited-from-a-superseded-commit

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Give every evidence comment of a currency-subject bot its own ledger row, so a second comment cannot bypass the currency test

- **Severity:** blocker
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:941-975`
  (the participation loop), specifically the short-circuit at `:943` and the first-observation arm at
  `:701-703`; the emission subtraction at `:1263-1271`
- **Evidence:** The loop reads
  `if not _bot_kind or _bot_kind in participated: continue`, so once a bot is credited no further
  comment of that bot is evaluated — and only the credited comment gets a `currency_updates` row
  (`:970-974`). On a later fetch at an advanced HEAD the first comment fails the currency test and hits
  `continue` at `:967`; the loop then reaches the bot's **second** evidence comment, which has no
  ledger row, so `_reviewed_at_merge_candidate` takes `if record is None: return bool(merge_candidate_sha)`
  and credits it at the new HEAD. The subtraction at `:1270` (`if bot not in participated`) then also
  drops the bot from `stale_participation_bots[]`, so the barrier sees a clean `participated`.
  Reachable for the only currency-subject bot: `automatic-review/standards/pr-agent.md:80-83` declares
  two publish shapes, `issue_comment` (the Guide) and `inline` (`/improve` suggestions, one comment
  each). No pre-filter narrows it: participation is derived from `raw_comments` before filtering and
  `cmd_fetch_findings` fetches with `unresolved_only=False` (`github_pr.py:881`), so even an
  already-resolved inline comment supplies the bypassing credit.
  CONFIRMED **and reproduced end-to-end** against the shipped producer: driving the real
  `cmd_fetch_findings` twice with two unchanged `pr-agent` evidence comments present at both fetches
  and `head_sha` advanced between them returns `participated_bots = [{pr-agent, issue_comment}]` on
  BOTH fetches, with `stale_participation_bots = []` on the second. No test covers it — the only
  two-comment case, `test_a_fresh_comment_outranks_a_stale_one_through_the_subtraction`
  (`test/plan-marshall/workflow-integration-github/test_github_pr.py:2553`), introduces its second
  comment only on the second fetch, so it exercises a genuinely new comment.
  The module docstring at `github_pr.py:779-782` compounds it by describing the ledger as recording
  each credit "uniformly whether the comment was stored as a finding or dropped as noise" — true of the
  storage axis, false of the per-comment axis.
- **Impact:** A `/improve` inline suggestion posted at commit N credits participation at commit N+1
  with no re-review. This is the plan's own headline false positive, still live: the pre-merge barrier
  passes for a tree the required bot never saw.
- **Task:** Evaluate the currency test for **every** comment of a `participation_requires_update` bot
  rather than stopping at the first credit — accumulate a ledger row per `(bot_kind, comment_id)` for
  each comment whose `kind` is a declared publish shape, whether or not the bot is already credited on
  this fetch. Keep the participation verdict "credited if ANY of the bot's evidence comments passes",
  but ensure every evaluated comment is recorded so no comment can arrive at a later HEAD without a
  history. Correct the `github_pr.py:779-782` docstring in the same change. Add a test: fetch at HEAD_A
  with two evidence comments of the same bot present, advance to HEAD_B with both unchanged, assert
  `participated_bots == []` and the bot in `stale_participation_bots[]`.
- **Done when:** With two unchanged evidence comments of a `participation_requires_update` bot present
  at both fetches, a HEAD advance resolves the bot to `participated_stale`, and the new test fails
  against the current code.
- **Suggested grouping:** workflow-integration-github / participation currency

## G2 — Apply the currency rule to every bot, or state in the contract that it applies only to `participation_requires_update` bots

- **Severity:** major
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:955-958`;
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:211-212`
- **Evidence:** The contract states "This one rule governs every site that credits participation"
  (`bot-participation-contract.md:211-212`), but the code gates the whole test on
  `_requires_update = bot_registry.participation_requires_update(_bot_kind)` (`github_pr.py:955`).
  `coderabbit.md:43` and `sourcery.md` declare `false`, so for those bots participation is still
  presence of a declared publish shape, computed from `raw_comments` before any filtering
  (`github_pr.py:917-919`) — a comment posted at commit N is still present and still credits at N+1.
  `report-01.md` § D0 row S2 records this exactly ("no currency test runs at all for these bots …
  currency-blind") and no deliverable disposes of it. The contract does disclose the *scope* twice in
  passing — `bot-participation-contract.md:478-479` ("today, only PR-Agent") and `:674` ("neither bot
  declares `participation_requires_update`, so neither can reach `participated_stale`") — but both sit
  in sections about something else and neither states the consequence, so the shipped defect is a
  contradiction between the rule's stated reach and the code's rather than an undisclosed restriction.
  CONFIRMED.
- **Impact:** The plan's original false positive survives unchanged for any project whose
  `required_bots` includes coderabbit or sourcery. It is inert in this repository only because
  `.plan/marshal.json` sets `"required_bots": "pr-agent"` — an operator knob, not an invariant.
- **Task:** Decide and implement one of two dispositions, and record which: (a) extend the currency
  ledger to every bot with a declared `participation_evidence`, anchoring an append-per-review bot on
  the merge-candidate SHA recorded when each of its comments was first credited; or (b) narrow the
  contract sentence to say the rule governs the `participation_requires_update` sites, and add an
  explicit § naming the currency-blind path for append-per-review bots as an accepted, bounded gap with
  its reason. Disposition (a) is the one the plan's Goal implies.
- **Done when:** The contract's scope sentence and `github_pr.py`'s guard agree, and a test asserts the
  chosen behaviour for a `participation_requires_update: false` bot after a HEAD advance.
- **Suggested grouping:** automatic-review / participation contract

## G3 — Stop asserting that a first observation is "by definition" an observation at the merge candidate

- **Severity:** major
- **Kind:** bug (fail-open) + stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:680-686`
  and `:701-703`; `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:235-236`
- **Evidence:** The contract states the arm as fact — "this fetch is the **first observation** of the
  comment, which is by definition an observation at the merge candidate." The code
  (`if record is None: return bool(merge_candidate_sha)`) credits any comment absent from the plan's
  ledger regardless of which commit the bot actually reviewed. A bot that finishes reviewing commit N
  and posts after N+1 lands is credited at N+1 on the first fetch that sees it. The plan's own § D0
  "Data constraint discovered" records why the true anchor is unavailable (a fetched comment carries no
  reviewed SHA), so the arm is a necessary fail-open heuristic — but it is documented as a definition.
  CONFIRMED by reading both.
- **Impact:** A review of an earlier commit is credited against the merge candidate whenever the plan's
  first fetch of that comment happens after HEAD advanced. A reader of the contract has no way to know
  the credit is unverified, so downstream work builds on a guarantee that does not exist.
- **Task:** (1) Tighten the arm where data allows: compare the comment's `created_at` / `updated_at`
  against the merge-candidate commit's own timestamp (obtainable alongside `fetch_pr_head_sha`) and
  withhold the first-observation credit when the comment predates the merge-candidate commit. (2)
  Rewrite `bot-participation-contract.md:235-236` to state the arm as a bounded assumption — what it
  cannot verify, why (comments carry no reviewed SHA), and which direction it errs in.
- **Done when:** A comment whose timestamps predate the merge-candidate commit resolves to
  `participated_stale` on its first observation, pinned by a test; and the contract text names the
  residual assumption instead of calling it a definition.
- **Suggested grouping:** workflow-integration-github / participation currency

## G4 — Sweep the eight prose sites that still describe the deleted two-arm predicate or its abandoned two-source anchor

- **Severity:** major
- **Kind:** stale-doc
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md:129`
  - `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:230-232`
  - `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:233`
  - `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:491-498`
  - `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:652`
  - `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md:86`
  - `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md:363`
  - `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py:486-487`
  - Test prose repeating the noise-sidecar framing:
    `test/plan-marshall/workflow-integration-github/test_pr_agent_contentless_guide_interaction.py:38-45,396-404,423-426`
- **Evidence:** Surviving text, each contradicted by `github_pr.py:600-708`:
  - `workflow-integration-github/SKILL.md:129` — "for a bot declaring `participation_requires_update` —
    the comment is **first-present or its `updated_at` has moved**". The deleted two-arm predicate,
    restated verbatim in the canonical `fetch_findings` step body of the skill that OWNS `github_pr.py`
    — the single most-read description of the behaviour, and the one an executing agent follows.
  - `bot-participation-contract.md:230-232` — the SHA arm read as two sources: "the
    `reviewed_commit_sha` stamped on the stored finding, or … the merge-candidate SHA the noise sidecar
    recorded when the comment was **first observed**". The shipped ledger is one source, covers stored
    and dropped comments alike, and is refreshed on every credit rather than frozen at first
    observation.
  - `:233` — "it was **edited in place** (`updated_at` differs from `created_at`) since it was posted".
    The code compares against the **recorded** `updated_at` (`:707-708`); the `created_at` form is the
    permanent "was ever edited" flag the PR reviewer flagged and the same landing removed.
  - `:491-498` — "the `reviewed_commit_sha` stamped on the `pr-comment` finding … evaluates the currency
    rule against the **union** of the stored-finding SHAs and the recorded sidecar SHAs". There is no
    union; `github_pr.py:915` reads one ledger, and no findings-derived SHA source exists.
  - `automatic-review/SKILL.md:652` — "only on first presence or observed `updated_at` movement", a
    verbatim restatement of the deleted predicate, in a workflow body an executing agent reads.
  - `pr-agent.md:86` / `:363` and `bot_registry.py:486-487` — the same "first presence OR updated_at
    movement" formulation, one of them inside the machine-readable registry record and one in
    production-code docstring prose.
  CONFIRMED by **two** grep passes over `marketplace/bundles/plan-marshall/skills/` and `test/` —
  `first presence|first-presence|updated_at movement|updated_at.*created_at` for the arm-wording
  family, and `first.present|updated_at (has )?mov|union of the stored|sidecar` for the rest. One pass
  is not enough: the first pattern misses `workflow-integration-github/SKILL.md:129` (which writes
  "first-present … has moved") and both two-source-anchor paragraphs. The `wait-for-comments`
  completion predicate (site S8) and the `github_re_review` matchers (S3/S4) are excluded from both —
  they are legitimately timestamp-keyed and are not the currency test.
- **Impact:** An agent or maintainer reading any of these implements or reasons against a predicate
  that no longer exists. Three of them were written by this landing and invalidated by its own late
  fix, so the contract now describes a design the code deliberately abandoned — and one of the
  survivors sits in the owning skill's own workflow body.
- **Task:** Rewrite all eight (plus the test prose) to the shipped three-arm predicate: SHA currency
  against the ledger's recorded `reviewed_commit_sha`; first observation, guarded on a resolvable
  merge-candidate SHA; fresh edit measured against the ledger's recorded `updated_at`. Delete the
  union-of-two-sources paragraphs in favour of the single currency ledger.
- **Done when:** Both searches above return no hit that describes the currency test, and each rewritten
  site names the ledger as the sole source.
- **Suggested grouping:** automatic-review / participation contract

## G5 — Correct the three report claims naming symbols that never existed

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/010-participation-credited-from-a-superseded-commit/report-01.md`
  § D2 (two symbols) and § D4 bullet 4 (one test)
- **Evidence:**
  - § D2: "the reviewed SHA per comment is the union of `_existing_pr_comment_shas` (stored-finding
    stamps) and `_recorded_dropped_comment_shas` (the noise sidecar…)". Neither symbol exists at `HEAD`
    nor in `git show 50f67ed2:…/github_pr.py` (grep count 0 in both). The landed reader is
    `_recorded_currency_records` (`github_pr.py:600`).
  - § D4: "`test_currency_anchor_is_derived_from_both_sha_sources` (both SHA sources are the SUT's own
    readers)". `grep -rn "def test_currency_anchor_is_derived_from_both_sha_sources" test/` → no match;
    `git log --all --oneline -S'currency_anchor_is_derived'` returns only the squash, which contains
    this report. The real test is `test_currency_anchor_is_recorded_in_the_ledger_on_credit`
    (`test/plan-marshall/workflow-integration-github/test_github_pr.py:2335`), and it asserts one ledger
    source.
  The cause is visible in the report itself: Finding 4 records that the late review-fix collapsed the
  two-source design into one ledger, but §§ D2 and D4 were never re-derived against the final tree.
- **Impact:** A named test that does not exist is the highest-severity kind of report defect — a later
  reader treats the coverage as present and does not re-check. The two symbol names send a maintainer
  looking for a two-source design that was deliberately removed.
- **Task:** Amend `report-01.md` §§ D2 and D4 to name the shipped symbols
  (`_recorded_currency_records`, `_record_currency_records`,
  `test_currency_anchor_is_recorded_in_the_ledger_on_credit`) and the single-ledger design, and note
  under Findings 4 that the D2/D4 text was re-derived after the fix.
- **Done when:** Every symbol and test name in `report-01.md` resolves to something present at `HEAD`.
- **Suggested grouping:** review-apparatus / plan reporting

## G6 — Make the trigger-B and `not_triggered`-remediation consumers honour `head_sha_verified`

- **Severity:** major
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:250` (trigger B),
  `:729` (the `not_triggered` remediation), and `:679` (the FIND-step `review_completeness check`
  invocation)
- **Evidence:** `bot-participation-contract.md:267-270` states the rule: "The deciding bit … is
  **computed and must be consumed**: a `matched: true` with `head_sha_verified: false` is a decline,
  never a completed re-review, and a consumer that reads `matched` alone credits a review that never
  named the commit it matched." `SKILL.md:250` says "When `matched: true`, the fresh review is now on
  the PR"; `SKILL.md:729` says "`matched: true` — that bot published a fresh review for this HEAD".
  `grep -c head_sha_verified marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
  returns **0**. `SKILL.md:679` does not interpolate `--declined-bots`, and
  `test/plan-marshall/automatic-review/test_bot_participation_contract.py:806-807` — the header comment
  on the `_CONFIRMED_SITES` roster at `:817` — records the omission as intentional: "the participation
  guard passes six (``--declined-bots`` is documented in the canonical block but not interpolated at
  the FIND-step site)". `report-01.md` § Residue names trigger B only; the `not_triggered`-remediation
  consumer with the identical defect is not named anywhere. CONFIRMED.
- **Impact:** A decline observed at the FIND-step loop-back or during `not_triggered` remediation is
  credited as a completed re-review, and never reaches the quorum as `declined`. D3 closes half of the
  "recorded-but-ignored bit" defect the plan's Notes describe.
- **Task:** Mirror `branch-cleanup-rereview.md:50-70` at both `SKILL.md` sites: read
  `head_sha_verified`, route `matched: true` / `head_sha_verified: false` to a decline, accumulate
  `{declined_bots}`, and interpolate `--declined-bots "{declined_bots}"` into the FIND-step
  `review_completeness check` at `SKILL.md:679`. Update the confirmed-site flag count for the
  participation-guard row in `test_bot_participation_contract.py:_CONFIRMED_SITES` and delete the
  comment recording the omission.
- **Done when:** `grep -rn "matched: true" marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
  shows every arm paired with a `head_sha_verified` read, the FIND-step invocation forwards
  `--declined-bots`, and the flag-count assertion is raised in lock-step.
- **Suggested grouping:** automatic-review / decline accounting

## G7 — Close the empty-merge-candidate-SHA non-idempotence and stop poisoning the ledger with an empty SHA

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:704-708`
  and `:970-974`
- **Evidence:** Driving the extracted `_reviewed_at_merge_candidate` directly with a ledger record
  `('AAA','u1')`, a comment with `updated_at='u2'`, and `merge_candidate_sha=''`:
  `True` on the first evaluation, `False` on the second (after the credit records `('', 'u2')`), and
  `False` thereafter even at a real head `'BBB'`. Two defects: the verdict flips between two
  evaluations at the same unreadable HEAD — the observer effect surviving on one path — and the
  empty-SHA ledger row makes `recorded_sha == merge_candidate_sha` permanently false, so the comment
  stays stale until a further edit. `report-01.md` Finding 2 claims the empty-SHA case "fails closed on
  both fetches", which holds only for the no-record arm;
  `test_unresolvable_head_sha_fails_closed_and_stays_idempotent`
  (`test/plan-marshall/workflow-integration-github/test_github_pr.py:2462`) covers only that arm.
  CONFIRMED.
- **Impact:** One provider hiccup during the fetch that observes a genuine re-review either flips the
  barrier verdict between two runs, or locks the bot into `participated_stale` until it edits again —
  a permanent hard block if the bot re-reviews only on demand.
- **Task:** Guard the fresh-edit arm on a resolvable `merge_candidate_sha` too (so an unreadable head
  fails closed on every arm), and never write a ledger row whose `reviewed_commit_sha` is empty. Extend
  the existing empty-SHA test with a second case: ledger row present + fresh edit + empty head SHA,
  asserting both fetches return the same blocking answer and no empty-SHA row is written.
- **Done when:** The extended test passes and fails against the current code, and
  `_record_currency_records` is never called with an empty SHA.
- **Suggested grouping:** workflow-integration-github / participation currency

## G8 — Handle pre-existing key-only ledger rows instead of failing open once

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:600-624`
- **Evidence:** `_recorded_currency_records` defaults both fields to `''`
  (`str(record.get('reviewed_commit_sha') or '')`, `str(record.get('updated_at') or '')`). Before this
  landing the same artifact held rows carrying only `bot_kind` and `comment_id` (the removed
  `_record_dropped_comment_keys`, visible in `git show 50f67ed2`). Such a row reads as `('', '')`, so
  the SHA arm misses and the predicate falls to `bool(updated_at) and updated_at != ''` — true for
  essentially every real comment, crediting a stale unchanged Guide once before the ledger self-heals.
  No schema-version guard exists. CONFIRMED by reading the reader and the removed writer.
- **Impact:** A plan mid-flight across the upgrade credits participation once against a commit nobody
  reviewed — the plan's own defect class, on the migration path.
- **Task:** Treat a row missing `reviewed_commit_sha` (or carrying an empty one) as an **invalid legacy
  record** that blocks — a state distinct from both "no record" and "a usable record". Dropping such a
  row from the map is NOT a fix: an absent key takes the first-observation arm, which returns
  `bool(merge_candidate_sha)` (`github_pr.py:701-703`) and so credits the bot at any resolvable
  advanced HEAD — the very fail-open path this gap names. Either carry the invalid-record state through
  `_recorded_currency_records` and make the predicate return False for it, or version the artifact and
  migrate the pre-upgrade rows to a real `(sha, updated_at)` before the participation loop evaluates
  them. Add a test seeding a key-only row and asserting the bot resolves to `participated_stale` at an
  advanced HEAD.
- **Done when:** A ledger carrying only pre-upgrade key-only rows resolves the bot to
  `participated_stale` at an advanced resolvable HEAD — not to `participated` — pinned by a test that
  fails against the current reader.
- **Suggested grouping:** workflow-integration-github / participation currency

## G9 — Derive and assert the participation-site population D0 enumerated

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/workflow-integration-github/test_github_pr.py:2313-2333` and
  `test/plan-marshall/automatic-review/test_bot_participation_contract.py:145,860`
- **Evidence:** The plan's D4(d) asks that "the site set D0 enumerated is population-derived,
  non-empty, and every member asserted; copy the derivation pattern from
  `test/_shared/_dispatch_roster.py`". What exists is a registry-derived **bot** population
  (`_UPDATE_REQUIRING_BOTS`), a derived **taxonomy-member** population (`_DERIVED_NON_PARTICIPATION`)
  and a derived **doc-invocation-site** population for two command families
  (`_scan_invocation_sites`). None is the S1–S8 set; S3 (`github_re_review._match_review`), S4
  (`_match_bot_comment`), S7 (the trigger-A consumer) and S8 (the `wait-for-comments` predicate) are
  members of no asserted population. Searched `grep -rn "_dispatch_roster" test/` and
  `grep -rn "site population|participation sites" test/`. CONFIRMED.
- **Impact:** A future site that credits participation or consumes a participation verdict can be added
  without any test noticing — the hand-maintained-list defect class D0's ⛔ named.
- **Task:** Add a derived roster over the participation sites — scan for the participation symbols
  (`_reviewed_at_merge_candidate`, `participation_requires_update`, `head_sha_verified`,
  `stale_participation`, `declined`) across `marketplace/bundles/**` in the
  `test/_shared/_dispatch_roster.py` pattern, guard it non-empty, and assert each discovered site
  against a per-site expectation record naming its anchor and its idempotence.
- **Done when:** Adding a new participation-crediting site without a matching expectation record fails
  a test at import.
- **Suggested grouping:** review-apparatus / test derivation

## G10 — Discharge the plan's cold-read verification obligation

- **Severity:** minor
- **Kind:** omission
- **Where:** `doc/plans/review-apparatus/010-participation-credited-from-a-superseded-commit/plan.md`
  § Verification bullet 4; `report-01.md` § "Verification sub-agent (Step 6)"
- **Evidence:** The plan demands, with a ⭐: "Have the pre-PR verification sub-agent read the changed
  text **cold** — without this plan — and report, in its own words: (a) which commit a credit is
  evaluated against, and (b) whether a `declined` bot blocks, is disclosed, or is ignored. … Report the
  reading verbatim." `report-01.md` records three sub-agent findings and their dispositions but carries
  no verbatim cold reading of either question. CONFIRMED by reading the report section in full.
- **Impact:** The one check designed to catch *wording* failure was not performed, and G3 and G4 are
  exactly the wording failures it would have caught — a contract that calls a heuristic a definition,
  and six sites describing a deleted predicate.
- **Task:** Run the cold read against the current text of `bot-participation-contract.md` §§ "The
  currency rule", "Evidence for a bot that edits one comment in place" and "Detecting a decline", record
  the answers verbatim, and fold any mismatch into G3/G4's rewrite.
- **Done when:** A verbatim cold reading of (a) and (b) is recorded, and matches what D1 and D3
  intended.
- **Suggested grouping:** review-apparatus / plan reporting

## G11 — Rename the currency ledger artifact and its helpers to match what they hold

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:590`
  (`_DROPPED_COMMENT_KEYS_ARTIFACT = 'pr-noise-dropped-comments.jsonl'`), `:593`
  (`_dropped_comment_keys_path`); `bot-participation-contract.md:493-500` ("observation sidecar")
- **Evidence:** The artifact now records `(reviewed_commit_sha, updated_at)` for **every** credited
  `participation_requires_update` comment — including comments that were stored as findings and never
  noise-dropped (`github_pr.py:968-974`, which stages a record on the credited branch regardless of
  what the pre-filters later do). The module's own comment at `:569-574` says exactly that ("a comment
  stored as a finding and a comment dropped as noise … are treated identically"), contradicting the
  constant's name. CONFIRMED.
- **Impact:** A reader chasing the currency test looks for a noise-drop sidecar and misjudges the scope
  of what the ledger governs; a future change may re-add a separate noise-drop record under the same
  name.
- **Task:** Rename the constant and helpers to name the currency ledger
  (`_CURRENCY_LEDGER_ARTIFACT`, `_currency_ledger_path`) and choose a filename that says so, with a
  read-both-names migration or a documented one-way cutover. Update the contract's "observation
  sidecar" paragraphs alongside G4's rewrite.
- **Done when:** No identifier or prose in the participation path calls the currency ledger a
  noise-dropped-comment record.
- **Suggested grouping:** workflow-integration-github / participation currency

## G12 — Derive the complement ordinal in the taxonomy test comment instead of writing it as a literal

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `test/plan-marshall/automatic-review/test_bot_participation_contract.py:138-139`
- **Evidence:** "``STATE_PARTICIPATED`` is the sole intended exclusion: it is the taxonomy's COMPLEMENT
  (the bot delivered a usable review), not a ninth member". `_NON_PARTICIPATION_MEMBERS`
  (`:114-125`) now has **ten** members, so the correct word is "eleventh". The landing changed
  "eighth" → "ninth" correctly at the time and converted the *asserted* counts to derived
  (`_NUMBER_WORDS[taxonomy_size]`, `:581`) but left this prose ordinal a literal that rots on every
  taxonomy growth. Every other count restatement in the tree is currently consistent at ten
  (`automatic-review/SKILL.md:24,700`, `create-pr.md:201`,
  `workflow-pr-doctor/standards/automated-review-lifecycle.md:56`, `review_completeness.py:65,192`),
  confirmed by `grep -rn "seven-member|eight-member|nine-member|ten-member|eleventh|ninth member"`.
- **Impact:** A reader of the module's own guard comment gets the wrong cardinality; the pattern
  guarantees the drift recurs.
- **Task:** Replace the literal ordinal with prose that carries no count (e.g. "not a member of
  `_NON_PARTICIPATION_MEMBERS`"), or interpolate it from `len(_NON_PARTICIPATION_MEMBERS) + 1`.
- **Done when:** No hard-coded ordinal for the taxonomy's cardinality remains in the test module.
- **Suggested grouping:** automatic-review / participation contract

## G13 — Repair the line-wrap artifact left by the taxonomy-count edit

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md:205-207`
- **Evidence:** The blockquote now reads "… whose complement is `participated`. It" / "> is the ONLY
  member that is accounted-for rather than blocking, which is exactly why an intent-echo lands there" —
  a stranded two-word line and an over-long following line, produced by the seven→eight member edit in
  `50f67ed2` and never re-wrapped by the later eight→ten edits. CONFIRMED by reading the current file.
- **Impact:** Cosmetic only; noted because it is the visible trace of an edit made without re-reading
  the surrounding paragraph.
- **Task:** Re-wrap the blockquote paragraph to the file's prevailing width.
- **Done when:** No line in the block is a stranded fragment.
- **Suggested grouping:** phase-6-finalize / documentation hygiene

## G14 — Replace the decline-consumer doc test's bare substring presence with a routing assertion

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py:345-372`
  (`test_rereview_consumer_honors_head_sha_verified_as_a_decline`)
- **Evidence:** The one test guarding the obtain-side wiring of D3 asserts only that four literals
  appear somewhere in two markdown files: `'head_sha_verified' in doc`, `'head_sha_verified: false' in
  doc`, `'declined' in doc`, `'{declined_bots}' in doc` over `branch-cleanup-rereview.md`, and
  `'--declined-bots "{declined_bots}"' in barrier` over `branch-cleanup.md`. It discriminates against
  the pre-fix state, which carried none of those strings, but it cannot tell a document that *routes*
  the bit from one that merely *mentions* it, and it makes no statement about the two `matched`-alone
  consumers G6 names (`automatic-review/SKILL.md:250`, `:729`) — a document could satisfy every
  assertion while crediting a `head_sha_verified: false` outcome as a completed re-review. CONFIRMED by
  reading the test body.
- **Impact:** The only executable guard on the recorded-but-ignored bit is a presence check, so the
  wiring it is supposed to pin can be broken — or left half-done, which is exactly the shipped state
  G6 records — without the test noticing.
- **Task:** Assert the *routing*, not the vocabulary: pin that in `branch-cleanup-rereview.md` the
  `head_sha_verified: false` polarity is the antecedent of the decline branch that accumulates
  `{declined_bots}` (a structural read of the step block, not a whole-file substring), and extend the
  same assertion over the consumer set G6 enumerates so a `matched`-alone arm fails the test.
- **Done when:** Rewriting `branch-cleanup-rereview.md` so it mentions `head_sha_verified` without
  routing the false polarity to `declined` fails this test, and adding a new `matched`-alone consumer
  fails it too.
- **Suggested grouping:** phase-6-finalize / decline accounting
