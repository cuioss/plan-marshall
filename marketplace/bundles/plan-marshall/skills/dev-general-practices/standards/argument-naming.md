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

The cross-cutting `--plan-id` and `--audit-plan-id` flags are accepted by virtually every `manage-*` script and are not enumerated row-by-row.

### `manage-*` scripts

| Script | Operation | Canonical form |
|---|---|---|
| `manage-architecture` | Resolve a build command for a module | `architecture resolve --command {cmd} --module {name}` |
| `manage-architecture` | Read a module entry | `architecture module --module {name}` |
| `manage-architecture` | Read a derived module entry | `architecture derived-module --module {name}` |
| `manage-architecture` | List commands for a module | `architecture commands --module {name}` |
| `manage-architecture` | List sibling modules | `architecture siblings --module {name}` |
| `manage-config` | Get a phase config field | `manage-config plan {phase} get [--field {name}] --audit-plan-id {id}` |
| `manage-config` | Set a phase config field | `manage-config plan {phase} set --field {name} --value {v} --audit-plan-id {id}` |
| `manage-config` | Read an effort target | `manage-config effort read [--role {role} \| --phase {phase} --role {subkey} \| --default]` |
| `manage-config` | Resolve a recipe definition | `manage-config resolve-recipe --recipe {key}` |
| `manage-lessons` | Read a lesson by id | `manage-lessons get --lesson-id {id}` |
| `manage-logging` | Emit a warning-level log entry | `manage-logging work --plan-id {id} --level WARNING --message "{msg}"` |
| `manage-references` | Read the entire references body | `manage-references read --plan-id {id}` |
| `manage-references` | Get one field from references | `manage-references get --plan-id {id} --field {name}` |
| `manage-references` | Set one field in references | `manage-references set --plan-id {id} --field {name} --value {v}` |
| `manage-status` | Read plan status | `manage_status read --plan-id {id}` |
| `manage-status` | Get a metadata field | `manage_status metadata --get --plan-id {id} --field {name}` |
| `manage-status` | Set a metadata field | `manage_status metadata --set --plan-id {id} --field {name} --value {v}` |
| `manage-status` | Transition to next phase | `manage_status transition --plan-id {id} --completed {phase}` |
| `manage-status` | Resolve the worktree path for a plan | `manage_status get-worktree-path --plan-id {id}` |
| `manage-status` | Classify a change type heuristically | `manage_status change-type-heuristic --plan-id {id}` |
| `manage-tasks` | Read a task body | `manage-tasks read --plan-id {id} --task-number {n}` |
| `manage-tasks` | Update a task | `manage-tasks update --plan-id {id} --task-number {n}` |
| `manage-tasks` | Finalize a step | `manage-tasks finalize-step --plan-id {id} --task-number {n} --step {s} --outcome {done|failed|skipped}` |

The script name for `manage-status` rows is spelled `manage_status` (underscore) because the on-disk filename is `manage_status.py` and the executor's 3-part notation MUST match the filename; the skill directory is still `manage-status` (kebab-case) per bundle convention. See [`tools-script-executor/standards/notation.md`](../../../tools-script-executor/standards/notation.md) for the notation-to-path resolution rule.

### `workflow-integration-git:git_workflow`

The git workflow script provides commit-message formatting, diff analysis, artifact detection, and the full worktree CRUD surface (`worktree-path`, `worktree-create`, `worktree-remove`, `worktree-list`, `worktree-rebase-to`) plus the `baseline-reconcile` mechanical reconciliation verb. There is no `commit`, `push`, or `branch-create` subcommand — those operations go through provider-neutral `git` calls in skill workflows (`git -C {path} commit ...`, `git -C {path} push ...`, `git -C {path} switch -c ...`) or through `tools-integration-ci:ci` for PR-level branch creation. The 3-part script notation is `plan-marshall:workflow-integration-git:git_workflow` (the third segment matches the on-disk filename `git_workflow.py`).

| Operation | Canonical form |
|---|---|
| Format a conventional commit message | `git_workflow format-commit --type {type} [--scope {s}] --subject "{subject}" [--body "{b}"] [--breaking "{desc}"] [--footer "{f}"]` |
| Capture and analyze a worktree diff | `git_workflow analyze-diff --worktree-path {path} [--cached]` |
| Scan for committable artifacts | `git_workflow detect-artifacts [--root {path}] [--no-gitignore]` |
| Resolve the worktree path for a plan | `git_workflow worktree-path --plan-id {id}` |
| Create a worktree + feature branch + .plan symlink | `git_workflow worktree-create --plan-id {id} --branch {name} [--base {ref}]` |
| Remove a worktree | `git_workflow worktree-remove --plan-id {id} [--force]` |
| Enumerate plans that declare a worktree | `git_workflow worktree-list` |
| Rebase a worktree onto a base ref | `git_workflow worktree-rebase-to --plan-id {id} --base {ref}` |
| Baseline reconcile (phase-2-refine Step 3d) | `git_workflow baseline-reconcile --plan-id {id} [--base-branch {ref}] [--worktree-path {path}] [--skip-fetch] [--no-emit]` |

