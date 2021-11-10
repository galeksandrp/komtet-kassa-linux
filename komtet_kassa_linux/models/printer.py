from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.hybrid import hybrid_property

from komtet_kassa_linux.libs import VIRTUAL_PRINTER_PREFIX

from .meta import BaseModel


class Printer(BaseModel):

    serial_number = Column(String, primary_key=True)
    name = Column(String)
    pos_key = Column(String(32), unique=True)
    pos_secret = Column(String(32), unique=True)
    devname = Column(String)
    session_closed_at = Column(DateTime)

    @hybrid_property
    def is_virtual(self):
        return self.serial_number.startswith(VIRTUAL_PRINTER_PREFIX)

    @is_virtual.expression
    def is_virtual(self):
        return self.serial_number.ilike(VIRTUAL_PRINTER_PREFIX + '%')

    @hybrid_property
    def is_online(self):
        return bool(self.devname) or self.is_virtual

    @is_online.expression
    def is_online(self):
        return self.devname.isnot(None) | self.is_virtual

    def __eq__(self, other):
        return self.serial_number == other

    def __repr__(self):
        return '<Printer[%s] %s>: %s:%s' % (self.devname, self.serial_number, self.pos_key,
                                            self.pos_secret)
