"""
doas -su mylife.root
Base Framework - Perhaps

This module owns the shell, command registry, the inject/patcher extension
points, flags, the bootstrap sequence and the pseudo-user account helpers.

Design notes
------------
* Importing this module must not do I/O or start background services.  The
  boot text is printed by :func:`init` (called by the application entry
  point), not at import time.
* An inject callback may return ``None`` (do nothing) or a
  :class:`Handled`/:class:`Cancel` marker.  Anything else is a programming
  error and is reported by ``run_injects``.  This replaces the old
  ``(-1, callable)`` magic-list convention which was easy to get wrong.
* Patchers are registered separately from injects and are chained: each
  receives the previous value and may return a new one (``None`` = unchanged).
"""

from __future__ import annotations

import datetime
import getpass
import hashlib
import hmac
import logging
import os
import platform
import random
import shlex
import sys
import tempfile
import traceback
import argparse
from dataclasses import dataclass, field
from time import sleep
from typing import Any, Callable

import enlighten
import rich
import rich.console as ricon
from builtins import print as rprint
from rich.markup import escape

from . import config

console = ricon.Console()
print = console.print

registry: dict[str, Callable[["Arguments"], Any]] = {}
COMMAND_NOT_FOUND = "CNF-1"

_CONTROL_CHARS = set("/\\\x00\r\n")


def _valid_component(value: str) -> bool:
    """Reject names that could escape their directory or break line formats."""
    if not isinstance(value, str) or not value.strip():
        return False
    if value in (".", ".."):
        return False
    return not any(char in _CONTROL_CHARS for char in value)

# region Logging / crash reports
_LOGGER_NAME = "Perhaps"
logging.getLogger(_LOGGER_NAME).addHandler(logging.NullHandler())
_logger_configured = False
_log_file_path: str | None = None
_excepthook_installed = False


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def debug_switch_enabled() -> bool:
    """Is ``save.DebugSwitch`` currently truthy?

    Only consulted when the built-in save flow is enabled.  The story's
    debugger writes this key, so it is allowed to be a bool or a string.
    """
    if not getattr(config, "SAVE_PATCH_ENABLED", True):
        return False
    try:
        from .saving import save as maybe_save

        if not maybe_save.gotattr("DebugSwitch"):
            return False
        return _truthy(maybe_save.DebugSwitch)
    except Exception:
        return False


def logging_wanted() -> bool:
    """Should a normal log file be opened right now?"""
    if getattr(config, "LOGGING_ENABLED", False):
        return True
    return bool(
        getattr(config, "AUTO_LOGGING_FROM_DEBUG_SWITCH", True)
        and debug_switch_enabled()
    )


def configure_logging(
    *,
    log_dir: str | None = None,
    level: int | str | None = None,
) -> str | None:
    """Configure the file logger.  Returns the log path, or ``None`` on failure.

    This is safe to call repeatedly; only the first successful call installs
    handlers.  Logging is never configured just by importing this module.
    """
    global _logger_configured, _log_file_path
    if _logger_configured:
        return _log_file_path

    directory = log_dir or getattr(config, "LOG_DIR", "logs") or "logs"
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as exc:
        rprint(f"Perhaps: cannot create log directory {directory!r}: {exc}")
        return None

    path = os.path.join(
        directory,
        f"perhaps-{datetime.date.today().isoformat()}.log",
    )
    logger = logging.getLogger(_LOGGER_NAME)
    logger.propagate = False
    level_value = level if level is not None else getattr(config, "LOG_LEVEL", "INFO")
    if isinstance(level_value, str):
        level_value = getattr(logging, level_value.upper(), logging.INFO)
    try:
        logger.setLevel(level_value)
    except (TypeError, ValueError):
        logger.setLevel(logging.INFO)

    try:
        file_handler = logging.FileHandler(path, encoding="utf-8", delay=False)
    except OSError as exc:
        rprint(f"Perhaps: cannot open log file {path!r}: {exc}")
        return None
    file_handler.setLevel(logger.level)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
    )
    file_handler._perhaps_handler = True  # type: ignore[attr-defined]
    logger.addHandler(file_handler)

    if getattr(config, "LOG_TO_CONSOLE", False):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger.level)
        console_handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(message)s")
        )
        console_handler._perhaps_handler = True  # type: ignore[attr-defined]
        logger.addHandler(console_handler)

    _logger_configured = True
    _log_file_path = path
    logger.info("logging started: %s", path)
    return path


