#!/usr/bin/env python3
"""Tests for ascii_diagrams.py - ASCII box-diagram alignment validator.

Direct-import tests of the alignment predicates, box-run detection, and
rebuild logic, plus subprocess CLI plumbing tests for the ``check`` and
``fix`` subcommands. The two load-bearing behaviours the validator exists
to provide are exercised end-to-end: it DETECTS misalignment in a fixture
and REPAIRS it idempotently (a second ``fix`` pass changes nothing).
"""

from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

# Test directories / script under test
TEST_DIR = Path(__file__).parent
SCRIPT_PATH = get_script_path('pm-documents', 'ref-ascii-diagrams', 'ascii_diagrams.py')

# Direct-import of the validator module so the pure functions can be unit
# tested without subprocess overhead.
_mod = load_script_module('pm-documents', 'ref-ascii-diagrams', 'ascii_diagrams.py', 'ascii_diagrams')

is_top_rule = _mod.is_top_rule
is_bottom_rule = _mod.is_bottom_rule
is_box_line = _mod.is_box_line
rebuild_box = _mod.rebuild_box
_process_file = _mod._process_file
_box_run_lines = _mod._box_run_lines


# =============================================================================
# Fixture content
# =============================================================================

# A misaligned box: the interior lines and the bottom rule do not reach the
# column the longest interior line implies, so the right borders are ragged.
MISALIGNED_BOX = "\n".join(
    [
        "Intro paragraph.",
        "",
        "```",
        "┌────┐",
        "│ short │",
        "│ a longer line │",
        "└────┘",
        "```",
        "",
        "Outro paragraph.",
    ]
)

# An already-aligned box: every right border sits in the same column.
ALIGNED_BOX = "\n".join(
    [
        "```",
        "┌───────────────┐",
        "│ short         │",
        "│ a longer line │",
        "└───────────────┘",
        "```",
    ]
)

# Box-like content OUTSIDE any code fence must be ignored — only boxes inside
# code/literal blocks are normalized.
BOX_OUTSIDE_FENCE = "\n".join(
    [
        "┌────┐",
        "│ x │",
        "└────┘",
    ]
)


# =============================================================================
# Predicate unit tests (direct import)
# =============================================================================


def test_is_top_rule_detects_top_border():
    # Arrange / Act / Assert
    assert is_top_rule("┌────┐")
    assert is_top_rule("    ┌──┐")  # leading indent ignored


def test_is_top_rule_rejects_non_top_lines():
    assert not is_top_rule("│ content │")
    assert not is_top_rule("└────┘")
    assert not is_top_rule("plain text")
    assert not is_top_rule("")


def test_is_top_rule_rejects_text_between_corners():
    # A line with non-horizontal characters between the corners is NOT a top rule.
    assert not is_top_rule("┌ some text ┐")
    assert not is_top_rule("┌─ text ─┐")


def test_is_bottom_rule_detects_bottom_border():
    assert is_bottom_rule("└────┘")
    assert is_bottom_rule("  └──┘")


def test_is_bottom_rule_rejects_non_bottom_lines():
    assert not is_bottom_rule("┌────┐")
    assert not is_bottom_rule("│ content │")


def test_is_bottom_rule_rejects_text_between_corners():
    # A line with non-horizontal characters between the corners is NOT a bottom rule.
    assert not is_bottom_rule("└ some text ┘")
    assert not is_bottom_rule("└─ text ─┘")


def test_is_box_line_requires_both_vertical_borders():
    assert is_box_line("│ content │")
    assert not is_box_line("│ only-left")
    assert not is_box_line("only-right │")
    # A lone connector pipe is not a box interior line.
    assert not is_box_line("│")


# =============================================================================
# Box-run detection
# =============================================================================


def test_box_run_lines_matches_bottom_rule():
    # Arrange
    lines = ["┌──┐", "│x│", "│yy│", "└──┘"]

    # Act
    bottom = _box_run_lines(lines, 0)

    # Assert
    assert bottom == 3


def test_box_run_lines_returns_none_on_blank_break():
    # Arrange — a blank line breaks the run before a bottom rule appears.
    lines = ["┌──┐", "│x│", "", "└──┘"]

    # Act
    bottom = _box_run_lines(lines, 0)

    # Assert
    assert bottom is None


def test_box_run_lines_treats_deeper_indent_as_interior():
    # Arrange — a deeper-indented line is interior content, not a terminator.
    lines = ["┌──┐", "│x│", "  nested content", "│y│", "└──┘"]

    # Act
    bottom = _box_run_lines(lines, 0)

    # Assert — deeper indent is interior; box run still finds the bottom rule.
    assert bottom == 4


def test_box_run_lines_terminates_on_shallower_indent():
    # Arrange — a line at shallower indent than the box exits the box context.
    lines = ["  ┌──┐", "  │x│", "unindented line", "  └──┘"]

    # Act
    bottom = _box_run_lines(lines, 0)

    # Assert — shallower indent terminates the run; no bottom rule found.
    assert bottom is None


