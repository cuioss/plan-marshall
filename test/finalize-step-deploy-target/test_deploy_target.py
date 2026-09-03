#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract tests for the project-local ``project:finalize-step-deploy-target`` skill.

The skill is a markdown executor playbook backed by the multi-target
generator at ``marketplace/targets/generate.py``. These tests pin the
contract from three angles:

1. **Frontmatter and ordering** — the skill declares ``order: 81`` so
   the dispatcher places it post-merge after ``default:branch-cleanup``
   (70) and before ``project:finalize-step-sync-plugin-cache`` (85).
2. **Project-local registration** — the skill lives at
   ``.claude/skills/finalize-step-deploy-target/SKILL.md`` (NOT in any
   marketplace bundle, NOT in ``BUILT_IN_FINALIZE_STEPS``).
3. **Generator behaviour** — when the live generator runs against a
   fixture marketplace it exits ``0`` and prints a
   ``claude: produced {N} entries`` line to stdout with a non-zero
   ``{N}``; the executor reads its outcome from the exit code and its
   ``display_detail`` count from that line. The generator emits no
   machine-readable envelope, so the tests assert the exit code and the
   stdout line — the two signals the skill body is written against.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from _documented_example_scan import DEFECTIVE_GENERATOR_CALL
from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

_SKILL_MD = (
    PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-deploy-target' / 'SKILL.md'
)
_GENERATE_PY = PROJECT_ROOT / 'marketplace' / 'targets' / 'generate.py'

#: The invocation the skill prescribes. ``uv`` is installed only into the
#: project-local ``.pyprojectx/`` tree and is not on ``PATH``, so the wrapper
#: alias is the only form that runs from a normal shell.
_WRAPPER_INVOCATION = './pw generate-claude'

#: The prescription that cannot succeed as written — it exits 127 outside the
#: wrapper. Pinned as the COMMAND literal rather than as the bare words
#: ``uv run``, because the body legitimately names that form while explaining
#: why it is wrong, and a bare-word match would forbid the explanation too.
#: Imported rather than spelled: the repository-wide prescription guard sweeps
#: ``test/`` too, and a module that spells the literal reads to that guard as a
#: file prescribing it.
_DEFECTIVE_INVOCATION = DEFECTIVE_GENERATOR_CALL

#: The script segment the executor rejects with ``Unknown notation``. Its
#: diagnostic then suggests appending the typo as a subcommand, so the failure
#: sends a caller to fix something already correct.
_DEFECTIVE_NOTATION = 'manage_status'

_MANAGE_CONFIG_SCRIPTS_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)
if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))

import _config_defaults as cd  # noqa: E402


# ---------------------------------------------------------------------------
# 1) Frontmatter and ordering
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding='utf-8')
    match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    assert match is not None, f'frontmatter not found in {path}'
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            fm[key.strip()] = value.strip()
    return fm


def test_skill_md_exists():
    assert _SKILL_MD.is_file(), f'project-local finalize-step skill missing: {_SKILL_MD}'


def test_skill_frontmatter_has_canonical_fields():
    fm = _parse_frontmatter(_SKILL_MD)
    assert fm.get('name') == 'finalize-step-deploy-target'
    assert fm.get('description'), 'description must be non-empty'
    assert fm.get('order') == '81', (
        'deploy-target order must be 81 (post-merge: after branch-cleanup=70, '
        'before sync-plugin-cache=85)'
    )


def test_skill_body_documents_inline_only_and_no_skip_detector():
    text = _SKILL_MD.read_text(encoding='utf-8')
    flat = re.sub(r'\s+', ' ', text.lower())
    assert 'inline-only' in flat or 'inline only' in flat
    assert 'no skip detector' in flat, (
        'standard must explicitly state there is no skip detector — generator handles no-op'
    )
    # Generator command must appear verbatim
    assert _WRAPPER_INVOCATION in text
    # display_detail template must carry the count the produced-line supplies
    assert 'files emitted to target/claude/' in text


def test_skill_body_prescribes_no_command_that_fails_as_written():
    """Neither defective prescription the skill once carried may reappear.

    Both failed when run as written and both named the wrong culprit: the bare
    generator line exits 127 because ``uv`` is not on ``PATH``, and the
    underscore notation is rejected by the executor as ``Unknown notation``.
    Asserting only that the corrected forms are present would not catch a
    reintroduction sitting BESIDE them, so their absence is pinned separately.
    """
    text = _SKILL_MD.read_text(encoding='utf-8')

    assert _DEFECTIVE_INVOCATION not in text, (
        f'skill body prescribes {_DEFECTIVE_INVOCATION!r}, which exits 127 outside '
        f'the wrapper — prescribe {_WRAPPER_INVOCATION!r} instead'
    )
    assert _DEFECTIVE_NOTATION not in text, (
        f'skill body carries the {_DEFECTIVE_NOTATION!r} script segment, which the '
        'executor rejects as Unknown notation — the correct segment is manage-status'
    )


