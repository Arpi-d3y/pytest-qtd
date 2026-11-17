from __future__ import annotations

from collections import namedtuple
from contextlib import contextmanager
import datetime
import re
from _pytest._code.code import TerminalRepr, ReprFileLocation
import pytest
from pytestqt.qt_compat import qt_api
from pytestqt.utils import get_marker


class QtLoggingPlugin:
    """
    Plugin responsible for installing a QtMessageHandler before each
    test and augment reporting if the test failed with the messages captured.
    """

    LOG_FAIL_OPTIONS = ["NO", "CRITICAL", "WARNING", "DEBUG", "INFO"]

    def __init__(self, config):
        self.config = config

    def pytest_runtest_setup(self, item):
        if get_marker(item, "no_qt_log"):
            return
        log_ignore_marker = get_marker(item, "qt_log_ignore")
        if log_ignore_marker:
            if not set(log_ignore_marker.kwargs).issubset({"extend"}):
                raise ValueError(
                    "Invalid keyword arguments in {!r} for qt_log_ignore mark.".format(
                        log_ignore_marker.kwargs
                    )
                )
            if log_ignore_marker.kwargs.get("extend", True):
                config_regexes = self.config.getini("qt_log_ignore")
                ignore_regexes = config_regexes + list(log_ignore_marker.args)
            else:
                ignore_regexes = log_ignore_marker.args
        else:
            ignore_regexes = self.config.getini("qt_log_ignore")
        item.qt_log_capture = _QtMessageCapture(ignore_regexes)
        item.qt_log_capture._start()

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_makereport(self, item, call):
        """Add captured Qt messages to test item report if the call failed."""
        report = yield
        if not hasattr(item, "qt_log_capture"):
            return report

        if call.when == "call":
            log_fail_level = self._get_log_fail_level(item)
            if report.outcome != "failed":
                self._fail_report_on_matching_records(item, report, log_fail_level)
            if not report.passed:
                self._add_captured_messages_section(item, report)

            item.qt_log_capture._stop()
            del item.qt_log_capture
        return report

    def _get_log_fail_level(self, item):
        """
        Return the log level that makes a test fail: the value given to the
        ``qt_log_level_fail`` marker if present, otherwise the ini option.
        """
        fail_level_marker = get_marker(item, "qt_log_level_fail")
        if fail_level_marker:
            log_fail_level = fail_level_marker.args[0]
        else:
            log_fail_level = self.config.getini("qt_log_level_fail")
        assert log_fail_level in QtLoggingPlugin.LOG_FAIL_OPTIONS
        return log_fail_level

    def _fail_report_on_matching_records(self, item, report, log_fail_level):
        """
        Make the test fail if any captured record matches ``log_fail_level``
        (and is not ignored) or is a ``qt.modeltest`` warning.
        """
        for rec in item.qt_log_capture.records:
            is_modeltest_error = (
                rec.context is not None
                and rec.context.category == "qt.modeltest"
                and rec.matches_level("WARNING")
            )
            matches_fail_level = rec.matches_level(log_fail_level) and not rec.ignored
            if matches_fail_level or is_modeltest_error:
                report.outcome = "failed"
                if report.longrepr is None:
                    report.longrepr = _QtLogLevelErrorRepr(
                        item, log_fail_level, is_modeltest_error
                    )
                break

    def _add_captured_messages_section(self, item, report):
        """
        Add the captured Qt messages as a section of the terminal
        representation of a failed test.
        """
        long_repr = getattr(report, "longrepr", None)
        if not hasattr(long_repr, "addsection"):  # pragma: no cover
            return
        log_format = self.config.getoption("qt_log_format")
        context_format = None
        if log_format is None:
            context_format = (
                "{rec.context.file}:{rec.context.function}:{rec.context.line}:\n"
            )
            log_format = "    {rec.type_name}: {rec.message}"

        lines = []
        for rec in item.qt_log_capture.records:
            suffix = " (IGNORED)" if rec.ignored else ""

            if context_format is not None and _has_source_context(rec):
                context_line = context_format.format(rec=rec)
                lines.append(context_line)
            else:
                log_format = log_format.lstrip()

            line = log_format.format(rec=rec) + suffix
            lines.append(line)
        if lines:
            long_repr.addsection("Captured Qt messages", "\n".join(lines))


def _has_source_context(rec: Record) -> bool:
    """
    Return True if the record carries any information about where in the
    source code the Qt message was emitted (file, function or line).
    """
    context = rec.context
    if context is None:
        return False
    return context.file is not None or context.function is not None or context.line != 0


