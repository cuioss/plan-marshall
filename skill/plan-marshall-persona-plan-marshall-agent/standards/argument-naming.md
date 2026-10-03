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

An argument is **entity-identifying** when its value names *which instance* of a first-class entity the command acts on. Every such argument is spelled **entity-noun-first**: the entity noun is mandatory and comes first, and any suffix names the *kind of value*, never the entity. The suffix set is closed:

| Suffix | Value kind |
|---|---|
| _(none)_ | the entity's plain human-readable name |
| `-id` | an assigned or opaque identifier |
| `-number` | an ordinal within a scope |
| `-slug` | a kebab-case human-readable key, used only where the entity ALSO carries an `-id` and the two must stay distinguishable |

The entity-to-flag mapping:

| Entity | Canonical flag |
|---|---|
| Lesson | `--lesson-id` |
| Plan | `--plan-id` |
| Epic | `--epic` |
| Task | `--task-number` |
| Module | `--module` |
| Component | `--component` |

A flag that names only the value kind — `--id`, `--name`, `--slug`, `--number` standing alone — is **not** an entity-identifying flag and must not be used as one. Reserve `--id` for untyped contexts only: hash IDs of opaque records where the entity type is implicit in the subcommand, and where no second entity can appear on the same parser.

**Why**: callers conceptualize values by type, not by the abstract notion of "an identifier". A script that takes `--lesson-id` matches the way every skill, agent prompt, and lesson record refers to the value; a script that takes `--id` forces every caller to remember which flavour of identifier this particular script wanted.

**Why the entity noun is mandatory**: a spelling that carries no entity cannot be reused when a *second* entity appears on the same parser, so that second entity gets named around the incumbent instead of by its own name. The epic's former `--slug` spelling is the worked example — it named the value's shape rather than the entity, and the plan's slug on the same parser had to become `--slug-value` as a result. An entity-first spelling leaves the next entity a name to use.

The epic entity and the `--epic` / `--slug` reconciliation, the reasons the plan does not collapse into it, and the disposition of each existing `--name` and `--target` occupant are decided in [ADR-023](../../../../../../doc/adr/023-Entity_identifying_CLI_parameters_use_one_typed_vocabulary.adoc).

### Rule 2 — Read-verb canonicalization

Use the verb that matches the operation's semantics:

| Verb | Use when |
|---|---|
| `read` | Returning the contents of a scoped artifact (file, document, record body). |
| `get` | Returning a computed or derived value (a config field, a resolved command, a computed status). |
| `exists` | Boolean probe. Must never error on absence — return `exists: false` instead. |

**Why**: callers reach for `read` when they want a body and `get` when they want a value. Mixing these — for example using `get` to return a record body — produces typos that cost time at every call site and make scripts in the same bundle feel arbitrarily inconsistent.

**Accepted-secondary spellings**: three single-record read verbs accept the sibling spelling as an argparse alias so the two interchangeable forms both resolve to the same handler. The canonical verb in the left column stays primary — it is the form documentation and new call sites use; the alias is accepted only so an existing call site spelling the other verb does not fail at parse time:

| Script | Canonical verb | Accepted alias |
|---|---|---|
| `manage-lessons` | `get` | `read` |
| `manage-tasks` | `read` | `get` |
| `manage-status` | `read` | `get` |

The alias is purely additive at the CLI boundary; it does not change which verb Rule 2's semantics prescribe, and it does not introduce a second handler.

### Rule 3 — `--name` is not an entity spelling

`--module` over `--name` for a module argument is the general case of Rule 1, not a module-specific carve-out: `--name` names the *kind of value* and carries no entity, so it fails the entity-noun-first test exactly as `--id` and `--slug` do. The same substitution applies to every entity — an argument naming a component is `--component`, one naming an epic is `--epic`, and so on.

`--name` is reserved for arguments that are **not** entity-identifying at all: a generic string the command *writes* or matches on, rather than an identity selecting which record it acts on. The discriminator is Rule 1's: does this value name which instance the command acts on?

- `run_config commit-trailer set --name` supplies a co-author name the command writes into configuration. It selects no record, so `--name` is correct and stays.
- An argument that resolves a module, a component, or any other entity is that entity's flag, whatever the referent looks like as a string.

The same test governs `--target`, which is entity-identifying only where its value names a runtime target by name; where it carries a payload string or a closed selector enum (`{global,project}`, `{all,temp,logs,…}`) it is outside the partition and Rule 1 does not reach it.

**Why**: the caller's mental model is about the *referent* (which module), not the *kind of value* (a string name). Using `--module` makes that referent explicit at the call site, where the cost of confusion is highest.

The per-occupant dispositions this rule's reserved clause agrees with are recorded in [ADR-023](../../../../../../doc/adr/023-Entity_identifying_CLI_parameters_use_one_typed_vocabulary.adoc) § "(c) The fate of each existing `--name` occupant".

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

