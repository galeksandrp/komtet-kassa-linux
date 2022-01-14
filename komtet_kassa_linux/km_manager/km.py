import datetime
import decimal
import logging
import os
import shelve

from komtet_kassa_linux.devices.atol import DeviceManager
from komtet_kassa_linux.devices.atol.shift import Shift
from komtet_kassa_linux.devices.atol.receipt import FFD_1_20
from komtet_kassa_linux.devices.atol.receipt_v1 import receipt_v1_factory
from komtet_kassa_linux.devices.atol.receipt_v2 import receipt_v2_factory
from komtet_kassa_linux.devices.atol.kkt import KKT, INTERNET_SIGN
from komtet_kassa_linux.driver import IFptr
from komtet_kassa_linux.driver import ERROR_DENIED_IN_CLOSED_RECEIPT, Driver, DriverException
from komtet_kassa_linux.libs.komtet_kassa import POS


logger = logging.getLogger(__name__)


STORE_DIR = 'tmp/km_store/'
os.makedirs(STORE_DIR, exist_ok=True)


class Store:

    def __init__(self, kkt_name):
        self._file_path = STORE_DIR + kkt_name
        if True: # getStoreDictAvailability
            self.utilsDictionary = dict()

    def _open_shelve(self):
        return shelve.open(self._file_path)

    def get(self):
        if True: # getStoreDictAvailability
            return self.utilsDictionary.get('receipt')
        else:
            with self._open_shelve() as s:
                return s.get('receipt')

    def save(self, value):
        if True: # getStoreDictAvailability
            self.utilsDictionary['receipt'] = value
        else:
            with self._open_shelve() as s:
                s['receipt'] = value


class BaseKM:

    def __init__(self, printer, rent_station=None):
        self.printer = printer
        self.rent_station = rent_station
        self.pos = POS(printer.pos_key, printer.pos_secret, printer.serial_number)
        self.store = Store(printer.serial_number)

    def get_device_info(self):
        raise NotImplementedError

    def fiscalize_receipt(self, task):
        raise NotImplementedError

    def beat(self, is_only_send_report=False):
        if not self.printer.is_virtual:
            # TODO: вынести в AtolKM
            Shift(self._driver, self.printer.serial_number).autocheck()

        device_info = self.get_device_info()
        fiscal_data = None
        if 'error_description' not in device_info:
            receipt = self.store.get()
            if receipt:
                fiscal_data = (receipt.get('__fiscal_data__') or
                               self.fiscalize_receipt(receipt))

        try:
            if is_only_send_report:
                receipt = self.pos.send_report(fiscal_data)
            else:
                receipt = self.pos.get_task(device_info, fiscal_data)
        except AssertionError:
            raise
        except Exception:
            if fiscal_data:
                receipt['__fiscal_data__'] = fiscal_data
            logger.exception('Receipt didn\'t get')
        else:
            return bool(receipt)
        finally:
            self.store.save(receipt)


