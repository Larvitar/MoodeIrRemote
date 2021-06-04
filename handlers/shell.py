from typing import List, Dict
from handlers.base_handler import BaseActionHandler
from subprocess import run, DEVNULL


class ShellCommandsHandler(BaseActionHandler):

    def call(self, command_dict: Dict):
        command = command_dict['command']

        if not isinstance(command, list):
            command = [command]

        for _command in command:
            parsed = self._parse_command(_command)
            run(parsed, stdout=DEVNULL)

    def verify(self, command_dict):
        command = command_dict['command']

        if not isinstance(command, list):
            command = [command]

        for _command in command:
            self._parse_command(_command)

    @staticmethod
    def _parse_command(command: str) -> List[str]:
        command_parts: List[str] = command.split('"')

        parsed = []
        for index in range(len(command_parts)):
            if index % 2:
                # Inside ' " '
                parsed.append(command_parts[index])
            else:
                # Outside ' " '
                parsed.extend(command_parts[index].strip().split(' '))

        if '' in parsed:
            parsed.remove('')
        return parsed
