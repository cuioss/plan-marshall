#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Resolve the PR-PENDING era-stamp sentinel to the real PR number, in lock-step.

This is the backing executor for `project:finalize-step-era-stamp-fill`. It scans
`audit.py`'s `CHECK_ERA` map (and its `test_audit.py` mirror) for the double-quoted
``"PR-PENDING"`` sentinel and rewrites it to ``"#{pr_number}"`` in both files, so the
era stamp of the check this plan reworks resolves to the plan's own PR number. The
step is ordered post-`create-pr` / pre-merge (order 21) so the correction is
pushable and rides the PR — the general pre-merge source-edit contract.

Design:
- **Literal double-quoted-token substitution.** Only the map-value form
  ``"PR-PENDING"`` is matched, so prose mentions of PR-PENDING in comments are never
  touched and an already-resolved concrete ``"#NNN"`` is never re-resolved.
- **Lock-step.** The identical substitution is applied to both `audit.py` and its
  `test_audit.py` mirror, and the writes are staged then flushed together (nothing
  is written when the token is absent).
- **No-op / skipped.** When no ``"PR-PENDING"`` token is present the step is a
  clean no-op (`skipped: true`), so it is safe to register unconditionally, and a
  second run after a resolution is idempotent.

Stdlib-only and self-contained: this script is invoked DIRECTLY (not through the
executor) because it runs at order 21, before the finalize executor-regeneration
step (order 85) would add its mapping. The pure helpers (`normalize_pr_number`,
`fill_pending_token`) are unit-testable without any files or PYTHONPATH.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

# Paths relative to the worktree root.
AUDIT_REL = '.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py'
TEST_REL = 'test/plan-marshall/audit-archived-plan-retrospectives/test_audit.py'

# The double-quoted map-value sentinel. Matching the quoted form guarantees prose
# mentions of PR-PENDING (in comments/backticks) and a concrete "#NNN" are untouched.
PENDING_TOKEN = '"PR-PENDING"'


def normalize_pr_number(pr_number: str) -> str:
    """Normalize a PR reference to the canonical ``#NNN`` form.

    Accepts ``877`` or ``#877``; rejects any non-numeric residue with ValueError.
    """
    stripped = str(pr_number).strip().lstrip('#')
    if not stripped.isdigit():
        raise ValueError(f'pr-number must be numeric (got {pr_number!r})')
    return f'#{stripped}'


def fill_pending_token(text: str, pr_ref: str) -> tuple[str, int]:
    """Replace each double-quoted ``"PR-PENDING"`` sentinel with the quoted ``pr_ref``.

    ``pr_ref`` is the already-normalized ``#NNN`` form. Returns
    ``(new_text, replacement_count)``; when the token is absent the text is
    returned unchanged with a count of 0.
    """
    count = text.count(PENDING_TOKEN)
    if not count:
        return text, 0
    return text.replace(PENDING_TOKEN, f'"{pr_ref}"'), count


def _emit(fields: dict[str, object]) -> None:
    """Emit a flat TOON document (one ``key: value`` line per field)."""
    for key, value in fields.items():
        sys.stdout.write(f'{key}: {value}\n')


def _atomic_write(path: pathlib.Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically via a temp file + replace."""
    tmp = path.with_name(path.name + '.era-tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def run(pr_number: str, worktree_path: str) -> int:
    """Resolve the PR-PENDING sentinel across audit.py and its mirror.

    Returns 0 on success (including the skipped no-op) and 1 on error (bad
    pr-number or a missing target file). Writes nothing when the token is absent.
    """
    try:
        pr_ref = normalize_pr_number(pr_number)
    except ValueError as exc:
        _emit({'status': 'error', 'message': str(exc)})
        return 1

    root = pathlib.Path(worktree_path)
    planned: list[tuple[pathlib.Path, str, int]] = []
    total = 0
    for rel in (AUDIT_REL, TEST_REL):
        path = root / rel
        if not path.exists():
            _emit({'status': 'error', 'message': f'target not found: {path}'})
            return 1
        new_text, count = fill_pending_token(path.read_text(encoding='utf-8'), pr_ref)
        planned.append((path, new_text, count))
        total += count

    if total == 0:
        _emit({'status': 'success', 'filled_count': 0, 'skipped': 'true', 'pr_number': pr_ref})
        return 0

    # Flush both files together — nothing was written above, so a resolution is
    # applied to both the source and its mirror in lock-step.
    for path, new_text, count in planned:
        if count:
            _atomic_write(path, new_text)

    _emit({'status': 'success', 'filled_count': total, 'skipped': 'false', 'pr_number': pr_ref})
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            'Resolve the PR-PENDING era-stamp sentinel to the real PR number across '
            'audit.py and its test mirror, in lock-step. Emits flat TOON.'
        ),
        allow_abbrev=False,
    )
    parser.add_argument('command', choices=['run'], help='Subcommand (only `run`).')
    parser.add_argument('--plan-id', required=True, help='Plan identifier (contract; used for logging).')
    parser.add_argument('--pr-number', required=True, help='The real PR number (accepts NNN or #NNN).')
    parser.add_argument(
        '--worktree-path',
        default='.',
        help='Worktree root the audit.py + test mirror are resolved against (default: cwd).',
    )
    args = parser.parse_args(argv)
    return run(args.pr_number, args.worktree_path)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
