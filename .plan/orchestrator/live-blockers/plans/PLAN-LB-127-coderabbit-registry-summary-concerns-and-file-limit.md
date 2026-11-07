# PLAN-LB-127: CodeRabbit concerns raised only in its summary are filed, the file-limit notice is recognised, and the dormant cuioss-review-bot is removed

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-127-coderabbit-registry-summary-concerns-and-file-limit.md` and is queued as one row file, `queue/PLAN-LB-127.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's ruling of 2026-11-07 (ruling 23, option 1): parked PLAN-LB-46 is SPLIT. Its D1 and D2 become this plan, and
> its D3 to D6 stay parked. Its D7 (`cuioss-review-bot` removal) was first to be its own plan; on the operator's word of the same day
> ("preferably add it to an existing") it is D4 of this plan, because it edits the same bot registry and participation files. It is
> the last deliverable and the first to split off. The plan was re-grounded at HEAD
> `5cd8ccd92`, after PLAN-LB-106 and PLAN-LB-119 changed the participation rules. A claim that was re-read at its lines is labelled
> OBSERVED. Every claim about what CodeRabbit actually posts is a HYPOTHESIS and is settled first.
>
> Ruling check. Both defects can make a gate wrong in normal use. In D1 a dropped concern lets a review step pass with nothing
> filed, so the gate fails open. In D2 the notice is never read as a refusal, so the required bot neither escalates nor
> participates and the gate wrongly holds. Stop rule: a fix plan is staged only for a major that fails open or wrongly blocks a
> gate in normal use. D1 ships only if the verify-first clause reproduces its case. No token or measurement work. No Sonar.

## Objective

The producer drops every CodeRabbit comment that carries the summary marker or `## Walkthrough`, because both are unconditional
`ignore_patterns`. A concern that CodeRabbit raises only in its summary is therefore never filed, and the bot resolves
`participated_but_empty`. CodeRabbit's "files exceed the limit" notice matches no registered refusal and no structural arm. It is
then either filed as a finding or dropped as noise, and in neither case does it reach `refused_structural`.

After this plan, a summary that carries a concern files a finding while a summary without one still files nothing, and the
file-limit notice is a size refusal with its cap read from the notice. The contract states both rules once. The `cuioss-review-bot`
is dormant and the operator ordered it removed completely (2026-10-23): CodeRabbit is the one required bot and Sourcery the optional
one. After D4 no tracked file outside the ledger names the bot, its generator target, its standard and its publish workflow are gone,
and a consumer whose configuration still lists it is migrated rather than refused.

## Deliverables

1. **A summary-only concern is filed.**
   - The verify-first clause (Claim Labels) settles the live shape before any edit. If that shape cannot be reproduced, this
     deliverable is closed as not reproducible, the PR says so, and only D2 and D3 ship.
   - The fix is data-first. The summary marker and `## Walkthrough` stop being unconditional drops. They become a conditional drop,
     the existing `contentless_review_markers` / `contentless_review_headings` layer, which an `actionable_content_markers` veto
     overrides. The veto names the concern sections the reproduced body carries. The outline decides the exact field split and
     records it. No new mechanism and no second section parser are added.
   - Each other `ignore_patterns` entry the live summary carries is checked too (tips block, marketing line). A summary with a
     concern must not be dropped by a different unconditional marker.
   - Shapes recorded with fixtures: a finished summary that keeps a "Review limit reached" block. The filing loop treats it as a
     refusal (`github_pr.py:2364`) and does not read `review_coverage_is_finished` the way the participation loop does (`:2108`).
     If the reproduction shows a concern lost through this path, closing it is in scope. Otherwise its current behaviour is pinned
     and stated.

   *Done when:*
   - A summary body whose only content beyond the boilerplate is an actionable concern files one `pr-comment` finding (red at HEAD).
   - Each of these still files nothing and keeps `count_skipped_noise` as it is: the plain walkthrough, both in-progress summaries
     in `_github_pr_fixtures.py`, a clean-review verdict ("No actionable comments were generated"), and the skip-notice summary.
   - Each fixture names where its wording came from (observed / constructed / reconstructed).

