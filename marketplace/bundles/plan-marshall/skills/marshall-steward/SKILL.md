---
name: marshall-steward
description: Project configuration wizard for planning system. Manages executor generation, health checks, executor/config staleness signaling, build systems, and skill domains.
user-invocable: true
mode: workflow
---

# Marshall Steward Skill

Project configuration wizard for the planning system.

## Usage

```text
/marshall-steward           # Interactive menu or first-run wizard
/marshall-steward --wizard  # Force first-run wizard
```

## Banner

At command start, emit the following banner verbatim to the user:

```text
[ MARSHALL STEWARD ]
configure · verify · maintain
```

---

## Enforcement

**Execution mode**: Run scripts exactly as documented; return to Main Menu after each operation.

**Prohibited actions:**
- Do not invent alternative menu structures or options
- Do not end without returning to menu (unless Quit)
- Do not summarize what you are about to do instead of doing it
- Do not improvise script execution; run exactly as documented

**Constraints:**
- Bootstrap scripts use direct Python paths with glob
- All other scripts use `python3 .plan/execute-script.py {notation} ...`
- After any operation completes, return to Main Menu
- Only exit when user selects "Quit"

---

## What This Skill Provides

**Wizard Mode**: Sequential setup for new projects (executor generation, marshal.json init, build detection, skill domains)

**Menu Mode**: Interactive maintenance for returning users (regenerate executor, health check, configuration)

---

## Scripts

### Own Scripts (bootstrap-capable, run before executor exists)

| Script | Notation | Purpose |
|--------|----------|---------|
| determine_mode | `plan-marshall:marshall-steward:determine_mode` | Determine wizard vs menu mode; also exposes `check-working-prefixes` (project.working_prefixes presence/drift) and `check-staleness` (health-menu executor/config staleness preflight) |
| gitignore_setup | `plan-marshall:marshall-steward:gitignore_setup` | Configure .gitignore for .plan/ |
| bootstrap_plugin | _(direct Python call)_ | Detect plugin root, cache in `.plan/local/marshall-state.toon` |

### Delegated Scripts (require executor)

| Script | Notation | Purpose |
|--------|----------|---------|
| generate-executor | `plan-marshall:tools-script-executor:generate_executor` | Executor generation. Both surfaces (wizard Step 4 and maintenance "Regenerate Executor") detect whether they are running inside a git worktree (path under `.plan/local/worktrees/`) and, when so, pass `--marketplace-root <worktree-absolute-path>` so the generated executor's script mappings resolve against the worktree's `marketplace/bundles/` instead of the main checkout or the plugin cache. |
| manage-config | `plan-marshall:manage-config:manage-config` | Project-level marshal.json CRUD |
| run_config | `plan-marshall:manage-run-config:run_config` | Clean temp, logs, archived-plans, memory |
| ci_health | `plan-marshall:tools-integration-ci:ci_health` | CI provider detection |
| permission_doctor | `plan-marshall:tools-permission-doctor:permission_doctor` | Permission analysis |
| permission_fix | `plan-marshall:tools-permission-fix:permission_fix` | Permission fixes |
| extension_discovery | `plan-marshall:extension-api:extension_discovery` | Extension config defaults |
| credentials | `plan-marshall:manage-providers:credentials` | External tool provider management |

---

## Prerequisites

The `/marshall-steward` command must locate `bootstrap_plugin.py` and detect the plugin root before loading this skill. `bootstrap_plugin.py` is the single deterministic resolver for every other bootstrap script path — locate it once, then route all post-`get-root` path lookups through its `resolve` verb instead of hand-globbing each script.

1. **Locate `bootstrap_plugin.py` (the one unavoidable glob).** Resolve its path with the `Glob` tool against the **layout-agnostic** pattern `**/marshall-steward/scripts/bootstrap_plugin.py` and capture the first match as `${BOOTSTRAP}`. The recursive `**` prefix matches both deploy layouts — the flat `target/claude/plan-marshall/skills/…` tree and the versioned cache `…/plan-marshall/{version}/skills/…` tree — without a hand-placed `*` version level.
2. **Detect the plugin root** and cache it:

   ```bash
   python3 "${BOOTSTRAP}" get-root
   ```

   Read `plugin_root` from the TOON output and set `${PLUGIN_ROOT}` to it. The plugin root is cached in `.plan/local/marshall-state.toon` for subsequent calls.
