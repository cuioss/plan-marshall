# Plan — Reconcile the `*_without_asking` config family docs to code; promote a diagnosis-discipline standard

**Command:** `/plan-marshall task="implement .plan/plan-optimization/plans/plan-docs-contract-consistency.md"`
**Status:** queued — aggregated queue **P7 (GROUP=DOCS)**. Lightly touches phase-6 `SKILL.md` → SEQUENCE
AFTER P1/P2 (the finalize plans, which mutate the same file). Mostly no-code (doc + config-knob
semantics); one new standard section.
**Lane/posture:** light — this is a docs-accuracy plan, so the *citations are the contract*. Every
file:line here was verified against current source; the outline MUST re-verify before editing because
P1/P2 land first and will drift the phase-6 `SKILL.md` line numbers. **Do not edit a line by number —
match the quoted text.**
**Surface:** `phase-6-finalize/SKILL.md` (the `blocked_user_review` row + the auto-continuation
truth-table), `doc/user/configuration.adoc` (the Review-gates table), `manage-config/scripts/_config_defaults.py`
(read-only — the source of truth being reconciled to), `plan-marshall/standards/execution-recovery.md`
and `plan-marshall/workflow/execution.md` (read-only — the normative halt semantics), plus ONE new
diagnosis-discipline section in `persona-plan-marshall-agent/standards/agent-behavior-rules.md`.

## Problem (evidenced)

The `*_without_asking` config family has drifted from its own documentation in three independent ways,
and a fourth, unrelated anti-pattern (fix-loop misdiagnosis) has recurred often enough across repos to
deserve a standard. All four are documentation/contract defects, not runtime bugs.

**1. One doc says `loop_back_without_asking=false` is an ASK gate; every normative source says it HALTS.**
`phase-6-finalize/SKILL.md:894` — the `blocked_user_review` termination-cause row — lists, as one of
its triggers, *"sonar-roundtrip `loop_back` prompt under `loop_back_without_asking=false`"*, describing
the knob as an `AskUserQuestion` review gate. This is the **only** place that associates the knob with
an ASK, and it is wrong. The normative behaviour is **Display + STOP**, with no `AskUserQuestion`:
- `phase-6-finalize/SKILL.md:1058-1066` — `IF value == false (default): halt the FOR loop … Display: … STOP.`
- `plan-marshall/workflow/execution.md:546` — `ELSE (default, loop_back_without_asking == false) — …
  display the explicit target-named user prompt and STOP`.
- `plan-marshall/standards/execution-recovery.md:80-103` — the `ELSE (default)` branch asserts the
  persisted phase, displays the target-named prompt, and `Then STOP` (`:101`); `:103` names it *"the
  conservative interactive shape"* — a halt-and-instruct-the-user, not an inline `AskUserQuestion`.

The `:894` phrasing conflates a HALT (dispatcher stops, tells the user which slash-command to re-run)
with an ASK (dispatcher blocks inside an `AskUserQuestion` and continues on the answer). It mislabels
the one knob whose entire design point is *not* to prompt inline.

