# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared AST scan for the five mechanically-checkable test-harness shapes.

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
carries into every later test in the session. The leak is the MISSING arm, not
the condition: a branch that both restores a captured value and removes the key
when there was none covers the whole dichotomy and is a correct restore however
it is spelled, so only the one-armed form is reported. The same defect appears
in a fixture's post-yield half as a ``monkeypatch.delenv``/``delitem`` call,
which deletes a key the fixture may not have created. ``monkeypatch`` already
owns an unconditional restore that does not consult the prior value's
truthiness.

**R5 -- an unguarded runtime-derived parametrize.** A parametrize whose
argvalues are COMPUTED rather than displayed reports an empty parameter set as a
skip (or, once ``empty_parameter_set_mark = fail_at_collect`` is set, as a
collection failure). Either way the emptiness is invisible at the binding site,
so a derivation that silently came back empty makes every case it was meant to
produce disappear. A non-vacuity assertion beside the derivation is what turns
that into an attributable failure naming the population.

**R6 -- a hand-built CLI namespace.** A seam-pinned dispatcher test that
constructs its option object by hand carries only the attributes its author
remembered, not the parser's defaults -- so a flag added later with a default
breaks production while the suite stays green. The site is a module that both
stages an argv (directly or through the ``monkeypatch.setattr`` staging form)
and names the published ``build_parser`` seam; inside such a module every
``Namespace``/``SimpleNamespace`` construction carrying the ``command`` routing
key is reported, while a ``parse_ns`` call is the compliant form and is never
reported.

**R7 -- an unbounded walk from the shared temp root.** A per-test guard that
recursively walks the shared fixture base or the pytest basetemp tree pays the
cost of every sibling sandbox plus version-control stores and build caches on
every test. The walk is reported however it is spelled -- ``rglob`` over the
shared root, a recursive ``glob`` carrying a ``**`` pattern, or an ``os.walk``
rooted there. A walk over the test's own directories (``tmp_path``, a fixture
sandbox) is the compliant form and is never reported, however recursive it is.

**R8 -- a duplicate test-module registration.** A module loaded by file is
published in ``sys.modules`` under its stem, which replaces whatever that name
held. Registering the same name twice in one module, and adding a sibling
``conftest.py`` beside the single root registration point, both make the
binding a function of collection order. The predicate reports an intra-module
duplicate registration and any nested ``conftest.py``; a single registration
under the canonical stem, and a ``register=False`` load that publishes nothing,
are the compliant forms and are never reported.

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
from typing import TypeGuard

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
    """Repo-relative where that is meaningful, absolute otherwise.

    A caller may hand a predicate a path outside the repository — the matched
    negative controls feed each shape a synthetic module written to a temporary
    directory. Reporting such a path whole is right; raising on it would make the
    predicates unfalsifiable, since the only way to prove one fires is to give it
    an instance that is not in the tree it guards.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


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
        # Resolved on both sides of the comparison below: ``candidate`` is built
        # absolute-and-resolved, so comparing it against an unresolved parent
        # would never match for a caller that handed in a relative path, and
        # every same-directory reference would read as a cross-slice pin.
        own_dir = path.resolve().parent
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

    Both spellings count: a bare truthiness test (``if old_value:``) and an
    explicit ``is None`` comparison. Which of the two is used does not decide
    whether the shape leaks -- whether the other arm exists does, which
    :func:`_is_leaking_restore` applies on top of this.
    """
    if isinstance(test, (ast.Name, ast.Attribute)):
        return True
    if isinstance(test, ast.Compare):
        return any(isinstance(c, ast.Constant) and c.value is None for c in test.comparators)
    return False


def _is_leaking_restore(node: ast.If) -> bool:
    """True when this teardown branch puts state back on ONE arm only.

    The defect is the arm that is missing, not the condition that selects it. A
    branch that restores the captured value on one side and removes the key on
    the other covers both states the capture can be in, so it leaks nothing and
    is not reported -- ``monkeypatch`` is preferable where it is reachable, but a
    complete hand-rolled dichotomy is correct. A branch that acts on one side and
    falls through on the other leaves the mutated state in place for every later
    test in the session, which is the shape worth failing over.

    Which arm is the acting one does not matter, so the two arms are compared
    rather than read in a fixed order: ``if saved is None: pass / else:
    restore`` leaks exactly what ``if saved: restore`` leaks, and a predicate
    that only looked at the ``if`` body would report the first spelling and miss
    its mirror.
    """
    return _is_presence_keyed(node.test) and _is_restoring(node.body) != _is_restoring(node.orelse)