3. **Resolve every other bootstrap script path through `bootstrap_plugin resolve`** — version-aware, layout-agnostic. For any script `X.py` under a bundle, run:

   ```bash
   python3 "${BOOTSTRAP}" resolve --bundle plan-marshall --path skills/{skill}/scripts/X.py
   ```

   and read `resolved_path` from the TOON. Never hand-glob a `${PLUGIN_ROOT}/plan-marshall/*/skills/…` pattern to find a post-`get-root` script — `resolve` already iterates the version dirs deterministically.

---

## Step 1: Determine Mode

Determine whether to run wizard or menu based on existing files.

**BOOTSTRAP**: Since execute-script.py may not exist yet, use a DIRECT Python call. Resolve the script path deterministically via `bootstrap_plugin resolve` (`${BOOTSTRAP}` was located in Prerequisites) and read `resolved_path` from the TOON as `{DETERMINE_MODE}`:

```bash
python3 "${BOOTSTRAP}" resolve --bundle plan-marshall --path skills/marshall-steward/scripts/determine_mode.py
```

Then invoke the resolved script directly:

```bash
python3 "{DETERMINE_MODE}" mode
```

**Output (TOON)**:
```toon
mode	wizard
reason	executor_missing
```

### Mode Routing

| mode | reason | Action |
|------|--------|--------|
| `wizard` | `executor_missing` | Load: `Read references/wizard-flow.md` → Execute wizard |
| `wizard` | `marshal_missing` | Load: `Read references/wizard-flow.md` → Execute wizard |
| `menu` | `both_exist` | Show Main Menu below |

### Check for `--wizard` Flag

If `--wizard` flag provided, force wizard regardless of determine_mode result:
```text
Read references/wizard-flow.md
```
Execute the wizard flow from that file.

---

## Interactive Menu (Returning User)

Display menu when both executor and marshal.json exist.

### Main Menu

The Main Menu has 5 options, which exceeds the `AskUserQuestion` 4-option cap. It is presented as a paginated menu following the "More actions..." pattern documented in `plan-marshall/workflow/planning.md` (§ Action: list): each page presents at most 4 options, and every non-final page reserves its 4th slot for a "More..." continuation that triggers the next page's `AskUserQuestion`.

**Page 1** — first 3 options plus the "More..." continuation:

```text
AskUserQuestion:
  question: "What would you like to do?"
  header: "Main Menu"
  options:
    - label: "1. Maintenance"
      description: "Regenerate executor, clean logs"
    - label: "2. Health Check"
      description: "Verify setup, diagnose issues"
    - label: "3. Configuration"
      description: "Build systems, skill domains"
    - label: "More..."
      description: "Show remaining Main Menu options"
  multiSelect: false
```

**Page 2** — shown only when the user selects "More..." on Page 1 — the remaining options:

```text
AskUserQuestion:
  question: "What would you like to do?"
  header: "Main Menu (continued)"
  options:
    - label: "4. Effort"
      description: "Configure per-role model levels (variant routing)"
    - label: "5. Quit"
      description: "Exit plan-marshall"
  multiSelect: false
```

### Menu Routing

| User Selection | Action |
|----------------|--------|
| "1. Maintenance" | Load: `Read references/menu-maintenance.md` → Execute |
| "2. Health Check" | Load: `Read references/menu-healthcheck.md` → Execute |
| "3. Configuration" | Load: `Read references/menu-configuration.md` → Execute |
| "More..." | Present Main Menu Page 2 `AskUserQuestion` |
| "4. Effort" | Load: `Read standards/effort-menu.md` → Execute |
| "5. Quit" | Output "Good bye!" → STOP |

After any menu option completes, return to Main Menu Page 1 (except Quit).

---

## Deferred Loading Pattern

This skill uses **progressive disclosure** to minimize context usage:

1. **Core skill loads**: ~150 lines (this file - routing logic only)
2. **On wizard mode**: Load `references/wizard-flow.md` (~250 lines)
3. **On menu selection**: Load only the selected reference (~100-150 lines)

### How to Load a Reference

When routing indicates to load a reference:
```text
Read references/{file}.md
```
Then execute the workflow described in that file. Each reference file is loaded in full when its menu path is chosen — only one reference is active at a time.

---

## Available References

