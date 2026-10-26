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

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

#: The helper every routed join goes through. Either spelling is accepted: the
#: resolving one returns a path, the requiring one raises naming both shapes.
_HELPER_NAMES: frozenset[str] = frozenset({'resolve_sibling_skill_path', 'require_sibling_skill_path'})

#: Discovered joins that are legitimately flat-safe, keyed by
#: ``(module path relative to the repo root, skill literal)``. Each carries the
#: reason it cannot fail on a flat tree, in one line.
_FLAT_SAFE_LIB_LOOP = (
    'the same import loop probes plan-marshall-{lib} immediately after the bare join, which is the flat directory name'
)

_FLAT_SAFE_GENERATOR_BOOTSTRAP = (
    'sys.path hints only: every invocation is made with the executor PYTHONPATH, where the flat '
    'dirs already resolve; exercised from the flat fixture by test_flat_lane_path_joins'
)

FLAT_SAFE_JOINS: dict[tuple[str, str], str] = {
    (
        'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py',
        'ref-toon-format',
    ): _FLAT_SAFE_GENERATOR_BOOTSTRAP,
    (
        'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py',
        'script-shared',
    ): _FLAT_SAFE_GENERATOR_BOOTSTRAP,
    (
        'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py',
        'tools-file-ops',
    ): _FLAT_SAFE_GENERATOR_BOOTSTRAP,
    ('marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py', 'ref-toon-format'): (
        _FLAT_SAFE_LIB_LOOP
    ),
    ('marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py', 'tools-file-ops'): (
        _FLAT_SAFE_LIB_LOOP
    ),
    ('marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py', 'platform-runtime'): (
        _FLAT_SAFE_LIB_LOOP
    ),
    ('marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py', 'ref-toon-format'): (
        _FLAT_SAFE_LIB_LOOP
    ),
    ('marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py', 'tools-file-ops'): (
        _FLAT_SAFE_LIB_LOOP
    ),
    ('marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py', 'tools-script-executor'): (
        _FLAT_SAFE_LIB_LOOP
    ),
    ('marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py', 'ref-toon-format'): (
        _FLAT_SAFE_LIB_LOOP
    ),
    (
        'marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py',
        'ref-toon-format',
    ): _FLAT_SAFE_LIB_LOOP,
    (
        'marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py',
        'tools-file-ops',
    ): _FLAT_SAFE_LIB_LOOP,
    (
        'marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py',
        'tools-permission-doctor',
    ): _FLAT_SAFE_LIB_LOOP,
}

#: Modules whose sibling joins MUST go through the helper. Each entry is the
#: module path relative to the repo root.
ROUTED_MODULES: frozenset[str] = frozenset(
    {
        'marketplace/bundles/plan-marshall/skills/extension-api/scripts/configurable_contract.py',
        'marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py',
        'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py',
        'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py',
        'marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py',
        'marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_queue_slot.py',
        'marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/_ci_log_filter.py',
        'marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py',
        'marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py',
        'marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/integrate_into_main.py',
        'marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/prepare_execute.py',
    }
)

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


def _loop_bound_skills(tree: ast.Module, skill_names: frozenset[str]) -> dict[str, list[str]]:
    """Map a loop variable to the skill literals its ``for`` statement binds it to.

    The import-loop idiom this tree uses for a cross-skill ``sys.path`` entry walks
    a tuple of skill names and joins each one onto the skills root, so the join's
    right operand is a NAME rather than a literal. Recording those bindings is what
    lets the guard see that site at all; the predicate stays bounded because a
    literal that is not a real skill directory is not recorded.
    """
    bound: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        iterable = node.iter
        if not isinstance(iterable, (ast.Tuple, ast.List)):
            continue
        values = [
            element.value
            for element in iterable.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        ]
        skills = [value for value in values if value in skill_names]
        if skills:
            bound[node.target.id] = skills
    return bound


def _joins(tree: ast.Module, skill_names: frozenset[str]) -> list[tuple[str, int]]:
    """Return ``(skill literal, line)`` for every sibling join in ``tree``."""
    bound = _location_bound_names(tree)
    loop_skills = _loop_bound_skills(tree, skill_names)
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
            continue
        left = node.left
        if not ((isinstance(left, ast.Name) and left.id in bound) or _is_location_expression(left)):
            continue
        right = node.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            if right.value in skill_names:
                found.append((right.value, node.lineno))
        elif isinstance(right, ast.Name) and right.id in loop_skills:
            found.extend((skill, node.lineno) for skill in loop_skills[right.id])
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
        "A = _SKILLS_DIR / 'phase-6-finalize'\n"
        "B = _THIS_DIR.parent.parent / 'tools-file-ops' / 'scripts'\n"
        "C = Path(__file__).resolve().parent.parent / 'manage-locks'\n"
        "for _lib in ('ref-toon-format', 'not-a-skill'):\n"
        "    D = _SKILLS_DIR / _lib / 'scripts'\n"
        "E = some_dir / 'phase-6-finalize'\n"
        'F = base / name\n',
        encoding='utf-8',
    )
    skills = frozenset({'phase-6-finalize', 'tools-file-ops', 'manage-locks', 'ref-toon-format'})
    tree = ast.parse(planted.read_text(encoding='utf-8'), filename=str(planted))

    assert {skill for skill, _line in _joins(tree, skills)} == {
        'phase-6-finalize',
        'tools-file-ops',
        'manage-locks',
        'ref-toon-format',
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


def test_every_routed_module_calls_the_helper() -> None:
    """Each module the plan routed reaches its sibling skills through the helper."""
    missing: list[str] = []
    for relative in sorted(ROUTED_MODULES):
        tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding='utf-8'), filename=relative)
        called = {
            node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        }
        if not (called & _HELPER_NAMES):
            missing.append(relative)

    assert not missing, f'routed modules that do not call {sorted(_HELPER_NAMES)}: {missing}'


def test_a_routed_module_carries_no_bare_join() -> None:
    """A routed module must not keep a bare sibling join beside the helper call."""
    offenders = {
        f'{module} -> {skill}'
        for (module, skill) in _discovered_joins()
        if module in ROUTED_MODULES and (module, skill) not in FLAT_SAFE_JOINS
    }

    assert not offenders, sorted(offenders)
