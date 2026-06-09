#!/usr/bin/env python3
"""Extension API for pm-dev-oci bundle.

Provides OCI container standards and security best practices.

No build system detection or module discovery — this domain provides
standards only for container-related development.
"""

from extension_base import ExtensionBase  # type: ignore[import-not-found]


class Extension(ExtensionBase):
    """OCI container extension for pm-dev-oci bundle."""

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        """Check if OCI domain applies based on Dockerfile or container config."""
        paths = module_data.get('paths', {})
        module_path = paths.get('module', '')
        sources = paths.get('sources', [])

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
        metadata = module_data.get('metadata', {})
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

    # =========================================================================
    # File-type classifier
    # =========================================================================

    _PRODUCTION_FILENAME_PREFIXES: tuple[str, ...] = ('Dockerfile', 'Containerfile')
    _PRODUCTION_FILENAMES: tuple[str, ...] = ('.dockerignore',)
    _CONFIG_FILENAMES: tuple[str, ...] = ('compose.yml', 'docker-compose.yml', 'compose.yaml', 'docker-compose.yaml')

    def _match_classify(self, path: str) -> tuple[str, int] | None:
        filename = path.rsplit('/', 1)[-1]
        if filename in self._PRODUCTION_FILENAMES:
            return 'production', 1
        for prefix in self._PRODUCTION_FILENAME_PREFIXES:
            if filename.startswith(prefix):
                return 'production', 1
        if filename in self._CONFIG_FILENAMES:
            return 'config', 1
        return None

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        """Classify paths for the OCI containers domain.

        See extension-api/standards/extension-contract.md § classify_paths()
        for the full contract.
        """
        claims: dict[str, list[str]] = {
            'production': [], 'test': [], 'documentation': [], 'config': []
        }
        for path in paths:
            match = self._match_classify(path)
            if match is not None:
                claims[match[0]].append(path)
        return claims

    def classify_path_specificity(self, path: str, role: str) -> int:
        match = self._match_classify(path)
        if match is not None and match[0] == role:
            return match[1]
        return 0

    def classify_globs(self) -> list[tuple[str, str]]:
        """Return the OCI domain's portable (suffix, role_heuristic) vocabulary.

        Container build files are claimed under the location-agnostic
        ``production-by-location`` heuristic — ``.dockerignore`` and the
        ``Dockerfile`` / ``Containerfile`` family (matched as a basename suffix,
        so ``Dockerfile`` and ``app.Dockerfile`` are both caught). Compose files
        are claimed under ``config``. The deriver emits a concrete glob covering
        every matching file in the tree. See the base classify_globs() contract.
        """
        vocabulary: list[tuple[str, str]] = []
        # Production — exact .dockerignore and the Dockerfile / Containerfile family.
        for name in self._PRODUCTION_FILENAMES:
            vocabulary.append((name, 'production-by-location'))
        for name in self._PRODUCTION_FILENAME_PREFIXES:
            vocabulary.append((name, 'production-by-location'))
        # Config — compose / docker-compose filenames.
        for name in self._CONFIG_FILENAMES:
            vocabulary.append((name, 'config'))
        return vocabulary

    # build_class: this extension claims the ``production`` / ``config`` roles
    # (Dockerfile/Containerfile production; compose config), for which the
    # ExtensionBase defaults (``production → compile``,
    # ``config → verify``) are correct. No classify_build_class
    # override is required — the inherited base default is the contract.

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
                                'description': 'OCI container standards and Dockerfile best practices',
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
                },
            }
        ]
