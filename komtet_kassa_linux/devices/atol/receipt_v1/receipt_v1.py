from time import sleep

from .. import constants as c
from komtet_kassa_linux.devices.atol.receipt import set_params, Receipt
from komtet_kassa_linux.devices.atol.receipt import FFD_1_05, FFD_1_20, STATES_KM_FOR_MEASURABLE_POSITION
from komtet_kassa_linux.devices.atol.driver import IFptr
from komtet_kassa_linux.libs.helpers import get_mark_code
from komtet_kassa_linux.libs import version_helper

from ..receipt import KKM_MARKING_PROCESSING_MODE


class ReceiptV1(Receipt):
    '''
        Класс выполнения команд к драйверу Атол(чек v1 структуры)
    '''

    def __init__(self, driver, ffd_version):
        super().__init__(driver, ffd_version)
        self.params = {}
        self.positions = []
        self.payments = []
        self.cashless_payments = []
        self.cashier = {}

    @property
    def sno(self):
        return self.params[1055]

    @sno.setter
    def sno(self, val):
        self.params[1055] = c.SNO_MAP[val]

    @property
    def email(self):
        return self.params[1008]

    @email.setter
    def email(self, val):
        self.params[1008] = val

    @property
    def internet(self):
        return self.params[1125]

    @internet.setter
    def internet(self, val):
        self.params[1125] = val

    @property
    def payment_address(self):
        return self.params.get(1187)

    @payment_address.setter
    def payment_address(self, val):
        self.params[1187] = val

    def set_cashier(self, name, inn):
        self.cashier[1021] = name
        self.cashier[1203] = inn

    def set_client(self, inn=None, name=None):
        '''
            Добавление сведений о покупателе(клиенте).
            Поддерживаемые версии ФФД 1.2, 1.05
        '''
        if version_helper.greater_or_equal(self.ffd_version, FFD_1_20):
            if name and inn:
                self.params[1256] = {
                    1227: name,
                    1228: inn
                }
        elif version_helper.greater_or_equal(self.ffd_version, FFD_1_05):
            self.params[1228] = inn
            self.params[1227] = name

    def set_intent(self, intent):
        self.intent = c.RECEIPT_TYPE_MAP[intent]
        self.params[IFptr.LIBFPTR_PARAM_RECEIPT_TYPE] = c.RECEIPT_TYPE_MAP[intent]

    def set_additional_user_props(self, name=None, value=None):
        ''' Добавление дополнительного реквизита пользователя '''
        self.params[1084] = {
            1085: name,
            1086: value
        }

    def set_additional_check_props(self, value=None):
        ''' Добавление дополнительного реквизита чека '''
        self.params[1192] = value

    def set_correction_info(self, type, date, document=None):
        ''' Добавление сведений для чека коррекции '''
        self.params[1173] = c.CORRECTION_RECEIPT_BASIS_MAP[type]

        if document:
            self.params[1174] = {
                1178: date,
                1179: document
            }
        else:
            self.params[1174] = {
                1178: date
            }

    def add_position(self, name, price, quantity, total, vat, measurement_unit=None,
                     payment_method=None, payment_object=None, agent=None, supplier=None,
                     discount=0.0, nomenclature_code=None, excise=None, country_code=None,
                     declaration_number=None, **kw):
        ''' Добавление параметров для регистрации позиции '''
        params = {
            IFptr.LIBFPTR_PARAM_COMMODITY_NAME: name,
            IFptr.LIBFPTR_PARAM_PRICE: price,
            IFptr.LIBFPTR_PARAM_QUANTITY: quantity,
            IFptr.LIBFPTR_PARAM_TAX_TYPE: c.TAX_MAP[vat],
            IFptr.LIBFPTR_PARAM_POSITION_SUM: total,
            IFptr.LIBFPTR_PARAM_INFO_DISCOUNT_SUM: discount
        }

        if kw.get('user_data'):
            params[1191] = kw['user_data']

        if measurement_unit:
            if version_helper.greater_or_equal(self.ffd_version, FFD_1_20):
                params[2108] = c.MEASURE_MAP_V1.get(
                    measurement_unit.lower(),  IFptr.LIBFPTR_IU_PIECE
                )
            elif version_helper.greater_or_equal(self.ffd_version, FFD_1_05):
                params[1197] = measurement_unit

        if payment_method:
            params[1214] = c.PAYMENT_METHOD_MAP[payment_method]

        if payment_object:
            params[1212] = c.PAYMENT_OBJECT_MAP[payment_object]

        if country_code:
            params[1230] = country_code

        if declaration_number:
            params[1231] = declaration_number

        if excise:
            params[1229] = excise

        if agent:
            params.update(dict(agent))

        if supplier:
            params.update(dict(supplier))

        if nomenclature_code:
            if version_helper.greater_or_equal(self.ffd_version, FFD_1_20):
                mark_code = get_mark_code(nomenclature_code['code_restored'])
                is_verified, planing_marking_status = self.verify_mark_code(
                    mark_code=mark_code,
                    measure_name=measurement_unit
                )

                if not is_verified:
                    raise Exception('Ошибка проверки КМ')

                params.update({
                    IFptr.LIBFPTR_PARAM_MARKING_CODE_TYPE: IFptr.LIBFPTR_MCT12_AUTO,
                    IFptr.LIBFPTR_PARAM_MARKING_CODE: mark_code,
                    IFptr.LIBFPTR_PARAM_MARKING_CODE_STATUS: planing_marking_status,
                    IFptr.LIBFPTR_PARAM_MARKING_PROCESSING_MODE: KKM_MARKING_PROCESSING_MODE
                })

                if planing_marking_status in STATES_KM_FOR_MEASURABLE_POSITION:
                    params.update({
                        IFptr.LIBFPTR_PARAM_QUANTITY: float(quantity),
                        IFptr.LIBFPTR_PARAM_MEASUREMENT_UNIT: measurement_unit
                    })

            elif version_helper.greater_or_equal(self.ffd_version, FFD_1_05):
                params[1162] = bytearray.fromhex(nomenclature_code['hex_code'])

        self.positions.append(params)

    def add_payment(self, sum, type=None):
        self.payments.append({
            IFptr.LIBFPTR_PARAM_PAYMENT_TYPE: c.PAYMENT_MAP.get(type,
                                                                IFptr.LIBFPTR_PT_ELECTRONICALLY),
            IFptr.LIBFPTR_PARAM_PAYMENT_SUM: sum
        })

    def add_cashless_payment(self, _sum, method, _id, additional_info=None):
        if additional_info:
            self.cashless_payments.append(
                {
                    IFptr.LIBFPTR_PARAM_PAYMENT_SUM: _sum,
                    IFptr.LIBFPTR_PARAM_ELECTRONICALLY_PAYMENT_METHOD: method,
                    IFptr.LIBFPTR_PARAM_ELECTRONICALLY_ID: _id,
                    IFptr.LIBFPTR_PARAM_ELECTRONICALLY_ADD_INFO: additional_info
                }
            )
        else:
            self.cashless_payments.append(
                {
                    IFptr.LIBFPTR_PARAM_PAYMENT_SUM: _sum,
                    IFptr.LIBFPTR_PARAM_ELECTRONICALLY_PAYMENT_METHOD: method,
                    IFptr.LIBFPTR_PARAM_ELECTRONICALLY_ID: _id
                }
            )

    def fiscalize(self, is_print=True):
        '''
            Фискализация чека

            Примечание: последовательность выполнения команд имеет значение
        '''
        with self._driver.query() as fptr:
            if self.cashier:
                set_params(fptr, self.cashier)
                if fptr.operatorLogin():
                    raise self._driver.exception('Ошибка регистрации кассира')

            set_params(fptr, self.params)
            fptr.setParam(IFptr.LIBFPTR_PARAM_RECEIPT_ELECTRONICALLY, not is_print)

            if fptr.openReceipt():
                raise self._driver.exception('Ошибка открытия чека')

            for position in self.positions:
                set_params(fptr, position)
                if fptr.registration():
                    raise self._driver.exception('Ошибка регистрации позиции')

            fptr.setParam(
                IFptr.LIBFPTR_PARAM_SUM,
                sum(map(lambda p: p[IFptr.LIBFPTR_PARAM_PAYMENT_SUM], self.payments), 0)
            )
            if fptr.receiptTotal():
                raise self._driver.exception('Ошибка регистрации итога')

            for payment in self.payments:
                set_params(fptr, payment)
                if fptr.payment():
                    raise self._driver.exception('Ошибка регистрации платежа')

            for cashless_payment in self.cashless_payments:
                fptr.setParam(
                    IFptr.LIBFPTR_PARAM_PAYMENT_TYPE,
                    IFptr.LIBFPTR_PT_ADD_INFO
                )

                set_params(fptr, cashless_payment)

                if fptr.payment():
                    raise self._driver.exception('Ошибка регистрации сведений об оплате безналичными')

            # Перед закрытием проверяем, что все КМ отправились
            while True:
                fptr.checkMarkingCodeValidationsReady()
                if fptr.getParamBool(IFptr.LIBFPTR_PARAM_MARKING_CODE_VALIDATION_READY):
                    break
                sleep(1)

            if fptr.closeReceipt():
                pass
            elif fptr.checkDocumentClosed():
                raise self._driver.exception(
                    'Ошибка проверки состояния документа при закрытии чека'
                )
            elif not fptr.getParamBool(IFptr.LIBFPTR_PARAM_DOCUMENT_CLOSED):
                raise self._driver.exception('Документ не закрылся при закрытии чека')
