#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
  ``_sum_subagent_transcript``) behave as before;
- the exploration-share counters bucket each ``tool_use`` by tool name, sum the
  matching ``tool_result`` payload bytes, count an unknown name into
  ``unclassified`` rather than dropping it, and match names casefolded;
- the emitted per-phase bucket key set equals the key list the ``Runtime`` ABC's
  contract docstring declares (the key set is PARSED from that docstring, so a
  producer/contract drift fails here for both implementations); and
- the router dispatches the new ``metrics normalized-tokens`` operation.
"""

import json  # noqa: I001
import re
from pathlib import Path

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
import claude_runtime
import platform_runtime
from claude_runtime import ClaudeRuntime
from opencode_runtime import OpenCodeRuntime
from runtime_base import Runtime
from toon_parser import parse_toon


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


def _tool_use_entry(timestamp: str, calls: list[tuple[str, str]]) -> dict:
    """Build an assistant entry carrying one ``tool_use`` item per ``(id, name)``."""
    return {
        "timestamp": timestamp,
        "message": {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": tool_id, "name": name, "input": {}}
                for tool_id, name in calls
            ],
        },
    }


def _tool_result_entry(timestamp: str, tool_use_id: str, text: str) -> dict:
    """Build a user entry carrying the ``tool_result`` for *tool_use_id*."""
    return {
        "timestamp": timestamp,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": [{"type": "text", "text": text}],
                }
            ],
        },
    }


def _contract_bucket_keys() -> set[str]:
    """Parse the per-phase bucket key set out of the ABC's contract docstring.

    The key list is DERIVED from ``Runtime.metrics_normalized_tokens.__doc__``
    rather than restated here, so a producer that drifts from the published
    contract fails this assertion for BOTH implementations instead of the drift
    being invisible until a consumer reads a missing key.
    """
    doc = Runtime.metrics_normalized_tokens.__doc__ or ""
    match = re.search(r"\{phase_name:\s*\{(.*?)\}\}", doc, re.DOTALL)
    assert match is not None, "contract docstring no longer declares a per-phase bucket shape"
    return {key.strip() for key in match.group(1).split(",") if key.strip()}


# The four raw ``message.usage`` key spellings the Claude producer emits ALONGSIDE
# the contract's normalized short names. They are aliases of
# ``input``/``output``/``cache_read``/``cache_creation``, not additional contract
# surface, so they are carved out of the exact-match assertion below.
_RAW_USAGE_ALIASES = {
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
}

# The exploration-share counter keys, derived from the same contract docstring.
_EXPECTED_COUNTER_KEYS = {
    key
    for key in _contract_bucket_keys()
    if key.endswith("_tool_calls") or key.endswith("_result_bytes")
}


def _expected_attribution_keys() -> set[str]:
    """The cache-read attribution key set, DERIVED from the producer's bucket names.

    Derived rather than restated so a bucket added to ``_TOOL_BUCKETS`` cannot
    leave the attribution group behind without a test failing.
    """
    return {
        f"cache_read_attributed_{bucket}" for bucket in claude_runtime._TOOL_BUCKET_NAMES
    } | {"cache_read_unattributed"}


def _attribution_group(phase_bucket: dict) -> dict[str, int]:
    """Extract just the cache-read attribution group from an emitted phase bucket."""
    return {key: phase_bucket[key] for key in _expected_attribution_keys() if key in phase_bucket}


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
            _tool_use_entry(
                "2026-03-27T10:12:00+00:00",
                [("toolu_r1", "Read"), ("toolu_b1", "Bash"), ("toolu_w1", "Write")],
            ),
            _tool_result_entry("2026-03-27T10:12:10+00:00", "toolu_r1", "r" * 120),
            _tool_result_entry("2026-03-27T10:12:20+00:00", "toolu_b1", "b" * 30),
            _tool_result_entry("2026-03-27T10:12:30+00:00", "toolu_w1", "w" * 7),
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
    # total is the canonical four-field sum: 100 + 20 + 1000 + 40 = 1160.
    assert five["total"] == 1160
    # The <usage> tag attribution lands in the same phase window.
    assert five["subagent_total_tokens"] == 4000
    assert five["subagent_tool_uses"] == 5
    assert five["subagent_duration_ms"] == 25000

    # Contract-level key-set assertion: what the producer emits must equal what
    # the ABC's contract docstring declares, modulo the raw-usage aliases. This
    # fails on EITHER side of a drift — a producer that drops a contract key, or
    # a contract that gains one no producer writes.
    assert set(five) == _contract_bucket_keys() | _RAW_USAGE_ALIASES

    # Exploration-share counters: Read -> exploration, Bash -> execute,
    # Write -> work, each with its result payload's byte length.
    assert five["exploration_tool_calls"] == 1
    assert five["execute_tool_calls"] == 1
    assert five["work_tool_calls"] == 1
    assert five["exploration_result_bytes"] == 120
    assert five["execute_result_bytes"] == 30
    assert five["work_result_bytes"] == 7
    # Nothing landed in the excluded buckets, and the classifier met no unknown
    # name — a MEASURED zero, present as 0 rather than absent.
    assert five["orchestration_tool_calls"] == 0
    assert five["unclassified_tool_calls"] == 0
    assert int(result["unclassified_tool_calls"]) == 0


def test_claude_normalized_tokens_unknown_tool_name_is_counted_not_dropped(tmp_path, monkeypatch):
    """A tool name outside the classifier's domain lands in unclassified, never dropped."""
    session_id = "22222222-2222-2222-2222-222222222204"
    projects_root = tmp_path / "home" / ".claude" / "projects" / "plan"
    _write_jsonl(
        projects_root / f"{session_id}.jsonl",
        [
            _main_context_entry("2026-03-27T10:10:00+00:00", input_tokens=1, output_tokens=1),
            _tool_use_entry("2026-03-27T10:11:00+00:00", [("toolu_x", "NoSuchToolInvented")]),
            _tool_result_entry("2026-03-27T10:11:10+00:00", "toolu_x", "z" * 11),
        ],
    )

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    output_file = tmp_path / "normalized.json"
    result = _parse(
        ClaudeRuntime().metrics_normalized_tokens(session_id, _WINDOWS, str(output_file))
    )
    assert result["status"] == "success"

    five = json.loads(output_file.read_text(encoding="utf-8"))["5-execute"]
    assert five["unclassified_tool_calls"] == 1
    assert five["unclassified_result_bytes"] == 11
    # The unknown name inflated no other bucket.
    assert five["exploration_tool_calls"] == 0
    assert five["work_tool_calls"] == 0
    assert five["execute_tool_calls"] == 0
    assert five["orchestration_tool_calls"] == 0
    # ...and it is surfaced at run level so the classifier's gap is visible.
    assert int(result["unclassified_tool_calls"]) == 1


