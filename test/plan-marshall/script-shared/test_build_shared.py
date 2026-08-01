# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _build_shared utilities and resolve_project_dir executor resolution."""

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

# Add script path for imports
_SCRIPT_DIR = (
    Path(__file__).resolve().parents[3]
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'script-shared'
    / 'scripts'
    / 'build'
)
sys.path.insert(0, str(_SCRIPT_DIR))

# resolve_project_dir.py lives in the script-shared scripts/ dir (one level up
# from build/). Add it so `import resolve_project_dir` resolves regardless of
# the conftest PYTHONPATH wiring.
sys.path.insert(0, str(_SCRIPT_DIR.parent))

_build_shared = importlib.import_module('_build_shared')
_resolve_project_dir = importlib.import_module('resolve_project_dir')
# The worktree/checkout-root resolution these tests exercise now lives in
# file_ops (resolve_project_dir is the argv/flag layer on top of it), and
# marketplace_paths owns the distinctly-named git-common-dir resolver.
file_ops = importlib.import_module('file_ops')
marketplace_paths = importlib.import_module('marketplace_paths')


class TestGetBashTimeout:
    """Tests for get_bash_timeout()."""

    def test_adds_buffer_to_inner_timeout(self):
        result = _build_shared.get_bash_timeout(300)
        assert result == 330  # 300 + 30 buffer

    def test_small_timeout(self):
        result = _build_shared.get_bash_timeout(10)
        assert result == 40  # 10 + 30 buffer

    def test_zero_timeout(self):
        result = _build_shared.get_bash_timeout(0)
        assert result == 30  # 0 + 30 buffer

    def test_buffer_constant_is_30(self):
        assert _build_shared.OUTER_TIMEOUT_BUFFER == 30


class TestWorktreeQueryExecutorPath:
    """Executor resolution behind the worktree query now lives in file_ops.

    ``resolve_project_dir`` no longer owns an ``_executor_path`` helper: the
    executor lookup moved into ``file_ops._query_worktree_path``, which is the
    SINGLE place in the codebase that invokes ``manage-status
    get-worktree-path``. It still re-wraps a RuntimeError from
    ``get_executor_path`` (no git repo) into ``WorktreeResolutionError`` so
    callers can surface the message verbatim, and that re-wrap is what these
    tests pin.
    """

    def test_runtime_error_wrapped_in_worktree_resolution_error(self, monkeypatch):
        """A RuntimeError from get_executor_path becomes WorktreeResolutionError."""
        def _raise():
            raise RuntimeError('no git repository')
        monkeypatch.setattr(file_ops, 'get_executor_path', _raise)
        with pytest.raises(file_ops.WorktreeResolutionError, match='Cannot locate executor'):
            file_ops._query_worktree_path('some-plan')

    def test_resolve_project_dir_reexports_the_error_type(self):
        """resolve_project_dir surfaces file_ops' error type, not a private clone.

        Consumers catch ``resolve_project_dir.WorktreeResolutionError``; after
        the consolidation that name MUST be the very same class object as
        ``file_ops.WorktreeResolutionError``, or an ``except`` in a Bucket B
        script would silently stop catching the error the resolver raises.
        """
        assert _resolve_project_dir.WorktreeResolutionError is file_ops.WorktreeResolutionError

    def test_executor_path_helper_is_gone_from_resolve_project_dir(self):
        """The private helper MUST NOT survive as a second implementation.

        Anti-vacuity guard for the consolidation: if ``_executor_path`` were
        restored on ``resolve_project_dir`` the tests above would still pass
        while the duplication the consolidation removed had quietly returned.
        """
        assert not hasattr(_resolve_project_dir, '_executor_path')
        assert not hasattr(_resolve_project_dir, '_query_worktree_path')


