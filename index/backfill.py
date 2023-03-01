import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

from . import app_info
from . import sites
from . import widgets


def backfill_all():
    """Backfill the various weaviate indexes. Add new indexes here!

    This is called from the top-level backfill_index.sh script.

    """
    log.info('Backfilling app_info')
    app_info.backfill()

    log.info('Backfilling sites')
    sites.backfill()

    log.info('Backfilling widgets')
    widgets.backfill()
