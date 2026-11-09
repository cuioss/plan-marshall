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
test uses it), and a function-level one is a failure unless the value is bound to
a name and that name is removed on a path that also runs when the work fails.

The relocation tests are deliverable 1's direct proof: the scratch-root predicate
and the returned path shape are unchanged, and the registered teardown removes
the relocated directory.
"""

from __future__ import annotations

import ast
from pathlib import Path

import _system_temp
from _guard_node_harness import build_harness

#: ``test/`` — the tree whose modules the sweep covers.
TEST_ROOT = Path(__file__).resolve().parents[2]

#: A walk that found fewer modules than this did not find the test tree: the guard
#: fails on the population BEFORE it reports a clean offender list, so a mis-rooted
#: sweep can never pass vacuously. The floor is high enough to prove the walk and
#: low enough not to move with every new test module.
_MINIMUM_SCANNED_MODULES = 100

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


def _is_removal_call(node: ast.AST) -> bool:
    """Whether ``node`` is a call to one of :data:`_REMOVAL_CALLS`."""
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in _REMOVAL_CALLS


def _reference_name(node: ast.AST) -> tuple[str | None, str | None]:
    """The plain name and the ``self`` attribute an expression names, if either."""
    if isinstance(node, ast.Name):
        return node.id, None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'self':
        return None, node.attr
    return None, None


def _names_target(node: ast.AST, name: str | None, attr: str | None) -> bool:
    """Whether ``node`` names the directory under test (a local or a ``self`` attribute)."""
    plain, attribute = _reference_name(node)
    if name is not None and plain == name:
        return True
    return attr is not None and attribute == attr


def _bound_target(function: ast.AST, call: ast.Call) -> tuple[str | None, str | None]:
    """The name the mkdtemp result is assigned to, as ``(local, self-attribute)``.

    A result that is never assigned — returned, passed on, or wrapped inline — has
    no name, so no removal of it can be shown and the site is an offender.
    """
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        if not any(inner is call for inner in ast.walk(node.value)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                return target.id, None
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
                return None, target.attr
    return None, None


def _removes_in(statements: list[ast.stmt], name: str | None, attr: str | None) -> bool:
    """Whether any of ``statements`` removes the named directory."""
    for statement in statements:
        for node in ast.walk(statement):
            if _is_removal_call(node) and node.args and _names_target(node.args[0], name, attr):
                return True
    return False


def _removes_in_a_finally(function: ast.AST, name: str | None, attr: str | None) -> bool:
    """Whether a ``finally`` block in ``function`` removes the directory.

    The finally is what makes the removal cover the failure path too; a removal on
    the success path alone leaks on every exception, which is exactly the shape
    this arm rejects.
    """
    return any(isinstance(node, ast.Try) and _removes_in(node.finalbody, name, attr) for node in ast.walk(function))


def _removes_after_a_yield(function: ast.AST, name: str | None, attr: str | None) -> bool:
    """Whether a generator fixture removes the directory after its ``yield``."""
    yields = [node.lineno for node in ast.walk(function) if isinstance(node, ast.Yield)]
    if not yields:
        return False
    last_yield = max(yields)
    for node in ast.walk(function):
        if _is_removal_call(node) and getattr(node, 'lineno', 0) > last_yield and node.args:
            if _names_target(node.args[0], name, attr):
                return True
    return False


def _registers_a_removal(function: ast.AST, name: str | None, attr: str | None) -> bool:
    """Whether ``function`` hands the directory to a registered teardown."""
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _DEFERRED_REMOVAL_CALLS:
            continue
        if any(_names_target(argument, name, attr) for argument in node.args):
            return True
    return False


def _class_owns_teardown(klass: ast.ClassDef, attr: str | None) -> bool:
    """Whether ``klass`` removes the ``self`` attribute in a lifecycle method.

    The lifecycle method IS the teardown, so its removal needs no ``finally``; the
    attribute has to be the one the creating method assigned, so one class method
    removing its own directory cannot clear an unrelated site in the same class.
    """
    if attr is None:
        return False
    return any(
        isinstance(item, _FUNCTION_NODES) and item.name in _LIFECYCLE_METHODS and _removes_in([item], None, attr)
        for item in klass.body
    )


def _sites_without_removal(source: str, label: str) -> tuple[list[str], int]:
    """Every mkdtemp site in ``source`` with no deterministic removal path.

    Args:
        source: Python source text to analyse.
        label: How the source is named in the returned rows.

    Returns:
        ``(rows, sites)`` — one ``{label}:{line}: {reason}`` row per offending
        site in line order, and the total number of mkdtemp sites examined.
    """
    tree = ast.parse(source)
    rows: list[tuple[int, str]] = []
    sites = 0
    for call, function, klass in _mkdtemp_sites(tree):
        sites += 1
        if function is None:
            rows.append(
                (call.lineno, f'{label}:{call.lineno}: module-level mkdtemp runs at import, once per pytest process')
            )
            continue
        name, attr = _bound_target(function, call)
        if name is None and attr is None:
            rows.append(
                (
                    call.lineno,
                    f'{label}:{call.lineno}: the mkdtemp result is never bound, so no removal of it can be shown',
                )
            )
            continue
        if (
            _registers_a_removal(function, name, attr)
            or _removes_in_a_finally(function, name, attr)
            or _removes_after_a_yield(function, name, attr)
            or (klass is not None and _class_owns_teardown(klass, attr))
        ):
            continue
        rows.append(
            (
                call.lineno,
                f'{label}:{call.lineno}: function-level mkdtemp with no removal of '
                f'{name or f"self.{attr}"} in {getattr(function, "name", "<function>")}: no rmtree in a '
                f'finally, no removal after a yield, no registered teardown, no lifecycle method',
            )
        )
    rows.sort()
    return [row for _, row in rows], sites


def _tree_sweep() -> tuple[list[str], int, int]:
    """Every offending mkdtemp site under ``test/``, with the scanned population.

    Returns:
        ``(offenders, scanned_modules, scanned_sites)``.
    """
    offenders: list[str] = []
    scanned = 0
    sites = 0
    for path in sorted(TEST_ROOT.rglob('*.py')):
        scanned += 1
        label = path.relative_to(TEST_ROOT).as_posix()
        try:
            source = path.read_text(encoding='utf-8')
        except OSError as exc:
            offenders.append(f'{label}: unreadable ({exc})')
            continue
        try:
            rows, found = _sites_without_removal(source, label)
        except SyntaxError as exc:
            offenders.append(f'{label}: unparseable ({exc})')
            continue
        offenders.extend(rows)
        sites += found
    return offenders, scanned, sites


def test_no_test_support_module_leaks_a_system_temp_directory():
    """Every system temp directory in the test tree has a deterministic removal path.

    The population is checked BEFORE the offender list, so a sweep that walked the
    wrong root fails instead of reporting "nothing found" — an empty tree yields an
    empty offender list for every possible rule. The failure then names every site,
    so the remedy is one edit per row rather than a search. ``_system_temp.create``
    is the form for a directory that outlives its creating function; otherwise the
    creating function must remove it.
    """
    offenders, scanned, sites = _tree_sweep()

    assert scanned > _MINIMUM_SCANNED_MODULES, (
        f'the sweep found only {scanned} modules under {TEST_ROOT}; a mis-rooted walk reports a clean '
        f'result for every rule and must fail here instead'
    )
    assert not offenders, (
        f'{len(offenders)} of {sites} system temp directory site(s) have no deterministic removal path:\n  '
        + '\n  '.join(offenders)
        + '\nCreate the directory with _system_temp.create(prefix=...), or remove the value you bound in a '
        'finally (or after a fixture yield), register its removal, or remove the self attribute in a class '
        'lifecycle method.'
    )


def test_the_sweep_flags_a_module_level_mkdtemp():
    """Positive control: the sweep's module-level arm fires on the shape it names."""
    offenders, sites = _sites_without_removal(
        "import tempfile\n\nROOT = tempfile.mkdtemp(prefix='leak-')\n",
        'control.py',
    )

    assert sites == 1
    assert offenders == [
        'control.py:3: module-level mkdtemp runs at import, once per pytest process',
    ]