# ---------------------------------------------------------------------------
# 2) NOT a built-in default — meta-project-only project step
# ---------------------------------------------------------------------------


def test_deploy_target_is_not_a_built_in_default():
    """Per the relocation, deploy-target is a project-local step, not a default.

    The hand-maintained BUILT_IN_FINALIZE_STEPS / *_DESCRIPTIONS constants were
    removed; membership is discovered via extension_discovery.find_implementors.
    A ``default:deploy-target`` built-in id must NOT appear among the discovered
    finalize steps, and must NOT be in the default-on seed.
    """
    from extension_discovery import find_implementors

    discovered_names = {
        rec['name'] for rec in find_implementors(cd.FINALIZE_STEP_EXT_POINT) if rec.get('name')
    }
    assert 'default:deploy-target' not in discovered_names
    # Positive contract: the project-local step IS discovered under its
    # PATH-derived ``project:{dir}`` id — confirming the step is surfaced, not
    # merely that the wrong built-in id is absent.
    assert 'project:finalize-step-deploy-target' in discovered_names
    # DEFAULT_PLAN_FINALIZE['steps'] is a lazy None placeholder; the seeded map is
    # built by _seed_finalize_steps() (the discovered default-on built-in set).
    assert 'default:deploy-target' not in cd._seed_finalize_steps()


def test_no_bundled_standards_doc_for_deploy_target():
    """No bundled phase-6-finalize/standards/deploy-target.md exists — the skill
    is project-local under .claude/, not in the plan-marshall bundle."""
    bundled = (
        MARKETPLACE_ROOT
        / 'plan-marshall'
        / 'skills'
        / 'phase-6-finalize'
        / 'standards'
        / 'deploy-target.md'
    )
    assert not bundled.exists(), (
        f'Unexpected bundled standards doc: {bundled}. The deploy-target step '
        f'is project-local only; no marketplace bundle should ship it.'
    )


# ---------------------------------------------------------------------------
# 3) Generator behaviour smoke test (integration)
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


@pytest.fixture()
def fixture_marketplace(tmp_path: Path) -> Path:
    """Tiny single-bundle marketplace for smoke testing the generator."""
    marketplace = tmp_path / 'bundles'
    bundle = marketplace / 'demo'
    plugin_doc = json.dumps(
        {
            'name': 'demo',
            'version': '0.0.1',
            'description': 'demo bundle',
            'skills': ['./skills/demo-skill'],
        },
        indent=2,
    ) + '\n'
    _write(bundle / '.claude-plugin' / 'plugin.json', plugin_doc)
    _write(
        bundle / 'skills' / 'demo-skill' / 'SKILL.md',
        '---\nname: demo-skill\ndescription: demo desc\n---\n# Body\n',
    )
    # The Claude target's emit step regenerates a top-level marketplace.json
    # from the source manifest; provide a minimal one so emit mode succeeds.
    _write(
        tmp_path / '.claude-plugin' / 'marketplace.json',
        json.dumps(
            {
                'name': 'fixture-marketplace',
                'plugins': [{'name': 'demo', 'description': 'demo', 'source': './bundles/demo'}],
            },
            indent=2,
        )
        + '\n',
    )
    return marketplace


#: The stdout line the skill body reads its ``display_detail`` count from.
#: Named here so the test parses the count exactly as the documented step does,
#: rather than settling for a substring that would survive the line changing shape.
_PRODUCED_LINE_RE = re.compile(r'^claude: produced (?P<count>\d+) entries$', re.MULTILINE)

#: The exit codes ``generate.py`` returns. The exit code is the outcome signal —
#: there is no ``status:`` field on stdout to branch on.
_EXIT_OK = 0
_EXIT_ERROR = 2


