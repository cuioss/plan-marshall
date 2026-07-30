#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Plan-path-in-scripts analyzer for the ``plan-path-in-scripts`` rule.

This module detects hand-rolled re-implementations of canonical
``tools-file-ops:file_ops`` path helpers inside marketplace bundle scripts.
Three drift forms are detected via AST analysis:

**Form A — literal bypass**: A string constant (``ast.Constant``) whose value
contains ``.plan/plans/`` (the drifted form that omits ``/local/``) appears in
a code-active path-construction context: assignment target, string concatenation,
``Path(...)`` / ``os.path.join(...)`` call argument, or f-string nested
expression.  Module, class, and function **docstrings** (first ``ast.Expr`` in
a body) are excluded, as are strings in ``print()`` / ``help=`` annotation
positions.  The canonical resolved path is ``.plan/local/plans/``; the drifted
form creates a ghost ``.plan/plans/`` tree at the repo root on every invocation.

**Form B — parent-walking re-derivation**: A ``Path(__file__).parent…`` or
``os.path.dirname(__file__)`` expression chain whose final value is joined
(via ``/``, ``Path(…)``, or ``os.path.join``) against a ``.plan``-domain
subdirectory name (``plans``, ``lessons-learned``, ``logs``, ``archived-plans``,
``workspace``).  The canonical approach is to import and call
``tools-file-ops:file_ops.get_plan_dir`` / ``base_path`` / etc.

**Form C — resolver bypass**: A working-tree-binding ("Bucket B") consumer that
RE-DERIVES a worktree path by hand instead of routing through
``file_ops.resolve_plan_context`` — either by shelling out to
``manage-status get-worktree-path`` itself, or by reading the ``worktree_path``
key straight out of status metadata.

The **population** is re-derived from the live tree on every run by the four
Bucket B predicates — a ``--project-dir`` flag declaration, a reference to the
``resolve_project_dir`` argv layer, a ``get-worktree-path`` shell-out, or a
private ``_resolve_worktree*`` / ``_resolve_project_dir*`` helper — plus a fifth,
**migration-stable** arm: a reference to ``resolve_plan_context`` itself. A
script matching any one of them binds a working tree and is therefore in scope
the moment it lands; nothing is hand-listed, so the population cannot silently
stop covering new code.

The fifth arm is load-bearing, not decoration. The first four predicates
describe how a consumer binds a working tree *by hand*, so a migration that
replaces the hand-rolled binding with a resolver call ERASES the predicate that
put the consumer in the population — the guard would stop watching precisely the
files a migration just fixed. Routing through the ONE plan-context resolver is
itself proof that the consumer binds a plan's working tree, so the fifth arm
keeps every migrated consumer under permanent watch. It widens the population
only, never the verdict: a consumer that references the resolver is by
definition migrated, so it can never be flagged.

The **verdict** is deliberately **body-based, never name-based**. Several
helpers keep ``_resolve_worktree*`` / ``_resolve_project_dir*`` names as
legitimate CLI ARGUMENT ADAPTERS that own the ``--project-dir`` escape hatch and
delegate the real resolution to the resolver; a name-pattern verdict would flag
exactly those escape hatches and nothing else useful. The name seeds a
population CANDIDATE only — whether the consumer is flagged depends solely on
what its body does.

Exemptions (all forms)
----------------------
1. **Canonical source** — ``file_ops.py`` (``tools-file-ops`` bundle) is never
   flagged; it IS the canonical implementation, including of
   ``resolve_plan_context``.
2. **Canonical producer** — ``manage-status.py`` owns the ``get-worktree-path``
   command the resolver shells out to. Migrating it would close a cycle, so it
   is excluded by design.
3. **Import bootstraps** — ``Path(__file__).parent…`` chains that appear
   exclusively as the argument to ``sys.path.insert`` or ``sys.path.append``
   are bootstrap idioms, not path-resolution drift.
4. **Baseline stragglers (form C only)** — the named, enumerated set of
   consumers deferred to a later workstream (``_BASELINE_STRAGGLERS``). The set
   may only SHRINK: removing an entry records a migration, while adding one
   would license a new un-migrated consumer.

Convention documented here
--------------------------
The canonical plan-directory helper is ``get_plan_dir(plan_id)`` from
``tools-file-ops:file_ops`` which resolves to
``<repo>/.plan/local/plans/{plan_id}``.  Production scripts must use the
helper rather than constructing the path by hand.

