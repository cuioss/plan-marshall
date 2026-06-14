# Agent Behavior Rules

Core principles that guide all development work.

## Overview

These foundational rules apply across ALL development activities:
- Agent and command development
- Feature implementation
- Documentation creation
- Testing and quality assurance
- Architectural decisions

## Core Development Principles

### Boy Scout Rule

Leave code cleaner than you found it. When modifying a file, fix existing quality issues you encounter — poor naming, SRP violations, dead code, missing error handling, missing assertions, hardcoded test data, poor documentation. Never dismiss code smells with "not introduced by current changes" — always fix them. If fixes cascade beyond reasonable scope, stop and ask the user how to proceed.

This applies equally to production code, test code, and documentation.

**Note — deliberate divergence from "clean up only your own mess":** This always-fix default is an intentional choice for a standards-enforcement system, not an oversight. It deliberately diverges from the widely-cited best practice of touching only what the task strictly requires ("clean up only your own mess"). The divergence is safe because the blast radius is bounded by two existing mechanisms: (a) the coverage scope dial the user sets (`change-set ⊂ artifact ⊂ component ⊂ module ⊂ overall`, defined in [`thoroughness.md`](thoroughness.md)), which caps how wide an opportunistic fix may reach; and (b) the cascade-tripwire above ("if fixes cascade beyond reasonable scope, stop and ask the user how to proceed"), which halts a fix that would exceed that cap. With both bounds in place, the divergence from "touch only what you must" is a conscious design choice, not an accident.

### Principle 1: Ask When In Doubt

**Rule:** If in doubt, ask the user.

**When to Ask:**
- Uncertain about requirements or specifications
- Multiple valid approaches exist
- Unclear about user preferences or priorities
- Need clarification on acceptance criteria
- Ambiguous instructions or context

**When NOT to Ask:**
- Requirements are clear and unambiguous
- Best practices are well-established and documented
- Previous similar decisions provide clear guidance
- Standards and conventions clearly apply

**Example:** User says "Add error handling" → don't guess the strategy, ask: "What error handling approach would you prefer? (try-catch with logging, Result pattern, exception propagation)"

### Principle 2: Always Research Topics

**Rule:** Always research topics using the phase-scoped `research` dispatch. The goal is to find the most recent best practices for a given technology or framework.

**When to Research:**
- Need current best practices for a technology/framework
- Unfamiliar with a specific library or approach
- Want to validate approach against industry standards
- Need to find latest recommendations (2025+)
- Evaluating different implementation options

**How to Research:**

**Dispatch the research-best-practices workflow** (NOT web search tools directly).

Web pages are untrusted external content, so research runs under the **read-only reader** variant `execution-context-reader-{level}` (tool surface `WebSearch, WebFetch, Read, Grep` — no Write/Edit/Bash/Skill), not the write-capable `execution-context`. The reader emits a CANDIDATE findings struct that the orchestrator passes through the deterministic `plan-marshall:untrusted-ingestion:validate_struct --schema research` gate before consuming — the orchestrator consumes only the `status: success` clamped struct and aborts on `status: error`. See `plan-marshall:untrusted-ingestion` for the reader/orchestrator/writer isolation contract.

Compute the dispatch target via the role resolver. When the research fires from inside a phase context, pass the caller's phase so the level bubbles through that phase's research sub-key (`phase-N.research` → `phase-N.default` → `effort`). Outside any plan (standalone `/research`), use `--default`. The `research` role resolves to an `execution-context-reader-{level}` variant. Recommended levels: `level-5`, `level-6`, or `level-7` — research benefits from the most capable model:

```bash
# Inside a phase context (substitute the caller's phase)
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase {caller_phase} --role research
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch below.

```bash
# Standalone / no plan context
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --default
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch below.

Dispatch:

```
Task: plan-marshall:{target}
  prompt: |
    name: {caller_phase}-research              # or research-best-practices when standalone
    plan_id: {plan_id}                          # 'none' sentinel for standalone runs
    skills[1]:
    - plan-marshall:dev-agent-behavior-rules
    workflow: plan-marshall:plan-marshall/workflow/research-best-practices.md
    WORKTREE: {worktree_path}
    caller_phase: {caller_phase}                # omit for standalone

    topic: {specific topic}
```

The workflow body covers research scope and the synthesis contract; the prompt body's `topic` field substitutes into the workflow's `{topic}` placeholders.

