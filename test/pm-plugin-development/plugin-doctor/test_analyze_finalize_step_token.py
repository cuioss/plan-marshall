# ruff: noqa: I001, E402
"""Tests for the ``finalize-step-token-mismatch`` rule analyzer.

The analyzer (`scan_finalize_step_token`) is a pure, regex-driven static
scanner that detects mismatches between the ``mark-step-done --step <token>``
argument a finalize-step skill documents under ``--phase 6-finalize`` and the
skill's canonical manifest step_id. It walks two roots:

1. **Bundle finalize-step skills** —
   ``marketplace_root/{bundle}/skills/{skill}/SKILL.md`` whose
   ``{bundle}:{skill}`` reference is a member of the authoritative
   ``OPTIONAL_BUNDLE_FINALIZE_STEPS`` registry in
   ``manage-config/_config_defaults.py``. The expected step_id is that
   registry reference (i.e. ``{bundle}:{skill}``).

2. **Project-local finalize-step skills** —
   ``<repo>/.claude/skills/finalize-step-*/SKILL.md`` discovered by glob,
   resolved as ``marketplace_root.parent.parent / '.claude' / 'skills'``. The
   expected step_id is ``project:{name}`` where ``{name}`` is the skill
   directory basename.

A finding is emitted when the documented token differs from the expected
step_id. Skills emitting no ``mark-step-done --phase 6-finalize`` invocation
are silently skipped (no false positive).

Test layers:
  * (a) Bundle violating — a documented token that drifts from the registry
        step_id is flagged.
  * (b) Bundle clean — a documented token equal to the registry step_id is
        not flagged.
  * (c) Skip-context — a SKILL.md with no ``mark-step-done --phase 6-finalize``
        invocation produces no finding.
  * (d) ``--flag=value`` form — the equals form of both ``--phase`` and
        ``--step`` parses identically to the space form.
  * (e) Project-local — ``.claude/skills/finalize-step-*/SKILL.md`` is scanned
        with the ``project:{name}`` expected step_id (violating + clean).
  * (f) Finding shape — the finding carries the documented contract fields.
  * (g) Real-marketplace-zero — the real bundles tree produces zero findings
        (the PR #629 regression anchor).
"""

from pathlib import Path

import pytest
from conftest import MARKETPLACE_ROOT, load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_afst = _load_module(
    '_analyze_finalize_step_token',
    '_analyze_finalize_step_token.py',
)

scan_finalize_step_token = _afst.scan_finalize_step_token
RULE_ID = _afst.RULE_ID
RULE_NAME = _afst.RULE_NAME
FINDING_TYPE = _afst.FINDING_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# A bundle reference that the synthetic registry below treats as in-scope.
# Mirrors the real ``OPTIONAL_BUNDLE_FINALIZE_STEPS`` shape (``bundle:skill``).
_BUNDLE = 'plan-marshall'
_SKILL = 'plan-retrospective'
_BUNDLE_REF = f'{_BUNDLE}:{_SKILL}'


def _bundle_marketplace(tmp_path: Path) -> Path:
    """Build a synthetic marketplace root with the manage-config registry.

    The scanner imports ``OPTIONAL_BUNDLE_FINALIZE_STEPS`` from
    ``{marketplace_root}/plan-marshall/skills/manage-config/scripts/
    _config_defaults.py``. To make a synthetic ``tmp_path`` marketplace
    in-scope for a given ``{bundle}:{skill}``, that registry module must
    exist and list the reference.

    Returns the marketplace bundles root to pass to the scanner.
    """
    bundles_root = tmp_path / 'marketplace' / 'bundles'
    config_scripts = (
        bundles_root
        / 'plan-marshall'
        / 'skills'
        / 'manage-config'
        / 'scripts'
    )
    config_scripts.mkdir(parents=True)
    (config_scripts / '_config_defaults.py').write_text(
        f'OPTIONAL_BUNDLE_FINALIZE_STEPS = [{_BUNDLE_REF!r}]\n',
        encoding='utf-8',
    )
    return bundles_root


