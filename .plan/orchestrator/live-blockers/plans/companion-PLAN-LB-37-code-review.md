# PLAN-LB-37, part 2: the code review — is the implementation sound by best practice and this project's conventions

epic: live-blockers
workstream: WS-01

> Companion document of `PLAN-LB-37-functional-review.md`. The two documents are ONE plan: one
> outline, one branch, one landing, one consumer rollout. The main document carries the hand-off
> command, the migration and the rollout; this one carries the code-review deliverables, numbered on
> from the main document's (D10–D16). Staged with the main document; the hand-off command is in the main document only.

## Objective

The functional review (main document) answers *did the plan deliver what it was asked to deliver*. It does
not ask whether what was delivered is well made. That is the second question, and it has two sources of
truth: general good practice for the language and kind of change, and what **this project** has decided —
its standards skills, its conventions, its architecture, its recorded decisions. Security is **not** part
of it: it has its own reviewer (`finalize-step-security-audit`) and stays there.

The old structural self-review tried to make this review language-aware with per-language diff surfacers.
This plan does not. The knowledge a code reviewer needs per language already exists as **standards skills**
in the domain bundles (`java-core`, `junit-core`, `python-core`, `pytest-testing`, `javascript`,
`cui-logging`, `ref-code-quality`, …), and every repository already declares, in its `marshal.json`, which
domains it enables. The code review loads the standards the plan's domains name and reads the changed code
against them. Domain knowledge comes from configuration and existing skills, not from new scripts.

plan-marshall already generates a reviewer artifact for the organisation's PR bot: the `cuioss-review-bot`
export target (`marketplace/targets/cuioss_review_bot/`) emits one instruction pack per derived domain plus a
spine charter. **As it stands that artifact is security-scoped**: domains are discovered from `*-security`,
`arch-gate-*` and `ext-triage-*` skills, rules are harvested only from the `*-security` skills
(`_RULE_SOURCE_KINDS`), the spine comes from `persona-security-expert`, and five of the nine spine categories
are security categories. What carries over unchanged is the machinery (derived domain set, orthogonal
per-domain artifacts, category and rule budgets, stale-artifact pruning) and the four charter clauses —
substantiation, anti-fabrication, intent-as-claim, severity-is-not-a-threshold — which are exactly the
discipline an in-run code reviewer needs. This plan adds a second, non-security derivation through that
machinery and makes it the shared rulebook for both reviewers: the in-run step and the external bot.

## Deliverables

10. **A code-review rule set derived from the standards skills, without security.** Extend the
    `cuioss-review-bot` target with a second artifact set, *code-review packs*:
    - domains are the domain bundles themselves; each pack's rules come from the bundle's
      implementation, testing and quality standards (the skills its `skills_by_profile` names for
      `implementation`, `module_testing` and `quality` — verify-first clause A settles the source);
      `*-security` skills and `persona-security-expert` are excluded by construction;
    - the spine carries the four charter clauses verbatim and a non-security category list drawn from
      `ref-code-quality` (correctness, error handling and fail-closed behaviour, resource lifecycle,
      complexity and duplication, naming and documentation accuracy, test quality including negative cases,
      contract and doc drift between code and its governing documents);
    - the existing security packs are unchanged.
    *Done when:* `./pw generate --target cuioss-review-bot` emits both sets; a guard test proves no
    code-review pack contains a rule harvested from a `*-security` skill or a security spine category, and that
    every derived domain has a pack.

11. **The code review step exists.** A new finalize step `default:code-review` in the settle band, after
    `default:functional-review` and before the quality gate and push; `head_dependent: true`,
    `mutates_source: false`, `default_on: true`, dispatched like the functional review. It reads:
    - the change: every changed file and function, read whole against the base branch — no candidate
      surfacer;
    - the code-review spine and the packs for the plan's domains (from `references.json` `domains`), loaded
      from the generated artifacts;
    - the project's own conventions: `CLAUDE.md` / `AGENTS.md`, the ADRs whose tags or affected paths match
      the change (`manage-adr`), and the architecture hints for the touched modules (`manage-architecture`).
    *Done when:* a Python-only fixture plan loads the plan-marshall and python packs, a Java-only one loads the
    java and java-cui packs, and neither loads a security pack.

12. **Findings name their rule.** Every finding cites the rule it rests on — a pack rule, a spine category, a
    project convention (file and heading) or an ADR — plus `file:line` and the failure scenario the charter's
    substantiation clause requires. A finding that cites no rule is rejected by the return-schema validator.
    *Done when:* the validator refuses an uncited finding and accepts a cited one (matched fixtures).

13. **Grading, loop and verifier, shared with the functional review.** Same severity vocabulary, same blocking
    line, same author/verifier separation, same loop-back targets (missing work → `5-execute`; an amendment
    to the diff in hand → `6-finalize` inline), same delta-then-closing-round rule. The rubric's code-review
    half lives beside the functional half in one document. *Done when:* the shared rubric document is the
    only place the blocking line is stated, and both steps' tests read it.

14. **The structural check classes are not lost.** The language-neutral reasoning the old self-review applied
    — contract drift, source-of-truth duplication, same-document contradiction, stale count prose,
    description-vs-body drift, fail-open on unreadable input, symmetric-pair asymmetry, regex over-fit —
    becomes spine categories or `ref-code-quality` rules feeding the code-review spine, worded by what they
    look for. The ones that are plan-marshall-specific (skill frontmatter, canonical-invocation blocks,
    executor notations) go into the plan-marshall pack. *Done when:* each of the old step's check classes is
    mapped to a spine category, a pack rule, or a recorded "dropped, because …", in a table in the outline.