Findings have the shape::

    {
        'rule_id': 'plan-path-in-scripts',
        'file': '<absolute file path>',
        'line': <int, 1-based>,
        'category': 'production_script' | 'test_assertion',
        'snippet': '<line excerpt>',
    }

Public API
----------
- ``analyze_plan_path_in_scripts(marketplace_root)``: entry point — scans
  ``marketplace/bundles/**/scripts/**/*.py`` and emits findings for
  non-whitelisted drift occurrences across all three forms.
- ``derive_working_tree_binding_population(marketplace_root)``: the form-C
  population — every non-whitelisted bundle script matching a working-tree
  binding arm.
- ``binding_arms(tree)``: the arms one module matches, for population diagnosis.
- ``routes_through_resolver(tree)``: True when a module reaches the resolver.
- ``collect_bypass_signals(tree)``: the ``(line, signal)`` re-derivation
  evidence for one module.
- ``find_resolver_bypasses(marketplace_root, apply_baseline=...)``: the form-C
  check. ``apply_baseline=False`` returns the raw bypassing set before the
  exemptions are subtracted (the anti-vacuity view).
- ``baseline_stragglers()`` / ``skill_key(file_path)``: read-only access to the
  exemption set and its key derivation, for the anti-vacuity assertions.
- ``is_whitelisted(file_path)``: returns True when ``file_path`` matches a
  whitelist entry.
