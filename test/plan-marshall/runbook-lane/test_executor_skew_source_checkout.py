#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The executor-skew check answers ``not_applicable`` in a source checkout.

In a plan-marshall source checkout the executor maps every notation to the
checkout's own ``marketplace/bundles/...`` tree, and the lane text is that same
checkout's text. The comparison exists to catch a lane text that names a verb its
mapped script does not have; in a source checkout the two are one tree, so the
comparison can change nothing — and it cannot be made either, because neither the
versioned nor the flat leg finds a version there.

The verdict is therefore a distinct ``not_applicable``, never ``match``: the
comparison was not made, and saying it agreed would be a claim nobody earned. The
lane proceeds without asking the operator a question that cannot change the
outcome. ``skew`` and ``could_not_check`` are unchanged everywhere else — a stale
executor in a versioned cache, a flat install without a usable stamp, and an
unreadable executor all still stop the run.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

_SKILL_NAME = 'runbook-lane'
_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / _SKILL_NAME

#: The phrase the reason must carry: the verdict is safe BECAUSE the executor
#: dispatches the checkout's own scripts, not because the versions happened to
#: line up.
_OWN_SCRIPTS_PHRASE = "this source checkout's own scripts"


def _lane_module():
    """Load the lane script fresh, publishing nothing."""
    return load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)


def _executor(tmp_path: Path, version: str | None) -> Path:
    """Write a minimal executor carrying ``version`` (``None``: no assignment)."""
    path = tmp_path / 'execute-script.py'
    path.write_text('' if version is None else f"MARSHALL_VERSION = '{version}'\n", encoding='utf-8')
    return path


def _source_checkout(tmp_path: Path, *, version_dir: str | None = None) -> Path:
    """Lay out a source checkout and return its lane skill directory.

    The source shape is a bundle carrying ``.claude-plugin/plugin.json`` DIRECTLY
    under it — the same manifest ``marketplace/bundles/plan-marshall`` holds. The
    bundle's own ``skills/`` directory is therefore a nested bundle skill root, so
    the flat leg cannot claim it.

    Args:
        tmp_path: Base directory of the fixture.
        version_dir: When set, also lay out ``{bundle}/{version_dir}/`` carrying a
            bundle manifest and the lane skill — the hybrid tree that must NOT be
            read as a source checkout.
    """
    bundle = tmp_path / 'checkout' / 'marketplace' / 'bundles' / 'plan-marshall'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{}\n', encoding='utf-8')
    lane = bundle / 'skills' / _SKILL_NAME
    lane.mkdir(parents=True)
    (lane / 'SKILL.md').write_text(f'---\nname: {_SKILL_NAME}\n---\n\n# Runbook Lane\n', encoding='utf-8')
    if version_dir is not None:
        stale = bundle / version_dir
        (stale / '.claude-plugin').mkdir(parents=True)
        (stale / '.claude-plugin' / 'plugin.json').write_text('{}\n', encoding='utf-8')
    return lane


def _skew_result(executor: Path, lane_dir: Path) -> dict[str, object]:
    """Run the verb in-process against ``lane_dir`` and return its payload."""
    payload: dict[str, object] = _lane_module().cmd_executor_skew(
        argparse.Namespace(executor=str(executor), lane_dir=str(lane_dir))
    )
    return payload


# -----------------------------------------------------------------------------
# A source checkout answers its own verdict
# -----------------------------------------------------------------------------


def test_source_checkout_answers_not_applicable_and_never_match(tmp_path: Path) -> None:
    """The checkout's own scripts make the comparison unnecessary, not equal."""
    lane = _source_checkout(tmp_path)

    data = _skew_result(_executor(tmp_path, '0.1.2025'), lane)

    assert data['verdict'] == 'not_applicable'
    assert data['verdict'] != 'match', 'an unmakeable comparison must never be reported as agreement'
    assert _OWN_SCRIPTS_PHRASE in str(data['reason'])
    assert 'source checkout' in str(data['reason'])


def test_source_checkout_is_probed_not_assumed(tmp_path: Path) -> None:
    """The verdict comes from the bundle's own layout, not from its directory name."""
    lane = _source_checkout(tmp_path)

    module = _lane_module()

    assert module._lane_version_probe(lane).layout == 'source_checkout'
    assert module._lane_text_version(lane) is None, 'the version is still unread, so it stays None'


def test_source_checkout_with_an_unreadable_executor_cannot_check(tmp_path: Path) -> None:
    """A source checkout explains an unmakeable comparison, not a broken executor."""
    lane = _source_checkout(tmp_path)

    data = _skew_result(tmp_path / 'absent-execute-script.py', lane)

    assert data['verdict'] == 'could_not_check'
    assert data['reason'] == 'executor version unreadable'


def test_a_bundle_that_also_carries_a_version_directory_is_not_a_source_checkout(tmp_path: Path) -> None:
    """The source shape means the manifest directly under the bundle AND no version dir."""
    lane = _source_checkout(tmp_path, version_dir='0.1.2010')

    data = _skew_result(_executor(tmp_path, '0.1.2025'), lane)

    assert data['verdict'] == 'could_not_check', 'a version-carrying bundle is a cache, not a source checkout'
    assert data['reason'] == f'lane text version unknown: no version directory under {lane.parents[1]}'


def test_source_checkout_in_this_checkout_answers_not_applicable(tmp_path: Path) -> None:
    """This repository IS a source checkout, so its own lane text answers the new verdict."""
    data = _skew_result(_executor(tmp_path, '0.1.2025'), _SKILL_DIR)

    assert data['verdict'] == 'not_applicable'
    assert _OWN_SCRIPTS_PHRASE in str(data['reason'])


# -----------------------------------------------------------------------------
# The lane text states every verdict a run can reach
# -----------------------------------------------------------------------------


def _skill_section(text: str, heading: str) -> str:
    """Return one heading's prose, whitespace-normalised, up to the next ``##``/``###``."""
    start = text.index(heading)
    rest = text[start + len(heading) :]
    following = re.search(r'\n#{2,3} ', rest)
    end = following.start() if following else -1
    return ' '.join((heading + (rest if end == -1 else rest[:end])).split())


def test_skill_states_every_executor_skew_verdict() -> None:
    """Every verdict a lane can reach is named, with what the new one does NOT cover."""
    text = (_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
    section = _skill_section(text, '### executor-skew')

    for verdict in ('match', 'skew', 'not_applicable', 'could_not_check'):
        assert f'`{verdict}`' in section, f'the executor-skew section does not name the {verdict} verdict'
    assert 'source checkout' in section
    assert 'own scripts' in section, 'the source-checkout verdict states no reason it is safe'
    assert 'template' in section, 'the source-checkout verdict does not say what it leaves uncovered'
    assert 'records the verdict' in section, 'the source-checkout verdict is not recorded in the landing'
    assert 'never read as' in section, 'could_not_check is not distinguished from no skew'


def test_input_section_sends_the_source_checkout_verdict_on() -> None:
    """Section 0 says what a lane does on each verdict it can reach."""
    text = (_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
    section = _skill_section(text, '## 0. Input')

    assert '`not_applicable`' in section
    assert 'proceeds' in section
