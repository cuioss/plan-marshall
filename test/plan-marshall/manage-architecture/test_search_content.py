#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``search --content`` reader on ``manage-architecture``.

``find`` answers *which PATH matches*; ``search --content`` answers *which file
CONTAINS*. The gap between them is the reason this verb exists: a dispatched
leaf whose ``Grep``/``Glob`` tools are revoked and whose Bash ``grep``/``find``
is hook-blocked had no sanctioned content-search path at all.

The assertions here pin the properties that make the verb trustworthy rather
than merely present:

* **The gap is real** — a body hit whose path does NOT contain the pattern is
  found by ``search`` and NOT by ``find`` (a matched positive/negative control
  over the same fixture, so the test cannot pass vacuously).
* **The backend is not ``git grep``** — an untracked-but-not-gitignored file in
  a directory that is not a git worktree at all is still searched. This is the
  property that refuted the ``git grep`` backend at outline time.
* **No caller input reaches a shell** — a pattern full of shell metacharacters
  is matched verbatim under ``--literal`` (and, as the paired control, does NOT
  match when the same string is compiled as a regex).
* **A negative is never confident** — ``count: 0`` always rides with
  ``files_scanned``, ``truncated``/``elided`` and ``unreadable[]``, so "nothing
  was searched" and "N files searched, genuinely absent" stay distinguishable.
* **The payload boundary holds** — a result entry carries exactly ``module``,
  ``category``, ``path``, ``match_count`` and never a line body or line number.
  This is a settled design decision (response size must scale with FILE count,
  not with match density), pinned as a test rather than left to review.
* **``match_count`` is a real count** — a file matched three times reports 3,
  not a truthy hit flag.
* **Anchors are per line** — ``^`` and ``$`` mean line-start / line-end (the
  semantics grep, ripgrep and the harness ``Grep`` tool give them), not
  file-start / file-end. A token on the SECOND line of a fixture is reachable by
  ``^token``; the mid-line control proves the anchor still binds.
