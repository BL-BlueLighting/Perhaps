"""
doas -su mylife.root
Perhaps Package Manager (pm) — foundation.

An open, pacman-flavored package manager base for the HumanOS/DROM world:

- ``Package`` / ``PackageFile`` / ``Dependency`` models;
- local installed DB + sync repositories (JSON-friendly);
- pluggable sources, file/command backends and stores;
- dependency/conflict resolver with transaction planning;
- transactional installs/removals with rollback and hooks;
- pacman-ish CLI (``-Q`` / ``-S`` / ``-R`` / ``-U`` / ``-T`` / ``-D`` / ``-F``);
- MPM compatibility facade for the story's original dict-based manager.

Nothing is auto-registered on import.  A game wires it up explicitly::

    from Perhaps.pm import default_manager
    pm = default_manager()
    pm.register_commands("mpm")

For a dry/in-memory setup::

    from Perhaps.pm import PackageManager
    pm = PackageManager(backend=MemoryBackend(), store=MemoryStore())

btw i am really want to add my big burger in it 😋
"""

from __future__ import annotations

from typing import Any

from .errors import *  # noqa: F401,F403
from .version import (
    ParsedVersion,
    check_constraint,
    compare_versions,
    format_version,
    parse_version,
    versions_equal,
)
from .package import (
    CommandHandler,
    DEFAULT_DIR_PERMISSIONS,
    DEFAULT_FILE_PERMISSIONS,
    Dependency,
    Package,
    PackageFile,
    normalize_package_path,
)
from .database import PackageDatabase, PackageRecord, Repository, RepositorySet
from .backends import MemoryBackend, PackageBackend, VirtualFSBackend
from .sources import (
    CallbackSource,
    CompositeSource,
    DictSource,
    HostJsonSource,
    JsonTextSource,
    PackageSource,
    VirtualFSJsonSource,
    repository_from_data,
)
from .store import HostJsonStore, MemoryStore, PackageStore, VirtualFSStore
from .resolver import ResolvePlan, Resolver
from .hooks import (
    CallbackHook,
    Hook,
    HookContext,
    HookManager,
    POST_INSTALL,
    POST_REMOVE,
    POST_TRANSACTION,
    PRE_INSTALL,
    PRE_REMOVE,
    PRE_TRANSACTION,
    ROLLBACK,
)
from .transaction import Transaction, TransactionResult
from .manager import PackageManager
from .compat import MPMManager
from .cli import (
    CLIController,
    CliParseError,
    CliRequest,
    PM_VERSION,
    parse_args,
    register_pm_command,
)

VERSION = PM_VERSION

__all__ = [
    "PM_VERSION",
    "VERSION",
    # errors
    "PackageError",
    "PackageNotFound",
    "PackageAlreadyInstalled",
    "DependencyError",
    "ConflictError",
    "FileConflict",
    "VersionError",
    "RepositoryError",
    "SourceError",
    "StoreError",
    "BackendError",
    "TransactionError",
    "RollbackError",
    "HookError",
    "UnregisteredCommand",
    # version
    "ParsedVersion",
    "parse_version",
    "compare_versions",
    "versions_equal",
    "check_constraint",
    "format_version",
    # model
    "Package",
    "PackageFile",
    "Dependency",
    "CommandHandler",
    "normalize_package_path",
    "DEFAULT_FILE_PERMISSIONS",
    "DEFAULT_DIR_PERMISSIONS",
    # database
    "PackageDatabase",
    "PackageRecord",
    "Repository",
    "RepositorySet",
    # backends
    "PackageBackend",
    "VirtualFSBackend",
    "MemoryBackend",
    # sources
    "PackageSource",
    "DictSource",
    "JsonTextSource",
    "HostJsonSource",
    "VirtualFSJsonSource",
    "CallbackSource",
    "CompositeSource",
    "repository_from_data",
    # store
    "PackageStore",
    "MemoryStore",
    "VirtualFSStore",
    "HostJsonStore",
    # resolver/transaction
    "Resolver",
    "ResolvePlan",
    "HookManager",
    "Hook",
    "CallbackHook",
    "HookContext",
    "PRE_TRANSACTION",
    "POST_TRANSACTION",
    "PRE_INSTALL",
    "POST_INSTALL",
    "PRE_REMOVE",
    "POST_REMOVE",
    "ROLLBACK",
    "Transaction",
    "TransactionResult",
    # facade/CLI
    "PackageManager",
    "MPMManager",
    "CLIController",
    "CliRequest",
    "CliParseError",
    "parse_args",
    "register_pm_command",
    "default_manager",
    "create_manager",
]


def default_manager(
    *,
    load: bool = True,
    strict: bool = False,
    backend: PackageBackend | None = None,
    store: PackageStore | None = None,
    hooks: HookManager | None = None,
    root: str = "/var/lib/pm",
    allow_unowned_overwrite: bool = False,
) -> PackageManager:
    """Create the usual virtual-FS manager, optionally loading persisted state.

    :param load: read ``/var/lib/pm`` when true.
    :param strict: let store errors escape instead of starting empty.
    """
    if backend is None:
        backend = VirtualFSBackend()
    if store is None:
        store = VirtualFSStore(backend, root=root)
    manager = PackageManager(
        backend=backend,
        store=store,
        hooks=hooks,
        allow_unowned_overwrite=allow_unowned_overwrite,
    )
    if load:
        try:
            manager.load()
        except Exception:
            if strict:
                raise
    return manager


def create_manager(**kwargs: Any) -> PackageManager:
    """Alias for :func:`default_manager`."""
    return default_manager(**kwargs)
