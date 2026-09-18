#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Message-formatting and population measurements for the derivation.

This module holds the measurement half of the former
``_exit_code_convention_derivation`` helper: the :class:`Coverage`,
:class:`BodySweep`, and :class:`Derivation` records plus :func:`derive` and
:func:`sweep_convention_bodies`. Cause-selection predicates live in
``_exit_code_convention_derivation_causes`` and are imported here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from _exit_code_convention_derivation_causes import (
    EXECUTOR_TOKEN,
    NARROW,
    NONE,
    WIDENED,
    classify,
    documents,
    invoked_notations,
    retains,
)

from conftest import PROJECT_ROOT


@dataclass(frozen=True)
class Coverage:
    """What the walk actually reached, reported beside what it found."""

    #: Markdown files under ``marketplace/`` that were read successfully.
    files_scanned: int
    #: Repo-relative paths that could not be decoded, named rather than dropped.
    unreadable: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """True only when something was scanned and nothing was unreadable."""
        return self.files_scanned > 0 and not self.unreadable


@dataclass(frozen=True)
class BodySweep:
    """Where the contract is stated in full, and what was swept to establish it."""

    #: Repo-relative paths of every document stating the contract in full.
    documents: tuple[str, ...]
    coverage: Coverage

    @property
    def occurrences(self) -> int:
        """How many documents state the contract in full."""
        return len(self.documents)


@dataclass(frozen=True)
class Derivation:
    """The three disjoint classes of the retained population, plus coverage."""

    #: Documents that reach the contract.
    widened: tuple[str, ...]
    #: Documents carrying a convention heading that reaches nothing.
    narrow: tuple[str, ...]
    #: Documents carrying no exit-code convention heading at all.
    none: tuple[str, ...]
    coverage: Coverage

    @property
    def population_size(self) -> int:
        """How many documents were retained and classified."""
        return len(self.widened) + len(self.narrow) + len(self.none)


def derive(root: Path | None = None) -> Derivation:
    """Walk the skill documents under *root* and return the classified population."""
    from _exit_code_convention_derivation_causes import states_full_contract

    base = Path(root) if root is not None else PROJECT_ROOT

    buckets: dict[str, list[str]] = {WIDENED: [], NARROW: [], NONE: []}
    unreadable: list[str] = []
    files_scanned = 0

    for path in documents(base):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            unreadable.append(path.relative_to(base).as_posix())
            continue
        files_scanned += 1
        if EXECUTOR_TOKEN not in text:
            continue
        if not retains(invoked_notations(text)):
            continue
        buckets[classify(text)].append(path.relative_to(base).as_posix())

    return Derivation(
        widened=tuple(buckets[WIDENED]),
        narrow=tuple(buckets[NARROW]),
        none=tuple(buckets[NONE]),
        coverage=Coverage(files_scanned=files_scanned, unreadable=tuple(unreadable)),
    )


def sweep_convention_bodies(root: Path | None = None) -> BodySweep:
    """Find every document under *root* that states the contract in full."""
    from _exit_code_convention_derivation_causes import states_full_contract

    base = Path(root) if root is not None else PROJECT_ROOT

    found: list[str] = []
    unreadable: list[str] = []
    files_scanned = 0

    for path in documents(base):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            unreadable.append(path.relative_to(base).as_posix())
            continue
        files_scanned += 1
        if states_full_contract(text):
            found.append(path.relative_to(base).as_posix())

    return BodySweep(
        documents=tuple(found),
        coverage=Coverage(files_scanned=files_scanned, unreadable=tuple(unreadable)),
    )
