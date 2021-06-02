from abc import ABC


class BaseActionHandler(ABC):

    def call(self, command):
        return NotImplementedError

    def verify(self, command):
        return NotImplementedError
