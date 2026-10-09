#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``changed_code_units`` candidate list.

The list is the review anchor of the behavioural defect check: one entry per
function or method the diff touched in a non-test ``.py`` file. These tests pin
what it lists, what it leaves out, and that it stays out of ``counts.total``.
"""

import subprocess
from pathlib import Path

import pytest
from _self_review_detectors import _detect_changed_code_units, _parsed_code_units
from _self_review_diff import _iter_removed_line_anchors
from _self_review_patterns import CANDIDATE_LISTS

_LIST = 'changed_code_units'

_MODULE = (
    'import json\n'  # 1
    '\n'  # 2
    '\n'  # 3
    'def untouched(path):\n'  # 4
    '    return path\n'  # 5
    '\n'  # 6
    '\n'  # 7
    'def modified(path):\n'  # 8
    '    text = path.read_text()\n'  # 9
    '    return json.loads(text)\n'  # 10
    '\n'  # 11
    '\n'  # 12
    'class Store:\n'  # 13
    '    def load(self, key):\n'  # 14
    '        return self._data.get(key)\n'  # 15
    '\n'  # 16
    '    async def refresh(self):\n'  # 17
    '        self._data = {}\n'  # 18
)


def _project(tmp_path: Path, rel: str = 'pkg/mod.py', body: str = _MODULE) -> Path:
    project_dir = tmp_path / 'proj'
    target = project_dir / rel
    target.parent.mkdir(parents=True)
    target.write_text(body)
    return project_dir


class TestDetectChangedCodeUnits:
    def test_modified_function_is_listed_and_its_neighbour_is_not(self, tmp_path):
        project_dir = _project(tmp_path)

        units = _detect_changed_code_units([('pkg/mod.py', 10, '    return json.loads(text)')], project_dir)

        assert units == [{'file': 'pkg/mod.py', 'line': 8, 'name': 'modified', 'kind': 'function'}]

    def test_newly_added_method_is_listed_as_a_method(self, tmp_path):
        project_dir = _project(tmp_path)
        added = [
            ('pkg/mod.py', 14, '    def load(self, key):'),
            ('pkg/mod.py', 15, '        return self._data.get(key)'),
        ]

        units = _detect_changed_code_units(added, project_dir)

        assert units == [{'file': 'pkg/mod.py', 'line': 14, 'name': 'load', 'kind': 'method'}]

    def test_async_def_opens_a_unit(self, tmp_path):
        project_dir = _project(tmp_path)

        units = _detect_changed_code_units([('pkg/mod.py', 18, '        self._data = {}')], project_dir)

        assert units == [{'file': 'pkg/mod.py', 'line': 17, 'name': 'refresh', 'kind': 'method'}]

    def test_markdown_only_diff_lists_nothing(self, tmp_path):
        project_dir = _project(tmp_path, rel='docs/guide.md', body='# Guide\n\ndef not_code():\n')

        assert _detect_changed_code_units([('docs/guide.md', 3, 'def not_code():')], project_dir) == []

    @pytest.mark.parametrize(
        'rel',
        ['test/pkg/test_mod.py', 'tests/helpers.py', 'pkg/test_mod.py', 'pkg/mod_test.py', 'pkg/conftest.py'],
    )
    def test_test_module_only_diff_lists_nothing(self, tmp_path, rel):
        project_dir = _project(tmp_path, rel=rel)

        # Matched control: the same hunk in a production path IS listed, so the
        # empty result below is the path exclusion and not an inert fixture.
        control = _project(tmp_path / 'control')
        assert _detect_changed_code_units([('pkg/mod.py', 10, '    return json.loads(text)')], control)

        assert _detect_changed_code_units([(rel, 10, '    return json.loads(text)')], project_dir) == []

    def test_without_a_post_image_the_added_lines_alone_are_walked(self):
        added = [('pkg/mod.py', 3, 'def fresh(path):'), ('pkg/mod.py', 4, '    return path')]

        assert _detect_changed_code_units(added, None) == [
            {'file': 'pkg/mod.py', 'line': 3, 'name': 'fresh', 'kind': 'function'}
        ]

    def test_an_unparseable_post_image_falls_back_to_the_line_split(self, tmp_path):
        body = 'def broken(path):\n    return path +\n'
        project_dir = _project(tmp_path, body=body)
        assert _parsed_code_units(body.splitlines()) is None

        units = _detect_changed_code_units([('pkg/mod.py', 2, '    return path +')], project_dir)

        assert units == [{'file': 'pkg/mod.py', 'line': 1, 'name': 'broken', 'kind': 'function'}]

    def test_a_docstring_line_reading_like_a_class_header_does_not_hide_the_function(self, tmp_path):
        body = (
            'def discover(path):\n'  # 1
            '    """Find extensions.\n'  # 2
            '\n'  # 3
            '    A bundle without the\n'  # 4
            '    class is silently omitted.\n'  # 5
            '    """\n'  # 6
            '    return path\n'  # 7
        )
        project_dir = _project(tmp_path, body=body)

        units = _detect_changed_code_units([('pkg/mod.py', 7, '    return path')], project_dir)

        assert units == [{'file': 'pkg/mod.py', 'line': 1, 'name': 'discover', 'kind': 'function'}]

    def test_a_line_is_attributed_to_the_innermost_function_only(self, tmp_path):
        body = (
            'def outer(items):\n'  # 1
            '    def inner(item):\n'  # 2
            '        return item\n'  # 3
            '\n'  # 4
            '    return [inner(i) for i in items]\n'  # 5
        )
        project_dir = _project(tmp_path, body=body)

        inner = _detect_changed_code_units([('pkg/mod.py', 3, '        return item')], project_dir)
        outer = _detect_changed_code_units([('pkg/mod.py', 5, '    return [inner(i) for i in items]')], project_dir)

        assert [u['name'] for u in inner] == ['inner']
        assert [u['name'] for u in outer] == ['outer']

    def test_a_line_outside_every_function_names_no_unit(self, tmp_path):
        body = 'def f():\n    return 1\n\n\nLIMIT = 3\n\n\nclass C:\n    size = 2\n'
        project_dir = _project(tmp_path, body=body)

        # Matched control: the same file with a line inside ``f`` does list it.
        assert _detect_changed_code_units([('pkg/mod.py', 2, '    return 1')], project_dir)

        assert _detect_changed_code_units([('pkg/mod.py', 5, 'LIMIT = 3')], project_dir) == []
        assert _detect_changed_code_units([('pkg/mod.py', 9, '    size = 2')], project_dir) == []

    def test_a_decorator_line_belongs_to_the_function_it_decorates(self, tmp_path):
        body = 'def first():\n    return 1\n\n\n@cache\ndef second():\n    return 2\n'
        project_dir = _project(tmp_path, body=body)

        units = _detect_changed_code_units([('pkg/mod.py', 5, '@cache')], project_dir)

        assert units == [{'file': 'pkg/mod.py', 'line': 6, 'name': 'second', 'kind': 'function'}]


