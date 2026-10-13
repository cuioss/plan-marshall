#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared scanners for the two review step doc-contract test modules.

``test_code_review_contract.py`` and ``test_functional_review_contract.py`` pin
the same two clauses against their own step document:

* every placeholder in a free-text argument (``--message`` / ``--title`` /
  ``--detail`` / ``--display-detail``) sits inside one single-quoted shell word,
  and no placeholder rides a bare word after that argument;
* every advisory decision-log template is followed by a halt rule before the
  ``mark-step-done`` that records the outcome.

The scanners live here once; each test module keeps its own per-document
constants (rule heading, owner, anchor) and its own controls.
"""

from __future__ import annotations

import re

#: The arguments through which a template carries free text into a command.
FREE_TEXT_FLAGS = ('--message', '--title', '--detail', '--display-detail')
#: The alternation of :data:`FREE_TEXT_FLAGS`, derived so a flag added to the
#: declared set is scanned without a second edit.
FREE_TEXT_FLAG = '(?:' + '|'.join(re.escape(flag) for flag in FREE_TEXT_FLAGS) + ')'
DOUBLE_QUOTED_PLACEHOLDER_RE = re.compile(rf'{FREE_TEXT_FLAG}\s+"[^"\n]*\{{')
SINGLE_QUOTED_PLACEHOLDER_RE = re.compile(rf"{FREE_TEXT_FLAG}\s+'[^'\n]*\{{")
#: A free-text flag and the separator before its argument.
FREE_TEXT_ARGUMENT_RE = re.compile(rf'(?<![\w-]){FREE_TEXT_FLAG}(?:\s+|=)')
#: The one safe form: the whole argument is a single single-quoted shell word.
ONE_SINGLE_QUOTED_WORD_RE = re.compile(r"'[^'\n]*'")
#: A fence at any indentation — a template inside a list item is indented.
ANY_FENCE_RE = re.compile(r'^\s*```(\w*)\s*$')

#: The halt rule that must sit between an advisory decision-log template and the
#: ``mark-step-done`` that records the outcome after it.
ADVISORY_HALT_RE = re.compile(
    r'On a non-`success` return from any advisory line[^\n]*do NOT record[^\n]*surface the returned error and halt'
)


# ---------------------------------------------------------------------------
# Command templates
# ---------------------------------------------------------------------------


def bash_blocks_with_lead_in(text: str) -> list[tuple[str, str]]:
    """Every ``bash`` block, indented ones included, paired with the prose that introduces it.

    Blocks separated only by blank lines share one lead-in: the prose before the
    first of them introduces the whole run.
    """
    pairs: list[tuple[str, str]] = []
    lead_in: list[str] = []
    block: list[str] | None = None
    language = ''
    after_block = False
    for line in text.splitlines():
        fence = ANY_FENCE_RE.match(line)
        if fence and block is None:
            block, language = [], fence.group(1)
            continue
        if fence and block is not None:
            if language == 'bash':
                pairs.append((' '.join(lead_in), '\n'.join(block)))
            block, after_block = None, True
            continue
        if block is not None:
            block.append(line)
        elif line.strip():
            lead_in = [line] if after_block else [*lead_in, line]
            after_block = False
    return pairs


def logical_commands(block: str) -> list[str]:
    """Every logical command of ``block``: backslash-continued lines joined into one."""
    joined = block.replace('\\\n', ' ')
    return [line.strip() for line in joined.splitlines() if line.strip()]


def free_text_lines(block: str, pattern: re.Pattern[str]) -> list[str]:
    return [line.strip() for line in block.splitlines() if pattern.search(line)]


def shell_words(text: str) -> list[str]:
    """The shell words of ``text``, split on whitespace outside quotes, quotes kept."""
    words: list[str] = []
    current: list[str] = []
    quote = ''
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            quote = '' if char == quote else quote
            current.append(char)
        elif char == '\\':
            current.append(text[index : index + 2])
            index += 1
        elif char in ('"', "'"):
            quote = char
            current.append(char)
        elif char.isspace():
            if current:
                words.append(''.join(current))
                current = []
        else:
            current.append(char)
        index += 1
    if current:
        words.append(''.join(current))
    return words


def _is_flag(word: str) -> bool:
    return word.startswith('-')


def unquoted_free_text_arguments(command: str) -> list[str]:
    """Every placeholder ``command`` passes as free text outside one single-quoted argument.

    Two shapes offend. A free-text argument that carries a placeholder but is not
    one single-quoted word — bare, partly quoted, or double-quoted. And, once a
    free-text flag has been seen, any bare word that carries a placeholder: a word
    that is neither a flag nor the argument right after one lands as an unquoted
    shell word, whatever was quoted before it. Backslash-continued lines are
    joined first, so a word on a continuation line is read as part of its command.
    """
    words = shell_words(command.replace('\\\n', ' '))
    offenders: list[str] = []
    free_text_span = ''
    index = 0
    while index < len(words):
        word = words[index]
        if not _is_flag(word):
            if free_text_span and '{' in word:
                offenders.append(f'{free_text_span} {word}')
            index += 1
            continue
        flag, separator, inline = word.partition('=')
        takes_next = not separator and index + 1 < len(words) and not _is_flag(words[index + 1])
        argument = inline if separator else (words[index + 1] if takes_next else '')
        if flag in FREE_TEXT_FLAGS:
            free_text_span = word if separator else f'{word} {argument}'.rstrip()
            if '{' in argument and not ONE_SINGLE_QUOTED_WORD_RE.fullmatch(argument):
                offenders.append(free_text_span)
        index += 2 if takes_next else 1
    return offenders


# ---------------------------------------------------------------------------
# Advisory lines and the halt rule
# ---------------------------------------------------------------------------


def is_advisory_template(block: str) -> bool:
    return 'manage-logging' in block and 'decision' in block and ') Advisory ' in block


def unhalted_advisory_templates(text: str) -> list[str]:
    """Every advisory template in ``text`` followed by a ``mark-step-done`` with no halt rule in between.

    An advisory template after which no ``mark-step-done`` follows records
    nothing over the line, so it is not read.
    """
    items: list[tuple[str, str]] = []
    block: list[str] | None = None
    for line in text.splitlines():
        if ANY_FENCE_RE.match(line):
            if block is None:
                block = []
            else:
                items.append(('block', '\n'.join(block)))
                block = None
            continue
        if block is not None:
            block.append(line)
        else:
            items.append(('prose', line))

    unhalted: list[str] = []
    for index, (kind, content) in enumerate(items):
        if kind != 'block' or not is_advisory_template(content):
            continue
        prose: list[str] = []
        for later_kind, later in items[index + 1 :]:
            if later_kind == 'block' and 'mark-step-done' in later:
                if not ADVISORY_HALT_RE.search(' '.join(prose)):
                    unhalted.append(next(line.strip() for line in content.splitlines() if 'Advisory' in line))
                break
            if later_kind == 'prose':
                prose.append(later)
    return unhalted