15. **The external bot reads the same rulebook.** The `cuioss/cuioss-review-bot` settings repository is
    switched to compose a repository's review from the code-review spine plus its domains' code-review packs,
    and keeps the security spine and packs for its security pass. Two reviewers, one source. Verify-first
    clause B settles whether the bot runs one pass with both sets or two passes. *Done when:* the settings
    repository references the new artifacts and a PR in this repository receives a bot review composed from
    them. (This deliverable changes the settings repository; see the main document's write-boundary.)

16. **Configuration, landing facts and migration include the code review.** The main document's D7 (roster,
    composer, steward seeding, dispatch roster, required steps, output template, landing facts) and D8 (the
    `marshall-steward upgrade` migration) cover `default:code-review` as well: a `marshal.json` naming
    `default:pre-submission-self-review` is migrated onto BOTH new steps, its `lane` carried to each. The
    landing payload carries the code-review counts (blocking, advisory, rules cited). *Done when:* the D8
    fixtures assert both steps after migration, and a composed manifest lists both.

## Claim labels and verify-first clauses

- OBSERVED: the `cuioss-review-bot` target derives domains from `*-security`, `arch-gate-*` and
  `ext-triage-*` skills, harvests rules from the security skills only (`_RULE_SOURCE_KINDS = (KIND_SECURITY,)`),
  takes its spine from `persona-security-expert`, and carries nine spine categories, five of them security —
  `marketplace/targets/cuioss_review_bot/target.py`.
- OBSERVED: the four charter clauses are module constants in that file and are carried verbatim into the
  spine artifact.
- OBSERVED: repositories declare their domains in `marshal.json` `skill_domains` (e.g. `cui-http`: `java`,
  `java-cui`, `documentation`) with `active_profiles` `implementation`, `module_testing`, `quality`.
- Verify-first clause A — the rule source per domain: the bundle's `skills_by_profile` for the three profiles,
  or an explicit list per bundle. Rules must be harvestable — check whether those skills carry a block the
  target can harvest (as the security skills' "Prohibited actions" / "Constraints" do) or need one added, and
  respect `MAX_DOMAIN_RULES`.
- Verify-first clause B — one bot pass or two. The org charter's category ceiling (about ten) argues for two
  focused passes rather than one merged list.
- Verify-first clause C — the in-run step reads the generated packs from where: the generated `target/` tree
  exists only in this repository; consumers need the packs from the installed plugin cache or regenerated at
  review time. Settle the read path before D11.
- Verify-first clause D — the plan's domains as recorded in `references.json` versus the domains the realized
  footprint touches (a plan can touch a file of a domain it did not declare). Recommended: the union.

### Re-grounding at staging (orchestrator, 2026-10-10, `main` at `370f42379`, read-only)

- CONFIRMED: domain discovery (`marketplace/targets/cuioss_review_bot/target.py:18-19, 75-85,
  256-262`), `_RULE_SOURCE_KINDS = (KIND_SECURITY,)` (line 104; harvested headings "Prohibited
  actions" / "Constraints", line 96; `MAX_DOMAIN_RULES = 12`, line 135), `SPINE_SKILL` =
  `persona-security-expert` (line 73), the four charter clauses as module constants (lines 173,
  182, 190, 197, emitted at 464).
- PARTLY: nine spine categories (lines 207-219), but four are plainly security (injection,
  authn/authz, secrets, supply chain); concurrency/TOCTOU arguably a fifth; the ninth (missing
  negative tests "for any of the above") inherits the security scope.
- PARTLY: cui-http's `skill_domains` keys are system, general-dev, java, java-cui, documentation
  (`cui-http/.plan/marshal.json:246`) — `general-dev` is missing from the claim above;
  `active_profiles` is confirmed (line 276).
- **Clause A is a real gap**: the standards skills carry no "Prohibited actions" / "Constraints"
  block the harvester can read; D10 adds one per skill it draws from, or a new harvest rule.
- **Clause C, the facts**: the target writes to the git-ignored `target/cuioss-review-bot/packs/`
  (`target.py:164, 695`; `emits_bundle_tree` False, line 625). CI
  (`.github/workflows/cuioss-review-bot-packs-publish.yml`) regenerates the packs on pushes to
  main and opens a PR copying `packs/*.md` into `cuioss/cuioss-review-bot`. `sync.py` syncs only
  the claude, opencode and antigravity harnesses, and the plugin cache holds no packs. A consumer
  can therefore read packs today only from the settings repository; D11 needs a new read path.
- **The surface entry "its README" is wrong**: `marketplace/targets/cuioss_review_bot/` holds only
  `__init__.py` and `target.py`. The target's documentation is
  `automatic-review/standards/cuioss-review-bot.md`.
- **Naming**: `default:code-review` sits beside the existing `plan-marshall:recipe-code-review`
  and `persona-code-reviewer`; check for a collision in step discovery and in prose before
  fixing the id.

## Expected surface

- `marketplace/targets/cuioss_review_bot/target.py` and its README — the code-review derivation (D10)
- `test/marketplace/targets/cuioss_review_bot/` — derivation and no-security guards (D10)
- standards skills that need a harvestable rule block (`ref-code-quality`, per-domain core/testing skills) —
  only where clause A requires it (D10, D14)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/code-review.md` — new (D11–D13)
- the shared rubric document from the main document's D4 — extended (D13)
- the return-schema validator script from the main document's D2 — extended for cited rules (D12)
- the D7/D8 surface of the main document — both steps (D16)
- the `cuioss/cuioss-review-bot` settings repository — pack composition (D15)

## Sequencing inside the plan

Main D1–D5 (functional review) and D10–D13 (code review) can be built in parallel; D14 needs the old step's
check list, so it runs before main D6 deletes that step; main D6–D8 with D16 switch over and migrate; land;
then D15 (the bot) and main D9 (the consumer rollout) after the harness sync.
