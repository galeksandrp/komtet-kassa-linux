import logging

from komtet_kassa_linux import settings
from komtet_kassa_linux.km_manager.manager import KmManager


logger = logging.getLogger(__name__)


def run():
    logger.info('Start main loop')
    km_manager = KmManager(settings.DB_FILE, rent_station=settings.LEASE_STATION)
    try:
        km_manager.loop()
    except Exception:
        logger.exception('Error in main loop')
    else:
        logger.info('Stop main loop')


if __name__ == '__main__':
    run()
