# README

## Generate migration file

After making schema changes in the code via sqlalchemy, create a corresponding Alembic migration to manage the database schema:
`ENV_TAG=dev alembic revision --autogenerate -m "Add Bar table"`

This compares the actual database schema against the schema defined by the Sqlalchemy code, and produces the required operations to reconcile the diff. These operations are encapsulated within a migration file within `versions/`. Make sure the changes in the file look right before continuing.

Note that the `ENV_TAG` variable is used to identify which database's schema to compare to. For consistency, always use the `ENV_TAG=dev` database instance.

Alternatively, you can manually craft a migration file. Alembic has limitations around auto-generation, especially around sqlalchemy_utils functionality, which may require deep customization (e.g. see `render_item` in `env.py`).


## Run migration to update schema

Update the database schema with
`ENV_TAG=dev alembic upgrade head`

This will run all migrations from the database's current Alembic version up until the most recent one. If things are working as intended after the schema change, bring the prod instance up to parity:
`ENV_TAG=prod alembic upgrade head`


## Other

`b37b4d7dd234` is a special seeding migration, which brings the null schema up to the schema snapshot at the time of adding Alembic support.