| Reference | Purpose | Load When |
|-----------|---------|-----------|
| `wizard-flow.md` | First-run wizard steps 1-15 (bootstrap 1-4, configuration 5 onwards) | mode=wizard or --wizard flag |
| `provider-setup.md` | Provider discovery/activation, CI detection, credential setup (extracted from wizard-flow.md) | Linked from `wizard-flow.md` (provider/CI/credential steps) |
| `architecture-setup.md` | Extension defaults, module discovery, build commands, Maven profiles, LLM analysis + architecture_refresh tier knobs (extracted from wizard-flow.md) | Linked from `wizard-flow.md` Step 8 |
| `build-map-setup.md` | Build-map seed/read workflow — `build.map` file-to-build contract, write-once seed, menu re-seed operation | Linked from `wizard-flow.md` Step 8b and `menu-configuration.md` (Project Structure) |
| `skill-domains-setup.md` | Skill-domain configuration, profile activation, execute-task/recipe registration (extracted from wizard-flow.md) | Linked from `wizard-flow.md` Step 9 |
| `menu-maintenance.md` | Regenerate executor, cleanup. The cleanup operation routes to the `Action: cleanup` workflow, which now includes a stalled-lesson-sourced-plan restore pass (restoring trapped lessons to the active corpus via `restore-from-plan`) — see [`../plan-marshall/workflow/planning.md`](../plan-marshall/workflow/planning.md) § "Action: cleanup" for the authoritative procedure. | Menu option 1 |
| `menu-healthcheck.md` | Verify setup, diagnose issues | Menu option 2 |
| `menu-configuration.md` | Build systems, skill domains, architecture refresh tier knobs | Menu option 3 |
| `standards/effort-menu.md` | Per-phase effort configuration (Effort submenu) | Menu option 4 |
| `menu-recipes.md` | Built-in recipes available in the wizard | Linked from `menu-configuration.md` |
| `menu-terminal-title.md` | Two-action sub-menu: install render-hook wiring; override active-plan for the current session | Linked from `menu-configuration.md` (Terminal Title) |
| `menu-enforcement-hook.md` | Detect→confirm→install sub-menu for the conditional PreToolUse enforcement hook (orthogonal `--enforcement` install) | Linked from `menu-configuration.md` (Enforcement Hook) |
| `merge-queue-setup.md` | Idempotent probe→ask→configure provisioning of the platform merge queue (GitHub merge queue / GitLab merge train) via the `ci repo merge-queue` verbs | Linked from `wizard-flow.md` Step 13.5 and `menu-configuration.md` (Merge Queue) |
| `error-handling.md` | Error types and recovery | On error conditions |

---

## Phase 6 Finalize Step Seeding

The wizard seeds `phase-6-finalize.steps` in `marshal.json` from the
default-on built-in finalize-step set discovered via
`extension_discovery.find_implementors` — the SOLE finalize-step
discovery path. Membership, execution order, and default-seed inclusion
are declared in each step doc's frontmatter (`implements: ...ext-point-finalize-step`,
`order`, `default_on: true`), NOT a hand-maintained constant list; see
[`extension-api/standards/ext-point-finalize-step.md`](../extension-api/standards/ext-point-finalize-step.md).
The seed intentionally covers only steps that are sensible defaults for
**any** plan-marshall consumer (pre-push-quality-gate, finalize-step-simplify,
finalize-step-security-audit, push, create-pr, ci-verify, automated-review,
sonar-roundtrip, lessons-capture, branch-cleanup, finalize-step-preference-emitter,
record-metrics, finalize-step-print-phase-breakdown, archive-plan), ordered
by their declared `order`. `pre-push-quality-gate` is a built-in default
like the rest; its activation is derived from `build.map` — it activates
whenever the live footprint touches a glob registered in the build_map.
Those globs are tree-derived from each extension's `classify_globs()`
vocabulary (complete-by-construction over the real tree), not author-shipped
static literals.

Steps that are **meta-project-only** — e.g. running the multi-target
generator and pushing the host plugin cache — are NOT default-on built-ins.
They live as project-local skills under
`.claude/skills/finalize-step-{name}/SKILL.md` in the meta-project that
needs them (discovered as `project:finalize-step-{name}` with `default_on: false`),
and that meta-project's `marshal.json` registers them explicitly. Consumer
projects don't see them and don't have them seeded.

