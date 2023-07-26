__doc__ = """

Module for handling environment settings

Specify which environment to use via the ENV_TAG environment variable
e.g. ENV_TAG=dev ./start.sh
"""
from dotenv import load_dotenv
load_dotenv(dotenv_path="./env/.env")

import os
import logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_ENV_TAG = 'local'


def is_prod():
    return os.environ.get('ENV_TAG', DEFAULT_ENV_TAG) == 'prod'


def is_local():
    return os.environ.get('ENV_TAG', DEFAULT_ENV_TAG) == 'local'


def get_env():
    return os.environ.get('ENV_TAG', DEFAULT_ENV_TAG)
