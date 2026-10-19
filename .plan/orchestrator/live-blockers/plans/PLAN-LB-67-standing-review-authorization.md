# PLAN-LB-67: Runbook-lane follow-up — standing review authorization, personas, domain skills, docs-only build

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-67-standing-review-authorization.md` and is queued as one row file,
> `queue/PLAN-LB-67.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-18 by operator instruction. **Emit only after PLAN-LB-66 has landed**, because it
> amends the `plan-marshall:runbook-lane` skill that PLAN-LB-66 ships. **Each deliverable is its own
> outline deliverable, and each Done-when is its own success criterion. Do not merge them.**

## Objective

Runbook-lane runs keep stalling at the merge gate for the same reason. A required reviewer with a
review quota reviewed the PR once. Every finding was fixed and resolved. Then the quota refused
every re-review of the later heads, which only carried those fixes or a merge of `main`.

PLAN-LB-61, PLAN-LB-63 and PLAN-LB-52 all hit this. The run then either waits up to 10 × 90 minutes
and closes and reopens the PR, or merges on free text the lane does not accept.

The operator's rule (2026-10-18): **if there was at least one correct review by that reviewer, and
all its findings were handled, the run is authorized to merge.** The reason is the quota, which
exists besides any technical trigger problem.

The local runbook (`.plan/local/opencode/RUNBOOK.md` § 7 "Standing CodeRabbit authorization")
already carries the rule for runs started before PLAN-LB-66 lands. This plan moves it into the
product skill, in repository-neutral form.

## Deliverables

1. **The skill's merge gate carries the standing authorization, scoped to quota-limited reviewers.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-asciidoc, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-implementer
   - `runbook-lane/SKILL.md` § merge gate. For a required reviewer that the project marks as
     quota-limited (see D2), "reviewed the current head" may be replaced by all of these:
     1. **a qualifying review exists**: a formal review by that reviewer on one of this PR's heads,
        listed by `ci pr reviews` with its commit id. Rate-limit notices, summary comments and
        thread replies do not count;
     2. **every finding is handled**: each finding from that review and any later one is fixed in a
        pushed commit, or answered with a reason, and every one of that reviewer's threads is
        resolved;
     3. **it was re-triggered once after the last push**, and the refusal or silence is recorded;
     4. **every other gate condition holds on the current head**: every reviewer that is not
        quota-limited reviewed it, every comment is handled, the build gate is green, CI is green.
   - The reviewer quota policy (steps 1–3) applies only while no qualifying review exists.
   - The authorization never applies to a reviewer that is not quota-limited, and never to a PR
     without a qualifying review.
   - The landing report names, per quota-limited reviewer:
     - the head it reviewed;
     - the current head;
     - each finding and how it was handled.
   - The wording stays repository-neutral: PLAN-LB-66's forbidden-literal scan still passes.

   *Done when:* skill doc tests assert that:
   - the gate names the four conditions;
   - the quota policy is conditional on "no qualifying review";
   - the scope sentence excludes reviewers that are not quota-limited;
   - the landing-report section requires the reviewed head, the current head and the per-finding
     handling;
   - the forbidden-literal scan is clean.

   Each assertion fails against PLAN-LB-66's merged skill.

2. **`runbook_lane resolve` reports which required reviewers are quota-limited, from project
   configuration.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - Each required and optional bot in the resolve payload gains `quota_limited: true|false`.
   - It is read from the bot's standard (`automatic-review/standards/{bot}.md`, the source the verb
     already reads `trigger_comment` from) or from `marshal.json`. Choose at outline and record why.
   - `coderabbit` and `sourcery` declare `quota_limited: true`; `cuioss-review-bot` declares
     `false`.
   - A bot whose standard declares nothing resolves `false`: the authorization stays off by
     default.

   *Done when:* the resolve tests show:
   - `coderabbit` resolves `quota_limited: true`;
   - `cuioss-review-bot` resolves `false`;
   - a fixture bot standard with no declaration resolves `false`.

   All three fail against PLAN-LB-66's merged verb, which carries no such field.

