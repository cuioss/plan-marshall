# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every sibling-skill join is routed through the flat-aware helper, or declared.

A script that reaches a SIBLING skill builds its path by joining a bare skill name
onto a path derived from the skills root. That join is correct only on a nested
tree: a flat install (OpenCode, Antigravity) names the directory
``{bundle}-{skill}``, so the bare join names a path that cannot exist and the
caller silently degrades.

The guard is a call-site inventory, not a per-module spot check, and it works like
``test_flat_install_call_sites.py`` does for ``resolve_bundles_root``:

* the population is DISCOVERED from the source by AST — every
  ``<location-derived path> / '<known skill name>'`` join under
  ``marketplace/bundles/**/scripts/`` — so a new one cannot be added quietly;
* each discovered site must be DECLARED below with the one-line reason it is
  flat-safe, and the comparison runs in BOTH directions, so a stale declaration
  reds as loudly as an undeclared join;
* the modules the plan routed through the helper are named in ``ROUTED_MODULES``,
  and each must actually call it — a routed site that reverted to a bare join
  reappears in the discovered population and reds.

The skill names are read from the marketplace tree (every directory under
``marketplace/bundles/*/skills/``), never listed here: a second list is a second
answer waiting to diverge.
"""

from __future__ import annotations

import ast
from pathlib import Path

from test_skill_bootstrap_guard import DECLARED_CARRIERS

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

#: The helper every routed join goes through. Either spelling is accepted: the
#: resolving one returns a path, the requiring one raises naming both shapes.
_HELPER_NAMES: frozenset[str] = frozenset({'resolve_sibling_skill_path', 'require_sibling_skill_path'})

#: Discovered joins that are legitimately flat-safe, keyed by
#: ``(module path relative to the repo root, skill literal)``. Each carries the
#: reason it cannot fail on a flat tree, in one line.
_FLAT_SAFE_BOOTSTRAP_ANCHOR = (
    'the shared bootstrap anchor probes the flat `*-script-shared/scripts` sibling '
    'immediately after this nested candidate, and hands the library list to '
    'skill_bootstrap (PLAN-LB-93 D1/D2)'
)

#: The carrier roster is DERIVED from the bootstrap guard's own declaration, so a
#: carrier added or removed there cannot leave a second, hand-kept list behind.
#: One roster, one edit.
FLAT_SAFE_JOINS: dict[tuple[str, str], str] = {
    (module, 'script-shared'): _FLAT_SAFE_BOOTSTRAP_ANCHOR for module in sorted(DECLARED_CARRIERS)
}


#: Modules whose sibling joins MUST go through the helper — DERIVED, never listed.
#:
#: The defining property is "this module calls the flat-aware join", so the roster
#: is discovered by the same traversal the join inventory uses: an AST scan for a
#: call to either helper name. A second, hand-kept membership list would drift the
#: moment a module was routed or unrouted, and the whole point of the guard is that
#: nobody has to remember.
def _routed_modules() -> frozenset[str]:
    """Return every module under ``marketplace/bundles`` that calls the helper."""
    routed: set[str] = set()
    for module_path in _module_paths():
        tree = ast.parse(module_path.read_text(encoding='utf-8'), filename=str(module_path))
        called = {
            node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        }
        if called & _HELPER_NAMES:
            routed.add(module_path.relative_to(PROJECT_ROOT).as_posix())
    return frozenset(routed)


#: Attributes that make an expression "derived from a filesystem location", which
#: is what every sibling join in this tree walks up from.
_LOCATION_ATTRIBUTES: frozenset[str] = frozenset({'parent', 'parents', 'resolve', 'absolute'})


def _known_skill_names() -> frozenset[str]:
    """Return every skill directory name the marketplace source ships."""
    names: set[str] = set()
    for bundle_dir in MARKETPLACE_ROOT.iterdir():
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                names.add(skill_dir.name)
    return frozenset(names)


def _module_paths() -> list[Path]:
    """Return every ``scripts/**/*.py`` module under the marketplace bundles."""
    return [
        path
        for path in sorted(MARKETPLACE_ROOT.rglob('*.py'))
        if '__pycache__' not in path.parts and 'scripts' in path.parts
    ]


def _is_location_expression(node: ast.AST) -> bool:
    """Return whether ``node`` derives from a script location or the skills root."""
    if isinstance(node, ast.Call):
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ''
        if name == 'resolve_skills_root':
            return True
        if name in {'resolve', 'absolute', 'expanduser', 'Path'}:
            return any(_is_location_expression(arg) for arg in node.args)
        return False
    if isinstance(node, ast.Attribute):
        if node.attr in _LOCATION_ATTRIBUTES:
            return True
        return _is_location_expression(node.value)
    if isinstance(node, ast.Name):
        return node.id == '__file__'
    if isinstance(node, ast.Subscript):
        return _is_location_expression(node.value)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_location_expression(node.left)
    return False


def _location_bound_names(tree: ast.Module) -> set[str]:
    """Return the module-level names bound to a filesystem location expression.

    ``_SKILLS_DIR = resolve_skills_root(Path(__file__))`` and
    ``_THIS_DIR = Path(__file__).resolve().parent`` are the two spellings this tree
    uses; both are recorded so a later ``_SKILLS_DIR / 'skill'`` is recognised as a
    sibling join rather than as an arbitrary division.
    """
    bound: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if node.value is None or not _is_location_expression(node.value):
            continue
        bound.update(target.id for target in targets if isinstance(target, ast.Name))
    return bound


def _module_constant_skills(tree: ast.Module, skill_names: frozenset[str]) -> dict[str, list[str]]:
    """Map a module-level constant name to the skill literals it holds.

    ``_BUILD_EXTENSION_SKILLS = ('build-pyproject', …)`` is the shape the tree
    uses for a skill ROSTER, and a ``for skill in _BUILD_EXTENSION_SKILLS`` join is
    a sibling join like any other. Resolving the constant is what makes that shape
    visible; an iterable that is neither a literal nor such a constant stays
    invisible, which is the honest limit of a bounded AST scan.
    """
    constants: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, (ast.Tuple, ast.List)):
            continue
        literals = [
            element.value
            for element in value.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        ]
        skills = [literal for literal in literals if literal in skill_names]
        if not skills:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                constants[target.id] = skills
    return constants


def _loop_bound_skills(
    tree: ast.Module, skill_names: frozenset[str], constants: dict[str, list[str]]
) -> dict[str, list[str]]:
    """Map a loop variable to the skill literals its ``for`` statement binds it to.

    The import-loop idiom this tree uses for a cross-skill ``sys.path`` entry walks
    a tuple of skill names and joins each one onto the skills root, so the join's
    right operand is a NAME rather than a literal. The iterable is either a literal
    tuple (the ``_lib`` loops) or a module constant (``_BUILD_EXTENSION_SKILLS``);
    both are resolved. The predicate stays bounded because a literal that is not a
    real skill directory is never recorded.
    """
    bound: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        iterable = node.iter
        if isinstance(iterable, (ast.Tuple, ast.List)):
            values = [
                element.value
                for element in iterable.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
            skills = [value for value in values if value in skill_names]
        elif isinstance(iterable, ast.Name) and iterable.id in constants:
            skills = list(constants[iterable.id])
        else:
            continue
        if skills:
            bound[node.target.id] = skills
    return bound


def _right_operand_skills(node: ast.AST, constants: dict[str, list[str]], skill_names: frozenset[str]) -> list[str]:
    """Return the skill literals a join's right operand names, if any.

    Two spellings are covered beyond a plain literal: a loop variable bound to
    skill names, and a ``Path(base, '<skill>')``/ ``base.joinpath('<skill>')``
    argument. A computed name (f-string, concatenation) is out of scope for a
    bounded AST scan and is recorded nowhere.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value] if node.value in skill_names else []
    if isinstance(node, ast.Name):
        return list(constants.get(node.id, []))
    return []


