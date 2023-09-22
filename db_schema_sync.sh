#!/bin/bash

set -euxf -o pipefail

# This will assert if we run this on local but are pointed to dev db
python3 -m scripts.verify_local_db

# This will ensure database schema is upgraded to the head revision
# for the specified ENV_TAG database
alembic upgrade head
