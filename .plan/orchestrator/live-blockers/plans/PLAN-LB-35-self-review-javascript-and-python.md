# PLAN-LB-35: Self-review for every domain, part 2: surfacers for JavaScript and Python

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-35-self-review-javascript-and-python.md` and is queued as one row file, `queue/PLAN-LB-35.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on 2026-10-09 by operator instruction (self-review surfacers "for all domains"). Second of
> three plans; it CANNOT start before PLAN-LB-34 has landed. It revives the retired `truthful-signals`
> specs PLAN-TRUTH-184 (JavaScript) and PLAN-TRUTH-183 (Python). Every OBSERVED claim was read at
> HEAD `fcd54e6ef`; the mechanism it builds on does not exist until PLAN-LB-34 ships, so its first
> deliverable re-reads that landing.

## Objective

After PLAN-LB-34 the self-review can host several surfacers and Java has one. A change to a
JavaScript or TypeScript file is still reported as not covered, and a change to Python in a
consumer project is reviewed by a surfacer tuned to this repository's own script conventions
(executor notations, TOON output, argparse surfaces), which is the wrong lens for an ordinary
Python codebase. This plan adds a surfacer to the frontend bundle and one to the Python bundle,
each on the shared module and each passing the conformance suite PLAN-LB-34 ships. The two are one
plan because they are the two remaining programming-language domains, sit in separate bundles
with no shared file, and can be built side by side inside the plan.

## Deliverables

1. **Gate: read what PLAN-LB-34 landed.** Read its merge commit, the authoring guide and the
   published class table, and re-scope this spec where the mechanism differs — the routing path,
   the class names, whether a second implementor may contribute to a class another owns. *Done
   when:* the outline records the landed mechanism in three lines and lists every deliverable
   below whose wording changed because of it.

2. **The JavaScript surfacer exists.** `ext-self-review-javascript` in `pm-dev-frontend`, with
   its declaration, detection rules and the JavaScript reading of each check, and a `self_review`
   script on the shared module. It covers JavaScript and TypeScript sources (`*.js`, `*.mjs`,
   `*.cjs`, `*.jsx`, `*.ts`, `*.tsx`) and the frontend project files the class table of
   PLAN-LB-34 assigns to it (`package.json`, `tsconfig.json`, `*.css`). *Done when:* discovery
   lists it with its classes; a `.ts` footprint selects it and nothing else.

3. **JavaScript detectors.** Each emits into an existing registry key. At least:
   `changed_code_units` (functions, methods, arrow functions bound to a name, and exported
   components a diff touches, removal-only hunks included); `unguarded_boundaries` (`fetch`,
   `XMLHttpRequest`, file-system calls with no `catch` and no enclosing `try`);
   `contract_sources` (exported interfaces and types, `*.d.ts`, public component props);
   `schema_bearing_files` (`package.json`, JSON schemas, generated API clients); `regexes`
   (literals and `new RegExp`); `user_facing_strings` (JSX text, user-rendered template
   literals, message keys, error messages); `symmetric_pairs` (`addEventListener` /
   `removeEventListener`, `subscribe` / `unsubscribe`); `flag_guard_pairs`,
   `producer_consumer`, `source_of_truth`. Every other key is emitted empty. *Done when:* each
   detector has a positive and a matched negative fixture in the conformance suite.

4. **The JavaScript surfacer states its limits.** The structural limit names what static
   surfacing of JavaScript cannot see (dynamic dispatch, generated code, minified files); CSS is
   its own class row, covered or not covered, never absorbed; the bundle README names the
   surfacer. *Done when:* a mixed TypeScript and CSS fixture reports two class rows.

5. **The Python surfacer exists, and it does not collide with this repository's own.**
   `ext-self-review-python` in `pm-dev-python`, covering Python sources and Python project files
   (`pyproject.toml`, `setup.cfg`) in consumer projects. In this repository the plan-marshall
   surfacer keeps the Python files it covers today; the class table of PLAN-LB-34 decides the
   boundary, and this deliverable implements it. *Done when:* in a consumer-shaped fixture a `.py`
   footprint selects the Python surfacer; in a fixture shaped like this repository the same
   relative path under `marketplace/bundles/` selects the plan-marshall surfacer and not both;
   discovery reports no duplicate-class error.

