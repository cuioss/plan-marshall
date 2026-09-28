#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every documented ``manage-status transition --completed`` call site halts on a refusal.

A refused transition leaves the phase where it was, so a call site that goes on
to its next step — the completion log, the handshake capture, an auto-continue
gate, the next phase — runs that step against a phase that never advanced. The
single statement of what a call site does instead is the refused-transition halt
rule in ``ref-workflow-architecture/standards/phase-lifecycle.md``; every other
call site links it rather than restating it.

The population is DERIVED, never listed
---------------------------------------
Call sites are found by scanning every ``marketplace/bundles/**/*.md`` for fenced
``bash`` / ``sh`` / ``shell`` blocks that invoke ``manage-status transition`` with
``--completed <anything>`` — a literal phase key or a ``{placeholder}`` alike,
with backslash continuations collapsed first. A prose mention outside a fence is
excluded by that predicate, not by an allow-list, and a call block added anywhere
in the marketplace joins the population without editing this module.

What each call site must carry
------------------------------
For every call block, the section text after it — up to the next heading at the
same or a higher level — must link the halt-rule anchor (the anchor's own home
states the rule under the anchor heading instead), and that marker must come
before any auto-continue gate mention, because a gate read ahead of the halt is a
continuation past a refusal. The gate names are DERIVED from the halt rule's own
section — every backticked ``*_without_asking`` token between the anchor heading
and the next heading at the same or a higher level — so a gate the rule gains is
checked without editing this module. Every refusal code a recovery table under a call
site names must be a member of ``VERIFY_REFUSAL_ERRORS``, imported from the
production module, so a table can neither invent a code nor imply that an
unlisted refusal has a recovery.

Why the scan is cross-checked and controlled
--------------------------------------------
A fence parser that silently parses nothing would pass every per-site check over
an empty population. The module therefore asserts a non-empty population holding
at least one templated block, cross-checks the parser against an independent raw
regex (every file the regex hits must have yielded a parsed call block), and runs
negative controls: a synthetic literal-phase block followed straight by a
``finalize_without_asking`` check, and a synthetic templated block followed by an
unconditional auto-transition, must both be flagged. A synthetic block carrying
the correct link is the positive control that keeps the predicate satisfiable.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_halt_call_sites_cmd_lifecycle')

VERIFY_REFUSAL_ERRORS: frozenset[str] = _lifecycle.VERIFY_REFUSAL_ERRORS

#: The anchor every call site links. Its value IS the contract: a renamed heading
#: breaks every link, and this spelling is what the links are checked against.
HALT_RULE_ANCHOR = 'refused-transition-halt-rule'

_SHELL_LANGS = frozenset({'bash', 'sh', 'shell'})
_FENCE_RE = re.compile(r'^[ \t]*(?P<fence>`{3,}|~{3,})(?P<lang>[\w+-]*)[ \t]*$')
_HEADING_RE = re.compile(r'^(?P<hashes>#{1,6})[ \t]+(?P<title>.*?)[ \t]*#*[ \t]*$')
_CONTINUATION_RE = re.compile(r'\\\n[ \t]*')
_CALL_RE = re.compile(r'manage-status[ \t]+transition\b[^\n]*?--completed(?:[ \t]+|=)\S+')
_TEMPLATED_RE = re.compile(r'--completed(?:[ \t]+|=)\{')
_LINK_RE = re.compile(rf'\]\((?P<target>[^)\s#]*phase-lifecycle\.md)#{HALT_RULE_ANCHOR}\)')
_BACKTICK_RE = re.compile(r'`([^`]+)`')
_GATE_TOKEN_RE = re.compile(r'`(\w+_without_asking)`')
_RAW_CALL_RE = re.compile(
    r'```(?:bash|sh|shell)[^\n]*\n(?:(?!```).)*?manage-status\s+transition(?:(?!```).)*?--completed', re.S
)


def _slug(title: str) -> str:
    """The GitHub-style heading anchor for ``title``."""
    kept = re.sub(r'[^\w\s-]', '', title.strip().lower())
    return re.sub(r'\s', '-', kept)


@dataclass(frozen=True)
class CallBlock:
    """One fenced call site and the section text that follows it."""

    path: Path
    line: int
    templated: bool
    following: str

    @property
    def label(self) -> str:
        """``path:line``, marketplace-relative when the file lives in the marketplace."""
        shown = (
            self.path.relative_to(MARKETPLACE_ROOT) if self.path.is_relative_to(MARKETPLACE_ROOT) else self.path.name
        )
        return f'{shown}:{self.line}'


