import env


def _get_weaviate_url(config):
    return f"{config.get('protocol', 'https')}://{config['user']}:{config['password']}@{config['host']}:{config['port']}"


def _get_postgres_url(config, database_name):
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{database_name}"


WEAVIATE_URL = _get_weaviate_url(env.env_config['weaviate'])
CHATDB_URL = _get_postgres_url(env.env_config['chatdb'], 'chatdb')
SCRAPEDB_URL = _get_postgres_url(env.env_config['scrapedb'], 'scrapedb')
