# The test tree

Navigation and ownership for the Python test corpus: what lives where, what the
shared surfaces own, and where a new helper belongs.

This is **not** a restatement of the testing standards. How to write a test —
naming, AAA structure, fixture scoping, parametrization, isolation idioms,
mocking, assertion style — is owned by:

- [`pm-dev-python:pytest-testing`](../marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md)
  — pytest mechanics and Python-specific patterns.
- [`plan-marshall:persona-module-tester`](../marketplace/bundles/plan-marshall/skills/persona-module-tester/SKILL.md)
  — language-agnostic testing methodology.

Where this file and those skills disagree, the skills win.

## Layout

```text
test/
├── conftest.py                  # the one root conftest — the shared surface
├── README.md                    # this file
├── test_conftest_discipline.py  # root-level meta-tests: guards over the tree itself
├── test_runner_falsifiability.py
├── test_shared_harness.py
├── _shared/                     # bundle-neutral helpers, importable by bare name
│   └── _poll_until.py …
├── fixtures/                    # static fixture data (no .py)
└── {bundle}/                    # one directory per marketplace bundle
    └── {skill}/                 # …and per skill, where a bundle has many
        ├── test_*.py            # the tests
        └── _{domain}_fixtures.py  # helpers used only inside this subtree
```

A root-level `test_*.py` is a **meta-test**: a guard whose subject is the tree
or the toolchain rather than a marketplace script. New meta-tests go here beside
their siblings.

## What `test/conftest.py` owns

It is the single shared surface, on `sys.path` for every test, and it owns:

| Surface | What it gives you |
|---|---|
| `load_script_module(bundle, skill, script)` | Import a marketplace script as a module, addressed from the skill's `scripts/` directory. **Use this instead of hand-rolling `spec_from_file_location`.** Pass `register=False` when only the returned object is needed, so the load cannot displace a name another module imports plainly. |
| `load_skill_module(bundle, skill, file)` | The same, addressed from the SKILL ROOT — for a file that is not under `scripts/`, such as a bundle's `plan-marshall-plugin/extension.py`. Pass a distinct `module_name`: every bundle ships that file under the same stem. |
| `get_scripts_dir` / `get_script_path` | Resolve a skill's `scripts/` directory. **Use this instead of `Path(__file__).parent.parent…` arithmetic.** |
| `get_skill_dir(bundle, skill)` | Resolve the skill directory itself, for a skill that ships no `scripts/` tree. |
| `add_skill_scripts_to_path` | The narrow escape hatch for sibling modules that import each other by bare name. |
| `run_script(...)` → `ScriptResult` | Run a script as a subprocess. |
| `parse_ns(bundle, skill, script, *argv)` | Build an `argparse.Namespace` **from the script's own parser**, so it carries the parser's defaults. Use instead of `argparse.Namespace(...)`. |
| `create_marshal_json(...)` / `create_run_config(...)` | Stage `marshal.json` / `run-configuration.json` fixtures, from a named preset or a full config. |
| `create_raw_project_data(...)` | Stage the module-facts companion. |
| `plan_context` / `PlanContext` / `BuildContext` | Pre-wired plan and build environments. |
| `create_temp_file` / `create_temp_dir` / `load_fixture` | Small file helpers. |
| The autouse isolation fixtures | See below — they apply whether or not you ask. |

### What it deliberately does not own

- **Anything bundle-specific.** A helper that knows a particular script's
  arguments, output shape, or config vocabulary belongs to that subtree, not here.
- **Assertion helpers for one domain.** `assert_valid_module` and friends live in
  the subtree that has modules.
- **A second way to do something it already does.** If `load_script_module`
  nearly fits, extend the call, do not add a parallel loader. `load_skill_module`
  is not an exception to that rule but an application of it: the two resolve
  against **different roots**, which is a different question rather than a second
  answer to the same one. Making one loader guess the root from what happens to
  exist on disk is what the pair exists to avoid — the caller says which it means.
- **Nested `conftest.py` files.** There is exactly one, and
  `test_conftest_discipline.py` enforces that. A sibling conftest shadows others
  during discovery and leaks fixtures across unrelated modules.

## `test/_shared/` versus `_{domain}_fixtures.py`

Both hold helpers. They differ in **audience**, and the difference is what the
promotion rule below turns on.