def _delenv_delitem_calls(body: list[ast.stmt]) -> list[int]:
    """Line numbers of ``monkeypatch.delenv``/``delitem`` calls in these statements."""
    lines: list[int] = []
    for node in body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                if sub.func.attr in {'delenv', 'delitem'}:
                    lines.append(sub.lineno)
    return lines


def _contains_yield(body: list[ast.stmt]) -> bool:
    """True when these statements yield, not counting a nested function's yields.

    A generator fixture defined inside the one being examined owns its own
    teardown, so attributing its yield to the enclosing function would classify
    the wrong ``finally`` as this fixture's teardown half.
    """
    stack: list[ast.AST] = list(body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        if isinstance(node, ast.Yield):
            return True
        stack.extend(ast.iter_child_nodes(node))
    return False


def _post_yield_statements(body: list[ast.stmt]) -> list[ast.stmt]:
    """The teardown half of a generator fixture -- what runs after its yield.

    A fixture commonly WRAPS its yield rather than stating it bare: a ``try``
    whose matching ``finally`` holds the teardown, or a ``with`` that keeps a
    context manager open across the yield and leaves the teardown in the
    statements following the block. Both are the teardown half exactly as the
    statements after a bare yield are, and reading only a direct ``Expr(Yield)``
    statement in the function body would report either as having no teardown at
    all -- which is how an unsafe deletion in one goes unexamined. A ``with`` has
    no ``finally`` of its own, so its branch is the ``try`` branch minus that
    term. The recursion covers a yield nested one or more wrapper levels deep.
    """
    for index, stmt in enumerate(body):
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Yield):
            return body[index + 1 :]
        if isinstance(stmt, ast.Try) and _contains_yield(stmt.body):
            return [*stmt.finalbody, *_post_yield_statements(stmt.body), *body[index + 1 :]]
        if isinstance(stmt, (ast.With, ast.AsyncWith)) and _contains_yield(stmt.body):
            return [*_post_yield_statements(stmt.body), *body[index + 1 :]]
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

        # Keyed by line so one defect is reported once. A fixture's teardown half
        # is now reachable through its ``finally`` as well as through the fixture,
        # and a leak sitting in both would otherwise be counted twice. The fixture
        # pass runs first so the more specific wording wins.
        found: dict[int, str] = {}

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            teardown = _post_yield_statements(node.body)
            for stmt in teardown:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.If) and _is_leaking_restore(sub):
                        found.setdefault(sub.lineno, 'presence-keyed restore in a fixture teardown')
            for line in _delenv_delitem_calls(teardown):
                found.setdefault(line, 'delenv/delitem in a fixture teardown half')

        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for stmt in node.finalbody:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.If) and _is_leaking_restore(sub):
                        found.setdefault(sub.lineno, 'presence-keyed restore in a finally block')

        for line, what in sorted(found.items()):
            result.hits.append(f'{_rel(path)}:{line}: {what}')
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
        # ``{**derived}`` parses as a Dict with a ``None`` key, so a display made
        # entirely of unpackings is exactly as empty as what it unpacks. This is
        # the Dict counterpart of the ``Starred`` exclusion one arm above.
        return any(key is not None for key in node.keys)
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and bool(node.value.strip())
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
        # A comprehension with no filter clause emits one element per element of
        # what it iterates, so it is exactly as non-empty as its sources. Every
        # generator must qualify: a nested `for` whose inner iterable is derived
        # from the outer loop variable is not resolvable here and stays a hit.
        return bool(node.generators) and all(
            not gen.ifs and not gen.is_async and _is_non_empty_by_construction(gen.iter, bindings, depth + 1)
            for gen in node.generators
        )
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


def _is_len_call(node: ast.expr) -> TypeGuard[ast.Call]:
    """True when this expression is a ``len(...)`` call.

    The ``TypeGuard`` return keeps this predicate the single authority on what a
    ``len()`` call is: every call site narrows the operand to ``ast.Call`` from
    this one check, rather than restating an ``isinstance`` conjunct of its own
    that could drift from what the predicate actually accepts.
    """
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'len' and bool(node.args)