def _joins(tree: ast.Module, skill_names: frozenset[str]) -> list[tuple[str, int]]:
    """Return ``(skill literal, line)`` for every sibling join in ``tree``."""
    bound = _location_bound_names(tree)
    constants = _module_constant_skills(tree, skill_names)
    loop_skills = _loop_bound_skills(tree, skill_names, constants)
    constants.update(loop_skills)
    found: list[tuple[str, int]] = []

    def _left_is_location(node: ast.AST) -> bool:
        return (isinstance(node, ast.Name) and node.id in bound) or _is_location_expression(node)

    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if not _left_is_location(node.left):
                continue
            found.extend((skill, node.lineno) for skill in _right_operand_skills(node.right, constants, skill_names))
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ''
            if name == 'joinpath' and isinstance(func, ast.Attribute) and _left_is_location(func.value):
                for argument in node.args:
                    found.extend(
                        (skill, node.lineno) for skill in _right_operand_skills(argument, constants, skill_names)
                    )
            elif name == 'Path' and node.args and _left_is_location(node.args[0]):
                for argument in node.args[1:]:
                    found.extend(
                        (skill, node.lineno) for skill in _right_operand_skills(argument, constants, skill_names)
                    )
    return found


def _discovered_joins() -> dict[tuple[str, str], list[int]]:
    """Return ``{(module, skill): [lines]}`` for every live sibling-skill join."""
    skill_names = _known_skill_names()
    discovered: dict[tuple[str, str], list[int]] = {}
    for module_path in _module_paths():
        relative = module_path.relative_to(PROJECT_ROOT).as_posix()
        tree = ast.parse(module_path.read_text(encoding='utf-8'), filename=str(module_path))
        for skill, line in _joins(tree, skill_names):
            discovered.setdefault((relative, skill), []).append(line)
    return discovered


