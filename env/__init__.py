__doc__ = """

Module for handling environment settings

Specify which environment to use via the ENV_TAG environment variable
e.g. ENV_TAG=dev ./start.sh

To add a new environment, simply cargo-cult an existing .yaml config file
within this directory and name it <ENV>.yaml.

"""

import os
import logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
import pathlib

import yaml


DEFAULT_ENV_TAG = 'dev'


def _load_env_file(env_file_path):
    log.info(f'Loading env file {env_file_path}')
    with open(env_file_path, 'r') as f:
        return yaml.safe_load(f)


def _get_env_file_path(env_tag):
    env_filename = f'{env_tag}.yaml'
    return pathlib.Path(__file__).parent / env_filename


env_config = _load_env_file(
    _get_env_file_path(os.environ.get('ENV_TAG', DEFAULT_ENV_TAG))
)
