from komtet_kassa_linux.devices.atol.driver import IFptr


AGENT_TYPE_MAP = {
    'bank_payment_agent': IFptr.LIBFPTR_AT_BANK_PAYING_AGENT,
    'bank_payment_subagent': IFptr.LIBFPTR_AT_BANK_PAYING_SUBAGENT,
    'payment_agent': IFptr.LIBFPTR_AT_PAYING_AGENT,
    'payment_subagent': IFptr.LIBFPTR_AT_PAYING_SUBAGENT,
    'solicitor': IFptr.LIBFPTR_AT_ATTORNEY,
    'commissionaire': IFptr.LIBFPTR_AT_COMMISSION_AGENT,
    'agent': IFptr.LIBFPTR_AT_ANOTHER
}

PLANNED_STATUS_MAP = {
    1: IFptr.LIBFPTR_MES_PIECE_SOLD,
    2: IFptr.LIBFPTR_MES_DRY_FOR_SALE,
    3: IFptr.LIBFPTR_MES_PIECE_RETURN,
    4: IFptr.LIBFPTR_MES_DRY_RETURN,
    5: IFptr.LIBFPTR_MES_PIECE_FOR_SALE,
    6: IFptr.LIBFPTR_MES_DRY_SOLD,
    255: IFptr.LIBFPTR_MES_UNCHANGED
}

SNO_MAP = {
    0: IFptr.LIBFPTR_TT_OSN,
    1: IFptr.LIBFPTR_TT_USN_INCOME,
    2: IFptr.LIBFPTR_TT_USN_INCOME_OUTCOME,
    3: IFptr.LIBFPTR_TT_ENVD,
    4: IFptr.LIBFPTR_TT_ESN,
    5: IFptr.LIBFPTR_TT_PATENT
}

RECEIPT_TYPE_MAP = {
    'sell': IFptr.LIBFPTR_RT_SELL,
    'sellReturn': IFptr.LIBFPTR_RT_SELL_RETURN,
    'sellCorrection': IFptr.LIBFPTR_RT_SELL_CORRECTION,
    'sellReturnCorrection': IFptr.LIBFPTR_RT_SELL_RETURN_CORRECTION,
    'buy': IFptr.LIBFPTR_RT_BUY,
    'buyReturn': IFptr.LIBFPTR_RT_BUY_RETURN,
    'buyCorrection': IFptr.LIBFPTR_RT_BUY_CORRECTION,
    'buyReturnCorrection': IFptr.LIBFPTR_RT_BUY_RETURN_CORRECTION
}

CORRECTION_RECEIPT_BASIS_MAP = {
    'self': 0,
    'forced': 1,
    'instruction': 1
}

TAX_MAP = {
    'no': IFptr.LIBFPTR_TAX_NO,
    '0': IFptr.LIBFPTR_TAX_VAT0,
    '5': IFptr.LIBFPTR_TAX_VAT5,
    '7': IFptr.LIBFPTR_TAX_VAT7,
    '10': IFptr.LIBFPTR_TAX_VAT10,
    '20': IFptr.LIBFPTR_TAX_VAT20,
    '105': IFptr.LIBFPTR_TAX_VAT105,
    '107': IFptr.LIBFPTR_TAX_VAT107,
    '110': IFptr.LIBFPTR_TAX_VAT110,
    '120': IFptr.LIBFPTR_TAX_VAT120
}

