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

    def start_km(self, printer):
        ''' Запуск одного устройства
        '''
        if printer.is_virtual:
            # Запуск виртуальных принтеров
            pass
        elif printer.ip:
            # Запуск принтеров по tcp
            device = self._device_manager.connect_tcp_device(printer.ip)
            printer.serial_number = device.serial_number
        else:
            # Запуск принтеров по usb
            device = self._device_manager.get(printer.serial_number)
            if not device:
                return

        if printer.serial_number in self._km_threads:
            logger.warn(f'KM - {printer.serial_number}  was already run')
            self.stop_km(printer.serial_number)

        km = factory_km(printer, rent_station=self._rent_station)
        km_thread = self._km_threads[printer.serial_number] = RepeatThread(
            printer.serial_number, km.beat, self._interval
        )

        km_thread.start()
        printer.update(is_online=True)

        logger.info('Start KM[%s] %s', printer.serial_number, printer.pos_key)

        return km_thread

    def start(self, is_ingnore_online=False):
        ''' Запуск всех устройств зарегистрированных в базе
            Поднимаем всех из базы и запускаем
            @is_ingnore_online: игнорировать со статусом is_online. Для запуска при синхронизации.
        '''
        for printer in Printer.query.all():
            if printer.is_online and is_ingnore_online:
                continue

            self.start_km(printer)

    def stop_km(self, serial_number, is_wait_complete=True):
        ''' Остановка треда
        '''
        km_thread = self._km_threads.pop(serial_number, None)
        if km_thread:
            km_thread.stop()
            if is_wait_complete:
                km_thread.join()
                logger.info('Stop KM[%s]', serial_number)

        if printer := Printer.query.filter_by(serial_number=serial_number).first():
            printer.update(devname=None, is_online=False)

        return km_thread

    def stop(self):
        ''' Остановка всех запущенных тредов
        '''
        # Отправка сигнала завершения КМ
        stopped_km_threads = {
            serial_number: self.stop_km(serial_number, is_wait_complete=False)
            for serial_number in list(self._km_threads.keys())
        }

        # ожидание завершения всех КМ
        for serial_number, km_thread in stopped_km_threads.items():
            self._device_manager.remove_by_serial_number(serial_number)
            if km_thread:
                km_thread.join()
                logger.info('Stop KM[%s]', serial_number)

    def sync(self):
        # Все идентифицируются по serial_number
        db_printers = {printer.serial_number: printer for printer in Printer.query.all()}
        connected_devices = self._device_manager.list()

        # Есть в подключенных, но нет в базе - отключаем
        in_devices_not_in_db = set(connected_devices) - set(db_printers)
        for serial_number in in_devices_not_in_db:
            self.stop_km(serial_number)

        # Стартуем все созданные в базе, но не запущенные
        self.start(is_ingnore_online=True)

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