3. **The lane applies the engineering personas as standards, and the reviewer persona refutes
   adversarially.** Added 2026-10-18 by operator instruction, from the pm-mcp-clients Antigravity
   runbook (`~/git/pm-mcp-clients/doc/agy/runbook.md` § 1.3, § 2 Steps 2–3 and 6).
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-asciidoc, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-implementer
   - The skill names one persona per kind of work and tells the run to load it at that step:
     - implementer for production code;
     - module-tester for unit and module tests;
     - integration-tester for multi-module tests;
     - security-expert for trust boundaries, input validation and secrets;
     - documenter for docs;
     - code-reviewer for every self-review round and for triaging every PR comment.
   - The code-reviewer persona applies its adversarial-refute lenses to each finding: defect or
     preference, surplus or load-bearing, real or false-positive drift, and severity. It also
     applies them to the run's own Done-when verdicts, so that "met on paper" is challenged
     (reachability, end-to-end, intent).
   - The persona skills are loaded as **standards only**: the skill states that any plan-marshall
     machinery they mention (`manage-personas`, extension points, orchestrator pipelines) is
     ignored in this lane.
   - The landing report says, per step, which persona was applied.
   - Persona names come from the bundle the lane ships in; no project literal is added.

   *Done when:* skill doc tests assert that:
   - every lane step that writes code, tests or docs, or that reviews, names its persona;
   - self-review and PR triage name adversarial-refute;
   - the "standards only, ignore the machinery" sentence is present;
   - the landing-report section requires the persona list;
   - every named persona resolves to an existing bundle skill (plugin-doctor or a direct
     existence check).

   Each fails against PLAN-LB-66's merged skill, which names no persona.

4. **The lane loads exactly the skills and persona each deliverable names, and checks they exist.**
   Operator decision (2026-10-18): domain skills are decided **at the orchestrator**, when the spec
   is staged, not resolved inside the run. PLAN-LB-69 D4 makes the orchestrator write them into the
   spec.
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - Each spec deliverable carries a `Skills:` line (domain skills) and a `Persona:` line. The
     lane reads both, loads them as standards before working on that deliverable, and lists them
     per deliverable in the progress file and the landing report.
   - **Existence check at setup:** every named skill and persona must exist in the installed
     bundles. A missing one stops the run with a question to the operator; it is never skipped
     silently.
   - **Surface drift:** if a deliverable ends up touching a module the spec's surface did not
     name, the run loads that module's domain skills too, through the same configuration source
     the orchestrator uses. It records the addition (`skills added: …, reason: …`) in the
     landing report. The run never drops a named skill.
   - A spec without `Skills:`/`Persona:` lines (staged before this change) gets D3's per-step
     persona defaults and no domain skills. The landing report says `skills: none named`.

   *Done when:*
   - skill doc tests assert that the setup step names the existence check and the stop-and-ask,
     and that the landing-report section requires the per-deliverable skill list and any
     additions with a reason;
   - a resolve or setup test fails on a fixture spec naming a nonexistent skill, and passes on one
     naming existing skills;
   - a test shows a spec without the lines resolving to `skills: none named`.

   Each fails against PLAN-LB-66's merged skill and verb.

5. **A docs-only change skips the full local build.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-asciidoc
   - Persona: plan-marshall:persona-implementer
   - The build gate checks the worktree diff against the base. If no buildable source changed, it
     runs no full `verify`: it checks the changed docs (format, internal links and references,
     `git status` showing only doc files) and records `build-gate: docs-only` in the progress
     file and the landing message.
   - "Buildable" is decided by the project's own footprint rule, not by a hard-coded extension
     list:
     - this repository: the CI footprint gate (`skip-on-docs-only`) plus its `extra-buildable`
       paths, so `marketplace/**/*.md` still builds;
     - other projects: the architecture data.
     The source is chosen at outline and recorded.
   - Required CI checks still have to be green, so the merge gate is unchanged.

   *Done when:* tests (a `resolve` field or a helper verb, decided at outline) show:
   - a diff touching only `doc/**/*.adoc` classifies as docs-only;
   - a diff touching `marketplace/bundles/**/SKILL.md` in this repository classifies as
     buildable, because of `extra-buildable`;
   - a diff touching a `.py` file classifies as buildable.

   The skill's build-gate section documents the docs-only path. Each fails against PLAN-LB-66's
   merged skill.

