# Gaps — 280 the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one

**Source:** verification.md (same directory)   **Open items:** 7

> Line references below were re-derived at HEAD during the adversarial review. `_cmd_effort.py` has
> not changed since `1da26b13` (`git diff a884110e HEAD -- …/_cmd_effort.py` is empty), so the
> earlier off-by-two references were transcription errors, not drift.

## G1 — Make the backward-compat test actually constrain the `--workflow` gate

- **Kind:** vacuous-test
- **Severity:** high
- **Where:** `test/plan-marshall/manage-config/test_dispatch_seam_emission.py:273` —
  `test_bare_resolve_without_workflow_emits_nothing`; guard under test at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py:546` — `if workflow:`
- **What is wrong:** the test runs `effort resolve-target --phase phase-5-execute` with **no
  `--plan-id`**, then asserts `_dispatch_lines('bare') == []` and `_resolve_records('bare') == []`.
  An emission from that invocation routes to the dated **global** log (absent `plan_id` →
  `route_plan_id = None` at `_cmd_effort.py:501` → `plan_logging.get_log_path`'s global fallback —
  executed and confirmed: `get_log_path(None,'work')` and `get_log_path('none','work')` both return
  `.plan/local/logs/work-{date}.log`), not to plan `bare`'s log — so the assertions read a file the
  emission would never touch, and they are negative-only. **Mutation-proven twice:** replacing
  `if workflow:` with `if True:` (every bare read-only resolve now writes two log records) leaves all
  9 tests in the file green **and all 1151 tests in `test/plan-marshall/manage-config/` green** — no
  test anywhere in the module pins the gate.
- **Why it matters:** the "a bare resolve stays a pure read, byte-identical" guarantee is asserted in
  four shipped places — `dispatch-logging.md:44`, `manage-config/SKILL.md:1197`,
  `manage-config/standards/api-reference.md:385`, and the `cmd_effort_resolve_target` docstring
  (`_cmd_effort.py:533`) — and nothing enforces it. A future edit that widens or drops the gate would
  silently start writing two audit records for every read-only `resolve-target` query (the resolver is
  called from doctor and reference paths, not only from dispatch sites), polluting the very trail the
  audit reads and inflating both surfaces' populations.
- **Fix:** in `test_bare_resolve_without_workflow_emits_nothing`, pass `--plan-id bare` alongside
  `--phase phase-5-execute` (still no `--workflow`) so the assertion reads the log the emission would
  actually be routed to. Add a second assertion over the global log for the no-`--plan-id` case: read
  `plan_logging.get_log_path(None, 'work')` / `(None, 'decision')` before and after the invocation and
  assert the line counts are unchanged.
- **Done when:** replacing `if workflow:` with `if True:` at `_cmd_effort.py:546` makes
  `test_bare_resolve_without_workflow_emits_nothing` **fail**, and the unmutated file passes.
  *(The adversarial review applied exactly this fix in a scratch mutation and observed the required
  red — `Left contains one more item: '[DISPATCH] … workflow=None plan_id=bare'`, 1 failed / 8 passed
  — then restored both files from saved bytes. The fix is known-good, not merely plausible.)*
- **Module/topic:** `plan-marshall:manage-config` — the `effort resolve-target` seam and its tests.

## G2 — Migrate the 9 hand-written `[DISPATCH]` blocks at real dispatch sites to the seam

- **Kind:** incomplete-sweep
- **Severity:** high *(re-severitied from `medium` during adversarial review — see "Why it matters")*
- **Where:** 9 emission blocks across 5 dispatch-site files —
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md:112,146,431,484`
  (resolves at `:102,138,421,476`);
  `.../plan-marshall/workflow/planning.md:286,326` (resolves at `:270,312`);
  `.../workflow-pr-doctor/SKILL.md:38` (resolve at `:30`);
  `.../phase-6-finalize/workflow/pre-submission-self-review.md:204` (resolve at `:194`);
  `.../phase-3-outline/standards/outline-workflow-detail.md:217` (resolve at `:207`).
  The other two blocks in the tree — `lessons-capture.md:66` and `adr-propose.md:51` — are **not**
  dispatch sites (neither file contains an `effort resolve-target` command block at all); they are
  doc-echoes of a dispatcher that already migrated, and they belong to **G4**.
