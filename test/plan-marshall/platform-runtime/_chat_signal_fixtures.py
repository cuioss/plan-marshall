# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared fixture builders for the platform-runtime chat-signal reducer tests.

Holds the transcript-shape builders and the harness-injection block shapes the
``chat extract-signal`` reducer tests exercise. These model the transcript
FORMAT the runtime op owns, so they live beside the reducer tests that read
them; the plan-retrospective consumer tests no longer build transcripts at all
and instead drive the consumer against a mocked runtime-op hop.
"""

from __future__ import annotations

import json

# Harness-injection block shapes (chat-signal reduction).
#
# The shapes the harness actually injects, shared by the chat-signal test
# modules so one definition backs both the predicate tests and the reducer's
# output-contract tests.

SYSTEM_REMINDER = (
    '<system-reminder>\n'
    "As you answer the user's questions, you can use the following context:\n"
    '# claudeMd\nCodebase and user instructions are shown below.\n'
    '</system-reminder>'
)

# The shape observed verbatim in a real session transcript: attribute-less, with
# nested children, and multi-paragraph prose inside <result>. An invented flat
# one-line variant would not exercise nested-envelope-containing-prose at all.
TASK_NOTIFICATION = (
    '<task-notification>\n'
    '<task-id>a82b5c26048205450</task-id>\n'
    '<tool-use-id>toolu_0152fq8UnwvZDd6aieSbPXJh</tool-use-id>\n'
    '<output-file>/tmp/tasks/a82b5c26048205450.output</output-file>\n'
    '<status>completed</status>\n'
    '<summary>Agent "Verify work against plan" finished</summary>\n'
    '<result>Verification complete.\n\n'
    'The branch moved twice during the review; everything below is verified\n'
    'against HEAD, working tree clean.\n\n'
    '## Deliverable verdicts\n\n'
    'D1 implemented as specified. D2 partially — an over-claiming comment was\n'
    'reintroduced. Report every gap with file and symbol.\n'
    '</result>\n'
    '</task-notification>'
)

WAKE_ENVELOPE = (
    '<wake reason="external-event">'
    '<event source="github" kind="check_run" trust="relay">'
    '{"check": "verify / conclusion", "conclusion": "failure"}'
    '</event></wake>'
)

SLASH_COMMAND = (
    '<command-name>/plan-marshall</command-name>\n'
    '<command-message>plan-marshall is running…</command-message>\n'
    '<command-args>fix the provenance filter</command-args>'
)

SKILL_LOAD_TEXT = (
    'Base directory for this skill: /home/dev/.claude/plugins/cache/demo/skills/demo\n\n'
    '# Demo Skill\n\n'
    'Long injected skill body. ' * 40
)

REENTRY_NOTICE = (
    'This session is being continued from a previous conversation that ran out of '
    'context. The conversation is summarized below.'
)

STOP_HOOK_NOTICE = (
    'Stop hook feedback:\n'
    '[~/.claude/stop-hook-git-check.sh]: There are uncommitted changes in the repository.'
)

OPERATOR_TEXT = 'stop using the ratio as the check — validate by classification instead'


def chat_turn(role: str, content) -> str:
    """Produce one JSONL event line carrying a ``message`` with ``role``/``content``."""
    return json.dumps({'type': 'turn', 'message': {'role': role, 'content': content}})


def chat_tool_use(name: str, use_id: str) -> str:
    """Produce an assistant turn issuing a ``tool_use`` call."""
    return chat_turn('assistant', [{'type': 'tool_use', 'name': name, 'id': use_id}])


def chat_tool_result(use_id: str, text: str) -> str:
    """Produce a user turn carrying a ``tool_result`` — the gated-decision channel."""
    return chat_turn('user', [{'type': 'tool_result', 'tool_use_id': use_id, 'content': text}])


def chat_text_blocks(*texts: str) -> list[dict[str, str]]:
    """Build a list of ``text`` content blocks (the common multi-block shape)."""
    return [{'type': 'text', 'text': t} for t in texts]


def write_jsonl(path, *lines: str) -> None:
    """Write JSONL ``lines`` (each already a serialized event) to ``path``."""
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
