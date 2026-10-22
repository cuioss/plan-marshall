# PLAN-LB-85: The runbook lane reads the pull request's open Sonar issues before it reports ready, and the landing says how many

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-85-lane-sonar-issues.md` and is queued as one row file, `queue/PLAN-LB-85.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the consumer-epic finding `inbox/archive/pm-mcp-core-m2-m4/pm-mcp-core-m2-m4-005.md`
> ("the runbook lane leaves SonarCloud issues open at the merge"), corroborated against the source at
> `9a23d41e9`. Priority is **high**, as the sender rated it: a runbook-lane run reports "quality gate passed"
> and merges while the pull request's own open issues stay open, because the SonarCloud gate checks thresholds
> on new code and passes with open issues, and nothing in the lane reads them. **Each deliverable is its own
> outline deliverable, and each Done-when is its own success criterion. Do not merge them.** A Done-when says
> "fails at `9a23d41e9`" only where the behaviour is new at that sha; a clause that already holds says
> "holds at `9a23d41e9`". A Done-when is never labelled "holds at" while a claim it rests on is still a
> HYPOTHESIS below.

## Objective

A lane that reports a pull request ready to merge has said that the pull request is clean. For a project that
analyses its pull requests with SonarCloud, "clean" includes the open issues the analysis found on the head,
and the gate's word is not that: the gate passes with open issues. The lane reads the open issues of the
pull request, fixes each or dismisses it with a stated reason, treats any other open issue as a blocker of the
merge exactly as it treats a failing check, and writes the measured count into its landing so the drain reads a
figure instead of the gate's word. Where the count could not be read the landing says `unknown`, never `0`;
where the project has no Sonar the lane says so and goes on.

## Deliverables

1. **The Sonar provider can read a pull request's open issues without a plan.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `fetch_findings` cannot be the lane's call as it stands: it requires a plan id, reads the plan-local
     execution manifest, files one finding per issue into that plan's ledger and writes a scan summary into the
     plan directory (`sonar.py` L496-541), and the lane has no plan directory (it passes `--plan-id NO_PLAN`
     to the CI verbs). The provider gains a read that takes a project key and a pull request and returns the
     enumeration to the caller without persisting anything: the open issues' count, their rules and files,
     and the `count_status` discriminator (`confirmed` | `undecidable`) with its reason. Decide at outline
     whether this is a third verb or a no-persist mode of `fetch_findings`, and record why — the provider
     contract is stated as two verbs (`sonar.py` L4), and the choice changes that statement.
   - The read waits for the analysis of the head to settle through the helpers the existing verb uses
     (`_wait_for_ce_ready`, `_fetch_issues`), and it never returns a count over an analysis that did not settle:
     a timeout, an authentication failure or a REST failure returns `undecidable` with `count: null`, never `0`.
   - An unconfigured provider returns the typed `unconfigured` status the existing verb returns
     (`_sonar_unconfigured`), distinct from a read that failed.

   *Done when:* each of these fails at `9a23d41e9`:
   - the read runs with no plan directory present and leaves no file behind;
   - a pull request with open issues returns their count and rules with `count_status: confirmed`;
   - a read whose analysis never settles, and a read whose credential is rejected, each return
     `count: null` with `undecidable` and a reason, not `0`;
   - a project with no Sonar configuration returns `unconfigured`, not a count.

