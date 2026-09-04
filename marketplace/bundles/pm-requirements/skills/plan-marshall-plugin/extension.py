#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Extension API for pm-requirements bundle.

Provides skill-only domain detection for requirements engineering projects.
"""

from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Requirements extension for pm-requirements bundle.

    This is a knowledge-only domain: it provides authoring standards but no
    implementation, testing, or quality-gate skills.  The empty profiles
    below are intentional — requirements engineering guides content creation,
    it does not generate or verify code.
    """

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-requirements:ext-triage-reqs'

    def provides_file_globs(self) -> list[str]:
        """Declare no file globs — this domain owns no distinct file type.

        The empty list is a deliberate declaration, not an omission. Requirements
        are written as ordinary prose documents in whatever format the project
        already uses, and this bundle claims no requirements-document tree of its
        own: it registers no ``discover_modules`` and no Axis-D ``claim_paths``, so
        there is no path shape it could name that would not also name another
        domain's documents. A suffix claim over prose files would union this domain
        into every documentation change, which is what the ``file_globs`` inclusion
        leg exists to avoid. A project that does keep a distinct requirements tree
        declares it with ``set-inclusion``, whose operator value wins over the seed.
        """
        return []

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [
            {
                'domain': {
                    'key': 'requirements',
                    'name': 'Requirements Engineering',
                    'description': 'User stories, acceptance criteria, specifications',
                },
                'profiles': {
                    'core': {
                        'defaults': [
                            {
                                'skill': 'pm-requirements:requirements-authoring',
                                'description': 'Requirements authoring standards for user stories and acceptance criteria',
                            },
                        ],
                        'optionals': [],
                    },
                    # Knowledge-only domain: no implementation, testing, or quality skills
                    'implementation': {'defaults': [], 'optionals': []},
                    'module_testing': {'defaults': [], 'optionals': []},
                    'quality': {'defaults': [], 'optionals': []},
                },
            }
        ]
