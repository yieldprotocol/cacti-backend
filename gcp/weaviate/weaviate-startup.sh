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
docker-compose up -d