"""

from __future__ import annotations

import ast
from pathlib import Path

from _rule_registry import RuleDescriptor

RULE_ID = 'plan-path-in-scripts'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='file-local',
)

# ---------------------------------------------------------------------------
# Form A constants
# ---------------------------------------------------------------------------

# The literal string that indicates form-A drift: .plan/plans/ WITHOUT /local/.
# The canonical form is .plan/local/plans/; this marker catches the shorter
# (drifted) form.  String ".plan/local/" is NOT flagged.
_FORM_A_MARKER = '.plan/plans/'

# ---------------------------------------------------------------------------
# Form B constants
# ---------------------------------------------------------------------------

# .plan-domain subdirectory names that are legal join targets only via the
# canonical helpers in file_ops.py.  A parent-walking chain that ultimately
# joins against one of these names is form-B drift.
_PLAN_DOMAIN_DIRS: frozenset[str] = frozenset({
    'plans',
    'lessons-learned',
    'logs',
    'archived-plans',
    'workspace',
})

# ---------------------------------------------------------------------------
# Whitelist — path-component-anchored
# ---------------------------------------------------------------------------
# Each entry is a frozenset of path component names that must ALL be present
# in the file's parts.  Component-presence test, not raw substring of the
# full path string.

_WHITELIST_COMPONENT_SETS: list[frozenset[str]] = [
    # lint-analyzer: this file itself (self-referential — the marker is the
    # detection target).
    frozenset({'_analyze_plan_path_in_scripts.py'}),
    # Canonical source: file_ops.py is the implementation of get_base_dir /
    # get_plan_dir / base_path — and of resolve_plan_context, the form-C
    # resolver. It IS the canonical source; never flag it.
    frozenset({'tools-file-ops', 'file_ops.py'}),
    # Canonical producer: manage-status.py OWNS the `get-worktree-path`
    # command that form C treats as a bypass signal everywhere else. Routing
    # it through the resolver would close a cycle (the resolver shells out to
    # this very command), so it is excluded by design, not by omission.
    frozenset({'manage-status', 'manage-status.py'}),
]

# ---------------------------------------------------------------------------
# Form C constants — resolver bypass
# ---------------------------------------------------------------------------

# The one canonical plan-context resolver every working-tree-binding consumer
# must route through. A consumer that references this name (imported or called)
# is considered migrated. It doubles as the fifth, migration-stable population
# arm — see the module docstring for why that arm is load-bearing.
_RESOLVER_NAME = 'resolve_plan_context'

# Population predicate 1: the working-tree escape-hatch flag. A consumer that
# declares it accepts a caller-supplied project directory, i.e. it binds a
# working tree.
_PROJECT_DIR_FLAG = '--project-dir'

# Population predicate 2: the shared argv layer that turns `--project-dir` /
# `--plan-id` into a bound working tree. Matched as a function reference AND as
# an imported module name, because consumers reach it both ways
# (`from resolve_project_dir import resolve_from_args`).
_PROJECT_DIR_RESOLVER = 'resolve_project_dir'

# Population predicate 4: the private-re-deriver name prefixes. These seed a
# population CANDIDATE only — the verdict is body-based, so a helper carrying one
# of these names is flagged only when its body actually re-derives.
_PRIVATE_REDERIVER_PREFIXES = ('_resolve_worktree', '_resolve_project_dir')

# Population predicate 3, and simultaneously a bypass signal: the command the
# resolver owns. A consumer that names it in its own argv is re-deriving the
# worktree face instead of asking the resolver for it.
_WORKTREE_PATH_COMMAND = 'get-worktree-path'

# The status-metadata key a private re-deriver reads to reconstruct the
# worktree path by hand.
_WORKTREE_PATH_KEY = 'worktree_path'

# Baseline straggler set (D1 gate, decision-log entry f88f43): the
# working-tree-binding consumers deliberately DEFERRED to a later workstream.
# Each entry is ``{skill}/{filename}``.
#
# This set is an EXEMPTION list, and it may only SHRINK. Adding a member would
# license a new un-migrated consumer, which is exactly what form C exists to
# prevent; removing one records that the consumer has been migrated. The
# accompanying test suite pins four properties this set must satisfy against the
# live tree: the derived population is non-empty; the baseline is a strict subset
# of it; every baseline entry resolves to a file that still exists (no phantom
# exemptions silently un-guarding a renamed successor); and the raw bypassing
# set, taken BEFORE the baseline is subtracted, is non-empty — the anti-vacuity
# proof that the guard can actually flag something against the real tree.
_BASELINE_STRAGGLERS: frozenset[str] = frozenset({
    'manage-tasks/_cmd_pre_commit_verify_freshness.py',
    'plan-marshall/_handshake_commands.py',
    'platform-runtime/claude_runtime.py',
    'workflow-integration-git/_cmd_baseline_reconcile.py',
    'workflow-integration-git/_cmd_force_push.py',
    'workflow-integration-git/_cmd_prune_ref.py',
    'workflow-integration-git/_cmd_switch_and_pull.py',
    'workflow-integration-git/git-workflow.py',
    'workflow-integration-git/integrate_into_main.py',
    'workflow-integration-github/github_ops.py',
    'workflow-integration-gitlab/gitlab_ops.py',
})


def is_whitelisted(file_path: Path) -> bool:
    """Return True when ``file_path`` matches any whitelist entry.

    Each whitelist entry is a frozenset of path-component strings that must
    ALL appear as exact matches among the components of ``file_path``.
    """
    parts_set = set(file_path.parts)
    parts_set.add(file_path.name)
    for required_components in _WHITELIST_COMPONENT_SETS:
        if required_components.issubset(parts_set):
            return True
    return False


def _classify(file_path: Path) -> str:
    """Classify a file as ``production_script`` or ``test_assertion``."""
    for part in file_path.parts:
        if part in ('test', 'tests'):
            return 'test_assertion'
    name = file_path.name
    if name.startswith('test_') or name.endswith('_test.py'):
        return 'test_assertion'
    return 'production_script'


# ---------------------------------------------------------------------------
# AST helpers — docstring node identification
# ---------------------------------------------------------------------------


def _collect_docstring_node_ids(tree: ast.Module) -> set[int]:
    """Return the set of ``id()`` values of AST nodes that are docstrings.

    A node is a docstring when it appears as the first statement in a
    module, function, or class body and is an ``ast.Expr(ast.Constant)``
    expression.  These must NOT be flagged as form-A code literals.
    """
    docstring_ids: set[int] = set()
    for node in ast.walk(tree):
        body: list[ast.stmt] | None = None
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            docstring_ids.add(id(body[0].value))
    return docstring_ids


# ---------------------------------------------------------------------------
# AST helpers — Form A: literal bypass detection
# ---------------------------------------------------------------------------


def _collect_form_a_node_ids(tree: ast.Module, docstring_ids: set[int]) -> list[int]:
    """Return line numbers for form-A findings (literal .plan/plans/ in code context).

    Scans for ``ast.Constant`` nodes whose string value contains ``_FORM_A_MARKER``
    in a code-active path-construction context.  Docstrings (``docstring_ids``)
    are excluded.

    Code-active contexts include:
    - Assignment RHS (``ast.Assign``, ``ast.AnnAssign``, ``ast.AugAssign``)
    - Binary addition (``ast.BinOp`` with ``ast.Add``) — string concatenation
    - ``Path(...)`` constructor argument
    - ``os.path.join(...)`` argument
    - Return values (``ast.Return``)
    - f-string (``ast.JoinedStr``) interpolated values

    Deliberately excluded (documentation positions):
    - Docstrings (module/function/class body first statement)
    - ``print(...)`` call arguments
    - Argparse ``help=`` keyword arguments
    - Any ``ast.Expr`` statement that is not a recognized path-construction call
    """
    findings: list[int] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str):
            continue
        if _FORM_A_MARKER not in node.value:
            continue
        if id(node) in docstring_ids:
            continue
        # At this point we have a string containing .plan/plans/ that is not
        # a docstring.  We need to determine whether it is in a path-construction
        # context.  Since ast.walk does not give us parent context, we use a
        # conservative approach: any .plan/plans/ string literal that is NOT
        # inside a module/function/class docstring and is NOT the sole argument
        # to a print() call is considered a code-literal hit.
        #
        # The canonical false-positive cases (print(), help=) are handled by
        # the parent-context visitor below.
        findings.append(node.lineno if hasattr(node, 'lineno') else 0)

    return findings


class _FormAVisitor(ast.NodeVisitor):
    """Visitor that collects form-A findings with parent-context awareness.

    Walks the AST maintaining a parent stack so that string constants can be
    classified as code-literal (emit finding) or documentation (skip).
    """

    def __init__(self, docstring_ids: set[int]) -> None:
        self._docstring_ids = docstring_ids
        self._findings: list[tuple[int, str]] = []  # (line_no, snippet)
        self._parent_stack: list[ast.AST] = []

    @property
    def findings(self) -> list[tuple[int, str]]:
        return self._findings

    def _in_documentation_context(self) -> bool:
        """Return True when the current node is inside a pure-documentation call.

        Excluded contexts:
        - Argument to ``print(...)`` — informational display strings.
        - ``help=`` keyword argument in a call — argparse annotation.
        """
        for parent in reversed(self._parent_stack):
            if isinstance(parent, ast.Call):
                func = parent.func
                # print(...) call
                if isinstance(func, ast.Name) and func.id == 'print':
                    return True
                # help= keyword arg in any call (argparse add_argument, add_parser, etc.)
                for kw in parent.keywords:
                    if kw.arg == 'help':
                        return True
            # Stop propagating past assignment, return, or binary-op parents
            # (those ARE path-construction contexts)
            if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.Return,
                                   ast.BinOp, ast.JoinedStr)):
                break
        return False

    def generic_visit(self, node: ast.AST) -> None:
        self._parent_stack.append(node)
        super().generic_visit(node)
        self._parent_stack.pop()

    def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
        if (
            isinstance(node.value, str)
            and _FORM_A_MARKER in node.value
            and id(node) not in self._docstring_ids
            and not self._in_documentation_context()
        ):
            line_no = getattr(node, 'lineno', 0)
            self._findings.append((line_no, ''))
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# AST helpers — Form B: parent-walking chain detection
# ---------------------------------------------------------------------------


def _is_file_dunder(node: ast.expr) -> bool:
    """Return True when ``node`` is the ``__file__`` name reference."""
    return isinstance(node, ast.Name) and node.id == '__file__'


def _is_path_parent_chain(node: ast.expr) -> bool:
    """Return True when ``node`` is a ``Path(__file__).parent[.parent…]``
    or ``Path(__file__).parents[…]`` chain.
    """
    return _walk_path_chain(node)


def _walk_path_chain(node: ast.expr) -> bool:
    """Recursive helper for _is_path_parent_chain."""
    # Path(__file__) — the root of any chain
    if isinstance(node, ast.Call):
        func = node.func
        is_path_call = (isinstance(func, ast.Name) and func.id == 'Path') or (
            isinstance(func, ast.Attribute)
            and func.attr == 'Path'
            and isinstance(func.value, ast.Name)
            and func.value.id == 'pathlib'
        )
        if is_path_call and len(node.args) == 1 and _is_file_dunder(node.args[0]):
            return True

    # <chain>.parent
    if isinstance(node, ast.Attribute) and node.attr == 'parent':
        return _walk_path_chain(node.value)

    # <chain>.parents[N]
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Attribute) and node.value.attr == 'parents':
            return _walk_path_chain(node.value.value)

    return False


def _is_os_dirname_chain(node: ast.expr) -> bool:
    """Return True when ``node`` is an ``os.path.dirname(__file__)`` or
    nested ``os.path.dirname(os.path.dirname(…))`` chain.
    """
    if isinstance(node, ast.Call):
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == 'dirname'
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == 'path'
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == 'os'
        ):
            if len(node.args) == 1:
                arg = node.args[0]
                return _is_file_dunder(arg) or _is_os_dirname_chain(arg)
    return False


def _is_parent_walking_root(node: ast.expr) -> bool:
    """Return True when ``node`` is a file-relative parent-walking expression."""
    return _is_path_parent_chain(node) or _is_os_dirname_chain(node)


def _extract_joined_string(node: ast.expr) -> str | None:
    """Attempt to extract the rightmost string component from a Path division
    or os.path.join call rooted in a parent-walking expression.

    Returns the string value of the rightmost ``ast.Constant`` component
    (the subdirectory name being joined), or None when the pattern is not
    recognised.
    """
    # Unwrap str(...) wrapper
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'str'
        and len(node.args) == 1
    ):
        return _extract_joined_string(node.args[0])

    # Path(<chain>, "subdir", ...) constructor
    if isinstance(node, ast.Call):
        func = node.func
        is_path_call = (isinstance(func, ast.Name) and func.id == 'Path') or (
            isinstance(func, ast.Attribute)
            and func.attr == 'Path'
            and isinstance(func.value, ast.Name)
            and func.value.id == 'pathlib'
        )
        if is_path_call and len(node.args) >= 2:
            if _is_parent_walking_root(node.args[0]):
                parts = []
                for arg in node.args[1:]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        parts.append(arg.value)
                if parts:
                    return parts[0]

        # os.path.join(<chain>, "subdir", ...)
        if (
            isinstance(func, ast.Attribute)
            and func.attr == 'join'
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == 'path'
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == 'os'
        ):
            if len(node.args) >= 2 and _is_parent_walking_root(node.args[0]):
                second = node.args[1]
                if isinstance(second, ast.Constant) and isinstance(second.value, str):
                    return second.value

    # <chain> / "subdir" — BinOp with Div operator
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        right = node.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            if _lhs_rooted_in_parent_chain(node.left):
                return right.value
    return None


def _lhs_rooted_in_parent_chain(node: ast.expr) -> bool:
    """Return True when the left-hand side of a BinOp chain is ultimately
    rooted in a parent-walking expression.
    """
    if _is_parent_walking_root(node):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _lhs_rooted_in_parent_chain(node.left)
    return False


def _collect_sys_path_insert_arg_lines(tree: ast.Module) -> set[int]:
    """Return the set of line numbers that are arguments to sys.path.insert /
    sys.path.append calls (import-bootstrap chains exempt from form-B).
    """
    exempt_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            func = call.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in ('insert', 'append')
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == 'path'
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == 'sys'
            ):
                for arg in call.args:
                    for sub in ast.walk(arg):
                        if hasattr(sub, 'lineno'):
                            exempt_lines.add(sub.lineno)
    return exempt_lines


# ---------------------------------------------------------------------------
# AST helpers — Form C: resolver-bypass detection
# ---------------------------------------------------------------------------
#
# Form C is POPULATION-DERIVED and BODY-BASED, and both properties are
# load-bearing.
#
# *Population-derived*: the consumer set is not a hand-maintained list. It is
# re-derived on every run by AST-walking every bundle script for the five
# working-tree-binding arms (the four Bucket B predicates plus the
# migration-stable resolver reference), so a newly-added consumer is in scope the
# moment it lands. A hand-listed population would silently stop covering new
# code — a detector whose predicate never fires is the failure mode this rule
# exists to avoid.
#
# The population is deliberately NOT derived from a `--plan-id` argparse
# declaration. That walk was tried and rejected: it yields a set of 46 that
# contains ZERO of the 11 baseline stragglers, because seven of them declare the
# flag through a hand-rolled argv parser with no `add_argument` call at all and
# two are helper modules whose parent entry point owns the flag. Asserting a
# strict-subset property against that derivation was incoherent — the baseline
# was drawn from the Bucket B predicates, so the Bucket B predicates are what the
# population must be derived from.
#
# *Body-based, never name-based*: the check asks what a function DOES, never
# what it is called. Eight helpers legitimately keep `_resolve_worktree*` /
# `_resolve_project_dir*` names as CLI ARGUMENT ADAPTERS — they own the
# `--project-dir` escape hatch and its mutual-exclusivity error, and delegate
# the actual resolution to `resolve_plan_context`. A name-pattern detector
# would flag precisely those escape hatches, i.e. it would be a pure
# false-positive generator. Form C therefore flags only genuine RE-DERIVATION:
# a body that shells out to `get-worktree-path` itself, or that reads the
# `worktree_path` key straight out of status metadata.


def _skill_key(file_path: Path) -> str:
    """Return the ``{skill}/{filename}`` key used by the baseline set.

    Returns just the filename when the path carries no ``skills/{skill}/``
    segment, so a non-standard layout degrades to a filename match rather than
    raising.
    """
    parts = file_path.parts
    if 'skills' in parts:
        idx = parts.index('skills')
        if idx + 1 < len(parts):
            return f'{parts[idx + 1]}/{file_path.name}'
    return file_path.name


def _references_name(tree: ast.Module, name: str) -> bool:
    """Return True when the module references ``name`` in any reachable form.

    Four shapes count, because a consumer reaches a shared helper by all of
    them: a bare name, an attribute access (``file_ops.resolve_plan_context``),
    an ``from … import name`` alias, and ``from name import …`` where ``name``
    is the MODULE being imported (the shape
    ``from resolve_project_dir import resolve_from_args`` uses).
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            return True
        if isinstance(node, ast.Attribute) and node.attr == name:
            return True
        if isinstance(node, ast.ImportFrom):
            if node.module == name:
                return True
            for alias in node.names:
                if alias.name == name:
                    return True
    return False


