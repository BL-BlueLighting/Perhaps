"""
doas -su mylife.root
Pacman-flavoured command line for the package manager.

This is the part that mirrors the story's MPM command surface:

    mpm {-h --help}
    mpm {-V --version}
    mpm {-D --database} <options> <package>
    mpm {-F --files}    [options] [file]
    mpm {-Q --query}    [options] [package]
    mpm {-R --remove}   [options] <package>
    mpm {-S --sync}     [options] [package]
    mpm {-T --deptest}  [options] [package]
    mpm {-U --upgrade}  [options] <file>

The controller is extensible: ``CLIController.add_action("X", handler)``
registers a new operation.  A handler receives ``CliRequest`` and returns an
integer exit code.

btw i study British English
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .. import base as framework_base
from .errors import PackageError, PackageNotFound
from .manager import PackageManager
from .package import Package

PM_VERSION = "1.0.0"

ACTION_SHORT = set("QSRUTDF")
ACTION_LONG = {
    "query": "Q",
    "sync": "S",
    "remove": "R",
    "upgrade": "U",
    "deptest": "T",
    "database": "D",
    "files": "F",
}

#: short option -> canonical name
SHORT_OPTIONS = {
    "i": "info",
    "l": "list",
    "o": "owner",
    "s": "search",
    "q": "quiet",
    "c": "cascade",
    "d": "deps",
    "t": "unrequired",
    "e": "explicit",
    "g": "groups",
    "p": "print",
    "y": "refresh",
    "u": "sysupgrade",
    "n": "nosave",
    "w": "downloadonly",
    "k": "check",
    "v": "verbose",
    "f": "force",
}

LONG_OPTIONS = {
    "info": "info",
    "list": "list",
    "owner": "owner",
    "search": "search",
    "quiet": "quiet",
    "cascade": "cascade",
    "clean": "clean",
    "deps": "deps",
    "unrequired": "unrequired",
    "explicit": "explicit",
    "groups": "groups",
    "print": "print",
    "refresh": "refresh",
    "sysupgrade": "sysupgrade",
    "unneeded": "unneeded",
    "nosave": "nosave",
    "downloadonly": "downloadonly",
    "check": "check",
    "verbose": "verbose",
    "force": "force",
    "needed": "needed",
    "recursive": "recursive",
    "noconfirm": "noconfirm",
    "asdeps": "asdeps",
    "asexplicit": "asexplicit",
    "dbonly": "dbonly",
}


@dataclass
class CliRequest:
    action: str | None = None
    targets: list[str] = field(default_factory=list)
    options: set[str] = field(default_factory=set)
    long_options: set[str] = field(default_factory=set)
    option_values: dict[str, str] = field(default_factory=dict)
    help: bool = False
    version: bool = False

    def has(self, *names: str) -> bool:
        return any(name in self.options or name in self.long_options for name in names)


class CliParseError(Exception):
    pass


def parse_args(argv: list[str], extra_actions: set[str] | None = None) -> CliRequest:
    request = CliRequest()
    allowed_actions = ACTION_SHORT | set(extra_actions or ())
    index = 0
    positional_only = False
    while index < len(argv):
        token = str(argv[index])
        index += 1
        if positional_only:
            request.targets.append(token)
            continue
        if token == "--":
            positional_only = True
            continue
        if token in ("-h", "--help"):
            request.help = True
            continue
        if token in ("-V", "--version"):
            request.version = True
            continue
        if token.startswith("--"):
            name, separator, value = token[2:].partition("=")
            if name in ACTION_LONG:
                if request.action is not None and request.action != ACTION_LONG[name]:
                    raise CliParseError("only one operation may be used at a time")
                request.action = ACTION_LONG[name]
            elif name in LONG_OPTIONS:
                request.long_options.add(LONG_OPTIONS[name])
                if separator:
                    request.option_values[name] = value
            elif name in ("help", "version"):
                request.help = name == "help"
                request.version = name == "version"
            else:
                raise CliParseError(f"invalid option '--{name}'")
            continue
        if token.startswith("-") and len(token) > 1:
            for char in token[1:]:
                if char in allowed_actions:
                    if request.action is not None and request.action != char:
                        raise CliParseError("only one operation may be used at a time")
                    request.action = char
                elif char in SHORT_OPTIONS:
                    request.options.add(SHORT_OPTIONS[char])
                elif char == "h":
                    request.help = True
                elif char == "V":
                    request.version = True
                else:
                    raise CliParseError(f"invalid option '-{char}'")
            continue
        request.targets.append(token)
    _normalize_options(request)
    return request


def _normalize_options(request: CliRequest) -> None:
    """Give context-dependent short options their pacman meaning."""
    if request.action == "R":
        if "search" in request.options:
            request.options.discard("search")
            request.options.add("recursive")
        if "sysupgrade" in request.options:
            request.options.discard("sysupgrade")
            request.options.add("unneeded")
    elif request.action == "S":
        if "cascade" in request.options:
            request.options.discard("cascade")
            request.options.add("clean")


class CLIController:
    def __init__(self, manager: PackageManager, name: str = "mpm", console: Any = None) -> None:
        self.manager = manager
        self.name = name
        self.console = console or framework_base.console
        self.actions: dict[str, Callable[[CliRequest], int]] = {
            "Q": self.query,
            "S": self.sync,
            "R": self.remove,
            "U": self.upgrade,
            "T": self.deptest,
            "D": self.database,
            "F": self.files,
        }

    def add_action(self, action: str, handler: Callable[[CliRequest], int]) -> None:
        """Register a custom one-letter operation (e.g. ``"X"``)."""
        if not isinstance(action, str) or len(action) != 1:
            raise ValueError("action must be a single character")
        self.actions[action] = handler

    def remove_action(self, action: str) -> None:
        self.actions.pop(action, None)

    # ---------------------------------------------------------------- output
    def _print(self, *args: Any, **kwargs: Any) -> None:
        self.console.print(*args, **kwargs)

    def _error(self, message: str) -> None:
        self._print(f"[red]error:[/red] {framework_base.escape(message)}")

    def _warning(self, message: str) -> None:
        self._print(f"[yellow]warning:[/yellow] {framework_base.escape(message)}")

    def _package_name(self, package: Package, repository: str = "") -> str:
        prefix = f"{repository}/" if repository else ""
        return f"{prefix}{package.name} {package.version}"

    def _show_package(self, package: Package, repository: str = "") -> None:
        self._print(f"[bold cyan]{self._package_name(package, repository)}[/bold cyan]")
        if package.description:
            self._print(f"    {framework_base.escape(package.description)}")
        if package.author:
            self._print(f"    Author: {framework_base.escape(package.author)}")
        if package.date:
            self._print(f"    Date: {framework_base.escape(package.date)}")
        if package.depends:
            self._print("    Depends: " + ", ".join(framework_base.escape(dep) for dep in package.depends))
        if package.provides:
            self._print("    Provides: " + ", ".join(framework_base.escape(dep) for dep in package.provides))
        if package.conflicts:
            self._print("    Conflicts: " + ", ".join(framework_base.escape(dep) for dep in package.conflicts))
        if package.commands:
            self._print("    Commands: " + ", ".join(framework_base.escape(command) for command in package.commands))

    def _show_installed(self, record: Any) -> None:
        package = record.package
        self._print(f"[bold cyan]{package.name} {package.version}[/bold cyan]")
        if package.description:
            self._print(f"    {framework_base.escape(package.description)}")
        self._print(f"    Reason: {record.reason}")
        if record.install_date:
            self._print(f"    Installed: {framework_base.escape(record.install_date)}")
        if record.required_by:
            self._print("    Required by: " + ", ".join(sorted(record.required_by)))
        if package.depends:
            self._print("    Depends: " + ", ".join(framework_base.escape(dep) for dep in package.depends))

    # ----------------------------------------------------------------- help
    def print_help(self) -> None:
        self.console.print(f"""Usage: {self.name} <operation> [...]
