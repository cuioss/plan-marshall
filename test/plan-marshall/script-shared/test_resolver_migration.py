#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population-derived parity suite for the single plan-context resolver.

Every Bucket B (working-tree-binding) bundle script must resolve its worktree
through the ONE resolver — ``file_ops.resolve_plan_context``, reached either
directly or through the ``resolve_project_dir`` argv layer that delegates to it
— and must hold no surviving private re-deriver of its own.

Why this suite is population-derived rather than a hand-written checklist
------------------------------------------------------------------------
A checklist of file paths goes stale silently: a new Bucket B script that
re-derives the worktree by hand is simply absent from the list, so the guard
passes while the drift lands. The population here is derived from the LIVE
tree on every run, and the derivation is asserted **non-empty** and asserted to
**cover a pinned floor** — the two failure modes that turn a set-guarding
detector into a vacuous one (an empty population, or a population that quietly
shrinks) both fail the suite loudly.

Why the re-derivation detector is body-based, never name-based
--------------------------------------------------------------
Several private helpers legitimately KEEP a ``_resolve_worktree*`` /
``_resolve_project_dir*`` name after the migration: they are CLI **argument
adapters** that apply a ``--project-dir`` / ``--worktree-path`` escape hatch and
then delegate the actual resolution to the resolver. A name-pattern detector
flags exactly those sanctioned adapters and is therefore a false-positive
generator, not a guard. The detector below classifies a helper by what its BODY
does — shelling out to ``manage-status get-worktree-path``, or reading the
persisted ``worktree_path`` key out of a mapping — so an adapter that delegates
stays silent while a genuine re-deriver is caught.

Both detectors carry positive AND negative controls (see the anti-vacuity
section at the bottom): a detector whose predicate never fires would report a
clean tree for the wrong reason.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT

# =============================================================================
# Derivation constants
# =============================================================================

#: The resolver entry points. ``resolve_plan_context`` is the resolver itself;
#: ``resolve_project_dir`` / ``resolve_from_args`` are the two-state argv layer
#: that delegates to it (proven by
#: ``test_resolve_project_dir_delegates_to_resolve_plan_context`` below, which
#: is what makes "references any of these" equivalent to "resolves through
#: ``resolve_plan_context``").
_RESOLVER_ENTRY_POINTS: frozenset[str] = frozenset(
    {
        'resolve_plan_context',
        'resolve_project_dir',
        'resolve_from_args',
    }
)

#: The ``manage-status`` subcommand that produces the persisted worktree path.
#: A bundle script that puts this literal into an argv list is shelling out to
#: the producer directly instead of going through the resolver.
_GET_WORKTREE_PATH_VERB = 'get-worktree-path'

#: The persisted status-metadata key. A READ of this key inside a private
#: worktree helper is a hand-rolled re-derivation of the worktree face.
_WORKTREE_PATH_KEY = 'worktree_path'

#: Name prefixes of the private helpers that historically re-derived the
#: worktree. The prefixes seed the CANDIDATE set only — the verdict comes from
#: the body classification, never from the name (see module docstring).
_PRIVATE_HELPER_PREFIXES: tuple[str, ...] = (
    '_resolve_worktree',
    '_resolve_project_dir',
)

#: The resolver module itself, identified by path components rather than by a
#: raw substring. It legitimately owns the single ``get-worktree-path``
#: shell-out in the codebase, so it is the ONE exemption from the shell-out
#: assertion.
_RESOLVER_MODULE_COMPONENTS: frozenset[str] = frozenset({'tools-file-ops', 'file_ops.py'})

#: Population members that MUST survive every future re-derivation of this
#: suite's population. These are the Bucket B consumers migrated onto the
#: resolver; if the derivation stops finding one of them, the derivation itself
#: regressed and the suite must fail rather than silently guard a smaller set.
#: Paths are relative to ``marketplace/bundles``.
_PINNED_POPULATION_MEMBERS: frozenset[str] = frozenset(
    {
        'plan-marshall/skills/build-npm/scripts/js_coverage.py',
        'plan-marshall/skills/extension-api/scripts/extension_discovery.py',
        'plan-marshall/skills/manage-architecture/scripts/architecture.py',
        'plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py',
        'plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py',
        'plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py',
        'plan-marshall/skills/phase-5-execute/scripts/verify_failure_scope.py',
        'plan-marshall/skills/script-shared/scripts/build/_build_cli.py',
        'plan-marshall/skills/script-shared/scripts/resolve_project_dir.py',
        'plan-marshall/skills/tools-integration-ci/scripts/ci_base.py',
        'plan-marshall/skills/workflow-integration-git/scripts/_cmd_baseline_reconcile.py',
        'plan-marshall/skills/workflow-integration-git/scripts/_cmd_force_push.py',
        'plan-marshall/skills/workflow-integration-git/scripts/_cmd_prune_ref.py',
        'plan-marshall/skills/workflow-integration-git/scripts/_cmd_switch_and_pull.py',
        'plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py',
        'plan-marshall/skills/workflow-integration-git/scripts/integrate_into_main.py',
        'pm-dev-java/skills/manage-maven-profiles/scripts/profiles.py',
        'pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py',
    }
)


