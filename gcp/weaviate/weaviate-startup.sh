#! /bin/bash

# Script that the Weaviate GCP VM's will run upon launch.
# Updates here should be uploaded to cloud storage:
#   gcloud storage cp weaviate-startup.sh gs://chatweb3/weaviate-startup.sh
#
# In order for these changes to be picked up, reset the Weaviate GCP VM's
# (e.g. weaviate-dev, weaviate-prod)

apt -y update
apt -y install docker.io
apt -y install docker-compose
gcloud storage cp gs://chatweb3/docker-compose.weaviate.yaml ./docker-compose.yaml

# Temp solution to set API key using env vars as it's straightforward. Recommended solution is to use secrets manager which requires further investigation.
echo "export AUTHENTICATION_APIKEY_ALLOWED_KEYS=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/AUTHENTICATION_APIKEY_ALLOWED_KEYS)" >> ~/.bashrc
source ~/.bashrc

docker-compose down
docker-compose up -d
