import re

from pyflakes.api import checkPath
from pyflakes.reporter import Reporter as FlakeReporter
import pycodestyle
from flake8.main.application import Application as Flake8App
from flake8.checker import FileChecker
from flake8.formatting.default import Default as _Flake8Formatter


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

    def __init__(self, options):
        super().__init__(options)
        self._fmt = pycodestyle.REPORT_FORMAT.get(
            options.format.lower(), options.format)

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

        self.console.print(self._fmt % {
            'path': self.filename,
            'row': self.line_offset + line_number, 'col': offset + 1,
            'code': code, 'text': text[5:],
        })
        return code


class Flake8Formatter(_Flake8Formatter):
    def write(self, line, source):
        self.console.print(line, source)


##################################################################
### helper to create doit tasks

class LintPyflakes():
    """pyflakes"""
    def __init__(self, console):
        self.flake_reporter = FlakeRichReporter(console)

    def __call__(self, fn):
        """execute pyflakes on a single file"""
        flake_result = checkPath(fn, reporter=self.flake_reporter)
        return flake_result == 0


class LintCodeStyle():
    """pycodestyle"""
    def __init__(self, console, config_file=None):
        style = pycodestyle.StyleGuide(config_file=config_file)
        style_reporter = style.init_report(CodeStyleRichReporter)
        style_reporter.console = console
        self.style = style

    def __call__(self, fn):
        """execute pyflakes and pycodestyle on single file"""
        style_result = self.style.input_file(fn)
        return style_result==0


# FIXME: this is way slower compared to using flake8 CLI directly.
# flake8 uses all processors available, doit multiprocessing is failing due non-pickable
# thread.RLock reference. rich?
class LintFlake8():
    """flake8"""
    def __init__(self, console, config_file=None):
        self.console = console
        self.app = Flake8App()
        self.app.initialize([])
        self.checks = self.app.file_checker_manager.checks.to_dictionary()

        # It was supposed to be a plugin
        # https://flake8.pycqa.org/en/latest/plugin-development/index.html
        formatter = Flake8Formatter(self.app.options)
        formatter.console = console
        self.guide = self.app.file_checker_manager.style_guide.default_style_guide
        self.guide.formatter = formatter

    def excluded(self, fn):
        return self.app.file_checker_manager.is_path_excluded(fn)

    def __call__(self, fn):
        """execute pyflakes and pycodestyle on single file"""
        manager = self.app.file_checker_manager
        checker = FileChecker(str(fn), self.checks, manager.options)
        filename, results, stats = checker.run_checks()
        success = True
        for (error_code, line_number, column, text, physical_line) in results:
            has_reported_error = self.guide.handle_error(
                code=error_code,
                filename=filename,
                line_number=line_number,
                column_number=column,
                text=text,
                physical_line=physical_line,
            )
            if has_reported_error:
                success = False
        return success