"""

import sys
import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import seed_project  # noqa: E402

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_manage = load_script_module('plan-marshall', 'manage-architecture', '_cmd_manage.py', '_cmd_manage')
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

_post_process_files = _cmd_manage._post_process_files
FILE_CATEGORIES = _architecture_core.FILE_CATEGORIES
cmd_find = _cmd_client.cmd_find
cmd_search = _cmd_client.cmd_search

_ARCHITECTURE_SCRIPT = get_script_path('plan-marshall', 'manage-architecture', 'architecture.py')

# The exact key set a result entry is allowed to carry. Line bodies and line
# numbers are deliberately absent — see the module docstring.
_RESULT_KEYS = {'module', 'category', 'path', 'match_count'}

# Lives in a file body only; the fixture path ``pkg/alpha.py`` does not contain
# it, so ``find`` cannot reach it and ``search`` must.
_BODY_ONLY_TOKEN = 'ZEBRA_TOKEN'
# Written three times into one file so ``match_count`` has to be a count.
_TRIPLE_TOKEN = 'TRIPLE_TOKEN'
# Present in the fixture only inside an untracked file.
_UNTRACKED_TOKEN = 'UNTRACKED_TOKEN'
# A string of shell metacharacters: a VALID regex (so it compiles either way)
# that matches nothing as a regex, and matches verbatim under ``--literal``.
_METACHAR_PATTERN = '$(id); rm -rf'
# Never written into any fixture file.
_ABSENT_TOKEN = 'NO_SUCH_TOKEN_ANYWHERE'
# Starts lines 2 and 3 of ``pkg/anchored.py`` — never line 1, so a ``^``-anchored
# search reaches it only if the anchor is per LINE. Also appears mid-line in
# ``pkg/midline.py``, which is the negative half of the anchor assertion.
_ANCHOR_TOKEN = 'ANCHORED_TOKEN'
# Ends line 1 of ``pkg/dollar.py`` — never the last line, so a ``$``-anchored
# search reaches it only if the anchor is per LINE.
_ENDLINE_TOKEN = 'ENDLINE_TOKEN'
# In two different categories, so ``--category`` narrowing is observable.
_SHARED_TOKEN = 'SHARED_TOKEN'

_UNKNOWN_CATEGORY = 'bogus-category'
# A second real category the explicit-inventory fixture populates alongside
# ``source``, so the ``--category`` filter has something to narrow away from.
_SECOND_CATEGORY = 'doc'


def _write(path: Path, content: str = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _seed_crawled_project(tmpdir: str) -> None:
    """Seed a module whose inventory is produced by the REAL crawler.

    The crawl runs against a plain temporary directory that is not a git
    worktree, so every file in it is untracked by construction — which is
    precisely what makes the untracked-file assertion below non-vacuous. The
    inventory is built by ``_post_process_files`` (the gitignore-aware walk),
    never by ``git ls-files``.
    """
    project = Path(tmpdir)
    pkg = project / 'pkg'
    _write(pkg / 'alpha.py', f'{_BODY_ONLY_TOKEN} = 1\n')
    _write(pkg / 'beta.py', 'x = 2\n')
    _write(pkg / 'triple.py', f'{_TRIPLE_TOKEN}\n{_TRIPLE_TOKEN}\n{_TRIPLE_TOKEN}\n')
    _write(pkg / 'meta.py', f'value = "{_METACHAR_PATTERN}"\n')
    _write(pkg / 'untracked_only.py', f'{_UNTRACKED_TOKEN} = True\n')
    # Anchor fixtures. The token deliberately never starts line 1 / never ends
    # the last line, so a whole-body compile (no re.MULTILINE) cannot reach it.
    _write(pkg / 'anchored.py', f'import os\n{_ANCHOR_TOKEN} = 1\n{_ANCHOR_TOKEN} = 2\n')
    _write(pkg / 'midline.py', f'value = {_ANCHOR_TOKEN}\n')
    _write(pkg / 'dollar.py', f'a = {_ENDLINE_TOKEN}\nb = 2\n')

    modules = {'pkg': {'name': 'pkg', 'paths': {'module': 'pkg'}}}
    _post_process_files(modules, str(project))
    seed_project(tmpdir, modules)


def _seed_two_category_project(tmpdir: str) -> None:
    """Seed real files declared under two DIFFERENT categories.

    The ``files`` block is explicit (and uncapped, so the reader takes the
    fast path) which pins the category of each file exactly, independently of
    the crawler's extension heuristics. Both files really exist on disk, so the
    content read under test is a real read.
    """
    project = Path(tmpdir)
    pkg = project / 'pkg'
    _write(pkg / 'lib.py', f'{_SHARED_TOKEN} = 1\n')
    _write(pkg / 'notes.md', f'# {_SHARED_TOKEN}\n')

    modules = {
        'pkg': {
            'name': 'pkg',
            'paths': {'module': 'pkg'},
            'files': {'source': ['pkg/lib.py'], _SECOND_CATEGORY: ['pkg/notes.md']},
        },
    }
    seed_project(tmpdir, modules)


def _seed_unreadable_project(tmpdir: str) -> None:
    """Seed one readable file plus the two unreadable shapes.

    ``pkg/blob.bin`` holds bytes that are not valid UTF-8 (the decode arm) and
    ``pkg/ghost.py`` is declared in the inventory but never created on disk (the
    OS-error arm). Both must be REPORTED in ``unreadable[]`` rather than
    silently dropped.
    """
    project = Path(tmpdir)
    pkg = project / 'pkg'
    _write(pkg / 'good.py', f'{_SHARED_TOKEN} = 1\n')
    (pkg / 'blob.bin').write_bytes(b'\xff\xfe\x00\x80' + _SHARED_TOKEN.encode('utf-8'))

    modules = {
        'pkg': {
            'name': 'pkg',
            'paths': {'module': 'pkg'},
            'files': {'source': ['pkg/good.py', 'pkg/blob.bin', 'pkg/ghost.py']},
        },
    }
    seed_project(tmpdir, modules)


def _search(tmpdir: str, pattern: str, *, category: str | None = None, literal: bool = False) -> dict:
    """Invoke ``cmd_search`` with the argparse namespace the CLI would build."""
    result: dict = cmd_search(
        Namespace(project_dir=tmpdir, pattern=pattern, category=category, literal=literal, content=True)
    )
    return result


def test_body_hit_is_found_by_search_and_missed_by_find():
    """The gap ``find`` cannot close: a hit in the BODY, not in the path.

    The negative half is the point — running the identical pattern through
    ``cmd_find`` over the SAME fixture proves the new verb is answering a
    question the existing one genuinely cannot, so this test cannot pass by
    accident if ``search`` silently degraded into a path glob.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        found = _search(tmpdir, _BODY_ONLY_TOKEN)

        assert found['status'] == 'success'
        assert found['count'] == 1
        assert found['results'][0]['path'] == 'pkg/alpha.py'
        assert found['results'][0]['match_count'] == 1

        # Control: the same token as a path glob finds nothing — the token
        # appears in no path anywhere in the fixture.
        missed = cmd_find(Namespace(project_dir=tmpdir, pattern=f'*{_BODY_ONLY_TOKEN}*', category=None))
        assert missed['status'] == 'success'
        assert missed['count'] == 0


