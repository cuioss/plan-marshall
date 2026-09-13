#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Axis-D claimed-path de-duplication precedence (D2).

``_collapse_claimed_duplicate_rows`` is the reader-side precedence that makes one
physical file yield one row from ``find`` / ``search`` when it is inventoried by
more than one module (the documentation corpus, walked by both the ``documentation``
module and the project-root crawl). The precedence is keyed on the ownership CLAIM,
so it collapses exactly the claimed corpus and leaves an unclaimed duplicate — a
marketplace ``SKILL.md`` in both its bundle and the root — untouched.

The collapse is unit-tested directly against synthetic result rows with a stubbed
attribution resolver, so each rule is pinned in isolation without seeding a whole
fixture project.

``project_dir`` is a required third argument of the collapse, threaded straight
through to the attribution seam, which is keyed on ``(project_dir,
module_names)``. Every test here stubs that seam and asserts on row precedence
alone, so each call passes ``'.'`` and each stub accepts the argument and ignores
it — no test in this file depends on which project dir was threaded.
"""

from conftest import load_script_module

_handlers = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_handlers.py', '_cmd_client_handlers'
)

_PROJECT_DIR = '.'


def _stub_attribution(owner_by_path):
    """Return a resolve_path_attribution stand-in driven by a path→owner map."""

    def _resolve(path, _module_names, _project_dir):
        return owner_by_path.get(path), []

    return _resolve


def _rows(*triples):
    return [{'module': m, 'category': c, 'path': p} for m, c, p in triples]


def test_claimed_duplicate_collapses_to_owner(monkeypatch):
    monkeypatch.setattr(_handlers, 'resolve_path_attribution', _stub_attribution({'doc/x.adoc': 'documentation'}))
    rows = _rows(
        ('default', 'doc', 'doc/x.adoc'),
        ('documentation', 'doc', 'doc/x.adoc'),
    )
    out = _handlers._collapse_claimed_duplicate_rows(rows, ['default', 'documentation'], _PROJECT_DIR)
    assert out == [{'module': 'documentation', 'category': 'doc', 'path': 'doc/x.adoc'}]


def test_single_row_claimed_path_unchanged(monkeypatch):
    """A claimed path with one row keeps it — and that row still names the CRAWLER.

    ``README.md`` is the worked example, and the consequence is the one a caller
    most easily misreads. The ``documentation`` module CLAIMS the repo-root prose
    docs but does not walk them, so the only inventory row for ``README.md`` comes
    from the project-root crawl. The collapse picks the owner's row **only when
    the owner inventoried the path**; here it did not, so there is nothing to
    collapse onto and the lone crawled row survives unchanged — it is never
    rewritten to name the owner.

    Therefore a ``find`` / ``search`` row's ``module`` names the **inventorying**
    module, NOT the owner, and a caller that needs ownership must ask
    ``which-module`` — the authoritative answer — rather than reading ``module``
    off a result row. Dropping the row instead (the alternative to leaving it
    intact) would lose the path from the inventory altogether, which is why the
    single-row case is guarded separately from the duplicate case above.
    """
    monkeypatch.setattr(_handlers, 'resolve_path_attribution', _stub_attribution({'README.md': 'documentation'}))
    rows = _rows(('default', 'doc', 'README.md'))
    out = _handlers._collapse_claimed_duplicate_rows(rows, ['default', 'documentation'], _PROJECT_DIR)
    assert out == [{'module': 'default', 'category': 'doc', 'path': 'README.md'}]


def test_unclaimed_duplicate_left_untouched(monkeypatch):
    # An unclaimed marketplace duplicate is out of scope — both rows survive.
    monkeypatch.setattr(_handlers, 'resolve_path_attribution', _stub_attribution({}))
    rows = _rows(
        ('default', 'doc', 'marketplace/bundles/pm-dev-java/skills/x/SKILL.md'),
        ('pm-dev-java', 'skill', 'marketplace/bundles/pm-dev-java/skills/x/SKILL.md'),
    )
    out = _handlers._collapse_claimed_duplicate_rows(rows, ['default', 'pm-dev-java'], _PROJECT_DIR)
    assert len(out) == 2


def test_owner_not_among_rows_left_untouched(monkeypatch):
    # If the claimed owner is not among a duplicate's rows, the reader has no owner
    # row to collapse onto and must never drop the path.
    monkeypatch.setattr(_handlers, 'resolve_path_attribution', _stub_attribution({'doc/y.adoc': 'documentation'}))
    rows = _rows(
        ('default', 'doc', 'doc/y.adoc'),
        ('other', 'doc', 'doc/y.adoc'),
    )
    out = _handlers._collapse_claimed_duplicate_rows(rows, ['default', 'other'], _PROJECT_DIR)
    assert len(out) == 2


def test_match_count_preserved_for_search_rows(monkeypatch):
    monkeypatch.setattr(_handlers, 'resolve_path_attribution', _stub_attribution({'doc/x.adoc': 'documentation'}))
    rows = [
        {'module': 'default', 'category': 'doc', 'path': 'doc/x.adoc', 'match_count': 3},
        {'module': 'documentation', 'category': 'doc', 'path': 'doc/x.adoc', 'match_count': 3},
    ]
    out = _handlers._collapse_claimed_duplicate_rows(rows, ['default', 'documentation'], _PROJECT_DIR)
    assert out == [{'module': 'documentation', 'category': 'doc', 'path': 'doc/x.adoc', 'match_count': 3}]


def test_no_attributor_leaves_all_rows(monkeypatch):
    # attributor_count 0 (owner None) is the no-capability case: nothing collapses.
    monkeypatch.setattr(_handlers, 'resolve_path_attribution', lambda _p, _m, _d: (None, []))
    rows = _rows(
        ('default', 'doc', 'doc/x.adoc'),
        ('documentation', 'doc', 'doc/x.adoc'),
    )
    out = _handlers._collapse_claimed_duplicate_rows(rows, ['default', 'documentation'], _PROJECT_DIR)
    assert len(out) == 2
