"""
doas -su mylife.root
Package backends.

The package manager does not know how your world stores files or commands.
``PackageBackend`` is the small surface a transaction needs; the default
``VirtualFSBackend`` writes into ``Perhaps.fileutil``'s virtual file system and
registers commands in ``Perhaps.base.registry``.  ``MemoryBackend`` is useful
for tools/tests/custom worlds.

does anyone cares my English syntax 😢
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from .. import base as framework_base
from .. import fileutil
from ..fileutil import FileSystemPath, PermEnum

CommandHandler = Callable[[Any], Any]


def _content_lines(content: Any) -> list[str]:
    if isinstance(content, (list, tuple)):
        return [str(line) for line in content]
    if content is None:
        return [""]
    return str(content).splitlines() or [""]


def _permissions(values: list[PermEnum] | None) -> list[PermEnum]:
    return list(values) if values else [PermEnum.Readable, PermEnum.Listable]


class PackageBackend(ABC):
    """File + command operations required by ``Transaction``."""

    # ------------------------------------------------------------------ files
    @abstractmethod
    def exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def is_dir(self, path: str) -> bool:
        ...

    @abstractmethod
    def ensure_directory(self, path: str) -> None:
        ...

    @abstractmethod
    def write_file(
        self,
        path: str,
        content: Any,
        owner: str = "root",
        permissions: list[PermEnum] | None = None,
    ) -> None:
        ...

    @abstractmethod
    def read_file(self, path: str) -> str:
        ...

    @abstractmethod
    def remove_path(self, path: str, missing_ok: bool = True) -> None:
        ...

    @abstractmethod
    def list_dir(self, path: str) -> list[str]:
        ...

    # ---------------------------------------------------------------- rollback
    @abstractmethod
    def snapshot(self, path: str) -> Any:
        ...

    @abstractmethod
    def restore(self, path: str, snapshot: Any) -> None:
        ...

    # --------------------------------------------------------------- commands
    @abstractmethod
    def register_command(self, name: str, handler: CommandHandler, override: bool = False) -> None:
        ...

    @abstractmethod
    def unregister_command(self, name: str) -> None:
        ...

    @abstractmethod
    def command_exists(self, name: str) -> bool:
        ...

    @abstractmethod
    def snapshot_commands(self) -> Any:
        ...

    @abstractmethod
    def restore_commands(self, snapshot: Any) -> None:
        ...


class VirtualFSBackend(PackageBackend):
    """Backend that writes to the game's virtual file system."""

    def __init__(self, file_system: Any = None, root: str = "/") -> None:
        self.file_system = file_system
        self.root = str(FileSystemPath(root))
        self._owned_commands: dict[str, CommandHandler] = {}

    @property
    def fs(self):
        return self.file_system or fileutil.fs

    def resolve(self, path: str) -> str:
        value = str(FileSystemPath(path))
        if self.root != "/" and not value.startswith(self.root.rstrip("/") + "/"):
            value = str(FileSystemPath(self.root.rstrip("/") + "/" + value.lstrip("/")))
        return value

    def _entry(self, path: str):
        resolved = self.resolve(path)
        parsed = FileSystemPath(resolved)
        parent = str(parsed.parent)
        if parent not in self.fs.files:
            return None
        try:
            return self.fs.files[parent].__getitem__(parsed.name, True)
        except (ValueError, IndexError):
            return None

    def exists(self, path: str) -> bool:
        resolved = self.resolve(path)
        return resolved == "/" or resolved in self.fs.directories or self._entry(resolved) is not None

    def is_dir(self, path: str) -> bool:
        return self.resolve(path) in self.fs.directories

    def ensure_directory(self, path: str) -> None:
        resolved = self.resolve(path)
        if self.is_dir(resolved):
            return
        if resolved == "/":
            self.fs.AddDirectory("/", access="system")
            return
        if self.exists(resolved):
            raise ValueError(f"{resolved!r} exists and is not a directory")
        parsed = FileSystemPath(resolved)
        parent = str(parsed.parent)
        if parent != resolved:
            self.ensure_directory(parent)
        try:
            fileutil.CreateDirectory("", "", full_path=resolved, target=self.fs, access="system")
        except fileutil.FileOrDirectoryAlreadyExists:
            if not self.is_dir(resolved):
                raise
        except Exception as exc:
            raise ValueError(f"could not create directory {resolved!r}: {exc}") from exc

    def write_file(
        self,
        path: str,
        content: Any,
        owner: str = "root",
        permissions: list[PermEnum] | None = None,
    ) -> None:
        resolved = self.resolve(path)
        if self.is_dir(resolved):
            raise ValueError(f"{resolved!r} is a directory")
        parsed = FileSystemPath(resolved)
        parent = str(parsed.parent)
        self.ensure_directory(parent)
        lines = _content_lines(content)
        perms = _permissions(permissions)
        if self.exists(resolved):
            fileutil.WriteFile(
                parent,
                parsed.name,
                file_content=lines,
                file_owner=[owner],
                file_permission=perms,
                target=self.fs,
                access="system",
            )
        else:
            fileutil.CreateFile(
                parsed.name,
                file_content=lines,
                file_owner=[owner],
                file_permission=perms,
                file_parent=parent,
                target=self.fs,
                access="system",
            )

    def read_file(self, path: str) -> str:
        return self.fs.ReadFile(self.resolve(path), str, "system")

    def remove_path(self, path: str, missing_ok: bool = True) -> None:
        resolved = self.resolve(path)
        if not self.exists(resolved):
            if missing_ok:
                return
            raise FileNotFoundError(resolved)
        if self.is_dir(resolved):
            self.fs.RemoveDirectory(resolved, access="system")
            return
        parsed = FileSystemPath(resolved)
        self.fs.RemoveFile(str(parsed.parent), parsed.name, access="system")

    def list_dir(self, path: str) -> list[str]:
        return [file.fileName for file in self.fs.ListDirectory(self.resolve(path), "system")]

    def snapshot(self, path: str) -> Any:
        resolved = self.resolve(path)
        if not self.exists(resolved):
            return None
        if self.is_dir(resolved):
            return {"kind": "directory"}
        entry = self._entry(resolved)
        permissions = None
        owner = "root"
        if entry is not None:
            permission_attr = entry.fileAttributes["Permission"]
            raw_permissions = permission_attr.attrlist
            permissions = (
                list(raw_permissions[0])
                if raw_permissions and isinstance(raw_permissions[0], (list, tuple))
                else list(raw_permissions)
            )
            owner_attr = entry.fileAttributes["Owner"].attrlist
            owner = str(owner_attr[0]) if owner_attr else "root"
        return {
            "kind": "file",
            "content": self.read_file(resolved),
            "permissions": permissions or [],
            "owner": owner,
        }

    def restore(self, path: str, snapshot: Any) -> None:
        resolved = self.resolve(path)
        if snapshot is None:
            self.remove_path(resolved, missing_ok=True)
            return
        if snapshot.get("kind") == "directory":
            self.ensure_directory(resolved)
            return
        self.write_file(
            resolved,
            snapshot.get("content", ""),
            owner=str(snapshot.get("owner", "root")),
            permissions=list(snapshot.get("permissions", [])),
        )

    # --------------------------------------------------------------- commands
    def register_command(self, name: str, handler: CommandHandler, override: bool = False) -> None:
        if name in framework_base.registry and not override:
            raise ValueError(f"command already registered: {name}")
        framework_base.registry[name] = handler
        self._owned_commands[name] = handler

    def unregister_command(self, name: str) -> None:
        owned = self._owned_commands.pop(name, None)
        if owned is None:
            return
        if framework_base.registry.get(name) is owned:
            del framework_base.registry[name]

    def command_exists(self, name: str) -> bool:
        return name in framework_base.registry

    def snapshot_commands(self) -> Any:
        return dict(framework_base.registry)

    def restore_commands(self, snapshot: Any) -> None:
        framework_base.registry.clear()
        framework_base.registry.update(snapshot)
        self._owned_commands = {
            name: handler
            for name, handler in snapshot.items()
            if name in self._owned_commands
        }


