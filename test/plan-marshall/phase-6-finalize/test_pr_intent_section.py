#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for pr_intent_section.py — the PR body's distilled ``## Intent`` section.

The script owns every DETERMINISTIC decision about the section: whether it is
emitted at all, whether it fits the budget, and how a budget-exceeding draft is
truncated. The workflow agent only supplies the prose. These tests pin that
division, because handing any of it back to the agent would make the outcome
non-reproducible and reintroduce the silent-clip failure the script prevents.

Pinned properties:

* **Omit entirely, never a placeholder.** A plan with no ``solution_outline.md``
  yields a body with NO ``## Intent`` heading and no placeholder text, byte-
  identical to what it was. This is the fail-first case: pre-fix there was no
  script at all, and the LLM-authored body had no defined behaviour here.
* **Under budget => verbatim**, ``truncated: false``.
* **Over budget => truncated AND VISIBLY MARKED.** A truncation with no marker
  fails the suite — silent truncation is categorically forbidden.
* **The marker is counted INSIDE the budget**, so the written section never
  exceeds :data:`INTENT_BUDGET_CHARS`.
* **Exactly one outline reader.** The outline is read through
  ``manage-solution-outline read --section``, asserted on the CONSTRUCTED ARGV at
  the lowest subprocess primitive per the project's constructed-argv discipline —
  never by a second reader and never by a direct file read.
* **Truncation cuts at a word boundary**, not mid-token.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'phase-6-finalize', 'pr_intent_section.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pr_intent_section as pis  # noqa: E402

BUDGET = pis.INTENT_BUDGET_CHARS
MARKER_STEM = '_[Intent truncated'

_EXISTING_BODY = '## Summary\n\nReplace the thread_id-presence routing.\n'


