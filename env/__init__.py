import os
import logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
import pathlib

import yaml


DEFAULT_ENV_FILENAME = 'legacy_env.yaml'


def _load_env_file(env_file_path):
    log.info(f'Loading env file {env_file_path}')
    with open(env_file_path, 'r') as f:
        return yaml.safe_load(f)


env_config = _load_env_file(
    pathlib.Path(__file__).parent /
    os.environ.get('ENV_FILENAME', DEFAULT_ENV_FILENAME)
)
