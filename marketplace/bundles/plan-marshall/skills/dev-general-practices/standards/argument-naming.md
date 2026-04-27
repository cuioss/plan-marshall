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

The table below records the canonical argument form for each in-scope `manage-*` script after this convention lands. Future scripts in scope MUST follow these conventions; existing scripts that diverge are renamed to match.

| Script | Operation | Canonical form |
|---|---|---|
| `manage-lessons` | Read a lesson by id | `manage-lessons get --lesson-id {id}` |
| `manage-tasks` | Read a task body | `manage-tasks read --plan-id {id} --task {n}` |
| `manage-architecture` | Resolve a build command for a module | `architecture resolve --command {cmd} --module {name}` |
| `manage-logging` | Emit a warning-level log entry | `manage-logging work --plan-id {id} --level WARNING --message "{msg}"` |

When adding a new `manage-*` subcommand or argument, choose the spelling consistent with the rules above before authoring the argparse declaration. When in doubt, search this standard's table for an analogous operation and reuse the spelling.

## Related

- `general-development-rules.md` — Boy Scout rule and overall development discipline.
- `tool-usage-patterns.md` — Tool selection and Bash safety rules that govern how these scripts are invoked.
