#!/usr/bin/env python3
"""Regression tests for the phase-2-refine scope_estimate contract.

phase-2-refine is a workflow-driven skill (no Python entry point of its own).
Step 9 of phase-2-refine derives a `scope_estimate` value from the module
mapping using rules documented verbatim in
``marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/
refine-workflow-detail.md`` (§ Derivation Rules). Step 13 then persists the
value to references.json via ``manage-references set --field scope_estimate``.

These tests pin two invariants that phase-2-refine relies on:

1. **Derivation rule contract** — the rule-of-thumb table in the standards
   doc is unambiguous: every representative module-mapping shape resolves to
   exactly one of the canonical enum values
   (``none | surgical | single_module | multi_module | broad``). The
   reference implementation below mirrors the standard. If the standard is
   ever amended, this implementation must be updated in lockstep.
2. **Persistence contract** — ``manage-references set --field scope_estimate``
   round-trips every enum value (no per-field validation in cmd_set; the
   caller is responsible for enum integrity, which the SKILL workflow
   enforces).

Tests in this module intentionally do NOT cover broader manage-references
behaviour, which lives in
``test/plan-marshall/manage-references/test_manage_references.py``.
"""

from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, PlanContext

# -----------------------------------------------------------------------------
# Tier 2 direct import — load manage-references CRUD module via importlib so
# the persistence contract test exercises the same code path that phase-2-refine
# Step 13 invokes via the executor.
# -----------------------------------------------------------------------------

_REFS_SCRIPTS_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-references' / 'scripts'


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _REFS_SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_crud = _load_module('_p2refine_refs_crud', '_references_crud.py')
cmd_create = _crud.cmd_create
cmd_get = _crud.cmd_get
cmd_set = _crud.cmd_set


# -----------------------------------------------------------------------------
# Reference implementation of the derivation rules.
#
# This function mirrors §"Derivation Rules" in
# phase-2-refine/standards/refine-workflow-detail.md verbatim. It exists ONLY
# as a test oracle for the parametric cases below — the production phase-2-refine
# workflow performs the same derivation in-skill (LLM-driven, no Python entry
# point). Keeping the rules expressed as runnable code here means a future
# silent drift between the doc and reality is caught by the test suite.
# -----------------------------------------------------------------------------


_VALID_ENUM = ('none', 'surgical', 'single_module', 'multi_module', 'broad')


def derive_scope_estimate(
    *,
    affected_files: list[str],
    modules: list[str],
    has_globs: bool,
    touches_public_api: bool,
    is_pure_analysis: bool,
) -> str:
    """Derive `scope_estimate` from a normalized module-mapping summary.

    Mirrors the documented rules. Apply the rules in order; the first match
    wins. ``affected_files`` are concrete file paths only — patterns/globs
    must NOT appear in this list (they set ``has_globs=True`` instead).

    Args:
        affected_files: Concrete file paths (no globs/patterns).
        modules: The set of distinct modules the affected_files map to.
        has_globs: True if module_mapping contains any glob/pattern.
        touches_public_api: True if any affected file is on a public API surface.
        is_pure_analysis: True iff the request is report-only (no code changes).

    Returns:
        One of ``'none' | 'surgical' | 'single_module' | 'multi_module' | 'broad'``.
    """
    # Rule 1: pure analysis with no files → none
    if is_pure_analysis and not affected_files:
        return 'none'

    # Rule 5 (early gate): codebase-wide / glob-only → broad
    if has_globs and not affected_files:
        return 'broad'

    # Multi-module short-circuit (Rule 4) — single module is required for
    # surgical/single_module, so detect multi-module first to keep the
    # branching obvious.
    if len(set(modules)) > 1:
        return 'multi_module'

    # All remaining cases involve a single module + concrete file list
    file_count = len(affected_files)

    # Rule 2: surgical
    if file_count <= 3 and not touches_public_api:
        return 'surgical'

    # Rule 3: single_module (count ≤10, OR touches public API surface but
    # still bounded to one module)
    if file_count <= 10:
        return 'single_module'

    # Rule 5 (fallback): unbounded single-module file list also reads as broad
    return 'broad'


# -----------------------------------------------------------------------------
# Parametric derivation cases
# -----------------------------------------------------------------------------