# =============================================================================
# AST predicates — each one takes a node so it can be applied to a whole module
# OR to a single function body.
# =============================================================================


def _references_resolver(node: ast.AST) -> bool:
    """True when ``node``'s subtree names any resolver entry point.

    Four shapes count, matching the plugin-doctor analyzer's equivalent
    (``_references_name`` in ``_analyze_plan_path_in_scripts.py``): a bare
    name, an attribute access, ``from … import <entry_point>`` (including an
    aliased import such as ``from resolve_project_dir import resolve_from_args
    as _resolve``, where the bound name never appears as a matching
    ``ast.Name``), and ``from <entry_point> import …`` where the entry point is
    the MODULE being imported. Without the import arms an aliased or
    import-only reference is invisible, and such a script escapes both the
    population-parity test and the re-deriver check.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in _RESOLVER_ENTRY_POINTS:
            return True
        if isinstance(sub, ast.Attribute) and sub.attr in _RESOLVER_ENTRY_POINTS:
            return True
        if isinstance(sub, ast.ImportFrom):
            if sub.module in _RESOLVER_ENTRY_POINTS:
                return True
            if any(alias.name in _RESOLVER_ENTRY_POINTS for alias in sub.names):
                return True
    return False


def _argv_shell_out_lines(node: ast.AST) -> list[int]:
    """Line numbers where ``node``'s subtree builds a ``get-worktree-path`` argv.

    The literal is only a shell-out when it is an ELEMENT of a list/tuple
    display — i.e. an argv vector handed to ``subprocess``. The producer
    (``manage-status.py``) mentions the same literal as a direct
    ``add_parser('get-worktree-path')`` argument, which declares its own
    subcommand and is not a shell-out; keying on the list-display position is
    what tells the two apart structurally.
    """
    lines: set[int] = set()
    for sub in ast.walk(node):
        if not isinstance(sub, (ast.List, ast.Tuple)):
            continue
        for element in sub.elts:
            if isinstance(element, ast.Constant) and element.value == _GET_WORKTREE_PATH_VERB:
                lines.add(sub.lineno)
    return sorted(lines)


def _worktree_path_key_read_lines(node: ast.AST) -> list[int]:
    """Line numbers where ``node``'s subtree READS the ``worktree_path`` key.

    Both mapping read forms count — ``mapping['worktree_path']`` (a ``Load``
    subscript) and ``mapping.get('worktree_path')``. A WRITE
    (``payload['worktree_path'] = value``, a ``Store`` subscript) and a dict
    literal that merely EMITS the key are deliberately not reads: emitting the
    resolved path in an output payload is the opposite of re-deriving it.
    """
    lines: set[int] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Subscript) and isinstance(sub.ctx, ast.Load):
            index = sub.slice
            if isinstance(index, ast.Constant) and index.value == _WORKTREE_PATH_KEY:
                lines.add(sub.lineno)
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == 'get':
            first = sub.args[0] if sub.args else None
            if isinstance(first, ast.Constant) and first.value == _WORKTREE_PATH_KEY:
                lines.add(sub.lineno)
    return sorted(lines)


def _private_worktree_helpers(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function whose NAME matches a historical re-deriver prefix.

    Candidate seeding only — the verdict is the body classification applied by
    :func:`_classify_helper`.
    """
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith(_PRIVATE_HELPER_PREFIXES)
    ]


def _classify_helper(node: ast.AST) -> str:
    """Classify a helper body as ``'re-deriver'`` or ``'adapter'``.

    A body that shells out to the producer, or reads the persisted
    ``worktree_path`` key out of a mapping, re-derives the worktree face by
    hand. Anything else — including a body that applies a ``--project-dir``
    escape hatch and then delegates — is a sanctioned argument adapter.
    """
    if _argv_shell_out_lines(node) or _worktree_path_key_read_lines(node):
        return 're-deriver'
    return 'adapter'


def _is_resolver_module(path: Path) -> bool:
    """True for the resolver module itself, matched on path COMPONENTS."""
    parts = set(path.parts)
    parts.add(path.name)
    return _RESOLVER_MODULE_COMPONENTS.issubset(parts)


