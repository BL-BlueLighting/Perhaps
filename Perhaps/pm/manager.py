"""
doas -su mylife.root
Package manager facade.

``PackageManager`` wires together the database, repositories, resolver,
transaction/backend and hooks.  Everything can be replaced:

- ``database`` / ``repositories``: pre-built objects;
- ``backend``: file+command storage;
- ``store``: persistence of local/sync databases;
- ``hooks``: transaction hooks;
- ``resolver_class`` / ``transaction_class``: custom policy/execution.

The default manager is quiet and import-safe; call :meth:`load` when you want
to read persisted state, and :meth:`save` after changes.

Dear user, I am your package manager. 😎
(以防你不知道这句话我其实想模仿破壁人来着)
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterable

from .backends import MemoryBackend, PackageBackend, VirtualFSBackend
from .database import PackageDatabase, PackageRecord, Repository, RepositorySet
from .errors import PackageError, PackageNotFound, VersionError
from .hooks import HookManager
from .package import Dependency, Package
from .resolver import ResolvePlan, Resolver
from .sources import DictSource, PackageSource
from .store import MemoryStore, PackageStore, VirtualFSStore
from .transaction import Transaction, TransactionResult


class PackageManager:
    def __init__(
        self,
        database: PackageDatabase | None = None,
        repositories: RepositorySet | None = None,
        backend: PackageBackend | None = None,
        store: PackageStore | None = None,
        hooks: HookManager | None = None,
        *,
        resolver_class: type[Resolver] = Resolver,
        transaction_class: type[Transaction] = Transaction,
        allow_unowned_overwrite: bool = False,
        console: Any = None,
    ) -> None:
        self.database = database or PackageDatabase()
        self.repositories = repositories or RepositorySet()
        self.backend = backend or VirtualFSBackend()
        if store is None:
            store = MemoryStore() if isinstance(self.backend, MemoryBackend) else VirtualFSStore(self.backend)
        self.store = store
        self.hooks = hooks or HookManager()
        self.resolver_class = resolver_class
        self.transaction_class = transaction_class
        self.allow_unowned_overwrite = allow_unowned_overwrite
        self.console = console
        self.sources: dict[str, PackageSource] = {}

    # ------------------------------------------------------------ persistence
    def load(self) -> None:
        data = self.store.load_local()
        if data:
            self.database.load_dict(data)
        for name in self.store.repository_names():
            raw = self.store.load_repository(name)
            if raw is not None:
                self.repositories.add(Repository.from_dict(raw))

    def save(self) -> None:
        self.store.save_local(self.database.to_dict())
        for repository in self.repositories:
            self.store.save_repository(repository)

    # ------------------------------------------------------------ repositories
    def add_source(
        self,
        name: str,
        source: PackageSource | Any,
        priority: int = 0,
        *,
        refresh: bool = True,
        persist: bool = True,
    ) -> Repository:
        if not isinstance(source, PackageSource):
            source = DictSource(name, source, priority=priority)
        source.name = name
        source.priority = priority
        self.sources[name] = source
        if refresh:
            return self.refresh(name, persist=persist)
        repository = source.load()
        repository.name = name
        repository.priority = priority
        self.repositories.add(repository)
        if persist:
            self.store.save_repository(repository)
        return repository

    def refresh(self, name: str | None = None, *, persist: bool = True) -> Repository | list[Repository]:
        names = [name] if name is not None else list(self.sources)
        refreshed: list[Repository] = []
        for repo_name in names:
            source = self.sources.get(repo_name)
            if source is None:
                raise PackageError(f"unknown source: {repo_name}")
            repository = source.refresh()
            repository.name = repo_name
            repository.priority = source.priority
            self.repositories.add(repository)
            if persist:
                self.store.save_repository(repository)
            refreshed.append(repository)
        if name is not None:
            return refreshed[0]
        return refreshed

    def add_repository(
        self,
        name: str,
        data: Any,
        priority: int = 0,
        *,
        persist: bool = True,
    ) -> Repository:
        return self.add_source(
            name,
            DictSource(name, data, priority=priority),
            priority=priority,
            refresh=True,
            persist=persist,
        )

    def add_package(
        self,
        package: Package | dict[str, Any],
        repository: str = "local",
        priority: int = 50,
        *,
        persist: bool = True,
    ) -> Package:
        if not isinstance(package, Package):
            package = Package.from_dict(package)
        repo = self.repositories.repositories.get(repository)
        if repo is None:
            repo = Repository(repository, {}, priority=priority)
            self.repositories.add(repo)
        repo.packages[package.id] = package
        package.repository = repository
        if persist:
            self.store.save_repository(repo)
        return package

    # ------------------------------------------------------------------ query
    def find_installed(self, name: str) -> PackageRecord | None:
        return self.database.find_by_name(name)

    def find_available(self, name: str) -> tuple[Repository, Package] | None:
        return self.repositories.best(name)

    def search(self, query: str, installed: bool = False) -> list[Any]:
        if installed:
            return self.database.search(query)
        return self.repositories.search(query)

    def installed_packages(self) -> list[PackageRecord]:
        return sorted(self.database.installed.values(), key=lambda record: record.package.name)

    def available_packages(self) -> list[tuple[Repository, Package]]:
        return sorted(
            self.repositories.all_packages(),
            key=lambda item: (item[1].name, item[0].name),
        )

    def package_info(self, name: str, installed: bool = False) -> Package:
        if installed:
            record = self.database.find_by_name(name)
            if record is None:
                raise PackageNotFound(name)
            return record.package
        found = self.repositories.best(name)
        if found is None:
            raise PackageNotFound(name)
        return found[1]

    def files(self, name: str, installed: bool = True) -> list[str]:
        if installed:
            record = self.database.find_by_name(name)
            if record is None:
                raise PackageNotFound(name)
            return record.files
        package = self.package_info(name, installed=False)
        return [file.path for file in package.files]

    def owner(self, path: str) -> PackageRecord | None:
        package_id = self.database.owner_of(path)
        return self.database.installed.get(package_id) if package_id else None

    def groups(self, installed: bool = True) -> dict[str, list[Any]]:
        if installed:
            return self.database.groups()
        grouped: dict[str, list[Package]] = {}
        for repository, package in self.repositories.all_packages():
            for group in package.groups:
                grouped.setdefault(group, []).append(package)
        return grouped

    def validate(self) -> list[str]:
        return self.database.validate()

    # -------------------------------------------------------------- mutations
    def _reasons_for(self, plan: ResolvePlan, targets: Iterable[str]) -> dict[str, str]:
        explicit = list(targets)
        reasons: dict[str, str] = {}
        for package in plan.installs:
            record = self.database.installed.get(package.id)
            if record is not None:
                reasons[package.id] = record.reason
                continue
            is_explicit = False
            for target in explicit:
                if package.id == target or package.name == target:
                    is_explicit = True
                    break
                try:
                    if package.satisfies(target):
                        is_explicit = True
                        break
                except VersionError:
                    continue
            reasons[package.id] = "explicit" if is_explicit else "dependency"
        return reasons

    def _execute(
        self,
        plan: ResolvePlan,
        *,
        reasons: dict[str, str] | None = None,
        save: bool = True,
    ) -> TransactionResult:
        if plan.problems:
            return TransactionResult(success=False, problems=list(plan.problems))
        transaction = self.transaction_class(
            self.backend,
            self.database,
            self.hooks,
            self,
        )
        result = transaction.execute(plan, reasons=reasons, save=False)
        if result.success and save:
            self.save()
        return result

    def install(
        self,
        targets: list[str],
        *,
        reason: str = "explicit",
        allow_downgrade: bool = False,
        needed: bool = False,
        save: bool = True,
    ) -> TransactionResult:
        resolver = self.resolver_class(
            self.database,
            self.repositories,
            allow_downgrade=allow_downgrade,
            needed=needed,
        )
        plan = resolver.resolve_install(targets, allow_downgrade=allow_downgrade, needed=needed)
        reasons = self._reasons_for(plan, targets)
        if reason != "explicit":
            for package_id in reasons:
                reasons[package_id] = reason
        return self._execute(plan, reasons=reasons, save=save)

    def upgrade(
        self,
        *,
        allow_downgrade: bool = False,
        save: bool = True,
    ) -> TransactionResult:
        resolver = self.resolver_class(
            self.database,
            self.repositories,
            allow_downgrade=allow_downgrade,
            needed=True,
        )
        plan = resolver.resolve_upgrade(allow_downgrade=allow_downgrade)
        if not plan.installs and not plan.removals and not plan.problems:
            return TransactionResult(success=True, details=["nothing to do"])
        reasons = {
            record.id: record.reason for record in self.database.installed.values()
        }
        return self._execute(plan, reasons=reasons, save=save)

    def remove(
        self,
        targets: list[str],
        *,
        cascade: bool = False,
        recursive: bool = False,
        save: bool = True,
    ) -> TransactionResult:
        resolver = self.resolver_class(self.database, self.repositories)
        plan = resolver.resolve_remove(targets, cascade=cascade, recursive=recursive)
        return self._execute(plan, save=save)

    def load_package_file(self, path_or_data: str | dict[str, Any] | Package) -> Package:
        if isinstance(path_or_data, Package):
            return path_or_data
        if isinstance(path_or_data, dict):
            return Package.from_dict(path_or_data)
        text = ""
        try:
            if self.backend.exists(path_or_data):
                text = self.backend.read_file(path_or_data)
            elif os.path.isfile(path_or_data):
                with open(path_or_data, "r", encoding="utf-8") as fh:
                    text = fh.read()
        except Exception as exc:
            raise PackageError(f"could not read package file {path_or_data!r}: {exc}") from exc
        if not text:
            raise PackageError(f"package file not found: {path_or_data!r}")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PackageError(f"invalid package JSON in {path_or_data!r}: {exc}") from exc
        if isinstance(data, list):
            if len(data) != 1:
                raise PackageError(
                    f"{path_or_data!r} contains {len(data)} packages; "
                    "use a repository source for collections"
                )
            data = data[0]
        return Package.from_dict(data)

    def install_file(
        self,
        path_or_data: str | dict[str, Any] | Package,
        *,
        save: bool = True,
    ) -> TransactionResult:
        package = self.load_package_file(path_or_data)
        if not package.repository:
            package.repository = "__local__"
        self.add_package(package, repository="__local__", persist=False)
        result = self.install([package.id], save=save)
        return result

    def check_dependencies(self) -> list[str]:
        return self.resolver_class(self.database, self.repositories).check_dependencies()

    # ------------------------------------------------------------------- mpm
    def register_commands(
        self,
        name: str = "mpm",
        *,
        override: bool = False,
    ) -> "PackageManager":
        from .cli import register_pm_command

        register_pm_command(self, name=name, override=override)
        return self
