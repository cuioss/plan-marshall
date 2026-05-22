#!/usr/bin/env python3
"""Print the marshall-steward ASCII-art banner to stdout.

Bootstrap-capable: this script takes no executor dependency and is invoked
via a direct Python path (the same bootstrap convention determine_mode.py
uses at SKILL.md Step 1). It exposes a no-argument invocation that prints
the banner and exits 0.

Usage:
    python3 print_logo.py
"""

import sys

BANNER = r"""
╔═══════════════════════════════════════════════════════════════════════╗
║                                 :                                     ║
║                               .;:;.                                   ║
║                              :;:::;:                                  ║
║          ...             .;:::::::::;.              ...               ║
║          .::;:::::::::::::;:::::::::;:::::::::::::;::.                ║
║               :;:::::::::::::::::::::::::::::::;:                     ║
║                .;:::::::::::::::::::::::::::::;.                      ║
║                                                                       ║
║                        █▀█ █   █▀█ █▄ █                               ║
║                        █▀▀ █▄▄ █▀█ █ ▀█                               ║
║                  █▀▄▀█ █▀█ █▀█ █▀ █ █ █▀█ █   █                       ║
║                  █ ▀ █ █▀█ █▀▄ ▄█ █▀█ █▀█ █▄▄ █▄▄                     ║
║                                                                       ║
║                .;:::::::::::::::::::::::::::::;.                      ║
║               :;:::::::::::::::::::::::::::::::;:                     ║
║          .::;:::::::::::::;:::::::::;:::::::::::::;::.                ║
║         ...              .;:::::::::;.              ...               ║
║                              :;:::;:                                  ║
║                               .;:;.                                   ║
║                                 :                                     ║
╚═══════════════════════════════════════════════════════════════════════╝
"""


def main() -> int:
    """Print the banner and return a success exit code."""
    print(BANNER.strip("\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