class MemoryBackend(PackageBackend):
    """In-memory backend; good for tests, dry runs and custom worlds."""

    def __init__(self) -> None:
        self.directories: set[str] = {"/"}
        self.files: dict[str, dict[str, Any]] = {}
        self.commands: dict[str, CommandHandler] = {}

    @staticmethod
    def _normal(path: str) -> str:
        return str(FileSystemPath(path))

    def exists(self, path: str) -> bool:
        resolved = self._normal(path)
        return resolved in self.directories or resolved in self.files

    def is_dir(self, path: str) -> bool:
        return self._normal(path) in self.directories

    def ensure_directory(self, path: str) -> None:
        resolved = self._normal(path)
        if resolved in self.files:
            raise ValueError(f"{resolved!r} exists and is not a directory")
        current = []
        for part in [part for part in resolved.split("/") if part]:
            current.append(part)
            self.directories.add("/" + "/".join(current))
        self.directories.add("/")

    def write_file(
        self,
        path: str,
        content: Any,
        owner: str = "root",
        permissions: list[PermEnum] | None = None,
    ) -> None:
        resolved = self._normal(path)
        parent = str(FileSystemPath(resolved).parent)
        self.ensure_directory(parent)
        self.files[resolved] = {
            "content": "\n".join(_content_lines(content)),
            "owner": owner,
            "permissions": list(permissions or [PermEnum.Readable, PermEnum.Listable]),
        }

    def read_file(self, path: str) -> str:
        resolved = self._normal(path)
        try:
            return self.files[resolved]["content"]
        except KeyError:
            raise FileNotFoundError(resolved) from None

    def remove_path(self, path: str, missing_ok: bool = True) -> None:
        resolved = self._normal(path)
        if resolved in self.files:
            del self.files[resolved]
            return
        if resolved in self.directories and resolved != "/":
            prefix = resolved.rstrip("/") + "/"
            for key in [key for key in self.files if key.startswith(prefix)]:
                del self.files[key]
            for key in [key for key in self.directories if key == resolved or key.startswith(prefix)]:
                self.directories.discard(key)
            return
        if not missing_ok:
            raise FileNotFoundError(resolved)

    def list_dir(self, path: str) -> list[str]:
        resolved = self._normal(path).rstrip("/")
        prefix = resolved + "/"
        names = set()
        for key in self.files:
            if key.startswith(prefix):
                names.add(key[len(prefix):].split("/")[0])
        for key in self.directories:
            if key != resolved and key.startswith(prefix):
                names.add(key[len(prefix):].split("/")[0])
        return sorted(names)

    def snapshot(self, path: str) -> Any:
        resolved = self._normal(path)
        if resolved in self.files:
            return {"kind": "file", **self.files[resolved]}
        if resolved in self.directories:
            return {"kind": "directory"}
        return None

    def restore(self, path: str, snapshot: Any) -> None:
        resolved = self._normal(path)
        if snapshot is None:
            self.remove_path(resolved, missing_ok=True)
            return
        if snapshot.get("kind") == "directory":
            self.ensure_directory(resolved)
            return
        self.files[resolved] = {
            "content": snapshot.get("content", ""),
            "owner": snapshot.get("owner", "root"),
            "permissions": list(snapshot.get("permissions", [])),
        }

    def register_command(self, name: str, handler: CommandHandler, override: bool = False) -> None:
        if name in self.commands and not override:
            raise ValueError(f"command already registered: {name}")
        self.commands[name] = handler

    def unregister_command(self, name: str) -> None:
        self.commands.pop(name, None)

    def command_exists(self, name: str) -> bool:
        return name in self.commands

    def snapshot_commands(self) -> Any:
        return dict(self.commands)

    def restore_commands(self, snapshot: Any) -> None:
        self.commands.clear()
        self.commands.update(snapshot)
