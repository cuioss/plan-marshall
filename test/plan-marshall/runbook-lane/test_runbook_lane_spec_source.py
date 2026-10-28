#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Which copy of a staged spec ``resolve`` reads, and what it says about it.

With ``orchestrator.use_worktree`` on, every spec edit lives only in the shared
ledger worktree until a ledger land, so a lane that always read the main checkout
could run a spec other than the one the orchestrator reports. The read is
therefore WORKTREE-FIRST by default: the ledger worktree's copy wins when it
exists, and the main checkout's copy is the fallback. ``--spec-from-ledger`` is
accepted as a documented no-op — it names the read the default makes, so a command
line that carries it behaves exactly as one that does not.

The two copies carry DIFFERENT deliverable titles in these fixtures, so an
assertion on the parsed output proves which BODY was read, not merely which path
was echoed back.

Every fixture keeps its state inside its own ``tmp_path``: ``PLAN_BASE_DIR``
anchors the main-checkout seam on the fixture's ``.plan`` (so the ledger worktree
resolves to ``{fixture}/.plan/worktrees/_orchestrator``) and ``PLAN_MARSHALL_HOME``
isolates the machine-global tier.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from conftest import MARKETPLACE_ROOT, get_scripts_dir, load_script_module, run_script

_SKILL_NAME = 'runbook-lane'
_SCRIPT = get_scripts_dir('plan-marshall', _SKILL_NAME) / 'runbook_lane.py'
_SKILL_TEXT = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / _SKILL_NAME / 'SKILL.md'

SLUG = 'demo-epic'
SPEC_NAME = 'PLAN-LB-90-lane-reads-ledger-spec.md'
SPEC_REL = f'.plan/orchestrator/{SLUG}/plans/{SPEC_NAME}'

MAIN_TITLE = 'Main checkout deliverable'
LEDGER_TITLE = 'Ledger worktree deliverable'


def _spec_body(title: str) -> str:
    """A minimal staged spec whose ONLY observable content is its deliverable title."""
    return f'# staged spec\n\n## Deliverables\n\n1. **{title}**\n'


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _seed_project(root: Path, *, use_worktree: bool) -> None:
    """Seed the project surface ``resolve`` reads: the config and the architecture."""
    _write(
        root / '.plan' / 'marshal.json',
        json.dumps(
            {
                'orchestrator': {'use_worktree': use_worktree},
                'plan': {
                    'phase-6-finalize': {'steps': {'plan-marshall:automatic-review': {'required_bots': 'some-bot'}}}
                },
            }
        ),
    )
    architecture = root / '.plan' / 'project-architecture'
    _write(
        architecture / '_project.json',
        json.dumps({'name': 'test-project', 'modules': {'root-mod': {}, 'documentation': {}}}),
    )
    _write(
        architecture / 'root-mod' / 'derived.json',
        json.dumps(
            {
                'name': 'root-mod',
                'build_systems': ['pyproject'],
                'paths': {'module': '.'},
                'commands': {
                    'quality-gate': 'python3 .plan/execute-script.py build run --command-args "quality-gate"',
                    'module-tests': 'python3 .plan/execute-script.py build run --command-args "module-tests"',
                    'verify': 'python3 .plan/execute-script.py build run --command-args "verify"',
                },
            }
        ),
    )
    _write(
        architecture / 'documentation' / 'derived.json',
        json.dumps(
            {
                'name': 'documentation',
                'build_systems': ['documentation'],
                'paths': {'module': 'doc'},
                'files': {'doc': ['doc/usage.md']},
            }
        ),
    )


def _main_spec(root: Path) -> Path:
    return root / SPEC_REL


def _ledger_spec(root: Path) -> Path:
    """The ledger worktree's copy, at the path the store seam computes for the fixture.

    ``PLAN_BASE_DIR`` stands in for the main checkout's ``.plan/local``, so the
    worktree lands at ``{fixture}/.plan/worktrees/_orchestrator`` and its store at
    ``{worktree}/.plan``.
    """
    return root / '.plan' / 'worktrees' / '_orchestrator' / SPEC_REL


def _seed_copies(
    root: Path,
    *,
    use_worktree: bool,
    main_body: str | None,
    ledger_body: str | None,
) -> None:
    _seed_project(root, use_worktree=use_worktree)
    if main_body is not None:
        _write(_main_spec(root), main_body)
    if ledger_body is not None:
        _write(_ledger_spec(root), ledger_body)