def _parse(path: Path, text: str) -> tuple[list[CallBlock], list[tuple[int, int, str]]]:
    """Return the file's call blocks and its headings ``(line_index, level, title)``.

    Headings are collected only outside fences, so a ``#`` comment inside a shell
    block is never read as structure.
    """
    lines = text.split('\n')
    headings: list[tuple[int, int, str]] = []
    blocks: list[tuple[int, int, str]] = []
    open_fence: tuple[int, str, str] | None = None
    for index, line in enumerate(lines):
        fence = _FENCE_RE.match(line)
        if open_fence is None:
            if fence:
                open_fence = (index, fence.group('fence'), fence.group('lang').lower())
                continue
            heading = _HEADING_RE.match(line)
            if heading:
                headings.append((index, len(heading.group('hashes')), heading.group('title')))
            continue
        start, marker, lang = open_fence
        if fence and not fence.group('lang') and fence.group('fence').startswith(marker):
            if lang in _SHELL_LANGS:
                blocks.append((start, index, '\n'.join(lines[start + 1 : index])))
            open_fence = None

    call_blocks: list[CallBlock] = []
    for start, end, body in blocks:
        collapsed = _CONTINUATION_RE.sub(' ', body)
        if not _CALL_RE.search(collapsed):
            continue
        enclosing = [level for idx, level, _ in headings if idx < start]
        level = enclosing[-1] if enclosing else 0
        section_end = next((idx for idx, lvl, _ in headings if idx > end and lvl <= level), len(lines))
        call_blocks.append(
            CallBlock(
                path=path,
                line=start + 1,
                templated=bool(_TEMPLATED_RE.search(collapsed)),
                following='\n'.join(lines[end + 1 : section_end]),
            )
        )
    return call_blocks, headings


def _halt_rule_gates(path: Path, text: str) -> tuple[str, ...]:
    """The backticked ``*_without_asking`` gates the halt-rule section names, in first-mention order.

    The section runs from the anchor heading to the next heading at the same or a
    higher level; a document without the anchor heading names no gate.
    """
    lines = text.split('\n')
    _, headings = _parse(path, text)
    anchor = next(((idx, level) for idx, level, title in headings if _slug(title) == HALT_RULE_ANCHOR), None)
    if anchor is None:
        return ()
    start, level = anchor
    end = next((idx for idx, lvl, _ in headings if idx > start and lvl <= level), len(lines))
    return tuple(dict.fromkeys(_GATE_TOKEN_RE.findall('\n'.join(lines[start + 1 : end]))))


def _marker_offset(block: CallBlock, home: Path) -> int | None:
    """Offset of the first halt-rule marker in the block's following text, or ``None``.

    At the rule's home the marker is the anchor heading itself; everywhere else it
    is a link whose target resolves to the home file.
    """
    offsets: list[int] = []
    if block.path == home:
        for match in re.finditer(r'^#{1,6}[ \t]+(.*)$', block.following, re.M):
            if _slug(match.group(1)) == HALT_RULE_ANCHOR:
                offsets.append(match.start())
    for match in _LINK_RE.finditer(block.following):
        if (block.path.parent / match.group('target')).resolve() == home.resolve():
            offsets.append(match.start())
    return min(offsets) if offsets else None


def _recovery_codes(following: str) -> list[str]:
    """Every backticked code in the first column of a table carrying a ``Recovery`` column."""
    codes: list[str] = []
    rows = [line.strip() for line in following.split('\n')]
    index = 0
    while index < len(rows):
        if not rows[index].startswith('|'):
            index += 1
            continue
        table: list[str] = []
        while index < len(rows) and rows[index].startswith('|'):
            table.append(rows[index])
            index += 1
        header = [cell.strip().lower() for cell in table[0].strip('|').split('|')]
        if 'recovery' in header:
            for row in table[2:]:
                codes.extend(_BACKTICK_RE.findall(row.strip('|').split('|')[0]))
    return codes


def _violations(block: CallBlock, home: Path) -> list[str]:
    """What the block's section fails to carry; empty when it halts correctly."""
    problems: list[str] = []
    marker = _marker_offset(block, home)
    if marker is None:
        problems.append(f'{block.label}: no link to the #{HALT_RULE_ANCHOR} halt rule follows the call')
    gate_offsets = [block.following.find(gate) for gate in AUTO_CONTINUE_GATES if gate in block.following]
    if marker is not None and gate_offsets and min(gate_offsets) < marker:
        problems.append(f'{block.label}: an auto-continue gate is read before the halt-rule link')
    for code in _recovery_codes(block.following):
        if code not in VERIFY_REFUSAL_ERRORS:
            problems.append(f'{block.label}: recovery table names {code!r}, not a VERIFY_REFUSAL_ERRORS member')
    return problems


