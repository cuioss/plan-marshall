#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _cred_ensure_denied.py module.

The module states a goal — protect the credentials directory — and the active
target's runtime renders and writes whatever expresses that on its own
permission model. So these tests cover the CALLER's contract (what it asks for,
what it reports, how it handles a target that declines) and leave the rule
content to the runtime's own pins in
the ``test_permission_rendering_*`` modules under
``test/plan-marshall/platform-runtime/``, which is where the grammar lives.
"""

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-providers', 'credentials.py')


@pytest.fixture
def claude_project(tmp_path, monkeypatch):
    """Make *tmp_path* a claude-target project with cwd pinned to it.

    The runtime resolves the settings file from the working directory, so a
    test that does not pin cwd writes into the checkout's own
    ``.claude/settings.json``. Pinning cwd is the isolation that holds whichever
    module performs the write — mocking a save function does not, because the
    call routes through the runtime rather than through this skill.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'marshal.json').write_text(
        json.dumps({'runtime': {'target': 'claude'}}), encoding='utf-8'
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _deny_list(project_root: Path) -> list[str]:
    settings = project_root / '.claude' / 'settings.local.json'
    if not settings.is_file():
        return []
    deny: list[str] = json.loads(settings.read_text(encoding='utf-8'))['permissions']['deny']
    return deny


class TestEnsureDeniedCLI:
    """Tests for the ensure-denied subcommand."""

    def test_ensure_denied_writes_rules_for_the_credentials_dir(
        self, claude_project, capsys
    ) -> None:
        import _cred_ensure_denied

        assert _cred_ensure_denied.run_ensure_denied(Namespace(target='project')) == 0

        deny = _deny_list(claude_project)
        assert deny, 'ensure-denied must write deny rules'
        # Name the directory from the module's own bound constant rather than
        # matching the word "credentials": the autouse sandbox chooses that
        # directory, and its name is not this test's to assume. The absolute
        # spelling is rendered whether or not the sandbox lies under $HOME, so
        # these three hold on any machine.
        protected = str(_cred_ensure_denied.CREDENTIALS_DIR)
        assert f'Read({protected}/**)' in deny
        assert f'Bash(cat {protected}/*)' in deny
        assert f'Bash(base64 {protected}/*)' in deny
        # Protection covers the canonical directory only: no rule may name
        # the pre-migration location that `migrate-home` moves away from.
        assert not any('.plan-marshall-credentials' in rule for rule in deny)

        reported = capsys.readouterr().out
        assert 'status: success' in reported
        assert f'rules_added: {len(deny)}' in reported
        # This fixture's deny list starts empty, so `len(deny)` and
        # `protection_rules_total` coincide here by construction — the
        # distinction between the protection's own denominator and the settings
        # file's total deny count is pinned by
        # `test_protection_total_counts_the_protection_not_the_deny_list`, not
        # by this line.
        assert f'protection_rules_total: {len(deny)}' in reported

    def test_ensure_denied_is_idempotent(self, claude_project, capsys) -> None:
        from _cred_ensure_denied import run_ensure_denied

        run_ensure_denied(Namespace(target='project'))
        first = _deny_list(claude_project)
        capsys.readouterr()

        run_ensure_denied(Namespace(target='project'))
        assert _deny_list(claude_project) == first

        reported = capsys.readouterr().out
        assert 'rules_added: 0' in reported
        assert f'rules_existing: {len(first)}' in reported
        # `protection_rules_total` counts the protection's rules, so it is
        # unchanged by the re-run — unlike an added/existing split, which moves.
        assert f'protection_rules_total: {len(first)}' in reported

    def test_protection_total_counts_the_protection_not_the_deny_list(
        self, claude_project, capsys
    ) -> None:
        """`protection_rules_total` is the protection's denominator, not the file's.

        An unrelated deny entry is seeded first, which is what makes the two
        numbers differ: against an empty deny list they coincide, so a report
        that counted the whole file would look correct.
        """
        from _cred_ensure_denied import run_ensure_denied

        settings = claude_project / '.claude' / 'settings.local.json'
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps({'permissions': {'allow': [], 'deny': ['Read(~/.ssh/**)'], 'ask': []}}),
            encoding='utf-8',
        )

        assert run_ensure_denied(Namespace(target='project')) == 0

        deny = _deny_list(claude_project)
        reported = capsys.readouterr().out
        assert deny[0] == 'Read(~/.ssh/**)'
        assert f'protection_rules_total: {len(deny) - 1}' in reported
        assert f'rules_added: {len(deny) - 1}' in reported

    def test_ensure_denied_reports_a_declining_target_as_no_op(
        self, claude_project, monkeypatch, capsys
    ) -> None:
        """A target with no permission backend declines, and that is reported.

        Never as success: a fabricated effect count would tell an operator their
        credentials are guarded by rules that were never written.
        """
        import _cred_ensure_denied

        plan_dir = claude_project / '.plan'
        (plan_dir / 'marshal.json').write_text(
            json.dumps({'runtime': {'target': 'opencode'}}), encoding='utf-8'
        )
        # The memoised target read is per-process; drive the router directly.
        monkeypatch.setattr(_cred_ensure_denied, '_read_runtime_target', lambda: 'opencode')

        assert _cred_ensure_denied.run_ensure_denied(Namespace(target='project')) == 0

        reported = capsys.readouterr().out
        assert 'status: no-op' in reported
        assert 'rules_added' not in reported
        assert _deny_list(claude_project) == []

    def test_ensure_denied_reports_an_unresolvable_runtime_as_error(
        self, claude_project, monkeypatch, capsys
    ) -> None:
        """No runtime is an error, not a silent success."""
        import _cred_ensure_denied

        monkeypatch.setattr(_cred_ensure_denied, '_resolve_runtime', lambda: None)
        assert _cred_ensure_denied.run_ensure_denied(Namespace(target='project')) == 0

        reported = capsys.readouterr().out
        assert 'status: error' in reported


    def test_an_unenforceable_directory_mode_does_not_cost_the_deny_rules(
        self, claude_project, monkeypatch, capsys
    ) -> None:
        """A `chmod` this process cannot perform must not abort the subcommand.

        The 0700 mode is the primary boundary and the deny rules are the
        defence-in-depth layer, so the layer is worth applying precisely when
        the boundary cannot be re-asserted. Raising would also replace the TOON
        payload with a traceback.
        """
        import _cred_ensure_denied

        _cred_ensure_denied.CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        # 0o755 puts the directory in the state that calls for a chmod, so the
        # refusal below is reached rather than skipped.
        _cred_ensure_denied.os.chmod(str(_cred_ensure_denied.CREDENTIALS_DIR), 0o755)

        def _refuse(*_args, **_kwargs):
            raise PermissionError(13, 'Operation not permitted')

        monkeypatch.setattr(_cred_ensure_denied.os, 'chmod', _refuse)

        assert _cred_ensure_denied.run_ensure_denied(Namespace(target='project')) == 0

        captured = capsys.readouterr()
        assert 'Could not enforce 0o700' in captured.err
        # The rules still reached disk: the point of not raising.
        assert 'status: success' in captured.out
        assert _deny_list(claude_project)


    def test_the_runtimes_own_error_code_reaches_the_operator(
        self, claude_project, monkeypatch, capsys
    ) -> None:
        """A runtime error is forwarded by CODE, not flattened to a generic one.

        A caller branching on `error` needs the code the runtime produced —
        `io_error` (rules rendered, nothing written) calls for a different
        response than a malformed settings file. Nothing else drives the
        `status != 'success'` branch, so without this the whole forwarding path
        is unguarded end-to-end.
        """
        import _cred_ensure_denied

        class _FailingRuntime:
            def permission_fix(self, *_args, **_kwargs):
                return (
                    'operation: permission fix\n'
                    'status: error\n'
                    'error: io_error\n'
                    'message: Failed to write settings\n'
                )

        monkeypatch.setattr(_cred_ensure_denied, '_resolve_runtime', _FailingRuntime)
        assert _cred_ensure_denied.run_ensure_denied(Namespace(target='project')) == 0

        reported = capsys.readouterr().out
        assert 'status: error' in reported
        # The specific code, not the `protect_path_failed` fallback.
        assert 'error: io_error' in reported

    def test_the_reported_target_is_the_one_the_caller_asked_for(
        self, claude_project, monkeypatch, capsys
    ) -> None:
        """`target` echoes the argument rather than a constant.

        Every other test in this module passes `project`, which is also the
        value a hardcoded echo would produce.
        """
        import _cred_ensure_denied

        monkeypatch.setattr(_cred_ensure_denied, '_resolve_runtime', lambda: None)
        assert _cred_ensure_denied.run_ensure_denied(Namespace(target='global')) == 0

        assert 'target: global' in capsys.readouterr().out

    def test_a_loose_directory_mode_is_tightened_back_to_0700(
        self, claude_project, capsys
    ) -> None:
        """The primary boundary is re-asserted, and says so.

        The deny rules are defence in depth; this mode is the boundary they back
        up, and nothing else in this module exercises it.
        """
        import _cred_ensure_denied

        _cred_ensure_denied.CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        _cred_ensure_denied.os.chmod(str(_cred_ensure_denied.CREDENTIALS_DIR), 0o755)

        assert _cred_ensure_denied.run_ensure_denied(Namespace(target='project')) == 0

        mode = _cred_ensure_denied.CREDENTIALS_DIR.stat().st_mode & 0o777
        assert mode == 0o700
        assert 'expected 0o700' in capsys.readouterr().err


class TestEnsureDeniedRendersNoGrammar:
    """The module states intent; it must not build or receive permission strings."""

    def test_module_source_constructs_no_permission_dsl(self) -> None:
        source = (
            Path(__file__).resolve().parents[3]
            / 'marketplace'
            / 'bundles'
            / 'plan-marshall'
            / 'skills'
            / 'manage-providers'
            / 'scripts'
            / '_cred_ensure_denied.py'
        ).read_text(encoding='utf-8')

        assert 'Read(' not in source
        assert 'Bash(' not in source
        assert 'DENY_RULES' not in source
