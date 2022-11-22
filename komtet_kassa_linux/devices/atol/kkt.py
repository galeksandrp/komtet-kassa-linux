import logging

from komtet_kassa_linux.devices.atol.driver import IFptr
from komtet_kassa_linux.libs.memoize import memoize_property

logger = logging.getLogger(__name__)


TYPES = STRING, DOUBLE, INTEGER, BOOL, DATETIME = 'string', 'double', 'integer', 'bool', 'datetime'
MODE_SIGNS = (AUTO_MODE_SIGN, OFFLINE_MODE_SIGN, ENCRYPTION_SIGN, INTERNET_SIGN, SERVICE_SIGN,
              BSO_SIGN, LOTTERY_SIGN, GAMBLING_SIGN, EXCISE_SIGN, MACHINE_INSTALLATION_SIGN) = [
    1001,  # 'Признак автоматического режима',
    1002,  # 'Признак автономного режима',
    1056,  # 'Признак шифрования',
    1108,  # 'Признак ККТ для расчетов в сети Интернет',
    1109,  # 'Признак расчетов за услуги',
    1110,  # 'Признак АС БСО',
    1126,  # 'Признак проведения лотерей',
    1193,  # 'Признак проведения азартных игр',
    1207,  # 'Признак подакцизного товара',
    1221  # 'Признак установки в автомате'
]


def _get_param(fptr, tag, _type=STRING):
    if _type == INTEGER:
        return fptr.getParamInt(tag)
    elif _type == DATETIME:
        return fptr.getParamDateTime(tag)
    elif _type == DOUBLE:
        return fptr.getParamDouble(tag)
    elif _type == BOOL:
        return fptr.getParamBool(tag)

    return fptr.getParamString(tag).strip()


class KKT:

    _driver = None

    def __init__(self, driver):
        self._driver = driver

    def _get_reg_info(self, tag, param_type=STRING):
        with self._driver.query_fn_data(IFptr.LIBFPTR_FNDT_REG_INFO) as fptr:
            return _get_param(fptr, tag, param_type)

    def _get_fn_info(self, tag, param_type=STRING):
        with self._driver.query_fn_data(IFptr.LIBFPTR_FNDT_FN_INFO) as fptr:
            return _get_param(fptr, tag, param_type)

    @property
    def ffd_version(self):
        with self._driver.query_fn_data(IFptr.LIBFPTR_FNDT_FFD_VERSIONS) as fptr:
            return _get_param(fptr, IFptr.LIBFPTR_PARAM_FFD_VERSION)

    @property
    def date_time(self):
        with self._driver.query_data(IFptr.LIBFPTR_DT_STATUS) as fptr:
            return _get_param(fptr, IFptr.LIBFPTR_PARAM_DATE_TIME, DATETIME)

    @property
    def serial_number(self):
        with self._driver.query_data(IFptr.LIBFPTR_DT_STATUS) as fptr:
            return _get_param(fptr, IFptr.LIBFPTR_PARAM_SERIAL_NUMBER)

    @property
    def inn(self):
        return self._get_reg_info(1018)

    @memoize_property
    def mode_signs(self):
        return {code: self._get_reg_info(code, BOOL) for code in MODE_SIGNS}

    @property
    def reg_number(self):
        return self._get_reg_info(1037)

    @property
    def fiscal_drive_id(self):
        return self._get_fn_info(IFptr.LIBFPTR_PARAM_SERIAL_NUMBER)

    @property
    def fn_state(self):
        return self._get_fn_info(IFptr.LIBFPTR_PARAM_FN_FLAGS, INTEGER)

    @property
    def ofd_url(self):
        return self._get_reg_info(1046)

    @property
    def organisation(self):
        return self._get_reg_info(1048)

    @property
    def organisation_address(self):
        return self._get_reg_info(1009)

    @property
    def is_closed_document(self):
        with self._driver.query() as fptr:
            return _get_param(fptr, IFptr.LIBFPTR_PARAM_DOCUMENT_CLOSED, BOOL)

    @property
    def last_receipt(self):
        with self._driver.query_fn_data(IFptr.LIBFPTR_FNDT_LAST_RECEIPT) as fptr:
            return {
                'fiscal_document_number': _get_param(fptr, IFptr.LIBFPTR_PARAM_DOCUMENT_NUMBER),
                'sum': _get_param(fptr, IFptr.LIBFPTR_PARAM_RECEIPT_SUM, DOUBLE),
                'fiscal_id': _get_param(fptr, IFptr.LIBFPTR_PARAM_FISCAL_SIGN),
                'time': _get_param(fptr, IFptr.LIBFPTR_PARAM_DATE_TIME, DATETIME).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
            }

    @property
    def validity(self):
        with self._driver.query_fn_data(IFptr.LIBFPTR_FNDT_VALIDITY) as fptr:
            return _get_param(fptr, IFptr.LIBFPTR_PARAM_DATE_TIME, DATETIME)

    @property
    def unconfirmed_fiscal_document_count(self):
        with self._driver.query_fn_data(IFptr.LIBFPTR_FNDT_OFD_EXCHANGE_STATUS) as fptr:
            return _get_param(fptr, IFptr.LIBFPTR_PARAM_DOCUMENTS_COUNT)

    @property
    def last_document_number(self):
        with self._driver.query_fn_data(IFptr.LIBFPTR_FNDT_LAST_DOCUMENT) as fptr:
            return _get_param(fptr, IFptr.LIBFPTR_PARAM_DOCUMENT_NUMBER)

    @property
    def shift_info(self):
        with self._driver.query_fn_data(IFptr.LIBFPTR_FNDT_SHIFT) as fptr:
            return {
                'session_check': _get_param(fptr, IFptr.LIBFPTR_PARAM_RECEIPT_NUMBER),
                'session': _get_param(fptr, IFptr.LIBFPTR_PARAM_SHIFT_NUMBER)
            }

    def get_info(self):
        return {
            'serial_number': self.serial_number,
            'fiscal_id': self.fiscal_drive_id,
            'reg_till': self.validity,
            'fn_state': self.fn_state
        }

    def get_detail_info(self):
        return {
            'serial_number': self.serial_number,
            'fiscal_id': self.fiscal_drive_id,
            'validity': self.validity,
            'errors': self.fn_warnings_and_errors,
            'unconfirmed_document_count': self.unconfirmed_fiscal_document_count,
            'last_document': self.last_document_number,
        }

    @property
    def fn_warnings_and_errors(self):
        # TODO: Вынести из класса
        warnings = self.fn_state
        if warnings:
            flags = {
                0: 'Требуется срочная замена ФН',
                1: 'Исчерпан ресурс ФН',
                2: 'Память ФН переполнена',
                3: 'Превышено время ожидания ответа от ОФД',
                7: 'Критическая ошибка ФН'
            }
            return list(map(lambda offset: flags.get(offset),
                            filter(lambda offset: (warnings >> offset) & 1, range(7))))
        return []
