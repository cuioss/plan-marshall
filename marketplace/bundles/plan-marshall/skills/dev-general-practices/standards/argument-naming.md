# Script Argument Naming Conventions

Cross-cutting naming rules for `manage-*` scripts in the `plan-marshall` bundle. These conventions establish a single mental model for callers — skill prose, agent prompts, and other scripts — so that the flag spelled in documentation matches the flag the script actually accepts.

## Scope

These rules apply to every script under `marketplace/bundles/plan-marshall/skills/manage-*/scripts/`. Scripts in other bundles are not in scope but are encouraged to follow the same conventions.

## Rationale

Without a shared convention, each script picks a flag spelling that feels locally correct, and cross-script drift accumulates silently:

- **Caller mental-model alignment**: Skill documentation and agent prompts refer to values conceptually (a *lesson*, a *plan*, a *module*). When the script flag is spelled the same way (`--lesson-id`, `--plan-id`, `--module`), pattern-matching from prose to invocation succeeds. When the script uses a generic flag (`--id`, `--name`), the caller has to look up `--help` for every invocation.
- **Cross-script consistency**: Sibling scripts that perform the same operation should use the same verb. When `manage-status read`, `manage-files read`, and `manage-plan-documents request read` all use `read`, but a peer script uses `get` for the same operation, the inconsistency produces typos and self-correcting failures that cost time on every call site.
- **Standard library affinity**: Where Python's standard library defines canonical names (notably log levels), match the standard rather than abbreviating. Every Python developer writing into a finalize agent or test fixture will reach for the stdlib spelling first.

## Rules

### Rule 1 — Typed IDs

For arguments that identify a scoped entity, use the typed form:

| Entity | Canonical flag |
|---|---|
| Lesson | `--lesson-id` |
| Plan | `--plan-id` |
| Task | `--task-number` |
| Module | `--module` |
| Component | `--component` |

Reserve `--id` for untyped contexts only — hash IDs of opaque records where the entity type is implicit in the subcommand and there is no risk of ambiguity at the caller surface.

**Why**: callers conceptualize values by type, not by the abstract notion of "an identifier". A script that takes `--lesson-id` matches the way every skill, agent prompt, and lesson record refers to the value; a script that takes `--id` forces every caller to remember which flavour of identifier this particular script wanted.

### Rule 2 — Read-verb canonicalization

Use the verb that matches the operation's semantics:

| Verb | Use when |
|---|---|
| `read` | Returning the contents of a scoped artifact (file, document, record body). |
| `get` | Returning a computed or derived value (a config field, a resolved command, a computed status). |
| `exists` | Boolean probe. Must never error on absence — return `exists: false` instead. |

**Why**: callers reach for `read` when they want a body and `get` when they want a value. Mixing these — for example using `get` to return a record body — produces typos that cost time at every call site and make scripts in the same bundle feel arbitrarily inconsistent.

### Rule 3 — Module-name arguments

When a script argument names a module, prefer `--module` over `--name`. Reserve `--name` for generic strings whose referent is unambiguous from the surrounding subcommand context (for example, naming a brand-new entity at creation time).

**Why**: the caller's mental model is about the *referent* (which module), not the *kind of value* (a string name). Using `--module` makes that referent explicit at the call site, where the cost of confusion is highest.

### Rule 4 — Log-level naming

Accept Python-stdlib level names verbatim:

- `INFO`
- `WARNING`
- `ERROR`
- `DEBUG`

Do not abbreviate (`WARN`), do not invent new level names, and do not rename existing levels. If a script needs additional severity granularity, choose stdlib-compatible names (`CRITICAL`).

**Why**: every Python author muscle-memories `logging.WARNING`. Accepting the stdlib spelling eliminates an entire class of caller-facing failure at zero semantic cost.

## Canonical Forms

The table below records the canonical argument form for each in-scope script after this convention lands. Future scripts in scope MUST follow these conventions; existing scripts that diverge are renamed to match.

The cross-cutting `--plan-id` and `--trace-plan-id` flags are accepted by virtually every `manage-*` script and are not enumerated row-by-row.

### `manage-*` scripts

| Script | Operation | Canonical form |
|---|---|---|
| `manage-lessons` | Read a lesson by id | `manage-lessons get --lesson-id {id}` |
| `manage-tasks` | Read a task body | `manage-tasks read --plan-id {id} --task-number {n}` |
| `manage-tasks` | Update a task | `manage-tasks update --plan-id {id} --task-number {n}` |
| `manage-tasks` | Finalize a step | `manage-tasks finalize-step --plan-id {id} --task-number {n} --step {s} --outcome {done|failed|skipped}` |
| `manage-architecture` | Resolve a build command for a module | `architecture resolve --command {cmd} --module {name}` |
| `manage-architecture` | Read a module entry | `architecture module --module {name}` |
| `manage-architecture` | Read a derived module entry | `architecture derived-module --module {name}` |
| `manage-architecture` | List commands for a module | `architecture commands --module {name}` |
| `manage-architecture` | List sibling modules | `architecture siblings --module {name}` |
| `manage-logging` | Emit a warning-level log entry | `manage-logging work --plan-id {id} --level WARNING --message "{msg}"` |

