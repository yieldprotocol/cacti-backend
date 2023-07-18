# README

## Generate migration file

After making schema changes in the code via sqlalchemy, create a corresponding Alembic migration to manage the database schema:
`ENV_TAG=dev alembic revision --autogenerate -m "Add Bar table"`

This compares the actual database schema against the schema defined by the Sqlalchemy code, and produces the required operations to reconcile the diff. These operations are encapsulated within a migration file within `versions/`. Make sure the changes in the file look right before continuing.

Note that the `ENV_TAG` variable is used to identify which database's schema to compare to. For consistency, always use the `ENV_TAG=dev` database instance.

Alternatively, you can manually craft a migration file. Alembic has limitations around auto-generation, especially around sqlalchemy_utils functionality, which may require deep customization (e.g. see `render_item` in `env.py`).

## Test migrations locally

Update `env/local.yaml` to run the database container. Make sure you change the dev database url to point localhost. Then start running it with `docker-compose up`.

Bring your local schema up-to-date with `ENV_TAG=local ./db_schema_sync.sh`, and test your new schema changes.

## Create PR with your proposed changes

Once the PR is approved, you may merge the PR into dev. Merging will trigger a GitHub Actions workflow that will apply the
migration to the dev database. (Likewise, when merged with master, the prod database will be updated).

## Manual migration

In general, you should not need to run these manually, as they are handled by GitHub Actions when `dev` and `master` branches are updated. But if necessary, here are the steps:

For dev:
`ENV_TAG=dev ./db_schema_sync.sh`

For prod:
`ENV_TAG=prod ./db_schema_sync.sh`


## Other

`b37b4d7dd234` is a special seeding migration, which brings the null schema up to the schema snapshot at the time of adding Alembic support.