def _scan() -> tuple[list[CallBlock], list[Path], set[Path]]:
    """Scan the marketplace: call blocks, anchor homes, and files the raw regex hits."""
    call_blocks: list[CallBlock] = []
    homes: list[Path] = []
    raw_hits: set[Path] = set()
    for path in sorted(MARKETPLACE_ROOT.rglob('*.md')):
        text = path.read_text(encoding='utf-8')
        blocks, headings = _parse(path, text)
        call_blocks.extend(blocks)
        if any(_slug(title) == HALT_RULE_ANCHOR for _, _, title in headings):
            homes.append(path)
        if _RAW_CALL_RE.search(text):
            raw_hits.add(path)
    return call_blocks, homes, raw_hits


_CALL_BLOCKS, _HOMES, _RAW_HITS = _scan()
assert _CALL_BLOCKS, f'no fenced manage-status transition --completed call block found under {MARKETPLACE_ROOT}'
assert len(_HOMES) == 1, f'exactly one file must carry the #{HALT_RULE_ANCHOR} heading, found {_HOMES}'
_HOME = _HOMES[0]

#: The auto-continue gates a call site must not read ahead of the halt, derived from
#: the halt rule's own section rather than restated here.
AUTO_CONTINUE_GATES = _halt_rule_gates(_HOME, _HOME.read_text(encoding='utf-8'))
assert AUTO_CONTINUE_GATES, f'the #{HALT_RULE_ANCHOR} section in {_HOME} names no backticked *_without_asking gate'


def test_the_halt_rule_lives_under_its_anchor_in_the_phase_lifecycle_standard():
    """The canonical rule is stated once, in the shared completion protocol."""
    assert _HOME == MARKETPLACE_ROOT / 'plan-marshall/skills/ref-workflow-architecture/standards/phase-lifecycle.md', (
        f'the #{HALT_RULE_ANCHOR} heading must live in the phase-lifecycle standard, found in {_HOME}'
    )


def test_the_population_includes_a_templated_call_block():
    """The scan reaches ``--completed {placeholder}`` blocks, not only literal phase keys."""
    templated = [block.label for block in _CALL_BLOCKS if block.templated]

    assert templated, f'no templated call block among {[block.label for block in _CALL_BLOCKS]}'


def test_every_file_the_raw_regex_hits_yielded_a_parsed_call_block():
    """The fence parser and an independent raw regex agree on which files hold call sites."""
    parsed_files = {block.path for block in _CALL_BLOCKS}

    missed = sorted(str(path.relative_to(MARKETPLACE_ROOT)) for path in _RAW_HITS - parsed_files)

    assert _RAW_HITS, 'the raw cross-check regex matched no file, so it cross-checked nothing'
    assert not missed, f'files with a raw call-site match yielded no parsed call block: {missed}'


def test_a_recovery_table_exists_under_some_call_site():
    """The recovery-code check has a population to run over."""
    codes = [code for block in _CALL_BLOCKS for code in _recovery_codes(block.following)]

    assert codes, 'no call site carries a recovery table, so the code-membership check ran over nothing'


@pytest.mark.parametrize('block', _CALL_BLOCKS, ids=[block.label for block in _CALL_BLOCKS])
def test_every_call_site_links_the_halt_rule_before_any_continuation(block):
    """Each call block's section links the halt rule ahead of every auto-continue gate."""
    assert _violations(block, _HOME) == []


def _synthetic(tmp_path: Path, body: str) -> CallBlock:
    """Parse one synthetic document written under ``tmp_path`` and return its only call block."""
    path = tmp_path / 'synthetic.md'
    path.write_text(body, encoding='utf-8')
    blocks, _ = _parse(path, body)
    assert len(blocks) == 1, f'the synthetic document must hold exactly one call block, parsed {len(blocks)}'
    return blocks[0]


