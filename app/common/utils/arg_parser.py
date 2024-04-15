import argparse
from typing import Callable, Iterable


class ProgramCommandArgument:
    def __init__(self, *,
                 name: str,
                 data_type,
                 help_str: str,
                 optional: bool = False,
                 long_string: bool = False,
                 choices: Iterable[str] | None = None):
        self.__name = name

        self.__kwargs = {
            'type': data_type,
            'help': help_str,
        }

        if choices:
            self.__kwargs.update({
                'choices': choices
            })

        if optional:
            self.__kwargs.update({
                'nargs': '?',
                'default': None
            })
        elif long_string:
            self.__kwargs.update({
                'nargs': '+'
            })

    @property
    def name(self):
        return self.__name

    @property
    def kwargs(self):
        return self.__kwargs


class ProgramCommand:
    def __init__(self, command: str, help_str: str,
                 *arguments: ProgramCommandArgument,
                 aliases: Iterable[str] | None = None,
                 callback: Callable[[...], int] | None = None):
        self.__command = command
        self.__help_str = help_str
        self.__arguments = arguments
        self.__aliases = aliases
        self.__callback = callback

    @property
    def command(self):
        return self.__command

    @property
    def help_str(self):
        return self.__help_str

    @property
    def arguments(self):
        return self.__arguments

    @property
    def callback(self):
        return self.__callback

    @property
    def aliases(self):
        return self.__aliases


class ProgramArgumentParser:
    def __init__(self, app_name: str):
        self.__parser = argparse.ArgumentParser(
            prog=app_name
        )
        self.__sub_parser = self.__parser.add_subparsers(help='commands')

    def __add_command(self, command: str, help_str: str,
                      *arguments: ProgramCommandArgument,
                      aliases: Iterable[str] | None,
                      callback: Callable[[...], int] | None):

        commands = [command, *(aliases if aliases else [])]

        for cmd in commands:
            parser = self.__sub_parser.add_parser(cmd, help=help_str)
            for argument in arguments:
                parser.add_argument(argument.name, **argument.kwargs)
            if callback:
                parser.set_defaults(func=callback)

    def add_command(self, program_command: ProgramCommand):
        self.__add_command(program_command.command,
                           program_command.help_str,
                           *program_command.arguments,
                           aliases=program_command.aliases,
                           callback=program_command.callback)

    def add_commands(self, *program_commands: ProgramCommand):
        for command in program_commands:
            self.add_command(command)

    def parse(self, *args, **kwargs):
        return self.__parser.parse_args(*args, **kwargs)

    def execute(self, *args, **kwargs) -> tuple[bool, int]:
        context = self.parse(*args, **kwargs)
        if hasattr(context, 'func'):
            return True, context.func(context)
        else:
            return False, -1
