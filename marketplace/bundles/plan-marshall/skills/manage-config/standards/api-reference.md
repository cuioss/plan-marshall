# API Reference

Complete noun-verb API for manage-config.

## Execution Pattern

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  {noun} {verb} [--param value]
```

## Noun: skill-domains

Manage implementation skill defaults and optionals per domain.

| Verb | Parameters | Description |
|------|-----------|-------------|
| `list` | -- | List all configured domains |
| `get` | `--domain` | Get full domain configuration (defaults + optionals) |
| `get-defaults` | `--domain` | Get default skills for a domain |
| `get-optionals` | `--domain` | Get optional skills for a domain |
| `set` | `--domain`, `--defaults`, `--optionals`, optional `--profile` | Update domain configuration |
| `add` | `--domain`, `--defaults` | Add a new domain |
| `validate` | `--domain`, `--skill` | Check if a skill is valid for a domain |
| `detect` | -- | Auto-detect domains from project files |
| `get-extensions` | `--domain` | Get workflow skill extensions for a domain |
| `set-extensions` | `--domain`, `--type`, `--skill` | Set a workflow skill extension |
| `get-available` | -- | Get available domains based on detected build systems |
| `configure` | `--domains` | Configure selected domains with templates |

### Example: set (profile-based)

```bash
manage-config skill-domains set \
  --domain java \
  --profile implementation \
  --defaults "pm-dev-java:java-core" \
  --optionals "pm-dev-java:java-cdi,pm-dev-java:java-maintenance"
```

### Example: validate

```bash
manage-config skill-domains validate \
  --domain java \
  --skill pm-dev-java:java-lombok
```

Output includes `valid`, `in_defaults`, and `in_optionals` booleans.

### Extension Types

Used by `get-extensions` and `set-extensions`:

- `outline` - Domain-specific patterns for solution-outline phase
- `triage` - Domain-specific finding decision logic for plan-finalize phase

### configure Notes

- Always configures the `system` domain with execute_task_skills
- Applies domain templates for each selected domain
- Collects verify steps from domain extensions via `provides_verify_steps()`

---

## Standalone Commands (Skill Resolution)

| Command | Parameters | Description |
|---------|-----------|-------------|
| `resolve-workflow-skill-extension` | `--domain`, `--type` | Resolve domain-specific workflow skill extension (returns `null` if not found) |
| `resolve-domain-skills` | `--domain`, `--profile` | Resolve all skills for domain + profile (core + profile skills) |
| `get-skills-by-profile` | `--domain` | Get skills organized by profile for a domain |
| `configure-execute-task-skills` | -- | Auto-discover profiles and register execute-task skills |
| `resolve-execute-task-skill` | `--profile` | Resolve execute-task skill for a profile |

### Profiles

Used by `resolve-domain-skills` and `resolve-execute-task-skill`: `implementation`, `module_testing`, `integration_testing`, `quality`

### Example: resolve-domain-skills

```bash
manage-config resolve-domain-skills \
  --domain java --profile implementation
```

Returns `defaults` and `optionals` arrays with skill references and descriptions.

### Example: configure-execute-task-skills

```bash
manage-config configure-execute-task-skills
```

Convention: profile X maps to skill `plan-marshall:execute-task-X`.

### resolve-workflow-skill-extension Notes

Returns `extension: null` (not error) when no extension exists for the domain/type combination.

---

## Noun: system

Manage system-level settings.

| Verb | Parameters | Description |
|------|-----------|-------------|
| `retention get` | -- | Get all retention settings |
| `retention set` | `--field`, `--value` | Set a retention field |

### Example: retention set

```bash
manage-config system retention set \
  --field logs_days \
  --value 7
```

Retention fields: `logs_days`, `archived_plans_days`, `temp_on_maintenance`.

---

## Noun: project

Manage project-level, cross-phase, cross-plan settings stored under the
`project.*` block in marshal.json. `marshal.json` is the source of truth;
`constants.py` holds only the fail-closed fallback consulted when a key is
absent or unreadable.

| Verb | Parameters | Description |
|------|-----------|-------------|
| `get` | `--field` | Get a project field. Falls back to the canonical default (from `DEFAULT_PROJECT`) when the key is absent from the live `project` block. |
| `set` | `--field`, `--value` | Set a project field. Scalar fields are coerced (bool/int/str); the list-valued JSON field `working_prefixes` takes a JSON array value that round-trips through `get`. |

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_base_branch` | string | `main` | Project's canonical base branch; seeds `references.base_branch` at plan init. |
| `working_prefixes` | list[string] | `["feature/", "fix/", "chore/"]` | The closed set of allowed working-branch prefixes for plan feature branches (e.g. `feature/`), enforced by the branch-prefix validation in `marshall-steward`. A structural test (`test_branch_prefix_allowlist.py`) asserts every prefix is covered by a `.github/workflows/python-verify.yml` push trigger, so a dropped prefix that would make a PR unmergeable fails CI. The `docs/` prefix is explicitly retired and absent. |

