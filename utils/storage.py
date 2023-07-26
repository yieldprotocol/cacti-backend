import env
import os

def _get_weaviate_url(config):
    return f"{config.get('protocol', 'https')}://{config['host']}:{config['port']}"


def _get_postgres_url(config, database_name):
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{database_name}"


WEAVIATE_URL = os.environ['WEAVIATE_URL']
CHATDB_URL = os.environ['CHATDB_URL']

# Scrape DB is optional
SCRAPEDB_URL = os.environ.get('SCRAPEDB_URL', None)