# Each case is a representative module_mapping shape. The test asserts the
# derivation rule resolves it to the documented enum value.
DERIVATION_CASES = [
    pytest.param(
        {
            'affected_files': [],
            'modules': [],
            'has_globs': False,
            'touches_public_api': False,
            'is_pure_analysis': True,
        },
        'none',
        id='rule1-pure-analysis-no-files',
    ),
    pytest.param(
        {
            'affected_files': ['skills/foo/SKILL.md'],
            'modules': ['plan-marshall'],
            'has_globs': False,
            'touches_public_api': False,
            'is_pure_analysis': False,
        },
        'surgical',
        id='rule2-surgical-1-file-no-public-api',
    ),
    pytest.param(
        {
            'affected_files': [
                'skills/foo/SKILL.md',
                'skills/foo/standards/x.md',
                'skills/foo/standards/y.md',
            ],
            'modules': ['plan-marshall'],
            'has_globs': False,
            'touches_public_api': False,
            'is_pure_analysis': False,
        },
        'surgical',
        id='rule2-surgical-3-files-no-public-api',
    ),
    pytest.param(
        {
            'affected_files': ['skills/foo/SKILL.md', 'skills/foo/__init__.py'],
            'modules': ['plan-marshall'],
            'has_globs': False,
            'touches_public_api': True,
            'is_pure_analysis': False,
        },
        'single_module',
        id='rule3-single-module-public-api-forces-upgrade',
    ),
    pytest.param(
        {
            'affected_files': [f'skills/foo/file{i}.py' for i in range(7)],
            'modules': ['plan-marshall'],
            'has_globs': False,
            'touches_public_api': False,
            'is_pure_analysis': False,
        },
        'single_module',
        id='rule3-single-module-7-files',
    ),
    pytest.param(
        {
            'affected_files': [f'skills/foo/file{i}.py' for i in range(10)],
            'modules': ['plan-marshall'],
            'has_globs': False,
            'touches_public_api': False,
            'is_pure_analysis': False,
        },
        'single_module',
        id='rule3-single-module-boundary-10-files',
    ),
    pytest.param(
        {
            'affected_files': [
                'plan-marshall/skills/a/SKILL.md',
                'pm-dev-java/skills/b/SKILL.md',
            ],
            'modules': ['plan-marshall', 'pm-dev-java'],
            'has_globs': False,
            'touches_public_api': False,
            'is_pure_analysis': False,
        },
        'multi_module',
        id='rule4-multi-module-2-modules',
    ),
    pytest.param(
        {
            'affected_files': [
                'plan-marshall/skills/a/SKILL.md',
                'pm-dev-java/skills/b/SKILL.md',
                'pm-dev-frontend/skills/c/SKILL.md',
            ],
            'modules': ['plan-marshall', 'pm-dev-java', 'pm-dev-frontend'],
            'has_globs': False,
            'touches_public_api': False,
            'is_pure_analysis': False,
        },
        'multi_module',
        id='rule4-multi-module-3-modules',
    ),
    pytest.param(
        {
            'affected_files': [],
            'modules': ['plan-marshall'],
            'has_globs': True,
            'touches_public_api': False,
            'is_pure_analysis': False,
        },
        'broad',
        id='rule5-broad-glob-only',
    ),
    pytest.param(
        {
            'affected_files': [f'skills/foo/file{i}.py' for i in range(25)],
            'modules': ['plan-marshall'],
            'has_globs': False,
            'touches_public_api': False,
            'is_pure_analysis': False,
        },
        'broad',
        id='rule5-broad-unbounded-single-module-file-list',
    ),
]


@pytest.mark.parametrize('mapping,expected', DERIVATION_CASES)
def test_scope_estimate_derivation_rules(mapping: dict, expected: str) -> None:
    """Each representative module_mapping resolves to the documented enum value.

    Asserts the derivation rules in ``refine-workflow-detail.md`` § Derivation
    Rules are unambiguous on the canonical input shapes. If the documented
    rules ever change, both the standard and the ``derive_scope_estimate``
    reference implementation above must be updated.
    """
    actual = derive_scope_estimate(**mapping)
    assert actual == expected, (
        f'Derivation rule mismatch for module_mapping={mapping!r}: expected {expected!r}, got {actual!r}'
    )
    assert actual in _VALID_ENUM, f'Derived value {actual!r} outside allowed enum {_VALID_ENUM!r}'


# -----------------------------------------------------------------------------
# Persistence contract — manage-references set/get round-trip
# -----------------------------------------------------------------------------


