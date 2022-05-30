import logging
import os
import threading
import time

import psutil

from komtet_kassa_linux.devices.atol import DeviceManager
from komtet_kassa_linux.models import Printer, change_event as change_db_event

from .km import factory_km


logger = logging.getLogger(__name__)

LIMIT_USE_MEMORY = 75  # %


def wait(timeout, event=None):
    if not event:
        event = threading.Event()
    return event.wait(timeout)


class RepeatThread(threading.Thread):

    def __init__(self, name, func, interval=1):
        self.func = func
        self.interval = interval
        self._stop_event = threading.Event()
        threading.Thread.__init__(self, name=name)

    def run(self):
        while True:
            repeat_immediately = False
            try:
                repeat_immediately = self.func()
            except Exception:
                logger.exception('Error during a beat')

            interval = self.interval
            if repeat_immediately:
                interval = 0.05

            if wait(interval, self._stop_event):
                # self.func(is_only_send_report=True)
                break

    def stop(self):
        self._stop_event.set()


class KmManager:
    _km_threads = {}

    def __init__(self, db_path, interval=10, rent_station=None):
        self._interval = interval
        self._rent_station = rent_station
        self._device_manager = DeviceManager()

    def _start_km(self, printer):
        if printer.serial_number in self._km_threads:
            logger.warn(f'KM - {printer.serial_number}  was already run')
            self._stop_km(printer.serial_number)

        km = factory_km(printer, rent_station=self._rent_station)
        km_thread = self._km_threads[printer.serial_number] = RepeatThread(
            printer.serial_number, km.beat, self._interval
        )

        km_thread.start()
        logger.info('Start KM[%s] %s', printer.serial_number, printer.pos_key)
        return km_thread

    def _connect_device(self, device):
        printer = Printer.query.filter_by(serial_number=device['SERIAL_NUMBER']).first()
        if printer:
            printer.update(devname=device['DEVPATH'])
            self._start_km(printer)

    def start(self):
        # Запуск виртуальных принтеров
        for printer in Printer.query.filter(Printer.is_virtual):
            self._start_km(printer)

        # Запуск подключенных Атолов
        for device in self._device_manager.list_of_devices():
            self._connect_device(device)

    def _stop_km(self, serial_number, is_wait_complete=True):
        km_thread = self._km_threads.pop(serial_number, None)
        if km_thread:
            km_thread.stop()
            if is_wait_complete:
                km_thread.join()
                logger.info('Stop KM[%s]', serial_number)
        elif Printer.query.filter_by(serial_number=serial_number).first():
            logger.warn('KM[%s] is not found', serial_number)

        return km_thread

    def _disconnect_device(self, devpath):
        printer = Printer.query.filter_by(devname=devpath).first()
        if printer:
            self._stop_km(printer.serial_number, is_wait_complete=True)
            printer.update(devname=None)

    def stop(self):
        # Отправка сигнала завершения КМ
        stopped_km_threads = {
            serial_number: self._stop_km(serial_number, is_wait_complete=False)
            for serial_number in list(self._km_threads.keys())
        }

        # ожидание завершения всех КМ
        for serial_number, km_thread in stopped_km_threads.items():
            if km_thread:
                km_thread.join()
                logger.info('Stop KM[%s]', serial_number)

        for printer in Printer.query:
            printer.update(devname=None)

    def sync(self):
        registrated_devices = {
            printer.serial_number: printer
            for printer in Printer.query.filter(Printer.is_online)
        }
        connected_devices = self._device_manager.list() + [
            serial_number for serial_number, printer in registrated_devices.items()
            if printer.is_virtual  # Добавляем виртуальные принтеры в список подключенных устройств
        ]

        # Останавливаем устройства удаленные из web-интерфейса
        for serial_number in (set(self._km_threads) - (set(registrated_devices) & set(connected_devices))):
            self._stop_km(serial_number)

        # Запускем устройства добавленные в web-интерфейс
        for serial_number in ((set(registrated_devices) & set(connected_devices)) - set(self._km_threads)):
            self._start_km(registrated_devices[serial_number])

    def loop(self):
        logger.info('Start KMManager')
        self.start()

        process = psutil.Process(os.getpid())
        try:
            while not getattr(self, '_stop_loop', False):
                if process.memory_percent() > LIMIT_USE_MEMORY:
                    logger.warning('Stop KMManager: leak memory')
                    break
                if change_db_event.isSet():
                    change_db_event.clear()
                    self.sync()
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

        self.stop()
        logger.info('Stop KMManager')
