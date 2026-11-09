# PLAN-LB-138: The orchestrator reads a spaced landing-facts fence, states the Done-when and Expected Surface authoring rules, and authors each deliverable's skills

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-138-orchestrator-staging-and-landing-read-hygiene.md` and is queued as one row file, `queue/PLAN-LB-138.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Regrouped on the operator's word of 2026-11-09 from PLAN-LB-69 (D4 and the folded authoring rules; D5 is retired, see
> Dependencies) and PLAN-LB-84 (D6, the landing fence). PLAN-LB-69 D1 to D3 are retired: `analyze.md` already carries the three-layer
> analysis (PLAN-LB-111, `8859bc1b0`) that replaced the two-leaf audit. Every claim was re-grounded against `main` at `9cd644892` by a
> read-only leaf on 2026-11-09. **Each deliverable is its own outline deliverable, and each Done-when is its own success criterion.
> Do not merge them.** Every Done-when below fails at `9cd644892` unless it says "holds at". No Sonar. No token or measurement work.

## Objective

A landing whose facts fence has a space after the backticks is reported incomplete although it carries every key. The spec template
and `decompose` say nothing about how a Done-when is worded or how an Expected Surface entry is written, so specs have carried
Done-whens that cannot be met ("fails at" a behaviour that already holds) and surface entries the parser drops without a word. And the
lane's reader of each deliverable's `Skills:` and `Persona:` lines has no author: nothing on the orchestrator side writes the lines, so
the lane reports "none named" for every spec staged from the template. This plan closes those three.

## Deliverables

1. **A landing whose facts fence has a space after the backticks is read.**
   - `_LANDING_FENCE_RE` (`_orchestrator_inbox.py`) accepts optional spaces or tabs between the backticks and the info string (the
     CommonMark rule) and still refuses a different info string, an indented fence and a fence of more than three backticks. It reuses
     `script-shared/scripts/markdown_fence.py` `fence_marker` if that reads the same fence correctly, and says which in the PR.
   - `emit-landing.md` Step 2 item 2 states the exact opening line instead of "a ` landing-facts ` info-string fence"
     (padded backticks, which a model reads as spaces).

   *Done when:* each of these fails at `9cd644892`: `parse_landing_facts` on a body opening with ```` ``` landing-facts ```` returns the
   facts dict (it returns `None` at `9cd644892`, so `inbox landing-check` reports every required key missing); a doc test asserts
   `emit-landing.md` carries the exact opening line. And these hold at `9cd644892` and must keep holding: a fence with the info string
   `json` or `landing-factsX` is still not read; an indented fence is still not read.

2. **The Done-when and Expected Surface authoring rules are stated once, and a surface entry the parser drops is reported.**
   - `templates/plan-spec.md` and `workflow/decompose.md` Step 4 state: a Done-when may say "fails at `{sha}`" only for behaviour that
     is new at that sha; a preservation or coverage clause says "holds at `{sha}`"; a Done-when is never labelled "holds at" while a
     claim it rests on is still a HYPOTHESIS in the same spec's Claim Labels; an Expected Surface entry is a full repo-relative path.
   - `epic_spec_parser.py` `_is_path_candidate` (L511-525) accepts a single-segment span only if it contains `*` or exists at the repo
     root, so a bare filename written after "and" (``` `marketplace/x/a.py` and `b.py` ```) is dropped silently and never reaches
     `unresolved`. A bare span that looks like a file (carries a file extension) and resolves to nothing is reported in `unresolved`,
     without admitting dotted symbols such as `monkeypatch.delitem` (the reason the single-segment filter exists).
   - `cleanup.md` Step 5 flags a staged Done-when that says "fails at" beside "still", "keeps" or "unchanged", and one labelled
     "holds at" over a symbol a HYPOTHESIS claim of the same spec also names, through a deterministic `corpus` sub-verb the step
     consumes (today the check is a judgement); decide at outline whether the sub-verb is worth its size and record the answer. If it
     is not, the rule text and the parser report ship and the lint is dropped with the reason in the PR.

   *Done when:* each of these fails at `9cd644892`: a template test and a decompose test assert the three rules; a parser test where the
   bullet ``` `marketplace/x/a.py` and `b.py` ``` yields `b.py` in `unresolved`. And these hold at `9cd644892` and must keep holding:
   `pyproject.toml` and `test_*.py` still resolve; `monkeypatch.delitem` stays excluded.

3. **The orchestrator authors each deliverable's skills and persona, and `next` refuses a spec that names a skill that does not exist.**
   - `templates/plan-spec.md` gives every deliverable a `Skills:` line (domain skills) and a `Persona:` line (implementer,
     module-tester, integration-tester, security-expert or documenter), in the child-line shape `runbook_lane.py` already reads
     (`_SKILLS_DECL_RE` / `_PERSONA_DECL_RE`, both optional); `decompose.md` Step 4 says how they are filled.
   - A script verb fills them: it maps each deliverable's Expected Surface paths to modules through the architecture data and returns
     the domain skills from the project's configuration and a persona suggested from the path kind (source, test, document); an
     unmapped path is reported as `unmapped`, never guessed, and the orchestrator then names skills explicitly or records `none`. The
     source of the skill list is chosen at outline and recorded.
   - The lane's declaration reader and existence probe (`_spec_deliverables`, `_resolve_deliverable_skills` with `missing_skills`) is
     lifted into `script-shared` and imported by both the lane and the orchestrator verb: one reader, not a copy.
   - `next` refuses to emit a spec whose named skills do not exist in the installed bundles (it names the missing ones), and
     `cleanup` Step 5 flags a staged spec with no declaration.

   *Done when:* each of these fails at `9cd644892`: a template test asserts `Skills:` and `Persona:` inside `## Deliverables`; the new
   verb exists (an argparse call is rejected at `9cd644892`) and a Python spec yields this repository's Python domain skills, a Maven
   spec touching a Java module yields the Java domain skills, an unmapped path yields `unmapped`; a `next` fixture whose spec names
   `plan-marshall:does-not-exist` is refused (it is emitted at `9cd644892`). And this holds at `9cd644892` and must keep holding: a
   spec with no `Skills:` line still resolves in the lane as `none named`.

