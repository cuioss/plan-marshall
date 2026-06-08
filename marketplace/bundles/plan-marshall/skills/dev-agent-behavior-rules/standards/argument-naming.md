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

### Rule 5 — List-verb canonicalization

For the operation-class "return a collection of records", use the verb `list`. Filter dimensions are expressed as flags on `list`, not as distinct subcommand verbs.

- Canonical verb: `list` (e.g., `manage-findings list`, `manage-tasks list`).
- Filter dimensions are `--{dimension}` flags: `manage-tasks list --domain {d}`, `manage-tasks list --profile {p}`.
- Domain-qualified verbs (`tasks-by-domain`, `tasks-by-profile`) and operation-specific synonyms (`query` for a collection read) are drift — rename them to `list` plus a filter flag.
- A qualified list verb is kept ONLY where one script has multiple distinct list targets and the qualifier disambiguates which collection is listed; record the keep-decision rationale at the call site.

This rule is distinct from Rule 2: Rule 2's `read` / `get` / `exists` tiers cover single-record and scalar reads and are NOT affected. Rule 5 governs only the collection-listing operation-class.

**Why**: an LLM pattern-matching from one `manage-*` script to another guesses the verb for "list the records". When one script spells it `query`, another `list`, and a third `tasks-by-domain`, the guess is wrong more often than right, producing silent `exit_code: 2` argparse rejections. One verb per operation-class makes the guess correct by construction.

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
| `manage-findings` | Add a plan-scoped finding | `manage-findings add --plan-id {id} --type {type} --title "{t}" --detail "{d}" [--file-path {p}] [--line {n}] [--component {c}] [--module {m}] [--rule {r}] [--severity error\|warning\|info]` |
| `manage-findings` | List plan-scoped findings | `manage-findings list --plan-id {id} [--type {csv}] [--resolution {res}] [--promoted {bool}] [--file-pattern {glob}]` |
| `manage-findings` | Get a single finding | `manage-findings get --plan-id {id} --hash-id {hash}` |
| `manage-findings` | Resolve a finding | `manage-findings resolve --plan-id {id} --hash-id {hash} --resolution {res} [--detail "{d}"]` |
| `manage-findings` | Add a Q-Gate finding | `manage-findings qgate add --plan-id {id} --phase {phase} --source qgate\|user_review --type {type} --title "{t}" --detail "{d}" [--file-path {p}] [--component {c}] [--severity error\|warning\|info] [--iteration {n}]` |
| `manage-findings` | List Q-Gate findings | `manage-findings qgate list --plan-id {id} --phase {phase} [--resolution {res}] [--source qgate\|user_review] [--iteration {n}]` |
| `manage-findings` | Resolve a Q-Gate finding | `manage-findings qgate resolve --plan-id {id} --hash-id {hash} --resolution {res} --phase {phase} [--detail "{d}"]` |
| `manage-findings` | Clear Q-Gate findings for a phase | `manage-findings qgate clear --plan-id {id} --phase {phase}` |
| `manage-findings` | List component assessments | `manage-findings assessment list --plan-id {id} [--certainty {c}] [--min-confidence {n}] [--max-confidence {n}] [--file-pattern {glob}]` |
| `manage-tasks` | List tasks (optionally filtered) | `manage-tasks list --plan-id {id} [--status {s}] [--deliverable {n}] [--ready] [--domain {d}] [--profile {p}]` |
| `manage-lessons` | Read a lesson by id | `manage-lessons get --lesson-id {id}` |
| `manage-logging` | Emit a warning-level log entry | `manage-logging work --plan-id {id} --level WARNING --message "{msg}"` |
| `manage-references` | Read the entire references body | `manage-references read --plan-id {id}` |
| `manage-references` | Get one field from references | `manage-references get --plan-id {id} --field {name}` |
| `manage-references` | Set one field in references | `manage-references set --plan-id {id} --field {name} --value {v}` |
| `manage-status` | Read plan status | `manage-status read --plan-id {id}` |
| `manage-status` | Get a metadata field | `manage-status metadata --get --plan-id {id} --field {name}` |
| `manage-status` | Set a metadata field | `manage-status metadata --set --plan-id {id} --field {name} --value {v}` |
| `manage-status` | Transition to next phase | `manage-status transition --plan-id {id} --completed {phase}` |
| `manage-status` | Resolve the worktree path for a plan | `manage-status get-worktree-path --plan-id {id}` |
| `manage-status` | Classify a change type heuristically | `manage-status change-type-heuristic --plan-id {id}` |
| `manage-tasks` | Read a task body | `manage-tasks read --plan-id {id} --task-number {n}` |
| `manage-tasks` | Update a task | `manage-tasks update --plan-id {id} --task-number {n}` |
| `manage-tasks` | Finalize a step | `manage-tasks finalize-step --plan-id {id} --task-number {n} --step {s} --outcome {done|failed|skipped}` |

