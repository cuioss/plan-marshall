# Gaps — 110-participation-derived-from-a-lossy-view

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Make an unreadable head SHA an UNKNOWN, not a blocking `participated_stale`

- **Severity:** major
- **Kind:** bug
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:904`
    (`reviewed_commit_sha = _github.fetch_pr_head_sha(pr_number)`)
  - `.../github_pr.py:705`, `:708` (the two arms that both go False on an empty SHA)
  - `.../github_pr.py:1245–1300` (the return dict, which carries no resolution signal)
  - `.../_github_ci.py:55–64` (`fetch_pr_head_sha` — "Returns the SHA on success or an empty string on
    any failure path")
- **Evidence:** With a comment already in the currency ledger at `recorded_sha = A`, and
  `merge_candidate_sha == ''` because the provider read failed, `_reviewed_at_merge_candidate` runs:
  `if merge_candidate_sha and recorded_sha == merge_candidate_sha:` → False (falsy SHA), then
  `return bool(updated_at) and updated_at != recorded_updated_at` → False for an unedited comment.
  The bot lands in `stale_participation`, which `bot-participation-contract.md:64` defines as
  **blocking**. The docstring's idempotence claim — *"a later fetch that likewise cannot read the SHA
  reaches the same (blocking) answer, not a flip"* — is scoped to two consecutive **failed** reads.
  The mixed sequence (successful read credits, failed read revokes) is a flip at an unchanged real
  HEAD, which is exactly what D1's *Done when* forbids. Confirmed by reading `github_pr.py:699–708`
  and `_github_ci.py:55–64`. Confirmed untested by `grep -rn "head_sha=''" test/plan-marshall/` →
  two hits total, the only `test_github_pr.py` one being line 2479 inside
  `test_unresolvable_head_sha_fails_closed_and_stays_idempotent`, which patches `head_sha=''` for
  **both** fetches.
- **Impact:** A transient GitHub API hiccup on one `fetch_findings` call revokes a proven required
  reviewer's credit, blocks the pre-merge barrier, and prescribes the **wrong remedy** — the
  `participated_stale` member's remedy is "re-trigger a re-review", which cannot fix a read failure.
  The caller has no way to tell this apart from a genuine loop-back, because nothing in the
  `fetch_findings` return reports whether the SHA resolved. This is the plan's own "a false `absent`
  and a true `absent` were indistinguishable at the moment of the merge decision", one taxonomy
  member over.
- **Task:** Add a third verdict to the currency path so an unresolvable merge candidate is reported
  as *undecidable* rather than as a failed currency test. Concretely: (a) emit a
  `merge_candidate_sha_resolved: bool` (or `head_sha_status`) field from `cmd_fetch_findings`,
  derived from `bool(reviewed_commit_sha)`; (b) when it is false, do **not** move an
  already-credited bot into `stale_participation` — carry the previous ledger credit forward, or
  route the bot into an explicit undecidable set; (c) document at
  `phase-6-finalize/standards/branch-cleanup.md` § "UNKNOWN — the re-fetch itself failed" that an
  unresolved head SHA is one of the shapes that routes to UNKNOWN, consistent with that section's
  existing positive-validation rule.
- **Done when:** A test in `test/plan-marshall/workflow-integration-github/test_github_pr.py`
  parametrized over `_UPDATE_REQUIRING_BOTS` performs fetch 1 with `head_sha=_HEAD_A` (credited),
  then fetch 2 with `head_sha=''`, and asserts the bot is **not** reported in
  `stale_participation_bots` and that the return carries an explicit unresolved-head signal. The test
  fails against today's code.
- **Suggested grouping:** workflow-integration-github / participation currency

## G2 — Give the cross-iteration filing dedup a content or edit term so an in-place-edited review is re-filed

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:1102`

  ```python
  if (bot_kind or '', comment_id) in existing_comment_keys:
      skipped_duplicate += 1
      continue
  ```
- **Evidence:** This is plan 110's D2 defect statement verbatim — *"the cross-iteration dedup is keyed
  on `(bot_kind, comment_id)` **alone — no content or timestamp term.** A bot that edits **one
  persistent comment in place** never changes its id, so an *updated* review is dropped as a
  duplicate"* — and it is unchanged at HEAD. pr-agent declares `participation_requires_update: true`
  with the comment *"a re-review EDITS that same comment in place"*
  (`automatic-review/standards/pr-agent.md:85`). `report-01.md` § D2 reframes this half as "a
  different question" and records no residue for it.
