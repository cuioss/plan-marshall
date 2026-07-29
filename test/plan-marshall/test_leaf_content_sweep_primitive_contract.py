#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Doc-contract sweep for the dispatched leaf's broad-content-sweep primitive.

A dispatched ``execution-context`` leaf whose runtime grant omits ``Grep``/``Glob``
needs a working primitive for a broad content sweep across prose. ``git grep`` is
that primitive — the single sanctioned carve-out to the "Bash: No file operations"
hard rule. This module pins the contract across every documentation site that
describes it, so a future edit cannot quietly reinstate the retired
"no Bash fallback exists" instruction at one site while the others say otherwise.

Six sites, split into two groups because they carry different prose shapes:

* **Carve-out / degradation sites (4)** — ``persona-plan-marshall-agent/SKILL.md``
  (the carve-out home, which must additionally state the three bounds),
  ``persona-plan-marshall-agent/standards/tool-usage-patterns.md``,
  ``agents/execution-context.md``, and
  ``ref-workflow-architecture/standards/agents.md``. These carry the full prose.
* **Hand-maintained hard-rule mirrors (2)** — ``CLAUDE.md`` and ``AGENTS.md``.
  These carry only a one-line pointer, so they are asserted against the pointer
  shape (the no-shell-file-operations bullet names ``git grep`` and references
  ``plan-marshall:persona-plan-marshall-agent``), never the full carve-out prose.

Three properties are pinned:

1. **Presence** — every site names the primitive; the carve-out home additionally
   states all three bounds (git-tracked files only, the one-command-per-call
   pattern-character rule, and no carve-out for ``cat``/``head``/``tail``/
   ``find``/``ls``).
2. **Absence of the retired instruction** — the retired "NOT a fallback" claim and
   the terminal "rather than passing green with {shrunken,reduced} coverage"
   degradation instruction no longer appear in any of the four degradation sites.
   Both anchors are present on the pre-fix tree, so this half cannot pass
   vacuously.
3. **Invocability** — the invocation form is read *out of* the carve-out doc at
   runtime (never hard-coded) and asserted not denied by any of R1-R4 under a
   gated payload. Reading the form from the doc means doc-vs-hook drift trips this
   test too — a failure mode a literal-payload test cannot see.

The ``_R2_FILE_OPS`` bound is deliberately NOT re-asserted here:
``test_r2_denies_each_file_op`` in
``test/plan-marshall/platform-runtime/test_claude_pretooluse_hook.py`` already
iterates that six-tuple and asserts ``evaluate()`` returns ``_R2_REASON`` for each,
which is a strictly stronger behavioural pin than re-reading the constant.

This module sweeps an explicit six-path tuple rather than walking a directory, so
it is structurally excluded from its own presence sweep — it can never scan itself,
even though it carries the retired phrases as string literals.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from conftest import PROJECT_ROOT, get_script_path

_HOOK_PATH = get_script_path(
    "plan-marshall", "platform-runtime", "claude_pretooluse_hook.py"
)

if str(_HOOK_PATH.parent) not in sys.path:
    sys.path.insert(0, str(_HOOK_PATH.parent))

import pretooluse_gate as gate  # noqa: E402
import claude_pretooluse_hook as hook  # noqa: E402


_BUNDLE = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall'

#: The carve-out home — the one site required to state all three bounds.
_CARVE_OUT_HOME = _BUNDLE / 'skills' / 'persona-plan-marshall-agent' / 'SKILL.md'

#: The four sites carrying the full carve-out / degradation prose.
_DEGRADATION_SITES = (
    _CARVE_OUT_HOME,
    _BUNDLE / 'skills' / 'persona-plan-marshall-agent' / 'standards' / 'tool-usage-patterns.md',
    _BUNDLE / 'agents' / 'execution-context.md',
    _BUNDLE / 'skills' / 'ref-workflow-architecture' / 'standards' / 'agents.md',
)

#: The two hand-maintained root-doc mirrors of the hard rule.
_HARD_RULE_MIRRORS = (
    PROJECT_ROOT / 'CLAUDE.md',
    PROJECT_ROOT / 'AGENTS.md',
)

#: The sanctioned primitive, as it must be named at every site.
_PRIMITIVE = 'git grep'

#: The bullet the two mirrors carry the one-line pointer on.
_MIRROR_BULLET = 'No shell file operations'

#: The skill the mirrors must point at for the substance.
_MIRROR_POINTER = 'plan-marshall:persona-plan-marshall-agent'

#: The three bounds the carve-out home must state, as (label, pattern) pairs.
_BOUNDS = (
    ('git-tracked files only', re.compile(r'[Gg]it-tracked files only')),
    ('one-command-per-call still binds', re.compile(r'one-command-per-call')),
    (
        'no carve-out for cat/head/tail/find/ls',
        re.compile(r'`cat`.*`head`.*`tail`.*`find`.*`ls`'),
    ),
)