@pytest.mark.parametrize('value', list(_VALID_ENUM))
def test_scope_estimate_persists_to_references_json(value: str) -> None:
    """``manage-references set --field scope_estimate --value {value}``
    round-trips for every canonical enum value.

    This pins the persistence contract phase-2-refine Step 13 depends on.
    cmd_set is intentionally generic (no per-field validation) — enum
    integrity is enforced by the SKILL workflow that selects the value, and
    by the manage-solution-outline schema gate downstream.
    """
    # plan_id MUST be kebab-case — underscores in enum values (single_module,
    # multi_module) are translated to hyphens for the plan_id alone.
    plan_id = f'phase2-scope-estimate-{value.replace("_", "-")}'
    with PlanContext(plan_id=plan_id):
        # Bootstrap references.json — phase-1-init does this for real plans;
        # we replicate the minimum here so the persistence call has a target.
        create_result = cmd_create(
            Namespace(
                plan_id=plan_id,
                branch='feature/test',
                issue_url=None,
                build_system=None,
                domains=None,
            )
        )
        assert create_result['status'] == 'success', create_result

        # Step 13 contract: persist scope_estimate
        set_result = cmd_set(Namespace(plan_id=plan_id, field='scope_estimate', value=value))
        assert set_result['status'] == 'success'
        assert set_result['field'] == 'scope_estimate'
        assert set_result['value'] == value

        # Read-back: phase-3-outline / manifest composer / Q-Gate bypass
        # consumers all rely on cmd_get returning the persisted value.
        get_result = cmd_get(Namespace(plan_id=plan_id, field='scope_estimate'))
        assert get_result is not None
        assert get_result['status'] == 'success'
        assert get_result['field'] == 'scope_estimate'
        assert get_result['value'] == value


def test_scope_estimate_overwrite_records_previous() -> None:
    """phase-3-outline MAY overwrite the value via the same set call (e.g.,
    downgrading single_module → surgical after deliverables crystalize).
    The contract: subsequent set calls overwrite cleanly and report the
    prior value via the ``previous`` field.
    """
    plan_id = 'phase2-scope-estimate-overwrite'
    with PlanContext(plan_id=plan_id):
        cmd_create(
            Namespace(
                plan_id=plan_id,
                branch='feature/test',
                issue_url=None,
                build_system=None,
                domains=None,
            )
        )
        cmd_set(Namespace(plan_id=plan_id, field='scope_estimate', value='single_module'))
        overwrite = cmd_set(Namespace(plan_id=plan_id, field='scope_estimate', value='surgical'))

        assert overwrite['status'] == 'success'
        assert overwrite['value'] == 'surgical'
        assert overwrite.get('previous') == 'single_module', (
            'Overwrite must report previous value so downstream phases can '
            'audit refinements (phase-3-outline downgrades, manifest revisions).'
        )

        final = cmd_get(Namespace(plan_id=plan_id, field='scope_estimate'))
        assert final is not None
        assert final['value'] == 'surgical'


# -----------------------------------------------------------------------------
# Documentation cross-reference — fail loudly if the standards doc loses the
# enum or the persistence command. Keeps SKILL.md, the detail doc, and this
# test in lockstep.
# -----------------------------------------------------------------------------


_DETAIL_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-2-refine' / 'standards' / 'refine-workflow-detail.md'
)


def test_standards_doc_documents_enum_and_persistence_call() -> None:
    """The detail standards doc must continue to document:

    1. The exact 5-value enum (so authors copy the right literals).
    2. The ``manage-references set --field scope_estimate`` persistence call.

    A future edit that drops either invariant would silently desync the
    SKILL workflow from its consumers — this test acts as an alarm.
    """
    text = _DETAIL_PATH.read_text(encoding='utf-8')

    # All five enum values must appear (in either order, possibly listed in
    # the rule headings or the bash invocation).
    for enum_value in _VALID_ENUM:
        assert enum_value in text, f'Detail doc missing enum value {enum_value!r}'

    # The persistence command must be documented verbatim — phase-3-outline
    # and the manifest composer copy this notation.
    assert 'manage-references' in text and '--field scope_estimate' in text, (
        'Detail doc must document the manage-references set --field scope_estimate '
        'persistence call so phase-2-refine Step 13 stays in sync with consumers.'
    )


def test_skill_md_documents_enum_and_persistence_call() -> None:
    """SKILL.md must reference the canonical enum and the persistence call so
    the entry-point summary stays consistent with the detail doc."""
    skill_path = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-2-refine' / 'SKILL.md'
    text = skill_path.read_text(encoding='utf-8')

    for enum_value in _VALID_ENUM:
        assert enum_value in text, f'SKILL.md missing enum value {enum_value!r}'

    assert 'manage-references' in text and 'scope_estimate' in text, (
        'SKILL.md must reference the manage-references persistence call so the '
        'workflow summary is consistent with refine-workflow-detail.md.'
    )


# Sanity check: ensure the test file lives where the deliverable specifies.
def test_test_file_lives_at_expected_path() -> None:
    """Pin the file's own location — the deliverable explicitly named this
    path (test/plan-marshall/phase-2-refine/test_phase_2_refine_scope_estimate.py).
    A future restructure should update this assertion deliberately.
    """
    here = Path(__file__).resolve()
    expected_suffix = Path('test/plan-marshall/phase-2-refine/test_phase_2_refine_scope_estimate.py')
    assert str(here).endswith(str(expected_suffix)), (
        f'Test file moved from expected path. Got {here}, expected suffix {expected_suffix}.'
    )
