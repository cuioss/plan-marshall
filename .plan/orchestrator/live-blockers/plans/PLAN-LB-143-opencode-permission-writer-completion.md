# PLAN-LB-143: The OpenCode target expresses an agent's tool restriction, and the permission writers stop dropping, ignoring and refusing what they should keep

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-143-opencode-permission-writer-completion.md` and is queued as one row file, `queue/PLAN-LB-143.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-11 ("aim at larger plans, a smaller number of plans if sensible") from the PLAN-LB-134
> landing analysis (`landings/PLAN-LB-134.md`): its three majors, its minors and the lane's own residue, in one plan on one surface.
> Grounded against `main` at `9771c0f9e` by a read-only leaf, with the orchestrator re-reading the emitter diff, the rule upsert and
> its shadow refusal, the scalar handling in `configure`, the map-removal and `web-apply` branches, and re-running two read-only
> OpenCode queries (`opencode --version` returned `v2.2.7`; `opencode api GET /api/agent/execution-context-reader` returned the ruleset
> quoted below). No Sonar. No token or measurement work.

## Objective

Two things are wrong on the OpenCode target and they share one surface. First, **an agent's tool restriction is not expressed**: the
installed `execution-context-reader` — the untrusted-content reader whose containment is "read-only by construction"
(`agents/execution-context-reader.md`) — evaluates to `[{*,*,allow}, …read/grep/webfetch/websearch allows…, {browser,*,deny},
{skill,browser,deny}]`, so nothing denies edit, write or shell; the emitter that PLAN-LB-134 rewrote now emits no rule at all, and the
documents, the code comments and the tests assume "no match means `ask`", which the live client contradicts. Second, **the permission
writers still lose, ignore or refuse what they should keep**: a scalar `bash` deny or ask becomes an empty map in six writers, a map
removal ignores the effect, `web-apply` replaces a pattern map, a request a later broader row already satisfies aborts
`protect-path` and `ensure`, and a partially overlapping glob is crossed without a conflict. This plan makes the emitted agent say
what its source says, and makes the writers idempotent and shape-preserving.

## Settled Design (decisions the plan implements, not questions)

1. **The base policy is allow-all, observed.** An OpenCode 2 agent's ruleset begins `{action:"*",resource:"*",effect:"allow"}`
   (`opencode v2.2.7`, the live `GET /api/agent/execution-context-reader`; the PLAN-LB-134 PR body records the same for `v2.2.6`). A
   restriction is therefore an explicit `deny` row; an omitted grant restricts nothing. The plan re-reads the same GET after its
   change and records the ruleset returned for the reader and for `execution-context` in the PR body.
2. **The emitter writes denies, never grants.** For an agent whose source declares `tools:`, the emitter writes one
   `{action, resource: "*", effect: deny}` row for each OpenCode action in the mapped universe that the source does not grant, and no
   `allow` or `ask` row. A deny for an action the agent lacks cannot weaken a global deny for that action (it only adds a deny after
   it), so the override hazard that PLAN-LB-134 removed by dropping the grants does not apply to denies. It does override a global
   specific allow for that action, which is intended: the agent has no such tool. The mapped universe is read from
   `mapping['tool_permissions']` (the non-null values), never hard-coded, so a tool the target cannot express adds no row.
3. **Nothing the plan changes widens a deny.** Every writer change preserves an existing deny or ask; none turns one into an allow.

## Deliverables

