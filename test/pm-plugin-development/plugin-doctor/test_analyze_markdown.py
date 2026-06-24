# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``broken-relative-link`` and ``fenced-code-no-language`` rules.

Both rules are checks in ``_analyze_markdown.py``:

  * ``check_broken_relative_link(content, file_path)`` — resolves every
    ``[text](relative/path.md)`` link against the linking file's own directory
    and flags targets that do not exist on disk (error severity). Absolute URLs,
    root-absolute paths, pure-anchor links, and links inside fenced code blocks
    are out of scope.
  * ``check_fenced_code_no_language(content)`` — flags every *opening* fenced
    block whose line carries no language info-string (warning severity, MD040).
    Closing fences legitimately carry no info-string and are never flagged.

The marketplace-wide gate aggregator ``analyze_markdown_mirror_rules`` wraps both
checks into standard issue dicts carrying ``rule_id`` / ``severity``; the tests
assert on those wired fields as well as the raw check output.

Test layers:
  * broken-relative-link: missing target fires; valid target stays silent; URL /
    anchor / fenced-block links stay silent.
  * fenced-code-no-language: language-less opening fence fires; tagged fence
    stays silent; closing fence is never double-flagged.
  * aggregator: wired findings carry the right rule_id and severity.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_am = _load_module('_analyze_markdown', '_analyze_markdown.py')
_da = _load_module('_doctor_analysis', '_doctor_analysis.py')

check_broken_relative_link = _am.check_broken_relative_link
check_fenced_code_no_language = _am.check_fenced_code_no_language
analyze_markdown_mirror_rules = _da.analyze_markdown_mirror_rules


# ===========================================================================
# broken-relative-link
# ===========================================================================