### `tools-integration-ci:ci` (provider-agnostic CI router)

The `pr`, `ci`, `issue`, and `branch` subcommand surfaces are common across providers; provider-specific extensions (e.g., `pr submit-review` on GitHub) follow the same flag conventions. The router consumes `--project-dir {path}` before delegating to the provider script.

| Operation | Canonical form |
|---|---|
| Create a pull request | `ci pr create --title "{title}" --plan-id {id}` |
| View the PR for the current branch | `ci pr view` |
| List pull requests | `ci pr list [--head {branch}] [--state open|closed|all]` |
| Reply to a PR | `ci pr reply --pr-number {n} --body-file {path}` |
| Resolve a review thread | `ci pr resolve-thread --thread-id {id}` |
| Reply within a thread | `ci pr thread-reply --pr-number {n} --thread-id {id} --body-file {path}` |
| Get PR reviews | `ci pr reviews --pr-number {n}` |
| Get PR inline comments | `ci pr comments --pr-number {n} [--unresolved-only]` |
| Wait for new bot comments | `ci pr wait-for-comments --pr-number {n} [--timeout {s}] [--interval {s}]` |
| Merge a pull request | `ci pr merge {--pr-number {n} \| --head {branch}} [--strategy merge\|squash\|rebase] [--delete-branch]` |
| Edit PR title or body | `ci pr edit --pr-number {n} [--title "{title}"] [--body-file {path}]` |
| Check CI status | `ci ci status {--pr-number {n} \| --head {branch}}` |
| Wait for CI to complete | `ci ci wait --pr-number {n} [--timeout {s}] [--interval {s}]` |
| Wait for CI status flip | `ci ci wait-for-status-flip --pr-number {n} [--timeout {s}] [--interval {s}] [--expected success\|failure\|any]` |
| Rerun a workflow | `ci ci rerun --run-id {id}` |
| Get failed run logs | `ci ci logs --run-id {id}` |
| Create an issue | `ci issue create --title "{title}" [--labels {csv}] --body-file {path}` |
| View an issue | `ci issue view --issue {id}` |
| Close an issue | `ci issue close --issue {id}` |
| Wait for issue close | `ci issue wait-for-close --issue-number {n} [--timeout {s}] [--interval {s}]` |
| Wait for issue label | `ci issue wait-for-label --issue-number {n} --label {name} [--mode present\|absent]` |
| Delete remote branch | `ci branch delete --remote-only --branch {name}` |

### `pm-plugin-development:plugin-doctor:doctor-marketplace`

| Operation | Canonical form |
|---|---|
| Scan all bundles | `doctor-marketplace scan [--bundles {csv}]` |
| Scan explicit component paths | `doctor-marketplace scan --paths {path} [{path} ...]` |
| Analyze components | `doctor-marketplace analyze [--bundles {csv}] [--type {csv}] [--name {csv}]` |
| Apply safe fixes | `doctor-marketplace fix [--bundles {csv}] [--type {csv}] [--name {csv}] [--dry-run]` |
| Generate report | `doctor-marketplace report [--bundles {csv}] [--output {dir}]` |
| Validate extension contracts | `doctor-marketplace validate-contracts [--extension-type {kind}] [--skill {bundle:skill}]` |

When adding a new subcommand or argument, choose the spelling consistent with the rules above before authoring the argparse declaration. When in doubt, search this standard's table for an analogous operation and reuse the spelling.

## Enforcement

The canonical forms above are enforced automatically by the `ARGUMENT_NAMING_*` rule cluster in `pm-plugin-development:plugin-doctor:doctor-marketplace` (see [`plugin-doctor/references/rule-catalog.md`](../../../../pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md) → "Argument Naming Rules"). The cluster scans `SKILL.md`, agent prose, recipes, and standards under `marketplace/bundles/*/` for `python3 .plan/execute-script.py {notation} ...` invocations and validates each token against the executor's `SCRIPTS` mapping and the target script's argparse declarations:

- `ARGUMENT_NAMING_NOTATION_INVALID` — flags 3-part notations that do not resolve in the executor mapping (snake_case bundles, self-referential repetition, unregistered skills).
- `ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN` — flags subcommands not declared in the resolved script's `subparsers.choices`.
- `ARGUMENT_NAMING_FLAG_UNKNOWN` — flags `--{flag}` tokens not declared via `add_argument` on the matched subparser.
- `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` — cross-checks every row above against the live argparse declarations and fails on drift.

Together, these rules close the loop between this standard and the implementation: a row added here is enforceable on the next `verify`; a flag renamed in argparse fails this standard's row until both sides agree.

## Related

- `general-development-rules.md` — Boy Scout rule and overall development discipline.
- `tool-usage-patterns.md` — Tool selection and Bash safety rules that govern how these scripts are invoked.
- `pm-plugin-development:plugin-doctor` rule catalog — automated enforcement of this standard's canonical forms.
