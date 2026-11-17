"""
doas -su mylife.root
MPM compatibility facade.

The story's original ``MPMManager`` was a tiny dict holder:

- ``packages``: package id -> metadata
- ``registrys``: package id -> declared command names
- ``CheckRegistry``: verify declared commands exist

Real MPM registries also contain story-only command names that are never
implemented ("models", "systemutil", ...).  This facade therefore treats
missing registrations as *informational* by default; only ``strict=True``
raises ``UnregisteredCommand``.

FAQ♂
"""

from __future__ import annotations

from typing import Any

from .. import base as framework_base
from .database import Repository
from .errors import UnregisteredCommand
from .manager import PackageManager
from .package import Package


class MPMManager(PackageManager):
    """Story-compatible view over the new package manager."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    # ------------------------------------------------------------ story view
    @property
    def packages(self) -> dict[str, dict[str, Any]]:
        """Package id -> MPM-style metadata (available + installed)."""
        result: dict[str, dict[str, Any]] = {}
        for repository, package in self.repositories.all_packages():
            result[package.id] = self._mpm_metadata(package, repository.name)
        for record in self.database.installed.values():
            result[record.id] = self._mpm_metadata(record.package, "local")
        return result

    @property
    def registrys(self) -> dict[str, list[str]]:
        """Package id -> declared command names (story MPM spelling)."""
        result: dict[str, list[str]] = {}
        for repository, package in self.repositories.all_packages():
            result[package.id] = list(package.commands)
        for record in self.database.installed.values():
            result[record.id] = list(record.package.commands)
        return result

    @staticmethod
    def _mpm_metadata(package: Package, repository: str) -> dict[str, Any]:
        return {
            "Name": package.name,
            "Version": package.version,
            "Author": package.author,
            "Date": package.date,
            "Description": package.description,
            "Depends": list(package.depends),
            "Provides": list(package.provides),
            "Repository": repository or package.repository,
        }

    # -------------------------------------------------------------- registry
    def check_registry(self, strict: bool = False) -> list[str]:
        """Return declared commands that are not registered in the shell.

        Missing names are normally story-only fakes, so this is not an error
        unless ``strict=True``.
        """
        missing: list[tuple[str, str]] = []
        for package_id, commands in self.registrys.items():
            for command in commands:
                if command not in framework_base.registry:
                    missing.append((package_id, command))
        if strict and missing:
            rendered = ", ".join(
                f"{package_id}:{command}" for package_id, command in missing
            )
            raise UnregisteredCommand(
                "Package command(s) did not register: " + rendered
            )
        return [command for _package_id, command in missing]

    def CheckRegistry(self, strict: bool = False) -> bool:
        """Story-style CamelCase wrapper; lenient by default."""
        self.check_registry(strict=strict)
        return True

    # ------------------------------------------------------------- seeding
    def add_mpm_packages(
        self,
        packages: dict[str, dict[str, Any]],
        registrys: dict[str, list[str]] | None = None,
        repository: str = "mpm",
    ) -> Repository:
        """Import the story's MPM dicts as an ordinary repository."""
        registrys = registrys or {}
        parsed: dict[str, Package] = {}
        for package_id, metadata in packages.items():
            package = Package.from_dict(metadata, package_id)
            package.commands = list(registrys.get(package_id, package.commands))
            package.repository = repository
            parsed[package.id] = package
        repo = Repository(repository, parsed, priority=100)
        self.repositories.add(repo)
        self.store.save_repository(repo)
        return repo

    @classmethod
    def from_mpm(
        cls,
        packages: dict[str, dict[str, Any]],
        registrys: dict[str, list[str]] | None = None,
        **kwargs: Any,
    ) -> "MPMManager":
        manager = cls(**kwargs)
        manager.add_mpm_packages(packages, registrys)
        return manager
