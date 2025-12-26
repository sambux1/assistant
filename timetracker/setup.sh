#!/bin/bash
# setup.sh - install timestart and timestop commands to PATH
# Usage: ./setup.sh

set -e

# get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTART="${SCRIPT_DIR}/timestart"
TIMESTOP="${SCRIPT_DIR}/timestop"
TIMETRACK="${SCRIPT_DIR}/timetrack"

# use ~/.local/bin as the target directory (standard location, usually in PATH)
BIN_DIR="${HOME}/.local/bin"

# create bin directory if it doesn't exist
mkdir -p "$BIN_DIR"

# create symlinks
echo "Creating symlinks in ${BIN_DIR}..."
ln -sf "$TIMESTART" "${BIN_DIR}/timestart"
ln -sf "$TIMESTOP" "${BIN_DIR}/timestop"
ln -sf "$TIMETRACK" "${BIN_DIR}/timetrack"

echo "✓ symlinks created"
echo "Setup complete! You can now use 'timestart', 'timestop', and 'timetrack' commands."
echo "Try it out:"
echo "  timestart work my-project"
echo "  timestop"
echo "  timetrack [day|week|month|year]"