**Missing-default detection.** When the wizard runs against an existing
project, `determine_mode.py` compares the existing
`marshal.json::plan["phase-6-finalize"]["steps"]` array against the
discovered default-on built-in set (via `extension_discovery.find_implementors`).
Any built-in step missing from the project's array is surfaced as
`missing_default_finalize_steps` so the wizard can prompt the user to add
it. This protects existing projects from quietly missing newly-added
consumer-applicable defaults when their `marshal.json` predates the additions.

## Blocking-Finding Classification (fixed rule — no wizard seed)

The blocking-finding gate is governed by a **fixed, hardcoded** actionable-vs-knowledge rule in `plan-marshall/scripts/_invariants.py` — there is **no** per-phase configuration partition, no `marshal.json` key, and no wizard seed step. **ACTIONABLE** types (`build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `qgate`, `pr-comment`) block when `pending` at a guarded boundary; **KNOWLEDGE** types (`insight`, `tip`, `best-practice`, `improvement`) never block. The wizard does not write any blocking-finding configuration. See [`plan-marshall:plan-marshall/references/phase-handshake.md`](../plan-marshall/references/phase-handshake.md) § `pending_findings_blocking_count` resolution for the full rule.

## Branch-Naming Surfacing (project.working_prefixes)

`project.working_prefixes` holds the canonical closed set of allowed
working-branch prefixes as the transparent, operator-editable source of truth in
`marshal.json`. It is seeded from `DEFAULT_PROJECT['working_prefixes']` (defined
in `manage-config/scripts/_config_defaults.py`) on `init` and back-filled into an
existing `marshal.json` by `sync-defaults`. The default value is:

| Key | Default |
|-----|---------|
| `working_prefixes` | `["feature/", "fix/", "chore/"]` |

The `docs/` prefix is explicitly retired and must not be re-admitted — it is not
CI-triggered, so a `docs/`-prefixed branch makes its PR structurally unmergeable
(see CLAUDE.md "Branch Naming"). The CI push-trigger allowlist is owned by
`.github/workflows/python-verify.yml` (not mirrored here); a structural test
(`test_branch_prefix_allowlist.py`) asserts every `working_prefix` is covered by
a workflow push trigger.

**Missing-default / drift detection.** When the wizard runs against an existing
project, `determine_mode.py check-working-prefixes` compares the live
`marshal.json::project["working_prefixes"]` list against
`DEFAULT_PROJECT['working_prefixes']`. It surfaces `missing` when the key is
entirely absent, or a drift signal when a default entry is missing, so the wizard
can prompt the user to add or update it. This protects projects whose
`marshal.json` predates the key, since `sync-defaults` is not auto-run in the
interactive menu flow.

**Idempotent and non-clobbering.** The detection performs no writes. An
operator's customized list — including a *superset* that adds prefixes beyond
the defaults — is returned as `ok` and never flagged or overwritten; only
genuine absence or a missing default entry is surfaced.

**Wizard step** (runs against an existing project to surface presence/drift):

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode \
  check-working-prefixes
```

**Output (TOON)** when the list is present and current (or operator-customized):

```toon
status	ok
```

When the `working_prefixes` key is absent:

```toon
status	missing
detail	absent
missing_keys	working_prefixes
```

When the key is present but a default entry has drifted out (e.g. `chore/`
dropped):

```toon
status	missing
detail	drift
missing_keys	working_prefixes
```

## Re-Run Remediation Pass

When the steward runs in **menu mode** (both the executor and `marshal.json`
already exist — an already-initialized project re-run/upgrade), it performs a
five-step remediation pass at **menu-mode entry, before the Main Menu** — a
sibling entry-time surface to "Branch-Naming Surfacing" and the missing-default
finalize-step detection above. The pass repairs config drift that accumulated in
projects initialized before the relevant fixes landed. The pass is not gated by
any version check; it runs unconditionally on every menu-mode entry and is
idempotent (an already-clean project is left byte-stable).

Steps (a), (b), (d), and (e) are deterministic script calls that are silent by
default — they run unconditionally and leave an already-normalized project
unchanged. They surface nothing to the user EXCEPT for the documented warning
conditions of steps (d) and (e): step (d)'s session-restart warning when it
regenerates the executor, and step (e)'s detect/warn advisory when the reconcile
could not see the current config seed. Step (c) is an LLM-driven Y/N
`AskUserQuestion` gate that consumes a deterministic diff, mirroring the existing
entry-time `check-working-prefixes` / missing-default surfacing.

**(a) Normalize `marshal.json` top-level key order** (silent, unconditional).
Re-write `marshal.json` with the canonical `save_config` key order. Pre-fix
projects accumulated a non-canonical top-level key order; this re-orders them
without touching values:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config normalize-keys
```

See the `manage-config` Canonical invocations (`normalize-keys`) for the verb
shape. The call is idempotent — an already-canonical file is left byte-stable.

**(b) Consolidate duplicate managed `.gitignore` blocks** (silent,
unconditional). Run the `.gitignore` setup script via the executor/bootstrap.
Pre-fix projects accumulated multiple `# Planning system (managed by
/marshall-steward)` managed-block headers (one per re-run); the consolidation
pass merges them into a single managed block preserving the union of rules, and
leaves an already-single-block file unchanged (`status: unchanged`):

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:gitignore_setup
```