class TestCwdCheckoutRoot:
    """Tests for file_ops.cwd_checkout_root().

    ``cwd_checkout_root()`` is the fallback returned when neither --plan-id nor
    --project-dir is supplied, and when --plan-id resolves to use_worktree=false.
    Under the uniform cwd rule (ADR-002) it resolves cwd-relatively via
    marketplace_paths._find_plan_root_from_cwd() — the nearest ancestor of cwd
    containing .plan/local — NOT via git rev-parse --show-toplevel. These tests
    lock in that cwd-relative routing behaviour.
    """

    def test_returns_cwd_relative_plan_root(self, tmp_path, monkeypatch):
        """When _find_plan_root_from_cwd resolves a root, it is returned verbatim."""
        plan_root = tmp_path / 'checkout'
        monkeypatch.setattr(file_ops, '_find_plan_root_from_cwd', lambda: plan_root)
        result = file_ops.cwd_checkout_root()
        assert result == str(plan_root)

    def test_falls_back_to_cwd_when_plan_root_unresolvable(self, tmp_path, monkeypatch):
        """When no .plan/local ancestor exists, the absolute cwd is the last-ditch fallback."""
        monkeypatch.setattr(file_ops, '_find_plan_root_from_cwd', lambda: None)
        monkeypatch.chdir(tmp_path)
        result = file_ops.cwd_checkout_root()
        # tmp_path may be a symlink target on macOS; compare resolved absolute paths.
        assert result == os.path.abspath(os.getcwd())

    def test_is_distinct_from_marketplace_paths_main_checkout_root(self):
        """The cwd-relative resolver is NOT marketplace_paths.main_checkout_root.

        ``marketplace_paths`` exports a same-shaped-sounding
        ``main_checkout_root`` that resolves via ``git --git-common-dir`` (always
        MAIN, even from a linked worktree) and returns a ``Path``. This one is
        the cwd-relative rule and returns a ``str``, resolving to the WORKTREE
        during phase-5+. Pinning the distinction keeps a future rename from
        silently collapsing two opposite worktree semantics into one name.
        """
        assert file_ops.cwd_checkout_root is not marketplace_paths.main_checkout_root
        assert isinstance(file_ops.cwd_checkout_root(), str)

    def test_neither_flag_routes_through_cwd_checkout_root(self, monkeypatch):
        """resolve_project_dir(None, None) delegates to the cwd-relative resolver."""
        monkeypatch.setattr(_resolve_project_dir, 'cwd_checkout_root', lambda: '/tmp/cwd-relative-root')
        resolved = _resolve_project_dir.resolve_project_dir(None, '.', default='.')
        assert resolved == '/tmp/cwd-relative-root'

    def test_plan_id_use_worktree_false_routes_through_cwd_checkout_root(self, monkeypatch):
        """--plan-id with use_worktree=false falls back to the cwd-relative resolver.

        The patch targets are both in ``file_ops``: the shell-out seam
        (``_query_worktree_path``) and the fallback the resolver reaches through
        the module global inside ``PlanContext._resolve_worktree_face``. The
        delegation chain from ``resolve_project_dir`` through
        ``resolve_plan_context`` runs for real.
        """
        monkeypatch.setattr(file_ops, '_query_worktree_path', lambda _pid: (False, ''))
        monkeypatch.setattr(file_ops, 'cwd_checkout_root', lambda: '/tmp/cwd-relative-root')
        resolved = _resolve_project_dir.resolve_project_dir('some-plan', '.', default='.')
        assert resolved == '/tmp/cwd-relative-root'

    def test_plan_id_use_worktree_true_returns_absolute_worktree_path(self, monkeypatch):
        """--plan-id with use_worktree=true returns the persisted worktree path."""
        monkeypatch.setattr(
            file_ops, '_query_worktree_path', lambda _pid: (True, '/tmp/wt-shared-resolved')
        )
        resolved = _resolve_project_dir.resolve_project_dir('some-plan', '.', default='.')
        assert resolved == '/tmp/wt-shared-resolved'