def _live_string_lines(tree: ast.Module, value: str) -> list[int]:
    """Return the lines where ``value`` appears as a non-docstring string constant.

    Docstrings are excluded so a module that merely DESCRIBES a flag or a command
    in prose is not treated as declaring or invoking it.
    """
    docstring_ids = _collect_docstring_node_ids(tree)
    return sorted(
        {
            getattr(node, 'lineno', 0)
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value == value
            and id(node) not in docstring_ids
        }
    )


def _declares_private_rederiver(tree: ast.Module) -> bool:
    """Return True when the module defines a ``_resolve_worktree*`` / ``_resolve_project_dir*``.

    This is a population CANDIDATE arm only. The name says the helper is in the
    worktree-resolution business; whether it actually re-derives is decided by
    :func:`collect_bypass_signals` reading its body.
    """
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith(_PRIVATE_REDERIVER_PREFIXES)
        for node in ast.walk(tree)
    )


def binding_arms(tree: ast.Module) -> list[str]:
    """Return the working-tree-binding arms ``tree`` matches, in canonical order.

    An empty list means the module binds no working tree and is out of form C's
    scope entirely. See the module docstring for why the fifth arm
    (``resolver_ref``) is load-bearing rather than redundant.
    """
    arms: list[str] = []
    if _live_string_lines(tree, _PROJECT_DIR_FLAG):
        arms.append('project_dir_flag')
    if _references_name(tree, _PROJECT_DIR_RESOLVER):
        arms.append('resolve_project_dir_ref')
    if _live_string_lines(tree, _WORKTREE_PATH_COMMAND):
        arms.append('worktree_path_shell_out')
    if _declares_private_rederiver(tree):
        arms.append('private_rederiver')
    if _references_name(tree, _RESOLVER_NAME):
        arms.append('resolver_ref')
    return arms


