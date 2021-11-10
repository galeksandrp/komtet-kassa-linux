from komtet_kassa_linux.driver import IFptr


RECEIPT_TYPE_MAP = {
    'sell': IFptr.LIBFPTR_RT_SELL,
    'sellReturn': IFptr.LIBFPTR_RT_SELL_RETURN,
    'sellCorrection': IFptr.LIBFPTR_RT_SELL_CORRECTION,
    'sellReturnCorrection': IFptr.LIBFPTR_RT_BUY_CORRECTION,
    'buy': IFptr.LIBFPTR_RT_BUY,
    'buyReturn': IFptr.LIBFPTR_RT_BUY_RETURN,
    'buyCorrection': IFptr.LIBFPTR_RT_BUY_CORRECTION,
    # IFptr.LIBFPTR_RT_BUY_RETURN_CORRECTION
}


SNO_MAP = {
    0: IFptr.LIBFPTR_TT_OSN,
    1: IFptr.LIBFPTR_TT_USN_INCOME,
    2: IFptr.LIBFPTR_TT_USN_INCOME_OUTCOME,
    3: IFptr.LIBFPTR_TT_ENVD,
    4: IFptr.LIBFPTR_TT_ESN,
    5: IFptr.LIBFPTR_TT_PATENT
}

AGENT_TYPE_MAP = {
    'bank_payment_agent': IFptr.LIBFPTR_AT_BANK_PAYING_AGENT,
    'bank_payment_subagent': IFptr.LIBFPTR_AT_BANK_PAYING_SUBAGENT,
    'payment_agent': IFptr.LIBFPTR_AT_PAYING_AGENT,
    'payment_subagent': IFptr.LIBFPTR_AT_PAYING_SUBAGENT,
    'solicitor': IFptr.LIBFPTR_AT_ATTORNEY,
    'commissionaire': IFptr.LIBFPTR_AT_COMMISSION_AGENT,
    'agent': IFptr.LIBFPTR_AT_ANOTHER
}

TAX_MAP = {
    # IFptr.LIBFPTR_TAX_DEPARTMENT,
    '20': IFptr.LIBFPTR_TAX_VAT20,
    '18': IFptr.LIBFPTR_TAX_VAT18,
    '10': IFptr.LIBFPTR_TAX_VAT10,
    '120': IFptr.LIBFPTR_TAX_VAT120,
    '118': IFptr.LIBFPTR_TAX_VAT118,
    '110': IFptr.LIBFPTR_TAX_VAT110,
    '0': IFptr.LIBFPTR_TAX_VAT0,
    'no': IFptr.LIBFPTR_TAX_NO
}

PAYMENT_MAP = {
    'cash': IFptr.LIBFPTR_PT_CASH,
    'card': IFptr.LIBFPTR_PT_ELECTRONICALLY,
    'prepayment': IFptr.LIBFPTR_PT_PREPAID,
    'credit': IFptr.LIBFPTR_PT_CREDIT,
    'counter_provisioning': IFptr.LIBFPTR_PT_OTHER
}


CORRECTION_RECEIPT_BASIS_MAP = {
    "self": 0,
    "forced": 1
}

PAYMENT_METHOD_MAP = {
    'pre_payment_full': 1,
    'pre_payment_part': 2,
    'advance': 3,
    'full_payment': 4,
    'credit_part': 5,
    'credit_pay': 6,
    'credit': 7
}

PAYMENT_OBJECT_MAP = {
    'product': 1,
    'product_practical': 2,
    'work': 3,
    'service': 4,
    'gambling_bet': 5,
    'gambling_win': 6,
    'lottery_bet': 7,
    'lottery_win': 8,
    'rid': 9,
    'payment': 10,
    'commission': 11,
    'composite': 12,
    'other': 13
}


