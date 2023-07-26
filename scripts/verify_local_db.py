import env
import utils.storage


def verify_local_db():
    # this is to avoid accidentally updating dev when the local config uses the dev db
    db_url = utils.CHATDB_URL
    assert 'localhost' in db_url or '127.0.0.1' in db_url, f'expecting localhost in db_url when using ENV_TAG=local with alembic, check env/local.yaml'


if __name__ == "__main__":
    if env.is_local():
        verify_local_db()