class TestBrokenRelativeLink:
    """A relative link whose target is missing on disk is flagged."""

    def test_missing_target_is_flagged(self, tmp_path: Path) -> None:
        skill_md = tmp_path / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\nSee [the standard](standards/missing.md) for details.\n',
            encoding='utf-8',
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert len(findings) == 1
        assert findings[0]['target'] == 'standards/missing.md'
        assert findings[0]['line'] == 3

    def test_existing_target_is_silent(self, tmp_path: Path) -> None:
        (tmp_path / 'standards').mkdir()
        (tmp_path / 'standards' / 'present.md').write_text('# present\n', encoding='utf-8')
        skill_md = tmp_path / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\nSee [the standard](standards/present.md).\n', encoding='utf-8'
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert findings == []

    def test_fragment_only_file_part_is_checked(self, tmp_path: Path) -> None:
        (tmp_path / 'standards').mkdir()
        (tmp_path / 'standards' / 'present.md').write_text('# present\n', encoding='utf-8')
        skill_md = tmp_path / 'SKILL.md'
        # The file part exists; the #anchor is stripped before resolution.
        skill_md.write_text(
            '# Doc\n\nSee [here](standards/present.md#section).\n', encoding='utf-8'
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert findings == []

    def test_url_anchor_and_absolute_links_are_out_of_scope(self, tmp_path: Path) -> None:
        skill_md = tmp_path / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\n'
            '[ext](https://example.com/page) '
            '[mail](mailto:x@example.com) '
            '[anchor](#section) '
            '[root](/abs/path.md)\n',
            encoding='utf-8',
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert findings == []

    def test_link_inside_fenced_block_is_ignored(self, tmp_path: Path) -> None:
        skill_md = tmp_path / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\n```text\nSee [missing](nope/gone.md) — illustrative only.\n```\n',
            encoding='utf-8',
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert findings == []

    def test_link_inside_inline_code_span_is_ignored(self, tmp_path: Path) -> None:
        # A relative-link literal inside a single-backtick inline-code span is an
        # illustrative example, not a real on-disk reference. Mirrors the
        # confirmed FPs at rule-provenance.md:209, rule-catalog.md:950, and
        # ref-svg-diagrams/standards/theme-handling.md:7 (a ``![](path)`` literal
        # inside backticks). None of these should fire broken-relative-link.
        skill_md = tmp_path / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\n'
            'When a target moves, every `[text](relative/path.md)` pointing at '
            'it becomes a dead reference.\n\n'
            'An SVG referenced via `![](path/to/file.svg)` (Markdown) is loaded '
            'as an `<img>`.\n',
            encoding='utf-8',
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert findings == []

    def test_real_link_outside_span_still_fires_with_span_on_same_line(self, tmp_path: Path) -> None:
        # The span exemption must be surgical: a real broken link OUTSIDE the
        # inline-code span on the same line is still flagged.
        skill_md = tmp_path / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\nThe `[text](in/span.md)` form is illustrative, but '
            'see [the standard](standards/missing.md) for the real link.\n',
            encoding='utf-8',
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert len(findings) == 1
        assert findings[0]['target'] == 'standards/missing.md'


# ===========================================================================
# fenced-code-no-language
# ===========================================================================


class TestFencedCodeNoLanguage:
    """A fenced block opened without a language info-string is flagged."""

    def test_language_less_opening_fence_is_flagged(self) -> None:
        content = '# Doc\n\n```\nsome code\n```\n'

        findings = check_fenced_code_no_language(content)

        assert len(findings) == 1
        assert findings[0]['line'] == 3

    def test_tagged_opening_fence_is_silent(self) -> None:
        content = '# Doc\n\n```python\nprint("hi")\n```\n'

        findings = check_fenced_code_no_language(content)

        assert findings == []

    def test_closing_fence_is_not_double_flagged(self) -> None:
        # A single language-less block must yield exactly one finding (the open),
        # never a second for the bare closing fence.
        content = '# Doc\n\n```\nbody\n```\n\nmore prose\n'

        findings = check_fenced_code_no_language(content)

        assert len(findings) == 1

    def test_multiple_blocks_mix(self) -> None:
        content = (
            '# Doc\n\n'
            '```bash\necho ok\n```\n\n'  # tagged → silent
            '```\nbare\n```\n'  # bare → flagged
        )

        findings = check_fenced_code_no_language(content)

        assert len(findings) == 1
        assert findings[0]['line'] == 7


# ===========================================================================
# Marketplace-wide aggregator — wired rule_id / severity fields.
# ===========================================================================


class TestAggregatorWiring:
    """analyze_markdown_mirror_rules wraps both checks with rule_id and severity."""

    def _bundle_md(self, root: Path, body: str) -> Path:
        skill_dir = root / 'b' / 'skills' / 'fixture-skill'
        skill_dir.mkdir(parents=True, exist_ok=True)
        md = skill_dir / 'SKILL.md'
        md.write_text(body, encoding='utf-8')
        return md

    def test_broken_link_finding_fields(self, tmp_path: Path) -> None:
        self._bundle_md(tmp_path, '# F\n\n[gone](standards/missing.md)\n')

        findings = analyze_markdown_mirror_rules(tmp_path)

        broken = [f for f in findings if f['rule_id'] == 'broken-relative-link']
        assert len(broken) == 1
        assert broken[0]['type'] == 'broken-relative-link'
        assert broken[0]['severity'] == 'error'
        assert broken[0]['fixable'] is False

    def test_fenced_no_language_finding_fields(self, tmp_path: Path) -> None:
        self._bundle_md(tmp_path, '# F\n\n```\ncode\n```\n')

        findings = analyze_markdown_mirror_rules(tmp_path)

        fenced = [f for f in findings if f['rule_id'] == 'fenced-code-no-language']
        assert len(fenced) == 1
        assert fenced[0]['type'] == 'fenced-code-no-language'
        assert fenced[0]['severity'] == 'warning'
        assert fenced[0]['fixable'] is False

    def test_clean_tree_is_silent(self, tmp_path: Path) -> None:
        (tmp_path / 'b' / 'skills' / 'fixture-skill' / 'standards').mkdir(parents=True)
        (tmp_path / 'b' / 'skills' / 'fixture-skill' / 'standards' / 'x.md').write_text(
            '# x\n', encoding='utf-8'
        )
        self._bundle_md(
            tmp_path,
            '# F\n\nSee [x](standards/x.md).\n\n```python\nok = 1\n```\n',
        )

        findings = analyze_markdown_mirror_rules(tmp_path)

        assert findings == []

    def test_empty_root_returns_no_findings(self, tmp_path: Path) -> None:
        findings = analyze_markdown_mirror_rules(tmp_path)

        assert findings == []
