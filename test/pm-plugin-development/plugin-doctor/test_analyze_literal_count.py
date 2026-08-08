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

The analyzer's second governed surface is the ``persona-security-expert``
``SKILL.md`` standards index, which restates the same set three times — a prose
count, the "Available Standards" table, and the "Standards Reference" table —
while the set itself lives on disk under that skill's ``standards/`` directory.
Every claim is compared against the DERIVED directory listing, and every finding
publishes the derived ``population_size`` so a clean result cannot be read as a
pass over an unread population.

Test layers:
  * Clean fixture: every count matches the enumerated implementer set → no findings.
  * Negative: an AST-hook count is stale → one finding.
  * Negative: the provider count is stale → one finding.
  * Boundary: unrecognised hook token, non-table form, missing file, multiple
    stale rows, empty root.
  * Standards index: agreeing index is clean; stale prose count, a table missing
    a document, and a table listing an absent document are each flagged. Every
    fixture carries a decoy sentence whose anchor phrase is preceded by an
    ordinary word, guarding the count-token discriminator in every case.
  * Standards index fail-closed: empty population, missing index section, an
    unanchored prose count, a prose link sitting outside the table, and a
    governed file that exists but cannot be read each emit a finding rather
    than passing silently.
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


# ---------------------------------------------------------------------------
# Helpers — the second governed surface: the persona-security-expert standards
# index, whose population is the skill's own ``standards/`` directory listing.
# ---------------------------------------------------------------------------

_PSE_PARTS = ('plan-marshall', 'skills', 'persona-security-expert')


def _write_persona_security_expert(
    root: Path,
    standards: list[str],
    *,
    prose: str | None = 'three',
    load_listed: list[str] | None = None,
    reference_listed: list[str] | None = None,
    include_load_section: bool = True,
    include_reference_section: bool = True,
    load_section_prose: str | None = None,
) -> Path:
    """Write a persona-security-expert skill whose index may agree or disagree with ``standards``.

    ``standards`` is the on-disk population (the source of truth). ``prose`` /
    ``load_listed`` / ``reference_listed`` are the three hand-maintained mirrors;
    each defaults to agreeing with the population so a test states only the
    mirror it is drifting.

    ``load_section_prose``, when given, is appended INSIDE the "Available
    Standards" section but AFTER the table — ordinary prose that is part of the
    section body yet is not a table row.
    """
    skill_dir = root.joinpath(*_PSE_PARTS)
    standards_dir = skill_dir / 'standards'
    standards_dir.mkdir(parents=True, exist_ok=True)
    for name in standards:
        (standards_dir / name).write_text('# standard\n', encoding='utf-8')
    load_rows = standards if load_listed is None else load_listed
    reference_rows = standards if reference_listed is None else reference_listed

    out = ['# Persona: Security Expert', '']
    if prose is None:
        out += ['**REFERENCE MODE**: the sub-documents hold the content.', '']
    else:
        out += [
            f'**REFERENCE MODE**: it indexes the {prose} `standards/` sub-documents that hold the '
            f'content. Load one on-demand; do not load all {prose} at once.',
            '',
        ]
    # Decoy carried by EVERY fixture: ordinary prose whose anchor phrase is
    # preceded by an ordinary word rather than a count token. It must never be
    # read as a count claim, so it doubles as a regression guard on the
    # count-token discriminator in every test below.
    out += [
        'The `standards/` sub-documents follow two conventions that future authors MUST preserve.',
        '',
    ]
    if include_load_section:
        out += [
            '## Available Standards (load on-demand)',
            '',
            '| Standard | Load when |',
            '|----------|-----------|',
        ]
        out += [f'| [`standards/{n}`](standards/{n}) | when relevant |' for n in load_rows]
        out += ['']
        if load_section_prose is not None:
            out += [load_section_prose, '']
    if include_reference_section:
        out += ['## Standards Reference', '', '| Standard | Purpose |', '|----------|---------|']
        out += [f'| {n} | purpose |' for n in reference_rows]
        out += ['']

    skill_md = skill_dir / 'SKILL.md'
    skill_md.write_text('\n'.join(out), encoding='utf-8')
    return skill_md


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

    def test_persona_security_expert_absent_contributes_nothing(self, tmp_path: Path) -> None:
        # Only the extension-api surface exists; the standards-index surface is
        # out of scope when its governed SKILL.md is absent.
        _write_bundle_extension(tmp_path, 'bundle-a', {'provides_triage': '"t"'})
        _write_extension_api_table(tmp_path, [('`provides_triage()`', '1')])

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


# ===========================================================================
# Second surface — the persona-security-expert standards index, checked
# against the population derived from that skill's standards/ directory.
# ===========================================================================