def test_untracked_file_is_searched():
    """An untracked-but-not-ignored file is searched — the anti-``git grep`` property.

    The fixture directory is not a git worktree at all, so nothing in it could
    be tracked; a ``git grep``-backed implementation would return nothing here.
    The explicit no-``.git`` precondition keeps that claim honest rather than
    incidental.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        # Precondition: no git worktree, so "untracked" is true by construction.
        assert not (Path(tmpdir) / '.git').exists()

        result = _search(tmpdir, _UNTRACKED_TOKEN)

        assert result['status'] == 'success'
        assert result['count'] == 1
        assert result['results'][0]['path'] == 'pkg/untracked_only.py'


def test_match_count_is_a_real_count_not_a_hit_flag():
    """A file containing the pattern three times reports ``match_count: 3``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        result = _search(tmpdir, _TRIPLE_TOKEN)

        assert result['status'] == 'success'
        assert result['count'] == 1
        assert result['results'][0]['path'] == 'pkg/triple.py'
        # The discriminating assertion: 3, never 1 (a truthy "it matched" flag).
        assert result['results'][0]['match_count'] == 3


def test_caret_anchors_to_line_start_not_file_start():
    """``^`` means line-start, the semantics grep/ripgrep/Grep already give it.

    The fixture is built so the pre-``re.MULTILINE`` implementation cannot pass:
    ``_ANCHOR_TOKEN`` starts lines 2 and 3 of ``pkg/anchored.py`` and never line
    1, so a whole-body compile anchors ``^`` at byte 0 and answers ``count: 0``
    over a fully-scanned corpus — the confident negative this pins against.

    Two controls keep a green result honest. The unanchored arm proves the token
    population is non-empty and strictly LARGER than the anchored subset, so the
    anchored count cannot be explained by the token simply being everywhere. The
    ``pkg/midline.py`` exclusion proves the anchor still BINDS — had the fix
    dropped anchoring altogether, that file would appear and this test would
    fail for the right reason.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        anchored = _search(tmpdir, f'^{_ANCHOR_TOKEN}')

        assert anchored['status'] == 'success'
        assert anchored['count'] == 1
        assert anchored['results'][0]['path'] == 'pkg/anchored.py'
        # match_count stays a real count under re.MULTILINE: two line-start
        # occurrences report 2, never a first-hit short-circuit to 1.
        assert anchored['results'][0]['match_count'] == 2
        assert anchored['files_scanned'] > 0

        # Control: unanchored, the same token also lives mid-line in a second
        # file — so the anchored arm above really did narrow the result.
        unanchored = _search(tmpdir, _ANCHOR_TOKEN)
        assert unanchored['count'] == 2
        assert {entry['path'] for entry in unanchored['results']} == {
            'pkg/anchored.py',
            'pkg/midline.py',
        }


def test_dollar_anchors_to_line_end_not_file_end():
    """``$`` means line-end — the ``^`` assertion's sibling half.

    ``_ENDLINE_TOKEN`` ends line 1 of a two-line file, so a whole-body compile
    (where ``$`` means end-of-file) matches nothing. The unanchored control
    confirms the token is present at all, so a green anchored arm is a real
    line-end match rather than an empty population.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        anchored = _search(tmpdir, f'{_ENDLINE_TOKEN}$')

        assert anchored['status'] == 'success'
        assert anchored['count'] == 1
        assert anchored['results'][0]['path'] == 'pkg/dollar.py'
        assert anchored['results'][0]['match_count'] == 1

        # Control: the token is genuinely in the corpus, so the anchored hit is
        # not an accident of an otherwise-empty search.
        unanchored = _search(tmpdir, _ENDLINE_TOKEN)
        assert unanchored['count'] == 1
        assert unanchored['results'][0]['path'] == 'pkg/dollar.py'