class KM(BaseKM):

    _device = None
    _driver = None
    _kkt = None
    utilsDeviceInfo = None

    def __init__(self, printer, rent_station=None):
        super().__init__(printer, rent_station)
        self._device = device = DeviceManager().get(printer.serial_number)
        if False: # utilsGetOpenCloseDeviceOnReceiptAvailability
            self._driver = driver = Driver(device)
            self._kkt = KKT(driver)

    def __del__(self):
        self._driver.destroy()

    def get_device_info(self):
        if self.utilsDeviceInfo is None:
            self._driver = Driver(self._device)
            try:
                self._kkt = KKT(self._driver)
                self.utilsDeviceInfo = self.get_device_info_real()
            finally:
                self._driver.destroy()

        self.utilsDeviceInfo.update({'rent_station': self.rent_station})
        return self.utilsDeviceInfo

    def get_device_info_real(self):
        try:
            info = self._kkt.get_info()
        except DriverException as exc:
            info = {
                'serial_number': self._kkt.serial_number,
                'error_description': str(exc)
            }

        info.update({'rent_station': self.rent_station})
        return info

    def fiscalize_receipt(self, task):
        self._driver = Driver(self._device)
        try:
            self._kkt = KKT(self._driver)
            self.utilsDeviceInfo = self.get_device_info_real()
            report = self.fiscalize_receipt_real(task)
        finally:
            self._driver.destroy()
        return report

    def fiscalize_receipt_real(self, task):
        report = dict(
            id=task['id'],
            inn=self._kkt.inn,
            kkt_serial_number=self._kkt.serial_number,
            kkt_reg_number=self._kkt.reg_number,
            fiscal_drive_id=self._kkt.fiscal_drive_id,
            ofd_url=self._kkt.ofd_url,
            organisation=self._kkt.organisation,
            organisation_address=self._kkt.organisation_address
        )

        if task['version'] == 'v1':
            report.update(dict(
                sno=str(task.get('sno')),
                cashier=task.get('cashier'),
                cashier_inn=task.get('cashier_inn'),
            ))
        elif task['version'] == 'v2':
            report.update(dict(
                sno=str(task['company']['sno']),
                cashier=task['cashier']['name'],
                cashier_inn=task['cashier']['inn'],
            ))

        ffd_version = self._kkt.ffd_version
        check_inn = task.get('inn',
                             task['company']['inn'] if task.get('company') else None)
        if check_inn != self._kkt.inn:
            logger.warning(f"Некорректный ИНН чека: {check_inn}. ИНН ККМ: {self._kkt.inn}")
            report['error_description'] = 'ИНН чека и ККМ не совпадают'
            return report

        is_only_internet_sign = (
            self._kkt.mode_signs[INTERNET_SIGN] and sum(self._kkt.mode_signs.values()) == 1
        )
        client = task.get('user',
                          task.get('client').get('email', task.get('client').get('phone'))
                          if task.get('client') else None)
        if is_only_internet_sign and not client:
            logger.warning('В режиме Интернет обязательно необходимы email(телефон) клиента')
            report['error_description'] = 'Отсутствует email(телефон) клиента для режима Интернет'
            return report

        shift = Shift(self._driver, self._device['SERIAL_NUMBER'])
        shift.open()

        if task['version'] == 'v1':
            try:
                receipt = receipt_v1_factory(self._driver, ffd_version, task)
            except Exception as exc:
                report['error_description'] = str(exc)
                return report

        elif task['version'] == 'v2':
            try:
                receipt = receipt_v2_factory(self._driver, ffd_version, task)
            except Exception as exc:
                report['error_description'] = str(exc)
                return report

        try:
            if True: # getATOLCallbackURLPhysicalChequeAvailability
                if task.get('atol_callback_url'):
                    receipt.fiscalize(True)
                else:
                    receipt.fiscalize(task.get('print'))
            else:
                receipt.fiscalize(task.get('print'))
        except DriverException as exc:
            logger.info(f'Ошибка фискализации чека: {repr(exc)}')
            try:
                receipt.cancel()
            except DriverException as cancel_exc:
                if cancel_exc.error_code != ERROR_DENIED_IN_CLOSED_RECEIPT:  # Чек не закрыт
                    raise exc
            finally:
                report['error_description'] = str(exc)

        report.update(self._kkt.last_receipt)
        report.update(self._kkt.shift_info)
        return report


class VirtualKM(BaseKM):

    def get_device_info(self):
        return {
            'serial_number': self.printer.serial_number,
            'rent_station': self.rent_station,
            'fiscal_id': '0000000000000001',
            'reg_till': datetime.date.today() + datetime.timedelta(days=10),
            'fn_state': 0
        }

    def fiscalize_receipt(self, task):
        return {
            'id': task['id'],
            'inn': (task['company']['inn']
                    if task['version'] == 'v2'
                    else task['inn']),
            'kkt_serial_number': self.printer.serial_number,
            'kkt_reg_number': '0000000000000001',
            'fiscal_drive_id': '0000000000000001',

            'ofd_url': 'ofdp.platformaofd.ru',

            'sno': (str(task['company']['sno'])
                    if task['version'] == 'v2'
                    else str(task.get('sno'))),
            'cashier': (task['cashier']['name']
                        if task['version'] == 'v2'
                        else task.get('cashier')),
            'organisation': (task['company']['name']
                             if task['version'] == 'v2'
                             else task.get('org_name') or ''),
            'organisation_address': (task['company']['place_address']
                                     if task['version'] == 'v2'
                                     else task.get('org_address') or ''),
            'fiscal_document_number': '1',
            'sum': sum([payment['sum'] for payment in task.get("payments")]),
            'fiscal_id': '0000000001',
            'time': datetime.datetime.now(),
            'session_check': '1',
            'session': '1'
        }


def factory_km(printer, rent_station=None):
    if printer.is_virtual:
        return VirtualKM(printer, rent_station=rent_station)

    return KM(printer, rent_station=rent_station)
