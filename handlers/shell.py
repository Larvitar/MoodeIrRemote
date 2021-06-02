from typing import List, Dict
from handlers.base_handler import BaseActionHandler
import subprocess
import traceback
import sys


class ShellCommandsHandler(BaseActionHandler):

    def call(self, command_dict: Dict):
        command = command_dict['command']

        if not isinstance(command, list):
            command = [command]

        for _command in command:
            parsed = self._parse_command(_command)
            subprocess.run(parsed)

    def verify(self, command_dict):
        try:
            command = command_dict['command']

            if not isinstance(command, list):
                command = [command]

            for _command in command:
                self._parse_command(_command)
        except Exception as e:
            error = f'Error while parsing "{command_dict}"'
            error += '\n' + traceback.format_exc(e)
            sys.exit(1)

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

        parsed.remove('')
        return parsed
