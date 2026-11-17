"""
doas -su mylife.root
Package model.

The shape mirrors the story's ``MPMManager`` metadata enough to be familiar
(``Name`` / ``Version`` / ``Author`` / ``Date``) but adds the pieces a real
package manager needs: dependencies, conflicts, provides, files, commands and
free-form ``extra`` metadata.

笑点解析：我忘了笑点解析的英文怎么打
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import VersionError
from .version import check_constraint, compare_versions

from ..fileutil import PermEnum

CommandHandler = Callable[[Any], Any]

DEFAULT_FILE_PERMISSIONS = (PermEnum.Readable, PermEnum.Listable)
DEFAULT_DIR_PERMISSIONS = (PermEnum.Readable, PermEnum.Listable, PermEnum.Writable)

_PACKAGED_KINDS = ("file", "directory", "symlink")


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def normalize_package_path(path: str) -> str:
    """Normalize a payload path into a virtual absolute path."""
    value = posixpath.normpath(str(path))
    if value in ("", "."):
        return "/"
    if not value.startswith("/"):
        value = "/" + value
    return value


def _permission_name(permission: PermEnum | str | int) -> str:
    if isinstance(permission, PermEnum):
        return permission.name
    if isinstance(permission, str):
        if permission in PermEnum.__members__:
            return permission
        try:
            return PermEnum[int(permission)].name
        except (ValueError, KeyError):
            raise ValueError(f"unknown permission: {permission!r}") from None
    if isinstance(permission, int):
        try:
            return PermEnum(permission).name
        except ValueError:
            raise ValueError(f"unknown permission: {permission!r}") from None
    raise TypeError(f"unknown permission: {permission!r}")


@dataclass
class PackageFile:
    """One file/directory/symlink shipped by a package."""

    path: str
    content: str | list[str] = ""
    kind: str = "file"
    target: str = ""
    owner: str = "root"
    permissions: list[PermEnum] = field(default_factory=lambda: list(DEFAULT_FILE_PERMISSIONS))

    def __post_init__(self) -> None:
        self.path = normalize_package_path(self.path)
        self.kind = str(self.kind or "file").lower()
        if self.kind not in _PACKAGED_KINDS:
            raise ValueError(f"unknown package file kind: {self.kind!r}")
        if self.kind == "directory":
            self.permissions = list(DEFAULT_DIR_PERMISSIONS)
        elif self.kind == "symlink":
            self.target = normalize_package_path(self.target)
        normalized_permissions: list[PermEnum] = []
        for permission in self.permissions:
            normalized_permissions.append(PermEnum[_permission_name(permission)])
        self.permissions = normalized_permissions
        if isinstance(self.content, (tuple, list)):
            self.content = [str(line) for line in self.content]
        elif self.content is None:
            self.content = []
        else:
            self.content = str(self.content)

    @property
    def content_lines(self) -> list[str]:
        if isinstance(self.content, list):
            return self.content
        return self.content.splitlines() or [""]

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "path": self.path,
            "kind": self.kind,
            "owner": self.owner,
            "permissions": [_permission_name(permission) for permission in self.permissions],
        }
        if self.kind == "symlink":
            data["target"] = self.target
        else:
            data["content"] = self.content
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> "PackageFile":
        if isinstance(data, str):
            data = {"path": data}
        permissions = [
            PermEnum[_permission_name(permission)] for permission in data.get("permissions", [])
        ]
        return cls(
            path=str(data["path"]),
            content=data.get("content", ""),
            kind=str(data.get("kind", "file")),
            target=str(data.get("target", "")),
            owner=str(data.get("owner", "root")),
            permissions=permissions or list(DEFAULT_FILE_PERMISSIONS),
        )


@dataclass(frozen=True)
class Dependency:
    """A package dependency such as ``foo`` or ``bar>=1.2-3``."""

    name: str
    operator: str = ""
    version: str = ""
    description: str = ""

    @classmethod
    def parse(cls, value: str | "Dependency") -> "Dependency":
        if isinstance(value, Dependency):
            return value
        text = str(value).strip()
        if not text:
            raise VersionError("empty dependency")
        description = ""
        if ": " in text:
            left, right = text.split(": ", 1)
            text, description = left.strip(), right.strip()
        for operator in (">=", "<=", "==", "!=", "=", ">", "<"):
            if operator in text:
                name, version = text.split(operator, 1)
                name = name.strip()
                version = version.strip()
                if not name:
                    raise VersionError(f"invalid dependency: {value!r}")
                return cls(name, operator, version, description)
        return cls(text, "", "", description)

    def constraint_satisfied(self, version: str) -> bool:
        return check_constraint(version, self.operator, self.version)

    def satisfied_by(self, package: "Package") -> bool:
        if package.id == self.name or package.name == self.name:
            return self.constraint_satisfied(package.version)
        for provided in package.provides:
            try:
                item = Dependency.parse(provided)
            except VersionError:
                continue
            if item.name != self.name:
                continue
            if not self.operator:
                return True
            if item.operator and item.version:
                return self.constraint_satisfied(item.version)
        return False

    def to_string(self) -> str:
        return f"{self.name}{self.operator}{self.version}" if self.operator else self.name


@dataclass
class Package:
    """A package definition (repository metadata + optional payload)."""

    id: str
    name: str
    version: str
    author: str = ""
    date: str = ""
    description: str = ""
    url: str = ""
    license: str = "MIT"
    groups: list[str] = field(default_factory=list)
    depends: list[str] = field(default_factory=list)
    optdepends: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)
    replaces: list[str] = field(default_factory=list)
    files: list[PackageFile] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    handlers: dict[str, CommandHandler] = field(default_factory=dict, repr=False)
    repository: str = ""

    def __post_init__(self) -> None:
        self.id = str(self.id).strip()
        self.name = str(self.name).strip()
        if not self.id or not self.name:
            raise ValueError("package id and name must not be empty")
        self.version = str(self.version)
        self.depends = _as_list(self.depends)
        self.optdepends = _as_list(self.optdepends)
        self.conflicts = _as_list(self.conflicts)
        self.provides = _as_list(self.provides)
        self.replaces = _as_list(self.replaces)
        self.commands = _as_list(self.commands)
        self.hooks = _as_list(self.hooks)
        self.groups = _as_list(self.groups)
        self.files = [
            item if isinstance(item, PackageFile) else PackageFile.from_dict(item)
            for item in self.files
        ]
        self.handlers = {
            str(name): handler for name, handler in (self.handlers or {}).items()
        }

    @property
    def full_name(self) -> str:
        return f"{self.name}-{self.version}"

    @property
    def dependencies(self) -> list[Dependency]:
        return [Dependency.parse(item) for item in self.depends]

    def conflict_matches(self, other: "Package") -> bool:
        for value in self.conflicts:
            try:
                dependency = Dependency.parse(value)
            except VersionError:
                continue
            if dependency.satisfied_by(other):
                return True
        return False

    def replaces_package(self, other: "Package") -> bool:
        for value in self.replaces:
            try:
                dependency = Dependency.parse(value)
            except VersionError:
                continue
            if dependency.satisfied_by(other):
                return True
        return False

    def satisfies(self, dependency: str | Dependency) -> bool:
        return Dependency.parse(dependency).satisfied_by(self)

    def newer_than(self, other: "Package") -> bool:
        return compare_versions(self.version, other.version) > 0

    def to_dict(self, include_files: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "date": self.date,
            "description": self.description,
            "url": self.url,
            "license": self.license,
            "groups": list(self.groups),
            "depends": list(self.depends),
            "optdepends": list(self.optdepends),
            "conflicts": list(self.conflicts),
            "provides": list(self.provides),
            "replaces": list(self.replaces),
            "commands": list(self.commands),
            "hooks": list(self.hooks),
            "metadata": dict(self.metadata),
        }
        if include_files:
            data["files"] = [file.to_dict() for file in self.files]
        if self.repository:
            data["repository"] = self.repository
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any], package_id: str | None = None) -> "Package":
        """Build a package from MPM-style (Name/Version) or snake_case data."""
        if not isinstance(data, dict):
            raise TypeError("package data must be a mapping")
        package_id = package_id or data.get("id") or data.get("Name") or data.get("name")
        if not package_id:
            raise ValueError("package data is missing id/name")
        handlers = data.get("handlers", {})
        if not isinstance(handlers, dict):
            handlers = {}
        return cls(
            id=str(package_id),
            name=str(data.get("name", data.get("Name", package_id))),
            version=str(data.get("version", data.get("Version", "0"))),
            author=str(data.get("author", data.get("Author", ""))),
            date=str(data.get("date", data.get("Date", ""))),
            description=str(data.get("description", data.get("Description", ""))),
            url=str(data.get("url", data.get("URL", ""))),
            license=str(data.get("license", data.get("License", "MIT"))),
            groups=_as_list(data.get("groups", data.get("Groups"))),
            depends=_as_list(data.get("depends", data.get("Depends"))),
            optdepends=_as_list(data.get("optdepends", data.get("OptDepends"))),
            conflicts=_as_list(data.get("conflicts", data.get("Conflicts"))),
            provides=_as_list(data.get("provides", data.get("Provides"))),
            replaces=_as_list(data.get("replaces", data.get("Replaces"))),
            files=[
                item if isinstance(item, PackageFile) else PackageFile.from_dict(item)
                for item in data.get("files", data.get("Files", [])) or []
            ],
            commands=_as_list(data.get("commands", data.get("Commands"))),
            hooks=_as_list(data.get("hooks", data.get("Hooks"))),
            metadata=dict(data.get("metadata", data.get("Metadata", {})) or {}),
            handlers={str(name): handler for name, handler in handlers.items()},
            repository=str(data.get("repository", data.get("Repository", ""))),
        )

    def copy_with(self, **changes: Any) -> "Package":
        data = self.to_dict()
        data.update(changes)
        return Package.from_dict(data)
