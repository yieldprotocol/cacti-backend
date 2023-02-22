#!/bin/bash

# Run this via ./database/dbinit.sh

source ../venv/bin/activate
python3 -c "from database.models import engine, Base; Base.metadata.create_all(bind=engine)"
