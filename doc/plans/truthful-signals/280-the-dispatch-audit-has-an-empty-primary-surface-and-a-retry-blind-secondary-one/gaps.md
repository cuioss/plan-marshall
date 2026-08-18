# Gaps — 280 the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one

**Source:** verification.md (same directory)   **Open items:** 6

## G1 — Make the backward-compat test actually constrain the `--workflow` gate

- **Kind:** vacuous-test
- **Severity:** high
- **Where:** `test/plan-marshall/manage-config/test_dispatch_seam_emission.py:271` —
  `test_bare_resolve_without_workflow_emits_nothing`; guard under test at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py:544` — `if workflow:`
- **What is wrong:** the test runs `effort resolve-target --phase phase-5-execute` with **no
  `--plan-id`**, then asserts `_dispatch_lines('bare') == []` and `_resolve_records('bare') == []`.
  An emission from that invocation routes to the dated **global** log (absent `plan_id` →
  `route_plan_id = None` → `plan_logging.get_log_path`'s global fallback, executed and confirmed), not
  to plan `bare`'s log — so the assertions read a file the emission would never touch, and they are
  negative-only. Mutation-proven: replacing `if workflow:` with `if True:` (every bare read-only
  resolve now writes two log records) leaves all 9 tests in the file **green**.
- **Why it matters:** the "a bare resolve stays a pure read, byte-identical" guarantee is asserted in
  four shipped places — `dispatch-logging.md:44`, `manage-config/SKILL.md:1197`,
  `manage-config/standards/api-reference.md:385`, and the `cmd_effort_resolve_target` docstring — and
  nothing enforces it. A future edit that widens or drops the gate would silently start writing two
  audit records for every read-only `resolve-target` query (the resolver is called from doctor and
  reference paths, not only from dispatch sites), polluting the very trail the audit reads and
  inflating both surfaces' populations.
- **Fix:** in `test_bare_resolve_without_workflow_emits_nothing`, pass `--plan-id bare` alongside
  `--phase phase-5-execute` (still no `--workflow`) so the assertion reads the log the emission would
  actually be routed to. Add a second assertion over the global log for the no-`--plan-id` case: read
  `plan_logging.get_log_path(None, 'work')` / `(None, 'decision')` before and after the invocation and
  assert the line counts are unchanged.
- **Done when:** replacing `if workflow:` with `if True:` at `_cmd_effort.py:544` makes
  `test_bare_resolve_without_workflow_emits_nothing` **fail**, and the unmutated file passes.
- **Module/topic:** `plan-marshall:manage-config` — the `effort resolve-target` seam and its tests.

## G2 — Reconcile the 11 hand-written `[DISPATCH]` blocks with the standard that now forbids them

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** 11 emission blocks across 7 files —
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md:112,146,431,484`;
  `.../plan-marshall/workflow/planning.md:286,326`;
  `.../workflow-pr-doctor/SKILL.md:38`;
  `.../phase-6-finalize/workflow/pre-submission-self-review.md:204`;
  `.../phase-6-finalize/workflow/lessons-capture.md:66`;
  `.../phase-6-finalize/workflow/adr-propose.md:51`;
  `.../phase-3-outline/standards/outline-workflow-detail.md:217`
- **What is wrong:** the same PR that left these in place rewrote
  `ref-workflow-architecture/standards/dispatch-logging.md` to state that a caller "MUST NOT also
  hand-write a separate `manage-logging work "[DISPATCH]"` line" (`:44`), to list that shape under
  **"Anti-pattern (forbidden)"** (`:100`), and to declare the seam "the **sole permitted**
  dispatch-emission shape" (`:106`). `grep -rn -- '--message "\[DISPATCH\]'` over `marketplace/` and
  `.claude/` returns 11 matches in 7 files. `planning.md:274` compounds it: it instructs the reader to
  emit the hand-written line and cites `dispatch-logging.md § Emission contract` as the authority for
  doing so — the cited section forbids it.
- **Why it matters:** the corpus contradicts its own contract, so a reader following `planning.md`
  writes a shape the standard calls forbidden, and a reader following the standard finds seven
  counter-examples. These sites also keep the per-role blind spot the plan was written to close: a
  q-gate or refine loop that re-fires still logs once, so the retrospective audit still under-counts
  the planning lane.
