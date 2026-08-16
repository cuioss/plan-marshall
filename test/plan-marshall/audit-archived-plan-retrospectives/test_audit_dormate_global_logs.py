#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``dormate_global_logs`` — a confirmed-gated move of past-dated global log files,
inert without ``--confirmed`` and never moving the current day's file.
"""

from datetime import datetime, timedelta
from pathlib import Path

from _audit_fixtures import audit


def _logs_dir(repo_root: Path) -> Path:
    """Path to ``{repo_root}/.plan/local/logs`` (the dormation source dir)."""
    return repo_root / '.plan' / 'local' / 'logs'


def _dormated_global_logs_dir(repo_root: Path) -> Path:
    """Path to the dormation destination ``dormated-plans/global-logs``."""
    return repo_root / '.plan' / 'temp' / 'dormated-plans' / 'global-logs'


def _seed_log_file(repo_root: Path, name: str, body: str = 'line\n') -> Path:
    """Create a single global-log file under the dormation source dir."""
    logs_dir = _logs_dir(repo_root)
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / name
    path.write_text(body, encoding='utf-8')
    return path


def _past_date_stamp(days_back: int = 1) -> str:
    """A ``YYYY-MM-DD`` stamp strictly before today (default: yesterday)."""
    return (datetime.now().date() - timedelta(days=days_back)).strftime('%Y-%m-%d')


def _today_stamp() -> str:
    """Today's ``YYYY-MM-DD`` stamp — the still-active log that must never move."""
    return datetime.now().date().strftime('%Y-%m-%d')


class TestDormateGlobalLogs:
    """``dormate_global_logs`` mirrors ``dormate_plan``: inert without
    ``--confirmed``, moves only COMPLETE past-date ``{prefix}-YYYY-MM-DD.log``
    files, never touches today's still-active log, and refuses (never
    overwrites) on a destination-name clash."""

    def test_inert_without_confirmed(self, tmp_path: Path):
        # a past-date log that WOULD be eligible if confirmed
        _seed_log_file(tmp_path, f'work-{_past_date_stamp()}.log')

        # inert path fires before any scan/move
        result = audit.dormate_global_logs(tmp_path, confirmed=False)

        # refused, nothing moved, source file untouched
        assert result['status'] == 'refused'
        assert result['moved'] == []
        assert 'requires --confirmed' in result['reason']
        assert (_logs_dir(tmp_path) / f'work-{_past_date_stamp()}.log').exists()

    def test_missing_logs_dir_is_noop_success(self, tmp_path: Path):
        # no .plan/local/logs dir at all

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # clean no-op, not an error
        assert result['status'] == 'success'
        assert result['moved'] == []

    def test_past_date_logs_moved(self, tmp_path: Path):
        # three distinct-prefix past-date logs
        yesterday = _past_date_stamp(1)
        older = _past_date_stamp(5)
        _seed_log_file(tmp_path, f'work-{yesterday}.log')
        _seed_log_file(tmp_path, f'decision-{older}.log')
        _seed_log_file(tmp_path, f'script-execution-{older}.log')

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # all three relocated, sorted, source emptied of them
        assert result['status'] == 'success'
        assert result['moved'] == sorted(
            [
                f'work-{yesterday}.log',
                f'decision-{older}.log',
                f'script-execution-{older}.log',
            ]
        )
        dest = _dormated_global_logs_dir(tmp_path)
        for name in result['moved']:
            assert (dest / name).exists()
            assert not (_logs_dir(tmp_path) / name).exists()

    def test_today_active_log_not_moved(self, tmp_path: Path):
        # today's log (still active) plus one past-date log
        today_name = f'work-{_today_stamp()}.log'
        past_name = f'work-{_past_date_stamp()}.log'
        _seed_log_file(tmp_path, today_name)
        _seed_log_file(tmp_path, past_name)

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # only the past-date log moved; today's stays put
        assert result['status'] == 'success'
        assert result['moved'] == [past_name]
        assert (_logs_dir(tmp_path) / today_name).exists()
        assert not (_dormated_global_logs_dir(tmp_path) / today_name).exists()

    def test_non_dated_files_ignored(self, tmp_path: Path):
        # files that do NOT match the dated-log grammar
        _seed_log_file(tmp_path, 'work.log')  # no date segment
        _seed_log_file(tmp_path, 'notes.txt')  # wrong extension
        _seed_log_file(tmp_path, 'work-2026-13-99.log')  # date-shaped but invalid

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # nothing eligible; all source files remain
        assert result['status'] == 'success'
        assert result['moved'] == []
        assert (_logs_dir(tmp_path) / 'work.log').exists()
        assert (_logs_dir(tmp_path) / 'notes.txt').exists()
        assert (_logs_dir(tmp_path) / 'work-2026-13-99.log').exists()

    def test_refuse_on_existing_destination_never_overwrites(self, tmp_path: Path):
        # a past-date source AND a colliding file already at the dest
        past_name = f'work-{_past_date_stamp()}.log'
        _seed_log_file(tmp_path, past_name, body='SOURCE CONTENT\n')
        dest_dir = _dormated_global_logs_dir(tmp_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        clash = dest_dir / past_name
        clash.write_text('PRE-EXISTING\n', encoding='utf-8')

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # all-or-nothing refusal; neither side mutated
        assert result['status'] == 'error'
        assert result['moved'] == []
        assert 'already exists' in result['reason']
        assert clash.read_text(encoding='utf-8') == 'PRE-EXISTING\n'
        assert (_logs_dir(tmp_path) / past_name).read_text(encoding='utf-8') == 'SOURCE CONTENT\n'

    def test_refuse_on_exists_is_all_or_nothing(self, tmp_path: Path):
        # two eligible past-date logs; one collides at the dest.
        # The refuse-on-exists pre-check must abort BEFORE moving the clean one.
        collide_name = f'work-{_past_date_stamp(1)}.log'
        clean_name = f'decision-{_past_date_stamp(2)}.log'
        _seed_log_file(tmp_path, collide_name)
        _seed_log_file(tmp_path, clean_name)
        dest_dir = _dormated_global_logs_dir(tmp_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / collide_name).write_text('PRE-EXISTING\n', encoding='utf-8')

        result = audit.dormate_global_logs(tmp_path, confirmed=True)

        # refused, and the non-colliding source was NOT partially moved
        assert result['status'] == 'error'
        assert result['moved'] == []
        assert (_logs_dir(tmp_path) / clean_name).exists()
        assert not (dest_dir / clean_name).exists()

    def test_filename_grammar_excludes_path_separators(self):
        # the dated-log regex never matches a name
        # carrying a path separator, complementing the is_relative_to guards so
        # a crafted entry cannot escape the source dir via the capture group.
        assert audit._GLOBAL_LOG_RE.match('work-2026-05-31.log') is not None
        assert audit._GLOBAL_LOG_RE.match('../escape-2026-05-31.log') is None
        assert audit._GLOBAL_LOG_RE.match('a/b-2026-05-31.log') is None
        assert audit._GLOBAL_LOG_RE.match('/abs-2026-05-31.log') is None