- **Impact:** When pr-agent re-reviews after a loop-back and its edited Guide now carries a real
  finding, the currency test's fresh-edit arm credits the bot as **participating** while the filing
  dedup drops the comment as a duplicate. The finding never becomes a `pr-comment` record, so it
  never reaches triage and never blocks the pre-merge barrier's pending-findings gate. The reviewer
  reads as present and clean while its actual feedback was discarded — the polarity inverse of the
  false-negative this plan was named for, and counted as `skipped_duplicate`, i.e. *counted but
  mislabelled*, exactly the shape the plan called out.
- **Task:** Widen the dedup key beyond `comment_id`. State the identity explicitly in-source, then
  implement it: the candidate is `(bot_kind, comment_id, updated_at)` — or a body digest where
  `updated_at` is absent — so a re-edited comment presents as new information while an unchanged
  re-fetch still dedupes. Update the in-source rationale block at `github_pr.py:1095–1101` and
  `workflow-integration-github/SKILL.md` § `fetch_findings` to name the new identity. Take care not
  to regress `test_second_fetch_dedupes_all_bot_kinds` (`test_github_pr.py:139`) or
  `test_same_comment_id_distinct_bots_not_collided` (`:209`).
- **Done when:** A test proves that a comment re-fetched with a **moved** `updated_at` and changed
  body is filed as a new `pr-comment` finding (`count_stored == 1`, `count_skipped_duplicate == 0`)
  while the identical unchanged comment still dedupes, and both existing dedup tests still pass.
- **Suggested grouping:** workflow-integration-github / comment identity

## G3 — Stop a drifted refusal wording from being credited as participation

- **Severity:** major
- **Kind:** bug
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py:950`
    (`if _is_refusal_notice(...): continue`) followed by `:953` (the publish-shape credit)
  - `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:183–187`
    (`_is_refusal_notice` — registry substring OR structural shape)
  - `.../_github_pr.py:150–152` (`_is_rate_limit_notice` — requires **both** an exceeded statement
    **and** a notice shape)
- **Evidence:** The plan tabled this as a claim to adjudicate — *"An unmatched refusal notice reaches
  the participation credit in our classifier | HYPOTHESIS — a lead | ⛔ **Read the MATCHER, not the
  contract prose**"* — and `report-01.md` never adjudicates it. Reading the matcher confirms it:
  `_is_refusal_notice` returns True only on a `refusal_patterns` substring hit or on the conjunctive
  structural recogniser. A reworded vendor notice that hits neither falls through to `:953`, where a
  refusal published in a declared shape (`review_body` / `issue_comment`) satisfies the evidence test
  and the bot is written into `participated`. The plan's own Notes name the consequence: *"A pattern
  that no longer matches degrades to a **false credit with no signal**."*
- **Impact:** A rate-limited or otherwise refusing required bot is credited as a proven participant,
  satisfying the quorum on **zero** review coverage — the exact failure the in-source comment at
  `github_pr.py:945–949` says the refusal exclusion exists to prevent, defeated whenever the vendor
  rewords. Nothing counts or reports the event.
- **Task:** Make the failure observable rather than silent. Where a comment resolves to a registered
  bot, is in a declared publish shape, and matches **no** `refusal_patterns` entry but **does** match
  the structural shape (or vice versa), record the divergence — a `refusal_pattern_drift[]` entry on
  the `fetch_findings` return naming the bot and which layer fired alone — so a vendor reword surfaces
  as a registry-maintenance signal instead of a silent credit. `_is_rate_limit_notice`'s own docstring
  already states the intent: *"a refusal recognized here but absent from the registry is a signal that
  the bot's `refusal_patterns` need the observed phrasing added"* — the signal is documented but not
  emitted.
- **Done when:** `fetch_findings` emits a drift record for a body the structural layer recognises but
  the bot's `refusal_patterns` does not, a test pins it, and the field is documented in
  `workflow-integration-github/SKILL.md` § `fetch_findings` output.
- **Suggested grouping:** automatic-review / refusal detection

## G4 — Correct the six prose sites that still state the retired pre-#1141 currency predicate

- **Severity:** major
- **Kind:** stale-doc
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:233`
    — "it was **edited in place** (`updated_at` differs from `created_at`) since it was posted"
  - `.../bot-participation-contract.md:491` and `:496` — "the SHA … is normally read from the
    `reviewed_commit_sha` stamped on the `pr-comment` finding" … "evaluates the currency rule against
    the **union** of the stored-finding SHAs and the recorded sidecar SHAs"
  - `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md:129` — "the comment
    is first-present or its `updated_at` has moved"
  - `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:652` — "only on first presence
    or observed `updated_at` movement"
  - `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md:86` and `:363–364`
    — "Evidence therefore requires first presence OR updated_at movement."
  - `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py:486–487`
    (docstring) — "evidence requires either first presence … or observed `updated_at` movement"
