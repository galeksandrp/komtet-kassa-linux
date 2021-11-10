import datetime
import functools
import hashlib
import hmac
import json
import re


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
