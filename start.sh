#!/bin/bash

# Check the current alembic revision, and see if it matches the head revision.
if [[ -z "${SKIP_DB_CHECK}" ]]
then
    echo "Checking current database revision..."
    alembic current | grep head || { echo "WARNING: Database schema not in sync. Run \"ENV_TAG=$ENV_TAG ./db_schema_sync.sh\" to update the $ENV_TAG database, or prepend SKIP_DB_CHECK=1 to your command to ignore this warning."; exit 1; }
fi

xvfb_cmd=xvfb-run
start_cmd="uvicorn main:app --host 0.0.0.0 --port 9999"

if [[ $(type -P "$xvfb_cmd") ]]
then
    $xvfb_cmd $start_cmd
else
    $start_cmd
fi