Operations:
    {self.name} {{-h --help}}
    {self.name} {{-V --version}}
    {self.name} {{-D --database}} <options> <package>
    {self.name} {{-F --files}}    [options] [file]
    {self.name} {{-Q --query}}    [options] [package]
    {self.name} {{-R --remove}}   [options] <package>
    {self.name} {{-S --sync}}     [options] [package]
    {self.name} {{-T --deptest}}  [options] [package]
    {self.name} {{-U --upgrade}}  [options] <file>

Common options:
    -i, --info          show package information
    -l, --list          list files
    -o, --owner         show owner of a file
    -s, --search        search by name/description
    -q, --quiet         minimal output
    -y, --refresh       refresh repositories
    -u, --sysupgrade    upgrade installed packages (with -S)
    -c, --cascade       remove dependents too (with -R)
    -n, --nosave        do not save the local database
    -t, --unrequired    list packages not required by anything
    -e, --explicit      explicit packages only
    -d, --deps          dependency packages only
    -g, --groups        list groups
    -k, --check         check integrity
    --needed            skip reinstall of up-to-date packages
    --asdeps            mark packages as dependencies
    --asexplicit        mark packages as explicit

Use '{self.name} {{-h --help}}' together with an operation for more options.""", markup=False)

    def print_version(self) -> None:
        self._print(f"Memory Package Manager {PM_VERSION} - Perhaps PM")
        self._print("(c) Copyright BL.BlueLighting / Perhaps Framework")

    # ------------------------------------------------------------------ run
    def run(self, argv: list[str]) -> int:
        try:
            request = parse_args(argv, extra_actions=set(self.actions))
        except CliParseError as exc:
            self._error(str(exc))
            return 1
        if request.help:
            self.print_help()
            return 0
        if request.version:
            self.print_version()
            return 0
        if request.action is None:
            self.print_help()
            return 0
        action = self.actions.get(request.action)
        if action is None:
            self._error(f"operation {request.action!r} is not available")
            return 1
        try:
            return action(request)
        except PackageError as exc:
            self._error(str(exc))
            return 1
        except FileNotFoundError as exc:
            self._error(str(exc))
            return 1

    # ---------------------------------------------------------------- query
    def query(self, request: CliRequest) -> int:
        database = self.manager.database
        if request.has("owner"):
            if not request.targets:
                self._error("no file specified")
                return 1
            result = 0
            for path in request.targets:
                owner = self.manager.owner(path)
                if owner is None:
                    self._error(f"no package owns {path}")
                    result = 1
                else:
                    self._print(f"{owner.package.name} {owner.package.version} owns {path}")
            return result

        if request.has("search"):
            query = " ".join(request.targets)
            for record in database.search(query):
                if request.has("quiet"):
                    self._print(record.package.name)
                else:
                    self._print(f"{record.package.name} {record.package.version}")
            return 0

        if request.has("info"):
            records = (
                [database.find_by_name(target) for target in request.targets]
                if request.targets
                else list(database.installed.values())
            )
            missing = [target for target, record in zip(request.targets, records) if record is None]
            for target in missing:
                self._error(f"package not found: {target}")
            for record in records:
                if record is not None:
                    self._show_installed(record)
            return 1 if missing else 0

        if request.has("list"):
            if not request.targets:
                self._error("no package specified")
                return 1
            result = 0
            for target in request.targets:
                record = database.find_by_name(target)
                if record is None:
                    self._error(f"package not found: {target}")
                    result = 1
                    continue
                for path in record.files:
                    self._print(path)
            return result

        if request.has("groups"):
            grouped = database.groups()
            if not request.targets:
                for group in sorted(grouped):
                    self._print(group)
            else:
                for group in request.targets:
                    for record in grouped.get(group, []):
                        self._print(f"{group} {record.package.name}")
            return 0

        records = list(database.installed.values())
        if request.has("explicit"):
            records = [record for record in records if record.reason == "explicit"]
        if request.has("deps"):
            records = [record for record in records if record.reason == "dependency"]
        if request.has("unrequired"):
            records = database.orphans()
        if request.targets:
            wanted = set(request.targets)
            records = [
                record
                for record in records
                if record.package.id in wanted or record.package.name in wanted
            ]
        records.sort(key=lambda record: record.package.name)
        for record in records:
            if request.has("quiet"):
                self._print(record.package.name)
            else:
                self._print(f"{record.package.name} {record.package.version}")
        return 0

    # ------------------------------------------------------------------ sync
    def sync(self, request: CliRequest) -> int:
        if request.has("refresh"):
            self.manager.refresh()
            if not request.targets and not request.has("sysupgrade"):
                return 0
        if request.has("clean"):
            self._print(":: no cache to clean")
            return 0
        if request.has("sysupgrade"):
            result = self.manager.upgrade(allow_downgrade=request.has("force"))
            return self._report_transaction(result)
        if request.has("search"):
            query = " ".join(request.targets)
            if not query:
                self._error("no search query specified")
                return 1
            for repository, package in self.manager.search(query):
                if request.has("quiet"):
                    self._print(package.name)
                else:
                    self._print(f"{repository.name}/{package.name} {package.version}")
                    if package.description:
                        self._print(f"    {framework_base.escape(package.description)}")
            return 0
        if request.has("info"):
            if not request.targets:
                self._error("no package specified")
                return 1
            result = 0
            for target in request.targets:
                found = self.manager.find_available(target)
                if found is None:
                    record = self.manager.find_installed(target)
                    if record is None:
                        self._error(f"package not found: {target}")
                        result = 1
                    else:
                        self._show_installed(record)
                else:
                    self._show_package(found[1], found[0].name)
            return result
        if request.has("list"):
            if not request.targets:
                self._error("no package specified")
                return 1
            result = 0
            for target in request.targets:
                found = self.manager.find_available(target)
                if found is None:
                    self._error(f"package not found: {target}")
                    result = 1
                    continue
                for path in found[1].files:
                    self._print(path.path)
            return result
        if request.has("groups"):
            grouped = self.manager.groups(installed=False)
            if not request.targets:
                for group in sorted(grouped):
                    self._print(group)
            else:
                for group in request.targets:
                    for package in grouped.get(group, []):
                        self._print(f"{group} {package.name}")
            return 0
        if not request.targets:
            self._error("no targets specified")
            return 1
        result = self.manager.install(
            request.targets,
            needed=request.has("needed"),
            allow_downgrade=request.has("force"),
            save=not request.has("nosave"),
        )
        return self._report_transaction(result)

    # ---------------------------------------------------------------- remove
    def remove(self, request: CliRequest) -> int:
        targets = list(request.targets)
        if request.has("unneeded") and not targets:
            targets = [record.id for record in self.manager.database.orphans()]
            if not targets:
                self._print(":: nothing to remove")
                return 0
        if not targets:
            self._error("no targets specified")
            return 1
        result = self.manager.remove(
            targets,
            cascade=request.has("cascade"),
            recursive=request.has("recursive") or request.has("search"),
            save=not request.has("nosave"),
        )
        return self._report_transaction(result)

    # --------------------------------------------------------------- upgrade
    def upgrade(self, request: CliRequest) -> int:
        if not request.targets:
            self._error("no package file specified")
            return 1
        status = 0
        for path in request.targets:
            try:
                result = self.manager.install_file(
                    path,
                    save=not request.has("nosave"),
                )
            except PackageError as exc:
                self._error(str(exc))
                status = 1
                continue
            status = max(status, self._report_transaction(result))
        return status

    # --------------------------------------------------------------- deptest
    def deptest(self, request: CliRequest) -> int:
        database = self.manager.database
        missing: list[str] = []
        if request.targets:
            for target in request.targets:
                record = database.find_by_name(target)
                if record is None:
                    found = self.manager.find_available(target)
                    package = found[1] if found else None
                else:
                    package = record.package
                if package is None:
                    missing.append(f"target not found: {target}")
                    continue
                for dependency in package.dependencies:
                    if database.find_satisfier(dependency) is None:
                        missing.append(f"{package.name}: {dependency.to_string()}")
        else:
            missing = self.manager.check_dependencies()
        for problem in missing:
            self._print(problem)
        return 1 if missing else 0

    # -------------------------------------------------------------- database
    def database(self, request: CliRequest) -> int:
        if request.has("check"):
            problems = self.manager.validate()
            for problem in problems:
                self._error(problem)
            return 1 if problems else 0
        if request.has("asdeps") or request.has("asexplicit"):
            reason = "dependency" if request.has("asdeps") else "explicit"
            if not request.targets:
                self._error("no package specified")
                return 1
            result = 0
            for target in request.targets:
                record = self.manager.database.find_by_name(target)
                if record is None:
                    self._error(f"package not found: {target}")
                    result = 1
                    continue
                self.manager.database.set_reason(record.id, reason)  # type: ignore[arg-type]
            self.manager.save()
            return result
        self.print_help()
        return 0

    # ----------------------------------------------------------------- files
    def files(self, request: CliRequest) -> int:
        if request.has("owner"):
            if not request.targets:
                self._error("no file specified")
                return 1
            result = 0
            for path in request.targets:
                record = self.manager.owner(path)
                if record is None:
                    self._error(f"no package owns {path}")
                    result = 1
                else:
                    self._print(f"{record.package.name} {record.package.version} owns {path}")
            return result
        if request.has("search"):
            query = " ".join(request.targets)
            if not query:
                self._error("no search query specified")
                return 1
            for path, package_id in sorted(self.manager.database.file_owners.items()):
                if query in path:
                    self._print(f"{package_id} {path}")
            return 0
        if request.has("list"):
            for path, package_id in sorted(self.manager.database.file_owners.items()):
                self._print(f"{package_id} {path}")
            return 0
        self.print_help()
        return 0

    # ------------------------------------------------------------- reporting
    def _report_transaction(self, result: Any) -> int:
        for problem in result.problems:
            self._error(problem)
        if result.rolled_back:
            self._warning("transaction rolled back")
        for package_id in result.installed:
            self._print(f":: installed {framework_base.escape(package_id)}")
        for package_id in result.removed:
            self._print(f":: removed {framework_base.escape(package_id)}")
        return 0 if result.success else 1


def register_pm_command(
    manager: PackageManager,
    name: str = "mpm",
    *,
    override: bool = False,
) -> CLIController:
    """Register a shell command that dispatches to *manager*."""
    controller = CLIController(manager, name=name)

    def _command(args: framework_base.Arguments) -> int:
        return controller.run([str(item) for item in args])

    framework_base.register(name, override=override)(_command)
    return controller