2. **The lane resolves its Sonar state, reads the issues before it reports ready, and gates the merge on them.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `runbook_lane.py resolve` reports the project's Sonar state beside the reviewers it already resolves
     (`cmd_resolve`, `_resolve_bots`): `configured` with the project key, or `not_configured`, read from the
     project's configuration (the meta-project keeps it at `credentials_config.workflow-integration-sonar`
     in `.plan/marshal.json`). Where it is `not_configured` the lane skips the step, records
     `sonar: not_configured` in the progress file and the landing, and nothing blocks. An unreadable
     configuration fails closed like the reviewers' does, with its own reason.
   - A step in `runbook-lane/SKILL.md` § 6, after CI is green on the head and before the lane reports the
     pull request ready: read the pull request's open issues through the deliverable 1 read, fix each in a
     pushed commit or dismiss it with a stated reason, and re-read after the push until the count is `0`
     confirmed or every remaining issue carries a recorded dismissal. How a dismissal is recorded and
     transmitted from a lane that has no plan (the provider's `post_responses` is plan-scoped too) is decided
     at outline and recorded; a dismissal the lane cannot transmit is a blocker, not a silent pass.
   - § 7 gains a merge condition: the open issues of the current head are `0` confirmed or each is dismissed
     with a reason, or the state is `not_configured`. An `undecidable` read is a blocker and is retried; the
     lane never treats it as `0`. A question that bears on the merge states the Sonar state from a read taken
     on the current head after the last push, as it states CI, and reports `pending` where no such read exists.

   *Done when:* each of these fails at `9a23d41e9`:
   - `resolve` on a project with Sonar configured returns `configured` with its project key, and on one
     without returns `not_configured`;
   - the lane text contains the read step in § 6 and the merge condition in § 7, and a test drives the
     resolve result through both states (a text-presence test alone does not satisfy this);
   - a lane run whose read returns `undecidable` does not reach the merge.

3. **The landing carries the measured figure.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The lane's landing facts (§ 8) gain an OPTIONAL Sonar fact: the open-issue count at the merge head and
     the rules of the issues left open, `unknown` where the read was `undecidable`, and `n/a` where the state
     was `not_configured`. It is optional, so the `landing-check` required-key set (`LANDING_REQUIRED_KEYS`,
     `_orchestrator_inbox.py` L1375-1389) is unchanged and no earlier landing becomes incomplete. Decide at
     outline whether it reuses the optional per-step channel the plan lifecycle already uses for
     `sonar-roundtrip`'s scan facts (`step.sonar-roundtrip.{fact_key}`, `emit-landing.md` L166-168) or
     takes its own key, and record why: one channel for one measurement is preferred.
   - `landing-payload-spec.md` documents the fact, the two sentinels and the rule that `unknown` is a failed
     read and never `0`; the landing-analysis template gains a row that reads it, so the drain compares a
     measured figure with the lane's own claim.

   *Done when:* each of these fails at `9a23d41e9`:
   - a lane landing built from a resolve result with a confirmed count carries the fact with that count;
   - a landing built from an `undecidable` read carries `unknown`, and `inbox landing-check` still reports
     `complete: true` for a landing that carries it;
   - `inbox landing-check` reports an unchanged required-key set.

4. **The spec template asks for the check where the project uses Sonar, and for the consumer's field set where a deliverable keeps a consumer unchanged.**
   - Skills: pm-plugin-development:plugin-architecture, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-documenter
   - The consumer epic's finding names this half as the orchestrator's: the specs it wrote listed the build
     gates in their Done-when and a rule-suppression instruction in their Standing Constraints, and neither
     asked for the open-issue read. `templates/plan-spec.md` states, for a project whose `resolve` reports
     Sonar `configured`, that the spec's Done-when lists the open-issue read at the head and that its
     Standing Constraints say how a dismissal is recorded; the staged specs of this epic that still carry a
     runbook hand-off are checked against it at the next `analyze` and corrected under the Fold rule.
   - The template also asks a deliverable that serves an existing consumer unchanged ("keep the consumer as
     is") to enumerate that consumer's consumer-visible field and edge set in the deliverable, with one
     verification criterion per element. PLAN-LB-49 D3 was written as prose against `manage-metrics enrich`;
     the plan's review rounds then discovered, one per round, the multi-root union, the duplicate-window
     aggregation, the documented counters, the window filters, the window boundary and the stale gap flags
     (candidate-lesson `lb-49-opencode-measurement-005`; ten fix tasks of sixteen, eight loop-backs, 25 files
     against 12 declared, per the landing analysis). A deliverable that cannot enumerate the set says so, which
     is the signal that the consumer boundary is not yet understood.

   *Done when:* the plan-spec template fails a check, written as a test over the template, that requires the
   Sonar line for a project with Sonar configured and the template, at `9a23d41e9`, carries none; and a second
   check that requires the consumer-visible-set line for an "unchanged consumer" deliverable, also failing
   at `9a23d41e9`.

Split guard: four deliverables across the Sonar provider, the lane text and resolver, the landing contract and
one template. Proceeding unsplit: D2 and D3 edit the same lane section pair as one decision (what the lane
reads is what it reports), D1 is the one provider read both need, and D4 is one template paragraph. If the
dismissal mechanism of D2 turns into a provider change larger than one verb, split D1 and D2 at outline and
say so in the outline's first deliverable.

## Claim Labels

- OBSERVED: the `runbook-lane` skill directory, scripts included, contains no mention of Sonar (a case-insensitive recursive content search over `marketplace/bundles/plan-marshall/skills/runbook-lane` returned nothing) — orchestrator-read at `9a23d41e9`.
- OBSERVED: `fetch_findings` takes `--plan-id`, reads the plan-local manifest (`_read_manifest_sonar_params`, `sonar.py` L107-138), files findings with `add_finding` and writes a plan-directory scan summary (`sonar.py` L464-541); the lane's CI verbs pass `--plan-id NO_PLAN` (`runbook-lane/SKILL.md` L434, L441) — orchestrator-read.
- OBSERVED: `sonar.py` L4 states "two-verb provider contract: fetch_findings + post_responses" — orchestrator-read.
- OBSERVED: `fetch_findings` returns `new_code_issue_count: null` with `count_status: undecidable` on a CE timeout or an auth/REST failure, never `0`, and a typed `unconfigured` status without a credential (`sonar.py` L479-504) — orchestrator-read.
- OBSERVED: the lane's merge gate (`SKILL.md` § 7, L470-489) lists reviewers, comments, `verify` and CI, with no Sonar condition — orchestrator-read.
- OBSERVED: `LANDING_REQUIRED_KEYS` (`_orchestrator_inbox.py` L1375-1389) carries no Sonar key; `executor_version` and the per-step typed facts ride optional keys, and `emit-landing.md` L166-168 names `sonar-roundtrip`'s scan facts as one of the per-step facts transcribed — orchestrator-read.
- OBSERVED: this repository keeps `credentials_config.workflow-integration-sonar.{organization, project_key}` and a `default:sonar-roundtrip` finalize step in `.plan/marshal.json` (L132-137, L285-290) — orchestrator-read; the layout of a consumer project's configuration is not read here.
- OBSERVED: `runbook_lane.py` `cmd_resolve` resolves reviewers from the `automatic-review` step and fails closed on an empty required list (`_resolve_bots`, L380-416) — orchestrator-read.
- UNVERIFIED LEAD: the consumer epic's counts — 38 open issues over eight merges (one pull request with 18, one with 10, one with 7), three merges clean, 118 open on its `main` — and its SonarCloud API read; reported by `pm-mcp-core-m2-m4-005.md`, not re-read, since the orchestrator did not query SonarCloud. The mechanism, not the counts, is what this spec rests on.
- UNVERIFIED LEAD: this repository's own runbook-lane landings (PLAN-LB-78 and earlier) left Sonar issues open on their pull requests; the lane never read them, so none of those landings can say. The first landing of this plan is the first with a measured figure.
- HYPOTHESIS: the Sonar helpers `_wait_for_ce_ready` and `_fetch_issues` can be called without a plan id and without a manifest — confirm at `sonar.py` L194-286, L411-462 (verify-at-outline).
- HYPOTHESIS: `resolve` can derive `configured` / `not_configured` from the project's `marshal.json` and a credential-presence check without a network call — confirm against `_sonar_credential_missing` (`sonar.py` L389) (verify-at-outline).
- HYPOTHESIS: the lane can dismiss an issue without a plan — the provider's `post_responses` reads the plan's findings, so it cannot as it stands; confirm and decide the mechanism at outline.
- HYPOTHESIS: the `step.sonar-roundtrip.{fact_key}` channel is parsed by the drain's landing reader the same way for a runbook landing as for a lifecycle one — confirm at `analyze.md` Step 4 and `_orchestrator_inbox.py` (verify-at-outline).
- Verify-first clause (deliverable 1): decide third verb versus no-persist mode before scoping; the provider contract text (`sonar.py` L4, the skill's `SKILL.md`) changes with the choice.
- Verify-first clause (deliverable 2): decide the dismissal mechanism before scoping; a mechanism that needs a plan directory loops back to re-scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py` — the plan-less read (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md` — the provider contract text (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar_provider.py` — only if the read moves into the provider seam (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — the Sonar state in `resolve` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — § 6 read step, § 7 merge condition, § 8 fact (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — the optional fact (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md` — the row that reads it (verify-at-outline) (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — Step 4's read of the fact, only if the channel needs it (verify-at-outline) (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/plan-spec.md` — the Sonar line (D4)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-sonar/` (verify-at-outline) (D1)
- HYPOTHESIS: `test/plan-marshall/runbook-lane/` (verify-at-outline) (D2, D3)
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/test_landing_completeness.py` (verify-at-outline) (D3)
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/` — the template check (verify-at-outline) (D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-78 (shipped, `9a23d41e9`) — the lane's resolver and its landing keys.
- Overlaps with: PLAN-LB-73 on `runbook-lane/SKILL.md` and `runbook_lane.py` (LB-73 D4 edits § 2 and § 8 and `_resolve_build` / `_resolve_runtime_stamp`) — sequence AFTER PLAN-LB-73 so the § 8 edit is made on the corrected text; PLAN-LB-58 on `sonar.py` (LB-58 D1 makes `count_status` compare the analysed revision with the head) — the lane's read must reuse that comparison if LB-58 lands first, and LB-58 must not be re-opened by this plan if it lands second; PLAN-LB-84 and PLAN-LB-69 on `landing-payload-spec.md`. The gate will ask.
- Adjacent to: the plan lifecycle's `sonar-roundtrip` finalize step, which this plan neither edits nor replaces — it gives the lane the same read, without a plan.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-85-lane-sonar-issues.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
