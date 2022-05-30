import datetime
import logging

from komtet_kassa_linux.driver import IFptr
from komtet_kassa_linux.models import Printer


SHIFT_STATES = CLOSED, OPENED, EXPIRED = (
    IFptr.LIBFPTR_SS_CLOSED, IFptr.LIBFPTR_SS_OPENED, IFptr.LIBFPTR_SS_EXPIRED
)


logger = logging.getLogger(__name__)

AUTOCLOSE_SESSION_TIME = (23, 59)


class Shift:

    _driver = None
    _device_id = None

    def __init__(self, driver, device_id):
        self._driver = driver
        self._device_id = device_id

    @property
    def state(self):
        with self._driver.query_data(IFptr.LIBFPTR_DT_SHIFT_STATE) as fptr:
            return fptr.getParamInt(IFptr.LIBFPTR_PARAM_SHIFT_STATE)

    @property
    def is_open(self):
        return self.state == OPENED

    @property
    def is_closed(self):
        return self.state == CLOSED

    @property
    def is_expired(self):
        return self.state == EXPIRED

    @property
    def number(self):
        if self.state == CLOSED:
            return

        with self._driver.query_data(IFptr.LIBFPTR_DT_SHIFT_STATE) as fptr:
            return fptr.getParamInt(IFptr.LIBFPTR_PARAM_SHIFT_NUMBER)

    def open(self, cashier_name=None, cashier_inn=None):
        if self.is_open:
            return
        elif self.is_expired:
            self.close()

        with self._driver.query() as fptr:
            if cashier_name and cashier_inn:
                fptr.setParam(1021, cashier_name)
                fptr.setParam(1203, cashier_inn)
                if fptr.operatorLogin():
                    raise self._driver.exception('Ошибка регистрации кассира')

            if fptr.openShift():
                raise self._driver.exception('Ошибка открытия смены')
            elif fptr.checkDocumentClosed():
                raise self._driver.exception(
                    'Ошибка проверки состояния документа при открытии смены'
                )
            elif not fptr.getParamBool(IFptr.LIBFPTR_PARAM_DOCUMENT_CLOSED):
                raise self._driver.exception('Документ не закрылся при открытии смены')

        logger.info('%s открыта', self)
        return True

    def close(self):
        if self.is_closed:
            return

        with self._driver.query() as fptr:
            fptr.setParam(IFptr.LIBFPTR_PARAM_REPORT_TYPE, IFptr.LIBFPTR_RT_CLOSE_SHIFT)
            if fptr.report():
                raise self._driver.exception('Ошибка печати отчета при закрытии смены')
            elif fptr.checkDocumentClosed():
                raise self._driver.exception(
                    'Ошибка проверки состояния документа при закрытии смены'
                )
            elif not fptr.getParamBool(IFptr.LIBFPTR_PARAM_DOCUMENT_CLOSED):
                raise self._driver.exception('Документ не закрылся при закрытии смены')

            printer = Printer.query.filter_by(serial_number=self._device_id).first()
            printer.update(session_closed_at=datetime.datetime.now())

        logger.info('%s закрыта', self)
        return True

    def reopen(self):
        if self.is_open or self.is_expired:
            self.close()
        return self.open()

    def autocheck(self):
        # TODO: вынести проверку от суда
        now = datetime.datetime.now()
        if (now.hour, now.minute) == AUTOCLOSE_SESSION_TIME:
            printer = Printer.query.filter_by(serial_number=self._device_id).first()
            if (
                not printer.session_closed_at or
                (printer.session_closed_at.hour,
                 printer.session_closed_at.minute) != AUTOCLOSE_SESSION_TIME or
                printer.session_closed_at.date() != now.date()
            ):
                self.close()

    def __repr__(self):
        return 'Смена[%s]' % self._device_id
