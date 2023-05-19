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
```