- **What is wrong:** the same PR that left these in place rewrote
  `ref-workflow-architecture/standards/dispatch-logging.md` to state that a caller "MUST NOT also
  hand-write a separate `manage-logging work "[DISPATCH]"` line" (`:44`), to list that shape as a
  forbidden shape under **"Anti-pattern (forbidden)"** (`:102`), and to declare the seam "the **sole
  permitted** dispatch-emission shape" (`:105`). `grep -rn -- '--message "\[DISPATCH\]'` over
  `marketplace/` and `.claude/` returns **11 matches in 7 files** (re-derived at HEAD); 9 of them, in
  5 files, are the dispatch sites listed above. `planning.md` compounds it **twice**: at `:275` and
  again at `:315` it instructs the reader to "emit the standardized pre-dispatch attempt log line and
  the post-resolve dispatch log line", and `:275` cites `dispatch-logging.md § Emission contract` as
  the authority for doing so — the cited section forbids exactly that shape.
- **Why it matters:** this is a **shipped false signal**, not merely a doc inconsistency. Two of the
  nine blocks sit inside re-fire paths — the `outline_prompt` re-dispatch (`planning-outline.md:130`),
  the `until_clean` q-gate auto-loops (`planning-outline.md:203,508`) and the `refine_prompt`
  re-dispatch (`planning.md:304`) all re-issue the prior `Task:` envelope **without re-running the
  hand-written logging line** — so a planning-lane step that fires N times still contributes one trail
  line. That is precisely the retry blindness D1 was declared "load-bearing … the only deliverable that
  closes the retry blindness by construction", and it remains open on the planning, PR-doctor and
  outline lanes. Compounding it, the corpus contradicts its own contract: a reader following
  `planning.md:275` writes the shape the standard calls forbidden, citing the standard as the reason.
  No lint rule guards this — `grep -rn DISPATCH marketplace/bundles/pm-plugin-development/` finds only
  an unrelated `Task:` regex — so nothing will catch a regression or the remaining instances.
- **Fix:** for each of the 5 files, add `--workflow {the doc's own workflow notation} --plan-id
  {plan_id} --caller plan-marshall:{calling-skill}` to the `effort resolve-target` call named above,
  delete the `manage-logging work "[DISPATCH]"` block, and reword the surrounding prose to "the resolve
  seam emits the line" (use `execution.md:132-136` and `phase-6-finalize/SKILL.md:618-629` as the two
  landed templates). Delete the `[ATTEMPT]` instruction sentences at `planning.md:275` and `:315` or
  restate them without the `[DISPATCH]` half, so neither cites `dispatch-logging.md` as authority for a
  shape that section forbids. Where a resolve passes neither `--role` nor `--phase`
  (`outline-workflow-detail.md:207` uses `--default`), confirm the emitted label first: with all three
  absent the seam falls back to the literal `default` (`_cmd_effort.py:495`; the `--default`
  short-circuit at `:358-371` returns no `role` key, verified by executing the resolver), so pass an
  explicit `--role` if today's hand-written label must be reproduced. Reword the re-fire loops at
  `planning-outline.md:130,203,508` and `planning.md:304` from "re-dispatch via the same `Task:`
  envelope" to "re-run the resolve (which re-emits) and re-dispatch".
- **Done when:** `grep -rn -- '--message "\[DISPATCH\]'` over `marketplace/` and `.claude/` returns no
  match in these 5 files; every `effort resolve-target` in them carries `--workflow`; and no sentence in
  `planning.md` instructs a hand-written `[DISPATCH]` emission.
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
  HEAD — `grep -c DISPATCH` returns **0** for **five** of the six files (`research-best-practices.md`,
  `agent-behavior-rules.md`, `finalize-step-simplify.md`, `ext-point-dynamic-level-executor.md`,
  `doctor-marketplace.md`); `planning.md` returns 2, both belonging to the G2 sites at `:286,326`, not
  to the light-lane site at `:233`. Every line number in the D0 report has drifted (all six, not the
  two verification.md named): `planning.md:232-244`→`:233`,
  `research-best-practices.md:100-108`→`:15`, `agent-behavior-rules.md:101-108`→`:85,93`,
  `finalize-step-simplify.md:124-129`→`:113`, `ext-point-dynamic-level-executor.md:171-179`→`:164`,
  `doctor-marketplace.md:51`→`:45`. They are distinct from G2: those sites emit the wrong *way*, these
  emit **nothing at all**, on either surface.
