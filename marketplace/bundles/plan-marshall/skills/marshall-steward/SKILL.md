---
name: marshall-steward
description: Project configuration wizard for planning system. Manages executor generation, health checks, executor/config staleness signaling, build systems, skill domains, and the upgrade verb for one-flow post-change reconciliation.
user-invocable: true
mode: workflow
---

# Marshall Steward Skill

Project configuration wizard for the planning system.

## Usage

```text
/marshall-steward                        # Interactive menu or first-run wizard
/marshall-steward --wizard               # Force first-run wizard
/marshall-steward upgrade                # Post-change reconciliation — asks before each stage
/marshall-steward upgrade integrate=true # Post-change reconciliation — runs all four stages end-to-end
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

### Check for `upgrade` Verb

If the invocation carries the `upgrade` verb argument (optionally with
`integrate=true`), bypass both the mode routing and the Main Menu entirely and
run the upgrade flow directly:
```text
Read references/upgrade-flow.md
```
Execute the upgrade flow from that file, passing the `integrate` value
(`true` when `integrate=true` was given, otherwise `false`). Follow that
reference's end-of-flow behavior when it completes.

---

## Interactive Menu (Returning User)

Display menu when both executor and marshal.json exist.

### Main Menu

The Main Menu has 6 options, which exceeds the `AskUserQuestion` 4-option cap. It is presented as a paginated menu following the "More actions..." pattern documented in `plan-marshall/workflow/planning.md` (§ Action: list): each page presents at most 4 options, and every non-final page reserves its 4th slot for a "More..." continuation that triggers the next page's `AskUserQuestion`.

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
    - label: "5. Upgrade"
      description: "Post-change reconciliation: regenerate, reconcile, verify, land"
    - label: "6. Quit"
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
| "5. Upgrade" | Load: `Read references/upgrade-flow.md` → Execute |
| "6. Quit" | Output "Good bye!" → STOP |

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
| `landing-cycle.md` | End-of-run landing cycle: detect uncommitted plan-marshall artifact diff → offer to commit → push → `skip-bot-review`-labelled plan-less PR → merge-queue-aware merge → switch-to-main → pull; base-branch-conditional branch selection + bot skip-label honoring matrix | Linked from the "End-of-Run Landing Cycle" hook (menu-mode Quit path + `wizard-flow.md` end) |
| `upgrade-flow.md` | Post-change `upgrade` verb: four-stage reconciliation driven by the project-kind-aware `upgrade.py plan` stage plan (the meta/consumer stage matrix — meta regenerates the target tree + executor and verifies with preflight + content-drift; consumer regenerates the executor only and verifies with preflight only), honoring each stage's per-stage gate dispositions and `sub_steps` | Main Menu option 5, or the `upgrade` early verb check |
| `error-handling.md` | Error types and recovery | On error conditions |

---

## Build Server Status (read-only pointer)

The Health Check may surface the machine-global `marshalld` build server's status
by running `manage-build-server status` and reporting the returned `running` /
`version` / `registered` fields to the operator:

```bash
python3 .plan/execute-script.py plan-marshall:manage-build-server:manage_build_server status
```

This is a **read-only pointer only**. Steward carries NO daemon lifecycle logic —
enrolment (`register` / `unregister`) and control (`start` / `stop` / `drain` /
`install` / `upgrade`) live exclusively in the user-invocable `manage-build-server`
control skill. When the operator wants to start, stop, or enrol, direct them to
`/manage-build-server`; steward never mutates registry or daemon state.

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

**First-run lane materialization.** At the end of the wizard (Step 16),
`sync-defaults` deep-merges the full default finalize step-set into `marshal.json`
before the step-sort, so the seeded pipeline becomes fully explicit — a
newly-materialized `default_on: false` step arrives `lane: off`, growing the step
count while leaving the effective running set unchanged (opt-in preserved). See
[`references/wizard-flow.md`](references/wizard-flow.md) Step 16 for the
materialize-then-sort sequencing.

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
six-step remediation pass at **menu-mode entry, before the Main Menu** — a
sibling entry-time surface to "Branch-Naming Surfacing" and the missing-default
finalize-step detection above. The pass repairs config drift that accumulated in
projects initialized before the relevant fixes landed. The pass is not gated by
any version check; it runs unconditionally on every menu-mode entry and is
idempotent (an already-clean project is left byte-stable).

Steps (a), (b), (d), (e), and (f) are deterministic script calls that are silent
by default — they run unconditionally and leave an already-normalized project
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

Safety follows the same `generate_executor preflight` rules described in
"Executor & Config Staleness Signaling" below (ADR-002: the executor is
per-tree derived state, never a user decision). When preflight reports
`executor_action: regenerated`, the "Session Restart Required After Executor /
Agent Changes" guardrail below applies — surface the session-restart warning
because the emitted agent set may have changed.

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
`status: success` do the three cases below apply, evaluated in order — the
`marshal_status: unknown` gate is checked FIRST and short-circuits, so an
unresolvable-manifest verdict is never swept into the
`marshal_status: fresh → continue silently` branch even when `added_count > 0`:

- **`marshal_status: unknown`** (evaluated first, regardless of `added_count`) →
  the installed `dist-manifest.json` could not be resolved, so version-based
  staleness cannot be determined — the preflight failed CLOSED. Surface the
  cannot-determine warning (echo the preflight `warning` field) telling the user
  freshness could not be substantiated, and advise verifying the install / a
  manual executor regeneration (Maintenance → Regenerate Executor) followed by a
  fresh `/marshall-steward` menu-mode entry. Do NOT report a clean silent pass in
  this case — an `unknown` verdict is not a `fresh` verdict.
- **`added_count: 0` AND `marshal_status: stale`** → surface a warning telling the
  user the reconcile could not see the current config seed even after the
  executor-freshness preflight, and advise a manual executor regeneration
  (Maintenance → Regenerate Executor) followed by a fresh `/marshall-steward`
  menu-mode entry. Do NOT report a clean pass in this case.
- **`added_count > 0`, OR `marshal_status: fresh`** → the normal path; continue
  silently to the Main Menu, preserving the idempotent silent-on-clean behavior
  of steps (a)–(e).

**(f) Sort `phase-6-finalize.steps` into frontmatter order** (silent,
unconditional). Re-sort the on-disk `plan.phase-6-finalize.steps` keyed-map into
ascending frontmatter `order`. `sync-defaults` (step (e)) deep-merges any
newly-added finalize step by appending it, so the operator-visible `marshal.json`
drifts out of frontmatter order over time; this step restores the canonical order
on disk, reusing the manifest composer's sort choke-point (no duplicated order
table). It is sequenced LAST — after step (e)'s `sync-defaults` may have appended
a step — so it corrects any freshly-appended step, and its potential reorder diff
is picked up by the End-of-Run Landing Cycle's uncommitted-artifact detection:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config steps-sort
```