### `tools-integration-ci:ci` (provider-agnostic CI router)

The `pr`, `ci`, `issue`, and `branch` subcommand surfaces are common across providers; provider-specific extensions (e.g., `pr submit-review` on GitHub) follow the same flag conventions. The router consumes the routing pair `--plan-id {id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {path}` (escape hatch / legacy) before delegating to the provider script. The two flags are mutually exclusive — see `tools-script-executor/standards/cwd-policy.md` § "Bucket B" for the canonical two-state contract.

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

### `choices=` vs `type=` when the data layer normalizes

argparse's `choices=[...]` parameter compares each incoming CLI token literally against the supplied list — the check fires **before** any per-argument `type=` callable runs, and well before the script's handler functions get a chance to normalize. When the data layer behind a flag is alias-aware (it accepts `passed`, `PASSED`, `Passed` and stores `PASS`), pairing it with `choices=` against a single literal spelling causes argparse to reject every other spelling at parse time, hiding the aliasing the data layer was designed to provide.

**Failure mode**: `add_argument('--outcome', choices=['PASS', 'FAIL'])` against a handler that maps `passed -> PASS` and `failed -> FAIL`. The invocation `--outcome passed` returns argparse's `usage: ... error: argument --outcome: invalid choice: 'passed' (choose from 'PASS', 'FAIL')` with exit code 2 — argparse never reaches the handler, so the alias is silently inaccessible from the CLI even though the in-process API supports it. Symptom-by-proxy: a `manage-*` script accepts a value programmatically (via Python imports) but refuses the same value on the command line.

**Corrective pattern**: replace `choices=...` with `type=callable_normalizer`, where `callable_normalizer` accepts a string, attempts alias resolution against the data layer, and raises `argparse.ArgumentTypeError(...)` on unknown tokens. The exception bubbles back through argparse with the same exit-code-2 surface, so failure semantics are preserved while accepted aliases pass through unchanged.

```python
_OUTCOME_ALIASES = {'passed': 'PASS', 'failed': 'FAIL'}

def normalize_outcome(value: str) -> str:
    folded = value.casefold()
    if folded in _OUTCOME_ALIASES:
        return _OUTCOME_ALIASES[folded]
    if value in _OUTCOME_ALIASES.values():
        return value
    raise argparse.ArgumentTypeError(
        f"invalid outcome: {value!r} (expected one of: PASS, FAIL, passed, failed)"
    )

parser.add_argument('--outcome', type=normalize_outcome, required=True)
```

The error message in `ArgumentTypeError` is what argparse renders in its usage line — keep it specific so users see the same alias list the data layer accepts, not a single canonical spelling.

**Test-coverage requirement**: every script that adopts the `type=callable_normalizer` pattern MUST have at least one subprocess-level CLI test exercising one alias path. An in-process unit test of the normalizer callable is necessary but not sufficient — only a subprocess test pins down the full argparse pipeline (the same pipeline that misbehaved when `choices=` was in place). The canonical shape:

```python
result = subprocess.run(
    ['python3', str(script_path), 'verb', '--outcome', 'passed', ...],
    capture_output=True, text=True,
)
assert result.returncode == 0, result.stderr  # The alias path reaches the handler
```

**Scope note**: this subsection lives going forward — no audit / convert / backport pass against existing `manage-*` scripts that still use `choices=` is performed in the plan that introduces it. Existing `choices=` usages remain valid until a future task explicitly rewrites them; new argparse declarations against alias-aware data layers MUST follow this pattern.

## Enforcement

The canonical forms above are enforced automatically by the `ARGUMENT_NAMING_*` rule cluster in `pm-plugin-development:plugin-doctor:doctor-marketplace` (see [`plugin-doctor/references/rule-catalog.md`](../../../../pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md) → "Argument Naming Rules"). The cluster scans `SKILL.md`, agent prose, recipes, and standards under `marketplace/bundles/*/` for `python3 .plan/execute-script.py {notation} ...` invocations and validates each token against the executor's `SCRIPTS` mapping and the target script's argparse declarations:

- `ARGUMENT_NAMING_NOTATION_INVALID` — flags 3-part notations that do not resolve in the executor mapping (snake_case bundles, self-referential repetition, unregistered skills).
- `ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN` — flags subcommands not declared in the resolved script's `subparsers.choices`.
- `ARGUMENT_NAMING_FLAG_UNKNOWN` — flags `--{flag}` tokens not declared via `add_argument` on the matched subparser.
- `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` — cross-checks every row above against the live argparse declarations and fails on drift.

Together, these rules close the loop between this standard and the implementation: a row added here is enforceable on the next `verify`; a flag renamed in argparse fails this standard's row until both sides agree.

## Related

- `agent-behavior-rules.md` — Boy Scout rule and overall development discipline.
- `tool-usage-patterns.md` — Tool selection and Bash safety rules that govern how these scripts are invoked.
- `pm-plugin-development:plugin-doctor` rule catalog — automated enforcement of this standard's canonical forms.