def test_the_sweep_flags_an_unbound_function_level_mkdtemp():
    """Positive control: a bare function-level site is a failure."""
    offenders, _sites = _sites_without_removal(
        'import tempfile\nfrom pathlib import Path\n\n\ndef build():\n    return Path(tempfile.mkdtemp())\n',
        'control.py',
    )

    assert len(offenders) == 1
    assert offenders[0].startswith('control.py:6: '), offenders[0]


def test_the_sweep_does_not_credit_removing_another_path():
    """Positive control: an unrelated removal in the same function clears nothing."""
    source = """
import tempfile
from pathlib import Path


def build(marker: Path):
    root = Path(tempfile.mkdtemp())
    marker.unlink()
    return root
"""

    offenders, _sites = _sites_without_removal(source, 'control.py')

    assert len(offenders) == 1, offenders
    assert 'root' in offenders[0], offenders[0]


def test_the_sweep_does_not_credit_a_success_path_only_removal():
    """Positive control: a removal outside a ``finally`` leaks on the failure path."""
    source = """
import shutil
import tempfile
from pathlib import Path


def build():
    root = Path(tempfile.mkdtemp())
    try:
        build_in(root)
    except OSError:
        return None
    shutil.rmtree(root, ignore_errors=True)
    return root
"""

    offenders, _sites = _sites_without_removal(source, 'control.py')

    assert len(offenders) == 1, offenders


def test_the_sweep_clears_the_accepted_removal_paths():
    """Matched negative control: finally-removal, post-yield removal, class lifecycle."""
    source = """
import shutil
import tempfile
from pathlib import Path


def with_finally():
    root = Path(tempfile.mkdtemp())
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def after_the_yield():
    root = Path(tempfile.mkdtemp())
    yield root
    shutil.rmtree(root, ignore_errors=True)


class Owner:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp())

    def __exit__(self, *_exc):
        shutil.rmtree(self.root, ignore_errors=True)
"""

    offenders, sites = _sites_without_removal(source, 'control.py')

    assert sites == 3
    assert offenders == []


def test_release_all_drains_the_registry(monkeypatch, outside_repo_dir: Path):
    """The teardown hook's drain removes every registered root and counts them.

    The registry is replaced for the assertion so this control cannot remove a
    directory another test still owns; the two roots are plain directories, not
    ``mkdtemp`` results, because this module is itself under the sweep.
    """
    first = outside_repo_dir / 'drain-a'
    second = outside_repo_dir / 'drain-b'
    first.mkdir()
    second.mkdir()
    monkeypatch.setattr(_system_temp, '_REGISTERED', [first, second])

    assert _system_temp.release_all() == 2
    assert not first.exists()
    assert not second.exists()


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
    assert _system_temp.release(harness.root) is True, 'the relocated root must be registered for teardown'
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
    assert _system_temp.release(plain_scratch) is False, 'an unrelocated root is not registered'