def test_a_literal_call_followed_by_a_finalize_gate_is_flagged(tmp_path):
    """Negative control: the continuation shape the rule exists to forbid is caught."""
    block = _synthetic(
        tmp_path,
        '### Phase Transition\n\n```bash\npython3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
        'transition \\\n  --plan-id {plan_id} --completed 5-execute\n```\n\n'
        'Check `finalize_without_asking` and continue to finalize.\n',
    )

    assert _violations(block, _HOME) == [
        f'synthetic.md:3: no link to the #{HALT_RULE_ANCHOR} halt rule follows the call'
    ]


def test_a_templated_call_followed_by_an_unconditional_auto_transition_is_flagged(tmp_path):
    """Negative control: a placeholder phase key is in the population and caught the same way."""
    block = _synthetic(
        tmp_path,
        '## Phase Transition\n\n1. Transition:\n   ```bash\n   python3 .plan/execute-script.py '
        'plan-marshall:manage-status:manage-status transition --plan-id {plan_id} --completed {phase}\n   ```\n\n'
        '2. **Auto-transition** to next phase.\n',
    )

    assert block.templated, 'the synthetic block must be recognised as templated'
    assert _violations(block, _HOME) == [
        f'synthetic.md:4: no link to the #{HALT_RULE_ANCHOR} halt rule follows the call'
    ]


def test_an_equals_form_call_without_the_link_is_flagged(tmp_path):
    """Negative control: ``--completed=<phase>`` joins the population and is checked like the space form."""
    block = _synthetic(
        tmp_path,
        '### Phase Transition\n\n```bash\npython3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
        'transition --plan-id {plan_id} --completed=4-plan\n```\n\n'
        'Continue to the next phase.\n',
    )

    assert _violations(block, _HOME) == [
        f'synthetic.md:3: no link to the #{HALT_RULE_ANCHOR} halt rule follows the call'
    ]


@pytest.mark.parametrize('gate', AUTO_CONTINUE_GATES)
def test_a_gate_read_ahead_of_the_link_is_flagged(tmp_path, gate):
    """Negative control: a link that arrives only after any derived gate is read does not halt the run."""
    link = os.path.relpath(_HOME, tmp_path)
    block = _synthetic(
        tmp_path,
        '### Phase Transition\n\n```bash\npython3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
        'transition --plan-id {plan_id} --completed 4-plan\n```\n\n'
        f'Read `{gate}` and continue.\n\n'
        f'See the [halt rule]({link}#{HALT_RULE_ANCHOR}).\n',
    )

    assert _violations(block, _HOME) == ['synthetic.md:3: an auto-continue gate is read before the halt-rule link']


@pytest.mark.parametrize('gate', AUTO_CONTINUE_GATES)
def test_a_call_linking_the_rule_before_its_gate_passes(tmp_path, gate):
    """Positive control: the compliant shape is not flagged for any derived gate, so the predicate is satisfiable."""
    link = os.path.relpath(_HOME, tmp_path)
    block = _synthetic(
        tmp_path,
        '### Phase Transition\n\n```bash\npython3 .plan/execute-script.py plan-marshall:manage-status:manage-status '
        'transition --plan-id {plan_id} --completed 4-plan\n```\n\n'
        f'On any non-success result, STOP per the [halt rule]({link}#{HALT_RULE_ANCHOR}).\n\n'
        f'Then read `{gate}`.\n',
    )

    assert _violations(block, _HOME) == []


def test_the_gate_derivation_reads_only_the_halt_rule_section():
    """The deriver collects the anchor section's backticked gates and stops at the next peer heading."""
    text = (
        '### Step 1: Transition\n\n#### Refused-transition halt rule\n\n'
        'No gate (`alpha_without_asking`, `beta_without_asking`) is read; `alpha_without_asking` again.\n\n'
        '#### On a successful transition\n\nRead `delta_without_asking`.\n'
    )

    assert _halt_rule_gates(Path('synthetic.md'), text) == ('alpha_without_asking', 'beta_without_asking')


def test_a_document_without_the_anchor_derives_no_gate():
    """Negative control: a missing anchor yields the empty set the binding-site guard refuses."""
    text = '#### Some other rule\n\nRead `alpha_without_asking`.\n'

    assert _halt_rule_gates(Path('synthetic.md'), text) == ()


def test_a_recovery_table_naming_an_unlisted_code_is_flagged():
    """Negative control: a recovery table cannot invent a refusal code."""
    following = '| Refusal | Condition | Recovery |\n|---|---|---|\n| `made_up_refusal` | invented | retry |\n'

    assert _recovery_codes(following) == ['made_up_refusal']
    assert 'made_up_refusal' not in VERIFY_REFUSAL_ERRORS
