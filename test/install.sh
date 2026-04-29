#!/bin/bash
set -e

# Update and install system dependencies
# Using sudo if available (for local use), otherwise assuming we have permissions (for GH Actions)
SUDO=""
if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
fi

$SUDO apt-get update
$SUDO apt-get install -y lua5.3 liblua5.3-dev lua-socket libunac1-dev python3-venv libicu-dev libpython3-dev build-essential libutf8proc-dev pkg-config

# Build lua_unac
cd lua_unac
make LUAV=5.3
cd ..

# Set up Python virtual environment
python3 -m venv venv
./venv/bin/pip install .

# Setup minimal data for testing
mkdir -p test/minimal_data/boundaries
cp osml10n/boundaries/jp.geojson test/minimal_data/boundaries/
cp osml10n/boundaries/th.geojson test/minimal_data/boundaries/
cp osml10n/boundaries/mo.geojson test/minimal_data/boundaries/
cp osml10n/boundaries/hk.geojson test/minimal_data/boundaries/