- **Evidence:** The production code states the opposite of two of these in its own comments.
  `github_pr.py:576–582`: *"Anchoring on the SHA alone leaves the edit-movement arm a permanent 'was
  ever edited' flag: once a comment is edited at some commit, `updated_at != created_at` stays true
  forever … Comparing `updated_at` against the value recorded at the LAST credit instead … closes that
  hole."* And `github_pr.py:909–911`: the currency ledger *"is the SOLE currency source, so a comment
  stored as a finding and a comment dropped as noise are treated identically"* — there is no union
  with stored-finding SHAs. `test_edit_at_one_commit_does_not_credit_a_later_commit`
  (`test_github_pr.py:2360`) pins the corrected behaviour. The four `first presence / updated_at
  movement` sites omit the SHA-currency arm entirely, which is the arm #1141 exists for. Search that
  produced the population: `grep -rn "first presence\|first-present\|updated_at movement\|updated_at\`
  has moved\|updated_at != created_at" marketplace/bundles/`.
- **Impact:** This plan's central thesis is that a rule enforced by prose is not enforced. An agent or
  reviewer consulting any of these six sites will apply the **pre-fix** rule — the "was ever edited"
  flag that #1141 closed as a false positive, and a non-existent union that suggests the stored
  findings are a currency source. `bot_registry.py:486` is a docstring inside production code, so the
  stale statement ships with the module.
- **Task:** Rewrite each site to state the live three-arm predicate — SHA currency (recorded
  `reviewed_commit_sha` equals the merge candidate), first observation (guarded on a resolvable head
  SHA), fresh edit (`updated_at` moved past the **recorded** `updated_at`, not past `created_at`) —
  and delete the union claim at `bot-participation-contract.md:491–496`, replacing it with the
  single-ledger statement the code makes. Keep the contract as the single normative source and have
  the SKILL.md sites cross-reference it rather than restate it, per the repository's no-duplication
  standard.
- **Done when:** `grep -rn "updated_at.*differs from.*created_at\|first presence OR updated_at\|first
  presence or observed \`updated_at\` movement\|union\*\* of the stored-finding SHAs"
  marketplace/bundles/` returns zero hits, and each rewritten site names all three arms.
- **Suggested grouping:** automatic-review / bot-participation contract

## G5 — Make the refusal fixture sweep every declared wording and fail rather than fall back on an empty pattern set

- **Severity:** major
- **Kind:** missing-test
- **Where:**
  - `test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming.py:62–74`
    (`_refusal_body`)
  - `.../test_refusal_recovery_arming.py:99` (`test_every_registered_bots_refusal_is_detected`)
  - `.../test_refusal_recovery_arming.py:234–249`
    (`test_a_bots_declared_refusal_is_recognized_as_DATA`, whose `pytest.skip` is at `:242–243`)
- **Evidence:** The plan's D3 ⭐: *"assert that each registered bot's known refusal **wordings**
  classify as refusals. ⛔ Not a hand-list — the fixture must publish the **population size it ranged
  over**; a check that can pass over an empty pattern set is the vacuous-guard archetype again."*
  `_refusal_body` returns `f'…{declared[0]}…'` — the **first** wording only — and its docstring states
  the fallback openly: *"Falls back to a structurally-shaped notice for a bot that declares no refusal
  phrasing."* So pr-agent (`refusal_patterns:` EMPTY, `pr-agent.md:128`) passes
  `test_every_registered_bots_refusal_is_detected` by exercising the structural recogniser, not any
  declared wording; and sourcery's second pattern (`"reached your weekly rate limit of"`,
  `sourcery.md:44` — the wording PR #1219's own run observed live) is never swept.
  `report-01.md` records the refusal-pattern population as 3 but no test publishes or asserts it.