**2. The `*_without_asking` family is semantically inconsistent under one naming convention.**
Same suffix, opposite mechanics:
- `final_merge_without_asking: false` (the merge gate) is a **genuine inline `AskUserQuestion`** — the
  pre-merge confirmation gate fires, and on confirm the pipeline **continues** to the merge
  (`branch-cleanup.md:412` "suppressed only when `final_merge_without_asking == true`"; `:423`
  "interactive-by-default: the operator is prompted to confirm before the irreversible merge"; `:438-440`
  the bypass path skips *"the `AskUserQuestion` block entirely"` — confirming a real ASK on the false path).
- `loop_back_without_asking: false` (the reverse-transition gate) **HALTS and exits** — no
  `AskUserQuestion`, the dispatcher stops and prints a slash-command to re-run (Problem 1 sources).

Two knobs sharing the `_without_asking` suffix mean opposite things: one asks-and-proceeds, one halts.
The suffix reads as "prompt me" for both, but only one prompts. A reader who has learned the merge
knob's behaviour will mis-predict the loop-back knob's. This divergence is the *root cause* of Problem 1
— the `:894` author generalised the merge knob's ASK semantics onto the loop-back knob.

**3. Two docs are stale against the code source-of-truth `_config_defaults.py`.**
- **Deleted knob still documented.** `doc/user/configuration.adoc:70` documents
  `plan.phase-6-finalize.auto_merge_after_ci` with default `true`; `:73` lists it among *"the three
  auto-continuation knobs … flat fields under `plan.phase-6-finalize`"*; `:81` gives a
  `set --field auto_merge_after_ci --value false` example. That knob **no longer exists**: it was renamed
  `final_merge_without_asking`, its default was **inverted `true → false`**, and it was **re-homed** out
  of the flat phase block into a step-owned param under `default:branch-cleanup`. Proven by
  `test_ceremony_automation_migration.py:27-28` (*"the merge gate's default was deliberately flipped from
  the historical `auto_merge_after_ci: True` to `final_merge_without_asking: False` (lesson
  2026-06-16-10-001)"*) and its assertions at `:213-220`. So all three lines are wrong on **name**,
  **default**, and **location**.
- **Truth-table default contradicts the code.** `phase-6-finalize/SKILL.md:1114-1119` — the
  symmetric-auto-continuation truth-table — row 1 (`:1116`) labels `finalize_without_asking` as
  `false (default)`. The code default is **`True`** (`_config_defaults.py:925`,
  `finalize_without_asking': True`). (The companion `loop_back_without_asking: False` at `:926` is
  correctly documented — only the `finalize_without_asking` cell is inverted.)

**4. Fix-loop misdiagnosis has recurred 4× across 2 repos with no governing standard.**
Seed lesson `2026-07-16-16-006` (component `plan-marshall:phase-5-execute`, category anti-pattern):
agents *"explain away real signals by changing/ignoring operating conditions"* rather than checking
ground truth. Four instances:
  1. **nifi #445** — three successive fix tasks (TASK-19/20/21) all failed the *identical* e2e assertion
     identically; each chased a product-code timing hypothesis and burned a full build+CI round-trip. The
     assertion was introduced by the plan itself (commit `fa68e2ca`); a 30-second
     `git log origin/main..HEAD -- <test>` provenance check would have redirected all three.
  2. **nifi finding F978ad9** — a real finding withdrawn after a local re-verify that ran with the
     processors STOPPED, when CI exercises them STARTED — the re-verify changed the operating condition.
  3. **TokenSheriff #572** — a red Sonar gate.
  4. **~90-event harness-kill corpus** — background builds killed by the harness, normalised as
     "flaky/transient" and blind-retried.
The common corrective is invariant: **verify against ground truth / check the diff vs main — never
"retry" or "re-verify locally."** This is the operational sibling of
[[feedback_verify_disk_state_on_tool_contamination]] (re-verify disk state on tool contamination), which
already governs the *tool-output* half; the *diagnosis* half has no home.

## Candidate deliverables (outline MUST split/drop — scope-bloat guard)

1. **Fix the `:894` mislabel (Problem 1).** Correct the `blocked_user_review` row so the `loop_back`
   trigger is described as a **halt/STOP**, not an `AskUserQuestion` review gate. The row legitimately
   covers real ASK gates (branch-cleanup confirmation, the `re_review_timeout` `escalate_ask`) — the fix
   is to *remove the loop-back clause from the ASK enumeration*, or re-file it as a halt, not to rewrite
   the row. Decide which at outline; the minimal edit is preferred.
2. **Reconcile the truth-table cell (Problem 3b).** `SKILL.md:1116` row-1 `finalize_without_asking`
   label `false (default)` → `true (default)` to match `_config_defaults.py:925`. Verify the row's
   *behaviour* prose is still self-consistent after the flip (row-1 describes the halt-and-prompt
   forward transition — re-read it against the corrected default).
3. **Kill the stale `auto_merge_after_ci` docs (Problem 3a).** In `configuration.adoc`, replace the
   `:70` row, the `:73` sentence, and the `:81` example so they document `final_merge_without_asking`
   with default `false`, homed as a **step-owned param under `default:branch-cleanup`** (read via
   `step get`, NOT the flat `plan phase-6-finalize get` path). This means the knob no longer belongs in
   the flat "three auto-continuation knobs" sentence at `:73` — the outline must decide whether to keep
   two flat knobs + one cross-reference, or restructure the sentence.