def _write_bundle_skill(
    bundles_root: Path, content: str, bundle: str = _BUNDLE, skill: str = _SKILL
) -> Path:
    """Create ``{bundles_root}/{bundle}/skills/{skill}/SKILL.md``."""
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return md


def _write_project_skill(
    tmp_path: Path, content: str, name: str = 'finalize-step-deploy-target'
) -> tuple[Path, Path]:
    """Create a project-local ``.claude/skills/{name}/SKILL.md`` + bundles root.

    The scanner resolves ``.claude/skills`` as
    ``marketplace_root.parent.parent / '.claude' / 'skills'``. Placing the
    bundles root at ``tmp_path/marketplace/bundles`` makes two levels up land
    on ``tmp_path``, where ``.claude/skills`` is created.

    Returns ``(bundles_root, skill_md_path)``.
    """
    bundles_root = tmp_path / 'marketplace' / 'bundles'
    bundles_root.mkdir(parents=True, exist_ok=True)
    skill_dir = tmp_path / '.claude' / 'skills' / name
    skill_dir.mkdir(parents=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return bundles_root, md


def _mark_step_done_block(token: str, phase: str = '6-finalize') -> str:
    """A ``mark-step-done`` fenced command block (space form)."""
    return (
        '```bash\n'
        'python3 .plan/execute-script.py '
        'plan-marshall:manage-status:manage-status mark-step-done \\\n'
        f'  --plan-id PLAN_ID --phase {phase} --step {token}\n'
        '```\n'
    )


# ===========================================================================
# (a) Bundle violating case — documented token drifts from registry step_id
# ===========================================================================


class TestBundleViolating:
    """A documented ``--step`` token that diverges from the registry step_id
    is flagged."""

    def test_drifted_token_triggers_finding(self, tmp_path: Path) -> None:
        bundles_root = _bundle_marketplace(tmp_path)
        # Documented token uses a bare-skill name instead of the canonical
        # ``{bundle}:{skill}`` reference — the classic PR #629 drift.
        content = (
            '# Plan Retrospective\n\n'
            'Finalize tail:\n\n'
            + _mark_step_done_block(_SKILL)
        )
        md = _write_bundle_skill(bundles_root, content)

        findings = scan_finalize_step_token(bundles_root)

        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['file'] == str(md)
        assert f['details']['documented_token'] == _SKILL
        assert f['details']['expected_step_id'] == _BUNDLE_REF

    def test_project_prefixed_token_on_bundle_skill_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """A ``project:`` token on a bundle skill drifts from its registry id."""
        bundles_root = _bundle_marketplace(tmp_path)
        content = '# Skill\n\n' + _mark_step_done_block(f'project:{_SKILL}')
        _write_bundle_skill(bundles_root, content)

        findings = scan_finalize_step_token(bundles_root)

        assert len(findings) == 1
        assert findings[0]['details']['expected_step_id'] == _BUNDLE_REF


# ===========================================================================
# (b) Bundle clean case — documented token matches registry step_id
# ===========================================================================


class TestBundleClean:
    """A documented token equal to the registry step_id is not flagged."""

    def test_matching_token_produces_no_finding(self, tmp_path: Path) -> None:
        bundles_root = _bundle_marketplace(tmp_path)
        content = '# Skill\n\n' + _mark_step_done_block(_BUNDLE_REF)
        _write_bundle_skill(bundles_root, content)

        findings = scan_finalize_step_token(bundles_root)

        assert findings == []

    def test_out_of_registry_bundle_skill_is_not_scanned(
        self, tmp_path: Path
    ) -> None:
        """A finalize-step-looking skill NOT in the registry is out of scope."""
        bundles_root = _bundle_marketplace(tmp_path)
        # Drift in a skill that is NOT a registry member — must not be flagged.
        content = '# Other\n\n' + _mark_step_done_block('wrong-token')
        _write_bundle_skill(
            bundles_root, content, bundle='pm-dev-java', skill='some-step'
        )

        findings = scan_finalize_step_token(bundles_root)

        assert findings == []


# ===========================================================================
# (c) Skip-context case — no mark-step-done --phase 6-finalize invocation
# ===========================================================================


class TestSkipContext:
    """Skills with no in-scope ``mark-step-done`` invocation are skipped."""

    def test_no_mark_step_done_block_is_skipped(self, tmp_path: Path) -> None:
        bundles_root = _bundle_marketplace(tmp_path)
        content = (
            '# Skill\n\nThis skill documents no finalize handshake at all.\n'
        )
        _write_bundle_skill(bundles_root, content)

        findings = scan_finalize_step_token(bundles_root)

        assert findings == []

    def test_mark_step_done_wrong_phase_is_skipped(
        self, tmp_path: Path
    ) -> None:
        """A ``mark-step-done`` under a non-6-finalize phase is not in scope."""
        bundles_root = _bundle_marketplace(tmp_path)
        # Token drifts, but the phase is not 6-finalize — silently skipped.
        content = '# Skill\n\n' + _mark_step_done_block(
            'drifted', phase='5-execute'
        )
        _write_bundle_skill(bundles_root, content)

        findings = scan_finalize_step_token(bundles_root)

        assert findings == []


# ===========================================================================
# (d) --flag=value form — equals form parses identically to space form
# ===========================================================================


class TestEqualsForm:
    """Both ``--phase=6-finalize`` and ``--step=token`` (equals form) parse."""

    def test_equals_form_violating_token_is_flagged(
        self, tmp_path: Path
    ) -> None:
        bundles_root = _bundle_marketplace(tmp_path)
        content = (
            '# Skill\n\n'
            '```bash\n'
            'python3 .plan/execute-script.py '
            'plan-marshall:manage-status:manage-status mark-step-done \\\n'
            f'  --plan-id PLAN_ID --phase=6-finalize --step={_SKILL}\n'
            '```\n'
        )
        _write_bundle_skill(bundles_root, content)

        findings = scan_finalize_step_token(bundles_root)

        assert len(findings) == 1
        assert findings[0]['details']['documented_token'] == _SKILL

    def test_equals_form_matching_token_is_clean(self, tmp_path: Path) -> None:
        bundles_root = _bundle_marketplace(tmp_path)
        content = (
            '# Skill\n\n'
            '```bash\n'
            'python3 .plan/execute-script.py '
            'plan-marshall:manage-status:manage-status mark-step-done \\\n'
            f'  --plan-id PLAN_ID --phase=6-finalize --step={_BUNDLE_REF}\n'
            '```\n'
        )
        _write_bundle_skill(bundles_root, content)

        findings = scan_finalize_step_token(bundles_root)

        assert findings == []


# ===========================================================================
# (e) Project-local case — .claude/skills/finalize-step-*/SKILL.md
# ===========================================================================


class TestProjectLocal:
    """The project-local ``.claude/skills/finalize-step-*`` tree is scanned
    with the ``project:{name}`` expected step_id."""

    def test_project_local_drifted_token_is_flagged(
        self, tmp_path: Path
    ) -> None:
        name = 'finalize-step-deploy-target'
        # Documented token drops the ``project:`` prefix — a drift.
        content = '# Deploy Target\n\n' + _mark_step_done_block(name)
        bundles_root, md = _write_project_skill(tmp_path, content, name=name)

        findings = scan_finalize_step_token(bundles_root)

        assert len(findings) == 1
        f = findings[0]
        assert f['file'] == str(md)
        assert f['details']['documented_token'] == name
        assert f['details']['expected_step_id'] == f'project:{name}'

    def test_project_local_matching_token_is_clean(
        self, tmp_path: Path
    ) -> None:
        name = 'finalize-step-deploy-target'
        content = '# Deploy Target\n\n' + _mark_step_done_block(
            f'project:{name}'
        )
        bundles_root, _ = _write_project_skill(tmp_path, content, name=name)

        findings = scan_finalize_step_token(bundles_root)

        assert findings == []

    def test_project_local_without_handshake_is_skipped(
        self, tmp_path: Path
    ) -> None:
        name = 'finalize-step-deploy-target'
        content = '# Deploy Target\n\nNo finalize handshake here.\n'
        bundles_root, _ = _write_project_skill(tmp_path, content, name=name)

        findings = scan_finalize_step_token(bundles_root)

        assert findings == []

    def test_bundle_and_project_findings_combine(self, tmp_path: Path) -> None:
        """Findings from the bundle tree and ``.claude/skills`` combine."""
        bundles_root = _bundle_marketplace(tmp_path)
        # Bundle-tree drift.
        _write_bundle_skill(
            bundles_root, '# Skill\n\n' + _mark_step_done_block(_SKILL)
        )
        # Project-local drift (same tmp_path → same .claude/skills resolution).
        proj_name = 'finalize-step-plugin-doctor'
        proj_dir = tmp_path / '.claude' / 'skills' / proj_name
        proj_dir.mkdir(parents=True)
        (proj_dir / 'SKILL.md').write_text(
            '# Plugin Doctor\n\n' + _mark_step_done_block(proj_name),
            encoding='utf-8',
        )

        findings = scan_finalize_step_token(bundles_root)

        assert len(findings) == 2
        files = {f['file'] for f in findings}
        assert any(f.endswith(f'{_SKILL}/SKILL.md') for f in files)
        assert any(f.endswith(f'{proj_name}/SKILL.md') for f in files)


# ===========================================================================
# (f) Finding shape
# ===========================================================================


class TestFindingShape:
    """The finding dict carries the documented contract fields."""

    def test_finding_shape(self, tmp_path: Path) -> None:
        bundles_root = _bundle_marketplace(tmp_path)
        content = '# Skill\n\n' + _mark_step_done_block(_SKILL)
        md = _write_bundle_skill(bundles_root, content)

        findings = scan_finalize_step_token(bundles_root)

        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == FINDING_TYPE
        assert f['rule'] == RULE_NAME
        assert f['file'] == str(md)
        assert isinstance(f['line'], int) and f['line'] >= 1
        assert f['severity'] == 'error'
        assert f['fixable'] is False
        assert isinstance(f['message'], str) and f['message']
        assert set(f['details']) == {'documented_token', 'expected_step_id'}

    def test_line_points_at_the_step_token(self, tmp_path: Path) -> None:
        """The reported line is the 1-based line of the ``--step`` token."""
        bundles_root = _bundle_marketplace(tmp_path)
        # The --step token lands on line 6 (1: heading, 2: blank, 3: prose,
        # 4: blank, 5: fence-open, 6: mark-step-done command line).
        content = (
            '# Skill\n'
            '\n'
            'Finalize tail:\n'
            '\n'
            '```bash\n'
            'python3 x mark-step-done --phase 6-finalize --step '
            f'{_SKILL}\n'
            '```\n'
        )
        _write_bundle_skill(bundles_root, content)

        findings = scan_finalize_step_token(bundles_root)

        assert len(findings) == 1
        assert findings[0]['line'] == 6


# ===========================================================================
# (g) Real-marketplace-zero — the PR #629 regression anchor
# ===========================================================================


def _marketplace_available() -> bool:
    return MARKETPLACE_ROOT.is_dir() and any(MARKETPLACE_ROOT.iterdir())


def test_real_marketplace_tree_produces_zero_findings() -> None:
    """The real bundles tree has zero finalize-step token drifts.

    This is the PR #629 regression anchor: the documented
    ``mark-step-done --step`` token in every in-scope finalize-step skill must
    equal its canonical manifest step_id. A non-empty result means a real
    skill drifted and the ``phase_steps_complete`` handshake would loop
    forever.
    """
    if not _marketplace_available():
        pytest.skip('Real marketplace not available')

    findings = scan_finalize_step_token(MARKETPLACE_ROOT)

    assert findings == [], (
        f'Found {len(findings)} finalize-step token mismatch(es) in the real '
        f'marketplace tree: '
        f'{[(f["file"], f["details"]) for f in findings]}. '
        f'Each documented mark-step-done --step token must equal its '
        f'canonical manifest step_id.'
    )
