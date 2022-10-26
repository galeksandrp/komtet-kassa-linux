import logging
from threading import Lock
from dataclasses import dataclass

from pyudev import Context, Monitor, MonitorObserver

from .driver import Driver
from komtet_kassa_linux.models import change_event


logger = logging.getLogger(__name__)


ATOL_VENDOR_ID = '2912'
SUBSYSTEM = 'usb'

@dataclass
class USBDevice:
    id: str
    serial_number: str = None
    devpath: str = None
    vendor_id: str = None

@dataclass
class TCPDevice:
    id: str
    serial_number: str = None
    ip_address: str = None


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
        self.connect_usb_devices()

    def connect_usb_devices(self):
        ''' Сканим порты, добавляем в список _devices
            и ставим observer на подключение / отключение
        '''
        context = Context()
        for device in context.list_devices(subsystem=SUBSYSTEM, ID_BUS=SUBSYSTEM, ID_VENDOR_ID=ATOL_VENDOR_ID):

            self._add(
                USBDevice(
                    id=device.properties.get('ID_SERIAL_SHORT'),
                    devpath=device.properties.get('DEVPATH'),
                    vendor_id=device.properties.get('ID_VENDOR_ID')
                )
            )

        monitor = Monitor.from_netlink(context)
        monitor.filter_by(subsystem=SUBSYSTEM)
        self.observer = observer = MonitorObserver(monitor, self.__observer_handler)
        observer.start()

    def connect_tcp_device(self, ip):
        ''' Устройства по ip подключаем по одному, поднимая из базы
        '''

        return self._add(
            TCPDevice(
                id=ip,
                ip_address=ip
            )
        )

    def __del__(self):
        self.observer.stop()

    def __observer_handler(self, action, device):
        if action == 'add':
            self._add(
                USBDevice(
                    id=device.properties.get('ID_SERIAL_SHORT'),
                    devpath=device.properties.get('DEVPATH'),
                    vendor_id=device.properties.get('ID_VENDOR_ID')
                )
            )
        elif action == 'remove':
            self._remove_by_devpath(device.properties.get('DEVPATH'))

        change_event.set()

    def get(self, serial_number):
        return self._devices.get(serial_number)

    def list(self):
        return list(self._devices.keys())

    def list_of_devices(self):
        return list(self._devices.values())

    def _add(self, device):
        if isinstance(device, USBDevice) and device.vendor_id != ATOL_VENDOR_ID:
            return

        with Driver(device) as driver:
            serial_number = driver.serial_number

        with self._lock:
            if serial_number not in self._devices:
                device.serial_number = serial_number
                self._devices[serial_number] = device
                logger.info('Connect device %s', serial_number)

        return self._devices[serial_number]

    def remove_by_serial_number(self, serial_number):
        if self._devices.get(serial_number):
            del self._devices[serial_number]
            logger.info('Disconnect device %s', serial_number)

    def _remove_by_devpath(self, devpath):
        with self._lock:
            removed_serial_number = None
            for serial_number, device in self._devices.items():
                if isinstance(device, USBDevice) and device.devpath == devpath:
                    removed_serial_number = serial_number
                    break

            if removed_serial_number:
                self.remove_by_serial_number(removed_serial_number)
