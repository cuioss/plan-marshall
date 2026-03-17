#!/usr/bin/env python3
"""Extension API for pm-dev-oci bundle.

Provides OCI container standards and security best practices.

No build system detection or module discovery — this domain provides
standards only for container-related development.
"""

from extension_base import ExtensionBase  # type: ignore[import-not-found]


class Extension(ExtensionBase):
    """OCI container extension for pm-dev-oci bundle."""

    def applies_to_module(self, module_data: dict,
                          active_profiles: set[str] | None = None) -> dict:
        """Check if OCI domain applies based on Dockerfile or container config."""
        paths = module_data.get('paths', {})
        module_path = paths.get('module', '')
        sources = paths.get('sources', [])

        signals = []
        all_paths = [module_path] + sources
        for p in all_paths:
            p_lower = str(p).lower()
            if 'dockerfile' in p_lower or 'containerfile' in p_lower:
                signals.append(f'Dockerfile in {p}')

        # Check metadata for container indicators
        metadata = module_data.get('metadata', {})
        if metadata.get('packaging') == 'docker' or metadata.get('container'):
            signals.append('container metadata detected')

        if not signals:
            return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}

        return self._build_applicable_result('high', signals,
                                              module_data=module_data,
                                              active_profiles=active_profiles)

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [{
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
        }]
