import logging.config
import os
import sys
from configparser import ConfigParser

from komtet_kassa_linux.libs import komtet_kassa


LEASE_STATION = None
DB_FILE = 'komtet_kassa_linux.db'

KOMTET_KASSA_API = 'https://kassa.komtet.ru/api/pos/v1'
LATEST_VERSION_URL = 'https://dist-kassa.komtet.ru/products/KOMTETKassaLinux4/latest.json'

SECRET_KEY = 'IjI2MjViNDkwYmFkNjAxZmY0NTVjZWQ5MmRlNGY5Yjk3ODgw'


CONFIG_FILE = 'settings.ini'
if os.path.exists(CONFIG_FILE):
    config_parser = ConfigParser()
    config_parser.read(CONFIG_FILE)
    if 'komtet_kassa_linux' in config_parser.sections():
        for key, value in config_parser['komtet_kassa_linux'].items():
            if hasattr(sys.modules[__name__], key.upper()):
                setattr(sys.modules[__name__], key.upper(), value)

    logging.config.fileConfig(config_parser)


if DB_FILE.startswith('~'):
    DB_FILE = os.path.join(os.path.expanduser('~'), DB_FILE[2:])
elif not DB_FILE.startswith('/'):
    DB_FILE = os.path.join(os.getcwd(), DB_FILE)


komtet_kassa.KOMTET_KASSA_API = KOMTET_KASSA_API