def _named_in(node: ast.expr) -> set[str]:
    """Every name an expression reads, including the names of what it calls."""
    names = {sub.id for sub in ast.walk(node) if isinstance(sub, ast.Name)}
    names |= {
        sub.func.id if isinstance(sub.func, ast.Name) else sub.func.attr
        for sub in ast.walk(node)
        if isinstance(sub, ast.Call) and isinstance(sub.func, (ast.Name, ast.Attribute))
    }
    return names - {'len'}


def _len_comparison_names(node: ast.Compare) -> set[str]:
    """Names a ``len()`` comparison proves non-empty -- empty when it proves nothing.

    ``len(cases) > 0``, ``>= 1``, ``== 3`` and ``!= 0`` can only hold for a
    non-empty population. ``>= 0``, ``== 0``, ``len(a) == len(b)`` -- and
    ``!= 3``, which an empty population satisfies -- are every bit as true of an
    empty one, so they name nothing. The inequality is accepted against the
    constant ``0`` alone for exactly that reason.
    """
    operands = [node.left, *node.comparators]
    for index, op in enumerate(node.ops):
        left, right = operands[index], operands[index + 1]
        if _is_len_call(left) and isinstance(right, ast.Constant) and isinstance(right.value, int):
            if (
                (isinstance(op, ast.Gt) and right.value >= 0)
                or (isinstance(op, (ast.GtE, ast.Eq)) and right.value >= 1)
                or (isinstance(op, ast.NotEq) and right.value == 0)
            ):
                return _named_in(left.args[0])
        if _is_len_call(right) and isinstance(left, ast.Constant) and isinstance(left.value, int):
            if (
                (isinstance(op, ast.Lt) and left.value >= 0)
                or (isinstance(op, (ast.LtE, ast.Eq)) and left.value >= 1)
                or (isinstance(op, ast.NotEq) and left.value == 0)
            ):
                return _named_in(right.args[0])
    return set()


def _positive_cardinality_names(test: ast.expr) -> set[str]:
    """The names an assertion proves non-empty -- empty when it proves nothing.

    The single predicate all three R5 guard sites consult, so what counts as a
    non-vacuity guarantee cannot drift between the helper guard, the module-level
    guard and the cardinality-pinning test.

    Each accepted form names only what it actually proves. A bare value
    (``assert cases``) proves that value non-empty. A call's truthiness (``assert
    derive()``) proves its RESULT non-empty and says nothing about its arguments
    -- which is why ``assert isinstance(cases, list)`` names ``isinstance``
    rather than ``cases``, and so cannot suppress a hit on ``cases``. ``len()``
    is the one call whose truthiness is about its argument. Everything else names
    nothing: ``assert len(cases) >= 0`` holds for an empty derivation, so reading
    it as a guard would suppress exactly the hit this shape exists to report.
    """
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        return set().union(*(_positive_cardinality_names(value) for value in test.values))
    if isinstance(test, (ast.Name, ast.Attribute, ast.Subscript)):
        return _named_in(test)
    if isinstance(test, ast.Call):
        return _named_in(test.args[0]) if _is_len_call(test) else _named_in(test.func)
    if isinstance(test, ast.Compare):
        return _len_comparison_names(test)
    return set()


def _carried_non_empty_names(node: ast.expr, depth: int = 0) -> set[str]:
    """Names whose non-emptiness a returned expression carries through to itself.

    A transform that can only preserve cardinality passes the guarantee along:
    ``sorted(cases)`` is non-empty exactly when ``cases`` is, and a comprehension
    with no filter clause emits one element per element it iterates. A NARROWING
    transform passes nothing along -- a comprehension carrying an ``if``, a
    ``filter()``, and any other call not known to preserve cardinality can all
    return nothing from a non-empty input, so they name nothing and an assertion
    about their input proves nothing about their result.

    A call the helper returns names its CALLEE, because that is the name an
    assertion on the same call names too (``assert derive()`` names ``derive``),
    so the two sides meet on it.
    """
    if depth > 6:
        return set()
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Call):
        base = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
        if base in _NON_EMPTYING and node.args:
            return _carried_non_empty_names(node.args[0], depth + 1)
        if not base or base in _EMPTYING:
            return set()
        return {base}
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
        # One generator only: with a second, a non-empty outer iterable proves
        # nothing, since an empty inner one still yields no element.
        generators = node.generators
        if len(generators) == 1 and not generators[0].ifs and not generators[0].is_async:
            return _carried_non_empty_names(generators[0].iter, depth + 1)
        return set()
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _carried_non_empty_names(node.left, depth + 1) | _carried_non_empty_names(node.right, depth + 1)
    return set()


