import datetime
import decimal
import logging
import os
import shelve

from komtet_kassa_linux.devices import DeviceManager, Receipt, Shift
from komtet_kassa_linux.devices.kkt import KKT, INTERNET_SIGN
from komtet_kassa_linux.devices.receipt import Agent, Supplier
from komtet_kassa_linux.driver import ERROR_DENIED_IN_CLOSED_RECEIPT, Driver, DriverException
from komtet_kassa_linux.libs.komtet_kassa import POS


logger = logging.getLogger(__name__)


STORE_DIR = 'tmp/km_store/'
os.makedirs(STORE_DIR, exist_ok=True)


def to_decimal(value, rounding='.00'):
    return decimal.Decimal(value).quantize(decimal.Decimal(rounding))


class Store:

    def __init__(self, kkt_name):
        self._file_path = STORE_DIR + kkt_name

    def _open_shelve(self):
        return shelve.open(self._file_path)

    def get(self):
        with self._open_shelve() as s:
            return s.get('receipt')

    def save(self, value):
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
            logger.exception("Receipt didn't get")
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

    def create_receipt(self, task):
        receipt = Receipt(self._driver, task['intent'])
        if True: # utilsGetChequeVATIDLessOperatorNameAvailability
            utilsOperator = ''
            utilsOperatorVATID = ''
            if task['cashier']:
                utilsOperator = task['cashier']
            if task['cashier_inn'] and task['cashier_inn'] != '000000000184':
                utilsOperatorVATID = task['cashier_inn']
            receipt.set_cashier(utilsOperator, utilsOperatorVATID)
        else:
            if task['cashier'] and task['cashier_inn']:
                receipt.set_cashier(task['cashier'], task['cashier_inn'])
        if task.get('client'):
            receipt.set_client(task['client'].get('inn'), task['client'].get('name'))
        receipt.sno = task['sno']
        receipt.email = task.get('user')

        if 'correction' in task:
            receipt.set_correction_info(
                task['correction']['type'],
                task['correction']['description'],
                datetime.datetime.strptime(task['correction']['date'], "%Y-%m-%d"),
                task['correction']['document']
            )
        else:
            receipt.payment_address = task.get('payment_address')

        for position in task['positions']:
            agent = supplier = None
            if position.get('agent_info'):
                info = position['agent_info']
                agent = Agent(info['type'])
                if info.get('paying_agent'):
                    agent.set_paying_agent(info['paying_agent']['operation'],
                                           info['paying_agent']['phones'])
                if info.get('receive_payments_operator'):
                    agent.set_receive_payments_operator(
                        info['receive_payments_operator']['phones']
                    )
                if info.get('money_transfer_operator'):
                    agent.set_money_transfer_operator(
                        info['money_transfer_operator']['phones'],
                        info['money_transfer_operator']['name'],
                        info['money_transfer_operator']['address'],
                        info['money_transfer_operator']['inn']
                    )

            if position.get('supplier_info'):
                info = position['supplier_info']
                supplier = Supplier(info['phones'], info['name'], info['inn'])

            # Подсчет скидки на позицию
            discount = position.get(
                'discount',
                position['price'] * position['quantity'] - position['total']
            )
            position_discount = to_decimal(discount / position['quantity'] if discount else 0)

            quantity = position['quantity']
            price = float(decimal.Decimal(position['price']) - position_discount)
            total = float(decimal.Decimal(position['total']))

            # Выявление позиций с погрешностью в тотал
            has_extra_position = (total != price * quantity) and quantity > 1

            if has_extra_position:
                quantity -= 1

            position_info = dict(
                name=position['name'],
                vat=position['vat']['number'],
                measurement_unit=position.get('measure_name'),
                payment_method=position.get('calculation_method'),
                payment_object=position.get('calculation_subject'),
                agent=agent, supplier=supplier,
                nomenclature_code=position.get('nomenclature_code')
            )

            base_position_total = float(to_decimal(price * quantity))

            receipt.add_position(price=price, quantity=quantity, total=base_position_total,
                                 discount=discount, **position_info)

            if has_extra_position:
                price = total - base_position_total
                receipt.add_position(price=price, quantity=1, total=price, **position_info)

        for payment in task['payments']:
            receipt.add_payment(payment['sum'], payment['type'])

        return receipt

    def fiscalize_receipt(self, task):
        self._driver = Driver(self._device)
        try:
            self._kkt = KKT(self._driver)
            report = self.fiscalize_receipt_real(task)
        finally:
            self._driver.destroy()
        return report

    def fiscalize_receipt_real(self, task):
        report = {
            "id": task['id'],
            'inn': self._kkt.inn,
            "kkt_serial_number": self._kkt.serial_number,
            "kkt_reg_number": self._kkt.reg_number,
            "fiscal_drive_id": self._kkt.fiscal_drive_id,

            'ofd_url': self._kkt.ofd_url,

            'sno': str(task.get('sno')),
            'cashier': task.get('cashier'),
            'organisation': self._kkt.organisation,
            'organisation_address': self._kkt.organisation_address
        }

        if task.get('inn') != self._kkt.inn:
            logger.warning("Некорректный ИНН чека: %s. ИНН ККМ: %s",
                           task.get('inn'), self._kkt.inn)
            report['error_description'] = 'ИНН чека и ККМ не совпадают'
            return report

        is_only_internet_sign = self._kkt.mode_signs[INTERNET_SIGN] and sum(self._kkt.mode_signs.values()) == 1
        if is_only_internet_sign and not task.get('user'):
            logger.warning("В режиме Интернет необходимы email/телефон клиента")
            report['error_description'] = 'Отсутствует email/телефон клиента для режима Интернет'
            return report

        shift = Shift(self._driver, self._device['ID_SERIAL_SHORT'])
        shift.open()

        receipt = self.create_receipt(task)
        try:
            receipt.fiscalize(task.get('print'))
        except DriverException as exc:
            logger.info('Ошибка фискализации чека: %s', repr(exc))
            try:
                receipt.cansel()
            except DriverException as cansel_exc:
                if cansel_exc.error_code != ERROR_DENIED_IN_CLOSED_RECEIPT:  # Чек не закрыт
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
            "id": task['id'],
            'inn': task['inn'],
            "kkt_serial_number": self.printer.serial_number,
            "kkt_reg_number": '0000000000000001',
            "fiscal_drive_id": '0000000000000001',

            'ofd_url': "ofdp.platformaofd.ru",

            'sno': str(task.get('sno')),
            'cashier': task.get('cashier'),
            'organisation': task.get('org_name') or '',
            'organisation_address': task.get('org_address') or '',

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