def routes_through_resolver(tree: ast.Module) -> bool:
    """Return True when the module reaches the canonical plan resolver.

    A plain name reference is sufficient — an import, a direct call, or a call
    through a module attribute (``file_ops.resolve_plan_context``) all count.
    Delegating to the resolver is what "migrated" means, and a consumer that
    merely imports it to hand off to a shared adapter is equally migrated.
    """
    return _references_name(tree, _RESOLVER_NAME)


def collect_bypass_signals(tree: ast.Module) -> list[tuple[int, str]]:
    """Return ``(line, signal)`` pairs for every resolver-bypass in the body.

    Two re-derivation signals, both structural:

    - ``worktree_path_shell_out`` — the module names ``get-worktree-path`` in
      its own code (an argv list handed to subprocess). The resolver owns that
      command; a consumer invoking it is re-deriving the worktree face.
    - ``worktree_path_metadata_read`` — the module reads the ``worktree_path``
      key out of status metadata, by subscript (``metadata['worktree_path']``)
      or by ``.get('worktree_path')``. That is the same re-derivation done
      without a subprocess.

    Docstrings are excluded so a module that merely DESCRIBES the command in
    prose is not flagged for documenting it.
    """
    docstring_ids = _collect_docstring_node_ids(tree)
    signals: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstring_ids:
                continue
            if node.value == _WORKTREE_PATH_COMMAND:
                signals.append((getattr(node, 'lineno', 0), 'worktree_path_shell_out'))
            continue

        # metadata['worktree_path']
        if isinstance(node, ast.Subscript):
            key = node.slice
            if isinstance(key, ast.Constant) and key.value == _WORKTREE_PATH_KEY:
                signals.append((getattr(node, 'lineno', 0), 'worktree_path_metadata_read'))
            continue

        # <mapping>.get('worktree_path')
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == 'get' and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and first.value == _WORKTREE_PATH_KEY:
                    signals.append((getattr(node, 'lineno', 0), 'worktree_path_metadata_read'))

    return signals


