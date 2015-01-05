import shlex

from subprocess import Popen, PIPE

import psutil
from django.utils import six
from django.utils.encoding import force_text, force_bytes


class CommandError(Exception):
    pass


class CommandExecutionError(CommandError):
    def __init__(self, code, stderr, command):
        lines = (six.text_type(line) for line in stderr.splitlines())
        message = u'code: {0} stderr: {1}. Command: {2}'.format(
            code, u' '.join(lines), repr(command.get_command()))
        super(CommandExecutionError, self).__init__(message)
        self.code = code
        self.stderr = stderr
        self.command = command


class CommandParameterError(CommandError):
    pass


class Command(object):
    pid = None
    command = 'true'
    ignore_output = True
    fail_silently = False
    required_parameters = None

    def __init__(self, **kwargs):
        self.parameters = kwargs
        if not self.validate_parameters():
            raise CommandParameterError(
                'Parameter(s) missing, required parameters: {0}'.format(
                    ', '.join(self.required_parameters)))

    def execute(self, ignore_output=None, fail_silently=None, **kwargs):
        command = self.get_command()
        ignore_output = ignore_output if ignore_output is not None else self.ignore_output
        fail_silently = fail_silently if fail_silently is not None else self.fail_silently

        # Don't automatically merge with os.environ for security reasons.
        # Make this forwarding explicit rather than implicit.
        environ = kwargs.pop('environ', None)
        shell = kwargs.pop('shell', False)

        try:
            process = Popen(
                command,
                shell=shell,
                universal_newlines=True,
                env=environ,
                stdout=PIPE,
                stderr=PIPE,
                stdin=PIPE,
            )
            self.pid = process.pid

            stdout, stderr = process.communicate()
        except OSError as exc:
            raise CommandExecutionError(1, six.text_type(exc), self)

        if not fail_silently and (stderr or process.returncode != 0):
            raise CommandExecutionError(process.returncode, stderr, self)

        return True if ignore_output else self.handle_output(stdout)

    def cleanup(self):
        if self.pid is None:
            return True

        try:
            process = psutil.Process(self.pid)
            process.kill()
        except:
            pass

        return True

    def validate_parameters(self):
        return all(k in self.parameters for k in self.required_parameters or [])

    def get_parameters(self):
        return filter(None, self.parameters)

    def get_command(self):
        command = self.command.format(**self.get_parameters())
        if six.PY2:
            return shlex.split(force_bytes(command))
        return shlex.split(force_text(command))

    def handle_output(self, output):
        return output


def expand_args(command):
    """Parses command strings and returns a Popen-ready list."""
    if isinstance(command, (list, set, frozenset, tuple)):
        return command

    splitter = shlex.shlex(command)
    splitter.whitespace = '|'
    splitter.whitespace_split = True
    command = []

    while True:
        token = splitter.get_token()
        if token:
            command.append(token)
        else:
            break

    command = list(map(shlex.split, command))

    return command