class TestCmdRunCommonSafetyNet:
    """SAFETY-NET: a failed build whose parser extracts no structured error
    must still yield exactly one synthetic errors[] row, so status and errors[]
    can never be mutually contradictory."""

    def test_synthetic_error_row_emitted_when_parser_returns_no_errors(self, tmp_path, capsys):
        # Arrange: a genuinely failed build (non-zero exit) whose parser finds
        # nothing structured — the exact contradiction the safety-net closes.
        log_path = tmp_path / 'build.log'
        log_path.write_text('colored output that the parser matched nothing in\n', encoding='utf-8')
        result = {
            'status': 'error',
            'exit_code': 1,
            'duration_seconds': 5,
            'log_file': str(log_path),
            'command': './pw module-tests plan-marshall',
        }

        def _empty_parser(_log_file):
            # Build FAILED but no structured error was extracted.
            return [], None, 'FAILURE'

        # Act
        exit_code = _build_shared.cmd_run_common(
            result,
            _empty_parser,
            tool_name='python',
            output_format='json',
        )
        parsed = json.loads(capsys.readouterr().out)

        # Assert: status is error and exactly one synthetic error row is present.
        assert exit_code == 0  # status is modeled in the output, not the exit code
        assert parsed['status'] == 'error'
        errors = parsed.get('errors', [])
        assert len(errors) == 1
        synthetic = errors[0]
        assert synthetic['file'] == str(log_path)
        assert synthetic['category'] == 'build_failure'
        assert synthetic['severity'] == _build_shared.SEVERITY_ERROR

    def test_parsed_errors_are_not_overwritten_by_safety_net(self, tmp_path, capsys):
        # Arrange: a failed build whose parser DID extract a real error. The
        # safety-net must not fire — the genuine error is preserved verbatim.
        log_path = tmp_path / 'build.log'
        log_path.write_text('real failure content\n', encoding='utf-8')
        result = {
            'status': 'error',
            'exit_code': 1,
            'duration_seconds': 5,
            'log_file': str(log_path),
            'command': './pw module-tests plan-marshall',
        }
        real_issue = _build_shared.Issue(
            file='tests/test_foo.py',
            line=42,
            message='assert 1 == 2',
            severity=_build_shared.SEVERITY_ERROR,
            category='test_failure',
        )

        def _real_parser(_log_file):
            return [real_issue], None, 'FAILURE'

        # Act
        _build_shared.cmd_run_common(
            result,
            _real_parser,
            tool_name='python',
            output_format='json',
        )
        parsed = json.loads(capsys.readouterr().out)

        # Assert: the single genuine error is kept; no synthetic row is added.
        errors = parsed.get('errors', [])
        assert len(errors) == 1
        assert errors[0]['file'] == 'tests/test_foo.py'
        assert errors[0]['category'] == 'test_failure'


