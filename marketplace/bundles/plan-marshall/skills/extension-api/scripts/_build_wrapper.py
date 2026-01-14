#!/usr/bin/env python3
"""Platform-aware build wrapper detection.

Provides centralized wrapper detection for all build tools,
selecting the appropriate variant based on the operating system.

On Windows: Uses .bat/.cmd variants (pw.bat, mvnw.cmd, gradlew.bat)
On Unix: Uses shell scripts (pw, mvnw, gradlew)
"""

import shutil
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == 'win32'


def detect_wrapper(
    project_dir: str,
    unix_wrapper: str,
    windows_wrapper: str,
    system_fallback: str | None = None,
) -> str | None:
    """Detect build wrapper based on platform.

    Args:
        project_dir: Project root directory.
        unix_wrapper: Unix wrapper filename (e.g., 'pw', 'mvnw', 'gradlew').
        windows_wrapper: Windows wrapper filename (e.g., 'pw.bat', 'mvnw.cmd').
        system_fallback: Optional system command to check on PATH.

    Returns:
        Path to wrapper or system command, None if not found.
    """
    root = Path(project_dir).resolve()

    if IS_WINDOWS:
        wrapper_path = root / windows_wrapper
        if wrapper_path.exists() and wrapper_path.is_file():
            return str(wrapper_path)
    else:
        wrapper_path = root / unix_wrapper
        if wrapper_path.exists() and wrapper_path.is_file():
            return f'./{unix_wrapper}'

    # Fallback to system command
    if system_fallback and shutil.which(system_fallback):
        return system_fallback

    return None


def has_wrapper(project_root: Path, unix_wrapper: str, windows_wrapper: str) -> bool:
    """Check if wrapper exists for current platform.

    Args:
        project_root: Project root directory.
        unix_wrapper: Unix wrapper filename.
        windows_wrapper: Windows wrapper filename.

    Returns:
        True if wrapper exists for current platform.
    """
    if IS_WINDOWS:
        return (project_root / windows_wrapper).exists()
    return (project_root / unix_wrapper).exists()
