import logging
from threading import Lock

from pyudev import Context, Monitor, MonitorObserver

from komtet_kassa_linux.driver import Driver
from komtet_kassa_linux.models import change_event


logger = logging.getLogger(__name__)


ATOL_VENDOR_ID = '2912'
SUBSYSTEM = 'usb'


class SingletonMeta(type):

    _instances = {}
    _lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class DeviceManager(metaclass=SingletonMeta):
    """ Менеджер подключенных устройств
    """

    _devices = {}

    def __init__(self):
        self._lock = Lock()

        context = Context()
        for device in context.list_devices(subsystem=SUBSYSTEM, ID_BUS=SUBSYSTEM,
                                           ID_VENDOR_ID=ATOL_VENDOR_ID):
            self._add(dict(device.properties))

        monitor = Monitor.from_netlink(context)
        monitor.filter_by(subsystem=SUBSYSTEM)
        self.observer = observer = MonitorObserver(monitor, self.__observer_handler)
        observer.start()

    def __del__(self):
        self.observer.stop()

    def __observer_handler(self, action, device):
        if action == 'add':
            self._add(dict(device))
        elif action == 'remove':
            self._remove(dict(device))

    def get(self, serial_number):
        return self._devices.get(serial_number)

    def list(self):
        return list(self._devices.keys())

    def list_of_devices(self):
        return list(self._devices.values())

    def _add(self, device):
        if not ({'DEVPATH', 'ID_SERIAL_SHORT', 'SUBSYSTEM', 'ID_VENDOR_ID'} <= set(device)):
            return

        if device['ID_VENDOR_ID'] != ATOL_VENDOR_ID:
            return

        with Driver(device) as driver:
            serial_number = driver.serial_number

        with self._lock:
            if serial_number not in self._devices:
                self._devices[serial_number] = {
                    'SERIAL_NUMBER': serial_number,
                    'ID_SERIAL_SHORT': device['ID_SERIAL_SHORT'],
                    'DEVPATH': device['DEVPATH'],
                    'SUBSYSTEM': device['SUBSYSTEM']
                }
                logger.info('Подключение устройства %s к порту %s',
                            serial_number, device['DEVPATH'])
                change_event.set()

    def _remove(self, device):
        if 'DEVPATH' not in device:
            return

        with self._lock:
            removed_serial_number = None
            for serial_number, dev in self._devices.items():
                if device['DEVPATH'] == dev['DEVPATH']:
                    removed_serial_number = serial_number

            if removed_serial_number:
                del self._devices[removed_serial_number]
                logger.info('Отключение устройства %s от порта %s',
                            removed_serial_number, device['DEVPATH'])
                change_event.set()