See the `gitignore_setup` Canonical invocations entry for the verb shape. The
consolidation runs on every invocation; a clean file is byte-stable.

**(c) `build.map` drift gate** (read-only diff + interactive Y/N gate). Compute
the drift between the persisted `build.map` and the live-tree derivation, then
gate any re-seed behind an `AskUserQuestion` so deliberate hand-edits are never
clobbered:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map drift
```

See the `manage-config` Canonical invocations (`build-map drift`) for the verb
shape. The verb is read-only — it never mutates `marshal.json`. It returns
`in_sync` plus the per-domain `added_globs` / `removed_globs` diff.

- **`in_sync: true`** → no drift; continue to the Main Menu silently (no prompt).
- **`in_sync: false`** → display the added/removed-glob diff to the user, then
  prompt:

  ```text
  AskUserQuestion:
    question: "The persisted build.map differs from the live-tree derivation. Re-seed it?"
    header: "build.map drift"
    options:
      - label: "Yes, re-seed"
        description: "Overwrite build.map with the live derivation"
      - label: "No, leave as-is"
        description: "Keep the persisted build.map (preserves deliberate hand-edits)"
    multiSelect: false
  ```

  - **Yes** → re-seed via the force path:

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed --force
    ```

  - **No** → leave the persisted `build.map` untouched.

**(d) Refresh the generated executor via `generate_executor preflight`** (silent,
unconditional). Run the executor-freshness preflight FIRST, before the
`sync-defaults` reconcile below. When the executor's embedded `MARSHALL_VERSION`
is older than the installed manifest's `executor_changed_at_version`, this
regenerates the executor in place; otherwise it is a no-op reporting
`executor_action: fresh`. Sequencing it ahead of sync-defaults is load-bearing:
a version-stale executor resolves `manage-config sync-defaults` to a stale
`_cmd_sync_defaults.py`, making the reconcile a silent no-op that never sees the
current config seed. Regenerating the executor first guarantees the subsequent
sync-defaults call — a fresh subprocess through `.plan/execute-script.py` —
resolves through the current-version script:

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor preflight
```

Regeneration is safe because the executor is per-tree derived state (ADR-002),
never a user decision. When preflight reports `executor_action: regenerated`, the
"Session Restart Required After Executor / Agent Changes" guardrail below applies
— surface the session-restart warning because the emitted agent set may have
changed.

**(e) Refresh provisioning stamps via `sync-defaults`** (silent, unconditional).
Run the config deep-merge reconcile. It back-fills any missing default keys AND
re-stamps the `system.provisioned_version` / `system.config_seed_fingerprint`
provisioning fields, so a config-seed change made after the project was
initialized is reflected in `marshal.json`. This is the config-reconcile step
the `check-staleness` preflight advises the user to run when it reports
`marshal_status: stale`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config sync-defaults
```

See the `manage-config` `sync-defaults` command for the deep-merge + re-stamp
contract. The call is idempotent — an already-current config is left byte-stable
(it persists only when the merge added a key or a stamp changed). The refreshed
`system.provisioned_version` is what `determine_mode check-staleness` compares
against the installed `dist-manifest.json`'s `config_changed_at_version`.

**Detect/warn after (e)** — because step (d) already guaranteed a current-version
executor, a `sync-defaults` that reports `added_count: 0` while the config is
still stale is now anomalous rather than expected. Immediately after step (e),
compare its `added_count` against a fresh `determine_mode check-staleness`
`marshal_status`.

