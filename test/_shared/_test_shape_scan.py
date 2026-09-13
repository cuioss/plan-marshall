# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared AST scan for the three mechanically-checkable test-harness shapes.

Each shape below is a way for a test to stop testing what it names while still
reporting green, so none of them is caught by running the suite -- that is
precisely what makes them worth a mechanical guard rather than review attention.

**R1 -- a cross-slice filename pin.** A test that names another slice's test
module by path couples itself to a filename it does not own. The unrelated slice
renaming its own file then fails THIS module, and the failure reports a filename
rather than the contract under test. The population a guard cares about is the
role the named module plays, which is derivable; the filename is an accident of
where that role currently lives.

**R4 -- a presence-keyed restore.** A teardown that restores captured state only
when the captured value is truthy leaks on the falsy branch: an empty-string
environment variable is captured, deleted, and never put back, so its absence
carries into every later test in the session. The same defect appears in a
fixture's post-yield half as a ``monkeypatch.delenv``/``delitem`` call, which
deletes a key the fixture may not have created. ``monkeypatch`` already owns an
unconditional restore that does not consult the prior value's truthiness.

**R5 -- an unguarded runtime-derived parametrize.** A parametrize whose
argvalues are COMPUTED rather than displayed reports an empty parameter set as a
skip (or, once ``empty_parameter_set_mark = fail_at_collect`` is set, as a
collection failure). Either way the emptiness is invisible at the binding site,
so a derivation that silently came back empty makes every case it was meant to
produce disappear. A non-vacuity assertion beside the derivation is what turns
that into an attributable failure naming the population.

**Why R3 has no entry here.** R3 -- a hand-kept constant mirror, where a test
restates a production constant as its own literal -- is not mechanically
checkable in the way the three above are. Deciding whether a literal in a test
MIRRORS a production constant or legitimately PINS an independently-chosen
expected value requires knowing the author's intent: the two are textually
identical, and a guard keyed on textual equality would flag every correct
expected-value assertion in the suite. R3 is handled by review and by the
converted instances, not by a predicate.

The general, forward-looking form of these rules lives in the
``plan-marshall:persona-module-tester`` testing-methodology standard, which
names this module as the concrete instance -- the same one-directional link that
standard already uses for ``_neutralize_daemon_routing``. The check-local reason
for each shape is stated here, where the check is.

Every entry point returns the population it examined -- modules walked, and the
modules that failed to parse -- alongside its hits. A module that could not be
parsed is reported as unmeasured coverage rather than counted as clean, so a
caller can refuse a scan that resolved nothing instead of reading it as a clean
result.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

#: The test tree this scan walks. ``_shared`` sits one level below it.
TEST_ROOT = Path(__file__).resolve().parents[1]

#: Repo root, used to resolve the repo-relative path literals R1 looks for.
REPO_ROOT = TEST_ROOT.parent


@dataclass
class ScanResult:
    """Hits plus the population they were drawn from.

    ``modules_examined`` is the count of modules successfully parsed, and
    ``unparseable`` names the ones that were not. A caller MUST treat a zero
    ``modules_examined`` -- or a non-empty ``unparseable`` -- as unmeasured
    coverage rather than as a clean result: a module that could not be parsed is
    one that might carry the shape and was never looked at.
    """

    hits: list[str] = field(default_factory=list)
    modules_examined: int = 0
    unparseable: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """True only when nothing was found AND the whole population was read."""
        return not self.hits and not self.unparseable and self.modules_examined > 0


def test_modules() -> list[Path]:
    """Every ``test_*.py`` module under the test tree, sorted."""
    return sorted(TEST_ROOT.rglob('test_*.py'))


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


# =============================================================================
# R1 -- cross-slice filename pin
# =============================================================================


def r1_cross_slice_filename_pins(paths: list[Path] | None = None) -> ScanResult:
    """String literals naming an EXISTING test module outside the owning directory.

    A literal naming a module in the containing module's OWN directory is not a
    cross-slice pin -- a slice may refer to its own files -- so the predicate
    keys on the directory boundary, not on the mere presence of a path literal.
    A literal that resolves to no file on disk is not reported either: it is a
    stale string or an example, not a live coupling to another slice's filename.
    """
    result = ScanResult()
    for path in paths if paths is not None else test_modules():
        tree = _parse(path)
        if tree is None:
            result.unparseable.append(_rel(path))
            continue
        result.modules_examined += 1
        own_dir = path.parent
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            value = node.value
            if not value.endswith('.py') or '/' not in value:
                continue
            candidate = (REPO_ROOT / value).resolve()
            if not candidate.is_file():
                continue
            if not Path(value).name.startswith('test_'):
                continue
            if candidate.parent == own_dir:
                continue
            result.hits.append(f'{_rel(path)}:{node.lineno}: pins {value}')
    return result


# =============================================================================
# R4 -- presence-keyed restore
# =============================================================================

