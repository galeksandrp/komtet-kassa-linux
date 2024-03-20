from sqlalchemy import Column, DateTime, String, Boolean

from .meta import BaseModel


class Printer(BaseModel):

    serial_number = Column(String, primary_key=True)
    name = Column(String)
    pos_key = Column(String(32), unique=True)
    pos_secret = Column(String(32), unique=True)
    devname = Column(String)
    ip = Column(String)
    is_online = Column(Boolean, default=False)
    session_closed_at = Column(DateTime)

    def __eq__(self, other):
        return self.serial_number == other

    def __repr__(self):
        return '<Printer[%s] %s>: %s:%s' % (self.devname, self.serial_number, self.pos_key,
                                            self.pos_secret)