def test_results_carry_no_line_bodies_or_line_numbers():
    """The payload boundary: exactly four keys per hit, never the matching lines.

    Pins the settled no-lines decision structurally. Key-set EQUALITY (rather
    than a spot-check for one forbidden name) is what makes this catch any
    future line/lineno/snippet field, not just the ones imagined today.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        result = _search(tmpdir, _TRIPLE_TOKEN)

        assert result['count'] == 1
        for entry in result['results']:
            assert set(entry) == _RESULT_KEYS
        # No response-level echo of the mode either — ``--content`` is the only
        # mode today, so a constant-valued key would be vacuous.
        assert 'mode' not in result


def test_metacharacter_pattern_matches_verbatim_under_literal():
    """Shell metacharacters are data, never code — and ``--literal`` is what makes them match.

    The regex arm is the paired control: the same string compiles as a valid
    regex and matches nothing, so a green literal arm cannot be explained by the
    pattern happening to work either way.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        literal = _search(tmpdir, _METACHAR_PATTERN, literal=True)

        assert literal['status'] == 'success'
        assert literal['literal'] is True
        assert literal['count'] == 1
        assert literal['results'][0]['path'] == 'pkg/meta.py'

        # Control: compiled as a regex the same string is valid but matches
        # nothing ('$' anchors, so the trailing characters can never follow).
        as_regex = _search(tmpdir, _METACHAR_PATTERN, literal=False)
        assert as_regex['status'] == 'success'
        assert as_regex['literal'] is False
        assert as_regex['count'] == 0


def test_invalid_regex_is_an_error_not_a_confident_zero():
    """An uncompilable pattern errors out instead of answering ``count: 0``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        result = _search(tmpdir, '[unclosed')

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_pattern'
        assert result['pattern'] == '[unclosed'
        assert result['message']
        # Anti-shape: never a confident count alongside a broken pattern.
        assert 'count' not in result


def test_invalid_regex_is_accepted_when_escaped_by_literal():
    """The same uncompilable pattern is a legitimate query under ``--literal``.

    Proves ``--literal`` escapes BEFORE compiling rather than merely relaxing
    the match, and keeps the error arm above from reading as "'[' is always
    rejected".
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        _write(project / 'pkg' / 'brackets.py', 'value = "[unclosed"\n')
        modules = {'pkg': {'name': 'pkg', 'paths': {'module': 'pkg'}}}
        _post_process_files(modules, str(project))
        seed_project(tmpdir, modules)

        result = _search(tmpdir, '[unclosed', literal=True)

        assert result['status'] == 'success'
        assert result['count'] == 1
        assert result['results'][0]['path'] == 'pkg/brackets.py'


