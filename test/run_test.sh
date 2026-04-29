#!/bin/bash
set -e

# Path to virtualenv
VENV_DIR="./venv"
ROOT_DIR=$(pwd)

# Start the transcription daemon in the background
# Use minimal boundaries for testing
$VENV_DIR/bin/python transcription-daemon/geo-transcript-srv.py --geomdir test/minimal_data/boundaries &
DAEMON_PID=$!

# Ensure the daemon is killed on exit
trap 'kill $DAEMON_PID' EXIT

# Give it a moment to start
sleep 5

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
