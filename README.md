<div align="center">
  <h1 align="center">🌵🌵🌵 Cacti 🌵🌵🌵 </h1>
  <h2 align="center"> <b>Cacti Backend</b>b> - <a href="https://github.com/yieldprotocol/cacti-frontend">Cacti Frontend</a></h2>
  <p align="center">
    Natural language interactions with web3.
    <br />
    <br />
    <a href="https://twitter.com/yield">Twitter</a>
    ·
    <a href="https://discord.gg/JAFfDj5">Try Online</a>
    ·
    <a href="https://github.com/yieldprotocol/cacti-backend/issues">Report a Bug</a>
  </p>
</div>

<br />

![A screenshot of Cacti.](/public/screenshot.jpg)

## About

Cacti is a natural language interface for interacting with web3. It uses OpenAI function calling capability and a small but growing library of web3 interactions (called "widget commands") to enable chat based interactions.  

Cacti includes a frontend and backend repo. This is the backend. The frontend is [here](https://github.com/yieldprotocol/cacti-frontend).

The Cacti backend manages chat interactions with OpenAI, chat history, and user logins. 


## Running Locally

To develop locally, you need to run the frontend and backend, because
the dev and production deployments do not allow local URLs to interact
with them.

To run the backend locally:
```
cp env/local.example.yaml env/local.yaml
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt

python -m scripts.check_update_widget_index
ENV_TAG=local ./start.sh
```

This connects to the dev database by default. If you are planning to make
database changes, consider running a local instance of the postgres database,
and modifying env/local.yaml to connect to that database instead. Same if
you are modifying weaviate schema.
```
cd docker
docker-compose up
# ensure schema is created/up-to-date
ENV_TAG=local ./db_schema_sync.sh
```

## Steps to add new widget command
- Update `widgets.yaml` with the widget command details
- Increment the numeric version in `WIDGET_INDEX_NAME` constant in `utils/constants.py`
- For local env, the widget index name would use your OS login name to create an isolated index. For dev/prod, the widget index would be the numeric version mentioned above. (more info in `scripts/check_update_widget_index.py`)
- Run this Python command to update your widget index with the new widget `python -m scripts.check_update_widget_index`
- Ensure textual translation for the display widget command is added to the `_widgetize_inner` function in `display_widget.py` file

## Contributing

See the [open issues](https://github.com/yieldprotocol/cacti-backend/issues) for a list of proposed features (and known issues).
