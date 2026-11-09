#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression guard: no test-support module may leak a system temp directory.

Two sites created system temp directories that nothing removed — the guard
harness's relocated scratch root (one per ``build_harness`` call, roughly 22
inodes each) and the executor-mapping stub directory (one per pytest process).
Run after run from inside a plan worktree they exhausted the ``/tmp`` tmpfs inode
pool, and every ``mkdir``/``touch``/build on the machine started failing with
``No space left on device`` while the root filesystem still had free bytes.

The sweep below is the standing guard: a module-level ``tempfile.mkdtemp`` is
always a failure (it runs at import, once per pytest process, whether or not any
test uses it), and a function-level one is a failure unless the same function
carries a deterministic removal path. The relocation test is deliverable 1's
direct proof: the scratch-root predicate and the returned path shape are
unchanged, and the registered teardown removes the relocated directory.
"""

from __future__ import annotations

import ast
from pathlib import Path

import system_temp
from _guard_node_harness import build_harness

#: ``test/`` — the tree whose modules the sweep covers.
TEST_ROOT = Path(__file__).resolve().parents[2]

_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)

#: Method names that turn an object into a lifecycle owner: a directory created in
#: one method of a class and removed in one of these is deterministically removed.
_LIFECYCLE_METHODS = frozenset({'__exit__', 'cleanup', 'teardown', 'close'})

#: Attribute names whose CALL is a removal. ``.cleanup()`` covers a
#: ``TemporaryDirectory`` handle; the rest are direct filesystem removals.
_REMOVAL_CALLS = frozenset({'rmtree', 'rmdir', 'unlink', 'cleanup'})

#: Attribute names whose call REGISTERS a later removal (``atexit.register``,
#: ``weakref.finalize``). The registration is the removal path: it is what runs
#: when the process exits, and the sweep cannot see the callback's body.
_DEFERRED_REMOVAL_CALLS = frozenset({'register', 'finalize'})

#: The shared registered-teardown helper (``test/_shared/system_temp.py``). A call
#: to ``system_temp.create(...)`` IS a removal path — the helper records the root
#: and registers its removal — so a site that delegates to it needs no other
#: evidence.
_SHARED_HELPER_MODULE = 'system_temp'
_SHARED_HELPER_ATTR = 'create'


def _is_mkdtemp_call(node: ast.AST) -> bool:
    """Whether ``node`` is a ``tempfile.mkdtemp`` (or bare ``mkdtemp``) call."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr == 'mkdtemp'
    return isinstance(func, ast.Name) and func.id == 'mkdtemp'


def _mkdtemp_sites(tree: ast.Module) -> list[tuple[ast.Call, ast.AST | None, ast.ClassDef | None]]:
    """Every mkdtemp call, with its enclosing function and class (or ``None``)."""
    found: list[tuple[ast.Call, ast.AST | None, ast.ClassDef | None]] = []

    def visit(node: ast.AST, function: ast.AST | None, klass: ast.ClassDef | None) -> None:
        if _is_mkdtemp_call(node):
            found.append((node, function, klass))
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _FUNCTION_NODES):
                visit(child, child, klass)
            elif isinstance(child, ast.ClassDef):
                visit(child, function, child)
            else:
                visit(child, function, klass)

    visit(tree, None, None)
    return found


def _carries_removal(function: ast.AST) -> bool:
    """Whether ``function``'s body removes a directory or registers its removal."""
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        attr = node.func.attr
        if attr in _REMOVAL_CALLS or attr in _DEFERRED_REMOVAL_CALLS:
            return True
    return False


def _delegates_to_shared_helper(function: ast.AST) -> bool:
    """Whether ``function`` creates its directory through ``system_temp.create``."""
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if isinstance(owner, ast.Name) and owner.id == _SHARED_HELPER_MODULE and node.func.attr == _SHARED_HELPER_ATTR:
            return True
    return False


def _class_owns_teardown(klass: ast.ClassDef) -> bool:
    """Whether ``klass`` defines a lifecycle method that removes a directory."""
    return any(
        isinstance(item, _FUNCTION_NODES) and item.name in _LIFECYCLE_METHODS and _carries_removal(item)
        for item in klass.body
    )


def _sites_without_removal(source: str, label: str) -> list[str]:
    """Every mkdtemp site in ``source`` that has no deterministic removal path.

    Args:
        source: Python source text to analyse.
        label: How the source is named in the returned rows.

    Returns:
        One ``{label}:{line}: {reason}`` row per offending site, in line order.
    """
    tree = ast.parse(source)
    offenders: list[str] = []
    for call, function, klass in _mkdtemp_sites(tree):
        if function is None:
            offenders.append(f'{label}:{call.lineno}: module-level mkdtemp runs at import, once per pytest process')
            continue
        if _carries_removal(function) or _delegates_to_shared_helper(function):
            continue
        if klass is not None and _class_owns_teardown(klass):
            continue
        offenders.append(
            f'{label}:{call.lineno}: function-level mkdtemp with no removal in '
            f'{getattr(function, "name", "<function>")}: no shutil.rmtree, no registered teardown, '
            f'no lifecycle method'
        )
    return sorted(offenders)


