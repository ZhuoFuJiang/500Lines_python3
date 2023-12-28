MISSING = object()


class Base(object):
    """基础类，class和instance都继承于此"""
    def __init__(self, cls, fields):
        self.cls = cls
        self._fields = fields

    def read_attr(self, fieldname):
        return self._read_dict(fieldname)

    def write_attr(self, fieldname, value):
        self._write_dict(fieldname, value)

    def isinstance(self, cls):
        return self.cls.issubclass(cls)

    def callmethod(self, methname, *args):
        meth = self.cls._read_from_class(methname)
        return meth(self, *args)

    def _read_dict(self, fieldname):
        return self._fields.get(fieldname, MISSING)

    def _write_dict(self, fieldname, value):
        self._fields[fieldname] = value


class Class(Base):
    def __init__(self, name, base_class, fields, metaclass):
        Base.__init__(self, metaclass, fields)
        self.name = name
        self.base_class = base_class


class Instance(Base):
    def __init__(self, cls):
        assert isinstance(cls, Class)
        Base.__init__(self, cls, {})


OBJECT = Class(name="object", base_class=None, fields={}, metaclass=None)
TYPE = Class(name="type", base_class=OBJECT, fields={}, metaclass=None)

TYPE.cls = TYPE
OBJECT.cls = TYPE
