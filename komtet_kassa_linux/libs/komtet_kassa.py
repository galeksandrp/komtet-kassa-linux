import logging

import requests

import komtet_kassa_linux
from komtet_kassa_linux.libs.helpers import get_signature, json_encode


KOMTET_KASSA_API = 'https://kassa.komtet.ru/api/pos/v1'


logger = logging.getLogger(__name__)


class POS:

    def __init__(self, key, secret, secret_salt=None):
        self.key = key
        self.secret = secret
        self.secret_salt = secret_salt

    def _generate_signature(self, method, url, data, use_secret_salt=True):
        if use_secret_salt:
            secret = self.secret + self.secret_salt
        else:
            secret = self.secret
        data = data or ''
        return get_signature(secret, method + url + data)

    def _request(self, url, data=None, use_secret_salt=True):
        url = KOMTET_KASSA_API + url
        data = data and json_encode(data)
        headers = {
            'Authorization': self.key,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-HMAC-Signature': self._generate_signature('POST', url, data, use_secret_salt)
        }

        response = requests.post(url, headers=headers, data=data, timeout=60)
        logger.debug('Sent request to KomtetKassa >>> %s [%s]: %s', url, headers, data)
        response.raise_for_status()
        response = response and response.text and response.json()
        logger.debug('Got response from KomtetKassa <<< %s', response)

        return response

    def activate(self, hardware_id, rent_station=None):
        return self._request('/pos/activate', {
            'hwid': hardware_id,
            'rent_station': rent_station
        }, use_secret_salt=False)

    def deactivate(self):
        return self._request('/pos/deactivate', use_secret_salt=False)

    def get_task(self, printer_report=None, check_report=None, limit=1):
        response = self._request('/tasks?limit=%s' % limit, {
            'printer': printer_report,
            'check': check_report,
            'version': 'linux-' + komtet_kassa_linux.__version__
        })
        checks = response and response.get('checks')
        return checks and checks[0] or None

    def send_report(self, check_report):
        return self.get_task(check_report=check_report, limit=0)
