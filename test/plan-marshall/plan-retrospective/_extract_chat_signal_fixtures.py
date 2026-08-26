# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``extract chat signal`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Parsing, reduction and output-contract tests for ``extract-chat-signal.py``.

The script reduces a Claude Code session JSONL transcript to its
signal-bearing turns (Aspect 14 of ``plan-retrospective``). It keeps every
OPERATOR-AUTHORED ``user`` turn and every ``assistant`` turn carrying a decision
marker, dropping everything else. A ``user`` turn is operator-authored when
prose remains after every harness envelope is stripped — a positive predicate,
not an enumeration of the synthetic shapes anyone happened to have seen. It
then emits a TOON payload carrying the two Tier-2 trigger flags:

- ``no_signal`` — true when the transcript carried no operator-authored signal
  of either kind: ``operator_turn_count == 0`` AND ``gate_decision_count == 0``.
- ``over_budget`` — true when the reduced text exceeds ``--read-budget-bytes``.

Either flag is the orchestrator's signal to fall back to the Tier-2 WARNING
finding (``reason: transcript_too_large``). A missing transcript yields
``status: skipped, reason: transcript_unavailable``.

Provenance classification is covered by ``test_chat_provenance.py``; the two
operator-signal counters and the routing verdict by
``test_extract_chat_signal_verdict.py``.
"""


from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


from conftest import MARKETPLACE_ROOT, load_script_module  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'extract-chat-signal.py'
)


# Direct module load so unit tests can poke the pure helpers.
_mod = load_script_module(
    'plan-marshall', 'plan-retrospective', 'extract-chat-signal.py', 'extract_chat_signal'
)


# The provenance predicate moved to its own module; this file exercises it only
# where the reduction's parsing behaviour depends on it.
_prov = load_script_module('plan-marshall', 'plan-retrospective', '_chat_provenance.py')


# ---------------------------------------------------------------------------
# JSONL turn builders
# ---------------------------------------------------------------------------


def _turn(role: str, content) -> str:
    """Produce one JSONL event line carrying a ``message`` with ``role``/``content``."""
    return json.dumps({'type': 'turn', 'message': {'role': role, 'content': content}})


def _text_blocks(*texts: str) -> list[dict[str, str]]:
    """Build a list of ``text`` content blocks (the common multi-block shape)."""
    return [{'type': 'text', 'text': t} for t in texts]


# The structural signature of a skill body injected as a synthetic ``user``
# turn: the base-directory line followed by a markdown heading and a body.
SKILL_LOAD_TEXT = (
    'Base directory for this skill: /home/dev/.claude/plugins/cache/demo/skills/demo\n\n'
    '# Demo Skill\n\n'
    'Long injected skill body. ' * 40
)


# ---------------------------------------------------------------------------
# Unit tests: cmd_run (pure, via a Namespace-like shim)
# ---------------------------------------------------------------------------


class _Args:
    """Minimal stand-in for ``argparse.Namespace`` carrying the two run args."""

    def __init__(self, transcript_path: str, read_budget_bytes: int):
        self.transcript_path = transcript_path
        self.read_budget_bytes = read_budget_bytes