def _guards_its_result(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the helper asserts that what IT RETURNS is non-empty.

    WHICH population an assertion is attached to is the whole question here. A
    helper that asserts its INPUT non-empty and then returns a narrowed view of
    it has proved nothing about the parameter set its caller binds: every
    candidate can be filtered out and the parametrization still receives no
    cases, so reading such an assertion as a guard would pass exactly the vacuous
    shape R5 exists to report. The assertion must therefore name the returned
    result itself, or a name the return carries the guarantee through -- never
    merely a name the return expression happens to read.
    """
    guarded: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and node.value is not None:
            guarded |= _carried_non_empty_names(node.value)
    if not guarded:
        return False
    return any(
        isinstance(node, ast.Assert) and bool(_positive_cardinality_names(node.test) & guarded) for node in ast.walk(fn)
    )


def r5_unguarded_runtime_parametrize(paths: list[Path] | None = None) -> ScanResult:
    """Runtime-derived parametrize bindings carrying no non-vacuity guard.

    A guard counts at any of three sites: the helper that builds the argvalues
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
            name
            for stmt in tree.body
            if isinstance(stmt, ast.Assert)
            for name in _positive_cardinality_names(stmt.test)
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
    """Names a non-parametrized test proves non-empty."""
    pinned: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith('test'):
            continue
        if any(_is_parametrize(d) for d in node.decorator_list):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assert):
                pinned |= _positive_cardinality_names(sub.test)
    return pinned


# =============================================================================
# R6 -- hand-built CLI namespace
# =============================================================================


def _is_cli_driving_module(tree: ast.Module) -> bool:
    """True when the module drives a seam-pinned CLI dispatcher over ``sys.argv``.

    Both signals must hold: the module stages an argv (a direct ``sys.argv``
    read or the ``monkeypatch.setattr(sys, 'argv', ...)`` staging form) AND it
    names the published ``build_parser`` seam. The conjunction is the point: a
    module that stages an argv without a published seam exercises a router
    whose parser is only reachable through ``main`` (a different seam with its
    own pre-dispatch behaviour), while a module that names the seam without
    staging an argv asserts on the parser's shape rather than standing where
    its output would stand. Only the conjunction is the population
    ``parse_ns`` serves directly.
    """
    stages_argv = False
    names_seam = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == 'argv':
            value = node.value
            if isinstance(value, ast.Name) and value.id == 'sys':
                stages_argv = True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != 'setattr':
                continue
            receiver = node.func.value
            if not (isinstance(receiver, ast.Name) and receiver.id == 'monkeypatch'):
                continue
            if len(node.args) < 2:
                continue
            target, name = node.args[0], node.args[1]
            if (
                isinstance(target, ast.Name)
                and target.id == 'sys'
                and isinstance(name, ast.Constant)
                and name.value == 'argv'
            ):
                stages_argv = True
        if isinstance(node, ast.Name) and node.id == 'build_parser':
            names_seam = True
        if isinstance(node, ast.Attribute) and node.attr == 'build_parser':
            names_seam = True
    return stages_argv and names_seam


def _is_namespace_construction(node: ast.Call) -> bool:
    """True when this call hand-builds a CLI-dispatched option object.

    Only a construction carrying the ``command`` routing key counts: a CLI
    dispatcher routes on the parsed subcommand, so a hand-built namespace that
    names a command stands where the parser's own output would stand. A
    namespace built for an in-process command function (``root``/``glob``,
    ``plan_id``, ``pr_number``) names no command and is outside the
    population, however it is spelled.
    """
    func = node.func
    if isinstance(func, ast.Name) and func.id in {'Namespace', 'SimpleNamespace'}:
        pass
    elif isinstance(func, ast.Attribute) and func.attr in {'Namespace', 'SimpleNamespace'}:
        pass
    else:
        return False
    return any(kw.arg == 'command' for kw in node.keywords)


