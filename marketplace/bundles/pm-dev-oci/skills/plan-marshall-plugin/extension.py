#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Extension API for pm-dev-oci bundle.

Provides OCI container standards and security best practices.

No build system detection or module discovery — this domain provides
standards only for container-related development.
"""

from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """OCI container extension for pm-dev-oci bundle."""

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if OCI domain applies based on Dockerfile or container config."""
        paths = module_data.get('paths') or {}
        module_path = paths.get('module') or ''
        sources = paths.get('sources') or []

        signals = []
        all_paths = [module_path] + sources
        container_filenames = (
            'dockerfile',
            'containerfile',
            'docker-compose',
            'compose.yml',
            'compose.yaml',
            '.dockerignore',
            '.containerignore',
            '.hadolint.yaml',
            '.hadolint.yml',
            '.trivyignore',
        )
        container_dirs = ('docker/',)
        for p in all_paths:
            p_lower = str(p).lower()
            if any(name in p_lower for name in container_filenames):
                signals.append(f'Container config: {p}')
            elif any(d in p_lower for d in container_dirs):
                signals.append(f'Container directory: {p}')

        # Check metadata for container indicators
        metadata = module_data.get('metadata') or {}
        if metadata.get('packaging') == 'docker' or metadata.get('container'):
            signals.append('container metadata detected')

        if not signals:
            return {
                'applicable': False,
                'confidence': 'none',
                'signals': [],
                'additive_to': None,
                'skills_by_profile': {},
            }

        return self._build_applicable_result('high', signals, module_data=module_data, active_profiles=active_profiles)

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-oci:ext-triage-oci'

    def provides_file_globs(self) -> list[str]:
        """Declare the container-manifest globs this domain owns.

        One glob per entry of the ``container_filenames`` set ``applies_to_module``
        recognises above — the container manifests, ignore files, and lint/scan
        descriptors ADR-004 records this bundle as recognising for Axis-A. Those
        same files have NO Axis-B owner: there is no ``build-oci``
        ``BuildExtensionBase``, they contribute no ``build.map`` route, and this
        declaration adds none. Recognised for skill-loading, absent from build
        routing, exactly as ADR-004 § Consequences requires.

        Written in the ``file_globs`` dialect, where a leading ``**/`` matches zero
        or more path segments — so a repo-root ``Dockerfile`` matches as well as a
        ``docker/Dockerfile``.
        """
        return [
            '**/Dockerfile',
            '**/Containerfile',
            '**/docker-compose.yml',
            '**/docker-compose.yaml',
            '**/compose.yml',
            '**/compose.yaml',
            '**/.dockerignore',
            '**/.containerignore',
            '**/.hadolint.yaml',
            '**/.hadolint.yml',
            '**/.trivyignore',
        ]

    def get_skill_domains(self) -> list[dict]:
        """Domain metadata for skill loading."""
        return [
            {
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
                                'description': 'OCI container standards, Dockerfile best practices, and build-context hardening (secrets management, .dockerignore secret exclusion, BuildKit secrets)',
                            },
                        ],
                        'optionals': [],
                    },
                    'implementation': {'defaults': [], 'optionals': []},
                    'module_testing': {'defaults': [], 'optionals': []},
                    'quality': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-oci:oci-security',
                                'description': 'Container security standards and OWASP best practices',
                            },
                        ],
                        'optionals': [],
                    },
                    'security': {
                        'defaults': [
                            {
                                'skill': 'pm-dev-oci:oci-security',
                                'description': 'Container runtime hardening, supply-chain controls, and OWASP Docker Top 10',
                            },
                        ],
                        'optionals': [],
                    },
                },
            }
        ]