The script notation third segment for `manage-status` rows is `manage-status` — every `manage-*` entrypoint filename is kebab-case, matching the skill directory and the executor's 3-part notation. See [`tools-script-executor/standards/notation.md`](../../../tools-script-executor/standards/notation.md) for the notation-to-path resolution rule.

### `workflow-integration-git:git-workflow`

The git workflow script provides commit-message formatting, diff analysis, artifact detection, and the full worktree CRUD surface (`worktree-path`, `worktree-create`, `worktree-remove`, `worktree-list`, `worktree-rebase-to`) plus the `baseline-reconcile` mechanical reconciliation verb. There is no `commit`, `push`, or `branch-create` subcommand — those operations go through provider-neutral `git` calls in skill workflows (`git -C {path} commit ...`, `git -C {path} push ...`, `git -C {path} switch -c ...`) or through `tools-integration-ci:ci` for PR-level branch creation. The 3-part script notation is `plan-marshall:workflow-integration-git:git-workflow` (the third segment matches the on-disk filename `git-workflow.py`).

| Operation | Canonical form |
|---|---|
| Format a conventional commit message | `git-workflow format-commit --type {type} [--scope {s}] --subject "{subject}" [--body "{b}"] [--breaking "{desc}"] [--footer "{f}"]` |
| Capture and analyze a worktree diff | `git-workflow analyze-diff --worktree-path {path} [--cached]` |
| Scan for committable artifacts | `git-workflow detect-artifacts [--root {path}] [--no-gitignore]` |
| Resolve the worktree path for a plan | `git-workflow worktree-path --plan-id {id}` |
| Create a worktree + feature branch + .plan symlink | `git-workflow worktree-create --plan-id {id} --branch {name} [--base {ref}]` |
| Remove a worktree | `git-workflow worktree-remove --plan-id {id} [--force]` |
| Enumerate plans that declare a worktree | `git-workflow worktree-list` |
| Rebase a worktree onto a base ref | `git-workflow worktree-rebase-to --plan-id {id} --base {ref}` |
| Baseline reconcile (phase-2-refine Step 3d) | `git-workflow baseline-reconcile --plan-id {id} [--base-branch {ref}] [--worktree-path {path}] [--skip-fetch] [--no-emit]` |

### `tools-integration-ci:ci` (provider-agnostic CI router)

The `pr`, `checks`, `issue`, and `branch` subcommand surfaces are common across providers; provider-specific extensions (e.g., `pr submit-review` on GitHub) follow the same flag conventions. The router consumes the routing pair `--plan-id {id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {path}` (escape hatch / legacy) before delegating to the provider script. The two flags are mutually exclusive — see `tools-script-executor/standards/cwd-policy.md` § "Bucket B" for the canonical two-state contract.

