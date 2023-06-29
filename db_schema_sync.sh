#!/bin/bash

# This will ensure database schema is upgraded to the head revision
# for the specified ENV_TAG database
alembic upgrade head