def test_claude_normalized_tokens_tool_name_matched_casefolded(tmp_path, monkeypatch):
    """A casing variant of a known tool name resolves to the same bucket."""
    session_id = "22222222-2222-2222-2222-222222222205"
    projects_root = tmp_path / "home" / ".claude" / "projects" / "plan"
    _write_jsonl(
        projects_root / f"{session_id}.jsonl",
        [
            _main_context_entry("2026-03-27T10:10:00+00:00", input_tokens=1, output_tokens=1),
            # ``bash`` really occurs lowercase in the corpus alongside ``Bash``.
            _tool_use_entry("2026-03-27T10:11:00+00:00", [("toolu_l", "bash")]),
        ],
    )

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    output_file = tmp_path / "normalized.json"
    result = _parse(
        ClaudeRuntime().metrics_normalized_tokens(session_id, _WINDOWS, str(output_file))
    )
    assert result["status"] == "success"

    five = json.loads(output_file.read_text(encoding="utf-8"))["5-execute"]
    assert five["execute_tool_calls"] == 1
    assert five["unclassified_tool_calls"] == 0


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


def test_claude_normalized_tokens_subagent_keys_zero_without_subagent_usage(tmp_path, monkeypatch):
    """A phase with no subagent usage still carries the four subagent_* keys at 0."""
    session_id = "22222222-2222-2222-2222-222222222203"
    projects_root = tmp_path / "home" / ".claude" / "projects" / "plan"
    transcript = projects_root / f"{session_id}.jsonl"
    _write_jsonl(
        transcript,
        [_main_context_entry("2026-03-27T10:10:00+00:00", input_tokens=100, output_tokens=20)],
    )

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    output_file = tmp_path / "normalized.json"
    result = _parse(
        ClaudeRuntime().metrics_normalized_tokens(session_id, _WINDOWS, str(output_file))
    )
    assert result["status"] == "success"

    five = json.loads(output_file.read_text(encoding="utf-8"))["5-execute"]
    # No <usage> tag and no subagent transcript → keys present, all zero.
    assert five["subagent_total_tokens"] == 0
    assert five["subagent_tool_uses"] == 0
    assert five["subagent_duration_ms"] == 0
    assert five["subagent_samples"] == 0


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
    fields, first_ts, tool_counters = claude_runtime._sum_subagent_transcript(path)
    assert fields["input_tokens"] == 150
    assert fields["output_tokens"] == 15
    assert fields["cache_read_input_tokens"] == 2000
    assert fields["cache_creation_input_tokens"] == 300
    assert first_ts == "2026-03-27T10:05:00+00:00"
    # No tool_use items in this transcript → every counter is a measured zero,
    # and the key set is complete rather than partially populated.
    assert set(tool_counters) == set(_EXPECTED_COUNTER_KEYS)
    assert set(tool_counters.values()) == {0}