def _run_generator(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the live generator with ``args`` and capture both streams."""
    return subprocess.run(
        [sys.executable, str(_GENERATE_PY), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_generator_success_exits_zero_and_prints_a_nonzero_produced_count(
    fixture_marketplace: Path, tmp_path: Path
):
    """The two signals the skill body is written against, asserted as such.

    The step reads its OUTCOME from the exit code and its ``display_detail``
    COUNT from the ``claude: produced {N} entries`` stdout line. Asserting only
    that ``'claude:'`` appears somewhere in stdout would pass on a line whose
    count had vanished — the count is the thing the executor consumes, so it is
    parsed here with the same shape the step body prescribes.

    The absence of an envelope is asserted on the SAME run, because it is what
    makes the exit code load-bearing: the body once branched on ``status:`` /
    ``emitted_count`` fields no code path emits, so re-introducing one on stdout
    must fail here and force the body to be updated in the same change.
    """
    output_dir = tmp_path / 'out'

    result = _run_generator(
        '--target', 'claude',
        '--output', str(output_dir),
        '--marketplace-dir', str(fixture_marketplace),
    )

    assert result.returncode == _EXIT_OK, f'generator exit={result.returncode}, stderr={result.stderr}'
    match = _PRODUCED_LINE_RE.search(result.stdout)
    assert match is not None, (
        f'stdout carries no "claude: produced N entries" line, which is where the step '
        f'body reads its display_detail count: {result.stdout!r}'
    )
    assert int(match.group('count')) > 0, 'a non-empty bundle must produce entries'
    for absent in ('status:', 'emitted_count'):
        assert absent not in result.stdout, (
            f'stdout carries {absent!r}; the skill body reads the exit code and the '
            f'produced-count line, so an envelope here means the two have diverged'
        )
    assert output_dir.is_dir()
    files_only = [p for p in output_dir.rglob('*') if p.is_file()]
    assert len(files_only) > 0, 'generator must emit at least one file for a non-empty bundle'


def test_generator_failure_exits_two_and_writes_its_diagnostic_to_stderr(tmp_path: Path):
    """MATCHED NEGATIVE — the failure half of the same two signals.

    Without it, the success case alone is satisfied by a generator that exits
    ``0`` unconditionally, and the step body's ``outcome=failed`` branch — which
    surfaces the ``error: …`` stderr line — rests on nothing. A missing
    marketplace directory is the generator's earliest documented failure path.
    """
    result = _run_generator(
        '--target', 'claude',
        '--output', str(tmp_path / 'out'),
        '--marketplace-dir', str(tmp_path / 'does-not-exist'),
    )

    assert result.returncode == _EXIT_ERROR, (
        f'a failed run must exit {_EXIT_ERROR}, got {result.returncode}: {result.stderr!r}'
    )
    assert 'error: marketplace directory not found' in result.stderr, (
        f'the failure text the step surfaces must be on stderr: {result.stderr!r}'
    )
    assert _PRODUCED_LINE_RE.search(result.stdout) is None, (
        f'a failed run must not print a produced-count line: {result.stdout!r}'
    )


def test_emit_marker_carries_file_hash_manifest(fixture_marketplace: Path, tmp_path: Path):
    """A successful emit writes a ``file_hashes`` manifest into the sentinel.

    The manifest pins every emitted file (keyed by output-root-relative
    POSIX path, excluding the sentinel itself) so the sync staleness guard
    can diagnose per-file drift against transformed generator output without
    re-deriving a raw source counterpart. The manifest must cover exactly the
    emitted regular files minus ``.emit-marker.json``.
    """
    output_dir = tmp_path / 'out'
    result = subprocess.run(
        [
            sys.executable,
            str(_GENERATE_PY),
            '--target', 'claude',
            '--output', str(output_dir),
            '--marketplace-dir', str(fixture_marketplace),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f'generator exit={result.returncode}, stderr={result.stderr}'

    marker_path = output_dir / '.emit-marker.json'
    assert marker_path.is_file(), 'emit must write the .emit-marker.json sentinel'
    marker = json.loads(marker_path.read_text(encoding='utf-8'))

    file_hashes = marker.get('file_hashes')
    assert isinstance(file_hashes, dict), 'sentinel must carry a file_hashes manifest'
    assert file_hashes, 'manifest must be non-empty for a non-empty bundle'
    # The sentinel never lists itself.
    assert '.emit-marker.json' not in file_hashes
    # Every SHA is a 40-char git blob hex digest.
    assert all(len(sha) == 40 for sha in file_hashes.values())

    # The manifest keys are exactly the emitted regular files minus the sentinel.
    emitted_rel = {
        p.relative_to(output_dir).as_posix()
        for p in output_dir.rglob('*')
        if p.is_file() and not p.is_symlink()
    }
    emitted_rel.discard('.emit-marker.json')
    assert set(file_hashes) == emitted_rel