def r6_hand_built_cli_namespace(paths: list[Path] | None = None) -> ScanResult:
    """Hand-built dispatcher namespaces inside CLI-driving test modules.

    A ``parse_ns`` call is the compliant form and is never reported -- only a
    ``Namespace``/``SimpleNamespace`` construction carrying the ``command``
    routing key, inside a module that drives a dispatcher over ``sys.argv``
    (see :func:`_is_cli_driving_module`), is a hit.
    """
    result = ScanResult()
    for path in paths if paths is not None else test_modules():
        tree = _parse(path)
        if tree is None:
            result.unparseable.append(_rel(path))
            continue
        result.modules_examined += 1
        if not _is_cli_driving_module(tree):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_namespace_construction(node):
                result.hits.append(f'{_rel(path)}:{node.lineno}: hand-built CLI namespace')
    return result


# =============================================================================
# R7 -- unbounded walk from the shared temp root
# =============================================================================

#: Name fragments that identify the shared temp root a per-test guard must not
#: recurse from. ``tmp_path`` and a fixture sandbox carry none of these, so a
#: scoped walk over the test's own directories never matches.
_SHARED_TEMP_ROOT_MARKERS = frozenset(
    {
        'TEST_FIXTURE_BASE',
        'FIXTURE_BASE',
        'PLAN_DIR_NAME',
        'basetemp',
        'pytest-basetemp',
        'test-fixture',
        'test_fixture',
    }
)


def _is_shared_temp_root_text(text: str) -> bool:
    """True when this source fragment names the shared temp root."""
    return any(marker in text for marker in _SHARED_TEMP_ROOT_MARKERS)


def _is_shared_temp_root_expr(node: ast.expr) -> bool:
    """True when this root expression resolves to the shared temp tree.

    The check is textual on the unparsed fragment: a ``Name`` carrying a marker
    (``TEST_FIXTURE_BASE``), an attribute hanging off one (``PROJECT_ROOT /
    '.plan'`` spells the same tree through a constant), or a call result derived
    from one. Textual matching keeps the predicate independent of how the caller
    spells the join, while ``tmp_path`` carries no marker and never matches.
    """
    try:
        text = ast.unparse(node)
    except (ValueError, SyntaxError):
        return False
    return _is_shared_temp_root_text(text)


def _is_recursive_glob(node: ast.Call) -> bool:
    """True when this ``glob`` call carries a recursive ``**`` pattern."""
    if not isinstance(node.func, ast.Attribute) or node.func.attr != 'glob':
        return False
    for arg in (*node.args, *(kw.value for kw in node.keywords)):
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and '**' in arg.value:
            return True
    return False


def r7_unbounded_shared_temp_walk(paths: list[Path] | None = None) -> ScanResult:
    """Recursive walks rooted at the shared temp root.

    A ``rglob`` over the shared root, a recursive ``glob`` carrying a ``**``
    pattern over it, or an ``os.walk`` rooted there is a hit. A walk over the
    test's own directories (``tmp_path``, a fixture sandbox) is the compliant
    form and is never reported, however recursive it is, because its cost is
    bounded by the test's own footprint.
    """
    result = ScanResult()
    for path in paths if paths is not None else test_modules():
        tree = _parse(path)
        if tree is None:
            result.unparseable.append(_rel(path))
            continue
        result.modules_examined += 1
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            attr = node.func.attr
            if attr == 'rglob':
                if _is_shared_temp_root_expr(node.func.value):
                    result.hits.append(f'{_rel(path)}:{node.lineno}: unbounded walk from shared temp root')
            elif attr == 'glob':
                if _is_recursive_glob(node) and _is_shared_temp_root_expr(node.func.value):
                    result.hits.append(f'{_rel(path)}:{node.lineno}: unbounded walk from shared temp root')
            elif attr == 'walk':
                receiver = node.func.value
                is_os_walk = isinstance(receiver, ast.Name) and receiver.id == 'os'
                if is_os_walk and node.args and _is_shared_temp_root_expr(node.args[0]):
                    result.hits.append(f'{_rel(path)}:{node.lineno}: unbounded walk from shared temp root')
    return result


# =============================================================================
# R8 -- duplicate test-module registration and nested conftest
# =============================================================================

#: Loader calls whose execution publishes a module in ``sys.modules`` under the
#: resolved name. ``parse_ns`` loads to reach its parser and publishes the same
#: way, but its fourth positional is an argv token rather than a module name, so
#: it is excluded here: reading it would invent registrations that do not exist.
_REGISTERING_CALLS = {'load_script_module', 'load_skill_module'}