def test_sum_subagent_transcript_counts_tool_calls_and_result_bytes(tmp_path):
    """A subagent transcript's tool calls are bucketed and their result bytes summed."""
    path = tmp_path / "agent-002.jsonl"
    _write_jsonl(
        path,
        [
            _tool_use_entry("2026-03-27T10:05:00+00:00", [("toolu_a", "Read"), ("toolu_b", "Edit")]),
            _tool_result_entry("2026-03-27T10:05:30+00:00", "toolu_a", "x" * 40),
            _tool_result_entry("2026-03-27T10:05:40+00:00", "toolu_b", "y" * 9),
        ],
    )
    _fields, _first_ts, tool_counters = claude_runtime._sum_subagent_transcript(path)
    assert tool_counters["exploration_tool_calls"] == 1
    assert tool_counters["work_tool_calls"] == 1
    assert tool_counters["exploration_result_bytes"] == 40
    assert tool_counters["work_result_bytes"] == 9


# =============================================================================
# 3b. Cache-read attribution — turn-weighted residency, exact reconciliation
# =============================================================================


def test_attribute_cache_read_emits_the_full_key_set_derived_from_bucket_names():
    """The emitted group is one key per bucket plus the residual, derived not restated."""
    attributed = claude_runtime._attribute_cache_read(500, {"exploration": 10})

    assert set(attributed) == _expected_attribution_keys()
    # The derivation is not vacuous: the producer really does declare more than
    # one bucket, so a group that collapsed to just the residual would fail.
    assert len(claude_runtime._TOOL_BUCKET_NAMES) > 1


def test_attribute_cache_read_reconciles_exactly_to_the_recorded_total():
    """Named parts plus residual equal the recorded cache_read, for every weight shape."""
    cases = [
        (0, {}),
        (0, {"exploration": 7}),
        (1000, {}),
        (1000, {"exploration": 3}),
        (1000, {"exploration": 1, "work": 2}),
        (997, {"exploration": 13, "work": 7, "execute": 11, "orchestration": 3}),
        (1, {"exploration": 1, "work": 1, "execute": 1}),
    ]
    for total, weights in cases:
        attributed = claude_runtime._attribute_cache_read(total, weights)
        assert sum(attributed.values()) == total, (total, weights, attributed)
        # A named part is never negative and never exceeds the whole.
        for key, value in attributed.items():
            assert 0 <= value <= total, (key, value, total, weights)