# =============================================================================
# Population derivation
# =============================================================================


def _iter_bundle_scripts() -> list[Path]:
    """Every ``.py`` file under a bundle skill's ``scripts/`` directory."""
    return [
        path
        for path in sorted(MARKETPLACE_ROOT.rglob('*.py'))
        if path.is_file() and 'scripts' in path.parts
    ]


def _parse(path: Path) -> ast.Module | None:
    """Parse ``path``; return ``None`` when it is unreadable or unparseable."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    try:
        return ast.parse(text, filename=str(path))
    except SyntaxError:
        return None


def _derive_population() -> dict[str, tuple[Path, ast.Module]]:
    """Derive the Bucket B working-tree-binding population from the live tree.

    A script is a member when it binds a working tree — either because it names
    a resolver entry point, or because it shells out to the producer directly.
    Including the shell-out arm is what keeps
    :func:`test_every_population_member_routes_through_the_resolver`
    substantive: an unmigrated script that still shells out lands in the
    population and then fails that assertion, rather than escaping the guard by
    virtue of not mentioning the resolver.

    Returns:
        Mapping of ``marketplace/bundles``-relative path -> ``(path, tree)``.
    """
    population: dict[str, tuple[Path, ast.Module]] = {}
    for path in _iter_bundle_scripts():
        tree = _parse(path)
        if tree is None:
            continue
        if _references_resolver(tree) or _argv_shell_out_lines(tree):
            population[str(path.relative_to(MARKETPLACE_ROOT))] = (path, tree)
    return population


@pytest.fixture(scope='module')
def population() -> dict[str, tuple[Path, ast.Module]]:
    """The derived population, computed once per module."""
    return _derive_population()


# =============================================================================
# Population integrity — the anti-vacuity floor for the whole suite
# =============================================================================


def test_population_is_non_empty(population):
    """The derivation must find members; an empty set would make every
    per-member assertion below vacuously true."""
    assert population, (
        'Bucket B population derived from the live tree is EMPTY — every '
        'per-member assertion in this module would pass vacuously. The '
        'derivation in _derive_population() has regressed.'
    )


def test_population_covers_every_pinned_member(population):
    """The derivation must still find each migrated consumer.

    Pins the population against silent shrinkage: a derivation that stops
    matching a known member would keep guarding, just over a smaller set.
    """
    missing = sorted(_PINNED_POPULATION_MEMBERS - set(population))
    assert not missing, (
        'The derived Bucket B population no longer covers these pinned '
        f'members: {missing}. Either the file moved (update the pin) or the '
        'derivation regressed (fix _derive_population).'
    )


# =============================================================================
# The migration contract
# =============================================================================


def test_every_population_member_routes_through_the_resolver(population):
    """Every working-tree-binding script reaches the ONE resolver.

    The resolver module itself is exempt — it IS the resolver.
    """
    offenders = sorted(
        rel
        for rel, (path, tree) in population.items()
        if not _is_resolver_module(path) and not _references_resolver(tree)
    )
    assert not offenders, (
        'These Bucket B scripts bind a working tree without routing through '
        f'the resolver: {offenders}. Resolve via file_ops.resolve_plan_context '
        '(or the resolve_project_dir argv layer that delegates to it).'
    )


def test_no_get_worktree_path_shell_out_survives_outside_the_resolver(population):
    """``manage-status get-worktree-path`` is invoked from exactly one place."""
    offenders = sorted(
        f'{rel}:{_argv_shell_out_lines(tree)}'
        for rel, (path, tree) in population.items()
        if not _is_resolver_module(path) and _argv_shell_out_lines(tree)
    )
    assert not offenders, (
        'These scripts shell out to manage-status get-worktree-path directly '
        f'instead of going through the resolver: {offenders}.'
    )


def test_no_private_worktree_re_deriver_survives(population):
    """No private helper in the population re-derives the worktree by hand.

    The resolver module is exempt: its own ``_resolve_worktree_face`` IS the
    canonical derivation.
    """
    offenders: list[str] = []
    for rel, (path, tree) in population.items():
        if _is_resolver_module(path):
            continue
        for helper in _private_worktree_helpers(tree):
            if _classify_helper(helper) == 're-deriver':
                offenders.append(f'{rel}::{helper.name} (line {helper.lineno})')
    assert not offenders, (
        'These private helpers still re-derive the worktree face by hand '
        f'(shell-out or persisted-key read): {sorted(offenders)}. Delegate to '
        'file_ops.resolve_plan_context and keep only the argv adaptation.'
    )


def test_resolve_project_dir_delegates_to_resolve_plan_context():
    """The argv layer resolves through ``resolve_plan_context``, not itself.

    This is the link that makes "references a resolver entry point" equivalent
    to "resolves through ``resolve_plan_context``" for every population member
    that reaches the resolver via the argv layer.
    """
    path = MARKETPLACE_ROOT / 'plan-marshall/skills/script-shared/scripts/resolve_project_dir.py'
    tree = _parse(path)
    assert tree is not None, f'resolve_project_dir.py did not parse: {path}'

    target = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'resolve_project_dir'
        ),
        None,
    )
    assert target is not None, 'resolve_project_dir() is no longer defined in the argv layer'

    delegates = any(
        isinstance(sub, ast.Call)
        and isinstance(sub.func, ast.Name)
        and sub.func.id == 'resolve_plan_context'
        for sub in ast.walk(target)
    )
    assert delegates, (
        'resolve_project_dir() no longer calls resolve_plan_context — the argv '
        'layer has grown its own worktree derivation.'
    )


# =============================================================================
# Anti-vacuity controls — prove each detector actually fires
# =============================================================================


def test_shell_out_detector_fires_on_the_one_sanctioned_site(population):
    """The shell-out detector is proven live against the real tree.

    ``test_no_get_worktree_path_shell_out_survives_outside_the_resolver`` above
    passes with an empty offender list. That is only meaningful if the detector
    fires at all — and the resolver's own shell-out is the standing witness
    that it does.
    """
    resolver_hits = {
        rel: _argv_shell_out_lines(tree)
        for rel, (path, tree) in population.items()
        if _is_resolver_module(path)
    }
    assert resolver_hits, 'The resolver module is not in the derived population'
    assert all(lines for lines in resolver_hits.values()), (
        'The shell-out detector no longer fires on the resolver own '
        f'get-worktree-path invocation: {resolver_hits}. The detector is '
        'vacuous, so the zero-offender assertion proves nothing.'
    )


_SYNTHETIC_SHELL_OUT = '''
import subprocess

def _resolve_project_dir(plan_id):
    out = subprocess.run(
        ['python3', 'x.py', 'plan-marshall:manage-status:manage-status',
         'get-worktree-path', '--plan-id', plan_id],
        capture_output=True,
    )
    return out.stdout
'''

_SYNTHETIC_KEY_READ_SUBSCRIPT = '''
def _resolve_worktree_path(status):
    return status['metadata']['worktree_path']
'''

_SYNTHETIC_KEY_READ_GET = '''
def _resolve_worktree_path(status):
    return status.get('metadata', {}).get('worktree_path')
'''

_SYNTHETIC_ADAPTER = '''
from file_ops import resolve_plan_context

def _resolve_project_dir(plan_id, override):
    if override:
        return override
    return resolve_plan_context(plan_id, ensure=False).worktree_path
'''

_SYNTHETIC_EMITTER = '''
def build_payload(resolved):
    payload = {'status': 'success', 'worktree_path': resolved}
    payload['worktree_path'] = resolved
    return payload
'''


@pytest.mark.parametrize(
    'source',
    [
        _SYNTHETIC_SHELL_OUT,
        _SYNTHETIC_KEY_READ_SUBSCRIPT,
        _SYNTHETIC_KEY_READ_GET,
    ],
    ids=['argv-shell-out', 'subscript-key-read', 'get-key-read'],
)
def test_re_deriver_detector_fires_on_synthetic_re_derivers(source):
    """Positive control: each re-derivation form is classified ``re-deriver``."""
    tree = ast.parse(source)
    helpers = _private_worktree_helpers(tree)
    assert helpers, 'the synthetic fixture defines no candidate helper'
    assert [_classify_helper(h) for h in helpers] == ['re-deriver'] * len(helpers)


@pytest.mark.parametrize(
    'source',
    [_SYNTHETIC_ADAPTER, _SYNTHETIC_EMITTER],
    ids=['delegating-adapter', 'payload-emitter'],
)
def test_re_deriver_detector_stays_silent_on_sanctioned_shapes(source):
    """Negative control: the detector is not a name-based false-positive generator.

    A delegating adapter KEEPS its ``_resolve_project_dir`` name by design (the
    escape hatch it owns is required), and an output payload that carries the
    resolved ``worktree_path`` key is an emit, not a read. Flagging either would
    make the guard reject exactly the shapes the migration deliberately kept.
    """
    tree = ast.parse(source)
    assert 're-deriver' not in [_classify_helper(h) for h in _private_worktree_helpers(tree)]
    assert _worktree_path_key_read_lines(tree) == [], (
        'the detector counted a WRITE or an output-payload emit of the '
        'worktree_path key as a re-derivation read'
    )
    assert _argv_shell_out_lines(tree) == []
