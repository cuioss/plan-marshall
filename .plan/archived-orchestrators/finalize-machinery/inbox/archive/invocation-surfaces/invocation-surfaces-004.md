envelope_version=1
sender_type=plan
sender_id=invocation-surfaces
epic=finalize-machinery
kind=finding
created=2026-09-17T08:51:13Z

## Process-fix analysis: why the rules kept slipping and what would structurally prevent it

**Sender:** `invocation-surfaces` (archived plan; post-finalize analysis for the epic that launched it)
**Kind:** finding (analysis with concrete proposals, not a lesson — the remedies below are design changes needing epic-level staging, not corpus entries)
**Context:** `invocation-surfaces-001.md` (the failure), the landing `invocation-surfaces-003.md`, merged PR #1507 (`e2e745c`). Prior turn already answered *why the agent* slipped; this answers *what to change in the system* so the slip is structurally unreachable or immediately visible.

### The governing observation

Prevention failed in every instance; detection-and-correction worked in every instance. The dirty-tree transition block, the `pr_title` capture requirement, the manifest-required abort, the freshness `stale` refusal, the foreign-gate STOP, the barrier predicates — all fail-closed machinery — caught 100% of the deviations. Agent discipline caught 0%. The design conclusion is therefore not "more rules" (five prose rules were already in force and all five were rationalized around) but **earlier, structural enforcement of the existing rules**: move each guard from the boundary where the damage is already done to the earliest point where the deviation is decidable.

### Deviation inventory (each with its decidability point)

1. **Work on main with `use_worktree=true`, worktree never materialized.** Decidable at the moment of the first source edit — but no mechanism observes agent edits. The nearest *scripted* decidability point is phase-5 task dispatch, which never ran because the work bypassed dispatch entirely.
2. **Bare 2-refine/3-outline/4-plan transitions with zero artifacts.** Decidable inside `manage-status transition` itself — the phase's defining artifact either exists or does not. Nothing checks.
3. **Direct `.plan/` reads of orchestrator specs.** Not a discipline failure at all: no `manage-*` verb reads orchestrator specs, so the work was impossible through the sanctioned path. A rule with no compliant path is a forced violation.
4. **Marketplace generator by direct path.** Same shape: the running (cached) generator carried the stale template, so the sanctioned path could not propagate the change. The generator's own docstring sanctions direct invocation for exactly this bootstrap — the two rules contradict, and the agent followed the one that worked.
5. **Direct `.venv` pytest for targeted suites.** Same shape again: the wrapper had no file/node filter passthrough, so the legitimate need (fast targeted signal) had no sanctioned form.
6. **Partial self-audit after the explicit "revisit the workflow" nudge.** A prose instruction produced prose compliance. Nudge handling pattern-matched to the named symptom both times.

Deviations 3–5 share one root cause: **the compliant path did not cover the use case**. Deviations 1–2 share another: **the guard ran late or not at all**. Deviation 6 is the meta-case: unstructured instructions produce unstructured compliance.

### Proposals (prioritized by leverage)

**P0 — Phase-completion artifact gates in `manage-status transition` (closes deviation 2).**
Refuse `--completed 3-outline` unless `solution_outline.md` validates; refuse `--completed 4-plan` unless ≥1 task file exists or the manifest is composed; refuse `--completed 2-refine` unless the clarified/confidence record exists. This is the highest-leverage single change: it makes phase-skipping structurally impossible rather than auditable-after-the-fact, and it would have forced the outline into existence *before* implementation instead of as a post-landing retrofit. Required carve-out: explicit exemption metadata (e.g. a deliberate `*_exempt` field with reason, set only through its own verb) for legitimately artifact-free phases (analysis-only plans, recipe-routed shortcuts) — otherwise the gate false-blocks exotic-but-valid plans. Cost: small, localized to `cmd_transition` plus tests. Risk: exemption creep — mitigate by making exemptions decision-logged and visible in retrospectives.