1. **The emitted agent expresses its tool restriction, and the repository's own configuration does not contradict it.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `transform_agent_frontmatter` (`marketplace/targets/opencode/frontmatter.py`) emits the deny rows of Settled Design 2 for an agent
     whose source declares `tools:`; an agent with no `tools:` field emits none. `render_variant_frontmatter` and `emit_agent_variants`
     (`marketplace/targets/opencode/variant_emitter.py`) carry the same rows into every `-level-N` variant.
   - The repository root `opencode.json` gives the reader agents no shell or edit allow (its `agents."execution-context-reader*"`
     blocks, which carry `python3 .plan/execute-script.py *` and `git status/log/diff *` shell allows although the source declares no
     Bash, are reconciled with the source), and the evaluation order between agent-markdown frontmatter rules and `opencode.json`
     `agents.*` rules is settled by reading the returned ruleset, with the source and version recorded.
   - Decide at outline, with the returned ruleset as the evidence, which denies `execution-context` (the write-capable dispatcher,
     source `tools: Read, Write, Edit, Glob, Grep, Bash, Skill`) receives and confirm none of them removes a tool its dispatch needs
     (`subagent`, `skill`, `question`, `external_directory` are not in the mapped universe unless `mapping.json` maps them).

   *Done when:* each of these fails at `9771c0f9e`, where the emitter emits no rule: a test evaluates the emitted rules of an agent whose
   source declares `tools: WebSearch, WebFetch, Read, Grep` (last match wins, behind `{*,*,allow}`) and finds `edit` and `shell`
   evaluate to `deny` and `webfetch`, `websearch`, `read` and `grep` do not; the same test on the `-level-N` variant output; a test
   finds the emitted frontmatter of an agent whose source grants `Bash` carries no `shell` deny; a test finds the emitter output
   contains no `allow` and no `ask` row for any input; a content test finds no shell allow in the reader agents' blocks of the root
   `opencode.json`. The mapping's null (target-absent) tools and an unmapped tool keep their current outcome, a refusal for the
   unmapped one.

2. **A request that is already satisfied is a success, and a crossing of a partially overlapping rule is a conflict.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `_upsert_permission_rule` (`marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py`) no longer
     returns a conflict when the requested effect already holds through a later broader row of the same effect: the write reports
     nothing added and the file is unchanged. A conflict stays reserved for a move that would CROSS a later, more specific rule with a
     different effect.
   - `_patterns_overlap` detects two glob patterns whose matched sets intersect although neither is a literal resource of the other,
     so `_conflicting_rule` sees `*--force*` against `git push *`. Where it cannot prove two patterns disjoint it treats them as
     overlapping (the fail-closed direction).
   - `permission fix protect-path` completes on a list that already denies `cat *`, `grep *`, `head *` or `tail *` after the shell
     catch-all, installs every remaining vector and the read denies, and reports what it added.

   *Done when:* each of these fails at `9771c0f9e`: on `[{shell,*,allow},{shell,"cat *",deny}]`, `permission fix protect-path` for
   `/home/u/.plan-x` returns success, saves, and the saved list denies the `less`, `more`, `cp`, `grep`, `base64` vectors (today it
   returns `permission_conflict` and saves nothing); on `[{shell,*,allow},{shell,"git *",ask}]`, `ensure ['ask(git push *)']` returns
   success with nothing added; on `[{shell,*,allow},{shell,"git *",ask},{shell,"*--force*",deny}]`, `ensure ['allow(git push *)']`
   returns `permission_conflict` with the file unchanged, or leaves `git push --force x` evaluating to `deny` (today the list ends
   with `git push *` allow and `git push --force x` evaluates to `allow` while the write reports one added).

3. **The OpenCode 1 map writers preserve what they hold.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - Every writer that reaches the `permission.bash` map — `permission_configure`, `permission_fix` ensure/add/remove,
     `permission_ensure_defaults` in `opencode_runtime.py`, and `cmd_ensure`, `cmd_ensure_wildcards`, `cmd_ensure_executor` in
     `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` — keeps a scalar `bash` other than
     `allow` as the map's own `*` row (the rule `_opencode_add` and `_set_map_catch_all` already apply) instead of replacing it with an
     empty map, and does not touch `bash` at all when the operation does not concern it. A non-dict `permission` is reported, not reset.
   - The map branch of `permission_fix` remove matches the requested effect, as `_remove_permission_rule` and `_opencode_remove` do.
   - `permission_web_apply` does not replace a `webfetch` pattern map: the grant becomes the map's `*` row beside the patterns.

   *Done when:* each of these fails at `9771c0f9e`: with `{"permission":{"bash":"deny"}}` each of the six writers, given an operation
   that does not concern `bash` (for example ensure `webfetch`), leaves `bash` as it was, and given `allow(git status *)` leaves a map
   whose `*` row is still `deny` with the new row beside it (today `bash` is `{}` or a map without the deny); with
   `{"permission":{"bash":{"git push *":"deny"}}}`, `permission fix` remove `['allow(git push *)']` removes nothing and reports it
   (today the deny is deleted); with `{"permission":{"webfetch":{"evil.com":"deny"}}}`, `permission_web_apply` add keeps the `evil.com`
   deny (today it is replaced by the string `allow`).

