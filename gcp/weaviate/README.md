This folder contains artifacts for running Weaviate instances on GCP.

`weaviate-startup.sh`: Script that runs when a VM starts. Performs necessary setup and then launches a Weaviate instance. This should be kept in sync with gs://chatweb3/weaviate-startup.sh
`docker-compose.weaviate.yaml`: docker-compose file to launch Weaviate with. This should be kept in sync with gs://chatweb3/docker-compose.weaviate.sh

In order to launch a new VM for Weaviate, create a new VM from the instance template at https://console.cloud.google.com/compute/instanceTemplates/details/weaviate?project=chatweb3-380221

TODO: there is not a good way of seeding a new empty Weaviate instance. For now you can manually copy the entire Weaviate storage files (from /mnt/data/weaviate) from an existing running instance.
