from abc import ABC


class BaseActionHandler(ABC):

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance

    def call(self, command_dict):
        return NotImplementedError

    def verify(self, command_dict):
        return NotImplementedError