def derive_working_tree_binding_population(marketplace_root: Path) -> list[Path]:
    """Re-derive the working-tree-binding ("Bucket B") population from the live tree.

    The population is every non-whitelisted bundle script matching at least one
    arm of :func:`binding_arms`. This is the denominator form C's exemption set is
    checked against, and it is recomputed on every run rather than
    hand-maintained.
    """
    population: list[Path] = []

    bundles_root = marketplace_root / 'bundles'
    if not bundles_root.is_dir():
        return population

    for py_file in sorted(bundles_root.rglob('*.py')):
        if not py_file.is_file() or is_whitelisted(py_file):
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding='utf-8'), filename=str(py_file))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        if binding_arms(tree):
            population.append(py_file)

    return population


def baseline_stragglers() -> frozenset[str]:
    """Return the named baseline straggler exemption set.

    Exposed read-only so the accompanying suite can assert the four properties
    the set must satisfy against the live tree without reaching for the private
    module global.
    """
    return _BASELINE_STRAGGLERS


def skill_key(file_path: Path) -> str:
    """Return the ``{skill}/{filename}`` baseline key for ``file_path``."""
    return _skill_key(file_path)


def find_resolver_bypasses(marketplace_root: Path, *, apply_baseline: bool = True) -> list[dict]:
    """Return form-C findings: derived consumers that bypass the resolver.

    A derived consumer is flagged when it carries at least one re-derivation
    signal AND does not reference the canonical resolver.

    Parameters
    ----------
    marketplace_root:
        Path to the ``marketplace/`` directory.
    apply_baseline:
        When True (the rule's behaviour), members of the D1 baseline straggler
        set are subtracted. When False, the raw bypassing set is returned —
        the anti-vacuity view the test suite uses to prove the detector can
        actually flag something before the exemptions are applied.
    """
    findings: list[dict] = []

    for py_file in derive_working_tree_binding_population(marketplace_root):
        if apply_baseline and _skill_key(py_file) in _BASELINE_STRAGGLERS:
            continue
        try:
            text = py_file.read_text(encoding='utf-8')
            tree = ast.parse(text, filename=str(py_file))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        if routes_through_resolver(tree):
            continue

        signals = collect_bypass_signals(tree)
        if not signals:
            continue

        lines = text.splitlines()
        line_no, signal = sorted(signals)[0]
        snippet = lines[line_no - 1].strip()[:120] if 0 < line_no <= len(lines) else ''
        findings.append(
            {
                'rule_id': RULE_ID,
                'file': str(py_file),
                'line': line_no,
                'category': _classify(py_file),
                'snippet': snippet,
                'form': 'C',
                'signal': signal,
            }
        )

    return findings


