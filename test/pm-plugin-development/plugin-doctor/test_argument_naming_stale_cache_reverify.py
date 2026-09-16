#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Stale cached accept-sets are re-probed live, never accused.

Empirical basis: the marketplace-wide gate failed on
``ARGUMENT_NAMING_FLAG_UNKNOWN`` for ``ci pr list --limit`` in
``phase-6-finalize/standards/branch-cleanup.md``, yet ``ci pr list --help``
declares ``--limit``. The derivation digest (entry script plus same-directory
siblings) cannot see the provider ``{provider}_ops`` modules that declare the
flag, so an edit there serves the cached surface describing the parser that
used to exist — and the unknown-flag rule accused a valid call out of that
too-small set.

Three matched tests, because the fix has three halves that can each fail
alone:

1. **Positive** — a flag added to a surface-defining file OUTSIDE the digest
   scope, after the cache entry was written, must NOT be reported.
2. **Negative** — a genuinely undeclared flag on the same invocation MUST
   still be reported. Without this control, the test above is satisfied by a
   rule that stopped reporting anything.
3. **Heal persistence** — after the re-probe, a fresh index built with an
   empty memo must already know the flag (the refresh wrote the disk entry
   through). Without this control, every run pays a live re-probe and a
   dropped write-through goes unnoticed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _plugin_doctor_dispatching_executor import write_dispatching_executor
from conftest import load_script_module

_aan = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_argument_naming.py',
    '_analyze_argument_naming_stale_cache',
)
build_script_index = _aan.build_script_index
scan_flag = _aan.scan_flag

NOTATION = 'synth:router:router'

#: Flags present when the cache entry is first derived.
SEEDED_FLAG = 'alpha'

#: Flag added to the out-of-digest-scope data file AFTER the cache entry exists.
LATE_FLAG = 'beta'

#: Flag no surface ever declares — the matched negative half.
UNKNOWN_FLAG = 'gamma'


def _write_router_script(marketplace_root: Path) -> None:
    """Write a synthetic script whose flags come from outside the digest scope.

    The ``run`` verb declares one ``--flag`` per line of
    ``marketplace/provider-data/flags.txt``. That data file is outside the
    entry script's own directory, so :func:`content_hash` never covers it —
    exactly the ``ci`` router / provider ``{provider}_ops`` shape that
    produced the stale accept-set in production.
    """
    scripts_dir = marketplace_root / 'bundles' / 'synth' / 'skills' / 'router' / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    parts = [
        '#!/usr/bin/env python3',
        '"""Synthetic router with an out-of-digest-scope flag source."""',
        'import argparse',
        'from pathlib import Path',
        '',
        'def _data_file():',
        '    for parent in Path(__file__).resolve().parents:',
        "        if parent.name == 'marketplace' and (parent / 'bundles').is_dir():",
        "            return parent / 'provider-data' / 'flags.txt'",
        '    return None',
        '',
        '',
        'def _flag_names():',
        '    data = _data_file()',
        '    if data is None:',
        '        return []',
        '    try:',
        '        return data.read_text(encoding="utf-8").split()',
        '    except OSError:',
        '        return []',
        '',
        '',
        'parser = argparse.ArgumentParser(prog="router")',
        'subparsers = parser.add_subparsers(dest="command")',
        'p = subparsers.add_parser("run")',
        'for _name in _flag_names():',
        '    p.add_argument(f"--{_name}")',
        '',
        'if __name__ == "__main__":',
        '    parser.parse_args()',
    ]
    (scripts_dir / 'router.py').write_text('\n'.join(parts) + '\n', encoding='utf-8')


def _write_flags(marketplace_root: Path, *names: str) -> None:
    data_dir = marketplace_root / 'provider-data'
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / 'flags.txt').write_text('\n'.join(names) + '\n', encoding='utf-8')


def _write_invocation(marketplace_root: Path, invocation: str) -> None:
    skill_dir = marketplace_root / 'bundles' / 'synth' / 'skills' / 'router'
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'SKILL.md').write_text(
        f'# Router\n\n```bash\npython3 .plan/execute-script.py {invocation}\n```\n',
        encoding='utf-8',
    )


def _fixture(tmp_path: Path) -> Path:
    """Materialize the fixture tree and return the marketplace root."""
    marketplace_root = tmp_path / 'marketplace'
    write_dispatching_executor(tmp_path / '.plan', [NOTATION])
    _write_router_script(marketplace_root)
    return marketplace_root


def _flag_findings(marketplace_root: Path, index: dict) -> list[dict]:
    return [f for f in scan_flag(marketplace_root, index) if f.get('rule_id') == 'ARGUMENT_NAMING_FLAG_UNKNOWN']


def test_flag_added_outside_the_digest_scope_is_not_reported(tmp_path):
    """The positive half: a late but declared flag must NOT be flagged.

    Arrange: derive the index while only ``alpha`` exists (populating the
    on-disk cache), then declare ``beta`` out of digest scope. Act: scan a
    line carrying ``--beta``. Assert: no finding — the rule re-probed live
    instead of accusing out of the stale set.
    """
    marketplace_root = _fixture(tmp_path)
    _write_flags(marketplace_root, SEEDED_FLAG)
    index = build_script_index({NOTATION}, marketplace_root)

    _write_flags(marketplace_root, SEEDED_FLAG, LATE_FLAG)
    _write_invocation(marketplace_root, f'{NOTATION} run --{LATE_FLAG} X')

    findings = _flag_findings(marketplace_root, index)
    assert findings == [], f'late-but-declared --{LATE_FLAG} reported as an invented flag: {findings!r}'


def test_genuinely_unknown_flag_on_the_same_line_is_still_reported(tmp_path):
    """The negative half: the re-probe must not disable the rule.

    Same script, same verb, one line carrying both the late-declared
    ``--beta`` and the never-declared ``--gamma``: exactly one finding,
    naming ``gamma``. Without this control, the test above is satisfied by a
    rule that stopped reporting anything at all.
    """
    marketplace_root = _fixture(tmp_path)
    _write_flags(marketplace_root, SEEDED_FLAG)
    index = build_script_index({NOTATION}, marketplace_root)

    _write_flags(marketplace_root, SEEDED_FLAG, LATE_FLAG)
    _write_invocation(marketplace_root, f'{NOTATION} run --{LATE_FLAG} X --{UNKNOWN_FLAG} Y')

    findings = _flag_findings(marketplace_root, index)
    assert len(findings) == 1, findings
    assert findings[0]['details']['flag'] == UNKNOWN_FLAG


def test_reprobe_heals_the_disk_entry_for_later_runs(tmp_path):
    """The persistence half: the live re-probe must write through.

    Arrange: as in the positive test, then scan once (healing the entry).
    Act: drop the in-process memo and build a FRESH index — it reads the
    on-disk entry with no live probe to rescue it. Assert: still no finding,
    proving the heal landed on disk rather than living for one scan only.
    """
    marketplace_root = _fixture(tmp_path)
    _write_flags(marketplace_root, SEEDED_FLAG)
    index = build_script_index({NOTATION}, marketplace_root)

    _write_flags(marketplace_root, SEEDED_FLAG, LATE_FLAG)
    _write_invocation(marketplace_root, f'{NOTATION} run --{LATE_FLAG} X')
    assert _flag_findings(marketplace_root, index) == []

    surf = sys.modules['argparse_surface']
    surf.clear_memo()
    fresh_index = build_script_index({NOTATION}, marketplace_root)

    findings = _flag_findings(marketplace_root, fresh_index)
    assert findings == [], f'healed entry did not persist to disk: {findings!r}'