### Example: get working_prefixes

```bash
manage-config project get --field working_prefixes
```

Returns the live list, or the default list (implicit-default fallback) when
the key is absent from marshal.json.

### Example: set working_prefixes

```bash
manage-config project set --field working_prefixes \
  --value '["feature/", "fix/", "chore/", "spike/"]'
```

The JSON array round-trips through `get`.

---

## Noun: plan

Manage phase-specific plan configuration. Each phase has its own sub-noun.

### Phase sub-nouns

| Sub-noun | Verbs | Description |
|----------|-------|-------------|
| `phase-1-init` | `get`, `set` | Init phase (e.g., `branch_strategy`) |
| `phase-2-refine` | `get`, `set` | Refine phase (e.g., `compatibility`) |
| `phase-5-execute` | `get`, `set`, `set-max-iterations`, `set-steps`, `add-step`, `remove-step`, `set-step`, `set-domain-step`, `set-domain-step-agent` | Execute phase |
| `phase-6-finalize` | `get`, `set`, `set-max-iterations`, `set-steps`, `add-step`, `remove-step` | Finalize phase (e.g., `pr_merge_strategy`) |

### Basic get/set pattern

```bash
manage-config plan phase-1-init set \
  --field branch_strategy --value feature
```

### phase-5-execute additional verbs

```bash
# Set maximum verification iterations
manage-config plan phase-5-execute set-max-iterations --value 10

# Enable/disable a generic boolean verification step
manage-config plan phase-5-execute set-step \
  --step verification_1_quality_check --enabled false

# Enable/disable a domain verification step
manage-config plan phase-5-execute set-domain-step \
  --domain java --step 1_technical_impl --enabled false

# Set a domain verification step's agent reference
manage-config plan phase-5-execute set-domain-step-agent \
  --domain java --step 1_lint --agent my-bundle:my-verify-step
```

### phase-6-finalize additional verbs

```bash
# Set PR merge strategy (squash, merge, rebase; default: squash)
manage-config plan phase-6-finalize set \
  --field pr_merge_strategy --value squash

# Set maximum finalize iterations
manage-config plan phase-6-finalize set-max-iterations --value 5

# Enable/disable a finalize step
manage-config plan phase-6-finalize set-step \
  --step 2_create_pr --enabled false
```

### Order-driven step verbs (phase-5-execute, phase-6-finalize)

`set-steps` and `add-step` on these two phases derive each step's effective order exclusively from the step's authoritative `order` field (frontmatter for built-in standards / project-local `SKILL.md`, return-dict key for extension-contributed steps). The resulting list is persisted sorted ascending by that order.

Error responses surfaced by `set-steps` and `add-step`:

| `error` | Additional fields | Meaning |
|---------|--------------------|---------|
| `missing_order` | `step`, `phase`, `detail` | One selected step has no discoverable `order` — declare an `order` field in its authoritative source. |
| `order_collision` | `steps` (2-element list), `order`, `phase`, `detail` | Two selected steps resolve to the same `order` — reassign one of them in its authoritative source. |

`list-finalize-steps` and `list-verify-steps` output now includes the resolved `order` for each step (value is `null` when the source has no declared order).

Optional `--field` parameter on `get` to retrieve a specific field:

```bash
manage-config plan phase-5-execute get --field max_iterations
```

---

## Noun: ext-defaults

Manage extension defaults (generic key-value storage for extension-set configuration).

| Verb | Parameters | Description |
|------|-----------|-------------|
| `get` | `--key` | Get extension default value by key |
| `set` | `--key`, `--value` | Set value (always overwrites) |
| `set-default` | `--key`, `--value` | Set value only if key does not exist (write-once) |
| `list` | -- | List all extension defaults |
| `remove` | `--key` | Remove extension default by key |

### set-default behavior

When key already exists, returns `status: skipped` with `reason: key_exists` and `existing_value`.

### Example

```bash
manage-config ext-defaults set --key my_setting --value my_value
manage-config ext-defaults set-default --key my_setting --value fallback
```

---

## Noun: effort

Manage per-phase effort levels stored under each `plan.<phase>.effort`
attribute (with `plan.effort` as the plan-wide fallback) in
`.plan/marshal.json`. The read verb is a pure resolver; the write
verb completely overwrites the per-phase effort configuration from a
named preset.