2. **The file-limit notice is a structural refusal.**
   - The notice's detection literal goes into `refusal_patterns` and `refusal_size_patterns`. Its cap regex goes into
     `refusal_size_cap_patterns`. The model is `sourcery.md`, which declares two size refusals and a cap regex for each.
     `refusal_cause` then returns `size`, and `refused_structural` follows from the contract with no code change.
   - The wording comes from a live notice (see the clause below), never from memory. If the exact string cannot be read, the
     literal stays a named HYPOTHESIS recorded in `coderabbit.md`'s provenance prose, for confirmation against a live notice. The
     fixture then uses the documented shape: `Review skipped`, `files exceed the limit of N`.
   - "Too many files!" and `over the limit of` stay unless the live notice shows they are wrong.

   *Done when:*
   - A fixture comment with the notice is counted in `count_skipped_refusal`, names `coderabbit` in `refused_bots[]` with
     `cause: size` and `cap: 100`, and files no finding (red at HEAD).
   - The control "Too many files! … over the limit of 100" still yields `size` and `100`.
   - The control "Review limit reached" still yields `quota`.

3. **The documents and the guards state the new rules.**
   - `bot-participation-contract.md` § "The four per-bot marker lists" states the CodeRabbit summary rule. That text is at
     `:1089`, which currently calls `ignore_patterns` a drop "whatever else the body carries".
   - `coderabbit.md` § "Producer stage" (`:130-134`) and the refusal prose (`:142-161`) state the new rule and the new refusal once.
   - `findings-pipeline.md:129`, which names only `comment-patterns.json` as the pre-filter, points to the contract.
   - The participation-site population guard is run. If D1 adds a call to a seed symbol (`review_coverage_is_finished` is one) at a
     new site, the site's expectation record is added in the `_records` and `_resolution` copies, as PLAN-LB-119 did for its
     placement site.

   *Done when:* each cited line reads the new rule. The guard suite passes. A seed-symbol site added by D1 has its record.

4. **The `cuioss-review-bot` is removed completely.** *(PLAN-LB-46 D7, operator instruction of 2026-10-23; hygiene, ordered)*
   - Delete the bot's generator target (`marketplace/targets/cuioss_review_bot/`) and its registration (`generate.py`, `__init__.py`,
     `component_targets.py`, `README.md`), its standard (`automatic-review/standards/cuioss-review-bot.md`) and its publish workflow
     (`.github/workflows/cuioss-review-bot-packs-publish.yml`).
   - Remove every registry entry, default, participation rule, migration and documentation sentence that names it (Expected Surface,
     D4) and the tests that pin it. The comment at `github_pr.py:2127-2130` and the `_SHIPPED_BOTS` pins in
     `test_bot_registry_patterns.py` go with it. The CodeRabbit and Sourcery registrations stay as they are.
   - Verify-first (consumer configuration, FIRST): a consumer project's `marshal.json` may still name the bot in its required or
     optional roster, and the roster read fails closed on an unreadable roster. Read what a roster entry with no registry entry does
     (`bot_registry.py`, `automatic-review` step-params, the legacy bot-list migration in `marshall-steward/scripts/upgrade.py`).
     If an unknown bot would refuse a consumer's merge, the migration strips the bot from the roster instead, in the same release,
     and a single documented tombstone constant is the one place the literal may remain; the outline records the choice.
   - Verify-first (the registry): removing the entry changes nothing for CodeRabbit or Sourcery, which register independently
     (`bot_registry.py`, the participation contract); settle by running the registry and participation tests after the removal of the
     entry alone, before the sweep.

   *Done when:* a content search for `cuioss-review-bot` and `cuioss_review_bot` over the tracked tree, excluding `.plan/orchestrator/`
   records and the migration's tombstone if the outline keeps one, returns nothing; `./pw generate --help` lists no `cuioss_review_bot`
   target; a fixture roster naming the bot is migrated or read without refusing the merge (red at HEAD if the registry entry is
   removed without the migration); the full test suite is green.