First gate on call success: the comparison below is evaluated ONLY when BOTH the
`sync-defaults` call AND the fresh `check-staleness` call return
`status: success`. A non-success status from either call must surface the failure
to the user and skip the clean-pass path entirely — never infer success from
`marshal_status: fresh` alone, because an error path does not guarantee a
well-formed `added_count` field. Only once both calls have returned
`status: success` do the two cases below apply:

- **`added_count: 0` AND `marshal_status: stale`** → surface a warning telling the
  user the reconcile could not see the current config seed even after the
  executor-freshness preflight, and advise a manual executor regeneration
  (Maintenance → Regenerate Executor) followed by a fresh `/marshall-steward`
  menu-mode entry. Do NOT report a clean pass in this case.
- **`added_count > 0`, OR `marshal_status: fresh`** → the normal path; continue
  silently to the Main Menu, preserving the idempotent silent-on-clean behavior
  of steps (a)–(e).

After the five steps settle, proceed to the Main Menu.

## Executor & Config Staleness Signaling

The steward surfaces executor/config staleness against the installed
`dist-manifest.json` (emitted by the target generator) through the deterministic
`generate_executor preflight` verb, wrapped by `determine_mode check-staleness`
so the Health Check menu can run it as one of its checks. The verb applies two
**asymmetric ownership** rules:

- **The executor is safe derived state (ADR-002).** When the executor's embedded
  `MARSHALL_VERSION` is older than the manifest's `executor_changed_at_version`,
  the verb regenerates the executor in place and reports
  `executor_action: regenerated`; otherwise `executor_action: fresh`.
  Regeneration is safe because the executor is per-tree derived state, never a
  user decision.
- **`marshal.json` holds user decisions and is never auto-mutated.** Config-seed
  staleness (`system.provisioned_version` older than the manifest's
  `config_changed_at_version`) is reported advisory-only as
  `marshal_status: stale`; the steward routes the user to a config reconcile
  rather than silently rewriting their config.

A fresh install with no manifest resolves both `changed_at` values to the empty
sentinel, so nothing is stale and the verb is a no-op reporting `fresh`.