class _Completed:
    """Minimal ``subprocess.run`` result stand-in."""

    def __init__(self, stdout: str = '', returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = ''


def _outline_toon(content: str) -> str:
    return f'status: success\nplan_id: p\nsection: summary\ncontent: "{content}"\n'


def _absent_toon() -> str:
    return 'status: error\nerror: not_found\n'


@pytest.fixture
def body_file(tmp_path: Path) -> Path:
    path = tmp_path / 'pr-body.md'
    path.write_text(_EXISTING_BODY, encoding='utf-8')
    return path


@pytest.fixture
def draft_file(tmp_path: Path) -> Path:
    return tmp_path / 'intent-draft.md'


def _args(plan_id: str, draft: Path, body: Path):
    import argparse

    return argparse.Namespace(plan_id=plan_id, draft_path=str(draft), body_path=str(body))


def _run(plan_id: str, draft: Path, body: Path, outline_stdout: str, capsys):
    """Drive ``cmd_render`` with the outline reader stubbed at the subprocess seam."""
    with patch.object(pis.subprocess, 'run', return_value=_Completed(outline_stdout)) as mock_run:
        code = pis.cmd_render(_args(plan_id, draft, body))
    return code, capsys.readouterr().out, mock_run


# =============================================================================
# Omit entirely — never an empty heading, never a placeholder
# =============================================================================


class TestOmitWhenNoOutlineIntent:
    """The fail-first case: no outline => no section AT ALL."""

    def test_absent_outline_writes_no_intent_heading_and_no_placeholder(
        self, body_file, draft_file, capsys
    ):
        """The body is byte-identical — no heading, no placeholder text.

        An empty ``## Intent`` would tell a reviewer less than no section at all,
        while implying the intent was considered and found vacuous. A placeholder
        (the terminal template's ``(no summary recorded)`` shape) would be worse
        still on this surface: it reads to a reviewer as a real, empty intent.
        """
        draft_file.write_text('A distillation that must not be rendered.', encoding='utf-8')
        before = body_file.read_text(encoding='utf-8')

        code, out, _ = _run('p', draft_file, body_file, _absent_toon(), capsys)

        assert code == 0
        after = body_file.read_text(encoding='utf-8')
        assert after == before, 'the body must be left BYTE-IDENTICAL'
        assert '## Intent' not in after
        assert 'no summary recorded' not in after
        assert 'omitted: true' in out
        assert 'chars_written: 0' in out

    def test_empty_outline_sections_also_omit(self, body_file, draft_file, capsys):
        """Present-but-empty sections are the same case as an absent outline."""
        draft_file.write_text('Should not be rendered.', encoding='utf-8')

        code, out, _ = _run('p', draft_file, body_file, _outline_toon('   '), capsys)

        assert code == 0
        assert '## Intent' not in body_file.read_text(encoding='utf-8')
        assert 'omitted: true' in out

    def test_the_omission_carries_an_explicit_reason(self, body_file, draft_file, capsys):
        """A silent omission would be indistinguishable from a renderer failure."""
        draft_file.write_text('x', encoding='utf-8')

        _code, out, _ = _run('p', draft_file, body_file, _absent_toon(), capsys)

        assert 'reason:' in out

    def test_an_outline_with_content_does_not_omit(self, body_file, draft_file, capsys):
        """Paired complement: the discriminator is the OUTLINE, not the draft."""
        draft_file.write_text('The problem, the approach, the non-goals.', encoding='utf-8')

        code, out, _ = _run('p', draft_file, body_file, _outline_toon('A real summary.'), capsys)

        assert code == 0
        assert 'omitted: false' in out
        assert '## Intent' in body_file.read_text(encoding='utf-8')


# =============================================================================
# Budget and VISIBLE truncation
# =============================================================================


class TestBudgetAndTruncation:
    """Under budget is verbatim; over budget is cut AND marked, inside the budget."""

    def test_under_budget_draft_is_emitted_verbatim(self, body_file, draft_file, capsys):
        draft = 'Problem: routing keyed on thread_id presence. Approach: key on kind. Non-goals: no batching change.'
        draft_file.write_text(draft, encoding='utf-8')

        code, out, _ = _run('p', draft_file, body_file, _outline_toon('summary'), capsys)

        written = body_file.read_text(encoding='utf-8')
        assert code == 0
        assert 'truncated: false' in out
        assert draft in written
        assert MARKER_STEM not in written

    def test_over_budget_draft_is_truncated_and_the_marker_is_written(
        self, body_file, draft_file, capsys
    ):
        """A truncation with no marker FAILS — silent clipping is forbidden.

        The marker must land in the WRITTEN BODY, not merely in the return
        envelope: a reviewer reads the body, and a clipped intent that looks
        complete is worse than an obviously-clipped one.
        """
        draft_file.write_text('intent ' * 600, encoding='utf-8')

        code, out, _ = _run('p', draft_file, body_file, _outline_toon('summary'), capsys)

        written = body_file.read_text(encoding='utf-8')
        assert code == 0
        assert 'truncated: true' in out
        assert MARKER_STEM in written, 'a truncation MUST be visibly marked in the body'

    def test_the_marker_quantifies_the_loss(self, body_file, draft_file, capsys):
        """"Truncated" alone does not tell a reviewer how much is missing."""
        total = 4200
        draft_file.write_text('x' * total, encoding='utf-8')

        _code, _out, _ = _run('p', draft_file, body_file, _outline_toon('summary'), capsys)

        written = body_file.read_text(encoding='utf-8')
        assert f'of {total} characters shown' in written

    @pytest.mark.parametrize('draft_len', [1, 500, 1400, 1490, 1500, 1501, 3000, 20000, 100000])
    def test_the_written_section_never_exceeds_the_budget(self, draft_len, body_file, draft_file, capsys):
        """The marker is counted INSIDE the budget, never added on top of it.

        Swept across the boundary rather than spot-checked, because the failure
        mode is a section that overruns by exactly the marker's length — invisible
        to a single under-budget sample.
        """
        draft_file.write_text(('intent ' * (draft_len // 7 + 2))[:draft_len], encoding='utf-8')
        before = body_file.read_text(encoding='utf-8')

        _code, _out, _ = _run('p', draft_file, body_file, _outline_toon('summary'), capsys)

        appended = body_file.read_text(encoding='utf-8')[len(before) :].strip()
        assert len(appended) <= BUDGET, f'{len(appended)} > budget {BUDGET}'

    def test_chars_written_matches_the_rendered_section(self, body_file, draft_file, capsys):
        """The reported count is the real one, so a caller can trust the envelope."""
        draft_file.write_text('intent ' * 600, encoding='utf-8')
        before = body_file.read_text(encoding='utf-8')

        _code, out, _ = _run('p', draft_file, body_file, _outline_toon('summary'), capsys)

        appended = body_file.read_text(encoding='utf-8')[len(before) :].strip()
        assert f'chars_written: {len(appended)}' in out
        assert f'budget: {BUDGET}' in out

    def test_truncation_cuts_at_a_word_boundary_not_mid_token(self):
        """A mid-token cut reads as a typo rather than as a truncation."""
        draft = 'alpha bravo charlie delta echo foxtrot golf hotel ' * 60
        section, truncated = pis.render_section(draft)

        assert truncated is True
        prose = section.split(MARKER_STEM)[0].rstrip()
        last_word = prose.split()[-1]
        assert last_word in draft.split(), f'{last_word!r} is a mid-token fragment'

    def test_an_unbreakable_token_still_respects_the_budget(self):
        """A hard cut is still preferable to overrunning a reserved budget."""
        section, truncated = pis.render_section('x' * 9000)

        assert truncated is True
        assert len(section) <= BUDGET
        assert MARKER_STEM in section

    def test_a_draft_exactly_at_the_boundary_is_not_falsely_marked(self):
        """Precision guard: a fitting draft must not claim to have been truncated."""
        prefix_len = len('## Intent\n\n')
        section, truncated = pis.render_section('a' * (BUDGET - prefix_len))

        assert truncated is False
        assert MARKER_STEM not in section
        assert len(section) == BUDGET


# =============================================================================
# Exactly one outline reader — constructed-argv assertion
# =============================================================================


class TestOutlineIsReadThroughTheCanonicalReaderOnly:
    """No second outline reader, and no direct read of solution_outline.md."""

    def test_the_constructed_argv_is_the_manage_solution_outline_read_verb(
        self, body_file, draft_file, capsys
    ):
        """Asserted on the argv at the LOWEST subprocess primitive.

        Per the project's constructed-argv discipline: asserting on a wrapper's
        arguments would pass even if the wrapper built the wrong command.
        """
        draft_file.write_text('distillation', encoding='utf-8')

        _code, _out, mock_run = _run('my-plan', draft_file, body_file, _outline_toon('s'), capsys)

        assert mock_run.call_count >= 1
        argv = mock_run.call_args_list[0].args[0]
        assert 'plan-marshall:manage-solution-outline:manage-solution-outline' in argv
        assert 'read' in argv
        assert '--plan-id' in argv
        assert argv[argv.index('--plan-id') + 1] == 'my-plan'
        assert '--section' in argv
        assert argv[argv.index('--section') + 1] in ('summary', 'overview')

    def test_every_outline_call_uses_the_same_reader_verb(self, body_file, draft_file, capsys):
        """Both sections go through ONE reader — never a second one for the fallback."""
        draft_file.write_text('distillation', encoding='utf-8')

        # An always-absent stub forces BOTH section reads to be attempted.
        _code, _out, mock_run = _run('p', draft_file, body_file, _absent_toon(), capsys)

        assert mock_run.call_count >= 2
        for call in mock_run.call_args_list:
            argv = call.args[0]
            assert 'plan-marshall:manage-solution-outline:manage-solution-outline' in argv
            assert argv[argv.index('--section') + 1] in ('summary', 'overview')

    def test_the_script_never_reads_solution_outline_md_directly(self):
        """A direct file read would be the second source of truth this avoids.

        Scans for the filename co-occurring with a file-access construct on the
        same line, so the name may still appear freely in prose and in the
        omission reason without tripping the guard.
        """
        access_constructs = ('read_text', 'open(', 'Path(', 'joinpath', 'glob(')
        offenders = [
            (number, line.strip())
            for number, line in enumerate(SCRIPT_PATH.read_text(encoding='utf-8').splitlines(), 1)
            if 'solution_outline' in line and any(c in line for c in access_constructs)
        ]

        assert offenders == [], f'direct outline file access: {offenders}'


# =============================================================================
# Fail-loud draft handling
# =============================================================================


class TestFailLoudOnABadDraft:
    """The renderer refuses rather than emitting a hollow section."""

    def test_missing_draft_file_is_an_error(self, body_file, tmp_path, capsys):
        missing = tmp_path / 'nope.md'
        before = body_file.read_text(encoding='utf-8')

        code, out, _ = _run('p', missing, body_file, _outline_toon('s'), capsys)

        assert code == 1
        assert 'error: draft_unreadable' in out
        assert body_file.read_text(encoding='utf-8') == before

    def test_empty_draft_with_a_real_outline_is_an_error(self, body_file, draft_file, capsys):
        """An outline states an intent but nothing was distilled — fail loud.

        Emitting an empty heading here would be the exact placeholder shape the
        omit-entirely rule exists to prevent, arrived at by a different route.
        """
        draft_file.write_text('   \n\n', encoding='utf-8')
        before = body_file.read_text(encoding='utf-8')

        code, out, _ = _run('p', draft_file, body_file, _outline_toon('s'), capsys)

        assert code == 1
        assert 'error: empty_draft' in out
        assert body_file.read_text(encoding='utf-8') == before


# =============================================================================
# CLI surface
# =============================================================================


class TestCLISurface:
    """The argparse contract the workflow doc's canonical invocation depends on."""

    def test_render_requires_all_three_flags(self):
        parser = pis.build_parser()

        for argv in (
            ['render', '--draft-path', 'd', '--body-path', 'b'],
            ['render', '--plan-id', 'p', '--body-path', 'b'],
            ['render', '--plan-id', 'p', '--draft-path', 'd'],
        ):
            with pytest.raises(SystemExit):
                parser.parse_args(argv)

    def test_render_is_the_only_subcommand(self):
        parser = pis.build_parser()

        parsed = parser.parse_args(
            ['render', '--plan-id', 'p', '--draft-path', 'd', '--body-path', 'b']
        )
        assert parsed.command == 'render'

        with pytest.raises(SystemExit):
            parser.parse_args(['emit', '--plan-id', 'p'])