**What the rows are measured against.** A row here is not a wish: it is a claim about a script's live argparse declaration, and `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` checks it against that declaration on every `quality-gate` run. The rule is build-failing, so a row and the script it prescribes are a coupled pair — neither may be moved to a new spelling while the other lags. Concretely, a rename lands the `add_argument` change and its row in the **same commit**; splitting them fails the gate on every commit in between. Per [ADR-017](../../../../../../doc/adr/017-A_validator_derives_its_contract_from_the_targets_own_declaration_and_fails_closed_when_it_cannot.adoc), the remedy for a row the rule flags is to fix the row or the declaration, never to suppress or annotate the rule.

**The governing framework is Rules 1–5 above, and the rows are its instances.** Where a row's spelling and the rules disagree, the rules are the authority and the row is drift awaiting a rename. [ADR-023](../../../../../../doc/adr/023-Entity_identifying_CLI_parameters_use_one_typed_vocabulary.adoc) decides the entity vocabulary the rows are measured against; **the rows below are not yet brought into line with it**. Because no flag has been renamed, a row rewritten here to a decided-but-unimplemented spelling would fail the drift gate immediately. Those rewrites belong to the follow-on rename plan, where each row moves in the same commit as the argparse declaration it prescribes — not here.

**Rule-1 conformance is not a substitute for reading the live surface.** The drift rule parses only rows whose third column is a lone backticked form in a three-column table; a row carrying trailing prose after the backticks, and every row of the two-column per-script tables below, is outside its reach. Those rows are governed by the same rules but are not machine-checked, so they can go stale silently — treat the script's own `## Canonical invocations` section as authoritative when the two disagree.

The cross-cutting `--plan-id` and `--audit-plan-id` flags are accepted by virtually every `manage-*` script and are not enumerated row-by-row.

**Shorthand resolution.** The first token in each row is a script shorthand that the drift rule resolves to a registered executor notation by third-segment match. The generated `default-bundle:` mirror duplicates every marketplace script for the OpenCode target; the rule ignores the mirror when a marketplace-native candidate exists, per the executor resolver-root priority (tree code wins). A row therefore names the marketplace-native script even when a mirror with the same short name is registered.

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
| `manage-lessons` | Read a lesson by id | `manage-lessons get --lesson-id {id}` (alias: `read`) |
| `manage-logging` | Emit a warning-level log entry | `manage-logging work --plan-id {id} --level WARNING --message "{msg}"` |
| `manage-references` | Read the entire references body | `manage-references read --plan-id {id}` |
| `manage-references` | Get one field from references | `manage-references get --plan-id {id} --field {name}` |
| `manage-references` | Set one field in references | `manage-references set --plan-id {id} --field {name} --value {v}` |
| `manage-status` | Read plan status | `manage-status read --plan-id {id}` (alias: `get`) |
| `manage-status` | Get a metadata field | `manage-status metadata --get --plan-id {id} --field {name}` |
| `manage-status` | Set a metadata field | `manage-status metadata --set --plan-id {id} --field {name} --value {v}` |
| `manage-status` | Transition to next phase | `manage-status transition --plan-id {id} --completed {phase}` |
| `manage-status` | Resolve the worktree path for a plan | `manage-status get-worktree-path --plan-id {id}` |
| `manage-status` | Classify a change type heuristically | `manage-status change-type-heuristic --plan-id {id}` |
| `manage-tasks` | Read a task body | `manage-tasks read --plan-id {id} --task-number {n}` (alias: `get`) |
| `manage-tasks` | Update a task | `manage-tasks update --plan-id {id} --task-number {n}` |
| `manage-tasks` | Finalize a step | `manage-tasks finalize-step --plan-id {id} --task-number {n} --step {s} --outcome {done|failed|skipped}` |

The script notation third segment for `manage-status` rows is `manage-status` — every `manage-*` entrypoint filename is kebab-case, matching the skill directory and the executor's 3-part notation. See [`tools-script-executor/SKILL.md`](../../tools-script-executor/SKILL.md) § "Notation Format" for the notation-to-path resolution rule.

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
| List pull requests | `ci pr list [--head {branch}] [--state open\|closed\|all] [--limit {n}]` (`--limit` and the returned `truncated` field are **GitHub-only**, `--limit` defaulting to 100; GitLab argparse-rejects `--limit` and reports no `truncated`, so a GitLab `total` is a page rather than a population) |
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
    raise argparse.ArgumentTypeError(f'invalid outcome: {value!r} (expected one of: PASS, FAIL, passed, failed)')


parser.add_argument('--outcome', type=normalize_outcome, required=True)
```

The error message in `ArgumentTypeError` is what argparse renders in its usage line — keep it specific so users see the same alias list the data layer accepts, not a single canonical spelling.

**Test-coverage requirement**: every script that adopts the `type=callable_normalizer` pattern MUST have at least one subprocess-level CLI test exercising one alias path. An in-process unit test of the normalizer callable is necessary but not sufficient — only a subprocess test pins down the full argparse pipeline (the same pipeline that misbehaved when `choices=` was in place). The canonical shape:

```python
result = subprocess.run(
    ['python3', str(script_path), 'verb', '--outcome', 'passed', ...],
    capture_output=True,
    text=True,
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