- **Impact:** The registered refusal-pattern list is, in the plan's words, *"unverifiable prose"* that
  *"drifts silently whenever a vendor rewords its notice"*. The fixture that was supposed to make it
  verifiable ranges over the wrong population, so a wording that stops matching produces a green
  suite. This is the direct test-side counterpart to G3.
- **Task:** Parametrize the detection sweep over `(bot_kind, pattern)` pairs derived from
  `bot_registry.refusal_patterns(bot)` for every `bot_registry.bot_kinds()` member, asserting each
  declared wording is detected by the registry layer. Guard the pair population non-empty and publish
  its size (a module-level constant asserted in a dedicated `test_..._population_is_not_vacuous`, in
  the style of `test_at_least_one_registered_bot_requires_update_movement`,
  `test_github_pr.py:2322`). Keep the structural-fallback case as its own explicitly-named test rather
  than as a silent fallback inside `_refusal_body`, so a bot with no declared wording is visibly
  uncovered instead of appearing covered.
- **Done when:** The declared-wording sweep parametrizes over 3 pairs today, a vacuity guard asserts
  the pair population is non-empty and publishes its size, and removing any single `refusal_patterns`
  entry from a registry doc makes a named case fail.
- **Suggested grouping:** automatic-review / refusal detection

## G6 — Record per-bot trigger semantics (`auto_on_push` vs `requires_explicit_trigger`) in the registry

- **Severity:** minor
- **Kind:** omission
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{coderabbit,pr-agent,sourcery}.md`
    (the YAML registry blocks)
  - `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
    (no accessor exists)
- **Evidence:** Plan D1 ⭐: *"record per-bot trigger semantics explicitly (`auto_on_push` versus
  `requires_explicit_trigger`, with the trigger command for the latter). ⭐ **For a bot needing an
  explicit trigger, POST the trigger** rather than waiting for a spontaneous pass that cannot come."*
  `report-01.md` § D1 answers: *"Per-bot trigger semantics are already registry data
  (`participation_requires_update`, `trigger_comment`, `rate_limit_class`)."* Search:
  `grep -rn "auto_on_push\|requires_explicit_trigger" marketplace/ test/ doc/` → **zero hits** outside
  this plan's own text. None of the three named fields encodes the distinction:
  `participation_requires_update` describes how a review is *published*, `rate_limit_class` describes
  *awaitability*, and `trigger_comment` is non-empty for all three registered bots so it discriminates
  nothing.
- **Impact:** Nothing in code or data distinguishes a bot that reviews automatically on push from one
  that only reviews when asked. A wait or barrier that assumes the former for a bot of the latter kind
  polls for a signal that cannot arrive — the plan's third proxy row. The re-review path
  (`github_re_review.py:176`) posts the trigger for *every* bot uniformly, which is a workaround
  rather than the recorded semantics.
- **Task:** Add a `trigger_semantics` key (values `auto_on_push` / `requires_explicit_trigger`) to
  each `automatic-review/standards/{bot_kind}.md` YAML block with the observation that grounds it, add
  a `bot_registry.trigger_semantics(bot_kind)` accessor fail-closed to `requires_explicit_trigger`,
  and document the field in `bot-participation-contract.md` § the registry-field table (`:658–665`).
  Then have the await/trigger path branch on it instead of triggering uniformly.
- **Done when:** Every registered bot declares `trigger_semantics`, a registry-derived test asserts
  every bot declares a value in the closed set, and `bot-participation-contract.md` lists the field
  among the registry keys its consumers read.
- **Suggested grouping:** automatic-review / bot registry

