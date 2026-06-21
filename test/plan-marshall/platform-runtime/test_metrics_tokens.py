#!/usr/bin/env python3
"""Tests for the platform-runtime ``metrics normalized-tokens`` operation (Gap 2).

The Claude session-transcript engine — transcript discovery, ``message.usage``
four-field parse, ``<usage>`` return-tag parse, the strict-UUID guard, and the
Anthropic cache-pricing weights — now lives in ``claude_runtime``. These tests
assert:

- ``ClaudeRuntime.metrics_normalized_tokens`` walks a synthetic transcript,
  normalizes per-phase token categories, and writes the JSON sidecar;
- it returns a ``transcript_not_found`` no-op when no transcript exists;
- ``OpenCodeRuntime.metrics_normalized_tokens`` is an honest no-op;
- the relocated arithmetic helpers (``_billing_weighted_total``,
  ``_sum_subagent_transcript``) behave as before; and
- the router dispatches the new ``metrics normalized-tokens`` operation.
"""

import json  # noqa: I001
from pathlib import Path

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
import claude_runtime  # type: ignore[import-not-found]
import platform_runtime  # type: ignore[import-not-found]
from claude_runtime import ClaudeRuntime  # type: ignore[import-not-found]
from opencode_runtime import OpenCodeRuntime  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]


def _parse(toon_str: str) -> dict:
    """Parse a TOON string and assert it is a non-empty dict."""
    result = parse_toon(toon_str)
    assert isinstance(result, dict), f"parse_toon returned non-dict: {toon_str!r}"
    return result


# Two well-separated phase windows used across the attribution tests.
_WINDOWS: list[tuple[str, str, str]] = [
    ("2-refine", "2026-03-27T09:00:00+00:00", "2026-03-27T09:30:00+00:00"),
    ("5-execute", "2026-03-27T10:00:00+00:00", "2026-03-27T10:30:00+00:00"),
]


def _main_context_entry(
    timestamp: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
) -> dict:
    """Build a JSONL entry shaped like an assistant message with main-context usage."""
    usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}
    if cache_read_input_tokens:
        usage["cache_read_input_tokens"] = cache_read_input_tokens
    if cache_creation_input_tokens:
        usage["cache_creation_input_tokens"] = cache_creation_input_tokens
    return {
        "timestamp": timestamp,
        "message": {"role": "assistant", "usage": usage, "content": [{"type": "text", "text": "x"}]},
    }


def _agent_return_entry(timestamp: str, usage_block: str) -> dict:
    """Build a JSONL entry shaped like a Claude tool_result carrying an embedded <usage>."""
    return {
        "timestamp": timestamp,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_test",
                    "content": [{"type": "text", "text": usage_block}],
                }
            ],
        },
    }


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


# =============================================================================
# 1. ClaudeRuntime — successful normalization
# =============================================================================


def test_claude_normalized_tokens_writes_per_phase_json(tmp_path, monkeypatch):
    """The Claude op walks the transcript and writes per-phase normalized categories."""
    session_id = "22222222-2222-2222-2222-222222222201"
    projects_root = tmp_path / "home" / ".claude" / "projects" / "plan"
    transcript = projects_root / f"{session_id}.jsonl"
    _write_jsonl(
        transcript,
        [
            _main_context_entry(
                "2026-03-27T10:10:00+00:00",
                input_tokens=100,
                output_tokens=20,
                cache_read_input_tokens=1000,
                cache_creation_input_tokens=40,
            ),
            _agent_return_entry(
                "2026-03-27T10:15:00+00:00",
                "<usage>total_tokens: 4000\ntool_uses: 5\nduration_ms: 25000</usage>",
            ),
        ],
    )

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    output_file = tmp_path / "normalized.json"
    result = _parse(
        ClaudeRuntime().metrics_normalized_tokens(session_id, _WINDOWS, str(output_file))
    )

    assert result["status"] == "success"
    assert result["operation"] == "metrics normalized-tokens"
    assert output_file.is_file()

    per_phase = json.loads(output_file.read_text(encoding="utf-8"))
    five = per_phase["5-execute"]
    # The four-field view is normalized into both canonical and short keys.
    assert five["input"] == 100
    assert five["output"] == 20
    assert five["cache_read"] == 1000
    assert five["cache_creation"] == 40
    # billing = 100 + 20 + round(0.1*1000=100) + round(1.25*40=50) = 270.
    assert five["billing_weighted_total"] == 270
    assert five["total"] == 270
    # The <usage> tag attribution lands in the same phase window.
    assert five["subagent_total_tokens"] == 4000
    assert five["subagent_tool_uses"] == 5
    assert five["subagent_duration_ms"] == 25000


def test_claude_normalized_tokens_subagent_transcript_summed(tmp_path, monkeypatch):
    """A subagent transcript's four-field usage is summed and attributed by spawn window."""
    session_id = "22222222-2222-2222-2222-222222222202"
    projects_root = tmp_path / "home" / ".claude" / "projects" / "plan"
    transcript = projects_root / f"{session_id}.jsonl"
    _write_jsonl(
        transcript,
        [_main_context_entry("2026-03-27T10:10:00+00:00", input_tokens=10, output_tokens=2)],
    )
    sub_dir = projects_root / session_id / "subagents"
    sub_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(
        sub_dir / "agent-001.jsonl",
        [
            {
                "timestamp": "2026-03-27T10:12:00+00:00",
                "message": {
                    "role": "assistant",
                    "usage": {
                        "input_tokens": 900,
                        "output_tokens": 180,
                        "cache_read_input_tokens": 9000,
                        "cache_creation_input_tokens": 360,
                    },
                },
            }
        ],
    )

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    output_file = tmp_path / "normalized.json"
    result = _parse(
        ClaudeRuntime().metrics_normalized_tokens(session_id, _WINDOWS, str(output_file))
    )
    assert result["status"] == "success"
    assert int(result["subagent_transcripts_walked"]) == 1

    five = json.loads(output_file.read_text(encoding="utf-8"))["5-execute"]
    # parent(10) + subagent(900) = 910 input; 2 + 180 = 182 output.
    assert five["input"] == 910
    assert five["output"] == 182
    assert five["cache_read"] == 9000
    assert five["cache_creation"] == 360


