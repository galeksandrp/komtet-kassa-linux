import base64
import datetime
import functools
import hashlib
import hmac
import json
import re
from decimal import Decimal


def get_signature(secret, data):
    return hmac.new(secret.encode('utf-8'), data.encode('utf-8'), hashlib.md5).hexdigest()


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%S')
        if isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        return super(JSONEncoder, self).default(obj)


json_encode = functools.partial(json.dumps, cls=JSONEncoder)


def uncamelcase(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def to_decimal(value, rounding='.00'):
    return Decimal(value).quantize(Decimal(rounding))


def get_mark_code(value):
    '''
        Получение кода номенклатуры. Если передан в base64, выполняется преобразование в строку
    '''
    try:
        value = base64.b64decode(value).decode('utf-8')
    except Exception:
        pass

    return value


def prepare_dict(old_dict):
    '''
        Формируем новый словарь без ключей с пустым значениями.
        Выполнение данной операции необходимо для того, чтобы избежать ошибку от драйвера атол.
    '''
    new_dict = {}
    for key, value in old_dict.items():
        if value:
            new_dict.update({key: value})

    return new_dict