class TestCmdRunCommonPlanIdGuards:
    """The two ``plan_id`` guards in ``cmd_run_common`` treat NO_PLAN as ABSENT.

    Both guards feed a per-plan FINDING STORE, which the ``NO_PLAN`` sentinel
    does not own. The sentinel is TRUTHY, so a ``if plan_id:`` guard goes
    vacuous the moment ``build_main`` starts resolving an absent ``--plan-id``
    to it: a plan-less build would begin auto-storing parsed issues into a
    ``NO_PLAN`` store and bulk-resolving findings in one. Today's plan-less
    behaviour — parse and format, store nothing — is the confirmed contract.

    Each guard is asserted in BOTH directions. The suppression half alone is
    satisfied by a guard that never fires at all, which would silently disable
    producer-side finding storage for every plan-scoped build too.
    """

    _FAILING_RESULT = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 5,
        'log_file': '',
        'command': './pw module-tests plan-marshall',
    }
    _GREEN_RESULT = {
        'status': 'success',
        'exit_code': 0,
        'duration_seconds': 5,
        'log_file': '',
        'command': './pw module-tests plan-marshall',
    }

    @staticmethod
    def _parser(_log_file):
        return [], None, 'FAILURE'

    @pytest.fixture
    def spy(self, monkeypatch):
        """Record every call to the two guarded finding-store seams."""
        calls: dict[str, list] = {'store': [], 'reconcile': []}
        monkeypatch.setattr(
            _build_shared,
            '_store_build_findings',
            lambda **kwargs: (calls['store'].append(kwargs['plan_id']), (0, 0, []))[1],
        )
        monkeypatch.setattr(
            _build_shared,
            '_reconcile_pending_build_findings',
            lambda **kwargs: (calls['reconcile'].append(kwargs['plan_id']), 0)[1],
        )
        return calls

    @pytest.mark.parametrize('plan_id', [None, '', 'NO_PLAN'])
    def test_sentinel_suppresses_producer_side_finding_storage(self, spy, plan_id, capsys):
        _build_shared.cmd_run_common(
            self._FAILING_RESULT, self._parser, tool_name='python',
            output_format='json', plan_id=plan_id,
        )
        capsys.readouterr()

        assert spy['store'] == [], (
            f'plan_id={plan_id!r} stored findings into a plan-less finding store'
        )

    @pytest.mark.parametrize('plan_id', [None, '', 'NO_PLAN'])
    def test_sentinel_suppresses_green_build_reconciliation(self, spy, plan_id, capsys):
        _build_shared.cmd_run_common(
            self._GREEN_RESULT, self._parser, tool_name='python',
            output_format='json', plan_id=plan_id,
        )
        capsys.readouterr()

        assert spy['reconcile'] == [], (
            f'plan_id={plan_id!r} bulk-resolved findings in a plan-less store'
        )

    def test_a_real_plan_id_engages_producer_side_finding_storage(self, spy, capsys):
        _build_shared.cmd_run_common(
            self._FAILING_RESULT, self._parser, tool_name='python',
            output_format='json', plan_id='a-real-plan',
        )
        capsys.readouterr()

        assert spy['store'] == ['a-real-plan']

    def test_a_real_plan_id_engages_green_build_reconciliation(self, spy, capsys):
        _build_shared.cmd_run_common(
            self._GREEN_RESULT, self._parser, tool_name='python',
            output_format='json', plan_id='a-real-plan',
        )
        capsys.readouterr()

        assert spy['reconcile'] == ['a-real-plan']


class TestRecordProducerMismatchPersist:
    """``_record_producer_mismatch`` reports a REJECTED persist to its caller.

    The emitter's whole purpose is to report findings that were lost, so its own
    persist can never be fire-and-forget. It returns ``None`` on an in-store
    outcome and a failure descriptor on a rejection — the signature change from
    ``-> None`` that lets the caller propagate ``qgate_persist_failed``.
    """

    @staticmethod
    def _record(plan_id):
        return _build_shared._record_producer_mismatch(
            plan_id=plan_id,
            tool_name='python',
            command_str='./pw module-tests plan-marshall',
            count_seen=3,
            count_stored=1,
            store_failures=['assert 1 == 2'],
        )

    def test_landed_persist_returns_none(self, plan_context):
        """A finding that reached the store yields no failure descriptor."""
        assert self._record('build-shared-persist-ok') is None

    def test_deduplicated_persist_stays_benign(self, plan_context):
        """A ``deduplicated`` re-persist is still in the store — still ``None``.

        The benign no-op must never collapse onto the rejection signal.
        """
        plan_id = 'build-shared-persist-dedup'
        assert self._record(plan_id) is None
        assert self._record(plan_id) is None

    def test_rejected_persist_returns_failure_descriptor(self, plan_context, monkeypatch):
        """A REJECTED persist returns the finding content plus the primitive's message.

        Driven by the real validator — ``build-error`` removed from the live
        ``FINDING_TYPES`` — not a synthetic persist mock.
        """
        import _findings_core

        monkeypatch.setattr(
            _findings_core,
            'FINDING_TYPES',
            tuple(t for t in _findings_core.FINDING_TYPES if t != 'build-error'),
        )

        failure = self._record('build-shared-persist-reject')

        assert failure is not None
        assert '(producer-mismatch)' in failure['title']
        assert 'count_stored=1' in failure['detail']
        assert './pw module-tests plan-marshall' in failure['detail']
        assert 'Invalid finding type' in failure['message']