See the `manage-config` Canonical invocations (`steps-sort`) for the verb shape.
The call is idempotent — an already-sorted map is left byte-stable (it persists
only when the key order actually changed), and per-step values are preserved
byte-identically. `phase-5-execute.verification_steps` is out of scope.

After the six steps settle, proceed to the Main Menu.

## End-of-Run Landing Cycle

A steward run can leave uncommitted changes to plan-marshall artifacts — the
Re-Run Remediation Pass alone may rewrite `marshal.json` (steps (a) normalize-keys,
(e) sync-defaults, (f) steps-sort), and interactive configuration edits touch it
too. The **End-of-Run Landing Cycle** is a single, uniform end-of-run hook that
offers to land those changes so a steward pass does not silently leave the working
tree dirty.

**Uniform firing point.** The hook fires at the natural END of every steward
mode:

- **Menu mode** — on the "Quit" path (Main Menu option 5), AFTER "Good bye!" is
  emitted and BEFORE the skill stops.
- **Wizard mode** — at the end of the wizard flow (see
  [`references/wizard-flow.md`](references/wizard-flow.md)), after the final
  configuration step completes.

**Trigger.** The hook runs the landing-cycle procedure only when the working tree
carries an uncommitted diff — the Step 1 check is a plain whole-tree
`git -C {repo_root} status --porcelain` that is NOT path-filtered; with no diff it
is a silent no-op and the run ends normally. In practice the changes a steward run
leaves uncommitted are always to tracked plan-marshall artifacts, but the check
itself is unscoped over the whole working tree. The full procedure — diff detection, the land/leave `AskUserQuestion`
gate, base-branch-conditional branch selection (create `chore/{slug}` on a base
branch; confirm reuse of a non-base working branch), commit → push →
`skip-bot-review`-labelled plan-less PR → merge-queue-aware merge → switch to
the base branch → pull, and the bot skip-label honoring matrix — is documented in
[`references/landing-cycle.md`](references/landing-cycle.md). Load and execute that
reference when the hook fires.

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
clears it. When `executor_action` is `regenerated`, surface the session-reload
directive (see "Session Reload Directive After Executor / Agent Changes" below)
because the emitted agent set may have changed.

## Session Reload Directive After Executor / Agent Changes

> **CRITICAL — Reload the session's plugin set before dispatching against
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
> generation step that regenerated the executor OR changed the agent set,
> resolve the harness-appropriate reload directive through the
> platform-runtime seam and surface it verbatim to the user:
>
> ```bash
> python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session reload-directive
> ```
>
> On Claude the directive is `/reload-plugins`, which refreshes the
> session-pinned registry live — only registered monitors force a full
> session restart, and plan-marshall registers none. On OpenCode the seam
> returns a `no-op` whose alternative is a full session restart. The WHY
> rationale (registry is session-pinned at startup) is unchanged and is
> documented at the sister surfaces — `/sync-plugin-cache`,
> `variant_emitter.py`, and `ext-point-dynamic-level-executor.md` — and
> MUST stay convergent across all four surfaces.

## Artifact Landing Cycle

When a plan's deliverables touch marshall-steward-owned artifacts — executor regeneration (`.plan/execute-script.py`), `marshal.json` migrations, or the plugin-cache sync — those changes already commit to the governing plan's feature branch and ship as part of its normal `phase-6-finalize` PR. Whether they ride that PR or split into their own is decided by the same project-wide `pr_strategy` policy every PR-opening surface consults. Call the decision verb with the landing cycle's changed-file count and branch on its verdict:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config project pr-decision \
  --changed-files N
```

Ride the plan's finalize PR on `decision: ride`; split into a separate PR on `decision: split`. Reference the verb by its canonical invocation (see `manage-config` Canonical invocations → `project pr-decision`) rather than restating the ceiling comparison. This documents already-implicit behaviour — steward artifacts already land on the plan's feature branch — now decided through the verb. For the ad-hoc (non-plan) counterpart of this rule, see [`persona-plan-marshall-agent` agent-behavior-rules.md § "Ad-hoc changes still get the full PR flow"](../persona-plan-marshall-agent/standards/agent-behavior-rules.md).

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

The canonical argparse surface for the four entry-point scripts this skill registers: `determine_mode.py`, `bootstrap_plugin.py`, `gitignore_setup.py`, and `upgrade.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

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

### upgrade — plan

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:upgrade plan [--integrate {true|false}] [--project-kind {auto|meta|consumer}]
```