4. **Reconcile the family-naming divergence (Problem 2) — DECIDE, do not just document.** The two knobs
   share a suffix but not semantics. Options for outline to weigh:
   - (a) **Rename the halt knob honestly** (e.g. `loop_back_without_asking` → a `_halt`/`_pause`-style
     name) so the suffix stops implying an ASK. **HIGH blast radius** — it is a persisted config key with
     a migration test, default-config seed, steward wizard, and consumer marshal.json files; a rename
     needs a back-compat migration exactly like the `auto_merge_after_ci` one. Likely **out of scope**
     for a docs plan — record the decision and the cost.
   - (b) **Make the halt a real ASK** — reverses a deliberate design decision
     (`execution-recovery.md:103` "eliminating any chance of silent re-routing through `2-refine`").
     **Do NOT do this** without a separate design plan; the halt exists on purpose.
   - (c) **Document the divergence in place** (the low-risk default): a one-line note at each knob's
     definition and in `configuration.adoc` clarifying that `loop_back_without_asking` *halts* while
     `final_merge_without_asking` *asks-and-proceeds*. This is the likely landing zone — the plan
     documents the divergence and proposes (a) as a follow-up, without executing a persisted-key rename.
5. **Promote the diagnosis-discipline standard (Problem 4).** Add a Core-Development-Principle-style
   section to `persona-plan-marshall-agent/standards/agent-behavior-rules.md` (§ "Core Development
   Principles" already hosts numbered foundational principles 1-7 at `:34-244` — this is the natural,
   all-work-applicable home; the lesson's `phase-5-execute` component is where it *fired*, but the
   anti-pattern spans FIND/triage/build-retry across every phase). Content: the trigger signal ("N
   consecutive fixes, same identical failure" / "a signal that vanishes only under a locally-changed
   condition"), the corrective (`git log origin/main..HEAD` provenance / green-on-main-vs-red-on-branch /
   verify-against-ground-truth), and an explicit "never blind-retry, never re-verify-locally-to-explain-away"
   rule. Cross-reference [[feedback_verify_disk_state_on_tool_contamination]] as the tool-output sibling.
   **Outline picks ONE home** — do not scatter the rule across phase-5, persona, and a new skill.
6. **Retire the seed lesson.** On landing, `2026-07-16-16-006` is fully absorbed by deliverable 5 →
   retire it (finalize-step-lessons-housekeeping). Do not leave a partially-covered residue.

## Constraints

- **`_config_defaults.py` is the source of truth and is READ-ONLY for this plan.** Docs move to match
  code, never the reverse. If the outline believes a *default* is wrong, that is a different plan — this
  one only reconciles documentation to the shipped defaults.
- **Do NOT rename a persisted config key as a side effect (deliverable 4a).** A key rename is a
  migration with a distribution-contract test, a steward-wizard touch, and consumer-marshal.json impact
  — it is its own plan. This plan may *propose* the rename and *document* the divergence, nothing more.
- **Do NOT convert the loop-back halt into an ASK (deliverable 4b).** The halt is a deliberate decision
  to avoid silent re-routing (`execution-recovery.md:103`). Reversing it is out of scope and adversarial.
- **Re-verify every line number before editing.** P1/P2 land first and rewrite `phase-6-finalize/SKILL.md`;
  `:894`, `:1058-1066`, `:1114-1119` WILL move. Match the quoted anchor text, not the number, and note
  the new line in the edit if it moved.
- **One standard home only (deliverable 5).** Resist adding the diagnosis rule to phase-5 *and* the
  persona *and* a new skill — pick the foundational home and cross-reference from nowhere else.
- **No transitionary prose** — the corrected docs describe current state only; do not narrate
  "renamed from `auto_merge_after_ci`" in user-facing docs (the migration test already records that
  history). Current-state only per the repo doc standards.

## Known landmines (do not rediscover)