- **Why it matters:** every dispatch from these paths is invisible to both audit surfaces at once.
  Under the audit's own coverage rule that is indistinguishable from the step having run inline, which
  is the exact false-clean this plan exists to eliminate. `dispatch-logging.md:105` makes this an
  explicit obligation on them — "Callers that today emit no dispatch log MUST pass the dispatch context
  to their resolve" — so these are shipped MUST-violations, not merely unmigrated. Two of them
  (`agent-behavior-rules.md` and `research-best-practices.md`) govern the research/reader dispatch used
  across phases, so the blind spot is not rare.
- **Fix:** add `--workflow {the workflow doc the subagent loads} --plan-id {plan_id} --caller
  plan-marshall:{calling-skill}` to the existing `effort resolve-target` call at each of the six sites,
  following `dispatch-logging.md` § "Canonical invocation". For the `--default` and
  `execution-context-reader-{level}` variants confirm the emitted `role=` label first: with none of
  `--role` / `--phase` / a payload `role` present, `_cmd_effort.py:495` falls back to the literal
  `default` (the `--default` short-circuit at `:358-371` emits no `role` key — verified by executing the
  resolver). **Caveat for `research-best-practices.md:15`:** that line also claims `resolve-target`
  "returns an `execution-context-reader-{level}` variant", which contradicts
  `manage-config/standards/data-model.md:262` and `plan-marshall/standards/effort-roles.md:86` — the
  reader surface reads the level and *composes* the variant name, and `resolve-target` returns the plain
  `execution-context-{level}`. Fix the sentence in the same edit rather than wiring `--workflow` onto a
  call the doc describes incorrectly.
- **Done when:** each of the six `effort resolve-target` invocations carries `--workflow`, and a
  re-derived sweep of execution-context dispatch sites finds no site that resolves a target without
  passing the dispatch context.
- **Module/topic:** dispatch-site migration — cross-bundle (`plan-marshall`,
  `persona-plan-marshall-agent`, `phase-6-finalize`, `extension-api`, `pm-plugin-development`).

## G4 — Fix the two finalize doc-echoes that describe an emission step that no longer exists

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md:57`
  (prose), `:59` (heading), `:61` (sentence), `:63-67` (command block); and
  `.../phase-6-finalize/workflow/adr-propose.md:42` (prose), `:44` (heading), `:46` (sentence),
  `:48-52` (command block)
- **What is wrong:** both say "The dispatcher emits the standardized `[DISPATCH]` work-log line **at
  the call site**", each then carries a heading "`[DISPATCH]` log line (emitted by the dispatcher)"
  and a `manage-logging work` command block introduced as "The phase-6-finalize SKILL.md dispatcher
  emits the line below immediately before invoking this workflow". That dispatcher was migrated to the
  seam: `phase-6-finalize/SKILL.md:618-629` now passes `--workflow`/`--plan-id`/`--caller` to the
  resolve and explicitly says "Do NOT hand-write a separate `[DISPATCH]` line", and all four
  `resolve-target` invocations in that SKILL.md (`:622,951,1015,1498`) carry `--workflow`, with no
  hand-written emission left in the file.
- **Why it matters:** the docs describe a step that no longer runs, and show the exact command the
  standard now forbids (`dispatch-logging.md:102`). A maintainer reading `lessons-capture.md` to
  understand where the line comes from will look for a `manage-logging` call in the dispatcher and not
  find one; a maintainer copying the block reintroduces a double-emission. These two blocks are also
  2 of the 11 tree-wide matches for the forbidden shape, so G2's sweep cannot reach zero without this
  gap being closed.
- **Fix:** in both files replace "emits the standardized `[DISPATCH]` work-log line at the call site"
  with "passes the dispatch context to its `effort resolve-target`, so the resolve seam emits the
  `[DISPATCH]` work-log line and the paired decision-log record, per firing", and delete the heading
  plus its command block (`lessons-capture.md:59-67`, `adr-propose.md:44-52`). Keep the
  cross-reference to `dispatch-logging.md`.
- **Done when:** neither file contains a `manage-logging … "[DISPATCH]"` block, and both describe the
  emission as a side-effect of the resolve.
- **Module/topic:** `plan-marshall:phase-6-finalize` — workflow docs.

## G5 — Correct the `role` field's Source cell in the dispatch-logging field table

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md:31`
  — the `role` row of the "Field semantics" table (row 31, not 32; 32 is the `workflow` row)
