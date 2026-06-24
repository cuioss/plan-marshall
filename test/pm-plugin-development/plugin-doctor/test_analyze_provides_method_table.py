# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``provides-method-table-drift`` rule analyzer.

The analyzer scans every ``*/skills/plan-marshall-plugin/SKILL.md`` paired with
its sibling ``extension.py`` and detects drift between the extension's
``provides_*()`` overrides (the machine-derivable source of truth) and the
``provides_*()`` function-name column in the SKILL.md "Extension API" markdown
table (the hand-maintained mirror).

It emits a warning-severity, non-fixable finding for two drift directions:

  * ``override_missing_from_table`` — a real override absent from the table.
  * ``phantom_table_row`` — a table row naming a ``provides_*()`` method that is
    NOT a real override (undefined on the class, or returns the base default).

Structural discriminator: only markdown TABLE rows in the Extension API section
are mirror rows. A generic bullet-list capability description is out of scope.

Test layers:
  * Clean fixture: table mirrors the overrides exactly → no findings.
  * Negative: real override missing from the table → one finding.
  * Negative: phantom table row (default / undefined method) → one finding.
  * Boundary: bullet-list (non-table) form, no sibling extension.py, no
    Extension API section, default-return methods, multi-bundle, empty root.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_apmt = _load_module('_analyze_provides_method_table', '_analyze_provides_method_table.py')

analyze_provides_method_table = _apmt.analyze_provides_method_table
RULE_ID = _apmt.RULE_ID


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake marketplace bundles tree carrying a
# plan-marshall-plugin SKILL.md and its sibling extension.py.
# ---------------------------------------------------------------------------


def _plugin_skill_dir(bundle_dir: Path) -> Path:
    """Return (creating) ``{bundle}/skills/plan-marshall-plugin``."""
    skill_dir = bundle_dir / 'skills' / 'plan-marshall-plugin'
    skill_dir.mkdir(parents=True, exist_ok=True)
    return skill_dir


def _write_extension(bundle_dir: Path, body: str) -> Path:
    """Write ``{bundle}/skills/plan-marshall-plugin/extension.py`` and return it."""
    skill_dir = _plugin_skill_dir(bundle_dir)
    ext_path = skill_dir / 'extension.py'
    ext_path.write_text(body, encoding='utf-8')
    return ext_path


def _write_skill_md(bundle_dir: Path, body: str) -> Path:
    """Write ``{bundle}/skills/plan-marshall-plugin/SKILL.md`` and return it."""
    skill_dir = _plugin_skill_dir(bundle_dir)
    skill_md = skill_dir / 'SKILL.md'
    skill_md.write_text(body, encoding='utf-8')
    return skill_md


