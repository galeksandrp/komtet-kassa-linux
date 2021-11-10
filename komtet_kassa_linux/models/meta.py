import os.path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import scoped_session, sessionmaker

from komtet_kassa_linux import settings
from komtet_kassa_linux.libs.helpers import uncamelcase


__all__ = ['BaseModel', 'session']


class Model:

    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        return uncamelcase(cls.__name__)

    def save(self):
        self.session.add(self)
        self._flush()
        return self

    def update(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return self.save()

    def delete(self):
        self.session.delete(self)
        self._flush()

    def _flush(self):
        try:
            self.session.commit()
        except DatabaseError:
            self.session.rollback()
            raise

    class Query(object):
        def __get__(self, instance, model):
            return model.session.query(model)

    query = Query()


def model_base(session):

    class DBModel(Model):
        session = session

    return DBModel


session = scoped_session(sessionmaker(expire_on_commit=False))
BaseModel = declarative_base(cls=model_base(session))


def configure(config):
    dsn = 'sqlite:///' + config.DB_FILE

    engine = create_engine(dsn)
    session.configure(bind=engine)

    os.makedirs(os.path.dirname(config.DB_FILE), exist_ok=True)
    upgrade(dsn)


def upgrade(url):
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location",
                                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             'migrations'))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, 'head')


configure(settings)
