#!/usr/bin/env python3
"""Extension API for pm-dev-oci bundle.

Provides OCI container standards and security best practices.

No build system detection or module discovery — this domain provides
standards only for container-related development.
"""

from extension_base import ExtensionBase  # type: ignore[import-not-found]


class Extension(ExtensionBase):
    """OCI container extension for pm-dev-oci bundle."""

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            'domain': {
                'key': 'oci-containers',
                'name': 'OCI Containers',
                'description': 'OCI container standards, Dockerfile best practices, and container security',
            },
            'profiles': {
                'core': {
                    'defaults': [
                        {
                            'skill': 'pm-dev-oci:oci-standards',
                            'description': 'OCI container standards and Dockerfile best practices',
                        },
                    ],
                    'optionals': [
                        {
                            'skill': 'pm-dev-oci:oci-security',
                            'description': 'Container security standards and OWASP best practices',
                        },
                    ],
                },
                'implementation': {'defaults': [], 'optionals': []},
                'module_testing': {'defaults': [], 'optionals': []},
                'quality': {'defaults': [], 'optionals': []},
            },
        }