class Agent:

    def __init__(self, type):
        self.__data = {
            1222: AGENT_TYPE_MAP[type]
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


class Receipt:

    _driver = None

    def __init__(self, driver, type='sell'):
        self._driver = driver
        self.params = {
            IFptr.LIBFPTR_PARAM_RECEIPT_TYPE: RECEIPT_TYPE_MAP[type],
            1055: IFptr.LIBFPTR_TT_DEFAULT
        }
        self.positions = []
        self.payments = []
        self.cashier = {}

    def _set_param(self, key, val):
        if not val:
            if key in self.params:
                del self.params[key]
            return

        self.params[key] = val

    @property
    def sno(self):
        return self.params[1055]

    @sno.setter
    def sno(self, val):
        self.params[1055] = SNO_MAP[val]

    @property
    def email(self):
        return self.params[1008]

    @email.setter
    def email(self, val):
        self._set_param(1008, val)

    @property
    def payment_address(self):
        return self.params.get(1187)

    @payment_address.setter
    def payment_address(self, val):
        self._set_param(1187, val)

    def set_cashier(self, name, inn):
        self.cashier[1021] = name
        self.cashier[1203] = inn

    def set_client(self, inn=None, name=None):
        self._set_param(1228, inn)
        self._set_param(1227, name)

    def add_position(self, name, price, quantity, total, vat, measurement_unit=None,
                     payment_method=None, payment_object=None, agent=None, supplier=None):
        params = {
            IFptr.LIBFPTR_PARAM_COMMODITY_NAME: name,
            IFptr.LIBFPTR_PARAM_PRICE: price,
            IFptr.LIBFPTR_PARAM_QUANTITY: quantity,
            IFptr.LIBFPTR_PARAM_POSITION_SUM: total,
            IFptr.LIBFPTR_PARAM_TAX_TYPE: TAX_MAP[vat],
        }
        if measurement_unit:
            params[1197] = measurement_unit
        if payment_method:
            params[1214] = PAYMENT_METHOD_MAP[payment_method]
        if payment_object:
            params[1212] = PAYMENT_OBJECT_MAP[payment_object]

        if agent:
            params.update(dict(agent))

        if supplier:
            params.update(dict(supplier))

        self.positions.append(params)

    def add_payment(self, sum, type=None):
        self.payments.append({
            IFptr.LIBFPTR_PARAM_PAYMENT_TYPE: PAYMENT_MAP.get(type,
                                                              IFptr.LIBFPTR_PT_ELECTRONICALLY),
            IFptr.LIBFPTR_PARAM_PAYMENT_SUM: sum
        })

    def set_correction_info(self, basis, name, date, number):
        self.params[1173] = CORRECTION_RECEIPT_BASIS_MAP[basis]
        self.params[1174] = {
            1177: name,
            1178: date,
            1179: number
        }

    def cansel(self):
        with self._driver.query() as fptr:
            if fptr.cancelReceipt():
                raise self._driver.exception('Ошибка отмены документа')

    def fiscalize(self, is_print=True):
        """ Фискализация чека

            Примечание: последовательность выполнения команд имеет значение
        """

        with self._driver.query() as fptr:
            if self.cashier:
                _set_params(fptr, self.cashier)
                if fptr.operatorLogin():
                    raise self._driver.exception('Ошибка регистрации кассира')

            _set_params(fptr, self.params)
            fptr.setParam(IFptr.LIBFPTR_PARAM_RECEIPT_ELECTRONICALLY, not is_print)
            if fptr.openReceipt():
                raise self._driver.exception('Ошибка открытия чека')

            for position in self.positions:
                _set_params(fptr, position)
                if fptr.registration():
                    raise self._driver.exception('Ошибка регистрации позиции')

            fptr.setParam(IFptr.LIBFPTR_PARAM_SUM,
                          sum(map(lambda p: p[IFptr.LIBFPTR_PARAM_PAYMENT_SUM],
                                  self.payments), 0))
            if fptr.receiptTotal():
                raise self._driver.exception('Ошибка регистрации итога')

            for payment in self.payments:
                _set_params(fptr, payment)
                if fptr.payment():
                    raise self._driver.exception('Ошибка регистрации платежа')

            if fptr.closeReceipt():
                pass
            elif fptr.checkDocumentClosed():
                raise self._driver.exception(
                    'Ошибка проверки состояния документа при закрытии чека'
                )
            elif not fptr.getParamBool(IFptr.LIBFPTR_PARAM_DOCUMENT_CLOSED):
                raise self._driver.exception('Документ не закрылся при закрытии чека')

    def print_out(self):
        return self.fiscalize(False)


class ByteArray:

    def __init__(self, bytes):
        self.__data = bytes

    def to_list(self):
        return self.__data


def _set_params(fptr, params):
    for tag, value in params.items():
        if isinstance(value, dict):
            _set_params(fptr, value)
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
