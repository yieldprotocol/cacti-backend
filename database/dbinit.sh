#!/bin/bash

# Run this via ENV_TAG=<env> ./database/dbinit.sh
# where <env> is one of the environments defined within env/
# (e.g. dev, prod)

source ../venv/bin/activate
python3 -c "from database.models import engine, Base; Base.metadata.create_all(bind=engine)"