#: Retired instructions that must not survive at any degradation site. Both were
#: present on the pre-fix tree, so assertion 2 cannot pass vacuously.
_RETIRED = (
    ('"NOT a fallback" claim', re.compile(r'NOT a fallback')),
    (
        'terminal degrade-to-coverage-gap instruction',
        re.compile(r'rather than passing green with'),
    ),
)

#: Extracts the worked ``git grep`` invocation out of the carve-out doc.
_INVOCATION_RE = re.compile(r"Bash\(command='(git grep .+?)'\)")


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _hits(path: Path, pattern: re.Pattern[str]) -> list[str]:
    """Return ``relpath:lineno: line`` hits for ``pattern`` inside ``path``."""
    rel = path.relative_to(PROJECT_ROOT)
    return [
        f'{rel}:{lineno}: {line.strip()}'
        for lineno, line in enumerate(_read(path).splitlines(), start=1)
        if pattern.search(line)
    ]


# =============================================================================
# (1) Presence — every site names the primitive
# =============================================================================


def test_every_degradation_site_names_the_primitive() -> None:
    """All four carve-out / degradation sites name ``git grep``."""
    missing = [
        str(path.relative_to(PROJECT_ROOT))
        for path in _DEGRADATION_SITES
        if _PRIMITIVE not in _read(path)
    ]
    assert not missing, (
        f'Documentation site(s) do not name the sanctioned broad-content-sweep '
        f'primitive {_PRIMITIVE!r}:\n  ' + '\n  '.join(missing)
    )


def test_carve_out_home_states_all_three_bounds() -> None:
    """The carve-out home states every bound the primitive is granted under."""
    text = _read(_CARVE_OUT_HOME)
    missing = [label for label, pattern in _BOUNDS if not pattern.search(text)]
    rel = _CARVE_OUT_HOME.relative_to(PROJECT_ROOT)
    assert not missing, (
        f'{rel} names {_PRIMITIVE!r} but omits bound(s):\n  ' + '\n  '.join(missing)
    )


def test_hard_rule_mirrors_carry_the_one_line_pointer() -> None:
    """Both hand-maintained mirrors qualify their bullet and point at the skill."""
    offenders: list[str] = []
    for path in _HARD_RULE_MIRRORS:
        rel = path.relative_to(PROJECT_ROOT)
        bullets = [
            line for line in _read(path).splitlines() if _MIRROR_BULLET in line
        ]
        if not bullets:
            offenders.append(f'{rel}: no {_MIRROR_BULLET!r} bullet found')
            continue
        for bullet in bullets:
            if _PRIMITIVE not in bullet:
                offenders.append(f'{rel}: bullet does not name {_PRIMITIVE!r}')
            elif _MIRROR_POINTER not in bullet:
                offenders.append(f'{rel}: bullet does not point at {_MIRROR_POINTER!r}')
    assert not offenders, (
        'Hand-maintained hard-rule mirror(s) contradict the carve-out:\n  '
        + '\n  '.join(offenders)
    )


# =============================================================================
# (2) Absence — the retired no-fallback instruction is gone
# =============================================================================


def test_no_degradation_site_retains_the_retired_instruction() -> None:
    """No degradation site still tells the leaf that no Bash fallback exists."""
    for label, pattern in _RETIRED:
        hits = [hit for path in _DEGRADATION_SITES for hit in _hits(path, pattern)]
        assert not hits, (
            f'Retired {label} still present ({len(hits)} hit(s)):\n  '
            + '\n  '.join(hits)
        )


# =============================================================================
# (3) Invocability — the doc-quoted form survives R1-R4
# =============================================================================


def test_doc_quoted_invocation_is_not_denied_by_the_hook() -> None:
    """The form the carve-out quotes is one a Bash-granted leaf can actually run."""
    match = _INVOCATION_RE.search(_read(_CARVE_OUT_HOME))
    rel = _CARVE_OUT_HOME.relative_to(PROJECT_ROOT)
    assert match is not None, (
        f'{rel} does not carry a worked Bash(command=\'git grep ...\') invocation '
        f'for the carve-out — the doc-vs-hook drift check has nothing to read.'
    )
    command = match.group(1)
    payload = {
        gate.CWD_FIELD: f'/Users/dev/project/{gate.WORKTREE_PATH_SEGMENT}/my-plan',
        'tool_name': 'Bash',
        'tool_input': {'command': command},
    }
    decision = hook.evaluate(payload)
    assert decision is None, (
        f'The invocation quoted in {rel} is denied by the PreToolUse hook: '
        f'{command!r} -> {decision!r}'
    )
