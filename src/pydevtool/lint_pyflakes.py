import re
from configparser import RawConfigParser

from doit.exceptions import TaskFailed
from rich.panel import Panel
from pyflakes.api import checkPath
from pyflakes.reporter import Reporter as FlakeReporter


# based on flake8 4.0:  src/flake8/plugins/pyflakes.py
FLAKE8_PYFLAKES_CODES = {
    "F401": "UnusedImport",
    "F402": "ImportShadowedByLoopVar",
    "F403": "ImportStarUsed",
    "F404": "LateFutureImport",
    "F405": "ImportStarUsage",
    "F406": "ImportStarNotPermitted",
    "F407": "FutureFeatureNotDefined",
    "F501": "PercentFormatInvalidFormat",
    "F502": "PercentFormatExpectedMapping",
    "F503": "PercentFormatExpectedSequence",
    "F504": "PercentFormatExtraNamedArguments",
    "F505": "PercentFormatMissingArgument",
    "F506": "PercentFormatMixedPositionalAndNamed",
    "F507": "PercentFormatPositionalCountMismatch",
    "F508": "PercentFormatStarRequiresSequence",
    "F509": "PercentFormatUnsupportedFormatCharacter",
    "F521": "StringDotFormatInvalidFormat",
    "F522": "StringDotFormatExtraNamedArguments",
    "F523": "StringDotFormatExtraPositionalArguments",
    "F524": "StringDotFormatMissingArgument",
    "F525": "StringDotFormatMixingAutomatic",
    "F541": "FStringMissingPlaceholders",
    "F601": "MultiValueRepeatedKeyLiteral",
    "F602": "MultiValueRepeatedKeyVariable",
    "F621": "TooManyExpressionsInStarredAssignment",
    "F622": "TwoStarredExpressions",
    "F631": "AssertTuple",
    "F632": "IsLiteral",
    "F633": "InvalidPrintSyntax",
    "F634": "IfTuple",
    "F701": "BreakOutsideLoop",
    "F702": "ContinueOutsideLoop",
    "F703": "ContinueInFinally",
    "F704": "YieldOutsideFunction",
    "F705": "ReturnWithArgsInsideGenerator",
    "F706": "ReturnOutsideFunction",
    "F707": "DefaultExceptNotLast",
    "F721": "DoctestSyntaxError",
    "F722": "ForwardAnnotationSyntaxError",
    "F723": "CommentAnnotationSyntaxError",
    "F811": "RedefinedWhileUnused",
    "F812": "RedefinedInListComp",
    "F821": "UndefinedName",
    "F822": "UndefinedExport",
    "F823": "UndefinedLocal",
    "F831": "DuplicateArgument",
    "F841": "UnusedVariable",
    "F901": "RaiseNotImplemented",
}

class FlakeRichReporter(FlakeReporter):
    def __init__(self, console, ignore, convert_flake8_code=False):
        self.print = console.print
        self.convert_flake8_code = convert_flake8_code
        if convert_flake8_code:
            self.ignore = set()
            for key in ignore:
                if item:=FLAKE8_PYFLAKES_CODES.get(key):
                    self.ignore.add(item)
                else:
                    self.ignore.add(key)
        else:
            self.ignore = set(ignore)
        self.reported = 0

    def flake(self, msg):
        if msg.__class__.__name__ in self.ignore:
            return
        self.reported += 1
        text = msg.message % msg.message_args
        self.print(f'{msg.filename}:{msg.lineno}:{msg.col+1} {msg.__class__.__name__} - {text}')

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
    def __init__(self, console, config_file=None, config_section="flake8", convert_flake8_code=False):
        ignore = []
        if config_file:
            config = RawConfigParser()
            config.read(config_file)
            if config.has_section(config_section):
                if ignore_str := config[config_section].get('ignore'):
                    for code in ignore_str.split(','):
                        code = code.strip()
                        if code and code[0] == 'F':  # ignore codestyle
                            ignore.append(code)
        self.flake_reporter = FlakeRichReporter(console, ignore=ignore,
                                                convert_flake8_code=convert_flake8_code)

    def __call__(self, fn):
        """execute pyflakes on a single file"""
        # checkPath() returns total flakes including ignored
        self.flake_reporter.reported = 0
        checkPath(fn, reporter=self.flake_reporter)
        if(self.flake_reporter.reported != 0):
            return TaskFailed('Check failed', report=True)