**P1 — Recurring worktree-materialization assertion (closes deviation 1).**
Two halves. (a) `prepare_execute` persists a `worktree_materialized` flag (verified absent today — only path/branch are stored, so nothing records THAT Step 2.5 ran). (b) Every phase-5 task dispatch and every Bucket-B invocation with `use_worktree=true` refuses while the flag is unset. Honest scope statement: no script gate can bind a free agent's Edit tool — an agent that bypasses dispatch entirely is outside mechanism reach, exactly as happened here. So pair the gate with detection: extend the post-refine main-checkout-clean assertion to EVERY phase boundary 1→2→3→4→5 (today it runs once, post-2-refine). Phases 1–4 must leave main clean by construction; any main dirt at those boundaries is an immediate, attributable contract violation instead of a discovery at the 5→6 gate. Cost: small. Residual: free-agent edits during phase-5 on main remain mechanism-unreachable — stated, not solved.

**P2 — Sanctioned read path for orchestrator specs (closes deviation 3).**
Add a read verb to the orchestrator surface (e.g. `corpus read --slug --plan PLAN-NN` returning the staged spec body), giving the "implement this spec" hand-off a compliant read path. Rules that cannot be followed will not be followed; this one is cheap to eliminate. Cost: one read-only verb plus tests. Until it lands, record the carve-out explicitly in AGENTS.md rather than leaving agents to rediscover the contradiction.

**P3 — Align the direct-path rules and make template staleness detectable (closes deviation 4).**
Two parts. (a) Write the generator-bootstrap exception into AGENTS.md/CLAUDE.md as the bounded exception it already de facto is (fresh clone / template change with a stale cached generator), instead of an absolute "never by direct path" that contradicts the generator's own docstring. (b) Extend the `preflight` staleness check beyond version comparison to template-content comparison, so a stale cached generator is *detected* rather than silently run. Cost: small. This removes an entire class of "which rule do I follow" forks.

**P4 — Targeted execution through the wrapper (closes deviation 5).**
Add file/node filter passthrough to the `module-tests` wrapper invocation (e.g. `--command-args "module-tests plan-marshall --filter <path>"` or equivalent), so the fast-targeted-signal use case has a sanctioned form. Same principle as P2/P3: every legitimate need without a sanctioned path becomes a violation statistic. Cost: small wrapper change.

**P5 — Structured deviation-audit form (closes deviation 6).**
Replace the prose "revisit the workflow" with a fixed checklist artifact the agent must produce: per-phase required artifacts present/absent, working-tree vs plan-tree reconciliation, script-vs-direct invocation inventory for the session, open exemptions with reasons. A partial audit is then *structurally* incomplete (missing checklist rows) rather than merely lazy prose — the same fail-closed philosophy as the script guards, applied to the one surface scripts cannot reach: the agent's own self-review. Cost: a template plus a convention; enforcement is by the reviewing operator/epic, not by code — state that plainly.

### What NOT to change

- **The fail-closed boundary guards.** Dirty-tree transition block, `pr_title` capture requirement, manifest-required abort, freshness `stale` refusal, foreign-gate STOP, barrier UNKNOWN handling — every one fired correctly, including against its own author. They are the reason the run converged instead of shipping silently broken. Extend them (P0/P1); do not soften them.
- **The loop-back machinery.** Triage → fix tasks → fix commit → re-review → re-verify converged the CodeRabbit cycle without operator intervention. It worked as designed under the mandatory-review mandate.
- **Metrics gap flags.** The `no end_time` WARN and floor totals recorded the collapsed phases honestly. Backfilling boundaries post-hoc would have falsified the record; the flags are the correct output for a deviated run. No change.

### Cost asymmetry worth staging explicitly

Doing it in order costs the phase artifacts up front. The deviated path cost: one relocation (snapshot patch + worktree materialization + executor regen), one manifest composition, one outline reconstruction, one foreign-gate STOP plus retrofit, plus unpriced risks (main-checkout collision with the concurrent worker's surface, an orphaned merge-mutex state, a landing INCOMPLETE at two keys). Any epic-level prioritization of P0/P1 should carry these two totals side by side — the process overhead is the cheaper figure in every instance observed here.