- **What is wrong:** the Source cell reads "The `--role` argument the caller passed to `effort
  resolve-target`". The implemented seam falls back through `--role` → `--phase` → the resolver
  payload's `role` → the literal `default` (`_cmd_effort.py:553-557` composes `emission_role`; `:495`
  applies the final `default`). Both landed migrated callers rely on that fallback:
  `execution.md:136` passes only `--phase phase-5-execute`, and `phase-6-finalize/SKILL.md:622` passes
  `--phase phase-6-finalize` with `--role` optional.
- **Why it matters:** a caller reading the table concludes `--role` is required to get a correct
  `role=` label, and may add a redundant or wrong `--role` when migrating a site (G2/G3), changing the
  label the audit rosters on.
- **Fix:** change the Source cell to "The `--role` argument, or `--phase` when `--role` is absent;
  falls back to the resolver's payload role, then to the literal `default` for a `--default` resolve."
- **Done when:** the table's `role` Source cell matches the fallback chain implemented at
  `_cmd_effort.py:553-557` and `:495`.
- **Module/topic:** `plan-marshall:ref-workflow-architecture` — `dispatch-logging.md`.

## G6 — Emit `plan_id=none` for the `NO_PLAN` sentinel, not the sentinel string

- **Kind:** bug
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py:494` —
  `plan_display = plan_id if plan_id else 'none'` in `_emit_dispatch_records`
- **What is wrong:** `NO_PLAN_SENTINEL` is the string `'NO_PLAN'`
  (`script-shared/scripts/marketplace_paths.py:73`) and is **truthy**, so a caller passing
  `--plan-id NO_PLAN` emits `plan_id=NO_PLAN`. **Confirmed by executing `_emit_dispatch_records`**
  with `plan_id='NO_PLAN'`: the work-log body is
  `[DISPATCH] (plan-marshall:manage-config) target=… role=default workflow=… plan_id=NO_PLAN`, while
  `plan_id=None` and `plan_id='none'` both emit `plan_id=none`. The routing branch two lines below
  (`:501`) correctly special-cases the sentinel via `names_real_plan`, but the displayed field does not
  — the guard is applied to one half of the expression and not the other. The function's own docstring
  says the argument may be "`None` / a non-plan sentinel for a standalone dispatch", and
  `dispatch-logging.md:33` specifies the field carries "`none` for standalone dispatches". (The routing
  half is in fact belt-and-braces: `get_log_path('NO_PLAN','work')` already resolves to the dated global
  log, executed and confirmed. The **display** field is the only live defect.)
