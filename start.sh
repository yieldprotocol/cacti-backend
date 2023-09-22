#!/bin/bash

# Check the current alembic revision, and see if it matches the head revision.
if [[ -z "${SKIP_DB_CHECK}" ]]
then
    echo "Checking current database revision..."
    alembic check || { echo "WARNING: Database schema not in sync. Run \"git pull\" to pick up any migrations that got deployed, or run \"ENV_TAG=local ./db_schema_sync.sh\" to update your local database of pending mgirations, or prepend SKIP_DB_CHECK=1 to your command to ignore this warning."; exit 1; }
fi

xvfb_cmd=xvfb-run
start_cmd="uvicorn main:app --host 0.0.0.0 --port 9999"

if [[ $(type -P "$xvfb_cmd") ]]
then
    $xvfb_cmd $start_cmd
else
    $start_cmd
fi