6. **The skill restores every runbook rule PLAN-LB-66 weakened, so the local `RUNBOOK.md` can be
   retired.** Added 2026-10-18 from the PLAN-LB-66 landing (`landings/PLAN-LB-66.md`), high.
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The ten weakened or dropped rules are restored in repository-neutral form:
     1. "never `sleep`", with no "bare" qualifier;
     2. the merge gate names `verify` (the full build) green on the current head, not "the build
        gate";
     3. the named review verbs: `ci pr comments`, `ci pr reviews`, `ci pr thread-reply`,
        `ci pr resolve-thread`;
     4. the guard-log path, returned by `resolve`;
     5. the facts block shown inside a literal `landing-facts` fence, with every line in
        `key=value` form (the `guard` fact included, or moved to prose);
     6. `{branch} = {prefix}{plan}` with the closed prefix set;
     7. the build timeout, returned by `resolve` from the architecture data;
     8. the sub-agent tool named so that every target rewrites it (OpenCode `subagent`,
        Antigravity `invoke_subagent`, Claude `Task`), with a target test;
     9. the concrete forbidden-binary list, resolved per project or stated generically with
        examples;
     10. the base branch from `project.default_base_branch` via `resolve`, never a literal `main`.
   - The local runbook's 2026-10-18 rules are carried too:
     - a merge question states CI and `verify` status only from a result obtained on that head
       after the last push, otherwise "pending";
     - the standing review authorization (D1).
   - **Rule-parity test:** the section-parity test is replaced or extended by a rule-level check —
     a list of required rule sentences or keywords per section, extracted from the source runbook
     — so that losing a rule fails the test even when every heading survives.

   *Done when:*
   - a rule-parity test enumerates items 1–10 plus the "pending" rule and fails against
     PLAN-LB-66's merged skill;
   - an emitted-skill test shows the sub-agent tool rewritten for OpenCode and Antigravity;
   - a `parse_landing_facts` test parses the skill's facts example with no dropped line;
   - `resolve` returns `base_branch` and `build_timeout_seconds` for the pyproject fixture.

Split guard: six deliverables, at the ~6 threshold. Kept as one plan by operator instruction ("add
this all to the follow-up (one) plan"); every deliverable lives on the `runbook-lane` skill and its
resolve verb.

## Claim Labels

- OBSERVED: the skill's merge gate in the PLAN-LB-66 worktree requires "Every required reviewer
  reviewed the **current head**" (`runbook-lane/SKILL.md` ~L314), and its quota policy covers ANY
  required reviewer (~L294-303). Read at PLAN-LB-66 head `e585b314c`, before it merged; re-read
  at outline.
- OBSERVED: `runbook_lane resolve` returns the required and optional bots with `trigger_comment`
  and `escalated_trigger_comment` from `automatic-review/standards/{bot}.md` (PLAN-LB-66 D2).
- OBSERVED: PLAN-LB-63 merged after one CodeRabbit review on `5f6ea9940` with both findings
  resolved. Eight quota refusals followed (`landings/PLAN-LB-63.md`).
- OBSERVED: PLAN-LB-61's merged head had no CodeRabbit review (`landings/PLAN-LB-61.md`).
- OBSERVED: PLAN-LB-52 is blocked on the quota with **no** CodeRabbit review at all. The
  authorization does not apply to it, and that case must stay blocked.
- HYPOTHESIS: the bot standards carry a machine-readable header the verb parses (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` (D1)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`,
  `sourcery.md`, `cuioss-review-bot.md` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`,
  which documents the new declaration (verify-at-outline) (D2)
- HYPOTHESIS: `doc/developer/opencode.adoc`, the runbook-lane section (verify-at-outline) (D1, D3, D5)
- OBSERVED: `runbook-lane/SKILL.md` steps for implementation, self-review, PR triage, build gate and landing report (D3, D5)
- HYPOTHESIS: `runbook_lane.py`, the skill existence check, the drift additions and the footprint resolution (verify-at-outline) (D4, D5)
- HYPOTHESIS: `.github/workflows/python-verify.yml`, read only, as the footprint source for this repository (D5)

## Dependencies and Sequencing

- Depends on: **PLAN-LB-66** (running), which ships `runbook-lane/` and the resolve verb.
- Overlaps with: none of the other running plans (PLAN-LB-45, PLAN-LB-52, PLAN-LB-65) on a file.
- Out of scope: the plan-marshall lane's own merge gate (`automatic-review` / phase-6). The
  operator scoped this rule to the runbook lane.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-67-standing-review-authorization.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
