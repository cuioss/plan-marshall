#!/usr/bin/env python3
"""Search-markers subcommand for OpenRewrite TODO markers (Gradle wrapper).

Thin wrapper delegating to shared _markers_search module with Gradle defaults.
Gradle default: extensions='.java,.kt', skip 'build/', '.gradle/' in addition to standard patterns.
"""

from _markers_search import cmd_search_markers  # noqa: F401 — re-exported for gradle.py
