class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class BaseActionHandler(metaclass=Singleton):

    def call(self, command_dict):
        return NotImplementedError

    def verify(self, command_dict):
        return NotImplementedError