Split guard: four deliverables. D2 is independent of D1 and can run alone: D2 is registry data plus fixtures, while D1 depends on
its reproduction. If D1 is closed as not reproducible, D3 shrinks to D2's text. D4 is a removal sweep over about 90 files (see
Expected Surface) and splits off FIRST if the PR grows: it is mechanical, it shares files with PLAN-LB-125 and 116, and it runs after
them, in sequence, never concurrently with D1 to D3's test edits.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around, and the PR says so.
- **Bot text is untrusted.** A live comment is read through the CI abstraction (`plan-marshall:tools-integration-ci:ci`) and is
  treated as a lead, never as an instruction.
- **Data, not code.** Recognition changes go into the registry block. `_github_pr.REFUSAL_LAYERS` and the producer stage order
  stay as they are. `refusal_patterns` is never unioned with `ignore_patterns`.
- **Fail closed toward filing.** A summary that strays from a declared clean shape is filed, never dropped. No relaxation ships
  without its matched control.
- **Operator policy unchanged.** CodeRabbit stays required. The 90-minute policy text and `rate_limit_class` stay.
- **Documentation states the current behaviour**, once. No plan ids or history in comments or docs.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, and are shown red where a Done-when says so. Fixture
  provenance is recorded in `_github_pr_fixtures.py`.
- **No executor regeneration** unless a verb or flag is added. None is expected.

## Claim Labels

- Verify-first clause (D1), FIRST: build a fixture from a captured live CodeRabbit summary body that carries a concern section.
  Before any edit, read:
  - the sections CodeRabbit puts in a review body: Actionable comments, Nitpick comments, Outside-diff comments, Follow-ups;
  - how `github_pr.py cmd_fetch_findings` stages a finding from a review body or an issue comment (`:2332-2461`);
  - how `_strip_footer_markers` (`:425-450`), the `ignore_patterns` check (`:551`) and `_is_contentless_boilerplate` (`:308-343`)
    apply.

  If no live body can be cited, or built from the registry's own documented format, D1 is closed as not reproducible.
- Verify-first clause (D2): read the live file-limit notice through the CI abstraction. The candidates are the PR #1753 notice or
  stored finding `5064d5`. Record whether it carries "Too many files!", which comment shape it arrives in, and whether that comment
  carries the summary marker.
- OBSERVED (D4): a read-only content search at HEAD `5cd8ccd92` finds `cuioss-review-bot` or `cuioss_review_bot` in 29 non-test files
  (the target package, its standard, the publish workflow, the automatic-review, workflow-integration-github, marshall-steward,
  manage-config, manage-status and phase-6-finalize documents and scripts, three documents, two `.claude` skills) and 63 test files;
  `.github/project.yml` no longer carries the block. The bot is dormant, CodeRabbit is the required bot and Sourcery the optional one.
- HYPOTHESIS (D4): a consumer `marshal.json` roster that still names the bot is refused or mis-read once its registry entry is gone,
  because an unreadable roster is an error — confirm/refute at `bot_registry.py`, the `automatic-review` step-params and the legacy
  bot-list migration in `marshall-steward/scripts/upgrade.py` (verify-at-outline). It decides whether D4 needs the migration.
- HYPOTHESIS (D4): removing the entry changes no behaviour for CodeRabbit or Sourcery — confirm at `bot_registry.py` and the
  participation contract (verify-at-outline).
- Verify-first clause (D4): the two hypotheses above are settled before the sweep, and the full registry and participation test set is
  run after the entry alone is removed.
- OBSERVED: `ignore_patterns` lists the summary marker (`coderabbit.md:63`) and `## Walkthrough` (`:64`). The producer-stage prose
  calls them whole-comment drops "that carry no per-line finding" (`:130-134`). CodeRabbit declares no contentless or actionable
  markers (`:21-24`).