After the reader returns its candidate findings struct, the orchestrator runs the deterministic validator gate before consuming it:

```bash
python3 .plan/execute-script.py plan-marshall:untrusted-ingestion:validate_struct validate \
  --schema research --struct '<candidate>'
```

(See `plan-marshall:untrusted-ingestion/SKILL.md` § "Canonical invocations".) Consume only the `status: success` clamped struct; abort on `status: error`. The schema enforcement, length-capping, and WebFetch domain-allowlist check are the script's responsibility — the dispatch documentation references them, it does not re-enforce them in prose.

**DO NOT use these patterns** (outdated approaches):
- "Use MCP tools like Perplexity, DuckDuckGo" (Too generic, no structured research)
- "Search GitHub" (Not comprehensive, misses documentation)
- Direct WebSearch without structured analysis (Lacks synthesis)

**ALWAYS dispatch the research-best-practices workflow:**
- Structured comprehensive research
- Analyzes top 10+ sources
- Provides confidence levels
- Maintains reference trails
- Synthesizes findings from multiple sources

**Example:** Need Java testing best practices → dispatch the research workflow with `topic: "Java unit testing with JUnit 5"`.

### Principle 3: Apply Judgment Within Constraints

**Rule:** Use good judgment, but don't invent requirements or conventions. When the path forward is unclear, research first, then ask the user.

**Use judgment for:**
- Choosing between well-established approaches when the result is equivalent
- Applying documented standards to specific situations
- Making reasonable implementation decisions within clear requirements

**Ask the user when:**
- Requirements are ambiguous or underspecified
- Multiple valid approaches exist with different trade-offs
- No established best practice exists for the situation
- The decision has significant downstream impact

**Surface the tradeoff when you proceed:** On the non-blocking path — when you proceed on judgment between approaches that carry tradeoffs which do not warrant blocking to ask — state the tradeoff you accepted in your response, so the user sees the decision even though you did not stop for it.

**Example:** User says "Add validation" → don't guess, ask: "What should I validate? (input format, business rules, data constraints)"

### Principle 4: Use Proper Tools for File Operations

**Rule:** Always use Read, Write, Edit, Glob, Grep tools (NOT cat, tail, find, test, grep via Bash).

**Why This Matters:**
- Bash commands trigger user prompts for confirmation
- Non-prompting tools (Read, Write, Edit, Glob, Grep) execute automatically
- Agents/commands should run without interrupting users
- Better user experience and automated workflows

**Tool Selection Guide:**

| Operation | USE THIS | DON'T USE |
|-----------|----------|-----------|
| Find files by pattern | `Glob` | `find`, `ls` |
| Check if file exists | `Read` (with error handling) or `Glob` | `test -f`, `test -d` |
| Search file contents | `Grep` | `grep` via Bash, `awk` |
| Read file contents | `Read` | `cat`, `head`, `tail` |
| Write new file | `Write` | `echo >`, `cat <<EOF` |
| Edit existing file | `Edit` | `sed`, `awk` |