def _env(root: Path) -> dict[str, str]:
    return {
        'PLAN_BASE_DIR': str(root / '.plan'),
        'PLAN_MARSHALL_HOME': str(root / '.machine-home'),
    }


def _run_resolve(root: Path, spec: str, *, from_ledger: bool = False) -> dict[str, Any]:
    """Invoke ``resolve`` through its real CLI, so a renamed flag is a red test."""
    argv = ['resolve', '--spec', spec, '--project-dir', str(root)]
    if from_ledger:
        argv.append('--spec-from-ledger')
    result = run_script(_SCRIPT, *argv, env_overrides=_env(root))
    assert result.success, f'resolve crashed: {result.stderr}'
    data: dict[str, Any] = result.toon()
    return data


def _titles(data: dict[str, Any]) -> list[str]:
    return [row['title'] for row in data['deliverables']]


def _lane_text() -> str:
    return str(_SKILL_TEXT.read_text(encoding='utf-8'))


# =============================================================================
# D1 — the default read order: the ledger worktree, then the main checkout
# =============================================================================


def test_default_reads_the_ledger_worktree_copy(tmp_path: Path) -> None:
    """With the flag absent the lane reads the worktree's body, not the main checkout's."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=_spec_body(LEDGER_TITLE))

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'success', data
    assert _titles(data) == [LEDGER_TITLE]
    assert data['spec'] == _ledger_spec(tmp_path).as_posix()


def test_a_spec_only_in_the_ledger_is_read_by_default(tmp_path: Path) -> None:
    """A worktree-only spec is exactly the case the default order has to reach."""
    _seed_copies(tmp_path, use_worktree=True, main_body=None, ledger_body=_spec_body(LEDGER_TITLE))

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'success', data
    assert _titles(data) == [LEDGER_TITLE]


def test_a_spec_only_in_the_main_checkout_is_read_by_default(tmp_path: Path) -> None:
    """The main checkout stays the fallback, so its copy is never lost."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=None)

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'success', data
    assert _titles(data) == [MAIN_TITLE]
    assert data['spec_source'] == 'main_checkout'


def test_use_worktree_off_reads_the_one_copy(tmp_path: Path) -> None:
    """With no ledger worktree there is one copy, read without error."""
    _seed_copies(tmp_path, use_worktree=False, main_body=_spec_body(MAIN_TITLE), ledger_body=None)

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'success', data
    assert _titles(data) == [MAIN_TITLE]
    assert data['spec_source'] == 'main_checkout'


def test_a_spec_in_neither_copy_is_refused(tmp_path: Path) -> None:
    """Neither copy existing is the fail-closed refusal, never a silent empty read."""
    _seed_copies(tmp_path, use_worktree=True, main_body=None, ledger_body=None)

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'error'
    assert data['error'] == 'invalid_spec'


def test_the_ledger_spelling_is_knob_gated(tmp_path: Path) -> None:
    """With the knob off a ledger-store path is not a staged spec: the filesystem does not decide."""
    _seed_copies(
        tmp_path,
        use_worktree=False,
        main_body=_spec_body(MAIN_TITLE),
        ledger_body=_spec_body(LEDGER_TITLE),
    )

    data = _run_resolve(tmp_path, str(_ledger_spec(tmp_path)))

    assert data['status'] == 'error'
    assert data['error'] == 'spec_outside_orchestrator'


def test_the_ledger_copy_is_readable_by_its_own_absolute_path(tmp_path: Path) -> None:
    """The shape check accepts the ledger store's form without any flag."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=_spec_body(LEDGER_TITLE))

    data = _run_resolve(tmp_path, str(_ledger_spec(tmp_path)))

    assert data['status'] == 'success', data
    assert _titles(data) == [LEDGER_TITLE]
    assert data['spec_source'] == 'ledger_worktree'


def test_the_knob_gate_ignores_a_ledger_copy_left_on_disk(tmp_path: Path) -> None:
    """The knob decides, not the filesystem: a stale ledger tree is not read with it off."""
    _seed_copies(
        tmp_path,
        use_worktree=False,
        main_body=_spec_body(MAIN_TITLE),
        ledger_body=_spec_body(LEDGER_TITLE),
    )

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'success', data
    assert _titles(data) == [MAIN_TITLE]
    assert data['spec_source'] == 'main_checkout'
    assert 'spec_differ' not in data


# =============================================================================
# D2 — the flag stays accepted and means what the default now means
# =============================================================================


def test_the_flag_means_what_the_default_means(tmp_path: Path) -> None:
    """An old emitted command carrying the flag reads the same copy the default reads."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=_spec_body(LEDGER_TITLE))

    plain = _run_resolve(tmp_path, SPEC_REL)
    flagged = _run_resolve(tmp_path, SPEC_REL, from_ledger=True)

    assert plain['spec_source'] == flagged['spec_source'] == 'ledger_worktree'
    assert _titles(plain) == _titles(flagged) == [LEDGER_TITLE]


