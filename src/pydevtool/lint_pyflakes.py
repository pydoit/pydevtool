import re

from rich.panel import Panel

from pyflakes.api import checkPath
from pyflakes.reporter import Reporter as FlakeReporter


class FlakeRichReporter(FlakeReporter):
    def __init__(self, console):
        self.print = console.print

    def flake(self, msg):
        text = msg.message % msg.message_args
        self.print(f'{msg.filename}:{msg.lineno}:{msg.col+1} {text}')

    def syntaxError(self, filename, msg, lineno, offset, text):
        """
        There was a syntax error in C{filename}.

        @param filename: The path to the file with the syntax error.
        @ptype filename: C{unicode}
        @param msg: An explanation of the syntax error.
        @ptype msg: C{unicode}
        @param lineno: The line number where the syntax error occurred.
        @ptype lineno: C{int}
        @param offset: The column on which the syntax error occurred, or None.
        @ptype offset: C{int}
        @param text: The source code containing the syntax error.
        @ptype text: C{unicode}
        """
        line = text.splitlines()[-1]
        if offset is not None:
            error = '%s:%d:%d: %s' % (filename, lineno, offset, msg)
        else:
            error = '%s:%d: %s' % (filename, lineno, msg)
        if offset is not None:
            caret = re.sub(r'\S', ' ', line[:offset - 1])
        self.print(Panel(f'{error}\n{line}\n{caret}^', title="Syntax Error"))

    def unexpectedError(self, filename, msg):
        """
        An unexpected error occurred trying to process C{filename}.

        @param filename: The path to a file that we could not process.
        @ptype filename: C{unicode}
        @param msg: A message explaining the problem.
        @ptype msg: C{unicode}
        """
        self.print(Panel(f'{filename}: {msg}', title="Unexpected Error"))


class LintPyflakes():
    """pyflakes"""
    def __init__(self, console):
        self.flake_reporter = FlakeRichReporter(console)

    def __call__(self, fn):
        """execute pyflakes on a single file"""
        flake_result = checkPath(fn, reporter=self.flake_reporter)
        return flake_result == 0
