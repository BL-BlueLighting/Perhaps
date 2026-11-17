"""
doas -su mylife.root
Package sources.

A source turns *something* (a dict, a JSON document, a virtual file, a host
file, a callback, a network driver you write yourself) into a ``Repository``.
The manager only knows this tiny interface, so adding a new source never
requires editing the rest of the package manager.

do you know if you want you can make a website for your package source?
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Callable

from .database import Repository
from .errors import RepositoryError, SourceError
from .package import Package


def repository_from_data(
    name: str,
    data: Any,
    priority: int = 0,
    server: str = "",
) -> Repository:
    """Build a repository from an MPM-ish dict/list/JSON-decoded object."""
    if isinstance(data, Repository):
        data.name = name
        data.priority = priority
        data.server = server or data.server
        return data
    if isinstance(data, list):
        packages: dict[str, Package] = {}
        for item in data:
            package = item if isinstance(item, Package) else Package.from_dict(item)
            packages[package.id] = package
        return Repository(name, packages, priority, server)
    if not isinstance(data, dict):
        raise SourceError(f"repository data for {name!r} must be a mapping or list")
    if "packages" in data and isinstance(data["packages"], (dict, list)):
        raw_packages = data["packages"]
        packages = {}
        if isinstance(raw_packages, dict):
            iterator = raw_packages.items()
        else:
            iterator = ((None, item) for item in raw_packages)
        for key, item in iterator:
            package = item if isinstance(item, Package) else Package.from_dict(item, key)
            packages[package.id] = package
        return Repository(
            name=str(data.get("name", name)),
            packages=packages,
            priority=int(data.get("priority", priority)),
            server=str(data.get("server", server)),
        )
    # A bare mapping package-id -> package data is also accepted.
    packages = {}
    for key, item in data.items():
        package = item if isinstance(item, Package) else Package.from_dict(item, str(key))
        packages[package.id] = package
    return Repository(name, packages, priority, server)


class PackageSource(ABC):
    """Minimal source interface: ``load()`` returns a Repository."""

    def __init__(self, name: str, priority: int = 0, server: str = "") -> None:
        self.name = name
        self.priority = priority
        self.server = server

    @abstractmethod
    def load(self) -> Repository:
        """Return the repository offered by this source."""

    def refresh(self) -> Repository:
        """Default refresh is just a reload; override for network sources."""
        return self.load()


class DictSource(PackageSource):
    """In-memory dict/list source, handy for story code and tests."""

    def __init__(
        self,
        name: str,
        data: Any,
        priority: int = 0,
        server: str = "",
    ) -> None:
        super().__init__(name, priority, server)
        self.data = data

    def load(self) -> Repository:
        return repository_from_data(self.name, self.data, self.priority, self.server)


class CallbackSource(PackageSource):
    """A source backed by an arbitrary ``loader() -> Repository`` callable."""

    def __init__(
        self,
        name: str,
        loader: Callable[[], Repository | dict | list],
        priority: int = 0,
        server: str = "",
    ) -> None:
        super().__init__(name, priority, server)
        self.loader = loader

    def load(self) -> Repository:
        try:
            data = self.loader()
        except Exception as exc:
            raise SourceError(f"source {self.name!r} failed: {exc}") from exc
        return repository_from_data(self.name, data, self.priority, self.server)


class JsonTextSource(PackageSource):
    """Source from a JSON string."""

    def __init__(
        self,
        name: str,
        text: str,
        priority: int = 0,
        server: str = "",
    ) -> None:
        super().__init__(name, priority, server)
        self.text = text

    def load(self) -> Repository:
        try:
            data = json.loads(self.text)
        except json.JSONDecodeError as exc:
            raise SourceError(f"source {self.name!r} has invalid JSON: {exc}") from exc
        return repository_from_data(self.name, data, self.priority, self.server)


class HostJsonSource(JsonTextSource):
    """Read a repository JSON file from the host file system.

    This is intentionally not used by the virtual-file-system backend; it is
    provided for tools that build a repository outside the game world.
    """

    def __init__(
        self,
        name: str,
        path: str,
        priority: int = 0,
        server: str = "",
    ) -> None:
        self.path = path
        text = ""
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        else:
            raise SourceError(f"repository file does not exist: {path!r}")
        super().__init__(name, text, priority, server)


class VirtualFSJsonSource(PackageSource):
    """Read a repository JSON file from the game's virtual file system."""

    def __init__(
        self,
        name: str,
        path: str,
        priority: int = 0,
        server: str = "",
        file_system: Any = None,
    ) -> None:
        super().__init__(name, priority, server)
        self.path = path
        self.file_system = file_system

    def load(self) -> Repository:
        from .. import fileutil

        file_system = self.file_system or fileutil.fs
        try:
            text = file_system.ReadFile(self.path, str, "system")
        except Exception as exc:
            raise SourceError(
                f"virtual repository {self.path!r} could not be read: {exc}"
            ) from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SourceError(f"source {self.name!r} has invalid JSON: {exc}") from exc
        return repository_from_data(self.name, data, self.priority, self.server)


class CompositeSource(PackageSource):
    """Merge several sources into one repository."""

    def __init__(
        self,
        name: str,
        sources: list[PackageSource],
        priority: int = 0,
        server: str = "",
    ) -> None:
        super().__init__(name, priority, server)
        self.sources = sources

    def load(self) -> Repository:
        packages: dict[str, Package] = {}
        for source in self.sources:
            repository = source.load()
            for package in repository:
                packages[package.id] = package
        return Repository(self.name, packages, self.priority, self.server)