def _tree_offenders() -> list[str]:
    """Every offending mkdtemp site under ``test/``."""
    offenders: list[str] = []
    for path in sorted(TEST_ROOT.rglob('*.py')):
        try:
            source = path.read_text(encoding='utf-8')
        except OSError as exc:  # unreadable module — the sweep cannot clear it
            offenders.append(f'{path.relative_to(TEST_ROOT)}: unreadable ({exc})')
            continue
        label = path.relative_to(TEST_ROOT).as_posix()
        offenders.extend(_sites_without_removal(source, label))
    return offenders


def test_no_test_support_module_leaks_a_system_temp_directory():
    """Every system temp directory in the test tree has a deterministic removal path.

    The failure names every site, so the remedy is one edit per row rather than a
    search. ``system_temp.create(prefix=...)`` is the sanctioned form; a direct
    ``tempfile.mkdtemp`` is acceptable only when the same function (or the
    enclosing class's lifecycle method) removes the directory.
    """
    offenders = _tree_offenders()

    assert not offenders, (
        f'{len(offenders)} system temp directory site(s) with no deterministic removal path:\n  '
        + '\n  '.join(offenders)
        + '\nCreate the directory with system_temp.create(prefix=...), or remove it in the same '
        'function (shutil.rmtree in a finally, a fixture finalizer, a registered teardown, or a '
        'class lifecycle method).'
    )


def test_the_sweep_flags_a_module_level_mkdtemp():
    """Positive control: the sweep's module-level arm fires on the shape it names."""
    offenders = _sites_without_removal(
        "import tempfile\n\nROOT = tempfile.mkdtemp(prefix='leak-')\n",
        'control.py',
    )

    assert offenders == [
        'control.py:3: module-level mkdtemp runs at import, once per pytest process',
    ]


def test_the_sweep_flags_a_function_level_mkdtemp_without_removal():
    """Positive control: a bare function-level site is a failure."""
    offenders = _sites_without_removal(
        'import tempfile\nfrom pathlib import Path\n\n\ndef build():\n    return Path(tempfile.mkdtemp())\n',
        'control.py',
    )

    assert len(offenders) == 1
    assert offenders[0].startswith('control.py:6: '), offenders[0]


def test_the_sweep_clears_the_three_accepted_removal_paths():
    """Matched negative control: finally-removal, shared helper, class lifecycle."""
    source = """
import shutil
import tempfile
from pathlib import Path

import system_temp


def with_finally():
    root = Path(tempfile.mkdtemp())
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def through_the_helper():
    return system_temp.create(prefix='ok-')


class Owner:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp())

    def __exit__(self, *_exc):
        shutil.rmtree(self.root, ignore_errors=True)
"""

    assert _sites_without_removal(source, 'control.py') == []


def test_a_worktree_shaped_scratch_root_is_relocated_and_torn_down(outside_repo_dir: Path):
    """Deliverable 1's direct proof: relocation is unchanged, teardown is real.

    A scratch path inside a faux ``.plan/local/worktrees/`` tree relocates to a
    ``guard-node-*`` system temp directory exactly as before; the registered
    teardown then removes that directory. Before this, the relocated root was
    created bare and nothing ever removed it.

    The faux tree is built outside the repository on purpose: the suite's own
    ``tmp_path`` resolves INSIDE the plan worktree this suite may be running from,
    which would relocate the nesting — the probe must not depend on where the run
    happens.
    """
    faux_worktree_scratch = outside_repo_dir / '.plan' / 'local' / 'worktrees' / 'plan-a' / 'scratch'
    faux_worktree_scratch.mkdir(parents=True)

    harness = build_harness(faux_worktree_scratch)

    assert harness.root != faux_worktree_scratch, 'a worktree-shaped scratch path must be relocated'
    assert harness.root.name.startswith('guard-node-'), harness.root
    assert (harness.root / 'driver.mjs').is_file(), 'the harness must be built in the relocated root'
    assert system_temp.release(harness.root) is True, 'the relocated root must be registered for teardown'
    assert not harness.root.exists(), 'the registered teardown must remove the relocated root'


def test_a_plain_scratch_root_is_used_as_is(outside_repo_dir: Path):
    """Matched control: outside a worktree the scratch path is returned unchanged.

    The relocation predicate is the one thing this plan must not change, so the
    non-worktree branch is pinned beside the relocating branch above.
    """
    plain_scratch = outside_repo_dir / 'plain'
    plain_scratch.mkdir()

    harness = build_harness(plain_scratch)

    assert harness.root == plain_scratch
    assert (plain_scratch / 'driver.mjs').is_file()
    assert system_temp.release(plain_scratch) is False, 'an unrelocated root is not registered'
