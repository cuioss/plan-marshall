#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A ``.plan/`` citation is confined to the graded plan's build-results tree.

Three behaviours:

* a citation that climbs out of ``.plan/`` into the checkout is refused even when
  the file it names exists;
* a self-written ``.plan/temp`` file is refused as evidence;
* a build log under the plan's OWN ``build-results`` directory is accepted (the
  positive control), while another plan's log is not.
"""

from __future__ import annotations

import _review_support_validate as _validate
import pytest

PLAN_ID = 'lb74-plan-citation-d4'
OTHER_PLAN = 'some-other-plan'


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    """A checkout whose ``.plan/local`` tree is the plan store the resolver reads."""
    root = tmp_path / 'checkout'
    base = root / '.plan' / 'local'
    (base / 'plans' / PLAN_ID / 'build-results' / 'default').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    monkeypatch.setattr(_validate, 'cwd_checkout_root', lambda: str(root), raising=False)
    return root


def test_a_citation_escaping_the_plan_directory_is_refused(checkout) -> None:
    source = checkout / 'src' / 'x.py'
    source.parent.mkdir()
    source.write_text('def test_x():\n    assert 1 == 1\n', encoding='utf-8')

    assert _validate.missing_evidence(checkout, ['.plan/../src/x.py'], PLAN_ID) == ['.plan/../src/x.py']


def test_a_self_written_temp_citation_is_refused(checkout) -> None:
    note = checkout / '.plan' / 'temp' / 'note.txt'
    note.parent.mkdir(parents=True)
    note.write_text('a note I wrote myself\n', encoding='utf-8')

    assert _validate.missing_evidence(checkout, ['.plan/temp/note.txt'], PLAN_ID) == ['.plan/temp/note.txt']


def test_a_build_log_under_the_plans_own_build_results_is_accepted(checkout) -> None:
    log = checkout / '.plan' / 'local' / 'plans' / PLAN_ID / 'build-results' / 'default' / 'python-1.log'
    log.write_text('collected 3 items\n', encoding='utf-8')
    citation = f'.plan/local/plans/{PLAN_ID}/build-results/default/python-1.log'

    assert _validate.missing_evidence(checkout, [citation], PLAN_ID) == []


def test_another_plans_build_log_is_refused(checkout) -> None:
    log = checkout / '.plan' / 'local' / 'plans' / OTHER_PLAN / 'build-results' / 'python-1.log'
    log.parent.mkdir(parents=True)
    log.write_text('collected 3 items\n', encoding='utf-8')
    citation = f'.plan/local/plans/{OTHER_PLAN}/build-results/python-1.log'

    assert _validate.missing_evidence(checkout, [citation], PLAN_ID) == [citation]