| Verb | Parameters | Description |
|------|-----------|-------------|
| `read` | `--phase` and/or `--role` (or `--default`) | Resolve the level keyword (walks `plan.<phase>.effort.<subkey>` -> `plan.<phase>.effort.default` -> `plan.effort` -> `inherit`) |
| `resolve-target` | same as `read` | Resolve + compute the dispatched-variant target name (`execution-context-{level}` or canonical) |
| `apply-preset` | `--preset` | **Completely overwrite** the per-phase effort configuration with a named preset (see `effort_presets.py` for per-preset values) |

### Verb: read

```bash
# Bare group (resolves to phase-2-refine.default then effort)
manage-config effort read --phase phase-2-refine

# Two-flag form
manage-config effort read --phase phase-6-finalize --role verification-feedback

# Dotted form
manage-config effort read --role phase-3-outline

# Zero-role fallback (standalone slash commands, LLM-fallback branches)
manage-config effort read --default
```

Walks the documented resolution order and validates the resolved value against
`ALLOWED_LEVELS` (`low|medium|high|xhigh|xxhigh|max|inherit`). Unknown role
groups produce a warning (not an error) so registry renames do not break
saved configs.

### Verb: apply-preset

```bash
manage-config effort apply-preset --preset balanced
```

Arguments:

- `--preset` (required) — Preset name. Canonical names are
  `economic`, `balanced`, `high-end` (returned by `EffortPresets.all_names()`).
  The lookup is case-insensitive and also accepts the underscore variant
  (`HIGH_END`, `high_end`, `Balanced`, ...). The argparse layer pre-validates
  `--preset` through a `type=` callable that delegates to
  `EffortPresets.get()`, so unknown names are rejected with a usage error
  (exit code 2) before the handler runs. `argparse choices=` is intentionally
  *not* used because it enforces exact case-sensitive matching of the
  canonical names and would reject the documented aliases.

Semantic — **completely overwrites, fully expanded**: every existing
per-phase `effort` attribute is discarded entirely and replaced by the
preset payload, and every sub-key listed in `KNOWN_ROLES` (in
`_cmd_effort.py`) is written explicitly under `plan.<phase>.effort` so
users editing `marshal.json` by hand can see and tune every dispatch
site without consulting the registry.

The expansion rule: every sub-key in every group of `KNOWN_ROLES` is
written under `plan.<phase>.effort` at the preset's `default` level
unless the preset payload defines a per-sub-key override, in which case
the override level is preserved. The `default` value itself is also
kept on the top-level `plan.effort` key so the resolver's documented
walk (`plan.<phase>.effort.<subkey>` -> `plan.<phase>.effort.default`
-> `plan.effort` -> `inherit`) keeps working unchanged.

Any keys present in the previous block but absent from the role registry
are gone after the write — only known roles survive. Merging across runs
is deliberately not supported. For per-role fine-tuning beyond the three
presets, edit the expanded `.plan/marshal.json` directly.

Per-preset values are defined in
`marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py`
(see the `EffortPresets` constant-class). The module documents each preset's
rationale and runs an import-time self-check to guarantee every level value is
in `ALLOWED_LEVELS`.

Success payload:

```toon
status: success
preset: balanced
default: medium
roles_count: 9
overrides_count: 5
```

`roles_count` is the total number of sub-key entries written under
`plan.<phase>.effort` (sum of `len(KNOWN_ROLES[group])` for every group
— 1+1+1+1+2+3 = 9). `overrides_count` is the number of sub-key entries
whose written level differs from `plan.effort` after expansion (i.e.
the user-visible definition of "override" — a sub-key explicitly listed
at the same level as `default` is functionally an inherit and is not
counted).

Common errors:

- `argument --preset: unknown preset '<name>'; valid names: ['economic', 'balanced', 'high-end']` —
  argparse usage error (exit code 2). The supplied `--preset` value did not
  normalise (lowercase + `_`→`-`) to any canonical name. Raised by the
  argparse `type=` callable that delegates to `EffortPresets.get()`.
- `marshal.json not initialized; run /marshall-steward first` — the project
  has not yet run `manage-config init`.
- `level '...' at preset.default ...` / `level '...' at preset.roles.<role> ...` —
  defense-in-depth: a preset value drifted out of `ALLOWED_LEVELS`. Should
  not occur in normal operation; indicates a desync between
  `_cmd_effort.ALLOWED_LEVELS` and the validation in `effort_presets.py`.

---

## Noun: coverage

Resolve and expand the two-dial coverage cell — `thoroughness` (T1–T5) × `scope` (change-set…overall). `read`/`resolve` are the project-DEFAULT resolvers: each field walks `plan.<phase>.coverage.<field>` → `plan.coverage.<field>` → `inherit` independently from `.plan/marshal.json` only (no per-plan tier), mirroring the `effort` resolver. The scope↔thoroughness coupling constraint (`reject thoroughness ≥ T4 ∧ scope < component`) is enforced at lookup/expand time. Coverage's consumers are the components that implement the [coverage-gathering contract](../../dev-agent-behavior-rules/standards/coverage-gathering-contract.md); they gather a per-invocation cell, `expand` it into the contract's operational instruction block, persist it in `status.json` metadata, and fall back to `resolve` (the project default) when no cell was gathered.