## G7 — Correct the report's residue section to record the open items

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/110-participation-derived-from-a-lossy-view/report-01.md`
  § Residue — *"**None blocking.** … No follow-up owed."*
- **Evidence:** G1, G2 and G3 are live defects in the exact surface the plan declares as its expected
  surface (`github_pr.py` `fetch_findings`, its participation derivation, and the cross-iteration
  dedup). G2 is the plan's own D2 defect statement, unchanged. G5 and G6 are ⭐ obligations the report
  marks satisfied that the tree does not satisfy. `git log --oneline --follow --
  .../github_pr.py` shows no later commit touching the currency or dedup paths (the most recent,
  `9e9e9880` / #1241, changed the size-cap path).
- **Impact:** A downstream reader — the epic's retrospective, a follow-up planner, or an operator
  triaging this surface — concludes the area is closed and does not schedule the remaining work. The
  epic's own theme is signals that read clean while carrying loss; a residue section reading "none"
  over five open items is an instance of it.
- **Task:** Append a "Residue reopened by ground-truth verification" note to `report-01.md` (or leave
  `report-01.md` as the historical record and rely on this `gaps.md`, per whichever convention the
  epic settles) that names G1–G6 and cross-references `verification.md`.
- **Done when:** The plan directory carries an unambiguous statement that follow-up is owed, naming
  the items, so no reader of the plan directory alone concludes otherwise.
- **Suggested grouping:** review-apparatus / plan hygiene

## G8 — Cite the test that actually derives the consumer population

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `report-01.md` § D3(d) — *"consumer population + refusal fixture — ALREADY COVERED.
  Consumer/currency population: `test_at_least_one_registered_bot_requires_update_movement`,
  `test_currency_anchor_is_recorded_in_the_ledger_on_credit`, and the `_registered_bots()`-derived
  taxonomy sweep."*
- **Evidence:** All three named tests exist, but each derives the **bot** population, not the consumer
  population: `test_at_least_one_registered_bot_requires_update_movement`
  (`test_github_pr.py:2322`) asserts `_UPDATE_REQUIRING_BOTS` is non-empty;
  `test_currency_anchor_is_recorded_in_the_ledger_on_credit` (`:2335`) reads the ledger for one bot;
  the taxonomy sweep (`test_bot_participation_contract.py:600–680`) parametrizes over observations ×
  bots. The test that *does* derive the consumer population is
  `TestCallSitePopulation` (`test_bot_participation_contract.py:829–960`), which scans
  `marketplace/bundles/**/*.md` via `_scan_invocation_sites()` for both invocation families with a
  per-family vacuity guard (`test_each_family_is_a_non_empty_sub_population`) and pins the four
  confirmed sites. `report-01.md` never mentions it.
- **Impact:** The plan's D3(d) is in fact substantially covered, but by a mechanism the report does not
  name — so a later reader auditing the claim against the cited tests concludes it is unsupported, and
  a maintainer weakening `TestCallSitePopulation` would not know it is load-bearing for this plan.
- **Task:** Record in `verification.md` (done) and, if `report-01.md` is amended for G7, correct the
  D3(d) citation to name `TestCallSitePopulation`. Additionally, extend that sweep's per-site
  assertions to record each site's **class** (reads the scan / the ledger / a deduped projection),
  which is what D0 asked for and what no test currently pins.
- **Done when:** The consumer-population claim is backed by a named test that both derives the site
  population and asserts each member's class, and the citation in the plan directory points at it.
- **Suggested grouping:** automatic-review / bot-participation contract

## G9 — Derive the added regression test's bot list from the registry

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `test/plan-marshall/workflow-integration-github/test_github_pr.py:195`
  — `assert first_bots == ['coderabbit', 'pr-agent', 'sourcery']`
- **Evidence:** The surrounding currency suite in the same file derives its populations from the
  registry — `_UPDATE_REQUIRING_BOTS` (`:2316`), `_BOT_KIND_TO_LOGIN` (`:2320`), and
  `_publish_comment` reading `participation_evidence(bot_kind)[0]` (`:2408`) — precisely so "a bot
  added or reclassified in a standards doc is swept here automatically". The test added by this plan
  hard-codes the three bot kinds and depends on the module-level `_COMMENTS` fixture, which also
  hard-codes three author logins.
- **Impact:** Low. A registry change breaks the assertion loudly rather than silently, so this is a
  maintenance cost rather than a coverage hole — but it is inconsistent with the convention the plan's
  own D3(d) demanded ("Not a hand-list") and with the file's stated derivation discipline.
- **Task:** Derive the expected participant list from `bot_registry.bot_kinds()` intersected with the
  bots represented in `_COMMENTS` (or build `_COMMENTS` itself from the registry, as `_publish_comment`
  does), so the assertion states the property rather than the current roster.
- **Done when:** `test_a_deduped_comment_is_still_credited_as_participating` contains no bot-name
  literal, and still fails when participation is re-coupled to `existing_comment_keys`.
- **Suggested grouping:** workflow-integration-github / test conventions