- OBSERVED: `_is_obvious_noise` strips footers, then drops on any `ignore_patterns` substring, then tests contentless boilerplate
  (`github_pr.py:540-553`). The noise filter is pre-filter 4 (`:2459-2461`), which runs after the refusal branch (`:2364-2420`).
- OBSERVED: a bot whose every comment was filtered as noise resolves `participated_but_empty`, "Accounted-for, not a failure"
  (`bot-participation-contract.md:89`, `:1103-1109`).
- OBSERVED: the contentless layer drops a comment only when every required marker is present, a declared heading is present and no
  actionable marker is present. An empty marker list never fires (`github_pr.py:308-343`; contract `:1092`).
- OBSERVED: both in-progress summary fixtures carry the summary marker. Only one carries `## Walkthrough`
  (`_github_pr_fixtures.py:370-395`). A control set keyed on the walkthrough heading alone would file the other one.
- OBSERVED: PLAN-LB-119 made a readable coverage marker outrank the refusal skip in the participation loop only
  (`github_pr.py:2099-2109`). The filing loop's refusal branch still reads `_is_refusal_notice` alone (`:2364`). PLAN-LB-119 also
  made the footer strip a terminal block (`:425-450`; contract `:1090`).
- HYPOTHESIS: the concerns on pm-mcp-core PR #43 sit in the comment carrying the summary marker, not in a `review_body` without it.
  Confirm/refute against that comment (verify-at-outline). It decides D1.
- HYPOTHESIS: the counting rule excludes a `review_body` that opens with "Actionable comments posted:" from finding counts even
  when concern sections follow. Confirm/refute at `bot-participation-contract.md` § "The counting rule" and
  `bot_registry.py:48-49` (verify-at-outline). If confirmed, it is recorded, and changed here only if D1's reproduction shows the
  concern lost there.
- OBSERVED: `refusal_patterns` hold five literals (`coderabbit.md:75-80`). `refusal_size_patterns` holds only "Too many files!"
  (`:84-85`). The cap regex is `over the limit of ([0-9][0-9,]*)` (`:86-87`). `test_bot_registry_patterns.py:155-156` pins the size
  list by exact equality.
- OBSERVED: the structural arm needs a past-tense "exceeded / reached / hit" statement (`_github_pr.py:104-120`), so "files exceed
  the limit of 100" is invisible to it. The enumerative arm is inert while `UNRECOGNISED_REFUSAL_MAX_CHARS` is `None`
  (`_github_pr.py:621`, `:691-693`).
- OBSERVED: `refusal_cause` returns `size` only on a declared size pattern (`_github_pr.py:757-759`). `refusal_size_cap` reads the
  declared regexes and leaves an unknown cap empty (`:824-865`). A size cause resolves `refused_structural`, which never waits
  (contract `:88`). With `review_rate_window_await` on by default, a size refusal escalates immediately with `refusal_structural`
  (`automatic-review/SKILL.md:46-48`).
- HYPOTHESIS: the live notice reads "Review skipped: 198 files exceed the limit of 100" and does not contain "Too many files!". This
  wording is quoted by PLAN-LB-46 D2 from PR #1753 and was not re-read (verify-at-outline). If the notice does carry "Too many
  files!", D2 reduces to the cap regex.
