#!/usr/bin/env python3
"""Extension API for pm-dev-general bundle.

Provides cross-cutting development principles (code quality, documentation,
testing methodology) applicable to any programming language.

No build system detection or module discovery — this domain provides
standards only, composed into other domains' profiles or used standalone.
"""

from extension_base import ExtensionBase  # type: ignore[import-not-found]


class Extension(ExtensionBase):
    """General development extension for pm-dev-general bundle."""

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'general-dev',
                'name': 'General Development',
                'description': 'Cross-cutting code quality, documentation, and testing methodology',
            },
            'profiles': {
                'core': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-general:dev-code-quality',
                            'description': 'Language-agnostic code quality principles (SRP, CQS, complexity, error handling)',
                        },
                    ],
                    'optionals': [],
                },
                'implementation': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-general:dev-code-documentation',
                            'description': 'Language-agnostic documentation principles (what/when/how to document)',
                        },
                    ],
                    'optionals': [],
                },
                'module_testing': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-general:dev-testing',
                            'description': 'Language-agnostic testing methodology (AAA, coverage, reliability, determinism)',
                        },
                    ],
                    'optionals': [],
                },
                'quality': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-general:dev-code-documentation',
                            'description': 'Language-agnostic documentation principles (what/when/how to document)',
                        },
                    ],
                    'optionals': [],
                },
            },
        }
