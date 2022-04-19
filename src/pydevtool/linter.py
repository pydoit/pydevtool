import re

from pyflakes.api import checkPath
from pyflakes.reporter import Reporter as FlakeReporter
import pycodestyle



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



class CodeStyleRichReporter(pycodestyle.BaseReport):
    console = None # must be assigned after creation

    def error(self, line_number, offset, text, check):
        """Report an error, according to options."""
        code = text[:4]
        if self._ignore_code(code):
            return
        if code in self.counters:
            self.counters[code] += 1
        else:
            self.counters[code] = 1
            self.messages[code] = text[5:]
        # Don't care about expected errors or warnings
        if code in self.expected:
            return
        if self.print_filename and not self.file_errors:
            print(self.filename)
        self.file_errors += 1
        self.total_errors += 1
        return code



##################################################################
### helper to create doit tasks

class Linter():
    """pyflakes + pycodestyle"""
    def __init__(self, console, config_file=None):
        style = pycodestyle.StyleGuide(config_file=config_file)
        style_reporter = style.init_report(CodeStyleRichReporter)
        style_reporter.console = console
        self.style = style
        self.flake_reporter = FlakeRichReporter(console)

    def __call__(self, fn):
        """execute pyflakes and pycodestyle on single file"""
        flake_result = checkPath(fn, reporter=self.flake_reporter)
        style_result = self.style.input_file(fn)
        return flake_result==0 and style_result==0