- **Fix:** for each of the 7 files, add `--workflow {the doc's own workflow notation} --plan-id
  {plan_id} --caller plan-marshall:{calling-skill}` to the `effort resolve-target` call that already
  precedes the dispatch, delete the `manage-logging work "[DISPATCH]"` block, and reword the
  surrounding prose to "the resolve seam emits the line" (use `execution.md:132` and
  `phase-6-finalize/SKILL.md:618-629` as the two landed templates). For `phase-6-finalize` dispatched
  steps pass an explicit `--role default` (or the step's sub-key) so the emitted `role=` reproduces
  today's label. Reword the `until_clean` / q-gate re-fire loops in `planning-outline.md:138,484` and
  `planning.md:326` from "re-dispatch via the same Task envelope" to "re-run the resolve (which
  re-emits) and re-dispatch".
- **Done when:** `grep -rn -- '--message "\[DISPATCH\]' marketplace/ .claude/` returns 0 matches, and
  every `effort resolve-target` in a dispatch-site doc carries `--workflow`.
- **Module/topic:** `plan-marshall:plan-marshall` workflow docs + `phase-6-finalize` /
  `phase-3-outline` / `workflow-pr-doctor` — dispatch-site migration to the seam.

## G3 — Close D0's six zero-emission dispatch sites

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md:233`
  (light-lane phase-3-outline);
  `.../plan-marshall/workflow/research-best-practices.md:15` (reader variant);
  `.../persona-plan-marshall-agent/standards/agent-behavior-rules.md:85,93`;
  `.../phase-6-finalize/standards/finalize-step-simplify.md:113`;
  `.../extension-api/standards/ext-point-dynamic-level-executor.md:164`;
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-marketplace.md:45`
- **What is wrong:** these are the six sites D0 enumerated as "dispatch happens, no co-located
  emission". All six still resolve a target without `--workflow` and carry no `[DISPATCH]` line at
  HEAD — `grep -c DISPATCH` returns **0** for `finalize-step-simplify.md`,
  `ext-point-dynamic-level-executor.md`, `doctor-marketplace.md` and `agent-behavior-rules.md`. They
  are distinct from G2: those sites emit the wrong *way*, these emit **nothing at all**, on either
  surface.
- **Why it matters:** every dispatch from these paths is invisible to both audit surfaces at once.
  Under the audit's own coverage rule that is indistinguishable from the step having run inline, which
  is the exact false-clean this plan exists to eliminate. Two of them (`agent-behavior-rules.md` and
  `research-best-practices.md`) govern the research/reader dispatch used across phases, so the blind
  spot is not rare.
- **Fix:** add `--workflow {the workflow doc the subagent loads} --plan-id {plan_id} --caller
  plan-marshall:{calling-skill}` to the existing `effort resolve-target` call at each of the six sites,
  following `dispatch-logging.md` § "Canonical invocation". For the `--default` and
  `execution-context-reader-{level}` variants confirm the emitted `role=` label first: with neither
  `--role` nor `--phase`, `_cmd_effort.py:495` falls back to the literal `default`.
- **Done when:** each of the six `effort resolve-target` invocations carries `--workflow`, and a
  re-derived sweep of execution-context dispatch sites finds no site that resolves a target without
  passing the dispatch context.
- **Module/topic:** dispatch-site migration — cross-bundle (`plan-marshall`,
  `persona-plan-marshall-agent`, `phase-6-finalize`, `extension-api`, `pm-plugin-development`).