# ---------------------------------------------------------------------------
# File scanner
# ---------------------------------------------------------------------------


def _scan_file(file_path: Path) -> list[dict]:
    """Scan one Python file for plan-path drift using AST analysis.

    Detects:
    - **Form A**: string constants containing ``.plan/plans/`` (without
      ``/local/``) in code-active (path-construction) contexts.
    - **Form B**: ``Path(__file__).parent…`` / ``os.path.dirname(__file__)``
      chains joined against a ``.plan``-domain subdirectory name.

    Exemptions applied:
    - Module/function/class docstrings are excluded from form-A detection.
    - ``print()`` and ``help=`` annotation strings are excluded from form-A.
    - Lines in ``sys.path.insert`` / ``sys.path.append`` arguments are exempt
      from form-B detection.
    """
    try:
        text = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(text, filename=str(file_path))
    except SyntaxError:
        return []

    lines = text.splitlines()
    findings: list[dict] = []
    category = _classify(file_path)

    # Collect docstring node ids for form-A exclusion
    docstring_ids = _collect_docstring_node_ids(tree)

    # Collect sys.path-insert exempt lines for form-B exclusion
    sys_path_exempt_lines = _collect_sys_path_insert_arg_lines(tree)

    # ---------------------------------------------------------------------------
    # Form A: parent-context-aware visitor
    # ---------------------------------------------------------------------------
    visitor = _FormAVisitor(docstring_ids)
    visitor.visit(tree)
    seen_form_a_lines: set[int] = set()
    for line_no, _ in visitor.findings:
        if line_no and line_no not in seen_form_a_lines:
            seen_form_a_lines.add(line_no)
            snippet = lines[line_no - 1].strip()[:120] if line_no <= len(lines) else ''
            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(file_path),
                    'line': line_no,
                    'category': category,
                    'snippet': snippet,
                }
            )

    # ---------------------------------------------------------------------------
    # Form B: parent-walking chain detection
    # ---------------------------------------------------------------------------
    seen_form_b_lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.expr):
            continue
        line_no = getattr(node, 'lineno', 0)
        if not line_no:
            continue
        if line_no in sys_path_exempt_lines:
            continue
        if line_no in seen_form_b_lines:
            continue

        joined = _extract_joined_string(node)
        if joined is not None and joined in _PLAN_DOMAIN_DIRS:
            seen_form_b_lines.add(line_no)
            snippet = lines[line_no - 1].strip()[:120] if line_no <= len(lines) else ''
            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(file_path),
                    'line': line_no,
                    'category': category,
                    'snippet': snippet,
                }
            )

    return findings


