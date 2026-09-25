#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2


def _bare(steps: list[str]) -> set[str]:
    """Strip the ``default:`` / ``project:`` prefix from each step for membership checks."""
    out: set[str] = set()
    for s in steps:
        for prefix in ('default:', 'project:'):
            if s.startswith(prefix):
                s = s[len(prefix) :]
                break
        out.add(s)
    return out
