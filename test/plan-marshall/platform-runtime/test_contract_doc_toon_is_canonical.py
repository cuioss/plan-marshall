#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pin the platform-runtime standards' TOON examples to the real serializer.

Every documented payload in these standards is a claim about what the runtime
emits, and until now nothing checked it. That gap is not theoretical: the
``project install-hook`` examples were once written by hand and documented an
inline ``key[N]: a,b,c`` list the serializer has never produced for a list of
strings, alongside a render-event label that does not exist. The quality gate,
plugin-doctor and the whole test suite passed over it, because a false sentence
in a document type-checks and lints exactly like a true one.

A round-trip is what closes it. ``serialize_toon`` has one canonical rendering
per value, so a block that survives ``serialize_toon(parse_toon(block))``
unchanged is in the shape the runtime actually emits, and a block that does not
is in a shape it cannot. The expectation is NOT computed from the document — it
comes from the serializer the production code calls.

What this does and does not buy: it pins SHAPE, not content. A block claiming a
field the operation never sets still round-trips, so this cannot replace reading
the payload against its producer. It does make the whole class of
transcription-invented syntax impossible to land.
"""

import pathlib  # noqa: I001

import pytest

# conftest.py sets up PYTHONPATH so imports resolve without manual sys.path work.
from toon_parser import parse_toon, serialize_toon

_STANDARDS = (
    pathlib.Path(__file__).resolve().parents[3]
    / "marketplace"
    / "bundles"
    / "plan-marshall"
    / "skills"
    / "platform-runtime"
    / "standards"
)


def _toon_blocks(doc: pathlib.Path) -> list[tuple[int, str]]:
    """Return EVERY fenced ``toon`` block in *doc* as ``(line_number, body)``.

    Nothing is exempted. An earlier version skipped blocks containing
    ``<angle-bracket>`` placeholders on the theory that a template is not a
    payload, and that exemption immediately hid a real defect: an ``io_error``
    example whose ``message`` was unquoted where the serializer quotes it. A
    placeholder sits in a VALUE, and a value with a placeholder still renders
    the way the serializer renders values — so a template can be canonical, and
    every one in these standards is. An exemption that is not needed is only a
    place for defects to hide.
    """
    blocks: list[tuple[int, str]] = []
    body: list[str] | None = None
    start = 0
    for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip() == "```toon" and body is None:
            body, start = [], lineno
        elif line.strip() == "```" and body is not None:
            blocks.append((start, "\n".join(body)))
            body = None
        elif body is not None:
            body.append(line)
    return blocks


def _cases() -> list[tuple[str, int, str]]:
    cases = [
        (doc.name, lineno, block)
        for doc in sorted(_STANDARDS.glob("*.md"))
        for lineno, block in _toon_blocks(doc)
    ]
    assert cases, f"no TOON blocks found under {_STANDARDS} — the scan is broken"
    return cases


@pytest.mark.parametrize(
    ("doc_name", "lineno", "block"),
    _cases(),
    ids=[f"{doc}-L{line}" for doc, line, _ in _cases()],
)
def test_documented_toon_block_is_what_the_serializer_emits(
    doc_name: str, lineno: int, block: str
) -> None:
    """Each documented payload round-trips through the canonical serializer unchanged."""
    assert serialize_toon(parse_toon(block)) == block, (
        f"{doc_name}:{lineno} is not in the shape serialize_toon emits — "
        f"it documents a payload the runtime cannot produce"
    )