def test_attribute_cache_read_floors_named_parts_and_banks_the_remainder_in_the_residual():
    """Rounding crumbs land in the residual — never inflating a named share."""
    # weights 1:2 over a total of 10 → 10*1//3 = 3 and 10*2//3 = 6, remainder 1.
    attributed = claude_runtime._attribute_cache_read(10, {"exploration": 1, "work": 2})

    assert attributed["cache_read_attributed_exploration"] == 3
    assert attributed["cache_read_attributed_work"] == 6
    assert attributed["cache_read_unattributed"] == 1
    # Matched control on the direction of the rounding: the naive proportional
    # split would have handed exploration 3.33 and work 6.67, so a rounded-up
    # named share is what this assertion rules out.
    assert attributed["cache_read_attributed_exploration"] < 10 * 1 / 3


def test_attribute_cache_read_without_observed_weight_leaves_everything_in_the_residual():
    """A phase billed for a context read the walk cannot explain discloses it, not spreads it."""
    attributed = claude_runtime._attribute_cache_read(4321, {})

    assert attributed["cache_read_unattributed"] == 4321
    named = {k: v for k, v in attributed.items() if k != "cache_read_unattributed"}
    assert set(named.values()) == {0}, named


def test_attribute_cache_read_zero_total_is_a_measured_zero_across_the_group():
    """Zero recorded cache_read still yields every key — a measured zero, never absent."""
    attributed = claude_runtime._attribute_cache_read(0, {"exploration": 999, "work": 1})

    assert set(attributed) == _expected_attribution_keys()
    assert set(attributed.values()) == {0}


def test_claude_normalized_tokens_attributes_cache_read_by_turn_weighted_residency(
    tmp_path, monkeypatch
):
    """cache_read splits by how long each source's bytes stayed resident, not by byte share.

    The two payloads are the SAME size, so a split that merely restated
    ``{bucket}_result_bytes`` would come out 1:1. The exploration payload enters a
    turn earlier and is therefore re-read once more, so the honest split is 2:1 —
    which is what separates an attribution from a byte-share rename.
    """
    session_id = "22222222-2222-2222-2222-222222222210"
    projects_root = tmp_path / "home" / ".claude" / "projects" / "plan"
    _write_jsonl(
        projects_root / f"{session_id}.jsonl",
        [
            # Turn 1 — the whole phase's cache_read is billed here; nothing is
            # resident yet, so this turn contributes no weight to any bucket.
            _main_context_entry(
                "2026-03-27T10:01:00+00:00",
                input_tokens=1,
                output_tokens=1,
                cache_read_input_tokens=1200,
            ),
            _tool_use_entry("2026-03-27T10:02:00+00:00", [("toolu_r", "Read")]),
            _tool_result_entry("2026-03-27T10:03:00+00:00", "toolu_r", "r" * 400),
            # Turn 2 — the Read payload is resident.
            _main_context_entry("2026-03-27T10:04:00+00:00", input_tokens=1, output_tokens=1),
            _tool_use_entry("2026-03-27T10:05:00+00:00", [("toolu_w", "Write")]),
            _tool_result_entry("2026-03-27T10:06:00+00:00", "toolu_w", "w" * 400),
            # Turn 3 — both payloads are resident.
            _main_context_entry("2026-03-27T10:07:00+00:00", input_tokens=1, output_tokens=1),
        ],
    )

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    output_file = tmp_path / "normalized.json"
    result = _parse(
        ClaudeRuntime().metrics_normalized_tokens(session_id, _WINDOWS, str(output_file))
    )
    assert result["status"] == "success"

    five = json.loads(output_file.read_text(encoding="utf-8"))["5-execute"]

    # The byte shares really are equal — this is the control that makes the
    # unequal attribution below meaningful rather than incidental.
    assert five["exploration_result_bytes"] == five["work_result_bytes"] == 400

    # Residency weights are 400x2 vs 400x1, so 1200 splits 800 / 400.
    assert five["cache_read"] == 1200
    assert five["cache_read_attributed_exploration"] == 800
    assert five["cache_read_attributed_work"] == 400
    assert five["cache_read_attributed_execute"] == 0
    assert five["cache_read_attributed_orchestration"] == 0
    assert five["cache_read_attributed_unclassified"] == 0
    # Every unit of the recorded figure is accounted for, so the residual is a
    # measured zero — and it is still EMITTED, which is what lets a reader tell
    # "fully explained" apart from "never computed".
    assert five["cache_read_unattributed"] == 0
    assert "cache_read_unattributed" in five
    assert sum(_attribution_group(five).values()) == five["cache_read"]