**Health-menu entry.** The Health Check menu runs the staleness preflight via:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode check-staleness
```

**Output (TOON)** when the executor and config are both current:

```toon
status	success
executor_action	fresh
marshal_status	fresh
installed_version	<version>
executor_version	<version>
marshal_version	<version>
```

When `marshal_status` is `stale`, advise the user to run a steward config
reconcile — the **Re-Run Remediation Pass** steps (d)-(e) above refresh the
executor and provisioning stamps (see those steps and their detect/warn
conditional for the sequencing rationale and warning mechanics), so
re-entering `/marshall-steward` in menu mode normally clears the advisory. The
exception is the detect/warn path (`added_count: 0` AND `marshal_status: stale`),
where the reconcile could not see the current config seed even after the
executor-freshness preflight — there, a manual executor regeneration
(Maintenance → Regenerate Executor) is required before a fresh menu-mode entry
clears it. When `executor_action` is `regenerated`, surface the session-restart
guardrail (see "Session Restart Required After Executor / Agent Changes" below)
because the emitted agent set may have changed.

## Session Restart Required After Executor / Agent Changes

> **CRITICAL — Restart Claude Code session before dispatching against
> newly-emitted agents or notations.** Claude Code's agent registry is
> **session-pinned at session start**: it scans the plugin cache exactly
> once when the session boots and never re-scans mid-session. Any
> steward operation that materially alters the agent set — executor
> regeneration that adds new notations, a `/sync-plugin-cache` run that
> emits new `execution-context-{level}` variants from the
> dynamic-level executor extension point — produces files the
> already-running session **cannot see**. Dispatching against a freshly
> emitted variant from the same session fails with
> `Agent type 'plan-marshall:execution-context-{level}' not found` even
> though the file exists on disk in the cache.
>
> **Operational guardrail:** after running steward operations from the
> Maintenance menu (Regenerate Executor) or the wizard's executor-
> generation step, surface a prominent "Restart Claude Code session
> before next dispatch" warning to the user when the operation regenerated
> the executor OR changed the agent set. The restart is the only
> mechanism that refreshes the registry. The same WHY rationale
> (registry is session-pinned at startup) is documented at the sister
> surfaces — `/sync-plugin-cache`, `variant_emitter.py`, and
> `ext-point-dynamic-level-executor.md` — and MUST stay convergent
> across all four surfaces.

## Architecture Refresh Tier Knobs

The wizard and the maintenance Configuration submenu both expose two `architecture_refresh` tier knobs that drive the `phase-6-finalize` `architecture-refresh` step. The canonical schema, defaults, and value contract are owned by `plan-marshall:manage-run-config` (see `manage-run-config/standards/run-config-standard.md` and the `architecture-refresh get-tier-0/get-tier-1/set-tier-0/set-tier-1` subcommands documented in `manage-run-config/SKILL.md`).

| Knob | Subcommand | Default | Allowed values |
|------|------------|---------|----------------|
| `architecture_refresh.tier_0` | `manage-run-config architecture-refresh set-tier-0 --value {value}` | `enabled` | `enabled`, `disabled` |
| `architecture_refresh.tier_1` | `manage-run-config architecture-refresh set-tier-1 --value {value}` | `prompt` | `prompt`, `auto`, `disabled` |

Surfaces inside this skill:

| Surface | Reference | Section |
|---------|-----------|---------|
| First-run wizard | `references/architecture-setup.md` | Architecture Refresh Tier Knobs (reached via wizard-flow.md Step 8) |
| Maintenance menu (returning users) | `references/architecture-setup.md` | Architecture Refresh Tier Knobs (reached via Configuration → Full Reconfigure, which re-runs the wizard from Step 5 onwards) |

Both surfaces share the same `architecture-setup.md` tier-knob question set, and both delegate persistence to the `manage-run-config architecture-refresh set-tier-*` subcommands — this skill never edits `run-config.json` directly.

---

## Built-In Recipes

The steward exposes the following built-in recipes (registered via `provides_recipes()` in `plan-marshall-plugin/extension.py`). Recipes are loaded by `phase-3-outline` when a plan's status metadata sets `plan_source=recipe` and `recipe_key=<key>`.

| Recipe key | Recipe skill | Default change_type | Scope |
|------------|--------------|---------------------|-------|
| `refactor-to-profile-standards` | `plan-marshall:recipe-refactor-to-profile-standards` | `tech_debt` | `codebase_wide` |
| `lesson_cleanup` | `plan-marshall:recipe-lesson-cleanup` | _derived from lesson kind_ (see below) | `single_lesson` |

**lesson_cleanup derived change_type**:

| Lesson kind | change_type |
|-------------|-------------|
| `bug` | `bug_fix` |
| `improvement` | `enhancement` |
| `anti-pattern` | `tech_debt` |

The `lesson_cleanup` recipe is auto-suggested by `phase-1-init` Step 5c when `source == lesson` and the lesson body is doc-shaped (no code-touching fences, no code-action verbs as primary subject). See `references/menu-recipes.md` for the wizard-facing description and `marketplace/bundles/plan-marshall/skills/recipe-lesson-cleanup/SKILL.md` for the recipe contract.

> **Note**: `shared-doc-check.md` content has been inlined into `wizard-flow.md` and `menu-maintenance.md`. For TOON output format, see `plan-marshall:ref-toon-format`.

---

## Error Handling

If an error occurs during execution:
```text
Read references/error-handling.md
```
Apply the recovery guidance for the specific error type.

## Canonical invocations

The canonical argparse surface for the three entry-point scripts this skill registers: `determine_mode.py`, `bootstrap_plugin.py`, and `gitignore_setup.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### determine_mode — mode

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode mode [--plan-dir PLAN_DIR]
```

### determine_mode — check-docs

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode check-docs [--project-root PROJECT_ROOT]
```

### determine_mode — fix-docs

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode fix-docs [--project-root PROJECT_ROOT]
```

### determine_mode — check-structure

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode check-structure [--plan-dir PLAN_DIR]
```

### determine_mode — check-missing-finalize-steps

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode check-missing-finalize-steps [--plan-dir PLAN_DIR]
```

### determine_mode — check-staleness

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode check-staleness
```

### bootstrap_plugin — get-root

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:bootstrap_plugin get-root [--refresh]
```

### bootstrap_plugin — resolve

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:bootstrap_plugin resolve --bundle BUNDLE --path PATH
```

### gitignore_setup

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:gitignore_setup [--project-root PROJECT_ROOT] [--dry-run]
```

