from time import sleep

from .. import constants as c
from komtet_kassa_linux.devices.atol.receipt import set_params, Receipt
from komtet_kassa_linux.devices.atol.receipt import FFD_1_05, FFD_1_20, STATES_KM_FOR_MEASURABLE_POSITION
from komtet_kassa_linux.devices.atol.driver import IFptr
from komtet_kassa_linux.libs.helpers import get_mark_code, prepare_dict
from komtet_kassa_linux.libs import version_helper

from ..receipt import KKM_MARKING_PROCESSING_MODE


class ReceiptV2(Receipt):
    '''
        Класс выполнения команд к драйверу Атол(чек v2 структуры)
    '''
    def __init__(self, driver, ffd_version):
        super().__init__(driver, ffd_version)
        self.params = {}
        self.positions = []
        self.payments = []
        self.cashier = {}

    @property
    def sno(self):
        return self.params[1055]

    @sno.setter
    def sno(self, val):
        self.params[1055] = c.SNO_MAP[val]

    @property
    def client(self):
        return self.params[1008]

    @client.setter
    def client(self, val):
        self.params[1008] = val

    @property
    def payment_address(self):
        return self.params.get(1187)

    @payment_address.setter
    def payment_address(self, val):
        self.params[1187] = val

    def set_intent(self, intent):
        self.intent = c.RECEIPT_TYPE_MAP[intent]
        self.params[IFptr.LIBFPTR_PARAM_RECEIPT_TYPE] = c.RECEIPT_TYPE_MAP[intent]

    def set_cashier(self, name, inn):
        self.cashier[1021] = name
        self.cashier[1203] = inn

    def set_client(self, name=None, inn=None, birthdate=None, citizenship=None,
                   document_code=None, document_data=None, address=None):
        '''
            Добавление сведений о покупателе(клиенте).
            Если в кассовом чеке нет ИНН покупателя, то указываются:
                - «дата рождения покупателя (клиента)» (Тег 1243);
                - «код вида документа, удостоверяющего личность» (Тег 1245);
                - «данные документа, удостоверяющего личность» (Тег 1246)
        '''
        client_info = {
            1227: name,
            1244: citizenship,
            1254: address
        }

        if inn:
            client_info.update({
                1228: inn
            })
        elif birthdate and document_code and document_data:
            client_info.update({
                1243: birthdate,
                1245: document_code,
                1246: document_data
            })

        self.params[1256] = prepare_dict(client_info)

    def set_sectoral_check_props(self, federal_id, date, number, value):
        ''' Добавление отраслевого реквизита чека '''
        self.params[1261] = {
            1262: federal_id,
            1263: date,
            1264: number,
            1265: value
        }

    def set_operation_check_props(self, name, value, timestamp):
        ''' Добавление операционного реквизит чека '''
        self.params[1270] = {
            1271: name,
            1272: value,
            1273: timestamp
        }

    def set_additional_user_props(self, name, value):
        ''' Добавление дополнительного реквизита пользователя '''
        self.params[1084] = {
            1085: name,
            1086: value
        }

    def set_additional_check_props(self, value=None):
        ''' Добавление дополнительного реквизита чека '''
        self.params[1192] = value

    def set_correction_info(self, type, date, document):
        ''' Добавление сведений для чека коррекции '''
        self.params[1173] = c.CORRECTION_RECEIPT_BASIS_MAP[type]
        self.params[1174] = {
            1178: date,
            1179: document
        }

    def add_position(self, name, price, quantity, total, vat, discount=0.0, measurement_unit=None,
                     payment_method=None, payment_object=None, agent=None, supplier=None,
                     mark_code=None, mark_quantity=None, **kw):
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

        if payment_object:
            params[1212] = c.PAYMENT_OBJECT_MAP[payment_object]

        if payment_method:
            params[1214] = c.PAYMENT_METHOD_MAP[payment_method]

        if agent:
            params.update(dict(agent))

        if supplier:
            params.update(dict(supplier))

        if kw.get('excise'):
            params[1229] = kw['excise']

        if kw.get('country_code'):
            params[1230] = kw['country_code']

        if kw.get('declaration_number'):
            params[1231] = kw['declaration_number']

        if kw.get('sectoral_item_props'):
            for sectoral_item in kw['sectoral_item_props']:
                params[1260] = {
                    1262: sectoral_item['federal_id'],
                    1263: sectoral_item['date'],
                    1264: sectoral_item['number'],
                    1265: sectoral_item['value']
                }
        if mark_code:
            type_mark_code = [*mark_code][0]
            mark_code = get_mark_code(mark_code[type_mark_code])

            is_verified, planing_marking_status = self.verify_mark_code(
                mark_code=mark_code,
                measure_name=measurement_unit,
                quantity=quantity,
                mark_quantity=mark_quantity
            )

            if not is_verified:
                raise Exception('Ошибка проверки КМ')

            params.update({
                IFptr.LIBFPTR_PARAM_MARKING_CODE_TYPE: IFptr.LIBFPTR_MCT12_AUTO,
                IFptr.LIBFPTR_PARAM_MARKING_CODE: mark_code,
                IFptr.LIBFPTR_PARAM_MARKING_CODE_STATUS: planing_marking_status,
                IFptr.LIBFPTR_PARAM_MARKING_PROCESSING_MODE: KKM_MARKING_PROCESSING_MODE,
            })

            if planing_marking_status in STATES_KM_FOR_MEASURABLE_POSITION:
                params.update({
                    IFptr.LIBFPTR_PARAM_QUANTITY: float(quantity),
                    IFptr.LIBFPTR_PARAM_MEASUREMENT_UNIT: measurement_unit
                })

            if mark_quantity:
                numerator = mark_quantity['numerator']
                denominator = mark_quantity['denominator']

                params.update({
                    IFptr.LIBFPTR_PARAM_MARKING_FRACTIONAL_QUANTITY: f'{numerator}/{denominator}'
                })

        self.positions.append(params)

    def add_payment(self, sum, type=None):
        ''' Регистрация оплаты '''
        self.payments.append({
            IFptr.LIBFPTR_PARAM_PAYMENT_TYPE: c.PAYMENT_MAP.get(type,
                                                                IFptr.LIBFPTR_PT_ELECTRONICALLY),
            IFptr.LIBFPTR_PARAM_PAYMENT_SUM: sum
        })

    def fiscalize(self, is_print=True):
        """ Фискализация чека

            Примечание: последовательность выполнения команд имеет значение
        """
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
