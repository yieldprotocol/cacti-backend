#!/bin/bash

# top-level helper script to backfill the weaviate indexes

source ../venv/bin/activate
python3 -c "from index import backfill; backfill.backfill_all()"