#: Calls that PUT state back. An ``If`` in a teardown whose body performs one of
#: these is a restore branch; keying on the act of restoring rather than on a
#: variable-name convention keeps the predicate from depending on how the
#: captured value happens to be spelled.
_RESTORE_CALLS = {'setattr', 'setenv', 'setitem', 'pop', 'update', '__setitem__'}


def _is_restoring(body: list[ast.stmt]) -> bool:
    """True when these statements put captured state back."""
    for node in body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign):
                for target in sub.targets:
                    if isinstance(target, ast.Subscript):
                        return True
            if isinstance(sub, ast.Call):
                name = sub.func.attr if isinstance(sub.func, ast.Attribute) else getattr(sub.func, 'id', '')
                if name in _RESTORE_CALLS:
                    return True
            if isinstance(sub, ast.Delete):
                return True
    return False


def _is_presence_keyed(test: ast.expr) -> bool:
    """True when the branch condition consults whether a captured value is present.

    Both spellings count: a bare truthiness test (``if old_value:``), which is
    the leaking form, and an explicit ``is not None`` comparison, which is
    correct about None but still hand-rolled.
    """
    if isinstance(test, (ast.Name, ast.Attribute)):
        return True
    if isinstance(test, ast.Compare):
        return any(isinstance(c, ast.Constant) and c.value is None for c in test.comparators)
    return False


def _delenv_delitem_calls(body: list[ast.stmt]) -> list[int]:
    """Line numbers of ``monkeypatch.delenv``/``delitem`` calls in these statements."""
    lines: list[int] = []
    for node in body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                if sub.func.attr in {'delenv', 'delitem'}:
                    lines.append(sub.lineno)
    return lines


def _post_yield_statements(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    """The teardown half of a generator fixture -- statements after its yield."""
    for index, stmt in enumerate(fn.body):
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Yield):
            return fn.body[index + 1 :]
    return []


def r4_presence_keyed_restores(paths: list[Path] | None = None) -> ScanResult:
    """Presence-keyed restore branches, and delenv/delitem in a teardown half.

    Two sub-shapes, reported together because they are the same defect wearing
    different clothes: a restore that consults the captured value's truthiness,
    and a teardown that deletes a key rather than restoring what was there.
    """
    result = ScanResult()
    for path in paths if paths is not None else test_modules():
        tree = _parse(path)
        if tree is None:
            result.unparseable.append(_rel(path))
            continue
        result.modules_examined += 1

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for stmt in node.finalbody:
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.If) and _is_presence_keyed(sub.test) and _is_restoring(sub.body):
                            result.hits.append(f'{_rel(path)}:{sub.lineno}: presence-keyed restore in a finally block')
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                teardown = _post_yield_statements(node)
                if not teardown:
                    continue
                for stmt in teardown:
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.If) and _is_presence_keyed(sub.test) and _is_restoring(sub.body):
                            result.hits.append(
                                f'{_rel(path)}:{sub.lineno}: presence-keyed restore in a fixture teardown'
                            )
                for line in _delenv_delitem_calls(teardown):
                    result.hits.append(f'{_rel(path)}:{line}: delenv/delitem in a fixture teardown half')
    return result


# =============================================================================
# R5 -- unguarded runtime-derived parametrize
# =============================================================================

#: Builtins that cannot turn a non-empty input into an empty output. A
#: parametrize binding one of these over a literal is as non-empty as the
#: literal, so it is NOT a runtime-derived binding and is not reported.
_NON_EMPTYING = {'sorted', 'list', 'tuple', 'set', 'frozenset', 'reversed'}

#: Builtins that CAN yield nothing from a non-empty input, so a binding through
#: one of them stays runtime-derived however literal its argument looks.
_EMPTYING = {'filter', 'zip', 'range'}


def _is_parametrize(dec: ast.expr) -> bool:
    return isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == 'parametrize'


def _argvalues(dec: ast.Call) -> ast.expr | None:
    for kw in dec.keywords:
        if kw.arg == 'argvalues':
            return kw.value
    return dec.args[1] if len(dec.args) >= 2 else None


def _bindings(body: list[ast.stmt]) -> dict[str, ast.expr]:
    out: dict[str, ast.expr] = {}
    for stmt in body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
            out[stmt.target.id] = stmt.value
    return out


def _is_non_empty_by_construction(node: ast.expr, bindings: dict[str, ast.expr], depth: int = 0) -> bool:
    """True when the expression cannot be empty, following module/class bindings.

    A Name is followed to its binding rather than treated as opaque: a name bound
    to a literal display one scope up is as visible as the display itself, and
    reporting it would bury the real hits under hundreds of false ones.
    """
    if depth > 6:
        return False
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return bool(node.elts) and not all(isinstance(e, ast.Starred) for e in node.elts)
    if isinstance(node, ast.Dict):
        return bool(node.keys)
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and bool(node.value.strip())
    if isinstance(node, ast.Name):
        target = bindings.get(node.id)
        return target is not None and _is_non_empty_by_construction(target, bindings, depth + 1)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_non_empty_by_construction(node.left, bindings, depth + 1) or _is_non_empty_by_construction(
            node.right, bindings, depth + 1
        )
    if isinstance(node, ast.Call):
        base = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
        if base in _EMPTYING:
            return False
        if base in _NON_EMPTYING and node.args:
            return _is_non_empty_by_construction(node.args[0], bindings, depth + 1)
        if base in {'keys', 'values', 'items'} and isinstance(node.func, ast.Attribute):
            return _is_non_empty_by_construction(node.func.value, bindings, depth + 1)
        return False
    return False


