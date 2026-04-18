"""Build-time guard enforcing conftest.py discipline across the test tree.

This test walks ``test/**/conftest.py`` and asserts that only the two sanctioned
conftest modules exist: ``test/conftest.py`` (root) and ``test/adapters/conftest.py``
(adapter-specific). Every other conftest.py is a sibling-fixture anti-pattern that
must be renamed to ``_fixtures.py`` per the shared testing standards.

Rationale: Sibling ``conftest.py`` files shadow each other during pytest discovery
and silently leak fixtures across unrelated test modules. Renaming them to
``_fixtures.py`` (explicit import) keeps fixture scoping intentional.

Guidance: ``plan-marshall:dev-general-module-testing`` and
``pm-dev-python:pytest-testing``.
"""

from pathlib import Path

ALLOWED_CONFTESTS: frozenset[str] = frozenset(
    {
        "test/conftest.py",
        "test/adapters/conftest.py",
    }
)


def test_no_unsanctioned_conftest_files() -> None:
    project_root = Path(__file__).resolve().parent.parent
    test_dir = project_root / "test"

    discovered = {
        conftest.relative_to(project_root).as_posix()
        for conftest in test_dir.rglob("conftest.py")
    }

    offenders = discovered - ALLOWED_CONFTESTS

    assert not offenders, (
        "Unsanctioned conftest.py files found:\n"
        + "\n".join(f"  - {path}" for path in sorted(offenders))
        + "\n\nRename to '_fixtures.py' per plan-marshall:dev-general-module-testing"
        " / pm-dev-python:pytest-testing guidance. Sibling conftest.py files leak"
        " fixtures across unrelated modules; explicit imports from _fixtures.py"
        " keep fixture scope intentional.\n\nAllowed conftest.py locations:\n"
        + "\n".join(f"  - {path}" for path in sorted(ALLOWED_CONFTESTS))
    )