class _QtMessageCapture:
    """
    Captures Qt messages when its `handle` method is installed using
    qInstallMessageHandler, and stores them into `records` attribute.

    :attr _records: list of Record instances.
    :attr _ignore_regexes: list of regexes (as strings) that define if a record
        should be ignored.
    """

    def __init__(self, ignore_regexes):
        self._records: list[Record] = []
        self._ignore_regexes = ignore_regexes or []
        self._previous_handler = None

    def _start(self):
        """
        Start receiving messages from Qt.
        """
        previous_handler = qt_api.QtCore.qInstallMessageHandler(
            self._handle_with_context
        )
        self._previous_handler = previous_handler

    def _stop(self):
        """
        Stop receiving messages from Qt, restoring the previously installed
        handler.
        """
        qt_api.QtCore.qInstallMessageHandler(self._previous_handler)

    @contextmanager
    def disabled(self):
        """
        Context manager that temporarily disables logging capture while
        inside it.
        """
        self._stop()
        try:
            yield
        finally:
            self._start()

    _Context = namedtuple("_Context", "file function line category")

    def _append_new_record(self, msg_type, message, context):
        """
        Creates a new Record instance and stores it.

        :param msg_type: Qt message typ
        :param message: message string, if bytes it will be converted to str.
        :param context: QMessageLogContext object or None
        """

        def to_unicode(s):
            if isinstance(s, bytes):
                s = s.decode("utf-8", "replace")
            return s

        message = to_unicode(message)

        ignored = False
        for regex in self._ignore_regexes:
            if re.search(regex, message) is not None:
                ignored = True
                break

        if context is not None:
            context = self._Context(
                to_unicode(context.file),
                to_unicode(context.function),
                context.line,
                to_unicode(context.category),
            )

        self._records.append(Record(msg_type, message, ignored, context))

    def _handle_with_context(self, msg_type, context, message):
        """
        Method to be installed using qInstallMessageHandler,
        stores each message into the `_records` attribute.
        """
        self._append_new_record(msg_type, message, context=context)

    @property
    def records(self) -> list[Record]:
        """Access messages captured so far."""
        return self._records[:]


class Record:
    """Hold information about a message sent by one of Qt log functions.

    :ivar str message: message contents.
    :ivar Qt.QtMsgType type: enum that identifies message type
    :ivar str type_name: ``type`` as string: ``"QtInfoMsg"``, ``"QtDebugMsg"``,
        ``"QtWarningMsg"`` or ``"QtCriticalMsg"``.
    :ivar str log_type_name:
        type name similar to the logging package: ``INFO``, ``DEBUG``,
        ``WARNING`` and ``CRITICAL``.
    :ivar datetime.datetime when: when the message was captured
    :ivar bool ignored: If this record matches a regex from the "qt_log_ignore"
        option.
    :ivar context: a namedtuple containing the attributes ``file``,
        ``function``, ``line``. Can be None if no context is available for the
        message.
    """

    def __init__(self, msg_type, message, ignored, context):
        self._type = msg_type
        self._message = message
        self._type_name = self._get_msg_type_name(msg_type)
        self._log_type_name = self._get_log_type_name(msg_type)
        self._when = datetime.datetime.now()
        self._ignored = ignored
        self._context = context

    message = property(lambda self: self._message)
    type = property(lambda self: self._type)
    type_name = property(lambda self: self._type_name)
    log_type_name = property(lambda self: self._log_type_name)
    when = property(lambda self: self._when)
    ignored = property(lambda self: self._ignored)
    context = property(lambda self: self._context)

    @classmethod
    def _get_msg_type_name(cls, msg_type):
        """
        Return a string representation of the given QtMsgType enum
        value.
        """
        if not getattr(cls, "_type_name_map", None):
            cls._type_name_map = {
                qt_api.QtCore.QtMsgType.QtDebugMsg: "QtDebugMsg",
                qt_api.QtCore.QtMsgType.QtWarningMsg: "QtWarningMsg",
                qt_api.QtCore.QtMsgType.QtCriticalMsg: "QtCriticalMsg",
                qt_api.QtCore.QtMsgType.QtFatalMsg: "QtFatalMsg",
                qt_api.QtCore.QtMsgType.QtInfoMsg: "QtInfoMsg",
            }
        return cls._type_name_map[msg_type]

    @classmethod
    def _get_log_type_name(cls, msg_type):
        """
        Return a string representation of the given QtMsgType enum
        value in the same style used by the builtin logging package.
        """
        if not getattr(cls, "_log_type_name_map", None):
            cls._log_type_name_map = {
                qt_api.QtCore.QtMsgType.QtDebugMsg: "DEBUG",
                qt_api.QtCore.QtMsgType.QtWarningMsg: "WARNING",
                qt_api.QtCore.QtMsgType.QtCriticalMsg: "CRITICAL",
                qt_api.QtCore.QtMsgType.QtFatalMsg: "FATAL",
                qt_api.QtCore.QtMsgType.QtInfoMsg: "INFO",
            }
        return cls._log_type_name_map[msg_type]

    def matches_level(self, level):
        assert level in QtLoggingPlugin.LOG_FAIL_OPTIONS
        if level == "NO":
            return False
        elif level == "INFO":
            return self.log_type_name in ("INFO", "DEBUG", "WARNING", "CRITICAL")
        elif level == "DEBUG":
            return self.log_type_name in ("DEBUG", "WARNING", "CRITICAL")
        elif level == "WARNING":
            return self.log_type_name in ("WARNING", "CRITICAL")
        elif level == "CRITICAL":
            return self.log_type_name in ("CRITICAL",)
        else:  # pragma: no cover
            raise ValueError(f"log_fail_level unknown: {level}")


class _QtLogLevelErrorRepr(TerminalRepr):
    """
    TerminalRepr of a test which didn't fail by normal means, but emitted
    messages at or above the allowed level.
    """

    def __init__(self, item, level, is_modeltest_error):
        if is_modeltest_error:
            msg = "Qt modeltester errors"
        else:
            msg = "Failure: Qt messages with level {0} or above emitted"
        path, line_index, _ = item.location
        self.fileloc = ReprFileLocation(
            path, lineno=line_index + 1, message=msg.format(level.upper())
        )
        self.sections = []

    def addsection(self, name, content, sep="-"):
        self.sections.append((name, content, sep))

    def toterminal(self, out):
        self.fileloc.toterminal(out)
        for name, content, sep in self.sections:
            out.sep(sep, name)
            out.line(content)