## G4 — Fix the two finalize doc-echoes that describe an emission step that no longer exists

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md:57-66`
  and `.../phase-6-finalize/workflow/adr-propose.md:42-51`
- **What is wrong:** both say "The dispatcher emits the standardized `[DISPATCH]` work-log line **at
  the call site**", and `lessons-capture.md:58-66` goes further with a heading "`[DISPATCH]` log line
  (emitted by the dispatcher)" and a `manage-logging work` command block introduced as "The
  phase-6-finalize SKILL.md dispatcher emits the line below immediately before invoking this
  workflow". That dispatcher was migrated to the seam: `phase-6-finalize/SKILL.md:618-629` now passes
  `--workflow`/`--plan-id`/`--caller` to the resolve and explicitly says "Do NOT hand-write a separate
  `[DISPATCH]` line", and `grep -n DISPATCH` finds no hand-written emission in that SKILL.md.
- **Why it matters:** the docs describe a step that no longer runs, and show the exact command the
  standard now forbids. A maintainer reading `lessons-capture.md` to understand where the line comes
  from will look for a `manage-logging` call in the dispatcher and not find one; a maintainer copying
  the block reintroduces a double-emission.
- **Fix:** in both files replace "emits the standardized `[DISPATCH]` work-log line at the call site"
  with "passes the dispatch context to its `effort resolve-target`, so the resolve seam emits the
  `[DISPATCH]` work-log line and the paired decision-log record, per firing", and delete the
  `manage-logging work` command block at `lessons-capture.md:62-66`. Keep the cross-reference to
  `dispatch-logging.md`.
- **Done when:** neither file contains a `manage-logging … "[DISPATCH]"` block, and both describe the
  emission as a side-effect of the resolve.
- **Module/topic:** `plan-marshall:phase-6-finalize` — workflow docs.

## G5 — Correct the `role` field's Source cell in the dispatch-logging field table

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md:32`
  — the `role` row of the "Field semantics" table
- **What is wrong:** the Source cell reads "The `--role` argument the caller passed to `effort
  resolve-target`". The implemented seam falls back through `--role` → `--phase` → the resolver
  payload's `role` → the literal `default` (`_cmd_effort.py:556-560` and `:495`). Both landed
  migrated callers rely on that fallback: `execution.md:136` passes only `--phase phase-5-execute`, and
  `phase-6-finalize/SKILL.md:622` passes `--phase phase-6-finalize` with `--role` optional.
- **Why it matters:** a caller reading the table concludes `--role` is required to get a correct
  `role=` label, and may add a redundant or wrong `--role` when migrating a site (G2/G3), changing the
  label the audit rosters on.
- **Fix:** change the Source cell to "The `--role` argument, or `--phase` when `--role` is absent;
  falls back to the resolver's payload role, then to the literal `default` for a `--default` resolve."
- **Done when:** the table's `role` Source cell matches the fallback chain implemented at
  `_cmd_effort.py:556-560`.
- **Module/topic:** `plan-marshall:ref-workflow-architecture` — `dispatch-logging.md`.

## G6 — Emit `plan_id=none` for the `NO_PLAN` sentinel, not the sentinel string

- **Kind:** bug
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py:494` —
  `plan_display = plan_id if plan_id else 'none'` in `_emit_dispatch_records`
- **What is wrong:** `NO_PLAN_SENTINEL` is the string `'NO_PLAN'`
  (`script-shared/scripts/marketplace_paths.py:73`) and is **truthy**, so a caller passing
  `--plan-id NO_PLAN` emits `plan_id=NO_PLAN`. The routing branch two lines below correctly special-cases
  the sentinel via `names_real_plan` (so the record does land in the global log), but the displayed
  field does not — the guard is applied to one half of the expression and not the other. The function's
  own docstring says the argument may be "`None` / a non-plan sentinel for a standalone dispatch", and
  `dispatch-logging.md:35` specifies the field carries "`none` for standalone dispatches".
- **Why it matters:** the `plan_id` field is one of the five literal fields the audit parses. A
  standalone dispatch that used the codebase's own sentinel idiom (`plan_id or NO_PLAN_SENTINEL`,
  documented at `marketplace_paths.py:87-89` as the correct routing/ledger form) produces a third
  vocabulary value the audit has never been told about — the same one-token mismatch class D0 was
  written to sweep for.
- **Fix:** compute the display value from the same predicate the routing uses, e.g.
  `plan_display = plan_id if names_real_plan(plan_id) else 'none'`. Add a test asserting that
  `--plan-id NO_PLAN` emits `plan_id=none` and routes to the global log.
- **Done when:** a `resolve-target --workflow … --plan-id NO_PLAN` emits a `[DISPATCH]` line carrying
  `plan_id=none`, pinned by a test.
- **Module/topic:** `plan-marshall:manage-config` — `_emit_dispatch_records`.
