#!/bin/bash
set -e

# Path to virtualenv
VENV_DIR="./venv"
ROOT_DIR=$(pwd)
PORT=8033

# Start the transcription daemon in the background
# Use minimal boundaries for testing
$VENV_DIR/bin/python transcription-daemon/geo-transcript-srv.py --geomdir test/minimal_data/boundaries --port $PORT &
DAEMON_PID=$!

# Ensure the daemon is killed on exit
trap 'kill $DAEMON_PID 2>/dev/null || true' EXIT

# Wait for the daemon to be ready
echo "Waiting for transcription daemon to start on port $PORT..."
MAX_RETRIES=30
COUNT=0
while ! lsof -i :$PORT >/dev/null 2>&1; do
    sleep 1
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "Error: Transcription daemon failed to start within $MAX_RETRIES seconds."
        exit 1
    fi
done
echo "Daemon is ready."

# Set up LUA_CPATH and LUA_PATH so Lua can find the modules
# unaccent.so is in lua_unac/
export LUA_CPATH="$ROOT_DIR/lua_unac/?.so;;"
# osml10n is in lua_osml10/
export LUA_PATH="$ROOT_DIR/lua_osml10/?.lua;$ROOT_DIR/lua_osml10/?/init.lua;;"

# Run the tests
cd lua_osml10/tests
lua5.3 runtests.lua
TEST_EXIT_CODE=$?
cd ../..

exit $TEST_EXIT_CODE