- HYPOTHESIS: the unrecognised notice is filed as a finding when it arrives on its own, and dropped as noise when it rides the
  summary comment. In the second case CodeRabbit has no evidence and resolves `absent` (verify-at-outline, by the D2 clause).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — `ignore_patterns`, contentless/actionable fields, refusal and cap patterns, producer prose (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` — the marker-list table (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/findings-pipeline.md` — the producer pre-filter row (D3)
- OBSERVED: `test/plan-marshall/workflow-integration-github/_github_pr_fixtures.py` — summary and notice fixtures with provenance (D1, D2)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_filters.py` — summary concern and controls (D1)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_refusals.py` — the file-limit refusal (D2)
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_registry_patterns.py` — the size-list pin, the new fields (D1, D2)
- OBSERVED: `test/plan-marshall/automatic-review/test_participation_site_population_guards.py` — run, edited only if D1 adds a seed-symbol site (D3)
- HYPOTHESIS: `test/plan-marshall/automatic-review/test_participation_site_population_records.py` — only if D1 adds a seed-symbol site (D3; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/automatic-review/test_participation_site_population_resolution.py` — only if D1 adds a seed-symbol site (D3; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — only if the retained-limit-block shape needs the filing loop changed, or the noise layer needs code (D1; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — expected untouched; only if the live notice cannot be expressed as registry data (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — only if a field needs an accessor or a load-time check (D1, D2, D4; verify-at-outline)
- OBSERVED: `marketplace/targets/cuioss_review_bot/target.py` — deleted (D4; the whole package directory is deleted, including any file of it that does not name the bot)
- OBSERVED: `marketplace/targets/cuioss_review_bot/__init__.py` — deleted (D4)
- OBSERVED: `marketplace/targets/__init__.py` — the registration (D4)
- OBSERVED: `marketplace/targets/generate.py` — the registration (D4)
- OBSERVED: `marketplace/targets/component_targets.py` — the registration (D4)
- OBSERVED: `marketplace/targets/README.md` — the target list (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` — deleted (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — the roster and bot sentences (D4)
- OBSERVED: `.github/workflows/cuioss-review-bot-packs-publish.yml` — deleted (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — bot sentences (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` — bot references (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — bot references (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` — the legacy bot-list migration (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md` — bot sentences (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/landing-cycle.md` — bot sentences (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` — the default roster (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` — the roster text (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — bot references (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — bot sentences (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/code-review.md` — bot sentences (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — bot sentences (D4)
- OBSERVED: `doc/developer/marketplace-build.adoc` — the target description (D4)
- OBSERVED: `doc/analysis/in-house-reviewer-efficacy.md` — the analysis (D4; the outline decides delete or keep as a record without the live reference)
- OBSERVED: `doc/analyzis-cloud-plan/review-apparatus.adoc` — bot sentences (D4)
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/SKILL.md` — bot sentences (D4)
- OBSERVED: `.claude/skills/cloud-plan-lane/SKILL.md` — bot sentences (D4)
- OBSERVED: `test/conftest.py` — bot pins (D4)
- OBSERVED: `test/default/test_workflow_lint.py` — bot pins (D4)
- OBSERVED: `test/pm-dev-java/doc-contracts/test_domain_content_rules.py` — bot pins (D4)
- OBSERVED: `test/pm-plugin-development/plugin-doctor/test_analyze_target_scope.py` — bot pins (D4)
- OBSERVED: `test/marketplace/targets/test_generate_cli.py` — the target list (D4)
- OBSERVED: `test/marketplace/targets/test_component_targets.py` — the target list (D4)
- OBSERVED: `test/marketplace/targets/cuioss_review_bot/test_charter_invariants.py` — deleted (D4)
- OBSERVED: `test/marketplace/targets/cuioss_review_bot/test_cuioss_review_bot_target.py` — deleted (D4)
- OBSERVED: `test/marketplace/targets/cuioss_review_bot/test_code_review_packs.py` — deleted (D4)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/manage-findings/test_manage_findings_finding.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/manage-findings/test_findings_store_query_findings.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/manage-status/test_merge_authorization_grant_record.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/manage-status/_merge_authorization_fixtures.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/marshall-steward/test_legacy_bot_list_migration.py` — the migration (D4)
- OBSERVED: `test/plan-marshall/marshall-steward/test_upgrade.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier_override.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier_members.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pr_agent_contentless_guide_interaction_guide.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pr_agent_contentless_guide_interaction_core.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pr_agent_contentless_code_review_guide.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_sizes.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_refusals.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_currency.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_bot_completion.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_dedupe.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_fetch_findings.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_ops_pr_comments.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_ops_errors.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_ops_ci.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_post.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_pr.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_fetch.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_re_review_strategy_cli.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_re_review_strategy_resolve.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_re_review_strategy_await.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_re_review_strategy_fresh_review.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_re_review_strategy_match.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pr_wait_for_comments_rate_limited_core.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pr_wait_for_comments_rate_limited_rate.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_registry_parsing.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_registry_kinds.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_registry_markers.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_registry_evidence.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_participation_contract_resolution.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_verdicts.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_state.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_cli.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_evidence.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_overlays.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_currency_holes_regression.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_gate_delta_cli.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_gate_delta_shares.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_gate_delta_exclusions.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_gate_delta_escapes.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_lb55_grant_and_review_policy.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_structural_refusal_diff.py` — bot pins (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_roster_read_failclosed.py` — bot pins (D4)

## Dependencies and Sequencing

- **Depends on:** none. PLAN-LB-106 and PLAN-LB-119 (`f84eb0e36`) are merged. This spec's line references are taken at
  `5cd8ccd92`.
- **Overlaps with staged PLAN-LB-116** (runbook-lane review gate). Its D1 parses review-body sections (Follow-ups, Nitpick,
  Outside-diff). Its HYPOTHESIS reads the format "documented in `automatic-review/standards/{bot}.md`", and its HYPOTHESIS surface
  entry is `_github_pr.py` (LB-116 spec lines 38-41, 163-165, 203). The section vocabulary this plan writes into `coderabbit.md` is
  the input for LB-116's parser. Keep one vocabulary: run this plan first, or have LB-116 read the registry rather than restate it.
  Sequence on any shared file.
- **Overlaps with PLAN-LB-125** (review gate fix plan). Its surface is in its own spec. Treat `github_pr.py` and
  `_github_pr.py` as a possible collision, and let the disjointness gate decide at emit from both specs' explicit files.
- **Parked PLAN-LB-46 remainder.** Its D3 rests on `review_rate_window_await` defaulting to false. At HEAD it defaults to true and a
  size refusal escalates immediately (`automatic-review/SKILL.md:46-48`), so D3 is likely closed. Re-ground it before it is
  un-parked. Its D4 to D6 touch `github_pr.py`, `review_completeness.py` and the Sourcery registry, so re-ground them against this
  plan's line moves.
- **D4 (the bot removal, PLAN-LB-46 D7) widens this plan's surface to about 90 files**, so the disjointness gate now reads this plan
  as overlapping every plan that edits the GitHub integration or the automatic-review tests. Real overlaps by the spec files: PLAN-LB-125
  (`github_ops.py`, `github_re_review.py`, `test_comments_stage_fetch.py`, `test_github_ops_pr_comments.py`,
  `test_github_pr_currency.py`, `_github_pr.py`) and PLAN-LB-116 (`test_runbook_lane.py`), and PLAN-LB-124 on `branch-cleanup.md`.
  Sequence: PLAN-LB-125, 116 and 124 first, then D4 (or this plan split so D4 runs last). It edits
  `test_bot_registry_patterns.py` (`_SHIPPED_BOTS`, `:42`, `:95`, `:109`) and the comment at `github_pr.py:2127-2130`, which D1 to D3 also
  touch, so D4 never runs concurrently with D1 to D3.
- **Parked PLAN-LB-41** D1 and D5 become moot with D4 (they describe the bot's code-review packs and comment shape); retire them when
  D4 merges. **Parked PLAN-LB-57** is retired already.
- **Adjacent to** (left untouched): the refusal-recovery branches in `automatic-review/SKILL.md`, `review_completeness.py`'s state
  mapping, the enumerative-arm threshold, and `sourcery.md`.
- **Owed outside this plan, operator-run:** a harness sync after merge. No executor regeneration.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-127-coderabbit-registry-summary-concerns-and-file-limit.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