class TestPersonaSecurityExpertIndex:
    """The prose count and both index tables are verified against standards/ on disk."""

    _POPULATION = ['alpha.md', 'beta.md', 'gamma.md']

    def test_index_agreeing_with_the_directory_is_clean(self, tmp_path: Path) -> None:
        _write_persona_security_expert(tmp_path, self._POPULATION)

        assert analyze_literal_count(tmp_path) == []

    def test_ordinary_prose_naming_the_standards_dir_is_not_a_count_claim(
        self, tmp_path: Path
    ) -> None:
        # The anchor phrase alone is not the discriminator: the token in front of
        # it must be a digit or a number word. Ordinary prose that merely names
        # the standards/ directory would otherwise be read as a count claim whose
        # "stated count" is an English word, flagging a correct document.
        skill_md = _write_persona_security_expert(tmp_path, self._POPULATION)
        body = skill_md.read_text(encoding='utf-8')

        assert '`standards/` sub-documents follow two conventions' in body, (
            'the decoy sentence must be present, or this test asserts nothing'
        )
        assert analyze_literal_count(tmp_path) == []

    def test_digit_form_of_the_prose_count_is_accepted(self, tmp_path: Path) -> None:
        # The count may be spelled as a word or as a digit; both compare against
        # the same derived population size.
        _write_persona_security_expert(tmp_path, self._POPULATION, prose='3')

        assert analyze_literal_count(tmp_path) == []

    def test_stale_prose_count_is_flagged_with_the_derived_population(self, tmp_path: Path) -> None:
        skill_md = _write_persona_security_expert(tmp_path, self._POPULATION, prose='four')

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 2, f'both anchored prose claims must be flagged, got {findings}'
        for finding in findings:
            assert finding['rule_id'] == RULE_ID
            assert finding['file'] == str(skill_md)
            assert finding['severity'] == 'warning'
            assert finding['fixable'] is False
            assert finding['details']['surface'] == 'prose'
            assert finding['details']['stated'] == 'four'
            assert finding['details']['actual'] == 3
            # The derived population size travels on every finding, so a reader
            # can never mistake the check for one run against an unread set.
            assert finding['details']['population_size'] == 3

    def test_load_table_missing_a_document_is_flagged(self, tmp_path: Path) -> None:
        _write_persona_security_expert(
            tmp_path, self._POPULATION, load_listed=['alpha.md', 'beta.md']
        )

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1
        details = findings[0]['details']
        assert details['surface'] == 'Available Standards'
        assert details['missing'] == ['gamma.md']
        assert details['unknown'] == []
        assert details['population_size'] == 3

    def test_reference_table_listing_an_absent_document_is_flagged(self, tmp_path: Path) -> None:
        _write_persona_security_expert(
            tmp_path, self._POPULATION, reference_listed=[*self._POPULATION, 'ghost.md']
        )

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1
        details = findings[0]['details']
        assert details['surface'] == 'Standards Reference'
        assert details['missing'] == []
        assert details['unknown'] == ['ghost.md']
        assert details['population_size'] == 3

    def test_both_tables_drift_independently(self, tmp_path: Path) -> None:
        _write_persona_security_expert(
            tmp_path,
            self._POPULATION,
            load_listed=['alpha.md'],
            reference_listed=['alpha.md', 'beta.md'],
        )

        findings = analyze_literal_count(tmp_path)

        by_surface = {f['details']['surface']: f['details'] for f in findings}
        assert set(by_surface) == {'Available Standards', 'Standards Reference'}
        assert by_surface['Available Standards']['missing'] == ['beta.md', 'gamma.md']
        assert by_surface['Standards Reference']['missing'] == ['gamma.md']


class TestPersonaSecurityExpertFailsClosed:
    """Every way the standards-index check could go vacuous emits a finding instead."""

    def test_empty_standards_directory_is_flagged(self, tmp_path: Path) -> None:
        # An empty population is the vacuous-guard condition: nothing to compare
        # against, so the check must NOT report agreement.
        _write_persona_security_expert(tmp_path, [], prose='zero')

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1
        assert findings[0]['details'] == {'surface': 'population', 'population_size': 0}

    def test_missing_index_section_is_flagged(self, tmp_path: Path) -> None:
        _write_persona_security_expert(
            tmp_path, ['alpha.md', 'beta.md'], prose='two', include_reference_section=False
        )

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1
        details = findings[0]['details']
        assert details['surface'] == 'Standards Reference'
        assert details['missing'] == ['alpha.md', 'beta.md']
        assert details['population_size'] == 2

    def test_prose_link_outside_the_table_does_not_mask_a_missing_row(
        self, tmp_path: Path
    ) -> None:
        # The "Available Standards" set is collected from TABLE ROWS only. A
        # prose link to standards/gamma.md that sits in the section but outside
        # the table is not an index entry: counting it would complete the set
        # and let a genuinely missing row report clean (fail-open).
        _write_persona_security_expert(
            tmp_path,
            ['alpha.md', 'beta.md', 'gamma.md'],
            prose='three',
            load_listed=['alpha.md', 'beta.md'],
            load_section_prose=(
                'See also [`standards/gamma.md`](standards/gamma.md) for the deep dive.'
            ),
        )

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1, f'the missing gamma.md row must still be flagged, got {findings}'
        details = findings[0]['details']
        assert details['surface'] == 'Available Standards'
        assert details['missing'] == ['gamma.md']
        assert details['unknown'] == []
        assert details['population_size'] == 3

    def test_unreadable_governed_file_is_flagged(self, tmp_path: Path) -> None:
        # analyze_literal_count gates on is_file(), so this path is reached only
        # for a file that EXISTS but cannot be decoded. Only an ABSENT governed
        # file is out of scope (see test_persona_security_expert_absent_...);
        # returning no findings here would make a broken index indistinguishable
        # from a clean one.
        skill_md = _write_persona_security_expert(tmp_path, ['alpha.md', 'beta.md'], prose='two')
        skill_md.write_bytes(b'# Persona: Security Expert\n\xff\xfe not valid utf-8\n')

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1
        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['file'] == str(skill_md)
        assert finding['severity'] == 'warning'
        assert finding['fixable'] is False
        assert finding['details']['surface'] == 'unreadable'
        assert finding['details']['error'] == 'UnicodeDecodeError'

    def test_unanchored_prose_count_is_flagged(self, tmp_path: Path) -> None:
        # A body that states the count in an unrecognised phrasing is UNVERIFIED,
        # not verified-clean.
        _write_persona_security_expert(tmp_path, ['alpha.md', 'beta.md'], prose=None)

        findings = analyze_literal_count(tmp_path)

        assert len(findings) == 1
        details = findings[0]['details']
        assert details['surface'] == 'prose'
        assert details['stated'] is None
        assert details['population_size'] == 2