def test_the_flag_is_still_accepted_with_use_worktree_off(tmp_path: Path) -> None:
    """No second copy means the flag stays harmless rather than becoming an error."""
    _seed_copies(tmp_path, use_worktree=False, main_body=_spec_body(MAIN_TITLE), ledger_body=None)

    data = _run_resolve(tmp_path, SPEC_REL, from_ledger=True)

    assert data['status'] == 'success', data
    assert _titles(data) == [MAIN_TITLE]


def test_lane_text_names_the_flag_status() -> None:
    """The lane text states what the flag now means, so a reader does not infer worktree-first."""
    text = _lane_text()

    assert '--spec-from-ledger' in text
    assert 'documented no-op' in text


# =============================================================================
# D3 — the result and the landing still say which copy was read
# =============================================================================


def test_resolve_reports_the_copy_it_read(tmp_path: Path) -> None:
    """Both modes name the worktree, because the default and the flag are one read."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=_spec_body(LEDGER_TITLE))

    plain = _run_resolve(tmp_path, SPEC_REL)
    flagged = _run_resolve(tmp_path, SPEC_REL, from_ledger=True)

    assert plain['spec_source'] == 'ledger_worktree'
    assert flagged['spec_source'] == 'ledger_worktree'


def test_two_differing_copies_carry_the_differ_marker(tmp_path: Path) -> None:
    """A silent read of the older copy is what the marker removes."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=_spec_body(LEDGER_TITLE))

    plain = _run_resolve(tmp_path, SPEC_REL)
    flagged = _run_resolve(tmp_path, SPEC_REL, from_ledger=True)

    assert plain.get('spec_differ') is True
    assert flagged.get('spec_differ') is True


def test_a_worktree_only_copy_reports_the_worktree_and_no_marker(tmp_path: Path) -> None:
    """One copy cannot differ from itself, and the source names where it was read."""
    _seed_copies(tmp_path, use_worktree=True, main_body=None, ledger_body=_spec_body(LEDGER_TITLE))

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['spec_source'] == 'ledger_worktree'
    assert 'spec_differ' not in data