class TestRemovedLines:
    """A removal has no post-image line of its own, and must still name its function."""

    _DIFF = (
        'diff --git a/pkg/mod.py b/pkg/mod.py\n'
        '--- a/pkg/mod.py\n'
        '+++ b/pkg/mod.py\n'
        '@@ -8,4 +8,3 @@ def untouched(path):\n'
        ' def modified(path):\n'
        '-    check_allowed(path)\n'
        '     text = path.read_text()\n'
        '     return json.loads(text)\n'
    )

    def test_a_removal_is_anchored_on_the_line_that_follows_it(self):
        assert _iter_removed_line_anchors(self._DIFF) == [('pkg/mod.py', 9)]

    def test_a_run_of_removed_lines_yields_one_anchor_and_added_lines_yield_none(self):
        diff = '+++ b/pkg/mod.py\n@@ -1,4 +1,3 @@\n keep\n-gone one\n-gone two\n+added\n keep\n'

        assert _iter_removed_line_anchors(diff) == [('pkg/mod.py', 2)]
        assert _iter_removed_line_anchors('+++ b/pkg/mod.py\n@@ -1,1 +1,2 @@\n keep\n+added\n') == []

    def test_a_deleted_file_yields_no_anchor(self):
        diff = (
            'diff --git a/pkg/kept.py b/pkg/kept.py\n'
            '+++ b/pkg/kept.py\n'
            '@@ -1,1 +1,1 @@\n'
            ' keep\n'
            'diff --git a/pkg/gone.py b/pkg/gone.py\n'
            '--- a/pkg/gone.py\n'
            '+++ /dev/null\n'
            '@@ -1,2 +0,0 @@\n'
            '-def f():\n'
            '-    return 1\n'
        )

        assert _iter_removed_line_anchors(diff) == []

    def test_a_deletion_only_change_names_the_function_it_was_made_in(self, tmp_path):
        project_dir = _project(tmp_path)

        # Matched control: with no removal anchor and no added line, nothing is listed.
        assert _detect_changed_code_units([], project_dir, []) == []

        units = _detect_changed_code_units([], project_dir, _iter_removed_line_anchors(self._DIFF))

        assert units == [{'file': 'pkg/mod.py', 'line': 8, 'name': 'modified', 'kind': 'function'}]

    def test_a_removal_between_two_functions_names_the_one_above_it(self, tmp_path):
        project_dir = _project(tmp_path)

        # The anchor is post-image line 6, so the removed text sat directly below
        # line 5 — the last line of ``untouched``.
        units = _detect_changed_code_units([], project_dir, [('pkg/mod.py', 6)])

        assert [u['name'] for u in units] == ['untouched']

    def test_a_removal_in_a_test_module_names_nothing(self, tmp_path):
        project_dir = _project(tmp_path, rel='test/pkg/test_mod.py')

        assert _detect_changed_code_units([], project_dir, [('test/pkg/test_mod.py', 10)]) == []