- **Why it matters:** the `plan_id` field is one of the five literal fields the audit parses. A
  standalone dispatch that used the codebase's own sentinel idiom (`plan_id or NO_PLAN_SENTINEL`,
  documented at `marketplace_paths.py:87-89` as the correct routing/ledger form) produces a third
  vocabulary value the audit has never been told about — the same one-token mismatch class D0 was
  written to sweep for. The sentinel is an accepted `--plan-id` value across the shipped CI surface
  (`tools-integration-ci/SKILL.md:181-218`, "accepted **uniformly** wherever this skill takes a
  `--plan-id`"), so the idiom is already in a caller's hands; `manage-config`'s own `--plan-id` has no
  validation that would reject it.
- **Fix:** compute the display value from the same predicate the routing uses, e.g.
  `plan_display = plan_id if names_real_plan(plan_id) else 'none'`. Add a test asserting that
  `--plan-id NO_PLAN` emits `plan_id=none` and routes to the global log.
- **Done when:** a `resolve-target --workflow … --plan-id NO_PLAN` emits a `[DISPATCH]` line carrying
  `plan_id=none`, pinned by a test.
- **Module/topic:** `plan-marshall:manage-config` — `_emit_dispatch_records`.

## G7 — The orchestrator lane's canonical dispatch form emits on neither surface

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md:130-135`
  — the "**Canonical form.** One dispatch shape, used verbatim" block, whose resolve is
  `effort resolve-target --default` with no `--workflow` / `--plan-id` / `--caller`; consumed by
  `.../plan-orchestrator/workflow/decompose.md:34` and `.../plan-orchestrator/workflow/analyze.md:38`,
  which point at it for their `orchestrator.decompose` / `orchestrator.analyze` dispatches
- **What is wrong:** the orchestrator lane creates `execution-context-{level}` envelopes through this
  one canonical shape, and it resolves without the dispatch context, so the seam emits nothing.
  `grep -rn DISPATCH` over `persona-plan-orchestrator/` and `plan-orchestrator/` returns **zero
  matches in the entire lane** — there is no hand-written emission either. This site is absent from
  D0's enumerated mismatch set (G3's six), so D0's "both directions enumerated" population was
  incomplete: it swept the plan lifecycle and missed the orchestrator lifecycle.
- **Why it matters:** `dispatch-logging.md:3` scopes the obligation to "every
  `plan-marshall:execution-context-{level}` dispatch site", and `:105` states that callers emitting no
  dispatch log MUST pass the dispatch context. The standard even provides the exact affordance this
  lane needs — `:64`, "For standalone dispatches outside any plan, pass `--plan-id none`; the record
  routes to the dated global work/decision log and carries `plan_id=none`" — which matches the
  orchestrator's own `plan_id: none` prompt-body convention (`orchestration-model.md:137`). So the
  omission is not a scoping decision the standard sanctions; it is an unswept lane. Every orchestrator
  analyze/decompose dispatch is invisible to both audit surfaces at once, and the emission would not
  violate the lane's S2 write-boundary rule: the record is written by the orchestrator's own resolve in
  main context, to the global log, not by a leaf into the orchestrator store.
- **Fix:** in `orchestration-model.md`'s canonical-form block, extend the command to
  `effort resolve-target --default --workflow {the workflow/instructions doc the leaf loads} --plan-id
  none --caller plan-marshall:persona-plan-orchestrator`, and add one sentence stating that the resolve
  seam emits the `[DISPATCH]` line and its paired decision-log record to the dated global log, per
  firing. Confirm the emitted label before landing: a `--default` resolve carries no payload `role`, so
  `role=` renders as the literal `default` (`_cmd_effort.py:495`, verified by executing the resolver);
  pass an explicit `--role orchestrator.{surface}` on the `analyze`/`decompose` sites so their records
  are distinguishable in the trail.
- **Done when:** the canonical-form block in `orchestration-model.md` carries `--workflow` and
  `--plan-id none`, and a resolve driven from `analyze.md` / `decompose.md` produces a `[DISPATCH]` line
  in the dated global work log naming the orchestrator surface.
- **Module/topic:** `plan-marshall:persona-plan-orchestrator` / `plan-marshall:plan-orchestrator` —
  orchestrator-lane dispatch emission.

## Refuted during adversarial review

Nothing recorded here. Every gap G1–G6 carried over from the first pass was re-checked against the
tree at HEAD and survived: G1 by re-running the mutation (and widening it to the full 1151-test
`manage-config` suite), G2/G3/G4 by re-deriving the sweeps and opening each cited file, G5 by reading
the implemented fallback chain, and G6 by **executing** `_emit_dispatch_records` on the sentinel. What
changed instead was scope, severity and references — recorded in the "Adversarial review" section of
`verification.md`:

- **G2 was over-scoped**, not wrong. Its 11-block / 7-file `Where` list included
  `lessons-capture.md:66` and `adr-propose.md:51`, and its **Fix** instructed an implementer to "add
  `--workflow` … to the `effort resolve-target` call that already precedes the dispatch" in each of
  the 7 files — but neither of those two files contains an `effort resolve-target` call at all
  (`grep -n 'effort resolve-target'` finds only prose mentions at `lessons-capture.md:57` and
  `adr-propose.md:42`). The instruction was therefore uncarryable for 2 of its 7 files. Those two
  blocks are doc-echoes and were moved into G4, which already owned them and states the correct
  remedy. G2 is now 9 blocks / 5 files.
- **Neither G2 nor G4 was a duplicate to delete.** They overlap on two command blocks but name
  different defects (an unmigrated dispatch site vs. a stale description of a migrated dispatcher) with
  different remedies. The overlap is now stated explicitly in both.
