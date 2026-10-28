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
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import target_context
from _flat_install_fixtures import LOCATION_ENV_VARS as _LOCATION_ENV_VARS

from conftest import MARKETPLACE_ROOT, load_script_module

_SKILL_NAME = 'runbook-lane'
_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / _SKILL_NAME

#: Every platform env signal the runtime detector reads, taken from the detector's
#: own declaration so a new signal cannot stay active in the subprocess paths.
_SIGNALS = tuple(signal for signal, _target in target_context.TARGET_ENV_SIGNALS)

#: The phrase the reason must carry: the verdict is safe BECAUSE the executor
#: dispatches the checkout's own scripts, not because the versions happened to
#: line up.
_OWN_SCRIPTS_PHRASE = "the checkout's own scripts"

ge = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py', register=False)


def _lane_module():
    """Load the lane script fresh, publishing nothing."""
    return load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)


def _executor(tmp_path: Path, version: str | None) -> Path:
    """Write a minimal executor carrying ``version`` (``None``: no assignment)."""
    path = tmp_path / 'execute-script.py'
    path.write_text('' if version is None else f"MARSHALL_VERSION = '{version}'\n", encoding='utf-8')
    return path


def _source_checkout(tmp_path: Path, *, version_dir: str | None = None, with_skill: bool = False) -> Path:
    """Lay out a source checkout and return its lane skill directory.

    The source shape is a bundle carrying ``.claude-plugin/plugin.json`` DIRECTLY
    under it — the same manifest ``marketplace/bundles/plan-marshall`` holds. The
    bundle's own ``skills/`` directory is therefore a nested bundle skill root, so
    the flat leg cannot claim it.

    Args:
        tmp_path: Base directory of the fixture.
        version_dir: When set, also lay out ``{bundle}/{version_dir}/`` carrying a
            plugin-cache-shaped bundle manifest.
        with_skill: When set with ``version_dir``, that version directory also
            carries the lane skill, which makes it the leg that answers.
    """
    bundle = tmp_path / 'checkout' / 'marketplace' / 'bundles' / 'plan-marshall'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{}\n', encoding='utf-8')
    lane = bundle / 'skills' / _SKILL_NAME
    lane.mkdir(parents=True)
    (lane / 'SKILL.md').write_text(f'---\nname: {_SKILL_NAME}\n---\n\n# Runbook Lane\n', encoding='utf-8')
    if version_dir is not None:
        versioned = bundle / version_dir
        (versioned / '.claude-plugin').mkdir(parents=True)
        (versioned / '.claude-plugin' / 'plugin.json').write_text('{}\n', encoding='utf-8')
        if with_skill:
            versioned_lane = versioned / 'skills' / _SKILL_NAME
            versioned_lane.mkdir(parents=True)
            (versioned_lane / 'SKILL.md').write_text(
                f'---\nname: {_SKILL_NAME}\n---\n\n# Runbook Lane\n', encoding='utf-8'
            )
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


def test_a_source_checkout_this_run_does_not_execute_cannot_check(tmp_path: Path) -> None:
    """A source checkout probed from elsewhere judges text this run's mapped script may not match."""
    lane = _source_checkout(tmp_path)

    data = _skew_result(_executor(tmp_path, '0.1.2025'), lane)

    assert data['verdict'] == 'could_not_check'
    assert data['verdict'] != 'match', 'an unmakeable comparison must never be reported as agreement'
    assert 'is not the checkout this run executes' in str(data['reason'])


def test_another_skill_in_the_same_bundle_is_not_excused(tmp_path: Path) -> None:
    """Bundle membership is not enough: only the skill directory this run executes counts."""
    lane = _source_checkout(tmp_path)
    sibling = lane.parent / 'other-lane'
    sibling.mkdir()
    (sibling / 'SKILL.md').write_text('---\nname: other-lane\n---\n\n# Other Lane\n', encoding='utf-8')

    data = _skew_result(_executor(tmp_path, '0.1.2025'), sibling)

    assert data['verdict'] == 'could_not_check'
    assert 'is not the checkout this run executes' in str(data['reason'])


def test_source_checkout_is_probed_not_assumed(tmp_path: Path) -> None:
    """The layout comes from the bundle's own shape, not from its directory name."""
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


def test_a_live_version_directory_still_wins_over_the_direct_manifest(tmp_path: Path) -> None:
    """A version dir carrying this skill is compared, not excused, even beside a direct manifest."""
    lane = _source_checkout(tmp_path, version_dir='0.1.2024', with_skill=True)

    data = _skew_result(_executor(tmp_path, '0.1.2010'), lane)

    assert data['verdict'] == 'skew'
    assert data['lane_version'] == '0.1.2024'