MEASURE_MAP_V1 = {
    'шт': IFptr.LIBFPTR_IU_PIECE,
    'г': IFptr.LIBFPTR_IU_GRAM,
    'кг': IFptr.LIBFPTR_IU_KILOGRAM,
    'т': IFptr.LIBFPTR_IU_TON,
    'см': IFptr.LIBFPTR_IU_CENTIMETER,
    'дм': IFptr.LIBFPTR_IU_DECIMETER,
    'м': IFptr.LIBFPTR_IU_METER,
    'кв. см': IFptr.LIBFPTR_IU_SQUARE_CENTIMETER,
    'кв. дм': IFptr.LIBFPTR_IU_SQUARE_DECIMETER,
    'кв. м': IFptr.LIBFPTR_IU_SQUARE_METER,
    'мл': IFptr.LIBFPTR_IU_MILLILITER,
    'л': IFptr.LIBFPTR_IU_LITER,
    'куб. м': IFptr.LIBFPTR_IU_CUBIC_METER,
    'квт ч': IFptr.LIBFPTR_IU_KILOWATT_HOUR,
    'гкал': IFptr.LIBFPTR_IU_GKAL,
    'сутки': IFptr.LIBFPTR_IU_DAY,
    'час': IFptr.LIBFPTR_IU_HOUR,
    'мин': IFptr.LIBFPTR_IU_MINUTE,
    'с': IFptr.LIBFPTR_IU_SECOND,
    'кбайт': IFptr.LIBFPTR_IU_KILOBYTE,
    'мбайт': IFptr.LIBFPTR_IU_MEGABYTE,
    'гбайт': IFptr.LIBFPTR_IU_GIGABYTE,
    'тбайт': IFptr.LIBFPTR_IU_TERABYTE,
    'у.е.': IFptr.LIBFPTR_IU_OTHER
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
    'pay': 12,
    'other': 13,
    'property_right': 14,
    'non_operating': 15,
    'insurance': 16,
    'sales_tax': 17,
    'resort_fee': 18,
    'deposit': 19,
    'consumption': 20,
    'sole_proprietor_cpi_contributins': 21,
    'cpi_contributins': 22,
    'sole_proprietor_cmi_contributins': 23,
    'cmi_contributins': 24,
    'csi_contributins': 25,
    'casino_payment': 26,
    'payment_of_the_money': 27,
    'atnm': 30,
    'atm': 31,
    'tnm': 32,
    'tm': 33
}

PAYMENT_MAP = {
    'cash': IFptr.LIBFPTR_PT_CASH,
    'card': IFptr.LIBFPTR_PT_ELECTRONICALLY,
    'prepayment': IFptr.LIBFPTR_PT_PREPAID,
    'credit': IFptr.LIBFPTR_PT_CREDIT,
    'counter_provisioning': IFptr.LIBFPTR_PT_OTHER
    #  5-9: расширенные виды оплаты не поддерживаются в KOMTET Kassa
}

MEASURE_MAP_V2 = {
    0: 'Шт',
    10: 'Грамм',
    11: 'Килограмм',
    12: 'Тонна',
    20: 'Сантиметр',
    21: 'Дециметр',
    22: 'Метр',
    30: 'Квадратный сантиметр',
    31: 'Квадратный дециметр',
    32: 'Квадратный метр',
    40: 'Миллилитр',
    41: 'Литр',
    42: 'Кубический метр',
    50: 'Киловатт час',
    51: 'Гигакалория',
    70: 'Сутки (день)',
    71: 'Час',
    72: 'Минута',
    73: 'Секунда',
    80: 'Килобайт',
    81: 'Мегабайт',
    82: 'Гигабайт',
    83: 'Терабайт',
    255: 'Прочие единицы измерения'
}

MARKING_CODE_ONLINE_VALIDATION_DESCRIPTION_MAP = {
    0: '[M] Проверка КП КМ не выполнена, статус товара ОИСМ не проверен',
    1: '[M-] Проверка КП КМ выполнена в ФН с отрицательным результатом, статус товара ОИСМ не проверен',
    2: '[M] Проверка КП КМ выполнена с положительным результатом, статус товара ОИСМ не проверен',
    16: '[M] Проверка КП КМ не выполнена, статус товара ОИСМ не проверен (ККТ функционирует в автономном режиме)',
    17: '[M-] Проверка КП КМ выполнена в ФН с отрицательным результатом, статус товара ОИСМ не проверен (ККТ функционирует в автономном режиме)',
    19: '[M] Проверка КП КМ выполнена в ФН с положительным результатом, статус товара ОИСМ не проверен (ККТ функционирует в автономном режиме)',
    5: '[M-] Проверка КП КМ выполнена с отрицательным результатом, статус товара у ОИСМ некорректен',
    7: '[M-] Проверка КП КМ выполнена с положительным результатом, статус товара у ОИСМ некорректен',
    15: '[M+] Проверка КП КМ выполнена с положительным результатом, статус товара у ОИСМ корректен'
}