6. **Python detectors, reused where they are already written.** The plan-marshall surfacer has
   Python detectors that are not specific to this repository — changed code units, unguarded
   boundaries, hoisted binding shadows, regular expressions, symmetric pairs, flag guards. Take
   them from one place: where PLAN-LB-34 moved a detector into the shared module, import it;
   where it stayed private, move it there in this plan and keep the plan-marshall surfacer's
   output unchanged. Add what a consumer codebase needs and the plan-marshall lens lacks:
   `user_facing_strings` over module-level and `async def` docstrings, log and exception
   messages; `advertised_form_help_strings` only where the project has a command line. The
   detectors that read plan-marshall conventions (`contract_sources` over skill documents,
   executor notations, TOON fences) are not carried. *Done when:* each detector has a positive
   and a matched negative fixture; the plan-marshall surfacer's golden envelope set is unchanged.

7. **The Python surfacer states its limits.** Its structural limit names what static surfacing of
   Python cannot see; project files are their own class row; the bundle README names the
   surfacer. *Done when:* a mixed `.py` and `pyproject.toml` fixture reports two class rows.

8. **Both surfacers run on a real repository.** Run each over one real consumer diff — for
   JavaScript, a recent commit of the repository on this machine that enables the `javascript`
   domain; for Python, a consumer Python project if one is checked out, else a synthetic project
   with the layout of one — and record in the pull request the candidate counts per list, the
   class rows, and three candidates read by hand with a judgement on whether a reviewer would
   want them. *Done when:* the pull request carries those figures and judgements; a detector
   whose three sampled candidates are all noise is tightened or removed before merge.

## Claim Labels