class TestParsedCodeUnitKind:
    def test_kind_follows_the_nearest_enclosing_function_or_class(self):
        units = _parsed_code_units(_MODULE.splitlines())

        assert units is not None
        assert [(u['name'], u['kind']) for u in units] == [
            ('untouched', 'function'),
            ('modified', 'function'),
            ('load', 'method'),
            ('refresh', 'method'),
        ]

    def test_a_function_under_a_conditional_after_a_class_is_not_a_method(self):
        source = 'class A:\n    x = 1\n\n\nif A.x:\n    def g():\n        def inner():\n            pass\n'

        units = _parsed_code_units(source.splitlines())

        assert units is not None
        assert [(u['name'], u['kind']) for u in units] == [('g', 'function'), ('inner', 'function')]


class TestRegistryEntry:
    def test_list_is_a_structural_review_anchor_outside_the_total(self):
        spec = next(s for s in CANDIDATE_LISTS if s.key == _LIST)

        assert spec.family == 'structural'
        assert spec.in_total is False


# =============================================================================
# Regression fixture: an unreadable input read as an empty set
# =============================================================================
#
# A reader that collapses "could not read" into "read, and empty", feeding a gate that then
# passes. The list names the reader so the behavioural check reads it whole.

_UNREADABLE_AS_EMPTY = (
    'from pathlib import Path\n'
    '\n'
    '\n'
    'def read_declared_paths(source: Path) -> set[str]:\n'
    '    try:\n'
    '        text = source.read_text()\n'
    '    except OSError:\n'
    '        return set()\n'
    '    return {line.strip() for line in text.splitlines() if line.strip()}\n'
    '\n'
    '\n'
    'def plans_comparable(left: Path, right: Path) -> bool:\n'
    '    return not (read_declared_paths(left) & read_declared_paths(right))\n'
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


def _surface(repo: Path) -> dict:
    from conftest import get_script_path, run_script

    script = get_script_path('pm-plugin-development', 'ext-self-review-plan-marshall', 'self_review.py')
    result = run_script(
        script, 'surface', '--plan-id', 'changed-units-plan', '--project-dir', str(repo), '--base-branch', 'main'
    )
    assert result.success, f'surface failed: stderr={result.stderr}'
    data: dict = result.toon()
    return data


class TestUnreadableReadAsEmptyIsSurfaced:
    @pytest.fixture
    def repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / 'repo'
        repo.mkdir()
        _git(repo, 'init', '-q', '-b', 'main')
        _git(repo, 'config', 'user.email', 'test@example.com')
        _git(repo, 'config', 'user.name', 'Test')
        (repo / 'base.txt').write_text('base\n')
        _git(repo, 'add', 'base.txt')
        _git(repo, 'commit', '-q', '-m', 'base')
        _git(repo, 'checkout', '-q', '-b', 'feature')
        (repo / 'gate.py').write_text(_UNREADABLE_AS_EMPTY)
        _git(repo, 'add', 'gate.py')
        return repo

    def test_the_fail_open_reader_is_named_for_the_behavioural_check(self, repo):
        data = _surface(repo)

        units = {(e['file'], e['name'], e['kind']) for e in data[_LIST]}
        assert ('gate.py', 'read_declared_paths', 'function') in units
        assert ('gate.py', 'plans_comparable', 'function') in units
        assert int(data['counts'][_LIST]) == len(data[_LIST])

    def test_a_committed_guard_removal_is_surfaced_end_to_end(self, repo):
        _git(repo, 'commit', '-q', '-m', 'add gate')
        guarded = _UNREADABLE_AS_EMPTY.replace('    return not (', '    assert left != right\n    return not (')
        assert guarded != _UNREADABLE_AS_EMPTY
        (repo / 'gate.py').write_text(guarded)
        _git(repo, 'commit', '-q', '-am', 'add guard')
        _git(repo, 'branch', '-f', 'main', 'HEAD')
        # The branch under review differs from its base by one removed line only.
        (repo / 'gate.py').write_text(_UNREADABLE_AS_EMPTY)
        _git(repo, 'commit', '-q', '-am', 'remove guard')

        data = _surface(repo)

        assert [(e['name'], e['kind']) for e in data[_LIST]] == [('plans_comparable', 'function')]

    def test_the_list_does_not_raise_the_total(self, repo):
        counts = _surface(repo)['counts']

        assert int(counts[_LIST]) >= 2
        # ``_LIST`` is excluded by name, not through its own registry flag, so the
        # equality below fails if the flag is ever set.
        excluded = {spec.key for spec in CANDIDATE_LISTS if not spec.in_total} | {_LIST}
        included_sum = sum(int(v) for k, v in counts.items() if k not in excluded and k not in ('total', 'by_family'))
        assert int(counts['total']) == included_sum
