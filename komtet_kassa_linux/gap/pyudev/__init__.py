import os
import json
from collections import namedtuple

class Context():
    def utilsPropertiesToDevice(self, properties):
        UtilsDevice = namedtuple('UtilsDevice', 'properties')
        return UtilsDevice(properties)

    def list_devices(self, subsystem, ID_BUS, ID_VENDOR_ID):
        with open(os.path.join(os.getcwd(), 'komtet_kassa_linux_devices.json')) as utilsKKLDevices:
            return list(map(self.utilsPropertiesToDevice, json.load(utilsKKLDevices)))

class Monitor():
    def from_netlink(context):
        return Monitor()

    def filter_by(self, subsystem):
        pass

class MonitorObserver():
    def __init__(self, monitor, observer_handler):
        pass

    def start(self):
        pass

    def stop(self):
        pass
