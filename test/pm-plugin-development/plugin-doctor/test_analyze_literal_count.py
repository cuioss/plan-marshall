# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``literal-count-drift`` rule analyzer.

The analyzer scans the ``extension-api`` ``SKILL.md`` "Extension Points" table
and detects drift between each row's manually-maintained "Implementations"
count token (the hand-maintained mirror) and the machine-derivable implementer
count enumerated from the bundle tree (the source of truth):

  * For the four AST hooks (``discover_modules`` / ``provides_triage`` /
    ``provides_outline_skill`` / ``provides_recipes``) the count is the number
    of bundles whose ``plan-marshall-plugin`` ``extension.py`` carries a *real
    override* (a non-default return).
  * For the ``*_provider.py`` provider hook the count is the number of
    ``*_provider.py`` files under any bundle's ``skills/*/scripts/`` tree.

It emits a warning-severity, non-fixable finding for each row whose stated count
differs from the actual count.

Structural discriminator: only a markdown TABLE row whose "Hook Method" cell
carries a recognised hook token AND whose "Implementations" cell is a bare
integer is checkable. Unrecognised hook tokens and incidental numbers elsewhere
are out of scope.

Test layers:
  * Clean fixture: every count matches the enumerated implementer set → no findings.
  * Negative: an AST-hook count is stale → one finding.
  * Negative: the provider count is stale → one finding.
  * Boundary: unrecognised hook token, non-table form, missing file, multiple
    stale rows, empty root.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_alc = _load_module('_analyze_literal_count', '_analyze_literal_count.py')

analyze_literal_count = _alc.analyze_literal_count
RULE_ID = _alc.RULE_ID


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake marketplace bundles tree carrying the governed
# extension-api SKILL.md table plus implementer sources (extension.py overrides
# and *_provider.py files).
# ---------------------------------------------------------------------------


def _write_extension_api_table(root: Path, rows: list[tuple[str, str]]) -> Path:
    """Write ``plan-marshall/skills/extension-api/SKILL.md`` with an Extension Points table.

    ``rows`` is a list of ``(hook_method_cell, implementations_cell)`` pairs;
    each becomes ``| <point> | <hook> | <contract> | <impl> |``.
    """
    skill_dir = root / 'plan-marshall' / 'skills' / 'extension-api'
    skill_dir.mkdir(parents=True, exist_ok=True)
    out = [
        '# Extension API',
        '',
        'Intro prose for the extension API.',
        '',
        '## Extension Points',
        '',
        '| Extension Point | Hook Method | Contract | Implementations |',
        '|-----------------|-------------|----------|-----------------|',
    ]
    for hook_cell, impl_cell in rows:
        out.append(f'| Some Point | {hook_cell} | [doc](standards/x.md) | {impl_cell} |')
    out += ['', '## Next Section', '', 'trailing prose.', '']
    skill_md = skill_dir / 'SKILL.md'
    skill_md.write_text('\n'.join(out), encoding='utf-8')
    return skill_md


def _extension_source(overrides: dict[str, str]) -> str:
    """Build an ``extension.py`` source defining the named hook overrides.

    ``overrides`` maps a hook method name to the literal return-value source. A
    method whose return source echoes the base default (``None`` / ``[]``) is a
    *default override* (not counted); a non-default literal is a *real override*.
    """
    lines = [
        'from plan_marshall.script_shared import ExtensionBase',
        '',
        '',
        'class Extension(ExtensionBase):',
    ]
    if not overrides:
        lines.append('    pass')
    else:
        for method, ret in overrides.items():
            lines.append(f'    def {method}(self):')
            lines.append(f'        return {ret}')
            lines.append('')
    return '\n'.join(lines) + '\n'


def _write_bundle_extension(root: Path, bundle: str, overrides: dict[str, str]) -> Path:
    """Write ``{bundle}/skills/plan-marshall-plugin/extension.py`` under ``root``."""
    skill_dir = root / bundle / 'skills' / 'plan-marshall-plugin'
    skill_dir.mkdir(parents=True, exist_ok=True)
    ext_path = skill_dir / 'extension.py'
    ext_path.write_text(_extension_source(overrides), encoding='utf-8')
    return ext_path


def _write_provider(root: Path, bundle: str, skill: str, name: str) -> Path:
    """Write ``{bundle}/skills/{skill}/scripts/{name}_provider.py`` under ``root``."""
    scripts_dir = root / bundle / 'skills' / skill / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    provider = scripts_dir / f'{name}_provider.py'
    provider.write_text('# provider stub\n', encoding='utf-8')
    return provider


# ===========================================================================
# Clean fixture — every count matches the enumerated implementer set.
# ===========================================================================


class TestCleanCounts:
    """A table whose counts match the bundle-tree enumeration produces no findings."""

    def test_matching_ast_and_provider_counts(self, tmp_path: Path) -> None:
        # Two bundles really override provides_triage; one provider file.
        _write_bundle_extension(tmp_path, 'bundle-a', {'provides_triage': '"t"'})
        _write_bundle_extension(tmp_path, 'bundle-b', {'provides_triage': '"t"'})
        _write_provider(tmp_path, 'plan-marshall', 'workflow-integration-git', 'git')
        _write_extension_api_table(
            tmp_path,
            [
                ('`provides_triage()`', '2'),
                ('`*_provider.py`', '1'),
            ],
        )

        findings = analyze_literal_count(tmp_path)

        assert findings == []

    def test_missing_governed_file_returns_no_findings(self, tmp_path: Path) -> None:
        # No extension-api SKILL.md exists at all.
        findings = analyze_literal_count(tmp_path)

        assert findings == []


