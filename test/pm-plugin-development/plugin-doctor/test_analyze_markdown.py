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
derive_link_boundary = _am.derive_link_boundary
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

    @staticmethod
    def _make_bundle_layout(tmp_path: Path) -> tuple[Path, Path]:
        """Build a ``<repo>/marketplace/bundles/<bundle>/skills/{a,b}/`` layout.

        Plants a ``.git`` marker at ``tmp_path`` so ``derive_link_boundary``
        resolves to the repo root (its sole anchor after the
        ``marketplace/bundles`` special-case was removed). Returns
        ``(repo_root, skill_a_dir)`` where ``repo_root`` is the ``.git``-bearing
        directory the boundary resolves to and ``skill_a_dir`` holds the linking
        file.
        """
        (tmp_path / '.git').mkdir()
        bundle = tmp_path / 'marketplace' / 'bundles' / 'my-bundle'
        skill_a = bundle / 'skills' / 'skill-a'
        skill_b = bundle / 'skills' / 'skill-b'
        skill_a.mkdir(parents=True)
        skill_b.mkdir(parents=True)
        repo_root = tmp_path
        return repo_root, skill_a

    def test_cross_directory_link_to_existing_file_is_silent(self, tmp_path: Path) -> None:
        # A cross-directory ``../skill-b/target.md`` link whose target EXISTS
        # must produce zero findings on the per-component (no-boundary) path —
        # this is the regressing case that produced ~234 false positives.
        _tree_root, skill_a = self._make_bundle_layout(tmp_path)
        target = skill_a.parent / 'skill-b' / 'target.md'
        target.write_text('# target\n', encoding='utf-8')
        skill_md = skill_a / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\nSee [sibling](../skill-b/target.md).\n', encoding='utf-8'
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert findings == []

    def test_cross_directory_link_to_missing_file_is_flagged(self, tmp_path: Path) -> None:
        # A cross-directory ``../skill-b/missing.md`` link whose target does NOT
        # exist, but resolves INSIDE the derived boundary, still fires exactly
        # one finding (the genuine broken-link case is preserved).
        _tree_root, skill_a = self._make_bundle_layout(tmp_path)
        skill_md = skill_a / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\nSee [sibling](../skill-b/missing.md).\n', encoding='utf-8'
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert len(findings) == 1
        assert findings[0]['target'] == '../skill-b/missing.md'

    def test_no_boundary_and_root_boundary_agree(self, tmp_path: Path) -> None:
        # The same fixture file, called once with no ``boundary_dir`` and once
        # with an explicit ``boundary_dir`` at the tree root, yields identical
        # findings — proving the unified boundary derivation makes the
        # per-component and whole-tree call sites agree.
        tree_root, skill_a = self._make_bundle_layout(tmp_path)
        target = skill_a.parent / 'skill-b' / 'present.md'
        target.write_text('# present\n', encoding='utf-8')
        skill_md = skill_a / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\n'
            'See [present](../skill-b/present.md) '
            'and [gone](../skill-b/gone.md).\n',
            encoding='utf-8',
        )
        content = skill_md.read_text()

        no_boundary = check_broken_relative_link(content, str(skill_md))
        root_boundary = check_broken_relative_link(
            content, str(skill_md), boundary_dir=tree_root
        )

        assert no_boundary == root_boundary
        assert len(no_boundary) == 1
        assert no_boundary[0]['target'] == '../skill-b/gone.md'

    # -- Repo-root boundary widening (deliverable D3) ------------------------

    @staticmethod
    def _make_repo_layout(tmp_path: Path) -> tuple[Path, Path]:
        """Build a ``<repo>/marketplace/bundles/<bundle>/skills/<skill>/`` tree.

        Plants a ``.git`` marker at ``tmp_path`` (the repo root) and a sibling
        ``doc/`` tree so cross-tree in-repo links can be exercised. Returns
        ``(repo_root, skill_dir)`` where ``skill_dir`` holds the linking file
        five levels below the repo root (``skills/<skill>`` under
        ``marketplace/bundles/<bundle>``).
        """
        (tmp_path / '.git').mkdir()
        (tmp_path / 'doc').mkdir()
        skill_dir = tmp_path / 'marketplace' / 'bundles' / 'my-bundle' / 'skills' / 'skill-a'
        skill_dir.mkdir(parents=True)
        return tmp_path, skill_dir

    def test_derive_boundary_resolves_bundles_file_to_repo_root(self, tmp_path: Path) -> None:
        # A file under marketplace/bundles/** resolves its containment boundary
        # to the repo root (the .git-bearing directory), not the
        # marketplace/bundles ancestor — the special-case was removed in D3.
        repo_root, skill_dir = self._make_repo_layout(tmp_path)
        skill_md = skill_dir / 'SKILL.md'
        skill_md.write_text('# Doc\n', encoding='utf-8')

        assert derive_link_boundary(str(skill_md)) == repo_root

    def test_in_repo_cross_tree_missing_link_is_flagged(self, tmp_path: Path) -> None:
        # An in-repo cross-tree link from a bundle file into doc/ whose target
        # is missing now resolves INSIDE the widened repo-root boundary and is
        # flagged. Under the old marketplace/bundles boundary it escaped the
        # boundary and was silently skipped.
        _repo_root, skill_dir = self._make_repo_layout(tmp_path)
        skill_md = skill_dir / 'SKILL.md'
        # skill_dir is five levels below the repo root.
        skill_md.write_text(
            '# Doc\n\nSee [guide](../../../../../doc/missing.md).\n', encoding='utf-8'
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert len(findings) == 1
        assert findings[0]['target'] == '../../../../../doc/missing.md'

    def test_in_repo_cross_tree_existing_link_is_silent(self, tmp_path: Path) -> None:
        # The same cross-tree link whose target EXISTS under the repo root is
        # silent — containment plus existence, never a false positive.
        repo_root, skill_dir = self._make_repo_layout(tmp_path)
        (repo_root / 'doc' / 'guide.md').write_text('# guide\n', encoding='utf-8')
        skill_md = skill_dir / 'SKILL.md'
        skill_md.write_text(
            '# Doc\n\nSee [guide](../../../../../doc/guide.md).\n', encoding='utf-8'
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert findings == []

    def test_link_escaping_repo_root_is_skipped(self, tmp_path: Path) -> None:
        # A link resolving ABOVE the repo root (outside the .git boundary) is
        # skipped without a disk probe — the containment property is preserved
        # by the widening, not weakened.
        _repo_root, skill_dir = self._make_repo_layout(tmp_path)
        skill_md = skill_dir / 'SKILL.md'
        # Six levels up escapes the repo root (five levels reaches it).
        skill_md.write_text(
            '# Doc\n\nSee [outside](../../../../../../escaped.md).\n', encoding='utf-8'
        )

        findings = check_broken_relative_link(skill_md.read_text(), str(skill_md))

        assert findings == []

    def test_template_scaffold_links_are_exempt(self, tmp_path: Path) -> None:
        # A *-template.md scaffold carries links written for its instantiation
        # location, not its storage location, so its broken-looking relative
        # links are never flagged (e.g. assets/readme-template.md).
        repo_root, skill_dir = self._make_repo_layout(tmp_path)
        assets = skill_dir / 'assets'
        assets.mkdir()
        template = assets / 'readme-template.md'
        template.write_text(
            '# {bundle-name}\n\n- [Docs](../../README.md)\n', encoding='utf-8'
        )

        findings = check_broken_relative_link(template.read_text(), str(template))

        assert findings == []


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
        assert fenced[0]['fixable'] is True

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
