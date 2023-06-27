# chatweb3-backend

To develop locally, you need to run the frontend and backend, because
the dev and production deployments do not allow local URLs to interact
with them.

To run the backend locally:
```
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt

cp env/local.example.yaml env/local.yaml
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
ENV_TAG=local alembic upgrade head
```

## Steps to add new widget command
- Update `widgets.txt` with the widget command details
- Bump up the widget index version in `INDEX_NAME` https://github.com/yieldprotocol/chatweb3-backend/blob/dev/index/widgets.py#L9
- Similarly, bump up the index version in `index_name`   https://github.com/yieldprotocol/chatweb3-backend/blob/dev/config.py#L6
- Run this Python command to update our Weaviate Vector DB with the new widget `python3 -c "from index import widgets; widgets.backfill()"`
- Add the widget's handler function in `replace_match()` https://github.com/yieldprotocol/chatweb3-backend/blob/dev/tools/index_widget.py#L189
