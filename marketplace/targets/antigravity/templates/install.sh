#!/usr/bin/env bash
# SPDX-License-Identifier: FSL-1.1-ALv2
set -euo pipefail

REPO="cuioss/plan-marshall"
DEFAULT_REF="dist-antigravity"
DEFAULT_GLOBAL_DIR="${HOME}/.gemini/config/plugins/plan-marshall"
DEFAULT_WORKSPACE_DIR="${PWD}/.agents/plugins/plan-marshall"

SCOPE="global"
TARGET_DIR=""
REF="${DEFAULT_REF}"
UNINSTALL=false

show_help() {
  cat <<'EOF'
Plan Marshall - Google Antigravity Plugin Installer

Usage:
  curl -fsSL https://raw.githubusercontent.com/cuioss/plan-marshall/dist-antigravity/install.sh | bash
  ./install.sh [OPTIONS]

Options:
  -g, --global           Install globally to ~/.gemini/config/plugins/plan-marshall (default)
  -w, --workspace        Install locally to <cwd>/.agents/plugins/plan-marshall
  -t, --target-dir PATH  Install to a custom directory
  -r, --ref REF          Branch or tag to install (default: dist-antigravity)
  -u, --uninstall        Remove the installed plugin
  -h, --help             Show this help message
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -g|--global)
      SCOPE="global"
      shift
      ;;
    -w|--workspace)
      SCOPE="workspace"
      shift
      ;;
    -t|--target-dir)
      if [ -z "${2:-}" ]; then
        echo "Error: --target-dir requires an argument" >&2
        exit 1
      fi
      TARGET_DIR="$2"
      shift 2
      ;;
    -r|--ref)
      if [ -z "${2:-}" ]; then
        echo "Error: --ref requires an argument" >&2
        exit 1
      fi
      REF="$2"
      shift 2
      ;;
    -u|--uninstall)
      UNINSTALL=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_help >&2
      exit 1
      ;;
  esac
done

if [ -z "$TARGET_DIR" ]; then
  if [ "$SCOPE" = "workspace" ]; then
    TARGET_DIR="${DEFAULT_WORKSPACE_DIR}"
  else
    TARGET_DIR="${DEFAULT_GLOBAL_DIR}"
  fi
fi

if [ "$UNINSTALL" = true ]; then
  if [ -d "$TARGET_DIR" ]; then
    echo "Uninstalling Plan Marshall Antigravity plugin from: $TARGET_DIR"
    rm -rf "$TARGET_DIR"
    echo "Uninstallation complete."
  else
    echo "No installation found at: $TARGET_DIR"
  fi
  exit 0
fi

# Detect whether running locally or remotely
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

CLEANUP_TMP=false
TMP_DIR=""

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/plugin.json" ] && [ -d "$SCRIPT_DIR/skills" ]; then
  SOURCE_DIR="$SCRIPT_DIR"
  echo "Installing Plan Marshall Antigravity plugin from local source: $SOURCE_DIR"
else
  TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'plan-marshall-antigravity')"
  CLEANUP_TMP=true
  trap 'if [ "$CLEANUP_TMP" = true ] && [ -d "$TMP_DIR" ]; then rm -rf "$TMP_DIR"; fi' EXIT

  if [[ "$REF" =~ ^v[0-9] ]]; then
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/tags/antigravity/${REF}.tar.gz"
  elif [[ "$REF" =~ ^antigravity/v ]]; then
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/tags/${REF}.tar.gz"
  else
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/heads/${REF}.tar.gz"
  fi

  echo "Downloading Plan Marshall (${REF}) from ${ARCHIVE_URL}..."
  curl -fsSL "$ARCHIVE_URL" | tar -xz -C "$TMP_DIR" --strip-components=1
  SOURCE_DIR="$TMP_DIR"
fi

if [ ! -f "$SOURCE_DIR/plugin.json" ]; then
  echo "Error: plugin.json not found in source directory ($SOURCE_DIR)." >&2
  exit 1
fi

echo "Installing plugin to: $TARGET_DIR"
PARENT_DIR="$(dirname "$TARGET_DIR")"
mkdir -p "$PARENT_DIR"

STAGE_DIR="${TARGET_DIR}.tmp.$$"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

cp "$SOURCE_DIR/plugin.json" "$STAGE_DIR/"
if [ -d "$SOURCE_DIR/skills" ]; then
  cp -R "$SOURCE_DIR/skills" "$STAGE_DIR/"
fi
if [ -d "$SOURCE_DIR/agents" ]; then
  cp -R "$SOURCE_DIR/agents" "$STAGE_DIR/"
fi
if [ -d "$SOURCE_DIR/commands" ]; then
  cp -R "$SOURCE_DIR/commands" "$STAGE_DIR/"
fi
if [ -f "$SOURCE_DIR/README.adoc" ]; then
  cp "$SOURCE_DIR/README.adoc" "$STAGE_DIR/"
fi
if [ -f "$SOURCE_DIR/install.sh" ]; then
  cp "$SOURCE_DIR/install.sh" "$STAGE_DIR/"
  chmod 0755 "$STAGE_DIR/install.sh"
fi

rm -rf "$TARGET_DIR"
mv "$STAGE_DIR" "$TARGET_DIR"

echo "Plan Marshall Antigravity plugin successfully installed at: $TARGET_DIR"
echo ""
echo "Antigravity automatically discovers installed plugins."
echo "You can verify the installation in Antigravity via Settings -> Plugins or in chat."