def _extension_source(overrides: dict[str, str]) -> str:
    """Build an ``extension.py`` source defining the named hook overrides.

    ``overrides`` maps a hook method name to the literal return-value source
    (e.g. ``'"some-triage-skill"'`` or ``'[]'``). A method whose return source
    echoes the base default (``None`` / ``[]``) is a *default override*; a
    non-default literal is a *real override*. Methods absent from the dict are
    simply not defined on the subclass.
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


def _skill_md_table(rows: list[str], heading: str = '## Extension API') -> str:
    """Build a SKILL.md whose Extension API section is a markdown table.

    ``rows`` are the table-cell first columns (e.g. ``'`provides_triage()`'``);
    each becomes a ``| <cell> | description |`` row.
    """
    out = [
        '# plan-marshall-plugin',
        '',
        'Intro prose for the plugin manifest.',
        '',
        heading,
        '',
        '| Hook | Description |',
        '|------|-------------|',
    ]
    for row in rows:
        out.append(f'| {row} | hook description |')
    out += ['', '## Next Section', '', 'unrelated trailing prose.', '']
    return '\n'.join(out)


def _skill_md_bullets(bullets: list[str]) -> str:
    """Build a SKILL.md whose Extension API section is a bullet list (non-table)."""
    out = [
        '# plan-marshall-plugin',
        '',
        '## Extension API',
        '',
    ]
    for bullet in bullets:
        out.append(f'- {bullet}')
    out += ['', '## Next Section', '', 'trailing prose.', '']
    return '\n'.join(out)


# ===========================================================================
# Clean fixture — table mirrors the extension overrides exactly → no findings.
# ===========================================================================


class TestCleanMirror:
    """A table that names exactly the real overrides produces no findings."""

    def test_table_matches_overrides_exactly(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _write_extension(
            bundle,
            _extension_source(
                {
                    'provides_triage': '"my-triage-skill"',
                    'provides_recipes': '["recipe-a"]',
                }
            ),
        )
        _write_skill_md(
            bundle,
            _skill_md_table(['`provides_triage()`', '`provides_recipes()`']),
        )

        findings = analyze_provides_method_table(tmp_path)

        assert findings == []

    def test_empty_root_returns_no_findings(self, tmp_path: Path) -> None:
        findings = analyze_provides_method_table(tmp_path)

        assert findings == []


# ===========================================================================
# Negative — a real override absent from the table → one finding.
# ===========================================================================


class TestOverrideMissingFromTable:
    """A real override not listed in the table is flagged."""

    def test_real_override_missing_is_flagged(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        ext_path = _write_extension(
            bundle,
            _extension_source(
                {
                    'provides_triage': '"my-triage-skill"',
                    'provides_recipes': '["recipe-a"]',
                }
            ),
        )
        # Table lists only provides_triage; provides_recipes override is missing.
        skill_md = _write_skill_md(bundle, _skill_md_table(['`provides_triage()`']))

        findings = analyze_provides_method_table(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['severity'] == 'warning'
        assert finding['fixable'] is False
        assert finding['file'] == str(skill_md)
        details = finding['details']
        assert details['bundle'] == 'my-bundle'
        assert details['method'] == 'provides_recipes'
        assert details['reason'] == 'override_missing_from_table'
        assert details['extension_path'] == str(ext_path)


# ===========================================================================
# Negative — a phantom table row (default / undefined method) → one finding.
# ===========================================================================


class TestPhantomTableRow:
    """A table row naming a non-override method is flagged."""

    def test_table_row_for_undefined_method_is_flagged(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        ext_path = _write_extension(bundle, _extension_source({}))  # no overrides
        skill_md = _write_skill_md(bundle, _skill_md_table(['`provides_triage()`']))

        findings = analyze_provides_method_table(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['severity'] == 'warning'
        assert finding['fixable'] is False
        assert finding['file'] == str(skill_md)
        details = finding['details']
        assert details['bundle'] == 'my-bundle'
        assert details['method'] == 'provides_triage'
        assert details['reason'] == 'phantom_table_row'
        assert details['extension_path'] == str(ext_path)
        # The phantom-row finding points at the offending table row, not line 1.
        assert finding['line'] > 1

    def test_table_row_for_default_return_method_is_flagged(self, tmp_path: Path) -> None:
        """A method whose body returns only the base default is not a real override."""
        bundle = tmp_path / 'my-bundle'
        _write_extension(
            bundle,
            _extension_source(
                {
                    'provides_triage': 'None',  # default-return override
                    'provides_recipes': '[]',  # default-return override
                }
            ),
        )
        _write_skill_md(
            bundle,
            _skill_md_table(['`provides_triage()`', '`provides_recipes()`']),
        )

        findings = analyze_provides_method_table(tmp_path)

        assert len(findings) == 2
        reasons = {f['details']['reason'] for f in findings}
        assert reasons == {'phantom_table_row'}
        methods = {f['details']['method'] for f in findings}
        assert methods == {'provides_triage', 'provides_recipes'}


# ===========================================================================
# Boundary — non-table form, missing siblings, multi-bundle, both directions.
# ===========================================================================


class TestBoundaryConditions:
    """Out-of-scope shapes stay silent; both drift directions co-occur."""

    def test_bullet_list_form_is_not_a_mirror(self, tmp_path: Path) -> None:
        """A bullet-list Extension API section is generic prose, never a mirror."""
        bundle = tmp_path / 'my-bundle'
        # Overrides exist but are NOT mirrored anywhere; the bullets describe the
        # hook contract abstractly, so no drift can be detected.
        _write_extension(bundle, _extension_source({'provides_triage': '"t"'}))
        _write_skill_md(
            bundle,
            _skill_md_bullets(
                [
                    '`provides_triage()` - Triage skill reference or None',
                    '`provides_recipes()` - Recipe list or empty',
                ]
            ),
        )

        findings = analyze_provides_method_table(tmp_path)

        assert findings == []

    def test_no_sibling_extension_is_skipped(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        # SKILL.md with a table but no extension.py beside it.
        _write_skill_md(bundle, _skill_md_table(['`provides_triage()`']))

        findings = analyze_provides_method_table(tmp_path)

        assert findings == []

    def test_no_extension_api_section_is_skipped(self, tmp_path: Path) -> None:
        bundle = tmp_path / 'my-bundle'
        _write_extension(bundle, _extension_source({'provides_triage': '"t"'}))
        _write_skill_md(
            bundle,
            '# plan-marshall-plugin\n\nIntro prose, no Extension API section.\n',
        )

        findings = analyze_provides_method_table(tmp_path)

        assert findings == []

    def test_both_directions_co_occur(self, tmp_path: Path) -> None:
        """A missing real override and a phantom row are flagged independently."""
        bundle = tmp_path / 'my-bundle'
        # Real override: provides_recipes. Table lists provides_triage (phantom)
        # and omits provides_recipes (missing).
        _write_extension(bundle, _extension_source({'provides_recipes': '["r"]'}))
        _write_skill_md(bundle, _skill_md_table(['`provides_triage()`']))

        findings = analyze_provides_method_table(tmp_path)

        assert len(findings) == 2
        by_reason = {f['details']['reason']: f for f in findings}
        assert set(by_reason) == {'override_missing_from_table', 'phantom_table_row'}
        assert by_reason['override_missing_from_table']['details']['method'] == 'provides_recipes'
        assert by_reason['phantom_table_row']['details']['method'] == 'provides_triage'

    def test_findings_span_multiple_bundles(self, tmp_path: Path) -> None:
        bundle_a = tmp_path / 'bundle-a'
        bundle_b = tmp_path / 'bundle-b'
        # bundle-a: phantom row. bundle-b: a real override missing from a table
        # that still carries another mirror row (so the section is a mirror).
        _write_extension(bundle_a, _extension_source({}))
        _write_skill_md(bundle_a, _skill_md_table(['`provides_triage()`']))
        _write_extension(
            bundle_b,
            _extension_source({'provides_triage': '"t"', 'provides_recipes': '["r"]'}),
        )
        # Table lists provides_triage but omits the provides_recipes override.
        _write_skill_md(bundle_b, _skill_md_table(['`provides_triage()`']))

        findings = analyze_provides_method_table(tmp_path)

        assert len(findings) == 2
        bundles = {f['details']['bundle'] for f in findings}
        assert bundles == {'bundle-a', 'bundle-b'}