Split guard: three deliverables. D1 is small and independent and ships first if the plan is split; D3 is the largest (a verb and a
lifted reader) and splits off first for size.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- One reader per fact: the Expected Surface stays read by `epic_spec_parser` alone, and the skills declaration stays read by one shared
  reader that the lane and the orchestrator both import.
- A rule that a script can check is a script check, not a prose rule; a rule that needs judgement stays in `cleanup` as judgement and
  says so.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where a Done-when says so.
- Executor regeneration is owed (D3 adds a verb) and the landing says so.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `_LANDING_FENCE_RE = r'^```' + LANDING_FACTS_FENCE + r'[ \t]*\n(?P<body>.*?)\n```[ \t]*$'` (`LANDING_FACTS_FENCE = 'landing-facts'` at L1338), at L1514-1517; `parse_landing_facts` (L1520-1546) returns `None` for a spaced fence — `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- OBSERVED: `emit-landing.md` L276 reads "open with a ` landing-facts ` info-string fence" and shows the exact line two lines below; `landing-payload-spec.md` L84 states the exact line; `runbook-lane/SKILL.md` § 8 (L919-922) is already exact and needs no edit
- OBSERVED: `templates/plan-spec.md` has no `Skills:` or `Persona:` line, no Done-when authoring rule and no `## Done-when` section; `decompose.md` Step 4 (L56-60) says nothing about either; no `spec-skills` verb exists; `next` (`orchestrate.md` Step 4, L74-144) gates on disjointness and prep-ready only; `cleanup.md` Step 5 A3 (L108) flags a missing Objective, Expected Surface or claim label only
- OBSERVED: the lane reads the declarations: `_SKILLS_DECL_RE` / `_PERSONA_DECL_RE` (`runbook_lane.py` L413-417), `_spec_deliverables` (~L823-860), `_resolve_deliverable_skills` (L888-929, `missing_skills`, `missing_probed`, `skills_note: declared|none named`); its docstring says the orchestrator authors the declaration and nothing does
- OBSERVED: `epic_spec_parser._is_path_candidate` (L511-525) drops a single-segment span unless it contains `*` or exists at the repo root; the unresolved report (L676-698) never sees it
- HYPOTHESIS: `script-shared/scripts/markdown_fence.py` `fence_marker` reads a fence with an optional space before the info string and a backtick-free info string, and can serve `parse_landing_facts` — confirm (verify-at-outline, D1)
- HYPOTHESIS: the architecture data and `marshal.json` `skill_domains` can map a repo-relative path to a module and its domain skills through `architecture which-module` without a per-spec guess — confirm the source (verify-at-outline, D3)
- Retired with reason: PLAN-LB-69 D5 (`next` refuses a spec that differs from `origin`): both lanes now read the store-checkout copy (runbook lane `runbook_lane.py` L30-43 with `spec_differ`, PLAN-LB-102 `6d1554570`; the plan-marshall lane through the store seam in `_cmd_request.py` L53-61). The residual hazard (a launch from a machine with no ledger worktree) is a report-only field at most and is not carried.
- Verify-first clause (D3): decide where the lifted reader lives in `script-shared` and which skill list source the verb uses; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — `_LANDING_FENCE_RE`, `parse_landing_facts` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` — Step 2 item 2 (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/plan-spec.md` (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/decompose.md` — Step 4 (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/cleanup.md` — Step 5 (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/orchestrate.md` — Step 4 (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — canonical invocations for the new verb (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — the new verb and the `next` refusal (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/epic_spec_parser.py` — `_is_path_candidate`, the unresolved report (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/markdown_fence.py` — read, edited only if the fence reader needs the spaced form (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — the declaration reader and probe, lifted into `script-shared` (verify-at-outline) (D3)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_landing_completeness.py` (D1)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_plan_spec_template_contract.py` (D2, D3)
- OBSERVED: `test/plan-marshall/script-shared/test_epic_spec_parser.py` (D2)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_expected_surface_single_reader.py` and `test/plan-marshall/plan-orchestrator/test_cleanup_contract.py` (D2, D3)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator.py` (D3)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the lifted reader's tests (D3)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator_spec_skills.py` — new (D3)

## Dependencies and Sequencing

- Depends on: none open. PLAN-LB-111 and PLAN-LB-122 (shipped) own the current `analyze.md`.
- Overlaps with: PLAN-LB-129 (the `review-gate` fix) and PLAN-LB-137 (lane recipes) on `runbook_lane.py` and `test_runbook_lane.py`, if D3 lifts the reader out of the lane; sequence this plan after both, or declare the lift out and keep the reader in place, and say so in the outline. PLAN-LB-133 does not touch this surface.
- Adjacent to: `analyze.md` (not edited) and the lane's use of the declaration (unchanged behaviour).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-138-orchestrator-staging-and-landing-read-hygiene.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
