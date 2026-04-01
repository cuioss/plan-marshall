#!/usr/bin/env python3
"""Search-markers subcommand for OpenRewrite TODO markers (Maven wrapper).

Thin wrapper delegating to shared _markers_search module with Maven defaults.
Maven default: extensions='.java', standard skip patterns.
"""

from _markers_search import cmd_search_markers  # noqa: F401 — re-exported for maven.py
