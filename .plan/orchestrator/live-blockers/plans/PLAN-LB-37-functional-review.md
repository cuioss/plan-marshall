# PLAN-LB-37: The review splits in two: a functional review and a code review

> This plan has TWO documents. This one carries the functional review (D1–D5), the switch-over and
> removal of the old self-review (D6–D7), the configuration migration (D8) and the consumer rollout
> (D9). The companion `companion-PLAN-LB-37-code-review.md` carries the code review (D10–D16). Both are one plan:
> one outline, one branch, one landing.

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-37-functional-review.md` (main document) with its companion `plans/companion-PLAN-LB-37-code-review.md`, and is queued as
> one row file, `queue/PLAN-LB-37.json`, in the epic ledger. Drafted in the PLAN-LB-34 session on
> 2026-10-10 and staged by the orchestrator on the same day by operator instruction ("stage, but review
> first"): the OBSERVED claims and the surface are re-grounded before the command is emitted.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> Staged on 2026-10-10 by operator instruction, after PLAN-LB-34 was stopped unmerged. The operator's
> direction: the review was originally *"did the plan implement the requirements?"* — read the final
> requirements and the solution outline and compare them with the code; that needs no domain knowledge.
> Over time it became an implementation review driven by per-language diff surfacers. Split the review
> apparatus into (1) a **functional review** — this plan — and (2) a **code review** against general best
> practice and project conventions, reusing the cuioss-review-bot instruction packs and explicitly not
> security (a separate, later plan). Security stays its own reviewer (`finalize-step-security-audit`).
> PLAN-LB-34 (`feature/lb-34-self-review-surfacing-foundation-and-java`, unmerged), PLAN-LB-35 and
> PLAN-LB-36 are superseded by this direction.

## Objective

The finalize step `default:pre-submission-self-review` ships switched on to every repository that uses
plan-marshall. It reviews the diff for structural defects using a surfacer — a script that reads the
diff and lists places worth attention. Exactly one surfacer exists and it understands only this
repository's own material, so in a Java or JavaScript repository the review reads nothing and closes
clean. Making it language-aware needs a heuristic, parser-free detector suite per language; PLAN-LB-34
built one for Java and four self-review rounds over that work kept finding defects in the diff-parsing
layer, while every real finding came from reading changed code — not from the candidate lists, most of
which (about 60%) were never reached.

None of that answers the question the review was introduced for: **did the plan deliver what it was
asked to deliver?** That question needs no language knowledge. Its inputs are already held by every
plan: the clarified request, the solution outline (deliverables, success criteria, out-of-scope), the
task records with their verification results, and the change as it stands. The cloud-lane analysis
(`doc/analyzis-cloud-plan/review-apparatus.adoc`) measured what a claim-relative audit of exactly this
shape finds: 9 of 56 deliverables came through unqualified, and 18% of all gaps were corrections to the
runs' own reports — a class no structural review looks for.

This plan replaces the structural self-review with a **functional review**: one reviewer reads the
requirements and the outline, reads the code and tests that implement them, and answers per deliverable
and per success criterion whether it is met, with evidence; it reports changes no deliverable asked for;
and it checks the plan's own claims about itself. A second, non-authoring verifier accepts or refuses
that verdict, as today. The surfacer apparatus is removed. The question it was really answering — is the code well made —
moves to a separate **code review** step defined in the companion document, which loads the standards of
the plan's domains from configuration instead of parsing diffs per language. Because the eight consumer
repositories on this machine are currently the only users, the change is breaking and the consumers are
migrated in the same landing.

## Deliverables

1. **The functional review step exists.** A new finalize step `default:functional-review` (verify-first
   clause 1 settles the id) replaces `default:pre-submission-self-review` in the built-in roster, at the
   same position in the settle band (after the source-mutating steps, before the quality gate and push),
   `head_dependent: true`, `mutates_source: false`, `default_on: true`. It reads, through the existing
   `manage-*` verbs only:
   - the clarified request (`manage-plan-documents request read`, the clarified section when present);
   - the solution outline — every deliverable, its success criteria, its declared affected files, and
     the out-of-scope statements (`manage-solution-outline`);
   - the task records, including each task's verification commands and recorded outcomes
     (`manage-tasks`);
   - the realized footprint and the change against the base branch (`manage-references
     compute-footprint`, `git diff`), read as files and functions, not as a candidate list;
   - the plan's own claims about itself: task closing notes, the decision log, and the commit messages
     on the branch.
   No language-specific script and no extension point is involved. *Done when:* the step is registered,
   discovered, sorted into the settle band, and the composer selects it for the same postures the old
   step was selected for; a fixture plan whose diff is Java-only is reviewed with the same procedure as a
   Python-only one.

2. **Per-deliverable verdicts with evidence.** The author returns one row per deliverable: `met`,
   `met_with_residuals` (names each residual), `not_met`, or `superseded` (only with the operator decision
   or recorded refutation that superseded it, cited), and for every success criterion the evidence it rests
   on — a `file:line`, a test identifier, or a recorded verification run — or `unevidenced`. A criterion
   claimed met with no evidence is `unevidenced`, never `met`. *Done when:* the return schema is defined in
   the workflow document and validated by a script, and a fixture outline with one criterion lacking any
   evidence yields `unevidenced` for it.

3. **Scope and claims are audited, not only coverage.** The review also returns:
   - **unrequested changes** — files in the realized footprint that no deliverable declares or plausibly
     needs, and behaviour changes the outline's out-of-scope section excluded;
   - **false or stale self-reports** — task closing notes, decision-log claims and commit messages that the
     tree contradicts (a symbol, test or count that does not exist or differs).
   *Done when:* fixtures for one unrequested file and one false claim in a task note are each reported, with
   a matched negative (a declared file; a true claim).

4. **Grading and the round loop.** One rubric, in the step's own `standards/`: a `not_met` deliverable or an
   `unevidenced` success criterion is blocking; a residual, an unrequested change or a false self-report is
   graded by consequence (a false claim that a reader would act on is blocking). Blocking findings are filed
   to the Q-Gate store and loop back: missing implementation goes to `5-execute` as fix tasks; a correction
   that needs no new work (a false note, a stale doc line) replays `6-finalize` inline. The author/verifier
   separation of today's step is kept unchanged (the verifier is a second dispatch from the inline context and
   answers whether the grading is supported and whether the round may close). *Done when:* both loop-back
   targets are reachable from fixtures, and a round with no blocking finding closes only on the verifier's
   acceptance.

5. **Bounded cost.** The review reads the outline and requirements whole, and the code each deliverable
   names; it does not walk the diff line by line. A round's record states what it read: deliverables
   reviewed, criteria checked, files read. A delta round after a fix re-checks only the deliverables whose
   files the fix touched, and a closing round re-checks every deliverable once. *Done when:* the step records
   those counts as facts, and a delta round over a one-file fix re-reviews only the deliverables that declare
   that file.

6. **The surfacer apparatus is removed.** Delete, with every reference and test:
   - `default:pre-submission-self-review` (`phase-6-finalize/workflow/pre-submission-self-review.md`) and its
     severity rubric;
   - the `ext-point-self-review-surfacing` extension point and its standard;
   - `pm-plugin-development:ext-self-review-plan-marshall` (skill, scripts, tests, plugin.json entry);
   - every reader of the old step id, its facts and its verdict strings (verify-first clause 2 enumerates them).
   Breaking change, no deprecation shim and no alias. *Done when:* no tracked file names the old step id, the
   extension point or the surfacer skill, and the plugin-doctor and module-tests are green.

7. **Configuration and landing facts follow.**
   - The candidate step list, the composer's decision rules (`commit_push_disabled`, `scope_gated_finalize`),
     the lane defaults, `marshall-steward`'s seeding, `dispatch-inline-split.md`, `required-steps.md`, the
     output template and `DEFAULT_PHASE_6_STEPS` name the new step.
   - The landing payload carries the functional verdict as facts an epic can read without parsing a string:
     deliverables met / with residuals / not met, criteria unevidenced.
   - `CLAUDE.md`'s component counts are re-derived from the plugin manifests.
   *Done when:* a freshly composed manifest lists `functional-review` where the old step stood, and the
   landing-payload test reads the new facts back.

8. **A one-shot migration for configured repositories.** Add a `marshall-steward upgrade` Stage-2 sub-step
   (precedent: `migrate-bot-lists`) that rewrites a `marshal.json` still naming
   `default:pre-submission-self-review` — its entry in `plan.phase-6-finalize.steps`, with its params mapped
   or dropped (`lane` kept; `drop_review_on_scope_gate` dropped or mapped per verify-first clause 3) — onto
   BOTH `default:functional-review` and `default:code-review` (companion D16), idempotent and
   self-disarming, and reports what it changed. *Done when:*
   fixtures cover a config with the old step, one without it, and one already migrated; the second and third
   are no-ops.

9. **Post-landing rollout to every configured repository on this machine.** Executed after the merge AND
   after the harness sync (`project:finalize-step-sync-plugin-cache`), because the consumers load the
   published bundles from the plugin cache. The eligible repositories are every git repository under
   `/home/oliver/git/` with a `.plan/marshal.json`, other than this one — at staging time:
   `API-Sheriff`, `TokenSheriff`, `cui-http`, `cui-jsf-test-basic`, `cui-open-rewrite`, `cuioss-parent-pom`,
   `nifi-extensions`, `plan-marshall-mcp` (re-derive the list at run time; do not trust this one). For each:
   1. pull the default branch; skip and report a repository with a dirty tree or an in-flight plan
      (`.plan/local/plans/*` not archived) — never stash or discard someone's work;
   2. run `/marshall-steward upgrade integrate=true` there (regenerates the executor, reconciles
      `marshal.json`, runs the step-8 migration);
   3. verify: `generate_executor preflight` reports fresh, and `manage-execution-manifest` composes with
      `functional-review` and `code-review` and without the old step;
   4. ship the `marshal.json` change through that repository's normal flow — a `chore/` branch, PR, checks,
      merge — not a direct push.
   Report one row per repository: pulled, migrated, verified, PR, merged, or skipped with the reason.
   *Done when:* every eligible repository is migrated and merged or listed as skipped with a reason the
   operator accepts.

## Claim labels and verify-first clauses

- OBSERVED: the structural self-review step, its workflow (≈1 060 lines), the surfacing extension point and
  the plan-marshall surfacer exist on `main`; the workflow's frontmatter lists 19 structural check classes —
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`.
- OBSERVED: nine repositories under `/home/oliver/git/` carry `.plan/marshal.json` (this one included); six
  of the eight consumers configure `default:pre-submission-self-review` explicitly, two (`cuioss-parent-pom`,
  `cui-jsf-test-basic`) carry no entry and take the default.
- OBSERVED: `marshall-steward upgrade` has a Stage-2 sub-step precedent for a one-shot config migration
  (`migrate-bot-lists`) — `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md`.
- OBSERVED: in PLAN-LB-34's four self-review rounds every blocking finding came from reading changed code
  whole, and the author reached roughly 40% of the line-level candidates per round — PLAN-LB-34 decision log.
- Verify-first clause 1 — the step id. A new id (`default:functional-review`) makes every stale reference fail
  loudly; reusing `default:pre-submission-self-review` avoids the consumer migration but keeps a name that
  now means something else. Recommended: new id. Decide before deliverable 1 and record why.
- Verify-first clause 2 — enumerate every reader of the old step before deleting it: its id, its
  `records_facts` keys, its verdict strings, its rule key `pre-submission-self-review-state`, the
  `manage-status loop-back close` derivation, the landing-payload spec, the output template, the composer's
  pre-filters, steward wizards and every test that pins any of them. Publish the list in the outline.
- Verify-first clause 3 — params: decide what `drop_review_on_scope_gate` maps to, or drop it.
- Verify-first clause 4 — no interim gap: the code review (companion document) lands in the same plan, so the
  old step is removed only once both new steps exist (D6 runs after D1–D5 and D10–D14).
- Verify-first clause 5 — what the review reads as "the code that implements a deliverable": the deliverable's
  declared affected files plus the files the realized footprint attributes to its tasks. Confirm the
  attribution is derivable from existing records (the change ledger's per-deliverable `kind=change` rows) and
  say what happens when it is not.

### Re-grounding at staging (orchestrator, 2026-10-10, `main` at `370f42379`, read-only)

- CONTRADICTED: the workflow is 881 lines, not about 1 060 —
  `phase-6-finalize/workflow/pre-submission-self-review.md`. The 19 check classes are confirmed
  (frontmatter `description`, line 6); `records_facts` are acceptance, may_close,
  work_performed, blocking_count, advisory_count, screened_out (lines 13-19).
- CONFIRMED: the nine repositories and the six explicit configurations. Params found:
  `{drop_review_on_scope_gate: false, lane: standard}` (API-Sheriff, TokenSheriff,
  nifi-extensions, this repository), `{lane: minimal}` (cui-http),
  `{drop_review_on_scope_gate: false, lane: auto}` (cui-open-rewrite), `{lane: standard}`
  (plan-marshall-mcp).
- **Clause 3 is settled: drop `drop_review_on_scope_gate`.** The param is already retired — no
  code reads it (`test/plan-marshall/manage-execution-manifest/test_decision_rules_retired.py:14-35`);
  it survives only in five consumer configurations, this repository's `.plan/marshal.json` and
  `doc/user/parallelism-and-locking.adoc:149`.
- CONFIRMED: the `migrate-bot-lists` precedent (`marshall-steward/SKILL.md:71, 435-440,
  1000-1007`; `references/upgrade-flow.md:51, 329`; a subcommand of `scripts/upgrade.py`), and
  the cloud-analysis figures (`doc/analyzis-cloud-plan/review-apparatus.adoc:139, 231, 458`).
- NOT VERIFIED: the PLAN-LB-34 figures (about 40 percent of candidates reached; every blocker from
  reading code) — they come from that plan's decision log, which was not read.
- **There is no severity rubric file to delete**: the rubric is inline in the workflow (one test,
  `test_pre_submission_self_review_severity.py`). `phase-6-finalize/scripts/` exists but holds no
  validator to extend — D2's script is new.
- **The surface is far wider than listed below.** 117 tracked files outside the ledger name the
  step, its workflow path, its rule key, the extension point or the surfacer. Missing from the
  list below, by group:
  - **manage-config** — the ceremony-gate key `self_review` maps to this step
    (`_cmd_sync_defaults.py:160, 169`; `_config_defaults.py:952, 1094, 1100, 1211`;
    `_manifest_rules.py:620-682`; `manage-execution-manifest.py:1009`). A consumer can set
    `self_review` in its ceremony policy and D8 does not migrate it: decide its successor (one key
    for both new steps, or two). Also `manage-config/SKILL.md`, `standards/data-model.md`.
    "Steward seeding" (D7) lives here, not in `marshall-steward/scripts`, which names the step
    nowhere.
  - **extension-api** — `SKILL.md`, `dispatch-granularity.md`, `ext-point-finalize-step.md`,
    `finalize-step-order-bands.md`, `marshal-json-reference.md`,
    `scripts/configurable_contract.py:122, 394`.
  - **manage-status** — `SKILL.md` (8 hits), `scripts/manage-status.py:33`,
    `scripts/_cmd_mark_step.py:55, 540` (`self_review --since-ref`), `scripts/_cmd_loop_back.py:99-100`
    (docstring; the `{step}-state` derivation is generic).
  - **manage-execution-manifest** — `SKILL.md`, `manifest-schema.md`; the composer reads the bare id
    in `_COMMIT_PUSH_DROP_STEPS` (`_manifest_rules.py:247`) and the scope-gated set (line 443).
  - **phase-6-finalize standards** — `ci-verify.md`, `finalize-step-simplify.md`,
    `pre-push-quality-gate.md`, `verdict-currency.md`.
  - **elsewhere in the bundle** — `automatic-review/SKILL.md`,
    `automatic-review/standards/bot-participation-contract.md`,
    `automatic-review/scripts/review_gate_delta.py:11`,
    `persona-plan-marshall-agent/standards/coverage-gathering-contract.md`,
    `plan-marshall/standards/effort-roles.md`, `plan-orchestrator/scripts/orchestrator.py:1101`.
  - **`<!-- self-review: keep … -->` markers** in six files (for example
    `output-template.md:329`) — dead once the surfacer is gone.
  - **tests** — 24 under `manage-execution-manifest/`, 15 under `phase-6-finalize/`, the
    manage-config and manage-status loop-back tests, `test_qgate_resolve_by_rule.py`, the
    marshall-steward `determine_mode` tests, `test/plan-marshall/test_phase_6_finalize_step_id_consistency.py`
    (14 hits), `test_extension_discovery.py`, `test_resolver_migration.py`,
    `test_finalize_step_sync_baseline.py`.
  - **docs and repository-local skills** — `doc/concepts/{README,automatic-reviews,extension-architecture}.adoc`,
    `doc/user/{configuration,efforts,parallelism-and-locking}.adoc`,
    `doc/resources/diagrams/extension-topology.svg`,
    `.claude/skills/finalize-step-review-retrospective/SKILL.md:361` (`--gates-green`),
    `.claude/skills/recipe-generalization-sweep/SKILL.md`.
- **Readers of the step's facts**: no machine reader keys on `step.pre-submission-self-review.*`;
  `emit-landing.md` and `landing-payload-spec.md` transcribe every step's facts generically;
  `loop-back close` and the `head_dependent` refusal in `mark-step-done` are generic. Human and
  agent readers: the review-retrospective's `--gates-green` rule and the bot-participation
  contract.
- **D6's done-when needs a path exclusion.** 43 git-tracked ledger files under
  `.plan/orchestrator/` name the old step and the write-boundary forbids editing them; the ADRs
  and `doc/analyzis-cloud-plan/` are historical records. Read "no tracked file" as "no file
  outside `.plan/orchestrator/**`, `doc/adr/**` and `doc/analyzis-cloud-plan/**`", or state the
  exclusion the outline chooses.
- **Collision with a running plan**: PLAN-LB-25 (running) declares `phase-6-finalize/SKILL.md`
  and five tests under `test/plan-marshall/phase-6-finalize/`, all inside this plan's surface.
  Launch after PLAN-LB-25 has landed, or rebase onto it before finalize.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — new (D1–D5)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/functional-review-rubric.md` — new (D4)
- a small script for the return-schema validation and the facts, in `phase-6-finalize/scripts/` (D2, D5)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — deleted (D6)
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — deleted (D6)
- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**` — deleted (D6)
- `marketplace/bundles/pm-plugin-development/.claude-plugin/plugin.json`, `README.md` — deregistration (D6)
- `phase-6-finalize/SKILL.md`, `standards/dispatch-inline-split.md`, `standards/required-steps.md`,
  `standards/output-template.md`, `standards/emit-landing.md` — step id and facts (D1, D7)
- `manage-execution-manifest` composer and `standards/decision-rules.md` — candidate set and pre-filters (D7)
- `plan-orchestrator/standards/landing-payload-spec.md` — functional-verdict facts (D7)
- `marshall-steward/scripts/upgrade.py`, `references/upgrade-flow.md`, `SKILL.md` — migration sub-step (D8)
- `.plan/marshal.json` of this repository — step id (D7)
- `CLAUDE.md` — component counts (D7)
- tests under `test/plan-marshall/phase-6-finalize/`, `test/plan-marshall/marshall-steward/`,
  `test/plan-marshall/manage-execution-manifest/`; deletion of `test/pm-plugin-development/ext-self-review-plan-marshall/**`
  and the self-review route, verdict and operator-close tests (D2–D8)

## Dependencies and sequencing

- Depends on: none. Supersedes PLAN-LB-34 (stopped unmerged), PLAN-LB-35 and PLAN-LB-36 — the orchestrator
  marks those three superseded when it stages this plan.
- Salvage from the PLAN-LB-34 branch only what this plan needs; nothing from it is a prerequisite.
- Part of this plan: the code review (companion document, D10–D16), with the cuioss-review-bot settings change
  (D15) run after landing alongside D9.
- Overlaps with: PLAN-LB-26 edits `pre-submission-self-review.md`, which this plan deletes — re-scope or
  supersede it at staging time.
- Suggested order: verify-first clauses 1–5 and the companion's A–D; D1–D5 and D10–D13 (both new steps,
  behind the old one in the roster); D14 (map the old step's checks); D6–D7 with D16 (switch-over and
  removal); D8; land; after the harness sync, D9 (consumer rollout) and D15 (bot settings).

## Hand-off command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-37-functional-review.md"
```

## Write-boundary

The plan implementing this spec touches its own repository's source and tests, and creates or edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message. **Two stated exceptions,
both after landing:** Deliverable 9 changes the `marshal.json` of the other configured repositories on this
machine, and companion Deliverable 15 changes the `cuioss/cuioss-review-bot` settings repository — each
through that repository's own branch-and-PR flow — and the per-repository outcome is reported in the inbox
message.
