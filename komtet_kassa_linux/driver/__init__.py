import inspect
import logging
import os
import platform
import time
import types
from contextlib import contextmanager
from threading import Lock

from .libfptr10 import IFptr


logger = logging.getLogger(__name__)


DRIVER_PLATFORM_DIRECTORY_MAP = {
    'armv7l': 'linux-armhf',
    'x86_64': 'linux-x64'
}
LIBRARY_PATH = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(IFptr))),
                            DRIVER_PLATFORM_DIRECTORY_MAP.get(platform.machine(), 'linux-armhf'))


ERROR_DENIED_IN_CLOSED_RECEIPT = IFptr.LIBFPTR_ERROR_DENIED_IN_CLOSED_RECEIPT


def factory_driver(device):
    if True: # utilsGetWinAvailability
        fptr = IFptr()
    else:
        fptr = IFptr(os.path.join(LIBRARY_PATH, "libfptr10.so"))
        fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_LIBRARY_PATH, LIBRARY_PATH)
    fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_MODEL, str(IFptr.LIBFPTR_MODEL_ATOL_AUTO))
    if True: # utilsGetWinAvailability
        fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_OFD_CHANNEL, str(IFptr.LIBFPTR_OFD_CHANNEL_NONE))
    else:
        fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_OFD_CHANNEL, str(IFptr.LIBFPTR_OFD_CHANNEL_AUTO))

    # fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_PORT, str(IFptr.LIBFPTR_PORT_COM))
    # fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_COM_FILE, device['DEVPATH'])
    fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_PORT, str(IFptr.LIBFPTR_PORT_USB))
    if False: # utilsGetWinAvailability
        fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_USB_DEVICE_PATH, device['DEVPATH'].split('/')[-1])

    fptr.applySingleSettings()
    return fptr


class SingletonMeta(type):
    ''' Менеджер драйверов

        Примичание: Многопоточный одиночка, реализованный на примере:
                    https://refactoring.guru/ru/design-patterns/singleton/python/example#example-1
    '''

    _lock = Lock()
    _drivers = {
        # <path>: <link>, <link_counter>
    }

    def __call__(cls, device, *args, **kwargs):
        subcls = super()
        return cls.bind(device, factory=lambda _device: subcls.__call__(_device, *args, **kwargs))

    @classmethod
    def bind(cls, device, factory):
        device_id = device['ID_SERIAL_SHORT']
        with cls._lock:
            if device_id not in cls._drivers:
                cls._drivers[device_id] = factory(device), 0

            driver, counter = cls._drivers[device_id]
            counter += 1
            cls._drivers[device_id] = driver, counter

        # logger.debug('Кол-во ссылок на %s: %d', driver, counter)
        return driver

    @classmethod
    def unbind(cls, device):
        device_id = device['ID_SERIAL_SHORT']
        with cls._lock:
            driver, counter = cls._drivers[device_id]
            counter -= 1
            cls._drivers[device_id] = driver, counter

            if counter < 1:
                driver._close()
                del cls._drivers[device_id]

        # logger.debug('Кол-во ссылок на %s: %d', driver, counter)


class DriverException(Exception):

    def __init__(self, error_code, error_description, error_msg):
        self.error_code = error_code
        self.error_description = error_description
        self.error_msg = error_msg

    def __repr__(self):
        return "%s - %s, %s" % (self.error_msg, self.error_code, self.error_description)


class Driver(metaclass=SingletonMeta):
    ''' Драйвер
    '''

    _device_id = None
    _fptr = None
    _lock = Lock()

    def __init__(self, device, factory=None):
        self._device = device
        self._fptr = (factory or factory_driver)(device)
        self._open()

    def __del__(self):
        self._close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tp):
        self.destroy()

    def _open(self):
        self._fptr.open()
        while not self._fptr.isOpened():
            logger.info('%s занят', self)
            time.sleep(0.1)
            self._fptr.open()
        logger.info('%s подключен', self)

    def _close(self):
        self._fptr.close()
        logger.info('%s отключен', self)

    def destroy(self):
        SingletonMeta.unbind(self._device)

    @contextmanager
    def query(self):
        with self._lock:
            yield self._fptr

    @contextmanager
    def query_data(self, data_type):
        with self.query() as fptr:
            fptr.setParam(IFptr.LIBFPTR_PARAM_DATA_TYPE, data_type)
            if fptr.queryData():
                raise self.exception('Ошибка запроса общей информации и статуса ККТ')
            yield fptr

    @contextmanager
    def query_fn_data(self, data_type):
        with self.query() as fptr:
            fptr.setParam(IFptr.LIBFPTR_PARAM_FN_DATA_TYPE, data_type)
            if fptr.fnQueryData():
                raise self.exception('Ошибка запроса регистрационных данных')
            yield fptr

    @property
    def serial_number(self):
        with self.query_data(IFptr.LIBFPTR_DT_STATUS) as fptr:
            return fptr.getParamString(IFptr.LIBFPTR_PARAM_SERIAL_NUMBER).strip()

    @property
    def version(self):
        with self.query() as fptr:
            return fptr.version()

    def exception(self, msg):
        return DriverException(self._fptr.errorCode(), self._fptr.errorDescription(),
                               error_msg=msg)

    def __repr__(self):
        return 'Драйвер[%s]' % self._device['ID_SERIAL_SHORT']