4. **The contract, the documents and the error codes say what the code does.**
   - Skills: pm-documents:ref-documentation
   - Persona: documenter
   - A settings file whose root is not an object, or whose `permissions` value is neither a list nor an object, is refused with
     `invalid_settings` and not written, by every mutating operation (today `permission_load_settings` returns `{}` and the writers
     save a skeleton over the file). No refused or failed operation leaves a file it created: `permission_settings_path(write=True)`
     creates the skeleton only when the first write happens, so a refusal that says "no rule was written" is true.
   - `permission_configure` and `permission_web_apply` return the code the contract lists for a failed save, and the protect-path load
     failure returns the code the contract lists for it; `contract.md` lists each unparseable-JSON case under one code.
     `platform-runtime/SKILL.md` § Error Codes lists every code the operations return.
   - `doc/developer/opencode.adoc`, the code comments and the test docstrings that say "no match means `ask`" state the observed base
     policy with its source and version; the matrix sentence "the agent `"*": "ask"` overrides the global deny" is corrected to what the
     root `opencode.json` does (it restates the global denies after the agent's catch-all).

   *Done when:* each of these fails at `9771c0f9e`: a settings file `[1,2,3]` and one `null` make `permission configure`, `permission
   fix` and `permission web-apply` return `invalid_settings` with the file byte-identical; a conflict or a load failure on a missing
   file leaves no file behind; a doc test finds the adoc, `contract.md` and `SKILL.md` list the same codes the operations return; a doc
   test finds no remaining statement that an unmatched action in an OpenCode 2 agent is `ask`.

5. **The tests pin the behaviours that were only argued.**
   - Skills: pm-dev-python:pytest-testing
   - Persona: module-tester
   - A test asserts a restricted agent stays restricted in emitted output; a test covers the shadow branch by name (the existing
     headline test's `ask` parameter passes through it, not through the crossing branch, and its fixture's deny is already dead before
     any write); the six writers, the map removal and `web-apply` have map-shape cases; `cmd_add`, `cmd_remove` and `cmd_apply_fixes`
     have an unparsable-file case; the setup path has a failed-save case; the OpenCode helper `_effect` and the tests that default to
     `ask` use the observed base policy.

   *Done when:* the cases above exist and each fails against the pre-change code of its deliverable, shown by the run the PR cites
   (mutation-after or test-first, named per case).

Split guard: five deliverables on one surface, below the six-deliverable guard; D1 is the security change and can be shipped first if
the lane judges it must not wait for the rest, which the PR records.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- The existing conflict and crossing tests (`test_ensure_refuses_to_override_a_more_specific_later_deny` with its `allow` parameter,
  `test_ensure_refuses_a_wildcard_action_deny_that_is_more_specific`, and the list-shape effect-matching tests) stay green unchanged:
  a crossing of a more specific later rule with a different effect is still a conflict.
- The emitter never emits an `allow` or an `ask` row (PLAN-LB-134's override hazard stays removed).
- Every change fails closed: an unreadable input, an unprovable overlap and an unknown shape refuse or preserve, never widen.
- A fixture answers a value the real function can give; the evaluation helper in the tests models the observed base policy.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where the Done-when says so.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: the installed `execution-context-reader` evaluates, at `opencode v2.2.7`, to `{*,*,allow}`, `{read,*.env,ask}`, `{read,*.env.*,ask}`, `{read,*.env.example,allow}`, `{grep,*,allow}`, `{read,*,allow}`, `{webfetch,*,allow}`, `{websearch,*,allow}`, `{browser,*,deny}`, `{skill,browser,deny}`: nothing denies edit, write or shell (`opencode api GET /api/agent/execution-context-reader --param directory=…`, run by the orchestrator)
- OBSERVED: `transform_agent_frontmatter` only validates `tools:` and emits no permission rule; the rows it emitted before `b09bf3197` were `allow` rows only (`git diff 27f4e4b96 b09bf3197 -- marketplace/targets/opencode/frontmatter.py`)
- OBSERVED: `_upsert_permission_rule` returns a conflict, saves nothing, when the effect already holds through a later broader row (`opencode_runtime.py` L721-733), and `_rule_exists` requires an exact-resource row (L623-639), so a vector whose resource is absent reaches the upsert
- OBSERVED: `permission_configure` replaces any scalar `bash` other than `allow` with `{}` (`opencode_runtime.py` L1742-1749); the map branch of `permission_fix` remove discards the effect (`cat, pat, _ = …`, L2064-2086); `permission_web_apply` replaces a `webfetch` pattern map with the string `allow` (L2372-2375)
- HYPOTHESIS: the same scalar replacement exists in `permission_fix` ensure/add (L1999-2002), `permission_ensure_defaults` (L2657-2668) and in `permission_fix.py` `cmd_ensure`, `cmd_ensure_wildcards`, `cmd_ensure_executor` (leaf read; confirm by reading each, verify-at-outline)
- HYPOTHESIS: `_patterns_overlap` (L541-545) tests each pattern as a literal resource of the other and `_conflicting_rule` is its only user (leaf read)
- HYPOTHESIS: `permission_load_settings` returns `{}` for a non-object root (L2573) and `permission_settings_path(write=True)` writes the skeleton before the load (L2527-2555); contract.md L55-60 documents the opposite (leaf read)
- HYPOTHESIS: the root `opencode.json` gives `execution-context-reader*` shell allows (`python3 .plan/execute-script.py *`, `git status|log|diff *`) at about L1665-1684 though the source declares no Bash, and restates the 21 global denies after each agent's `*` ask (leaf read)
- HYPOTHESIS: only two marketplace agents declare `tools:` (`execution-context-reader`: `WebSearch, WebFetch, Read, Grep`; `execution-context`: `Read, Write, Edit, Glob, Grep, Bash, Skill`), and the `-level-N` variants carry the same `tools:` (leaf read)
- HYPOTHESIS: a per-agent `deny` for action X evaluated after a global rule for X cannot weaken a global deny (OpenCode's documented order, agent rules appended last, last match wins); confirm by the returned ruleset of the changed agent (verify-at-outline)

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — `_upsert_permission_rule`, `_patterns_overlap`, `_conflicting_rule`, `permission_configure`, `permission_fix`, `permission_web_apply`, `permission_ensure_defaults`, `permission_load_settings`, `permission_settings_path` (D2, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` — `cmd_ensure`, `cmd_ensure_wildcards`, `cmd_ensure_executor`, `cmd_apply_fixes` (D3, D4)
- OBSERVED: `marketplace/targets/opencode/frontmatter.py` — `transform_agent_frontmatter` (D1)
- HYPOTHESIS: `marketplace/targets/opencode/variant_emitter.py` — `render_variant_frontmatter`, `emit_agent_variants`; only if the variants do not pick the change up through `transform_agent_frontmatter` (verify-at-outline)
- HYPOTHESIS: `marketplace/targets/opencode/mapping.json` — only if the mapped universe needs a corrected entry (verify-at-outline)
- OBSERVED: `opencode.json` — the reader agents' blocks (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` and `marketplace/bundles/plan-marshall/skills/platform-runtime/SKILL.md` (D4)
- OBSERVED: `doc/developer/opencode.adoc` (D4)
- OBSERVED: `test/marketplace/targets/opencode/test_frontmatter.py`, `test/marketplace/targets/opencode/test_opencode2_shape.py` and `test/marketplace/targets/opencode/test_variant_emitter.py` (D1, D5)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_permission_shape.py`, `test/plan-marshall/platform-runtime/test_opencode_runtime.py` and `test/plan-marshall/platform-runtime/test_opencode_root_config.py` (D2 to D5)
- OBSERVED: `test/plan-marshall/tools-permission-fix/test_runtime_dsl.py` (D3, D5)
- HYPOTHESIS: `test/plan-marshall/tools-permission-fix/_permission_fix_fixtures.py` and `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py` — the loader delegates to the runtime's, so only if a fixture or the loader needs a change (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-134 (shipped, `b09bf3197`).
- Sequence BEFORE PLAN-LB-135, 136 and 140: PLAN-LB-135 shares `opencode_runtime.py`, `opencode.adoc` and `test_opencode_runtime.py` with this plan and its D3 rewrites the matrix wording this plan's D4 corrects; 136 and 140 follow 135 one at a time. Their specs were grounded at `9cd644892`, before `b09bf3197`, so their line numbers are stale; their Objectives do not depend on the emitter or the shadow refusal.
- Overlaps with running work: none (PLAN-LB-142 touches the automatic-review, finalize-gate and lane surfaces).
- Adjacent to: the OpenCode `permission` doctor and audit unification the PLAN-LB-134 lane answered (the audit and health source sets differ by design) and the lessons-routing findings, which are not in this plan.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-143-opencode-permission-writer-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
