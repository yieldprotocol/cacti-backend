<div align="center">
  <h1 align="center">🌵🌵🌵 Cacti 🌵🌵🌵 </h1>
  <h2 align="center"> <b>Cacti Backend</b> - <a href="https://github.com/yieldprotocol/cacti-frontend">Cacti Frontend</a></h2>
  <p align="center">
    Natural language interactions with web3.
    <br />
    <br />
    <a href="https://twitter.com/yield">Twitter</a>
    ·
    <a href="https://discord.gg/JAFfDj5">Discord</a>
    ·
    <a href="https://github.com/yieldprotocol/cacti-backend/issues">Report a Bug</a>
  </p>
</div>

<br />

![A screenshot of Cacti.](/screenshot.jpg)

## About

Cacti is a natural language interface for interacting with web3. It uses OpenAI function calling capability and a small but growing library of web3 interactions (called "widget commands") to enable chat based interactions.  

Cacti includes a frontend and backend repo. This is the backend. The frontend is [here](https://github.com/yieldprotocol/cacti-frontend).

The Cacti backend manages chat interactions with OpenAI, chat history, and user logins. 


## Running Locally

To develop locally, you need to run the frontend and backend, because
the dev and production deployments do not allow local URLs to interact
with them.

## Usage Guide
The usage guide for the Cacti chatbot is available [here](./usage_guide.md)

## To run the backend locally:
* Install [Docker](https://docs.docker.com/get-docker/)
* Requires Python 3.10 (DO NOT use higher versions as 'pysha3' dependency has issues with them)
* Run the docker containers - `docker compose -f ./docker/docker-compose.yml up -d`
* Run `docker ps` and check the status on both Postgres DB and Weaviate Vector DB to make sure they are running
* Copy and setup `.env` file in `./env` dir - `cp ./env/.env.example ./env/.env`
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
    - If no value has to be returned please specify an empty string '' for `return_value_description`
- Increment the numeric version in `WIDGET_INDEX_NAME` constant in `utils/constants.py`
- For local env, the widget index name would use your OS login name to create an isolated index. For dev/prod, the widget index would be the numeric version mentioned above. (more info in `scripts/check_update_widget_index.py`)
- Run this Python command to update your widget index with the new widget `python -m scripts.check_update_widget_index`
- Ensure textual translation for the display widget command is added to the `_widgetize_inner` function in `display_widget.py` file

## Contributing

See the [open issues](https://github.com/yieldprotocol/cacti-backend/issues) for a list of proposed features (and known issues).

