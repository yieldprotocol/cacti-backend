# chatweb3-backend

To develop locally, you need to run the frontend and backend, because
the dev and production deployments do not allow local URLs to interact
with them.

## To run the backend locally:
* Install [Docker](https://docs.docker.com/get-docker/)
* Install Python 3.10 or higher
* Run the docker containers - `docker compose -f ./docker/docker-compose.yml up -d`
* Copy env file - `cp ./env/.env.example ./env/.env`
* Set your own credentials for the services defined in the `./env/.env` file
* Setup Python virtualenv - `python3 -m venv ../venv`
* Activate virtualenv - `source ../venv/bin/activate`
* Install dependencies - `pip install -r requirements.txt`
* Populate vector index with widgets - `python -m scripts.check_update_widget_index`
* Populate vector index with app info - `python -c "from index import app_info; app_info.backfill()"`
* Run DB migrations - `./db_schema_sync.sh`
* Run server - `./start.sh`

## To add a new env var/secret:
* Update `./env/.env.example` and `./env/.env` files
* Update `cloudbuild.yaml` file for GCP deployment

## Steps to add new widget command
- Update `widgets.yaml` with the widget command details
- Increment the numeric version in `WIDGET_INDEX_NAME` constant in `utils/constants.py`
- For local env, the widget index name would use your OS login name to create an isolated index. For dev/prod, the widget index would be the numeric version mentioned above. (more info in `scripts/check_update_widget_index.py`)
- Run this Python command to update your widget index with the new widget `python -m scripts.check_update_widget_index`
- Ensure textual translation for the display widget command is added to the `_widgetize_inner` function in `display_widget.py` file