def test_a_main_only_copy_reports_the_main_checkout_and_no_marker(tmp_path: Path) -> None:
    """The fallback is still labelled by where it actually resolves."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=None)

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['spec_source'] == 'main_checkout'
    assert 'spec_differ' not in data


def test_identical_copies_carry_no_differ_marker(tmp_path: Path) -> None:
    """Two copies that agree are not a discrepancy worth reporting."""
    body = _spec_body(MAIN_TITLE)
    _seed_copies(tmp_path, use_worktree=True, main_body=body, ledger_body=body)

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'success', data
    assert 'spec_differ' not in data


def test_the_no_op_mode_reports_one_copy_and_no_marker(tmp_path: Path) -> None:
    """A project with no second copy reports the main checkout and no differ marker."""
    _seed_copies(tmp_path, use_worktree=False, main_body=_spec_body(MAIN_TITLE), ledger_body=None)

    data = _run_resolve(tmp_path, SPEC_REL, from_ledger=True)

    assert data['spec_source'] == 'main_checkout'
    assert 'spec_differ' not in data


def test_the_fallback_is_the_main_checkout_not_the_project_dir(tmp_path: Path, monkeypatch) -> None:
    """A --project-dir inside a plan worktree must not be reported as the main checkout.

    The worktree has its own ``.plan`` tier and holds no spec of its own; the copy
    labelled ``main_checkout`` must come from the checkout the ledger worktree lives
    under, not from the directory the caller happened to run in.
    """
    main_root = tmp_path / 'main'
    project = tmp_path / 'plan-worktree'
    _write(main_root / SPEC_REL, _spec_body(MAIN_TITLE))
    _write(project / '.plan' / 'marshal.json', json.dumps({}))

    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)
    monkeypatch.setattr(module, 'main_checkout_root', lambda: main_root)
    monkeypatch.setattr(module, 'base_dir_override_active', lambda: False)
    monkeypatch.setattr(module, '_ledger_store_dir', lambda: None)

    choice = module._resolve_spec(SPEC_REL, project)

    assert choice.path == main_root / SPEC_REL
    assert choice.source == 'main_checkout'


def test_a_symlinked_spec_cannot_escape_its_store(tmp_path: Path) -> None:
    """A link planted at a main-store path must not hand the lane a file from outside it."""
    outside = tmp_path / 'outside.md'
    _write(outside, _spec_body(LEDGER_TITLE))
    _seed_project(tmp_path, use_worktree=True)
    staged = _main_spec(tmp_path)
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.symlink_to(outside)

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'error'
    assert data['error'] == 'spec_outside_orchestrator'


def test_a_link_at_the_ledger_copy_is_not_read_as_a_store_copy(tmp_path: Path) -> None:
    """The containment check covers the worktree copy too: it falls back rather than escaping."""
    outside = tmp_path / 'outside.md'
    _write(outside, _spec_body(LEDGER_TITLE))
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=None)
    ledger = _ledger_spec(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.symlink_to(outside)

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'success', data
    assert _titles(data) == [MAIN_TITLE]
    assert data['spec_source'] == 'main_checkout'


def test_a_link_at_the_derived_main_copy_is_not_read(tmp_path: Path, monkeypatch) -> None:
    """The containment check refuses a DERIVED copy that resolves outside its store.

    The named path passes the shape check, so only :func:`_contained_file` stands
    between the lane and the escaped file — and it fails closed with ``invalid_spec``
    rather than reading it under a store label.
    """
    main_root = tmp_path / 'main'
    project = tmp_path / 'plan-worktree'
    outside = tmp_path / 'outside.md'
    _write(outside, _spec_body(LEDGER_TITLE))
    _write(project / '.plan' / 'marshal.json', json.dumps({}))
    staged = main_root / SPEC_REL
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.symlink_to(outside)

    module = load_script_module('plan-marshall', _SKILL_NAME, 'runbook_lane.py', register=False)
    monkeypatch.setattr(module, 'main_checkout_root', lambda: main_root)
    monkeypatch.setattr(module, 'base_dir_override_active', lambda: False)
    monkeypatch.setattr(module, '_ledger_store_dir', lambda: None)

    with pytest.raises(ValueError, match='invalid_spec'):
        module._resolve_spec(SPEC_REL, project)


def test_lane_text_states_the_worktree_first_order() -> None:
    """§ 0 states the new order, and the old default sentence is gone."""
    text = _lane_text()

    assert 'The spec is read from the **shared ledger worktree** first' in text
    assert 'Read the spec from the **main checkout** by default' not in text


def test_lane_text_names_the_ledger_read_and_what_it_reports() -> None:
    """The landing's RULE-CHECK item carries both facts, not just the setup text."""
    text = _lane_text()
    rule_check = text.split('**Rule check**', 1)

    assert len(rule_check) == 2, 'the landing report has no rule-check section'
    # Stop at the next numbered report item, so only the rule-check item is searched.
    item = re.split(r'^ {0,4}\d+\. \*\*', rule_check[1], maxsplit=1, flags=re.MULTILINE)[0]
    assert 'spec_source' in item
    assert 'spec_differ' in item
    # The rationale names the mechanism that removes a silent older read: the
    # worktree-first default, not the accepted-as-a-no-op flag.
    assert 'worktree-first default' in item
    assert 'ledger flag' not in item


# =============================================================================
# D4 — the new read does not soften the write rule
# =============================================================================


def _snapshot(root: Path) -> dict[str, tuple[int, bytes]]:
    """Every file under ``root`` with its mtime and bytes — a write shows up here."""
    return {
        path.relative_to(root).as_posix(): (path.stat().st_mtime_ns, path.read_bytes())
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def test_reading_the_ledger_copy_writes_nothing(tmp_path: Path) -> None:
    """The worktree copy is READ ONLY: the default read leaves the tree byte-identical."""
    _seed_copies(tmp_path, use_worktree=True, main_body=_spec_body(MAIN_TITLE), ledger_body=_spec_body(LEDGER_TITLE))
    before = _snapshot(tmp_path)

    data = _run_resolve(tmp_path, SPEC_REL)

    assert data['status'] == 'success', data
    assert _titles(data) == [LEDGER_TITLE]
    assert _snapshot(tmp_path) == before


def test_lane_text_keeps_the_write_rule_verbatim() -> None:
    """The rule the new read must not soften, quoted as the lane states it."""
    text = _lane_text()

    assert 'Never edit the spec or any file under `.plan/orchestrator/`' in text
    assert 'The worktree copy is READ ONLY' in text
