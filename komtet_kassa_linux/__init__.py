import logging
import os.path
import threading

from komtet_kassa_linux.km_manager import run as run_manager
from komtet_kassa_linux.web import run as run_web


if True: # utilsGetLoggingAvailability
    logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


__version__ = os.environ.get('VERSION', 'undefined')


logger.info('Project version: %s', __version__)


def run():
    threading.Thread(target=run_web, daemon=True).start()
    run_manager()


if __name__ == '__main__':
    run()
