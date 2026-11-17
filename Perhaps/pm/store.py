"""
doas -su mylife.root
Package database storage.

The manager can persist its local database and synced repository metadata
anywhere.  The default is the virtual file system (``/var/lib/pm``); a memory
store and a host-file store are provided as examples, and the ABC is small
enough to wrap your own save format in a few lines.

does anyone care my python standard's nextstep?
"""

from __future__ import annotations

import copy
import json
import os
from abc import ABC, abstractmethod
from typing import Any

from .backends import PackageBackend
from .database import Repository
from .errors import StoreError


class PackageStore(ABC):
    """Persistence interface used by ``PackageManager``."""

    @abstractmethod
    def load_local(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def save_local(self, data: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def repository_names(self) -> list[str]:
        ...

    @abstractmethod
    def load_repository(self, name: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def save_repository(self, repository: Repository) -> None:
        ...


class MemoryStore(PackageStore):
    """In-memory store for dry runs, tools and tests."""

    def __init__(self) -> None:
        self.local: dict[str, Any] = {}
        self.repositories: dict[str, dict[str, Any]] = {}

    def load_local(self) -> dict[str, Any]:
        return copy.deepcopy(self.local)

    def save_local(self, data: dict[str, Any]) -> None:
        self.local = copy.deepcopy(data)

    def repository_names(self) -> list[str]:
        return sorted(self.repositories)

    def load_repository(self, name: str) -> dict[str, Any] | None:
        data = self.repositories.get(name)
        return copy.deepcopy(data) if data is not None else None

    def save_repository(self, repository: Repository) -> None:
        self.repositories[repository.name] = copy.deepcopy(
            repository.to_dict(include_files=True)
        )


class VirtualFSStore(PackageStore):
    """Store JSON inside the virtual file system (default ``/var/lib/pm``)."""

    def __init__(
        self,
        backend: PackageBackend | None = None,
        root: str = "/var/lib/pm",
    ) -> None:
        self.backend = backend
        self.root = root.rstrip("/") or "/"

    def _backend(self) -> PackageBackend:
        if self.backend is None:
            from .backends import VirtualFSBackend

            self.backend = VirtualFSBackend()
        return self.backend

    def _local_path(self) -> str:
        return f"{self.root}/local.json"

    def _sync_dir(self) -> str:
        return f"{self.root}/sync"

    def _repo_path(self, name: str) -> str:
        safe = "".join(char if char.isalnum() or char in "_.-" else "_" for char in name)
        return f"{self._sync_dir()}/{safe}.json"

    def _read_json(self, path: str) -> dict[str, Any] | None:
        backend = self._backend()
        if not backend.exists(path):
            return None
        try:
            text = backend.read_file(path)
            data = json.loads(text) if text.strip() else {}
        except Exception as exc:
            raise StoreError(f"could not read {path!r}: {exc}") from exc
        if not isinstance(data, dict):
            raise StoreError(f"{path!r} does not contain a JSON object")
        return data

    def _write_json(self, path: str, data: dict[str, Any]) -> None:
        backend = self._backend()
        parent = os.path.dirname(path).replace(os.sep, "/") or "/"
        backend.ensure_directory(parent)
        backend.write_file(
            path,
            json.dumps(data, ensure_ascii=False, indent=2),
            owner="root",
            permissions=[],
        )

    def load_local(self) -> dict[str, Any]:
        data = self._read_json(self._local_path())
        return data or {}

    def save_local(self, data: dict[str, Any]) -> None:
        self._write_json(self._local_path(), data)

    def repository_names(self) -> list[str]:
        backend = self._backend()
        if not backend.exists(self._sync_dir()):
            return []
        names = []
        for entry in backend.list_dir(self._sync_dir()):
            if entry.endswith(".json"):
                names.append(entry[:-5])
        return sorted(names)

    def load_repository(self, name: str) -> dict[str, Any] | None:
        return self._read_json(self._repo_path(name))

    def save_repository(self, repository: Repository) -> None:
        self._write_json(
            self._repo_path(repository.name),
            repository.to_dict(include_files=True),
        )


class HostJsonStore(PackageStore):
    """Store JSON under a host directory (useful for external tools)."""

    def __init__(self, root: str = "pm-data") -> None:
        self.root = root
        os.makedirs(self.local_dir, exist_ok=True)
        os.makedirs(self.sync_dir, exist_ok=True)

    @property
    def local_dir(self) -> str:
        return os.path.join(self.root, "local")

    @property
    def sync_dir(self) -> str:
        return os.path.join(self.root, "sync")

    def _read(self, path: str) -> dict[str, Any] | None:
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise StoreError(f"{path!r} does not contain a JSON object")
        return data

    def _write(self, path: str, data: dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    def load_local(self) -> dict[str, Any]:
        return self._read(os.path.join(self.local_dir, "local.json")) or {}

    def save_local(self, data: dict[str, Any]) -> None:
        self._write(os.path.join(self.local_dir, "local.json"), data)

    def repository_names(self) -> list[str]:
        return sorted(
            name[:-5]
            for name in os.listdir(self.sync_dir)
            if name.endswith(".json")
        )

    def load_repository(self, name: str) -> dict[str, Any] | None:
        return self._read(os.path.join(self.sync_dir, f"{name}.json"))

    def save_repository(self, repository: Repository) -> None:
        self._write(
            os.path.join(self.sync_dir, f"{repository.name}.json"),
            repository.to_dict(include_files=True),
        )