# ===========================================================================
# Negative — a stale AST-hook count → one finding.
# ===========================================================================


class TestStaleAstHookCount:
    """A stated AST-hook count that disagrees with the override tally is flagged."""

    def test_stale_count_is_flagged(self, tmp_path: Path) -> None:
        # Only one bundle really overrides provides_recipes, but the table says 4.
        _write_bundle_extension(tmp_path, 'bundle-a', {'provides_recipes': '["r"]'})
        _write_bundle_extension(tmp_path, 'bundle-b', {'provides_recipes': '[]'})  # default
        skill_md = _write_extension_api_table(tmp_path, [('`provides_recipes()`', '4')])

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['severity'] == 'warning'
        assert finding['fixable'] is False
        assert finding['file'] == str(skill_md)
        details = finding['details']
        assert details['hook'] == 'provides_recipes'
        assert details['stated'] == 4
        assert details['actual'] == 1
        # The finding points at the offending row, not line 1.
        assert finding['line'] > 1

    def test_zero_overrides_with_nonzero_count_is_flagged(self, tmp_path: Path) -> None:
        # No bundle overrides discover_modules; table claims 2.
        _write_bundle_extension(tmp_path, 'bundle-a', {})  # no overrides
        skill_md = _write_extension_api_table(tmp_path, [('`discover_modules()`', '2')])

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1
        assert findings[0]['details'] == {'hook': 'discover_modules', 'stated': 2, 'actual': 0}
        assert findings[0]['file'] == str(skill_md)


# ===========================================================================
# Negative — a stale provider count → one finding.
# ===========================================================================


class TestStaleProviderCount:
    """A stated *_provider.py count that disagrees with the file tally is flagged."""

    def test_stale_provider_count_is_flagged(self, tmp_path: Path) -> None:
        # Two provider files exist, but the table says 4.
        _write_provider(tmp_path, 'plan-marshall', 'workflow-integration-git', 'git')
        _write_provider(tmp_path, 'plan-marshall', 'workflow-integration-github', 'github')
        _write_extension_api_table(tmp_path, [('`*_provider.py`', '4')])

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1
        details = findings[0]['details']
        assert details['hook'] == '*_provider.py'
        assert details['stated'] == 4
        assert details['actual'] == 2


# ===========================================================================
# Boundary — out-of-scope rows stay silent; multiple stale rows co-occur.
# ===========================================================================


class TestBoundaryConditions:
    """Unrecognised hooks and non-table forms stay silent; stale rows co-occur."""

    def test_unrecognised_hook_token_is_ignored(self, tmp_path: Path) -> None:
        # A row whose Hook Method cell names no recognised hook is out of scope,
        # so its count (however wrong) is never checked.
        _write_extension_api_table(tmp_path, [('`some_other_hook()`', '99')])

        findings = analyze_literal_count(tmp_path)

        assert findings == []

    def test_prose_count_outside_table_is_ignored(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'extension-api'
        skill_dir.mkdir(parents=True, exist_ok=True)
        # An "Extension Points" section with NO table — only prose mentioning a
        # count. Nothing is checkable.
        (skill_dir / 'SKILL.md').write_text(
            '# Extension API\n\n## Extension Points\n\n'
            'There are 7 implementations of provides_triage().\n\n'
            '## Next\n',
            encoding='utf-8',
        )

        findings = analyze_literal_count(tmp_path)

        assert findings == []

    def test_non_integer_implementations_cell_is_ignored(self, tmp_path: Path) -> None:
        _write_bundle_extension(tmp_path, 'bundle-a', {'provides_triage': '"t"'})
        # The Implementations cell is prose, not a bare integer → not checkable.
        _write_extension_api_table(tmp_path, [('`provides_triage()`', 'several')])

        findings = analyze_literal_count(tmp_path)

        assert findings == []

    def test_multiple_stale_rows_co_occur(self, tmp_path: Path) -> None:
        # provides_triage: actual 1, stated 3 (stale). *_provider.py: actual 1,
        # stated 2 (stale). provides_outline_skill: actual 0, stated 0 (clean).
        _write_bundle_extension(tmp_path, 'bundle-a', {'provides_triage': '"t"'})
        _write_provider(tmp_path, 'plan-marshall', 'workflow-integration-git', 'git')
        _write_extension_api_table(
            tmp_path,
            [
                ('`provides_triage()`', '3'),
                ('`*_provider.py`', '2'),
                ('`provides_outline_skill()`', '0'),
            ],
        )

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 2
        by_hook = {f['details']['hook']: f['details'] for f in findings}
        assert set(by_hook) == {'provides_triage', '*_provider.py'}
        assert by_hook['provides_triage']['stated'] == 3
        assert by_hook['provides_triage']['actual'] == 1
        assert by_hook['*_provider.py']['stated'] == 2
        assert by_hook['*_provider.py']['actual'] == 1
