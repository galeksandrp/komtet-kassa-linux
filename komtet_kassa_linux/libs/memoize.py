class memoize_property(object):

    def __init__(self, fget):
        self.fget = fget
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self

        result = self.fget(obj)
        obj.__dict__[self.__name__] = result
        return result
