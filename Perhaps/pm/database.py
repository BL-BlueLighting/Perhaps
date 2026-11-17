"""
doas -su mylife.root
Package database and repositories.

``PackageDatabase`` is the local installed set (what pacman keeps in
``/var/lib/pacman/local``); ``RepositorySet`` is the sync set (what pacman
keeps under ``/var/lib/pacman/sync``).  Both serialize to plain JSON-friendly
dicts so any storage backend can persist them.

I LOVE PACMAN ❤️
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from functools import cmp_to_key
from typing import Any, Iterable, Literal

from .errors import (
    ConflictError,
    DependencyError,
    FileConflict,
    PackageAlreadyInstalled,
    PackageNotFound,
)
from .package import Dependency, Package
from .version import compare_versions

InstallReason = Literal["explicit", "dependency"]


@dataclass
class PackageRecord:
    """One installed package plus local bookkeeping."""

    package: Package
    reason: InstallReason = "explicit"
    install_date: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat(timespec="seconds")
    )
    required_by: set[str] = field(default_factory=set)

    @property
    def id(self) -> str:
        return self.package.id

    @property
    def name(self) -> str:
        return self.package.name

    @property
    def version(self) -> str:
        return self.package.version

    @property
    def files(self) -> list[str]:
        return [file.path for file in self.package.files]

    def to_dict(self) -> dict[str, Any]:
        return {
            "package": self.package.to_dict(),
            "reason": self.reason,
            "install_date": self.install_date,
            "required_by": sorted(self.required_by),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PackageRecord":
        package_data = data["package"]
        package = (
            package_data
            if isinstance(package_data, Package)
            else Package.from_dict(package_data)
        )
        return cls(
            package=package,
            reason=str(data.get("reason", "explicit")),  # type: ignore[arg-type]
            install_date=str(data.get("install_date", "")),
            required_by=set(data.get("required_by", [])),
        )


class PackageDatabase:
    """Local installed-package database."""

    def __init__(self) -> None:
        self.installed: dict[str, PackageRecord] = {}
        self.file_owners: dict[str, str] = {}
        self.command_owners: dict[str, str] = {}

    # ------------------------------------------------------------- accessors
    def __len__(self) -> int:
        return len(self.installed)

    def __iter__(self):
        return iter(self.installed.values())

    def __contains__(self, package_id: object) -> bool:
        return package_id in self.installed

    def get(self, package_id: str) -> PackageRecord:
        try:
            return self.installed[package_id]
        except KeyError:
            raise PackageNotFound(package_id) from None

    def find_by_name(self, name: str) -> PackageRecord | None:
        for record in self.installed.values():
            if record.package.id == name or record.package.name == name:
                return record
        return None

    def find_satisfier(self, dependency: str | Dependency) -> PackageRecord | None:
        parsed = Dependency.parse(dependency)
        for record in self.installed.values():
            if parsed.satisfied_by(record.package):
                return record
        return None

    def owner_of(self, path: str) -> str | None:
        return self.file_owners.get(path)

    def command_owner(self, command: str) -> str | None:
        return self.command_owners.get(command)

    def search(self, query: str) -> list[PackageRecord]:
        value = query.lower()
        result = []
        for record in self.installed.values():
            package = record.package
            if (
                value in package.id.lower()
                or value in package.name.lower()
                or value in package.description.lower()
            ):
                result.append(record)
        return sorted(result, key=lambda record: record.package.name)

    def explicit(self) -> list[PackageRecord]:
        return sorted(
            (record for record in self.installed.values() if record.reason == "explicit"),
            key=lambda record: record.package.name,
        )

    def dependencies(self) -> list[PackageRecord]:
        return sorted(
            (record for record in self.installed.values() if record.reason == "dependency"),
            key=lambda record: record.package.name,
        )

    def orphans(self) -> list[PackageRecord]:
        return [
            record
            for record in self.installed.values()
            if not record.required_by and record.reason == "dependency"
        ]

    def groups(self) -> dict[str, list[PackageRecord]]:
        grouped: dict[str, list[PackageRecord]] = {}
        for record in self.installed.values():
            for group in record.package.groups:
                grouped.setdefault(group, []).append(record)
        for records in grouped.values():
            records.sort(key=lambda record: record.package.name)
        return grouped

    # -------------------------------------------------------------- mutation
    def add(
        self,
        package: Package,
        reason: InstallReason = "explicit",
        replace: bool = False,
    ) -> PackageRecord:
        if package.id in self.installed and not replace:
            raise PackageAlreadyInstalled(package.id)
        if replace:
            self.remove(package.id, missing_ok=True)

        for file in package.files:
            owner = self.file_owners.get(file.path)
            if owner is not None and owner != package.id:
                raise FileConflict(
                    f"file {file.path!r} is already owned by package {owner!r}"
                )
        record = PackageRecord(package=package, reason=reason)
        self.installed[package.id] = record
        for file in package.files:
            self.file_owners[file.path] = package.id
        for command in package.commands:
            self.command_owners[command] = package.id
        self.recompute_required_by()
        return record

    def remove(self, package_id: str, missing_ok: bool = False) -> PackageRecord | None:
        record = self.installed.pop(package_id, None)
        if record is None:
            if missing_ok:
                return None
            raise PackageNotFound(package_id)
        for path, owner in list(self.file_owners.items()):
            if owner == package_id:
                del self.file_owners[path]
        for command, owner in list(self.command_owners.items()):
            if owner == package_id:
                del self.command_owners[command]
        self.recompute_required_by()
        return record

    def set_reason(self, package_id: str, reason: InstallReason) -> None:
        self.get(package_id).reason = reason

    def recompute_required_by(self) -> None:
        for record in self.installed.values():
            record.required_by.clear()
        for record in self.installed.values():
            for dependency in record.package.dependencies:
                satisfier = self.find_satisfier(dependency)
                if satisfier is not None and satisfier.id != record.id:
                    satisfier.required_by.add(record.id)

    # ---------------------------------------------------------------- checks
    def missing_dependencies(self) -> list[str]:
        problems = []
        for record in self.installed.values():
            for dependency in record.package.dependencies:
                if self.find_satisfier(dependency) is None:
                    problems.append(
                        f"{record.package.id}: missing dependency {dependency.to_string()}"
                    )
        return problems

    def file_conflicts(self) -> list[str]:
        problems = []
        for record in self.installed.values():
            for file in record.package.files:
                owner = self.file_owners.get(file.path)
                if owner != record.package.id:
                    problems.append(
                        f"{record.package.id}: file {file.path} is owned by {owner!r}"
                    )
        return problems

    def validate(self) -> list[str]:
        return self.missing_dependencies() + self.file_conflicts()

    # ------------------------------------------------------------ persistence
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "installed": [record.to_dict() for record in self.installed.values()],
            "file_owners": dict(self.file_owners),
            "command_owners": dict(self.command_owners),
        }

    def load_dict(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("local database must be a JSON object")
        self.installed.clear()
        self.file_owners.clear()
        self.command_owners.clear()
        for raw in data.get("installed", []):
            record = PackageRecord.from_dict(raw)
            self.installed[record.id] = record
        for file in self.installed.values():
            for path in file.files:
                self.file_owners[path] = file.id
        for record in self.installed.values():
            for command in record.package.commands:
                self.command_owners[command] = record.id
        self.recompute_required_by()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PackageDatabase":
        database = cls()
        database.load_dict(data)
        return database


@dataclass
class Repository:
    """A sync repository: package id -> metadata (payload optional)."""

    name: str
    packages: dict[str, Package] = field(default_factory=dict)
    priority: int = 0
    server: str = ""

    def __post_init__(self) -> None:
        self.name = str(self.name)
        cleaned: dict[str, Package] = {}
        for key, value in self.packages.items():
            package = value if isinstance(value, Package) else Package.from_dict(value, str(key))
            if not package.repository:
                package.repository = self.name
            cleaned[package.id] = package
        self.packages = cleaned

    def __len__(self) -> int:
        return len(self.packages)

    def __iter__(self):
        return iter(self.packages.values())

    def get(self, package_id: str) -> Package:
        try:
            return self.packages[package_id]
        except KeyError:
            raise PackageNotFound(package_id) from None

    def find_by_name(self, name: str) -> list[Package]:
        result = []
        for package in self.packages.values():
            if package.id == name or package.name == name:
                result.append(package)
        return result

    def find_satisfying(self, dependency: str | Dependency) -> list[Package]:
        parsed = Dependency.parse(dependency)
        return [
            package
            for package in self.packages.values()
            if parsed.satisfied_by(package)
        ]

    def search(self, query: str) -> list[Package]:
        value = query.lower()
        return sorted(
            (
                package
                for package in self.packages.values()
                if value in package.id.lower()
                or value in package.name.lower()
                or value in package.description.lower()
            ),
            key=lambda package: package.name,
        )

    def to_dict(self, include_files: bool = False) -> dict[str, Any]:
        return {
            "version": 1,
            "name": self.name,
            "priority": self.priority,
            "server": self.server,
            "packages": [
                package.to_dict(include_files=include_files)
                for package in self.packages.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Repository":
        packages: dict[str, Package] = {}
        raw_packages = data.get("packages", {})
        if isinstance(raw_packages, dict):
            iterator: Iterable = raw_packages.items()
        else:
            iterator = ((None, item) for item in raw_packages)
        for key, value in iterator:
            package = value if isinstance(value, Package) else Package.from_dict(value, key)
            packages[package.id] = package
        return cls(
            name=str(data.get("name", "unnamed")),
            packages=packages,
            priority=int(data.get("priority", 0)),
            server=str(data.get("server", "")),
        )


class RepositorySet:
    """Ordered collection of repositories with pacman-ish candidate lookup."""

    def __init__(self, repositories: Iterable[Repository] = ()) -> None:
        self.repositories: dict[str, Repository] = {}
        for repository in repositories:
            self.add(repository)

    def __len__(self) -> int:
        return len(self.repositories)

    def __iter__(self):
        return iter(self.repositories.values())

    def __contains__(self, name: object) -> bool:
        return name in self.repositories

    def add(self, repository: Repository) -> None:
        self.repositories[repository.name] = repository

    def remove(self, name: str) -> Repository:
        try:
            return self.repositories.pop(name)
        except KeyError:
            raise PackageNotFound(name) from None

    def get(self, name: str) -> Repository:
        try:
            return self.repositories[name]
        except KeyError:
            raise PackageNotFound(name) from None

    def names(self) -> list[str]:
        return list(self.repositories)

    def candidates(
        self,
        name: str,
        include_provides: bool = True,
    ) -> list[tuple[Repository, Package]]:
        """All packages matching *name* (optionally via provides)."""
        result: list[tuple[Repository, Package]] = []
        for repository in self.repositories.values():
            for package in repository.packages.values():
                if package.id == name or package.name == name:
                    result.append((repository, package))
                elif include_provides:
                    provided_names = []
                    for provided in package.provides:
                        try:
                            provided_names.append(Dependency.parse(provided).name)
                        except Exception:
                            continue
                    if name in provided_names:
                        result.append((repository, package))
        result.sort(key=cmp_to_key(self._compare_candidates))
        return result

    @staticmethod
    def _compare_candidates(
        left: tuple[Repository, Package],
        right: tuple[Repository, Package],
    ) -> int:
        if left[0].priority != right[0].priority:
            return -1 if left[0].priority > right[0].priority else 1
        return -compare_versions(left[1].version, right[1].version)

    def candidates_for(
        self,
        dependency: str | Dependency,
        include_provides: bool = True,
    ) -> list[tuple[Repository, Package]]:
        parsed = Dependency.parse(dependency)
        result: list[tuple[Repository, Package]] = []
        for repository in self.repositories.values():
            for package in repository.packages.values():
                if parsed.satisfied_by(package):
                    result.append((repository, package))
        result.sort(key=cmp_to_key(self._compare_candidates))
        return result

    def best(
        self,
        name: str,
        include_provides: bool = True,
    ) -> tuple[Repository, Package] | None:
        candidates = self.candidates(name, include_provides)
        return candidates[0] if candidates else None

    def search(self, query: str) -> list[tuple[Repository, Package]]:
        result: list[tuple[Repository, Package]] = []
        seen: set[tuple[str, str]] = set()
        for repository in self.repositories.values():
            for package in repository.search(query):
                key = (repository.name, package.id)
                if key in seen:
                    continue
                seen.add(key)
                result.append((repository, package))
        return result

    def upgrades_for(self, database: PackageDatabase) -> list[tuple[Repository, Package, PackageRecord]]:
        result = []
        for record in database.installed.values():
            candidates = self.candidates_for(record.package.id)
            if not candidates:
                candidates = self.candidates_for(record.package.name)
            for repository, package in candidates:
                if package.id != record.package.id:
                    continue
                if compare_versions(package.version, record.package.version) > 0:
                    result.append((repository, package, record))
                    break
        return result

    def all_packages(self) -> list[tuple[Repository, Package]]:
        return [
            (repository, package)
            for repository in self.repositories.values()
            for package in repository.packages.values()
        ]