def _guards_its_result(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the helper asserts the emptiness of what it returns.

    Only a non-vacuity assertion counts -- a bare truthiness assert, or one
    involving ``len()``. An equality assert about something unrelated is not a
    guard, and counting it as one would let an unguarded derivation through.
    """
    returned = {
        sub.id
        for node in ast.walk(fn)
        if isinstance(node, ast.Return) and node.value is not None
        for sub in ast.walk(node.value)
        if isinstance(sub, ast.Name)
    }
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        is_non_vacuity = isinstance(test, (ast.Name, ast.Call, ast.Attribute)) or (
            isinstance(test, ast.Compare)
            and any(isinstance(s, ast.Call) and getattr(s.func, 'id', '') == 'len' for s in ast.walk(test))
        )
        if not is_non_vacuity:
            continue
        names = {s.id for s in ast.walk(test) if isinstance(s, ast.Name)}
        if not returned or names & returned:
            return True
    return False


def r5_unguarded_runtime_parametrize(paths: list[Path] | None = None) -> ScanResult:
    """Runtime-derived parametrize bindings carrying no non-vacuity guard.

    A guard counts at any of three sites, because all three run at collection
    time and all three name the population: the helper that builds the argvalues
    asserting its own result, a module-level assert naming the bound name, or a
    separate non-parametrized test pinning the population's cardinality. An
    assertion inside the parametrized test's own body is NOT a guard -- that body
    never runs when the parameter set is empty.
    """
    result = ScanResult()
    for path in paths if paths is not None else test_modules():
        tree = _parse(path)
        if tree is None:
            result.unparseable.append(_rel(path))
            continue
        result.modules_examined += 1

        module_bindings = _bindings(tree.body)
        functions = {s.name: s for s in tree.body if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))}
        module_guarded = {
            sub.id
            for stmt in tree.body
            if isinstance(stmt, ast.Assert)
            for sub in ast.walk(stmt.test)
            if isinstance(sub, ast.Name)
        }
        cardinality_pinned = _cardinality_pinned_names(tree)

        for dec, bindings in _parametrize_sites(tree, module_bindings):
            argvalues = _argvalues(dec)
            if argvalues is None or _is_non_empty_by_construction(argvalues, bindings):
                continue
            names = {s.id for s in ast.walk(argvalues) if isinstance(s, ast.Name)}
            callees = {
                s.func.id if isinstance(s.func, ast.Name) else s.func.attr
                for s in ast.walk(argvalues)
                if isinstance(s, ast.Call) and isinstance(s.func, (ast.Name, ast.Attribute))
            }
            if any(fn in functions and _guards_its_result(functions[fn]) for fn in callees):
                continue
            if names & module_guarded or (names | callees) & cardinality_pinned:
                continue
            if any(
                (target := bindings.get(nm)) is not None
                and any(
                    isinstance(s, ast.Call)
                    and isinstance(s.func, ast.Name)
                    and s.func.id in functions
                    and _guards_its_result(functions[s.func.id])
                    for s in ast.walk(target)
                )
                for nm in names
            ):
                continue
            result.hits.append(f'{_rel(path)}:{dec.lineno}: unguarded runtime-derived parametrize')
    return result


def _parametrize_sites(tree: ast.Module, module_bindings: dict[str, ast.expr]):
    """Yield ``(decorator, visible bindings)`` for every parametrize in the module.

    Class bodies contribute their own bindings, so a parametrize naming a CLASS
    attribute resolves against it rather than reading as an unbound name.
    """

    def visit(body: list[ast.stmt], bindings: dict[str, ast.expr]):
        for stmt in body:
            if isinstance(stmt, ast.ClassDef):
                for dec in stmt.decorator_list:
                    if _is_parametrize(dec):
                        yield dec, bindings
                yield from visit(stmt.body, {**bindings, **_bindings(stmt.body)})
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in stmt.decorator_list:
                    if _is_parametrize(dec):
                        yield dec, bindings

    yield from visit(tree.body, module_bindings)


def _cardinality_pinned_names(tree: ast.Module) -> set[str]:
    """Names a non-parametrized test pins the cardinality of via ``len()``."""
    pinned: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith('test'):
            continue
        if any(_is_parametrize(d) for d in node.decorator_list):
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Assert):
                continue
            if not any(isinstance(s, ast.Call) and getattr(s.func, 'id', '') == 'len' for s in ast.walk(sub.test)):
                continue
            for s in ast.walk(sub.test):
                if isinstance(s, ast.Name):
                    pinned.add(s.id)
                elif isinstance(s, ast.Call) and isinstance(s.func, ast.Name):
                    pinned.add(s.func.id)
    return pinned
