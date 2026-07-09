# Effort Variants — Resolver Contract & Spec

> Precise resolution rules, environment-variable override semantics, and build-time guards for the per-role model variant system. Audience: skill authors writing dispatch sites, and maintainers debugging the resolver.

## What the System Resolves

Every plan-marshall `Task:` dispatch routes through the single role-eligible canonical agent `plan-marshall:execution-context`. The build target emits eight entries per role-eligible canonical (one canonical + seven suffixed level variants). The resolver chooses which entry the dispatch calls, based on the caller's `--phase` (and optional `--role <subkey>`) plus the project's `marshal.json` configuration.

Inputs: `--phase phase-N-{suffix}` (always required); `--role <subkey>` (optional). Output: a target name — either `execution-context` (the canonical, when the resolved level is `inherit`) or `execution-context-{level}` (one of the seven suffixed variants).

## Resolution Order (Authoritative)

For a dispatch with `--phase phase-N-{suffix} [--role <subkey>]`, the resolver returns the first match in this order:

1. **Explicit per-sub-key override** — `plan.phase-N-{suffix}.effort.<subkey>`, when the phase's `effort` value is an object and the sub-key is present.
2. **Phase `default` slot** — `plan.phase-N-{suffix}.effort.default`, when `effort` is an object and the sub-key is unset or unspecified.
3. **Phase plain-string `effort`** — `plan.phase-N-{suffix}.effort` when it is a string, applied to every workflow under that phase.
4. **Plan-wide `effort`** — `plan.effort` (string).
5. **Implicit fallback** — `inherit` (the canonical no-suffix variant; the dispatched subagent inherits the parent session's model).

`--default` (no `--phase`, no `--role`) short-circuits to step 4. This is the resolution path standalone `/research` outside any plan takes.

## Accepted Lookup Forms

All four forms produce the same resolution:

```bash
manage-config effort resolve-target --phase phase-2-refine                                  # bare group
manage-config effort resolve-target --role phase-6-finalize.verification-feedback           # dotted single-arg
manage-config effort resolve-target --phase phase-6-finalize --role verification-feedback   # two-flag
manage-config effort resolve-target --default                                               # zero-role fallback
```

The dotted form (`phase-N-{suffix}.<subkey>`) and the two-flag form are equivalent and validated identically.

## Polymorphic `effort` Field

The `plan.<phase>.effort` field accepts polymorphic JSON:

- **String** — applies the level to every workflow under the phase. Equivalent to an object with that level under every recognised sub-key.
- **Object** — sets per-sub-key overrides plus an optional `default` slot. Sub-keys not present fall through to `default`, then to `plan.effort`, then to `inherit`.

Sub-key whitelist per phase (validated at wizard save time; unknown keys are accepted by the resolver as a warning but produce noise in audit logs):

| Group | Whitelisted sub-keys |
|-------|----------------------|
| `phase-2-refine` … `phase-4-plan` | `default`, `research` |
| `phase-5-execute` | `default`, `verification-feedback`, `research` |
| `phase-6-finalize` | `default`, `verification-feedback`, `post-run-review`, `research` |

The plan-wide `plan.effort` is a single string.

## Validation

| Condition | Behaviour |
|-----------|-----------|
| Configured value is one of `level-1`, `level-2`, `level-3`, `level-4`, `level-5`, `level-6`, `level-7`, `inherit` | Accepted on read; refused at wizard save with a remediation message. |
| Configured value is anything else | Hard error on read with the offending key path; refused at wizard save. |
| Role key is not in the phase's sub-key whitelist | Warning (not error): unknown keys resolve via fallback (`default` → `effort` → `plan.effort` → `inherit`) so registry renames do not break saved configs. Audit log records the unknown key. |

## Build-Time Alias-Capability Guard

The two top tiers resolve to alias-capability-gated efforts: `level-6` resolves to `(opus, xhigh)` and `level-7` resolves to `(fable, max)`. The target's build-time emitter inspects the canonical agent's resolved alias capability flags and refuses to emit the `execution-context-level-6.md` / `execution-context-level-7.md` variant when the resolved alias does not advertise the level's effort (`xhigh` / `max`) support. The emitter logs a build-time warning naming the canonical and the missing capability.

At runtime: a dispatch site whose resolver returns `execution-context-level-6` / `execution-context-level-7` against a target where the variant was skipped will fail with `Agent type not found` from Claude Code's plugin loader. The resolver does not know the emitter skipped a variant — the contract is one-way (build → registry). Operators see this only via build logs.

## Environment-Variable Override

`CLAUDE_CODE_SUBAGENT_MODEL`, when set at Claude Code session start, overrides every subagent's pinned `model:` declaration (per code.claude.com agent docs). This takes effect **above** the resolver: the variant is still selected per `marshal.json`, but Claude Code substitutes the env var's model on subagent launch. To restore variant-pinned behaviour:

```bash
unset CLAUDE_CODE_SUBAGENT_MODEL
```

Restart Claude Code. The override is session-level, not dispatch-level — the resolver cannot work around it.

## No-Restart Semantics

The resolver reads `marshal.json` fresh on every dispatch via `manage-config effort resolve-target`. An `effort` edit takes effect on the **next** dispatch — no Claude Code restart, no plugin reinstall, no target regeneration required. The eight emitted variants are static; only which variant the resolver selects changes.

A restart **is** required when `target/claude/` is regenerated (e.g., when the variant frontmatter changes shape, when a new role-eligible canonical is added, or when the alias-capability build guard's emission decision changes). That is a meta-project / contributor flow, not a user-side flow.

## Cross-References

| Document | Content |
|----------|---------|
| [`effort-levels.md`](effort-levels.md) | Level → `(model, effort)` primitive binding. The alias-capability guard for `level-6` / `level-7` is specified there. |
| [`effort-roles.md`](effort-roles.md) | Role registry — phase-scoped sub-keys, the workflow doc each binds to, dispatch-site usage. |
| [`ext-point-dynamic-level-executor.md`](../../extension-api/standards/ext-point-dynamic-level-executor.md) | Variant-emission contract — what the build target produces from each role-eligible canonical. |
| [`ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md) | Workflow-doc contract — what the dispatched `execution-context` agent executes. |
| `marshall-steward/standards/effort-menu.md` | Wizard preset-picker UX contract. |