1. **`final_merge_without_asking` is NOT a flat phase field — it is step-owned.** It resolves via
   `step get --step-id default:branch-cleanup` / `step-params get`, declared in the step's
   `configurable:` frontmatter (`test_ceremony_automation_migration.py:9-12,86,159-174`). Any doc that
   lists it beside `finalize_without_asking`/`loop_back_without_asking` as a *flat* field (the current
   `configuration.adoc:73` framing) is structurally wrong, not just stale-on-default.
2. **The `:894` row is mostly correct — surgical edit only.** It genuinely enumerates the real ASK gates
   (branch-cleanup confirmation, the `escalate_ask{reason: re_review_timeout}` re-review prompt). Only
   the loop-back clause is wrong. Do not rewrite the whole row or you will break the escalate-ask
   description that item 7a depends on (`SKILL.md:898`).
3. **The truth-table's *behaviour* prose already reads the true default.** `SKILL.md:1116-1121` describe
   the correct halt-and-prompt behaviour and even say (`:1121`) *"the conservative default
   (`loop_back_without_asking=false`)"* — only the `finalize_without_asking` *label cell* at `:1116` is
   inverted. Fix the cell; do not "fix" the prose, which is already right.
4. **`loop_back_without_asking: false` at `_config_defaults.py:926` is correctly documented everywhere.**
   Do not "reconcile" it — only the `finalize_without_asking` default is mis-documented. Touching the
   loop-back default is a no-op edit that risks introducing a real error.
5. **`configuration.adoc` has a second copy in a worktree.** `find` surfaces
   `.plan/local/worktrees/marshall-orchestrator/doc/user/configuration.adoc` — that is the in-flight
   orchestrator plan's checkout, NOT a doc to edit. Edit only the repo-root copy.
6. **The lesson store resolves by CWD's git-common-dir.** `2026-07-16-16-006` lives in plan-marshall's
   store (it was re-homed there 2026-07-16 from nifi per the lesson body). Retire it from the
   plan-marshall CWD; do not re-file a duplicate ([[feedback_manage_lessons_cwd_store_resolution]]).
7. **The diagnosis standard must not become a "retry ban" that breaks legitimate retries.** Some retries
   are correct (a genuinely transient network flake). The rule is *"establish provenance / ground truth
   BEFORE re-attempting the same hypothesis class"* — not "never retry." Phrase it as a provenance-check
   gate, not a blanket prohibition, or it will be ignored as obviously-too-strong.

## Prior art / links

- `phase-6-finalize/SKILL.md:894` (the mislabel), `:1058-1066` (the halt semantics), `:1114-1121`
  (the truth-table + its correct prose).
- `plan-marshall/workflow/execution.md:539-551` and `plan-marshall/standards/execution-recovery.md:75-105`
  — the two normative loop-back halt walkthroughs.
- `phase-6-finalize/standards/branch-cleanup.md:408-440` — the pre-merge `AskUserQuestion` gate proving
  `final_merge_without_asking` is a genuine ask-and-proceed.
- `manage-config/scripts/_config_defaults.py:915-926` — `DEFAULT_PLAN_FINALIZE` (the source of truth:
  `finalize_without_asking: True`, `loop_back_without_asking: False`).
- `test/plan-marshall/manage-config/test_ceremony_automation_migration.py` — the distribution-contract
  test proving the rename + default-inversion + re-home of `auto_merge_after_ci`.
- Seed lesson `2026-07-16-16-006` (fix-loop misdiagnosis) + [[feedback_verify_disk_state_on_tool_contamination]]
  (the tool-output sibling) — deliverable 5.
- HANDOVER §4 P7 (GROUP=DOCS) queue row (the row this graduates); §5 rows for the
  `loop_back_without_asking` doc divergence and the diagnosis-discipline anti-pattern.

## Lifecycle (handled like a plan source)

Move into the plan's own directory on creation. **After archive:** add the §3 Shipped row; strike the
§4 P7 (GROUP=DOCS) queue row; retire the §5 `loop_back_without_asking` doc-divergence row and the
diagnosis-discipline row; retire lesson `2026-07-16-16-006`; update `00-README.md`.