| Operation | Canonical form |
|---|---|
| Create a pull request | `ci pr create --title "{title}" --plan-id {id}` |
| View the PR for the current branch | `ci pr view` |
| List pull requests | `ci pr list [--head {branch}] [--state open|closed|all]` |
| Reply to a PR | `ci pr reply --pr-number {n} --plan-id {id} [--slot {slot}]` (body via prior `ci pr prepare-comment --for reply`) |
| Resolve a review thread | `ci pr resolve-thread --thread-id {id}` |
| Reply within a thread | `ci pr thread-reply --pr-number {n} --thread-id {thread_id} --plan-id {id} [--slot {slot}]` (body via prior `ci pr prepare-comment --for thread-reply`) |
| Get PR reviews | `ci pr reviews --pr-number {n}` |
| Get PR inline comments | `ci pr comments --pr-number {n} [--unresolved-only]` |
| Wait for new bot comments | `ci pr wait-for-comments --pr-number {n} [--timeout {s}] [--interval {s}]` |
| Merge a pull request | `ci pr merge {--pr-number {n} \| --head {branch}} [--strategy merge\|squash\|rebase] [--delete-branch]` |
| Edit PR title or body | `ci pr edit --pr-number {n} --plan-id {id} [--title "{title}"] [--slot {slot}]` (body via prior `ci pr prepare-body`) |
| Check CI status | `ci checks status {--pr-number {n} \| --head {branch}}` |
| Wait for CI to complete | `ci checks wait --pr-number {n} [--timeout {s}] [--interval {s}]` |
| Wait for CI status flip | `ci checks wait-for-status-flip --pr-number {n} [--timeout {s}] [--interval {s}] [--expected success\|failure\|any]` |
| Rerun a workflow | `ci checks rerun --run-id {id}` |
| Get failed run logs | `ci checks logs --run-id {id}` |
| Create an issue | `ci issue create --title "{title}" [--labels {csv}] --body-file {path}` |
| View an issue | `ci issue view --issue {id}` |
| Close an issue | `ci issue close --issue {id}` |
| Wait for issue close | `ci issue wait-for-close --issue-number {n} [--timeout {s}] [--interval {s}]` |
| Wait for issue label | `ci issue wait-for-label --issue-number {n} --label {name} [--mode present\|absent]` |
| Delete remote branch | `ci branch delete --remote-only --branch {name}` |

### `pm-plugin-development:plugin-doctor:doctor-marketplace`

| Operation | Canonical form |
|---|---|
| List components | `doctor-marketplace list-components [--bundles {csv}]` |
| List explicit component paths | `doctor-marketplace list-components --paths {path} [{path} ...]` |
| Analyze components | `doctor-marketplace analyze [--bundles {csv}] [--type {csv}] [--name {csv}]` |
| Apply safe fixes | `doctor-marketplace fix [--bundles {csv}] [--type {csv}] [--name {csv}] [--dry-run]` |
| Generate report | `doctor-marketplace report [--bundles {csv}] [--output {dir}]` |
| Run quality gate (scoped) | `doctor-marketplace quality-gate [--paths {path} ...] [--marketplace-root {dir}]` |
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

The canonical forms above are enforced automatically by the `ARGUMENT_NAMING_*` rule cluster in `pm-plugin-development:plugin-doctor:doctor-marketplace` (see [`plugin-doctor/references/rule-catalog.md`](../../../../pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md) → "Argument Naming Rules"). The cluster scans `SKILL.md`, agent prose, recipes, standards, and workflow docs under `marketplace/bundles/*/` for `python3 .plan/execute-script.py {notation} ...` invocations and validates each token against the executor's `SCRIPTS` mapping and the target script's argparse declarations:

- `ARGUMENT_NAMING_NOTATION_INVALID` — flags 3-part notations that do not resolve in the executor mapping (snake_case bundles, self-referential repetition, unregistered skills).
- `ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN` — flags subcommands not declared in the resolved script's `subparsers.choices`.
- `ARGUMENT_NAMING_FLAG_UNKNOWN` — flags `--{flag}` tokens not declared via `add_argument` on the matched subparser.
- `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` — cross-checks every row above against the live argparse declarations and fails on drift.

Together, these rules close the loop between this standard and the implementation: a row added here is enforceable on the next `verify`; a flag renamed in argparse fails this standard's row until both sides agree.

## Related

- `agent-behavior-rules.md` — Boy Scout rule and overall development discipline.
- `tool-usage-patterns.md` — Tool selection and Bash safety rules that govern how these scripts are invoked.
- `pm-plugin-development:plugin-doctor` rule catalog — automated enforcement of this standard's canonical forms.