def ensure_logging(force: bool | None = None) -> bool:
    """Open the log file when config/DebugSwitch says so.

    :param force: ``True``/``False`` overrides config; ``None`` follows
        ``LOGGING_ENABLED`` / ``AUTO_LOGGING_FROM_DEBUG_SWITCH``.
    """
    if _logger_configured:
        return True
    enabled = logging_wanted() if force is None else bool(force)
    if not enabled:
        return False
    return configure_logging() is not None


def get_logger(name: str = "base") -> logging.Logger:
    """Return a logger below the ``Perhaps`` namespace, opening logs if needed."""
    ensure_logging()
    full_name = _LOGGER_NAME if name in ("", _LOGGER_NAME) else f"{_LOGGER_NAME}.{name}"
    return logging.getLogger(full_name)


def log(message: Any, *args: Any, level: int = logging.INFO, **kwargs: Any) -> None:
    """Write a normal log line (opens the log file according to config)."""
    get_logger("log").log(level, str(message), *args, **kwargs)


def log_debug(message: Any, *args: Any, **kwargs: Any) -> None:
    log(message, *args, level=logging.DEBUG, **kwargs)


def log_info(message: Any, *args: Any, **kwargs: Any) -> None:
    log(message, *args, level=logging.INFO, **kwargs)


def log_warning(message: Any, *args: Any, **kwargs: Any) -> None:
    log(message, *args, level=logging.WARNING, **kwargs)


def log_error(message: Any, *args: Any, **kwargs: Any) -> None:
    log(message, *args, level=logging.ERROR, **kwargs)


def log_exception(message: Any, exc: BaseException | None = None, *args: Any) -> None:
    logger = get_logger("exception")
    if exc is not None:
        logger.error(str(message), *args, exc_info=(type(exc), exc, exc.__traceback__))
    else:
        logger.exception(str(message), *args)


