import base64
from time import sleep

from komtet_kassa_linux.driver import IFptr
from komtet_kassa_linux.devices.atol import constants as c

COUNT_OISM_VERIFY_TIMES = 5
DEFAULT_QUANTITY = 1.0
FFD_UNKNOWN = 'unknown'
FFD_1_05 = '105'
FFD_1_10 = '110'
FFD_1_20 = '120'
FFD_FN_VERSIONS_TYPE_MAP = {FFD_UNKNOWN, FFD_1_05, FFD_1_10, FFD_1_20}
KKM_MARKING_PROCESSING_MODE = 0  # Режим обработки кода товара(необходимо передавать 0)
SUCCESS_CODE_VERIFY = 15
STATES_KM_FOR_MEASURABLE_POSITION = [IFptr.LIBFPTR_MES_DRY_FOR_SALE, IFptr.LIBFPTR_MES_DRY_RETURN]


class Receipt:

    def __init__(self, driver=None, ffd_version=FFD_1_05):
        self._driver = driver
        self.ffd_version = ffd_version
        self.intent = None

    def fiscalize(self, is_print=True):
        raise NotImplementedError

    def cancel(self):
        with self._driver.query() as fptr:
            if fptr.cancelReceipt():
                raise self._driver.exception('Ошибка отмены документа')

    def verify_mark_code(self, mark_code, measure_name=IFptr.LIBFPTR_IU_PIECE,
                         quantity=DEFAULT_QUANTITY, mark_quantity=None):
        '''
            Метод проверки Кода Маркировки(КМ)
            входные параметры:
                1. mark_code - значение КМ;
                2. measure_name - мера количества товара (тег 2108);
                3. mark_quantity - значение Дробного количества маркированного товара(1291).
        '''
        validation_result = False
        with self._driver.query() as fptr:
            fptr.cancelMarkingCodeValidation()  # Прерывание проверки КМ
            fptr.clearMarkingCodeValidationResult()  # Очистка таблицы проверенных КМ

            is_ism_available = self.ping_ism_server(fptr)
            if not is_ism_available:
                raise Exception('Сервер ИСМ недоступен')

            params = {
                IFptr.LIBFPTR_PARAM_MARKING_CODE_TYPE: IFptr.LIBFPTR_MCT12_AUTO,
                IFptr.LIBFPTR_PARAM_MARKING_CODE: mark_code,
                IFptr.LIBFPTR_PARAM_MARKING_WAIT_FOR_VALIDATION_RESULT: True,
                IFptr.LIBFPTR_PARAM_MARKING_PROCESSING_MODE: KKM_MARKING_PROCESSING_MODE
            }

            planing_marking_status = self.planing_marking_status(mark_quantity)
            params.update({
                IFptr.LIBFPTR_PARAM_MARKING_CODE_STATUS: planing_marking_status
            })

            if planing_marking_status in STATES_KM_FOR_MEASURABLE_POSITION:
                params.update({
                    IFptr.LIBFPTR_PARAM_QUANTITY: float(quantity),
                    IFptr.LIBFPTR_PARAM_MEASUREMENT_UNIT: measure_name
                })

            if mark_quantity:
                numerator = mark_quantity['numerator']
                denominator = mark_quantity['denominator']

                params.update({
                    IFptr.LIBFPTR_PARAM_MARKING_FRACTIONAL_QUANTITY: f'{numerator}/{denominator}'
                })

            set_params(fptr, params)
            fptr.beginMarkingCodeValidation()

            attempts_count = 0
            while attempts_count < COUNT_OISM_VERIFY_TIMES:
                fptr.getMarkingCodeValidationStatus()
                if fptr.getParamBool(IFptr.LIBFPTR_PARAM_MARKING_CODE_VALIDATION_READY):
                    break
                attempts_count += 1
                sleep(1)

            if fptr.getParamInt(IFptr.LIBFPTR_PARAM_MARKING_CODE_ONLINE_VALIDATION_RESULT) == SUCCESS_CODE_VERIFY:
                fptr.acceptMarkingCode()
                validation_result = True
            elif fptr.getParamInt(IFptr.LIBFPTR_PARAM_MARKING_CODE_ONLINE_VALIDATION_ERROR):
                error_description = fptr.getParamString(
                    IFptr.LIBFPTR_PARAM_MARKING_CODE_ONLINE_VALIDATION_ERROR_DESCRIPTION
                )
                raise Exception(error_description)

        return validation_result, planing_marking_status

    def planing_marking_status(self, mark_quantity):
        ''' Метод получения планируемого статуса КМ '''
        planing_mark_status = IFptr.LIBFPTR_MES_UNCHANGED  # статус товара не изменился

        if self.intent == c.RECEIPT_TYPE_MAP['sell'] or self.intent == c.RECEIPT_TYPE_MAP['buy']:
            planing_mark_status = (IFptr.LIBFPTR_MES_DRY_FOR_SALE
                                   if mark_quantity else IFptr.LIBFPTR_MES_PIECE_SOLD)

        elif (self.intent == c.RECEIPT_TYPE_MAP['sellReturn'] or
              self.intent == c.RECEIPT_TYPE_MAP['buyReturn']):
            planing_mark_status = (IFptr.LIBFPTR_MES_DRY_RETURN
                                   if mark_quantity else IFptr.LIBFPTR_MES_PIECE_RETURN)

        return planing_mark_status

    def ping_ism_server(self, fptr):
        '''
             Метод выполнения проверки связи с сервером ИСМ
        '''
        # Начать проверку связи с сервером ИСМ
        fptr.pingMarkingServer()
        while True:
            fptr.getMarkingServerStatus()
            if fptr.getParamBool(IFptr.LIBFPTR_PARAM_CHECK_MARKING_SERVER_READY):
                return True
            sleep(1)


class Agent:

    def __init__(self, type):
        self.__data = {
            1222: c.AGENT_TYPE_MAP[type]
        }

    def set_paying_agent(self, operation, phones):
        ''' Установка атрибутов платежного агента '''
        self.__data[1223] = {
            1044: operation,
            1073: phones
        }

    def set_receive_payments_operator(self, phones):
        ''' Установка атрибутов оператора по приему платежей '''
        self.__data[1223] = {
            1074: phones
        }

    def set_money_transfer_operator(self, phones, name, address, inn):
        ''' Установка атрибутов оператора перевода '''
        self.__data[1223] = {
            1026: name,
            1005: address,
            1016: inn,
            1075: phones
        }

    def __iter__(self):
        for item in self.__data.items():
            yield item

    def __getitem__(self, item):
        return self.__data[item]


class Supplier:

    def __init__(self, phones, name, inn):
        self.__data = {
            1224: {
                1225: name,
                1171: phones
            },
            1226: inn
        }

    def __iter__(self):
        for item in self.__data.items():
            yield item

    def __getitem__(self, item):
        return self.__data[item]


class ByteArray:

    def __init__(self, bytes):
        self.__data = bytes

    def to_list(self):
        return self.__data


def set_params(fptr, params):
    for tag, value in params.items():
        if isinstance(value, dict):
            set_params(fptr, value)
            fptr.utilFormTlv()
            params[tag] = ByteArray(fptr.getParamByteArray(IFptr.LIBFPTR_PARAM_TAG_VALUE))

    for tag, value in params.items():
        if isinstance(value, list):
            for val in value:
                fptr.setParam(tag, val)
        elif isinstance(value, ByteArray):
            fptr.setParam(tag, value.to_list())
        else:
            fptr.setParam(tag, value)
