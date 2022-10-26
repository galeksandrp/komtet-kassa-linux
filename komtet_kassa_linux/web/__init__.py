import os

from flask import Flask
from sqlalchemy.exc import DatabaseError

from komtet_kassa_linux import settings
from komtet_kassa_linux.models import session


app = Flask('raspberry_km',
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['is_lease'] = bool(settings.LEASE_STATION)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = settings.SECRET_KEY

from komtet_kassa_linux.web import routes  # isort:skip


@app.teardown_appcontext
def close_db(error):
    session.bind.connect().close()


@app.after_request
def session_commit(response):
    if response.status_code < 400:
        try:
            session.commit()
        except DatabaseError:
            session.remove()
            raise

    return response


def run():
    params = {}

    if os.environ.get('DEBUG', 'false').lower() in ['1', 'on', 'yes', 'y', 'true']:
        params['host'] = '0.0.0.0'

    app.run(**params)


if __name__ == '__main__':
    run()