def record_crash(
    exc: BaseException,
    *,
    context: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Write a complete crash report and return its path.

    The report includes environment information, the exception type/message,
    chained exception information and the full formatted traceback.
    """
    directory = getattr(config, "LOG_DIR", "logs") or "logs"
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        directory = "."

    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    path = os.path.join(directory, f"crash-{stamp}.log")
    suffix = 1
    while os.path.exists(path):
        suffix += 1
        path = os.path.join(directory, f"crash-{stamp}-{suffix}.log")

    try:
        traceback_text = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        if exc.__traceback__ is None:
            traceback_text += "\n--- current stack ---\n" + "".join(
                traceback.format_stack()
            )
    except Exception as format_exc:
        traceback_text = f"<could not format traceback: {format_exc}>{exc!r}"

    lines = [
        "Perhaps Framework crash report",
        "=" * 40,
        f"time      : {datetime.datetime.now().isoformat()}",
        f"python    : {sys.version}",
        f"platform  : {platform.platform()}",
        f"cwd       : {os.getcwd()}",
        f"argv      : {sys.argv!r}",
        f"context   : {context or '-'}",
        "",
        f"exc type  : {type(exc).__module__}.{type(exc).__qualname__}",
        f"exc str   : {exc}",
        f"exc repr  : {exc!r}",
        f"exc args  : {exc.args!r}",
        f"cause     : {exc.__cause__!r}",
        f"context ex: {exc.__context__!r}",
    ]
    notes = getattr(exc, "__notes__", None)
    if notes:
        lines.append(f"notes     : {notes!r}")
    if extra:
        lines.append(f"extra     : {extra!r}")
    lines.extend(["", "----- traceback -----", traceback_text])
    content = "\n".join(lines) + "\n"

    try:
        with open(path, "w", encoding="utf-8") as crash_file:
            crash_file.write(content)
    except OSError as exc2:
        fallback = f"crash-{stamp}.log"
        with open(fallback, "w", encoding="utf-8") as crash_file:
            crash_file.write(content)
        path = fallback
        rprint(f"Perhaps: could not write {path!r}, wrote {fallback!r}: {exc2}")

    if _logger_configured:
        try:
            logging.getLogger(_LOGGER_NAME + ".crash").critical(
                "crash report written to %s",
                path,
                exc_info=(type(exc), exc, exc.__traceback__),
            )
        except Exception:
            pass
    return path


def crash_exit(exc: BaseException, *, context: str | None = None) -> None:
    """Write a crash report, print a short message and terminate the shell."""
    path = record_crash(exc, context=context)
    try:
        clear()
    except Exception:
        pass
    print("[red]An unexpected exception occurred in your emulator.[/red]")
    print(f"[red]A crash log was written to '{escape(path)}'.[/red]")
    print(
        "[red]If you can submit the crash log to the developer, please do; "
        "the full traceback is in the file.[/red]"
    )
    print()
    print(f"Short exception: [red]{escape(str(exc))}[/red]")
    raise SystemExit(1)


def install_excepthook() -> None:
    """Install a crash-reporting ``sys.excepthook`` once."""
    global _excepthook_installed
    if _excepthook_installed:
        return
    previous_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        if isinstance(exc_value, SystemExit):
            previous_hook(exc_type, exc_value, exc_tb)
            return
        try:
            path = record_crash(exc_value, context="uncaught exception")
            rprint(f"Perhaps: unhandled exception; crash log: {path}")
        except Exception:
            pass
        previous_hook(exc_type, exc_value, exc_tb)

    _hook._perhaps_crash_hook = True  # type: ignore[attr-defined]
    sys.excepthook = _hook
    _excepthook_installed = True


# endregion

# region Injector
@dataclass
class InjectReport:
    """Result of running every inject callback registered for a point."""

    values: list[Any] = field(default_factory=list)
    executed: list[Any] = field(default_factory=list)
    handled: bool = False
    cancelled: bool = False


class Handled:
    """Return this from an inject to suppress the framework default action."""

    def __init__(self, callback: Callable[[], Any] | None = None) -> None:
        self.callback = callback


class Cancel(Handled):
    """Return this from ``after_enter`` to skip parsing the current input."""


injects: dict[str, list[Callable[..., Any]]] = {}
patchers: dict[str, list[Callable[..., Any]]] = {}


def inject(inject_point: str):
    """Register *func* as an inject callback for ``inject_point``."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        injects.setdefault(inject_point, []).append(func)
        return func

    return decorator


def patcher(patcher_point: str):
    """Register *func* as a patcher callback for ``patcher_point``."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        patchers.setdefault(patcher_point, []).append(func)
        return func

    return decorator


def run_injects(inject_point: str, *args: Any, **kwargs: Any) -> InjectReport:
    """Run every inject callback registered for *inject_point*.

    Callbacks may return ``None`` (no effect), ``Handled()`` (suppress the
    framework default), or ``Cancel()`` (additionally cancel command
    processing for ``after_enter``).  A callback registered as
    ``Handled(callable)`` has that callable invoked immediately.
    """
    report = InjectReport()
    for callback in tuple(injects.get(inject_point, ())):
        result = callback(*args, **kwargs)
        report.values.append(result)
        if isinstance(result, Handled):
            report.handled = True
            if isinstance(result, Cancel):
                report.cancelled = True
            if result.callback is not None:
                report.executed.append(result.callback())
        elif result is not None:
            raise TypeError(
                f"inject callback for {inject_point!r} returned unsupported "
                f"value {result!r}; return None, Handled() or Cancel()"
            )
    return report


def run_patcher(patcher_point: str, value: Any, *args: Any, **kwargs: Any) -> Any:
    """Chain every patcher registered for *patcher_point*.

    Each patcher receives the current value as its first argument and may
    return a replacement; ``None`` means "leave unchanged".
    """
    for callback in tuple(patchers.get(patcher_point, ())):
        new_value = callback(value, *args, **kwargs)
        if new_value is not None:
            value = new_value
    return value


# endregion

# region Command Creator
def register(command: str, *, override: bool = False):
    """Register a command by its invocation name.

    Registering an existing name raises ``ValueError`` unless
    ``override=True`` is passed.  Silent overrides used to make behaviour
    depend on import order.
    """
    if not isinstance(command, str) or command == "":
        raise ValueError("command name must be a non-empty string")

    def decorator(func: Callable[["Arguments"], Any]) -> Callable[["Arguments"], Any]:
        if command in registry and not override:
            raise ValueError(
                f"command {command!r} is already registered; "
                "pass override=True if this is intentional"
            )
        registry[command] = func
        return func

    return decorator


# endregion

# region Flags / userinfo
def _flag_path(flag_name: str) -> str:
    if not _valid_component(flag_name):
        raise ValueError(f"invalid flag name: {flag_name!r}")
    return os.path.join("flags", flag_name)


def _atomic_write(path: str, text: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".drom-", dir=parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def mkflag(flag_name: str, writeln: str = "") -> None:
    """Create or replace a flag file."""
    _atomic_write(_flag_path(flag_name), writeln)


def clear() -> None:
    """Clear console."""
    console.clear()


def flags(flag_name: str) -> bool:
    """Does a flag file exist?"""
    return os.path.isfile(_flag_path(flag_name))


def rdflag(flag_name: str) -> str:
    """Read flag content; returns ``""`` when the flag is missing."""
    try:
        path = _flag_path(flag_name)
    except ValueError:
        return ""
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def read_userinfo() -> tuple[str, str, str, str]:
    """Read ``flags/userinfo`` as ``(username, password_hash, hostname, salt)``.

    This is intentionally a low-level reader: it does not start setup.  Call
    :func:`ensure_initialized` (or :func:`init` / :func:`main_while`) first.
    """
    path = os.path.join("flags", "userinfo")
    if not os.path.isfile(path):
        raise RuntimeError(
            "flags/userinfo does not exist; the system is not initialized"
        )
    with open(path, "r", encoding="utf-8") as fh:
        lines = [line.rstrip("\n") for line in fh]
    while lines and lines[-1] == "":
        lines.pop()
    if len(lines) != 4:
        raise ValueError(
            "flags/userinfo must contain exactly 4 lines: "
            "username, password hash, hostname, salt"
        )
    return tuple(line.strip() for line in lines)  # type: ignore[return-value]


def is_initialized() -> bool:
    """Has setup completed and left a readable ``flags/userinfo``?"""
    return flags("setuped") and os.path.isfile(os.path.join("flags", "userinfo"))


def ensure_initialized() -> None:
    """Run setup when needed.  Setup exits the process for a restart."""
    if is_initialized():
        return
    if flags("skipsetup"):
        raise RuntimeError(
            "skipsetup is set but the system has no account; "
            "run setup() manually or remove the flag"
        )
    print("[yellow]System is not initialized. Starting setup...[/yellow]")
    setup()
    if not is_initialized():
        raise RuntimeError("setup did not complete; please restart")


# endregion

# region Functions
def process(desc: str, total: int = 100, unit: str = "items"):
    """Create a progress counter backed by its own enlighten manager."""
    manager = enlighten.Manager()
    pbar = manager.counter(total=total, desc=desc, unit=unit)
    # Keep the manager alive with the counter so common_process_loop can stop it.
    try:
        pbar._drom_manager = manager  # type: ignore[attr-defined]
    except AttributeError:
        pass
    return pbar


def md5(text: str) -> str:
    """Calculate an unsalted MD5 hex digest (legacy interface)."""
    return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()


def hash_password(password: str, salt: str) -> str:
    """Hash a password with scrypt and return a self-describing string."""
    raw = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return "scrypt$" + raw.hex()


def verify_password(password: str, stored: str, salt: str) -> bool:
    """Verify *password* against a stored hash (scrypt or legacy MD5)."""
    if stored.startswith("scrypt$"):
        candidate = hash_password(password, salt)
        return hmac.compare_digest(candidate, stored)
    if len(stored) == 32:
        legacy = md5(password + salt)
        return hmac.compare_digest(legacy, stored)
    return False


def random_num() -> int:
    """Return a six digit number (legacy helper)."""
    return random.randint(100000, 999999)


def common_process_loop(
    pbar: Any,
    tries: int = 100,
    delay: float = 0.09,
    while_do: Callable[[int], None] | None = None,
    callback: Callable[[], None] | None = None,
) -> None:
    """Run a progress loop.

    Both callbacks are optional; the old implementation compared
    ``type(x) != None`` which is always true and crashed on the defaults.
    """
    manager = getattr(pbar, "_drom_manager", None)
    try:
        for i in range(tries):
            sleep(delay)
            if while_do is not None:
                while_do(i)
            pbar.update()
        if callback is not None:
            callback()
    finally:
        try:
            pbar.close()
        except Exception:
            pass
        if manager is not None:
            try:
                manager.stop()
            except Exception:
                pass


class MissingArgument(IndexError):
    """Raised when a command accesses a positional argument that is absent."""


class Arguments:
    """Arguments passed to commands, plus the upstream pipeline result."""

    def __init__(self, args: list, tunnel_ret: "Arguments | None" = None) -> None:
        self.args = args
        self.tunnel_ret = tunnel_ret

    def __getitem__(self, key):
        if key == "TUNNEL":
            return self.tunnel_ret
        try:
            return self.args[key]
        except IndexError:
            raise MissingArgument(
                f"missing argument at index {key!r}"
            ) from None

    def __setitem__(self, key, value) -> None:
        self.args[key] = value

    def __delitem__(self, key) -> None:
        del self.args[key]

    def __getargs__(self) -> list:
        return self.args

    def __len__(self) -> int:
        return len(self.args)

    def __iter__(self):
        return iter(self.args)

    def __repr__(self) -> str:
        return f"Arguments({self.args!r})"



class Command:
    """Parse and execute a shell command, including ``|`` pipelines."""

    def __init__(self, command: str | list[str] | tuple[str, ...]) -> None:
        if isinstance(command, str):
            self.raw: str | None = command
            self._tokens: list[str] | None = None
        elif isinstance(command, (list, tuple)) and all(
            isinstance(token, str) for token in command
        ):
            self._tokens = list(command)
            self.raw = None
        else:
            raise TypeError("command must be a string or a sequence of strings")

        self.data: list[str] = []
        self.head: str = ""
        self.args: list[str] = []
        self.tunnel: Command | None = None
        self.parse_error: str | None = None

    @staticmethod
    def _split_pipeline(text: str) -> list[str]:
        """Split on unquoted, unescaped ``|`` characters."""
        parts: list[str] = []
        buf: list[str] = []
        quote: str | None = None
        i = 0
        while i < len(text):
            ch = text[i]
            if quote is not None:
                buf.append(ch)
                if ch == "\\" and quote == '"' and i + 1 < len(text):
                    i += 1
                    buf.append(text[i])
                elif ch == quote:
                    quote = None
            else:
                if ch == "\\":
                    buf.append(ch)
                    if i + 1 < len(text):
                        i += 1
                        buf.append(text[i])
                elif ch in "\"'":
                    quote = ch
                    buf.append(ch)
                elif ch == "|":
                    parts.append("".join(buf))
                    buf = []
                else:
                    buf.append(ch)
            i += 1
        if quote is not None:
            raise ValueError("no closing quotation")
        parts.append("".join(buf))
        return parts

    def _parse_str(self) -> list[list[str]]:
        assert self.raw is not None
        segments = self._split_pipeline(self.raw)
        groups: list[list[str]] = []
        for index, segment in enumerate(segments):
            tokens = shlex.split(segment)
            if not tokens:
                raise ValueError(
                    "empty command in pipeline"
                    if len(segments) > 1
                    else "empty command"
                )
            groups.append(tokens)
            if index == 0 and len(segments) > 1:
                # Keep the raw remainder for a recursive parse: this preserves
                # quoting of a literal ``"|"`` in later pipeline stages.
                self.tunnel = Command("|".join(segments[1:]))
                break
        return groups

    def _parse_tokens(self) -> list[list[str]]:
        assert self._tokens is not None
        groups: list[list[str]] = [[]]
        for token in self._tokens:
            if token == "|":
                groups.append([])
            else:
                groups[-1].append(token)
        if any(not group for group in groups):
            raise ValueError("empty command in pipeline")
        if len(groups) > 1:
            rest: list[str] = []
            for index, group in enumerate(groups[1:]):
                if index:
                    rest.append("|")
                rest.extend(group)
            self.tunnel = Command(rest)
        return groups

    def parse(self) -> None:
        """Parse the command and its pipeline.  Never raises for bad input."""
        self.data = []
        self.head = ""
        self.args = []
        self.tunnel = None
        self.parse_error = None
        try:
            if self.raw is not None:
                groups = self._parse_str()
            else:
                groups = self._parse_tokens()
        except ValueError as exc:
            self.parse_error = f"humansh: {exc}. please check then try again."
            return
        first = groups[0]
        self.head = first[0]
        self.args = first[1:]
        self.data = first[1:]
        if self.tunnel is not None:
            self.tunnel.parse()
            if self.tunnel.parse_error is not None:
                self.parse_error = self.tunnel.parse_error
                self.tunnel = None

    def __call__(self, tunnel_ret: "Arguments | None" = None):
        return self.execute(tunnel_ret)

    @staticmethod
    def _wrap_result(result: Any) -> Arguments:
        if isinstance(result, Arguments):
            ret = result
        elif result is None:
            ret = Arguments([0])
        elif isinstance(result, (list, tuple)):
            ret = Arguments(list(result))
        else:
            ret = Arguments([result])
        if len(ret) == 0:
            ret = Arguments([0])
        return ret

    def execute(self, tunnel_ret: "Arguments | None" = None) -> list[Arguments]:
        """Execute this command (and its pipeline), returning all results."""
        returns: list[Arguments] = []
        if self.parse_error is not None:
            print(escape(self.parse_error))
            return returns
        if not self.head:
            print("humansh: command not found: ")
            return returns

        func = registry.get(self.head)
        if func is None:
            print(f"humansh: command not found: {escape(self.head)}")
            return returns

        ret = self._wrap_result(func(Arguments(self.args, tunnel_ret)))
        if ret[0] == COMMAND_NOT_FOUND:
            print(f"humansh: command not found: {escape(self.head)}")
            return returns
        returns.append(ret)

        if self.tunnel is not None:
            returns.extend(self.tunnel(ret))
        return returns


# endregion

# region Shared progress / auth helpers
def ask_password_once(
    userinfo: tuple[str, str, str, str] | None = None,
    requirer: str | None = "sudo",
    prompt: str | Callable[[str], str] | None = None,
) -> str | None:
    """Prompt for a password once.

    :return: the typed password, or ``None`` on interrupt/EOF.
    """
    if userinfo is None:
        userinfo = read_userinfo()
    username = userinfo[0]
    if prompt is None:
        if requirer and requirer != "[No Requirer]":
            text = f"{requirer}: {username}'s password: "
        else:
            text = f"{username}'s password: "
    elif callable(prompt):
        text = prompt(username)
    else:
        text = str(prompt)
    try:
        return getpass.getpass(text)
    except (KeyboardInterrupt, EOFError):
        print()
        return None


def askpass(
    userinfo: tuple[str, str, str, str] | None = None,
    requirer: str | None = "sudo",
    attempts: int = 3,
    prompt: str | Callable[[str], str] | None = None,
) -> bool:
    """Low-level password prompt/verify helper.

    :param userinfo: ``(username, password_hash, hostname, salt)``; read from
        ``flags/userinfo`` when omitted.
    :param requirer: prefix shown before the password prompt.  ``None`` or
        ``"[No Requirer]"`` shows only ``<username>'s password: ``.
    :param attempts: maximum number of tries.
    :param prompt: custom prompt string, or callable taking the username.
    :return: ``True`` on success, ``False`` on wrong password/interrupt/EOF.

    ``fastutil.login`` is the full-featured backend (adds lockout when a
    virtual file system is available); ``fastutil.askpass`` is its simplified
    wrapper.  For compatibility, ``login`` is also an alias of this function
    in ``Perhaps.base``.
    """
    if userinfo is None:
        userinfo = read_userinfo()
    password_hash = userinfo[1]
    salt = userinfo[3]
    prefix = f"{requirer}: " if requirer and requirer != "[No Requirer]" else ""
    for _ in range(max(1, attempts)):
        password = ask_password_once(userinfo, requirer=requirer, prompt=prompt)
        if password is None:
            return False
        if verify_password(password, password_hash, salt):
            return True
        print(f"{prefix}incorrect password. please try again.")
    print(f"{prefix}too many incorrect password attempts.")
    return False


#: Low-level alias; full-featured login lives in ``Perhaps.fastutil``.
login = askpass


# endregion

# region Parts
def setup() -> None:
    """First-boot setup: collect user info and write the credential files."""

    if run_injects("before_setup").handled:
        return

    def setup_phase2(i: int) -> None:
        if i == 20:
            clear()
            print("\n[cyan]Second[/cyan], setup your hardwares.")
            print("Eyes Service: [gray]<disabled>[/gray]")
            print("Nervous Service: [gray]<disabled>[/gray]")
            print("No services need to setup.")
        elif i == 50:
            clear()
            print("\n[cyan]Third[/cyan], recovery from backups.")
            print("Backups     | Time | Recoverable | Select")
            print("<No backups>")
            print("")
            print("No backups found or recoverable.")
        elif i == 70:
            clear()
            print("\n[cyan]Fourth[/cyan], write configuration.")
            print("Please hold on.")
        elif i == 99:
            clear()

    def setup_phase3() -> None:
        clear()
        print("\n[cyan]Fifth[/cyan], set your personal informations.")
        print("Please input them.")
        username = input("Your username: ").strip()
        password = getpass.getpass("Password (Hidden): ")
        hostname = input("Your hostname: ").strip()
        if not _valid_component(username):
            raise ValueError("invalid username")
        if not password:
            raise ValueError("password must not be empty")
        if not _valid_component(hostname):
            raise ValueError("invalid hostname")
        salt = os.urandom(16).hex()
        password_hash = hash_password(password, salt)

        mkflag("setuped", "success")
        _atomic_write(
            os.path.join("flags", "userinfo"),
            "\n".join([username, password_hash, hostname, salt, ""]),
        )
        # New installations ask for the password before opening the shell.
        # Existing installations without this flag keep booting directly.
        mkflag("login_required")

        sleep(2)
        print("\n🎉 All configuration completed!")
        print("- File writed.")
        print("- Please restart to apply.")
        print()
        console.input("[dim]Enter to continue[/dim]> ")
        raise SystemExit(0)

    clear()
    print("\n[green]Welcome to HumanOS![/green]")
    print("This is a setup for you to initialize this system.")
    print("Thank you for your choose.")
    print()
    print("[cyan]First[/cyan], let's setup your machine.")
    print("")
    print("Detected hard / memory drives")
    print("    - /dev/sda1 1024PB used 369PB (B)")
    print("    - /dev/sda2 2048PB used 0PB   (X)")
    print("[italic](B) Bootable Flag; (X) Selecting; ( ) Unselected[/italic]")
    print("")
    common_process_loop(process("Auto Config..."), while_do=setup_phase2, callback=setup_phase3)


# endregion

# region Pre-init texts
def preload() -> None:
    """Print the boot text.  Called from :func:`init`, not at import time."""
    if flags("skipload"):
        return
    if run_injects("before_load").handled:
        return
    path = os.path.join("texts", "initpre.txt")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    for line in lines:
        rich.print(f"[green]{escape(line.strip())}[/green]", flush=True)
        sleep(0.04)
    sleep(1)
    rprint(".")
    sleep(1)
    rprint(".")
    sleep(2)


# endregion

# region Shell Pre
def init() -> None:
    """Welcome information."""
    install_excepthook()
    ensure_logging()
    log_info("init: welcome sequence started")
    clear()
    preload()
    if run_injects("before_shell_pre").handled:
        return

    print("[green]Welcome to HumanOS [/green]([cyan]v7.2.14-nature5-5-nature[/cyan]) !")
    print()
    print("[yellow][!][/yellow] [red]Warnings to you[/red]")
    print(
        "    - This mode is for [bold]EMERGENCY[/bold] use. If you entered this "
        "mode as yourself, please quit ASAP.\n    - If you entered this mode "
        "without your any actions, please read recovery documents."
    )
    print()
    print("Type 'help' for all commands.")
    print()

    ensure_initialized()


# endregion

# region Main While
def main_while(auth: bool | None = None) -> bool:
    """Run the doas shell.

    :param auth: force authentication on/off; ``None`` means "require it
        when the ``login_required`` flag exists".
    :return: ``True`` when the session ended normally, ``False`` on auth
        failure.
    """
    install_excepthook()
    ensure_logging()
    if not is_initialized():
        ensure_initialized()
    username, password_hash, hostname, salt = read_userinfo()
    if auth is None:
        auth = flags("login_required")
    if auth and not askpass((username, password_hash, hostname, salt)):
        print("Access denied.")
        log_warning("authentication failed for user=%s", username)
        return False

    directory = "~"
    prompt = f"{escape(username)}@{escape(hostname)}:{escape(directory)}$ "
    log_info(
        "shell session started user=%s host=%s cwd=%s",
        username,
        hostname,
        os.getcwd(),
    )

    try:
        while True:
            # ``save.DebugSwitch`` can be toggled at runtime; re-check every
            # loop so debugger > ea DebugSwitch true starts logging at once.
            ensure_logging()
            run_injects("while_head")
            run_injects("userinfo", username, password_hash, hostname, salt)
            run_injects("getdir", directory)

            directory = run_patcher("directory_patcher", directory)
            if not isinstance(directory, str):
                directory = str(directory)
            prompt = run_patcher(
                "prompt_patcher",
                prompt,
                (username, password_hash, hostname, salt),
                directory,
            )
            if not isinstance(prompt, str):
                prompt = str(prompt)

            try:
                ipt = console.input(prompt)
            except (KeyboardInterrupt, EOFError):
                run_injects("before_quit")
                print("\nLogging out...")
                log_info("shell session ended by interrupt/EOF")
                return True

            if not ipt.strip():
                continue
            if ipt.strip().lower() == "exit":
                run_injects("before_quit")
                print("\nLogging out...")
                log_info("shell session ended by exit command")
                return True

            log_info("command: %s", ipt)
            report = run_injects("after_enter", ipt)
            if report.cancelled:
                log_info("command cancelled by after_enter inject")
                continue

            cmd = Command(ipt)
            cmd.parse()
            if cmd.parse_error is not None:
                print(escape(cmd.parse_error))
                log_warning("command parse error: %s", cmd.parse_error)
                continue

            run_injects("before_execute", cmd)
            try:
                returns = cmd.execute()
            except MissingArgument:
                print(
                    f"{escape(cmd.head)}: arguments not enough. "
                    f"May you can use `{escape(cmd.head)} help` for information"
                )
                log_warning("command %r is missing an argument", cmd.head)
                continue
            log_info("command %r finished with %d result(s)", ipt, len(returns))
            run_injects("after_execute", cmd, returns)

    except (KeyboardInterrupt, EOFError):
        run_injects("before_quit")
        print("\nLogging out...")
        log_info("shell session ended by interrupt/EOF")
        return True
    except Exception as exc:
        log_exception("unhandled exception in main_while", exc)
        crash_exit(
            exc,
            context=f"main_while user={username!r} host={hostname!r}",
        )


# endregion

if __name__ == "__main__":
    init()
    print(">>> [cyan]Notice:[/cyan] This is Framework file! Please execute Chapter files or Menu file.")
    main_while()