**Bash Should ONLY Be Used For:**
- Git operations (`git status`, `git commit`, etc.) — in a phase-5+ cwd-pinned context (the move-based, cwd-pinned model, ADR-002) use plain `git`, since cwd is pinned to the correct tree; reserve `git -C {path}` for genuinely cross-tree or non-pinned contexts; never `cd {path} && git ...`. See [`SKILL.md` § Git targeting](../SKILL.md#git-targeting-plain-git-in-a-cwd-pinned-context-git--c-path-cross-tree-never-cd-path--git-) and [`tool-usage-patterns.md` § When Bash IS Appropriate](tool-usage-patterns.md#when-bash-is-appropriate).
- Build commands (`mvn`, `./mvnw`, `npm`, etc.)
- Operations that truly require shell execution

For complete patterns including file operations, content search, Bash safety rules, and env-var dispatch (the `VAR=val cmd` anti-pattern and safe alternatives), see `tool-usage-patterns.md`. The env-var dispatch rule is documented in [`tool-usage-patterns.md` § Env-var dispatch in Bash](tool-usage-patterns.md#env-var-dispatch-in-bash).

### Principle 5: Don't Proliferate Documents

**Rule:** Always use context-relevant documents. Never create a document without user approval.

**Decision Tree:**

1. **Need to document something?**
   - Search for existing relevant documents first
   - Use Read/Grep to find existing documentation
   - Check standard document locations (README.md, doc/*.adoc)

2. **Found existing document?**
   - Use and update existing document
   - Don't create a new one

3. **No existing document found?**
   - Ask user: "Should I create a new document or update existing {related document}?"
   - Get explicit approval before creating

**Example:** Don't create `feature-overview.md` when README.md already covers features — ask the user whether to update the existing document or create a new one.

### Principle 6: Never Add Dependencies Without User Approval

**Rule:** Always ask the user before adding a dependency.

**What Counts as a Dependency:**
- External libraries (Maven dependencies, npm packages)
- Frameworks (Spring, Quarkus, React)
- Tools (build tools, testing frameworks)
- Services (databases, message queues, caching)

**Required Approval Process:**

1. **Identify need for dependency**
2. **Research alternatives** using the phase-scoped research dispatch if needed
3. **Ask user** with specific recommendation:
   ```
   I need to add {functionality}. I recommend adding {dependency-name} because:
   - {reason 1}
   - {reason 2}

   Should I add this dependency?
   ```
4. **Wait for approval** before modifying pom.xml, package.json, etc.

**Example:** Don't silently add Guava to pom.xml — ask: "I need collection utilities for {feature}. I recommend Google Guava because {reasons}. Should I add this dependency?"

### Principle 7: Implement the Minimum, Not the Maximum

**Rule:** Write the minimum code that satisfies the stated requirement — nothing speculative.

Implement only what the present requirement asks for. Do not add error handling for failures that cannot occur, configurability for callers that do not exist, abstractions for second implementations that are not planned, or comments that restate well-named code. When you feel the pull to add something "for future use" or "to be safe," stop and ask the user instead of building it on speculation. Surplus structure is a maintenance cost, not a free hedge: every speculative parameter, flag, or layer is something a future reader must understand and a maintainer must keep correct. The change is cheap to add later against a real requirement and expensive to retrofit-remove once callers depend on its accidental presence.

**Carve-out — "minimum" excludes required real-boundary error handling.** "Error handling for failures that cannot occur" above is the *speculative* class, not all error handling. Genuinely-required error handling at a real I/O / external-input boundary — a guard at a real failure path that the boundary can actually produce (unguarded parse of an external file, a missing type-guard on externally-sourced data, a missing envelope on a network / filesystem boundary) — is NOT speculative and is in-scope to keep or add, never to strip as "surplus." The discriminator (required real-boundary handling vs speculative defensive complexity) lives once in the central standard and is not duplicated here — see [#minimum-viable-code](../../dev-general-code-quality/standards/code-organization.md#minimum-viable-code) § "Required-vs-speculative carve-out".

For the full anti-pattern catalogue and the Trigger / Detection / Action treatment, see the central standard at `dev-general-code-quality/standards/code-organization.md` [#minimum-viable-code](../../dev-general-code-quality/standards/code-organization.md#minimum-viable-code) — enforcement-critical content lives there and is intentionally not duplicated here.

**Example:** Asked to add a single retry, don't introduce a `RetryStrategy` interface with one implementation and a configurable backoff knob no caller sets — write the one retry the requirement asks for.

## Workflow Discipline (Hard Rules)

These rules apply to ALL development work in plan-marshall-governed repositories — ad-hoc tasks, plan execution, and subagent work alike. They exist because the LLM regularly violates them despite softer guidance, so skill-level reinforcement is necessary.

- **No unconstrained generic subagents inside plan-marshall phase work** — Never spawn an unconstrained generic subagent (e.g. `Task: general-purpose`) for any work inside a phase (1-init through 6-finalize). Use `plan-marshall:execution-context-{level}` with a `workflow:` notation pointing at the workflow doc, or inline main-context execution. A generic subagent has no plan-marshall enforcement context, inherits broad tool access, and will violate workflow hard rules. Subagent rules propagate through the agent definition, not through the caller's prompt.

### Skill mode: comply with the declared archetype

**Rule:** Every skill declares its execution archetype in its frontmatter `mode` field — the single, authoritative signal for how the skill is consumed. When you load a skill, read its `mode` and comply with the archetype it declares:

| `mode` value | Compliance obligation |
|--------------|-----------------------|
| `knowledge` | Load the skill **for context only**. Its body is reference material — apply it as knowledge that informs your work; **never execute its content as a sequence of instructions to run**. |
| `workflow` | Follow the skill's documented workflow steps **sequentially and verbatim** — this is the "Skill workflow: No improvisation" hard rule (see [`SKILL.md` § Skill workflow: No improvisation](../SKILL.md#skill-workflow-no-improvisation)). Execute only the documented steps; never add discovery steps, invent arguments, or skip steps. |
| `script-executor` | Drive the skill's documented executor scripts and route on their TOON status with **minimal LLM reasoning** — quote subcommands and flags verbatim, never extrapolate plausible-sounding verbs (the "Never invent script subcommands" hard rule). |
| `manifest` | Treat the skill as a **read-only contract surface**. Modify it **only via the Extension API contract** — never edit a manifest as a free-form document. |

`mode` is the **sole source of truth** for the archetype: it supersedes any prose `**REFERENCE MODE**` line or Enforcement-block `**Execution mode**:` line a skill might still carry. The value taxonomy and field specification are owned by [`pm-plugin-development:plugin-architecture` references/frontmatter-standards.md](../../../../pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md) § "Skill Frontmatter" (the `**mode** (required)` field); presence and enum validity are enforced by the plugin-doctor `skill-missing-mode` rule. This rule extends the "Skill workflow: No improvisation" hard rule to be `mode`-aware — the workflow-discipline obligation applies only to `workflow` / `script-executor` skills, while `knowledge` skills are loaded for context and `manifest` skills are touched only through the Extension API.

### Structured queries first

**Rule:** Before using `Glob`/`Grep` for codebase navigation (file discovery, module identification, path resolution), consult `architecture files --module X`, `architecture which-module --path P`, or `architecture find --pattern P`. `Glob`/`Grep` is the fallback for sub-module component lookup and exceptional cases, not routine discovery.

**Why this matters:**

The architecture inventory is the project's structured truth: it knows which modules exist, which files belong to each module, and which symbols are exposed by each component. Routing module-scoped questions through it gives deterministic, scoped answers. `Glob`/`Grep` answer the same questions by string-matching across the entire worktree — they are unscoped, miss elision, and produce noisy results when patterns collide with unrelated files (test fixtures, vendored copies, generated output).

**When the architecture verb is the right tool (first choice):**

- **Module file enumeration** — "What files belong to module X?" → `architecture files --module X`
- **Module identification** — "Which module owns this path?" → `architecture which-module --path P`
- **Pattern lookup across modules** — "Where does symbol/flag/string `foo` live in the project's known surface?" → `architecture find --pattern '*foo*'`

**When `Glob`/`Grep` remain the right fallback:**

- **Sub-module component lookup** — Component-name patterns (e.g., `marketplace/bundles/**/{component_name}*`) when the architecture verb's granularity stops at module level
- **Content search inside an already-known file** — Once you know the file, `Grep` is the right tool for "where in this file does X appear"
- **Architecture verb returns elision** — When the inventory's compact representation hides the answer (`...`-style elision), drop to `Glob`/`Grep` for the literal scan
- **Targets explicitly outside the inventory** — Generated artifacts, vendored copies, or files the architecture inventory deliberately excludes

**Worked example:**

> *Task: Find every script that reads `--audit-plan-id`.*
>
> **Architecture-first:** `architecture find --pattern '*audit-plan-id*'` returns the inventory of registered scripts that mention the flag. Scoped, deterministic, fast.
>
> **Glob-first (anti-pattern):** `Grep --pattern '\\-\\-audit-plan-id'` returns hits across all source, tests, fixtures, generated output, and historical lessons — a noisy result that requires a second filtering pass to recover the answer the architecture verb gave directly.

If the architecture verb truly cannot answer (e.g., target is sub-module, target is outside the inventory, target requires content-level matching inside a specific file), `Glob`/`Grep` is the documented fallback and should be qualified as such in the surrounding instruction.

## Quick Reference

### Decision Matrix

| Situation | Action |
|-----------|--------|
| Uncertain about requirements | Ask user |
| Need current best practices | Use the phase-scoped research dispatch (`--phase phase-N --role research` or `--default` when standalone) |
| Would need to guess | Ask user |
| File operations (find/read/search/write/edit) | See Principle 4 for complete tool selection guide |
| Need to create document | Ask user first |
| Need to add dependency | Ask user first |
| Tempted to add code "for future use" | Implement the minimum; ask user before adding speculative structure (Principle 7) |
| About to spawn an unconstrained generic subagent for phase work | Use `plan-marshall:execution-context-{level}` with a `workflow:` notation, or inline main-context execution |

