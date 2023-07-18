import enum
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
import sqlalchemy_utils

from alembic import context

import env
import utils.storage

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
import database.models
target_metadata = database.models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# set database based on environment
def _set_db_url():
    db_url = utils.storage.CHATDB_URL
    if env.is_local():
        # this is to avoid accidentally updating dev when the local config uses the dev db
        assert 'localhost' in db_url or '127.0.0.1' in db_url, f'expecting localhost in db_url when using ENV_TAG=local with alembic, check env/local.yaml'
    config.set_main_option('sqlalchemy.url', db_url)

_set_db_url()


# https://stackoverflow.com/questions/30132370/trouble-when-using-alembic-with-sqlalchemy-utils
def render_item(type_, obj, autogen_context):
    """Apply custom rendering for selected items.

    alembic does not work with sqlalchemy_utils (e.g. ChoiceType), so
    add custom handling for these types.

    """

    if isinstance(obj, sqlalchemy_utils.ChoiceType):
        choices_enum = obj.choices
        impl = obj.impl
        assert isinstance(choices_enum, enum.EnumMeta), f'add custom support for non-Enum ChoiceType {type(choices_enum)}'
        autogen_context.imports.add(f'import {choices_enum.__module__}')

        choices_str = f'{choices_enum.__module__}.{choices_enum.__qualname__}'
        if impl is None:
            impl_str = 'None'
        else:
            # sqlalchemy is imported as sa, see script.py.mako
            impl_str = f'sa.{repr(impl)}'

        return f'sqlalchemy_utils.ChoiceType({choices_str}, impl={impl_str})'

    # default rendering for other objects
    return False


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