def test_category_narrows_the_searched_set():
    """``--category`` restricts the search to one bucket."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_two_category_project(tmpdir)

        # Precondition: the narrowing category is a real member of the vocabulary.
        assert _SECOND_CATEGORY in FILE_CATEGORIES

        unfiltered = _search(tmpdir, _SHARED_TOKEN)
        assert unfiltered['count'] == 2
        assert {entry['category'] for entry in unfiltered['results']} == {'source', _SECOND_CATEGORY}

        narrowed = _search(tmpdir, _SHARED_TOKEN, category='source')
        assert narrowed['status'] == 'success'
        assert narrowed['category'] == 'source'
        assert narrowed['count'] == 1
        assert narrowed['results'][0]['path'] == 'pkg/lib.py'
        # Narrowing also shrinks what was READ, not just what was reported.
        assert narrowed['files_scanned'] == 1


def test_unknown_category_is_an_error_advertising_the_vocabulary():
    """An out-of-vocabulary ``--category`` errors instead of answering ``count: 0``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_two_category_project(tmpdir)

        result = _search(tmpdir, _SHARED_TOKEN, category=_UNKNOWN_CATEGORY)

        assert result['status'] == 'error'
        assert result['error'] == 'unknown_category'
        assert result['category'] == _UNKNOWN_CATEGORY
        assert result['valid_categories'] == sorted(FILE_CATEGORIES)
        # Anti-shape: never the confident zero count.
        assert 'count' not in result


def test_absent_token_reports_how_much_was_actually_searched():
    """``count: 0`` is qualified by ``files_scanned``, so it is never bare.

    The anti-vacuity assertion: without ``files_scanned`` a zero from "the
    corpus does not contain it" is indistinguishable from a zero from "nothing
    was searched at all".
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        result = _search(tmpdir, _ABSENT_TOKEN)

        assert result['status'] == 'success'
        assert result['count'] == 0
        assert result['results'] == []
        # The discriminator: files really were read and the token really is absent.
        assert result['files_scanned'] > 0
        assert result['truncated'] is False
        assert result['elided'] == []
        assert result['unreadable'] == []


def test_unreadable_files_are_reported_not_silently_dropped():
    """A file skipped for a decode or OS error lands in ``unreadable[]``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_unreadable_project(tmpdir)

        result = _search(tmpdir, _SHARED_TOKEN)

        assert result['status'] == 'success'
        assert result['count'] == 1
        assert result['results'][0]['path'] == 'pkg/good.py'

        reported = {entry['path']: entry['reason'] for entry in result['unreadable']}
        assert reported == {'pkg/blob.bin': 'decode_error', 'pkg/ghost.py': 'os_error'}
        # Only the one readable file was actually scanned — the skipped files
        # are excluded from the scanned count rather than inflating it.
        assert result['files_scanned'] == 1


def test_cli_rejects_search_without_the_content_mode_flag():
    """``search --pattern X`` without ``--content`` is rejected at parse time.

    Driven through the real argparse dispatch at the subprocess boundary, so it
    pins the shipped CLI contract rather than a handler-level convention: the
    mode stays explicit at every call site instead of silently defaulting.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        rejected = run_script(
            _ARCHITECTURE_SCRIPT, '--project-dir', tmpdir, 'search', '--pattern', _BODY_ONLY_TOKEN
        )

        assert not rejected.success
        assert '--content' in (rejected.stdout + rejected.stderr)


def test_cli_search_with_content_returns_the_body_hit():
    """The positive control for the rejection above — the same call plus ``--content`` succeeds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_crawled_project(tmpdir)

        accepted = run_script(
            _ARCHITECTURE_SCRIPT,
            '--project-dir',
            tmpdir,
            'search',
            '--content',
            '--pattern',
            _BODY_ONLY_TOKEN,
        )

        assert accepted.success, accepted.stderr
        data = accepted.toon()
        assert data['status'] == 'success'
        assert int(data['count']) == 1