def analyze_plan_path_in_scripts(marketplace_root: Path) -> list[dict]:
    """Scan marketplace bundle scripts for non-whitelisted plan-path references.

    Scans:
    - ``<marketplace_root>/bundles/**/skills/*/scripts/**/*.py``

    Three drift forms are detected (see module docstring for full specification):
    - Form A: string constants containing ``.plan/plans/`` in path-construction
      contexts (code literals, not docstrings or annotation strings).
    - Form B: ``Path(__file__).parent…`` chains joined to ``.plan``-domain dirs.
    - Form C: working-tree-binding consumers that re-derive a worktree path
      instead of routing through ``file_ops.resolve_plan_context``. Form C is
      population-derived over the whole tree rather than per-file, so it runs
      once after the per-file scan instead of inside it.

    Test files are scanned but their findings are categorised as
    ``test_assertion`` rather than ``production_script`` so callers can apply
    different triage.

    Parameters
    ----------
    marketplace_root:
        Path to the ``marketplace/`` directory.

    Returns
    -------
    list[dict]
        Findings for non-whitelisted drift occurrences.
    """
    findings: list[dict] = []

    bundles_root = marketplace_root / 'bundles'
    if not bundles_root.is_dir():
        return []

    for py_file in sorted(bundles_root.rglob('*.py')):
        if not py_file.is_file():
            continue
        if is_whitelisted(py_file):
            continue
        findings.extend(_scan_file(py_file))

    # Form C is population-derived rather than per-file, so it runs once over
    # the whole tree instead of inside the per-file scan above.
    findings.extend(find_resolver_bypasses(marketplace_root))

    return findings