# =============================================================================
# rebuild_box alignment logic (direct import)
# =============================================================================


def test_rebuild_box_aligns_right_borders_to_widest_line():
    # Arrange
    lines = ["┌──┐", "│ short │", "│ a longer line │", "└──┘"]

    # Act
    rebuilt = rebuild_box(lines, 0, 3)

    # Assert — every line now has the same total length.
    widths = {len(line) for line in rebuilt}
    assert len(widths) == 1, f"expected uniform width, got {widths}"
    assert rebuilt[0].startswith("┌") and rebuilt[0].endswith("┐")
    assert rebuilt[-1].startswith("└") and rebuilt[-1].endswith("┘")


def test_rebuild_box_is_a_fixed_point_for_aligned_input():
    # Arrange — an already-aligned box.
    lines = [
        "┌───────────────┐",
        "│ short         │",
        "│ a longer line │",
        "└───────────────┘",
    ]

    # Act
    rebuilt = rebuild_box(lines, 0, 3)

    # Assert — rebuilding an aligned box leaves it unchanged.
    assert rebuilt == lines


# =============================================================================
# _process_file detection (direct import, tmp_path isolated)
# =============================================================================


def test_process_file_detects_misalignment(tmp_path):
    # Arrange
    md = tmp_path / "diagram.md"
    md.write_text(MISALIGNED_BOX, encoding="utf-8")

    # Act
    _new_lines, changed = _process_file(md)

    # Assert — at least one interior/border line is reported as changed.
    assert changed, "expected misaligned lines to be detected"


def test_process_file_reports_no_change_for_aligned_box(tmp_path):
    # Arrange
    md = tmp_path / "aligned.md"
    md.write_text(ALIGNED_BOX, encoding="utf-8")

    # Act
    _new_lines, changed = _process_file(md)

    # Assert
    assert changed == []


def test_process_file_ignores_boxes_outside_code_blocks(tmp_path):
    # Arrange — a ragged box that is NOT inside a fence must be left alone.
    md = tmp_path / "outside.md"
    md.write_text(BOX_OUTSIDE_FENCE, encoding="utf-8")

    # Act
    _new_lines, changed = _process_file(md)

    # Assert
    assert changed == []


# =============================================================================
# CLI plumbing (subprocess)
# =============================================================================


def test_script_exists():
    assert SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}"


def test_check_subcommand_reports_misalignment(tmp_path):
    # Arrange
    md = tmp_path / "diagram.md"
    md.write_text(MISALIGNED_BOX, encoding="utf-8")

    # Act
    result = run_script(SCRIPT_PATH, "check", "--path", str(md))

    # Assert
    assert result.success, f"check failed: {result.stderr}"
    data = result.toon()
    assert data["operation"] == "check"
    assert data["misaligned_count"] >= 1


def test_check_subcommand_clean_on_aligned(tmp_path):
    # Arrange
    md = tmp_path / "aligned.md"
    md.write_text(ALIGNED_BOX, encoding="utf-8")

    # Act
    result = run_script(SCRIPT_PATH, "check", "--path", str(md))

    # Assert
    assert result.success, f"check failed: {result.stderr}"
    data = result.toon()
    assert data["misaligned_count"] == 0


def test_fix_subcommand_repairs_and_is_idempotent(tmp_path):
    # Arrange
    md = tmp_path / "diagram.md"
    md.write_text(MISALIGNED_BOX, encoding="utf-8")

    # Act — first fix pass repairs the file.
    first = run_script(SCRIPT_PATH, "fix", "--path", str(md))

    # Assert — the file was reported as fixed.
    assert first.success, f"first fix failed: {first.stderr}"
    first_data = first.toon()
    assert first_data["files_fixed"] == 1
    assert first_data["lines_changed"] >= 1

    repaired = md.read_text(encoding="utf-8")

    # Act — a re-check now reports zero misalignment.
    recheck = run_script(SCRIPT_PATH, "check", "--path", str(md))
    assert recheck.success
    assert recheck.toon()["misaligned_count"] == 0

    # Act — a second fix pass is idempotent: nothing changes on disk and the
    # script reports zero files fixed.
    second = run_script(SCRIPT_PATH, "fix", "--path", str(md))

    # Assert — idempotence: byte-identical content and no further fixes.
    assert second.success, f"second fix failed: {second.stderr}"
    second_data = second.toon()
    assert second_data["files_fixed"] == 0
    assert md.read_text(encoding="utf-8") == repaired


def test_main_requires_subcommand():
    # Act — invoking with no subcommand is an argparse error.
    result = run_script(SCRIPT_PATH)

    # Assert
    assert not result.success
    combined = (result.stdout + result.stderr).lower()
    assert "usage" in combined or "error" in combined