| | `test/_shared/*.py` | `{subtree}/_{domain}_fixtures.py` |
|---|---|---|
| Audience | Every bundle | One subtree |
| Import | Bare name, from anywhere (`conftest.py` puts it on `sys.path`) | Bare name, from inside that subtree |
| Knows about | No bundle in particular | Its own domain's scripts and vocabulary |
| Example | `_poll_until.py` — a bounded-poll primitive with no domain knowledge | `_manage_config_fixtures.py` — the manage-config script path and its config baselines |

Naming is not cosmetic. A helper module must be `_{domain}_fixtures.py`: never
`test_*.py` (pytest collects it, and a helper that collects zero tests is a
silent no-op in the run), never a nested `conftest.py`, and never a bare
`_fixtures.py` or `_helpers.py` (basenames must be unique tree-wide, because
they are imported by bare name).

## Where does a new helper go?

Count the **subtrees** that use it — not the modules, not the call sites.

| Used by | Where it goes | Who decides |
|---|---|---|
| **One** subtree | That subtree's `_{domain}_fixtures.py`. Create the file if it does not exist. | **You.** This is an ordinary edit inside your own subtree. |
| **Two** subtrees | Still local. Put it in one subtree's fixtures module and import it, or accept the duplication until a third consumer appears. | **You**, but say so in your change description. |
| **Three or more** subtrees | `test/conftest.py` or `test/_shared/` — but **not yet**. Three consumers make it a **promotion proposal**. | **The operator.** Propose the promotion and its signature; do not make the edit unilaterally. |

**Three or more subtrees is a proposal, not a licence to edit.** The shared
surfaces are consumed by every bundle's tests at once, so a signature added there
is a signature that becomes expensive to change and that concurrent work will
build against before anyone reviews it. Write the helper locally, record the
promotion as a proposal for the operator, and let the shared edit be made
deliberately.

**Which shared surface to propose**, once a helper has cleared that bar:

- `test/_shared/` for a **self-contained primitive with no domain knowledge** that
  a test imports when it needs it — `_poll_until.py` is the model.
- `test/conftest.py` for something that must be **implicitly available to every
  test**, or that belongs to the resolution machinery already there (script
  loading, path resolution, fixture staging, an autouse fixture).

If it would work as a plain import, propose `test/_shared/`. `conftest.py` is for
what cannot.

**Where to record the proposal.** State it in the change description of the work
that needed it, alongside the local helper you wrote — the same channel the
two-subtree row uses. A run executing a plan under `doc/plans/` records it in that
run's report instead. "The operator" is whoever reviews that change; the point of
the rule is that the shared edit is a separate, reviewed decision, not that any
particular person makes it.

The same rule binds in the other direction: if you are working inside one subtree
and find that `test/conftest.py` or `test/_shared/` lacks something you need, add
it to **your** subtree's `_{domain}_fixtures.py` and propose the promotion. Do not
edit the shared surface in passing.

## The autouse isolation fixtures

These run for **every** test without being requested. Each has one marker that
opts out of it, and each marker is registered in `pyproject.toml` with its full
rationale — read it there before reaching for one.

| Fixture | What it isolates | Opt out with |
|---|---|---|
| `_plan_base_dir_sandbox` | Redirects `PLAN_BASE_DIR` and the `_config_core` paths at a per-test temp tree, so no test reaches the tracked `.plan/`. | `@pytest.mark.allow_pollution` |
| `_credentials_dir_sandbox` | Redirects `CREDENTIALS_DIR` away from the real `~/.plan-marshall/credentials/`. | `@pytest.mark.allow_pollution` |
| `_pollution_guard` | Backstop: snapshots the real credential and plan paths before and after, and fails a test that mutated them. Runs its snapshot only for tests marked `touches_real_state` (auto-applied to every `plan_context` user). | `@pytest.mark.allow_pollution` |
| `_neutralize_daemon_routing` | Patches the `_route_to_daemon` seam to its non-routing outcome, so no test's behaviour depends on whether a `marshalld` daemon is running. Modules under `test/plan-marshall/build-server/` are carved out by location and need no marker. | `@pytest.mark.allow_daemon_routing` |
| `_root_fs_pollution_guard` | Clears the `/nonexistent` absence-sentinel before each test and fails any test that materializes it — a leak only a root host can produce. | `@pytest.mark.allow_root_filesystem_pollution` |

An opt-out marker is an escape hatch for a test whose **subject** is the real
state it reaches. It is never the fix for a test that leaks by accident.

## Running the suite

Build commands are resolved through the build system, never hard-coded — see
[`CLAUDE.md`](../CLAUDE.md) § Build Commands for the canonical invocations and
`doc/developer/build.adoc` for the build system itself.
