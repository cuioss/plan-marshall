envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=finding
created=2026-10-12T12:52:00Z

# [HIGH][Antigravity] Instrumentation failed to enforce quality build: CLAUDE.md unread, per-task quality-gate dropped, and ad-hoc plugin permitted

- Component: plan-marshall:platform-runtime (AGENTS.md / CLAUDE.md parity), plan-marshall:phase-4-plan (task verification commands), plan-marshall:phase-5-execute (per-task quality sweep enforcement), plan-marshall:build-maven (plugin guard), plan-marshall-antigravity-target-rules
- Category: bug

## What happened

During PLAN-41, the agent failed to use the repository's instructed quality build (`verify -Ppre-commit`) during task execution, improvised an unauthorized formatter (`spotless`), and pushed commits that bypassed the pre-commit gate. An analysis of the end-to-end instrumentation reveals five cascading failures across rules delivery, planning, execution, tool wrappers, and finalization:

1. **Workspace Instruction Delivery Failure (`CLAUDE.md` ignored):**
   The repository's build instructions and prohibitions are declared in `CLAUDE.md` (e.g., `Quality gate: verify -Ppre-commit`, "Never add a dependency or a plugin without asking the user first", "Never hard-code a build tool command").
   Antigravity discovers and auto-loads only `GEMINI.md`, `AGENTS.md`, and `.agents/rules/*.md`. Because this repository only has `CLAUDE.md` and the installer/steward created no `AGENTS.md` bridge or symlink, the agent executed with zero awareness of the repository's standing build rules and constraints.

2. **Planning Verification Command Omission (`phase-4-plan`):**
   When `phase-4-plan` generated `TASK-001.json` through `TASK-008.json`, the task generator populated `verification.commands` with bare scoped commands (`test-compile -pl pm-workflow -am` and `test -pl pm-workflow -am`), completely omitting the project's canonical `quality-gate` command. Tasks instructed only unit compilation and testing, giving the executor no task-level mandate to run the quality build.

3. **Execution Manifest `per_task` Tier Dropped (`phase-5-execute`):**
   Although `execution.toon` explicitly stamped `step_execution_tier: "verify:quality-gate",per_task`, `phase-5-execute` under Antigravity ran tasks inline without subagent delegation and completely dropped the per-task / per-deliverable (Step 10b) quality sweep. `verify:quality-gate` was executed only once across the entire phase at 08:30Z (`maven-2026-10-12-083052.log`).

4. **Hallucination Instead of Architecture Resolution & Build Tool Pass-Through:**
   At step 2544, the agent sensed a need to format its changes before completing tasks. Because `CLAUDE.md` was unread and `plan-marshall-antigravity-target-rules` contained no rule requiring command resolution for formatting, the agent guessed `spotless:apply`. When that failed (`No plugin found for prefix 'spotless'`), the agent bypassed Maven prefix resolution with the fully qualified coordinate `com.diffplug.spotless:spotless-maven-plugin:apply`. The `build-maven` script accepted this arbitrary goal, allowing Maven to download Spotless from Maven Central and commit foreign formatting.

5. **Finalize Pre-Push Gate Staleness (`phase-6-finalize`):**
   `pre-push-quality-gate` at 08:43Z only executed whole-tree `test-compile` (`maven-2026-10-12-084318.log`), not `verify -Ppre-commit`. Subsequent commits (Spotless formatting at 08:35Z, Sonar S1192 constant fixes at 09:02Z, new tests at 11:05Z, and inline review fixes at 11:37Z) advanced HEAD without ever re-running the project's pre-commit quality gate.

## Why it matters

- The quality gate (`verify -Ppre-commit`) is the repository's sole authority for OpenRewrite auto-formatting, license headers, Javadoc checks, and enforcer rules.
- Without automatic bridge/aliasing from `CLAUDE.md` to `AGENTS.md` under Antigravity, all repository-specific developer instructions, forbidden actions, and canonical commands are silently invisible to the assistant.
- When task-level verification commands omit the quality build and the harness does not enforce the manifest's declared `per_task` tier, agents default to narrow unit tests and improvise unauthorized formatting tools when they feel code style is needed.
- Permitting arbitrary plugin coordinates in `build-maven:maven run` undermines repository supply chain boundaries (`.mvn/rrf`) and allows agents to run unapproved tools from Maven Central.

## Suggested direction

- **Rule Delivery Parity:** Update `marshall-steward` / `dist-antigravity` installer / `platform-runtime` to ensure `CLAUDE.md` is automatically linked or mirrored to `AGENTS.md` (or `.agents/rules/project-instructions.md`) when running under Antigravity.
- **Canonical Command Resolution Invariant:** Add an explicit constraint in `plan-marshall-antigravity-target-rules`: "Never invent, guess, or execute unconfigured build plugins or goals (e.g., spotless). Always query `architecture resolve --command quality-gate` (or compile/verify) to obtain canonical commands."
- **Task Verification Synthesis:** In `phase-4-plan`, when `step_execution_tier` declares `per_task` for `quality-gate`, ensure the module-scoped canonical `quality-gate` command is synthesized into `TASK-*.json` verification commands, or make Step 10b per-deliverable quality builds strictly enforced.
- **Build Plugin Guard in `build-maven`:** Refuse execution in `build-maven:maven run` for plugin goals whose plugin is not declared in the project's effective POM or registered canonical commands.
- **Pre-Push Gate Freshness:** Require `pre-push-quality-gate` to re-verify against `quality-gate` whenever source-modifying commits have landed since the last successful quality build.

- Priority: **HIGH** (operator decision 2026-10-12: Antigravity issues are filed directly as high priority)
- Platform: Antigravity — first plan of epic pm-mcp-core-m2-m4 run under it
- Plan: `plan-41-static-verifier-remaining-rules` (PLAN-41), pm-mcp-core PR #34, merge commit ebe82b3
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-41-static-verifier-remaining-rules/` (logs/, metrics.md, execution.toon, build-results/)
- Origin: filed from analysis of user question and conversation transcript on PLAN-41