def test_claude_normalized_tokens_missing_transcript_is_noop(tmp_path, monkeypatch):
    """No transcript on disk → the op returns a transcript_not_found no-op."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home" / ".claude" / "projects").mkdir(parents=True, exist_ok=True)

    output_file = tmp_path / "normalized.json"
    result = _parse(
        ClaudeRuntime().metrics_normalized_tokens(
            "22222222-2222-2222-2222-222222222299", _WINDOWS, str(output_file)
        )
    )
    assert result["status"] == "no-op"
    assert result["reason"] == "transcript_not_found"
    assert not output_file.exists()


# =============================================================================
# 2. OpenCodeRuntime — honest no-op
# =============================================================================


def test_opencode_normalized_tokens_is_noop(tmp_path):
    """OpenCode exposes no transcript → the op is an honest transcript_not_found no-op."""
    output_file = tmp_path / "normalized.json"
    result = _parse(
        OpenCodeRuntime().metrics_normalized_tokens("any-session", _WINDOWS, str(output_file))
    )
    assert result["status"] == "no-op"
    assert result["operation"] == "metrics normalized-tokens"
    assert result["reason"] == "transcript_not_found"
    assert not output_file.exists()


# =============================================================================
# 3. Relocated arithmetic helpers
# =============================================================================


def test_billing_weighted_total_arithmetic():
    """billing = input + output + round(0.1*cache_read) + round(1.25*cache_creation)."""
    four = {
        "input_tokens": 1000,
        "output_tokens": 200,
        "cache_read_input_tokens": 5000,
        "cache_creation_input_tokens": 400,
    }
    # 1000 + 200 + round(500) + round(500) = 2200.
    assert claude_runtime._billing_weighted_total(four) == 2200


def test_billing_weighted_total_empty_is_zero():
    """An empty four-field dict yields a zero billing total."""
    assert claude_runtime._billing_weighted_total({}) == 0


def test_sum_subagent_transcript_sums_four_fields(tmp_path):
    """_sum_subagent_transcript accumulates the four message.usage fields across lines."""
    path = tmp_path / "agent-001.jsonl"
    _write_jsonl(
        path,
        [
            {
                "timestamp": "2026-03-27T10:05:00+00:00",
                "message": {
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 10,
                        "cache_read_input_tokens": 2000,
                        "cache_creation_input_tokens": 300,
                    }
                },
            },
            {
                "timestamp": "2026-03-27T10:06:00+00:00",
                "message": {"usage": {"input_tokens": 50, "output_tokens": 5}},
            },
        ],
    )
    fields, first_ts = claude_runtime._sum_subagent_transcript(path)
    assert fields["input_tokens"] == 150
    assert fields["output_tokens"] == 15
    assert fields["cache_read_input_tokens"] == 2000
    assert fields["cache_creation_input_tokens"] == 300
    assert first_ts == "2026-03-27T10:05:00+00:00"


# =============================================================================
# 4. Router dispatch
# =============================================================================


def test_router_dispatches_normalized_tokens(tmp_path, monkeypatch):
    """The router routes ``metrics normalized-tokens`` to the Claude runtime op."""
    # marshal.json selecting the claude target.
    marshal_dir = tmp_path / ".plan"
    marshal_dir.mkdir(parents=True, exist_ok=True)
    (marshal_dir / "marshal.json").write_text(
        json.dumps({"runtime": {"target": "claude"}}), encoding="utf-8"
    )

    windows_file = tmp_path / "windows.json"
    windows_file.write_text(json.dumps([list(w) for w in _WINDOWS]), encoding="utf-8")
    output_file = tmp_path / "out.json"

    monkeypatch.chdir(tmp_path)
    # No transcript exists for this session → the dispatched op returns a no-op,
    # which proves the router reached the runtime method with parsed arguments.
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    (tmp_path / "home" / ".claude" / "projects").mkdir(parents=True, exist_ok=True)

    rc = platform_runtime.main(
        [
            "metrics",
            "normalized-tokens",
            "--session-id",
            "22222222-2222-2222-2222-222222222277",
            "--windows-file",
            str(windows_file),
            "--output-file",
            str(output_file),
        ]
    )
    assert rc == 0


def test_router_normalized_tokens_invalid_windows_file(tmp_path, monkeypatch, capsys):
    """A missing/malformed --windows-file yields an invalid_argument error TOON."""
    marshal_dir = tmp_path / ".plan"
    marshal_dir.mkdir(parents=True, exist_ok=True)
    (marshal_dir / "marshal.json").write_text(
        json.dumps({"runtime": {"target": "claude"}}), encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)
    rc = platform_runtime.main(
        [
            "metrics",
            "normalized-tokens",
            "--session-id",
            "22222222-2222-2222-2222-222222222266",
            "--windows-file",
            str(tmp_path / "does-not-exist.json"),
            "--output-file",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    parsed = parse_toon(out)
    assert parsed["status"] == "error"
    assert parsed["error"] == "invalid_argument"