def test_a_version_directory_without_this_skill_still_probes_as_the_source_copy(tmp_path: Path) -> None:
    """A version dir holding no copy of this skill leaves the mapping on the unversioned copy."""
    lane = _source_checkout(tmp_path, version_dir='0.1.2010')

    assert _lane_module()._lane_version_probe(lane).layout == 'source_checkout'


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
    """Every verdict the script can answer is named, with what the new one does NOT cover."""
    text = (_SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
    section = _skill_section(text, '### executor-skew')

    # Derived from the implementation, never a list kept in step by hand: a verdict
    # added to the script but not to the doc fails this test.
    verdicts = sorted(value for name, value in vars(_lane_module()).items() if name.startswith('_EXECUTOR_SKEW_'))
    assert verdicts, 'the lane script declares no verdicts'
    for verdict in verdicts:
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


# -----------------------------------------------------------------------------
# The verdict on the path a lane takes: through an executor mapped into a
# source checkout
# -----------------------------------------------------------------------------


def _source_checkout_bundles(tmp_path: Path) -> Path:
    """Copy the real bundle tree into a disposable source checkout, and return its root.

    A copy rather than the working tree, so the mapping the executor embeds is
    PROVABLY the fixture's (asserted below) and the test cannot pass on a tree
    that happens to be a source checkout for another reason.
    """
    bundles = tmp_path / 'checkout' / 'marketplace' / 'bundles'
    shutil.copytree(MARKETPLACE_ROOT, bundles, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return bundles


def _generate_executor(
    monkeypatch: pytest.MonkeyPatch,
    plan_dir: Path,
    marketplace_root: Path,
    roots: tuple[tuple[str, str], ...],
    versions: tuple[tuple[str, str], ...],
) -> Path:
    """Generate a real executor whose OpenCode install is ``roots`` at ``versions``."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    for signal in _SIGNALS:
        monkeypatch.delenv(signal, raising=False)
    monkeypatch.setattr(ge, 'installed_harness_roots', lambda: list(roots))
    monkeypatch.setattr(ge, 'installed_harness_versions', lambda _roots=None: list(versions))
    result = ge.generate_executor({}, marketplace_root, dry_run=False, target='opencode')
    assert result['status'] == 'success', result
    executor = plan_dir / 'execute-script.py'
    assert executor.is_file()
    return executor


def _run_skew(
    executor: Path,
    project_dir: Path,
    lane_dir: Path,
    *,
    executor_arg: Path | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the verb through ``executor`` as an OpenCode call against ``lane_dir``.

    Every location variable a flat-install fixture scrubs is scrubbed here too: an
    ambient ``PM_MARKETPLACE_ROOT`` (or a plan base) would let the generated
    executor resolve this checkout's tree instead of its own mapping, and the test
    would then prove nothing about a fixture it did not run.

    ``cwd`` is the fixture's checkout ROOT when a test needs the executor's own
    upward walk to find the fixture rather than the repository that hosts the
    pytest basetemp. ``--executor`` is then passed explicitly, because the default
    is resolved relative to the cwd.
    """
    env = {key: value for key, value in os.environ.items() if key not in _SIGNALS}
    for variable in _LOCATION_ENV_VARS:
        env.pop(variable, None)
    env['OPENCODE'] = '1'
    env['PLAN_MARSHALL_HOME'] = str(project_dir / '.machine-home')
    command = [
        sys.executable,
        str(executor),
        'plan-marshall:runbook-lane:runbook_lane',
        'executor-skew',
        '--lane-dir',
        str(lane_dir),
    ]
    if executor_arg is not None:
        command.extend(['--executor', str(executor_arg)])
    return subprocess.run(command, cwd=cwd or project_dir, env=env, capture_output=True, text=True, timeout=300)


def test_executor_skew_answers_not_applicable_through_the_executor(tmp_path, monkeypatch) -> None:
    """A lane whose executor maps a source checkout reaches the new verdict end to end.

    The executor sits inside the fixture checkout (``{fixture}/.plan``), so the
    executor's own upward tree probe finds the fixture rather than the repository
    that hosts the pytest basetemp — the script the verdict judges is then the copy
    it runs.
    """
    bundles = _source_checkout_bundles(tmp_path)
    checkout = bundles.parent.parent
    executor = _generate_executor(
        monkeypatch,
        checkout / '.plan',
        marketplace_root=bundles,
        roots=(('opencode', str(tmp_path / 'opencode' / 'skills')),),
        versions=(('opencode', '0.1.2025'),),
    )
    assert str(bundles) in executor.read_text(encoding='utf-8'), 'the mapping does not point into the fixture'

    result = _run_skew(
        executor,
        checkout,
        bundles / 'plan-marshall' / 'skills' / _SKILL_NAME,
        executor_arg=executor,
        cwd=checkout,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'verdict: not_applicable' in result.stdout, result.stdout + result.stderr
    assert 'verdict: could_not_check' not in result.stdout, result.stdout + result.stderr
    assert _OWN_SCRIPTS_PHRASE in result.stdout
    assert 'remedy:' not in result.stdout, 'an unmakeable comparison must not claim the executor is stale'


def test_executor_skew_cannot_check_through_the_executor_when_it_is_removed(tmp_path, monkeypatch) -> None:
    """Removing the executor is a failed read, not a source-checkout verdict."""
    bundles = _source_checkout_bundles(tmp_path)
    checkout = bundles.parent.parent
    executor = _generate_executor(
        monkeypatch,
        checkout / '.plan',
        marketplace_root=bundles,
        roots=(('opencode', str(tmp_path / 'opencode' / 'skills')),),
        versions=(('opencode', '0.1.2025'),),
    )

    result = _run_skew(
        executor,
        checkout,
        bundles / 'plan-marshall' / 'skills' / _SKILL_NAME,
        executor_arg=checkout / '.plan' / 'removed-execute-script.py',
        cwd=checkout,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'verdict: could_not_check' in result.stdout, result.stdout + result.stderr
    assert 'executor version unreadable' in result.stdout