def _r8_registered_name(call: ast.Call) -> str | None:
    """Return the ``sys.modules`` name ``call`` publishes, or ``None``.

    A call passing a literal ``register=False`` publishes nothing and is never a
    registration. A ``module_name`` keyword names the registration directly; a
    third positional ending in ``.py`` names it by stem. Anything else is
    statically unresolvable and contributes no name rather than a guessed one.
    """
    for keyword in call.keywords:
        if keyword.arg == 'register' and isinstance(keyword.value, ast.Constant):
            if keyword.value.value is False:
                return None
        if keyword.arg == 'module_name' and isinstance(keyword.value, ast.Constant):
            if isinstance(keyword.value.value, str):
                return keyword.value.value
    if len(call.args) >= 3:
        script = call.args[2]
        if isinstance(script, ast.Constant) and isinstance(script.value, str):
            if script.value.endswith('.py'):
                return Path(script.value).stem
    return None


def _r8_file_key(call: ast.Call) -> str | None:
    """Return the ``(bundle, skill, file)`` triple ``call`` loads, or ``None``.

    Only literal triples resolve: a bundle, skill and file each spelled as a
    string constant. Anything else contributes no key rather than a guessed one,
    so a dynamically addressed load never joins — or splits — a file group.
    """
    if len(call.args) < 3:
        return None
    parts: list[str] = []
    for arg in call.args[:3]:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            parts.append(arg.value)
        else:
            return None
    return '/'.join(parts)


def _r8_all_test_files() -> list[Path]:
    """Every Python module under the test tree, sorted."""
    return sorted(TEST_ROOT.rglob('*.py'))


def r8_duplicate_test_module_registrations(paths: list[Path] | None = None) -> ScanResult:
    """One helper file registered under two names in the same module.

    Each helper registers once under its canonical stem: loading the same
    ``(bundle, skill, file)`` triple under a second ``sys.modules`` name
    publishes a duplicate registration, so collection order decides which copy a
    later importer sees. A single registration of the triple, and a
    ``register=False`` load that publishes nothing, are the compliant forms and
    are never reported. Triples are compared within each module, never across
    modules: two modules loading the same helper each hold their own
    registration, which is the expected reuse rather than a duplicate.
    """
    result = ScanResult()
    for path in paths if paths is not None else _r8_all_test_files():
        tree = _parse(path)
        if tree is None:
            result.unparseable.append(_rel(path))
            continue
        result.modules_examined += 1
        seen: dict[str, str] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', None)
            if name not in _REGISTERING_CALLS:
                continue
            registered = _r8_registered_name(node)
            key = _r8_file_key(node)
            if registered is None or key is None:
                continue
            if key in seen and seen[key] != registered:
                result.hits.append(
                    f'{_rel(path)}:{node.lineno}: duplicate registration of {key!r} '
                    f'as {registered!r} (first as {seen[key]!r})'
                )
            else:
                seen.setdefault(key, registered)
    return result


def r8_nested_conftest_files(paths: list[Path] | None = None) -> ScanResult:
    """Nested ``conftest.py`` files beside the single root registration point.

    ``test/conftest.py`` is the one permitted registration point. Every other
    ``conftest.py`` anywhere under ``test/**/`` shadows it by module name for
    the sibling tests that import by bare name. The scan walks the filesystem
    rather than the AST because the defect is the file's existence, not its
    content; an explicit ``paths`` list is honoured so synthetic controls stay
    falsifiable.
    """
    result = ScanResult()
    if paths is not None:
        candidates = paths
    else:
        candidates = sorted(TEST_ROOT.rglob('conftest.py'))
        result.modules_examined = max(len(candidates), 1)
        if not candidates:
            return result
    root = TEST_ROOT / 'conftest.py'
    explicit = paths is not None
    for path in candidates:
        if explicit:
            if _parse(Path(path)) is None:
                result.unparseable.append(_rel(Path(path)))
                continue
            result.modules_examined += 1
        if Path(path).name != 'conftest.py':
            continue
        try:
            resolved = Path(path).resolve()
        except OSError:
            resolved = Path(path)
        try:
            root_resolved = root.resolve()
        except OSError:
            root_resolved = root
        if resolved == root_resolved:
            continue
        result.hits.append(f'{_rel(Path(path))}: nested conftest.py beside the single root registration point')
    return result