- OBSERVED: no surfacer exists for JavaScript or Python — a listing of `marketplace/bundles/*/skills/ext-self-review-*` finds `pm-plugin-development/skills/ext-self-review-plan-marshall` only
- OBSERVED: `pm-dev-frontend` declares the domain key `javascript` with the globs `**/*.js`, `**/*.mjs`, `**/*.jsx` and `**/*.css`; TypeScript suffixes are not among them — `marketplace/bundles/pm-dev-frontend/skills/plan-marshall-plugin/extension.py`
- OBSERVED: `pm-dev-frontend-cui` declares the same four globs under the key `javascript-cui` and has no triage extension of its own — `marketplace/bundles/pm-dev-frontend-cui/skills/plan-marshall-plugin/extension.py`
- OBSERVED: `pm-dev-python` declares the domain key `python` with the glob `**/*.py`, which also matches every Python file under `marketplace/bundles/`, a tree the plugin-development domain claims as a whole — `marketplace/bundles/pm-dev-python/skills/plan-marshall-plugin/extension.py`, `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/extension.py`
- OBSERVED: the frontend bundle ships one deterministic analyzer, a JSDoc compliance check — `marketplace/bundles/pm-dev-frontend/skills/javascript/scripts/jsdoc.py`; `pm-dev-python` ships no script outside its `extension.py`
- OBSERVED: the plan-marshall surfacer's Python detectors are private functions in one 2753-line module, each gated on the `.py` suffix; `changed_code_units` uses `ast.parse` with a regular-expression fallback — `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py:2315`, `:2394-2398`
- OBSERVED: the plan-marshall surfacer's `contract_sources`, `schema_bearing_files` and `count_prose` detectors read plan-marshall conventions (the nearest `SKILL.md` and `standards/*.md`, executor notations, TOON fences) — same module; skill document § Detection Rules (282-372)
- OBSERVED: one repository on this machine enables the `javascript` domain — `/home/oliver/git/nifi-extensions/.plan/marshal.json`
- HYPOTHESIS: the functions a JavaScript or TypeScript diff touches can be found well enough without a parser, from hunk headers and a brace scan, for `changed_code_units` to be useful — confirm/refute on real diffs from `/home/oliver/git/nifi-extensions`; where it cannot, the structural limit says which shapes are missed (verify-at-outline)
- HYPOTHESIS: TypeScript files are meant to belong to the JavaScript domain although its globs omit them — confirm/refute with the operator and at the domain's skill documents; if they are, the domain's glob list is corrected in this plan (verify-at-outline)
- HYPOTHESIS: a consumer Python project is checked out on the machine that runs this plan — confirm/refute by listing the sibling checkouts whose `marshal.json` enables `python`; if none is, deliverable 8 uses the synthetic project and says so (verify-at-outline)
- Verify-first clause: the boundary between the Python surfacer and the plan-marshall surfacer must be a rule a script can evaluate from the path and the repository, not a judgement — for example "Python under a `marketplace/bundles/` tree, or in a repository that enables the plugin-development domain, belongs to the plan-marshall surfacer". Take the rule from PLAN-LB-34's class table; if that table left it open, settle it here before deliverable 5 and add it to the table.
- Verify-first clause: moving a detector into the shared module (deliverable 6) changes the plan-marshall surfacer's imports. Freeze its golden envelope set first, as PLAN-LB-34 did, and move one detector at a time.
- Verify-first clause: decided by the operator on 2026-10-09 — the `-cui` bundles contribute no detectors. State in the JavaScript surfacer's skill document that the `javascript-cui` domain is covered by it, and build nothing for `pm-dev-frontend-cui`.
- Verify-first clause: decided by the operator on 2026-10-09 — surfacers are routed per domain. Each of the two bundles names its surfacer in its `extension.py`; the surface entries for those two files below are therefore certain, not conditional.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-dev-frontend/.claude-plugin/plugin.json` — skill registration (D2)
- OBSERVED: `marketplace/bundles/pm-dev-frontend/README.md` — names the surfacer (D4)
- OBSERVED: `marketplace/bundles/pm-dev-python/.claude-plugin/plugin.json` — skill registration (D5)
- OBSERVED: `marketplace/bundles/pm-dev-python/README.md` — names the surfacer (D7)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` — the reusable Python detectors move out (D6)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — the class table rows for both domains (D2, D5)
- HYPOTHESIS: `marketplace/bundles/pm-dev-frontend/skills/ext-self-review-javascript/SKILL.md` — new skill document (D2, D4) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-frontend/skills/ext-self-review-javascript/scripts/self_review.py` — new script (D2, D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-python/skills/ext-self-review-python/SKILL.md` — new skill document (D5, D7) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-python/skills/ext-self-review-python/scripts/self_review.py` — new script (D5, D6) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/self_review_surfacing.py` — the shared module of PLAN-LB-34, receiving the moved Python detectors; name as landed (D6) (verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-dev-frontend/skills/plan-marshall-plugin/extension.py` — names the JavaScript surfacer; TypeScript globs if confirmed (D2)
- OBSERVED: `marketplace/bundles/pm-dev-python/skills/plan-marshall-plugin/extension.py` — names the Python surfacer (D5)
- HYPOTHESIS: `test/pm-dev-frontend/ext-self-review-javascript/test_self_review_javascript.py` — detector fixtures (D3, D4) (verify-at-outline)
- HYPOTHESIS: `test/pm-dev-python/ext-self-review-python/test_self_review_python.py` — detector fixtures and the ownership boundary (D5, D6, D7) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-34 (the shared module, the class declaration and table, the merge, the conformance suite). It must have landed.
- Priority: second in the self-review chain. It may run together with PLAN-LB-36: the two share one file, the extension-point standard's class table, where each edits its own rows; the second to merge rebases.
- Suggested order inside the plan: the gate; then the JavaScript surfacer (2 to 4) and the Python surfacer (5 to 7) side by side — they share no file; then 8.
- Overlaps with: PLAN-LB-36 on `ext-point-self-review-surfacing.md` (own rows only) and, if both move detectors, on the shared module; PLAN-LB-34 on everything it declares, which is why this plan waits for it.
- Left out on purpose: a JavaScript or TypeScript parser dependency; a surfacer of its own for the `-cui` frontend bundle unless PLAN-LB-34 decided for it; Gradle, npm or other build files beyond the project files named above.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-35-self-review-javascript-and-python.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
