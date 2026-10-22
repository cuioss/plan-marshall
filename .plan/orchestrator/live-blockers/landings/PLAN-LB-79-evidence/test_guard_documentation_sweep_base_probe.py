#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D4 base-probe: the sweep's D4 rows exercised against the PRE-FIX module.

The delivered module (`test_guard_documentation_sweep.py`) is the authority. This
probe states the same rows against the BASE checkout's module, and each fails for
a BEHAVIOURAL reason at the base sha:

* the sweep's wrapper words are the ONE shared table (``stdbuf``, ``ionice`` and
  the compound-command splice were missing);
* ``bash -c``, ``uv run`` and ``./pw`` lines are candidates, including a wrapper
  whose command string carries a ``cd`` and a separator;
* a refused documented invocation turned into a COMMENT is flagged;
* a named placeholder is also checked in its DEPLOYED spelling;
* the ``upgrade-flow.md`` PROSE recovery command is part of the swept set.
"""

from __future__ import annotations

import pathlib

import pytest
from _guard_node_harness import wrapper_table

import test_guard_documentation_sweep as sweep


def test_d4_wrapper_words_are_the_shared_table() -> None:
    table = wrapper_table().get('wrappers', {})
    assert table, 'the shared wrapper table is missing from the base checkout'
    assert sweep._WRAPPER_WORDS == frozenset(table), 'the sweep wrapper words are not the shared table'
    assert 'stdbuf' in sweep._WRAPPER_WORDS, 'stdbuf must join the sweep wrapper words'


@pytest.mark.parametrize(
    'command',
    [
        'bash -c "python3 -c x"',
        'uv run python -c x',
        './pw verify',
        'stdbuf -o0 python3 -c x',
        'zsh -c "cd /tmp; python3 -c x"',
        "watch 'cd /tmp && python3 -c x'",
    ],
    ids=['bash-c', 'uv-run', 'pw', 'stdbuf', 'zsh-compound', 'watch-compound'],
)
def test_d4_forms_are_candidates(command: str) -> None:
    assert sweep._is_candidate(command), f'{command!r} must be a swept candidate'


def test_d4_commented_candidate_is_flagged() -> None:
    """A refused invocation on a shell-fence comment line is collected AND flagged.

    The base module skips every comment line, so the fixture's commented
    invocation is not even a candidate.
    """
    import tempfile

    fixture = pathlib.Path(tempfile.mkdtemp(prefix='base-probe-')) / 'fixture.md'
    fixture.write_text('# Fixture\n\n```bash\n# python3 -c x\n```\n', encoding='utf-8')
    collector = getattr(sweep, 'collect_candidates_from', None)
    assert collector is not None, 'the base sweep cannot scan an explicit fixture path'
    candidates, _fenced = collector([(fixture, 'fixture.md')])
    assert candidates, 'a commented invocation must be collected'
    assert getattr(candidates[0], 'commented', False), 'the candidate must record that it is a comment'


def test_d4_deployed_spelling_is_checked() -> None:
    assert hasattr(sweep, '_deployed_paths'), 'the sweep must resolve the DEPLOYED spelling'


def test_d4_upgrade_flow_prose_is_swept() -> None:
    assert hasattr(sweep, 'collect_prose_candidates'), 'the sweep must scan the prose recovery command'
    path = pathlib.Path(sweep.REPO_ROOT) / (
        'marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md'
    )
    assert path.is_file(), f'the document under test is missing: {path}'
