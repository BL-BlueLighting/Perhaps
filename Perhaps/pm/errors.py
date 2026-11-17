"""
doas -su mylife.root
Package Manager errors.

A small exception tree so callers can catch exactly as much as they want:
``PackageError`` for everything PM-related, or the concrete class below.

do you like exceptions in it? 😋
"""

from __future__ import annotations


class PackageError(Exception):
    """Base class for every package-manager error."""


class PackageNotFound(PackageError):
    """Requested package does not exist in the local/available set."""


class PackageAlreadyInstalled(PackageError):
    """Same package id is already present in the local database."""


class DependencyError(PackageError):
    """A dependency is missing, unsatisfied, or forms a cycle."""


class ConflictError(PackageError):
    """Packages/versions conflict with each other."""


class FileConflict(PackageError):
    """Two packages want to own the same virtual path."""


class VersionError(PackageError):
    """A version string or version constraint could not be understood."""


class RepositoryError(PackageError):
    """Repository refresh/loading failed."""


class SourceError(PackageError):
    """A package source could not load its repository."""


class StoreError(PackageError):
    """The local/sync database store could not be read or written."""


class BackendError(PackageError):
    """The file/command backend refused an operation."""


class TransactionError(PackageError):
    """A transaction could not be prepared or completed."""


class RollbackError(TransactionError):
    """A failed transaction could not be fully rolled back."""


class HookError(TransactionError):
    """A transaction hook rejected the transaction."""


class UnregisteredCommand(Warning):
    """Compatibility warning from the story MPM: declared command is absent.

    Real MPM registries contain story-only command names that are never
    implemented; this warning is informational and must not abort a query.
    """