| Verb | Parameters | Description |
|------|-----------|-------------|
| `read` | `--phase` and/or `--role` (or `--default`) | Resolve the `{thoroughness, scope, thoroughness_source, scope_source}` cell (project default) |
| `resolve` | same as `read` | Resolve the cell plus a `coupling: ok` field (project default, consulted by the contract's implementors as fallback) |
| `expand` | `--thoroughness` and `--scope` (both required) | Expand a `(thoroughness, scope)` identifier into the contract's operational instruction block; `inherit/inherit` → the behavior-preserving instruction |

### Verb: read

```bash
# Resolve a phase's cell
manage-config coverage read --phase phase-5-execute

# --role is a synonym for --phase
manage-config coverage read --role phase-5-execute

# Raw plan-wide fallback
manage-config coverage read --default
```

### Verb: resolve

```bash
manage-config coverage resolve --phase phase-5-execute
```

### Verb: expand

The static identifier → instruction expander (backed by `coverage_presets.py`). Maps the `(thoroughness, scope)` identifier to the canonical operational instruction text owned by the coverage-gathering contract's expansion table. Both `--thoroughness` and `--scope` are required. `inherit/inherit` expands to the behavior-preserving instruction; an incoherent cell is rejected with `coverage_coupling_violation`.

```bash
# Expand a concrete cell
manage-config coverage expand --thoroughness T3 --scope component

# Behavior-preserving instruction
manage-config coverage expand --thoroughness inherit --scope inherit
```

### Coupling-violation error

An incoherent stored cell raises `error_type: coverage_coupling_violation`:

| `error_type` | Meaning |
|--------------|---------|
| `coverage_coupling_violation` | The resolved cell has `thoroughness ≥ T4` while `scope < component`. Relation-tracing thoroughness cannot be honoured below `component` scope. Widen `scope` to at least `component` or lower `thoroughness` below `T4`. Constraint defined in [`dev-agent-behavior-rules/standards/thoroughness.md`](../../dev-agent-behavior-rules/standards/thoroughness.md) § Coupling Constraint. |

`ALLOWED_THOROUGHNESS` and `ALLOWED_SCOPE` (in `_cmd_coverage.py`) are kept in lock-step with the T1–T5 and scope ladders in that standard.

---

## Noun: ci

### persist

Persist full CI config (provider, commands, tools) in a single operation.

```bash
manage-config ci persist \
  --provider github \
  --repo-url "https://github.com/org/repo" \
  --commands '{"issue-view": "gh issue view", "pr-create": "gh pr create"}' \
  --tools "gh" \
  --git-present true
```

---

## init

Initialize marshal.json.

```bash
manage-config init [--force]
```

---

## Noun: build-map

Seed and read the file-to-build contract (`skill_domains.build_map` block in marshal.json). The block is a domain-keyed inventory of `{glob, role, build_class}` entries seeded from the registered domain extensions; it lives under `skill_domains`, is required and always seeded, and is never clobbered on re-seed (write-once). There is no override layer — corrections are made directly to the seeded entries. See [data-model.md § skill_domains.build_map](data-model.md) for the complete schema and the closed `build_class` enum.

| Verb | Parameters | Description |
|------|-----------|-------------|
| `seed` | -- | Re-seed `skill_domains.build_map` from extensions with write-once semantics. Returns `action: seeded` when written; `action: preserved` when an existing block is left untouched. |
| `read` | -- | Return the effective build map from `skill_domains.build_map`. **Fails closed**: returns a structured error when `skill_domains.build_map` is absent (rather than an empty map). |

### Example: seed

```bash
manage-config build-map seed
```

Success payload:

```toon
status: success
action: seeded
domain_count: 2
build_map:
  python: [...]
  documentation: [...]
```

`action` is `seeded` when the block was written, or `preserved` when an existing block was left untouched.

### Example: read

```bash
manage-config build-map read
```

Success payload:

```toon
status: success
build_map:
  python: [...]
  documentation: [...]
domain_count: 2
```

`domain_count` is the number of domain keys in the returned `build_map`. When `skill_domains.build_map` is absent the read fails closed with a structured error payload instead.

## Error Responses

All errors follow this pattern:

```toon
status: error
error: {message}
```

Common errors:
- `marshal.json not found. Run command /marshall-steward first`
- `skill_domains not configured. Run command /marshall-steward first`
- `Unknown domain: {name}`