def test_claude_normalized_tokens_zero_cache_read_phase_carries_the_full_attribution_group(
    tmp_path, monkeypatch
):
    """Matched negative control for the full-key-set rule: no cache_read, keys still present."""
    session_id = "22222222-2222-2222-2222-222222222211"
    projects_root = tmp_path / "home" / ".claude" / "projects" / "plan"
    _write_jsonl(
        projects_root / f"{session_id}.jsonl",
        [
            # No cache_read on the usage record at all, yet real payload traffic —
            # so the group cannot be emitted merely because weight exists.
            _main_context_entry("2026-03-27T10:01:00+00:00", input_tokens=5, output_tokens=2),
            _tool_use_entry("2026-03-27T10:02:00+00:00", [("toolu_r", "Read")]),
            _tool_result_entry("2026-03-27T10:03:00+00:00", "toolu_r", "r" * 250),
            _main_context_entry("2026-03-27T10:04:00+00:00", input_tokens=5, output_tokens=2),
        ],
    )

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    output_file = tmp_path / "normalized.json"
    result = _parse(
        ClaudeRuntime().metrics_normalized_tokens(session_id, _WINDOWS, str(output_file))
    )
    assert result["status"] == "success"

    five = json.loads(output_file.read_text(encoding="utf-8"))["5-execute"]
    assert five["cache_read"] == 0
    # Bytes were observed, so the zero below is about the RECORDED figure being
    # zero — not about there being nothing to attribute.
    assert five["exploration_result_bytes"] == 250
    assert _expected_attribution_keys() <= set(five)
    assert set(_attribution_group(five).values()) == {0}


def test_claude_normalized_tokens_unexplained_cache_read_lands_in_the_residual(
    tmp_path, monkeypatch
):
    """A phase billed for context it never sourced from a payload discloses the whole figure."""
    session_id = "22222222-2222-2222-2222-222222222212"
    projects_root = tmp_path / "home" / ".claude" / "projects" / "plan"
    _write_jsonl(
        projects_root / f"{session_id}.jsonl",
        [
            _main_context_entry(
                "2026-03-27T10:01:00+00:00",
                input_tokens=3,
                output_tokens=1,
                cache_read_input_tokens=7777,
            ),
        ],
    )

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))

    output_file = tmp_path / "normalized.json"
    result = _parse(
        ClaudeRuntime().metrics_normalized_tokens(session_id, _WINDOWS, str(output_file))
    )
    assert result["status"] == "success"

    five = json.loads(output_file.read_text(encoding="utf-8"))["5-execute"]
    assert five["cache_read_unattributed"] == 7777
    named = {
        key: value
        for key, value in _attribution_group(five).items()
        if key != "cache_read_unattributed"
    }
    assert set(named.values()) == {0}, named
    assert sum(_attribution_group(five).values()) == five["cache_read"]


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
