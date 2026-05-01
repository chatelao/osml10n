#!/bin/bash
set -e

# Update and install system dependencies
# Using sudo if available (for local use), otherwise assuming we have permissions (for GH Actions)
SUDO=""
if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
fi

# Only update if we haven't done so recently (e.g. in the last hour) or if force updated
# In GH Actions, it's usually better to just run it once.
if [ ! -f /tmp/apt-updated ]; then
    $SUDO apt-get update || true
    touch /tmp/apt-updated
fi

$SUDO apt-get install -y --no-install-recommends \
    lua5.3 \
    liblua5.3-dev \
    lua-socket \
    libunac1-dev \
    python3-venv \
    libicu-dev \
    libpython3-dev \
    build-essential \
    libutf8proc-dev \
    pkg-config

# Build lua_unac
cd lua_unac
if [ ! -f unaccent.so ]; then
    make LUAV=5.3
fi
cd ..

# Set up Python virtual environment
if [ ! -d venv ]; then
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
fi
./venv/bin/pip install .

# Setup minimal data for testing
mkdir -p test/minimal_data/boundaries
for f in jp.geojson th.geojson mo.geojson hk.geojson tw.geojson; do
    if [ -f "osml10n/boundaries/$f" ]; then
        cp "osml10n/boundaries/$f" test/minimal_data/boundaries/
    fi
done