def test_the_detector_finds_a_planted_join(tmp_path: Path) -> None:
    """Non-vacuity: the detector sees every spelling the tree uses."""
    planted = tmp_path / 'planted.py'
    planted.write_text(
        'from pathlib import Path\n'
        'from marketplace_bundles import resolve_skills_root\n'
        '_SKILLS_DIR = resolve_skills_root(Path(__file__))\n'
        '_THIS_DIR = Path(__file__).resolve().parent\n'
        "_ROSTER = ('build-maven', 'not-a-skill')\n"
        "A = _SKILLS_DIR / 'phase-6-finalize'\n"
        "B = _THIS_DIR.parent.parent / 'tools-file-ops' / 'scripts'\n"
        "C = Path(__file__).resolve().parent.parent / 'manage-locks'\n"
        "for _lib in ('ref-toon-format', 'not-a-skill'):\n"
        "    D = _SKILLS_DIR / _lib / 'scripts'\n"
        'for _skill in _ROSTER:\n'
        "    E = _SKILLS_DIR / _skill / 'scripts'\n"
        "F = _SKILLS_DIR.joinpath('build-npm')\n"
        "G = Path(_SKILLS_DIR, 'build-gradle')\n"
        "H = some_dir / 'build-server-client'\n"
        'I = base / build_server_client\n'
        "J = _SKILLS_DIR / f'dynamic-{name}'\n",
        encoding='utf-8',
    )
    skills = frozenset(
        {
            'phase-6-finalize',
            'tools-file-ops',
            'manage-locks',
            'ref-toon-format',
            'build-maven',
            'build-npm',
            'build-gradle',
            'build-server-client',
        }
    )
    tree = ast.parse(planted.read_text(encoding='utf-8'), filename=str(planted))

    assert {skill for skill, _line in _joins(tree, skills)} == {
        'phase-6-finalize',
        'tools-file-ops',
        'manage-locks',
        'ref-toon-format',
        'build-maven',
        'build-npm',
        'build-gradle',
    }


def test_every_sibling_join_is_declared() -> None:
    """No sibling join exists that the declarations do not account for."""
    discovered = set(_discovered_joins())
    declared = set(FLAT_SAFE_JOINS)

    assert discovered - declared == set(), (
        'sibling-skill joins that are neither routed through the helper nor declared flat-safe: '
        f'{sorted(discovered - declared)}'
    )


def test_every_declaration_still_has_a_join() -> None:
    """No stale declaration: every declared reason still describes a live join."""
    discovered = set(_discovered_joins())

    assert set(FLAT_SAFE_JOINS) - discovered == set(), (
        'declarations with no matching join (the join moved or was routed): '
        f'{sorted(set(FLAT_SAFE_JOINS) - discovered)}'
    )


def test_every_declaration_carries_a_reason() -> None:
    """A declaration without a reason is not a classification."""
    unreasoned = sorted(site for site, reason in FLAT_SAFE_JOINS.items() if not reason.strip())

    assert not unreasoned, unreasoned


def test_every_declared_join_appears_exactly_once() -> None:
    """A SECOND bare join of an already-declared skill must still red.

    The population is keyed by ``(module, skill)``, so re-introducing a second join
    of the same skill in the same module changes no KEY. Every shipped site is a
    single join, so pinning the count closes that hole without pinning line numbers
    (which every edit would churn).
    """
    repeated = {site: lines for site, lines in _discovered_joins().items() if len(lines) != 1}

    assert not repeated, f'joins counted more than once (a duplicate or a shadowed site): {repeated}'


def test_every_routed_module_calls_the_helper() -> None:
    """The derived routed set is non-empty, and each member really calls the helper."""
    routed = _routed_modules()

    assert routed, 'the helper-call scan found no module: the derivation itself is broken'
    missing: list[str] = []
    for relative in sorted(routed):
        tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding='utf-8'), filename=relative)
        called = {
            node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        }
        if not (called & _HELPER_NAMES):
            missing.append(relative)

    assert not missing, f'routed modules that do not call {sorted(_HELPER_NAMES)}: {missing}'


def test_the_routed_roster_is_derived_not_declared() -> None:
    """The roster tracks the source: every routed module is the one the plan changed.

    A hand-kept membership list would let a routed module be un-routed (or a new one
    added) without the guard noticing. The derivation is the assertion: the set is
    non-empty AND every module that calls the helper is in it — which is true by
    construction, so what this pins is that the traversal still SEES them all.
    """
    routed = _routed_modules()
    helper_callers = {
        module_path.relative_to(PROJECT_ROOT).as_posix()
        for module_path in _module_paths()
        if _HELPER_NAMES
        & {
            node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
            for node in ast.walk(ast.parse(module_path.read_text(encoding='utf-8')))
            if isinstance(node, ast.Call)
        }
    }

    assert routed == helper_callers
    assert len(routed) >= 10, f"expected the plan's routed modules, found {sorted(routed)}"


def test_a_routed_module_carries_no_bare_join() -> None:
    """A routed module must not keep a bare sibling join beside the helper call."""
    routed = _routed_modules()
    offenders = {
        f'{module} -> {skill}'
        for (module, skill) in _discovered_joins()
        if module in routed and (module, skill) not in FLAT_SAFE_JOINS
    }

    assert not offenders, sorted(offenders)
