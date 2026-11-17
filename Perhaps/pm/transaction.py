"""
doas -su mylife.root
Package transaction execution.

``Transaction`` takes a ``ResolvePlan``, writes/removes payload files through
a backend, updates the local database and runs hooks.  If anything raises, the
whole thing is rolled back: files are restored from snapshots, commands are
restored and the local database is reloaded from a snapshot.

This is intentionally not a full journaling filesystem.  It tries hard to be
safe for one-process game use while staying hackable: replace the backend,
register hooks, or subclass ``Transaction``.

oh god, it's not right and not great.
"""

from __future__ import annotations

import datetime
import pathlib
from dataclasses import dataclass, field
from typing import Any

from .backends import PackageBackend
from .database import PackageDatabase, PackageRecord
from .errors import FileConflict, HookError, RollbackError, TransactionError
from .hooks import (
    POST_INSTALL,
    POST_REMOVE,
    POST_TRANSACTION,
    PRE_INSTALL,
    PRE_REMOVE,
    PRE_TRANSACTION,
    ROLLBACK,
    HookContext,
    HookManager,
)
from .package import Package, PackageFile
from .resolver import ResolvePlan

SYMLINK_MARKER = "<PM_SYMLINK>"


@dataclass
class TransactionResult:
    success: bool
    installed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    rolled_back: bool = False
    details: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.success


class Transaction:
    def __init__(
        self,
        backend: PackageBackend,
        database: PackageDatabase,
        hooks: HookManager | None = None,
        manager: Any = None,
    ) -> None:
        self.backend = backend
        self.database = database
        self.hooks = hooks or HookManager()
        self.manager = manager

    # --------------------------------------------------------------- helpers
    def _affected_paths(self, plan: ResolvePlan) -> list[str]:
        paths = []
        for package in plan.installs:
            paths.extend(file.path for file in package.files)
        for record in plan.removals:
            paths.extend(record.files)
        return list(dict.fromkeys(paths))

    def _emit_package_hooks(self, event: str, package: Package | None, record: PackageRecord | None) -> None:
        context = HookContext(
            event=event,
            package=package,
            record=record,
            database=self.database,
            manager=self.manager,
        )
        self.hooks.emit(event, context)
        if package is not None:
            for custom in package.hooks:
                self.hooks.emit(custom, context)

    def _install_file(self, package: Package, file: PackageFile) -> None:
        if file.kind == "directory":
            self.backend.ensure_directory(file.path)
            return
        owner = self.database.owner_of(file.path)
        if owner is not None and owner != package.id:
            raise FileConflict(
                f"{package.id}: path {file.path} is already owned by {owner}"
            )
        if (
            owner is None
            and self.backend.exists(file.path)
            and not getattr(self.manager, "allow_unowned_overwrite", False)
        ):
            raise FileConflict(
                f"{package.id}: path {file.path} already exists in the file system"
            )
        self.backend.ensure_directory(
            str(pathlib.PurePosixPath(file.path).parent)
        )
        if file.kind == "symlink":
            content = [f"{SYMLINK_MARKER} {file.target}"]
        else:
            content = file.content
        self.backend.write_file(
            file.path,
            content,
            owner=file.owner,
            permissions=file.permissions,
        )

    def _remove_package_files(self, record: PackageRecord) -> None:
        for path in sorted(record.files, key=len, reverse=True):
            self.backend.remove_path(path, missing_ok=True)
        for command in record.package.commands:
            self.backend.unregister_command(command)

    def _install_commands(self, package: Package) -> None:
        for name, handler in package.handlers.items():
            self.backend.register_command(name, handler, override=True)

    # -------------------------------------------------------------- execution
    def execute(
        self,
        plan: ResolvePlan,
        *,
        reasons: dict[str, str] | None = None,
        save: bool = False,
    ) -> TransactionResult:
        result = TransactionResult(success=False)
        if plan.problems:
            result.problems.extend(plan.problems)
            return result

        reasons = reasons or {}
        db_snapshot = self.database.to_dict()
        command_snapshot = self.backend.snapshot_commands()
        path_snapshots = {
            path: self.backend.snapshot(path) for path in self._affected_paths(plan)
        }
        installed: list[str] = []
        removed: list[str] = []

        try:
            self.hooks.emit(
                PRE_TRANSACTION,
                HookContext(event=PRE_TRANSACTION, manager=self.manager, plan=plan),
            )

            for record in plan.removals:
                self._emit_package_hooks(PRE_REMOVE, record.package, record)
                self._remove_package_files(record)
                self.database.remove(record.id, missing_ok=True)
                removed.append(record.id)
                self._emit_package_hooks(POST_REMOVE, record.package, record)

            for package in plan.installs:
                self._emit_package_hooks(PRE_INSTALL, package, None)
                for file in package.files:
                    self._install_file(package, file)
                self._install_commands(package)
                reason = reasons.get(package.id, "dependency")
                self.database.add(package, reason=reason, replace=True)  # type: ignore[arg-type]
                installed.append(package.id)
                self._emit_package_hooks(POST_INSTALL, package, None)

            self.hooks.emit(
                POST_TRANSACTION,
                HookContext(event=POST_TRANSACTION, manager=self.manager, plan=plan),
            )
            result.success = True
            result.installed = installed
            result.removed = removed
            result.details.append(
                f"transaction finished at {datetime.datetime.now().isoformat(timespec='seconds')}"
            )
            if save and self.manager is not None:
                self.manager.save()
            return result

        except Exception as exc:
            problems = [f"{type(exc).__name__}: {exc}"]
            rollback_error = self._rollback(db_snapshot, command_snapshot, path_snapshots)
            result.success = False
            result.rolled_back = True
            result.problems.extend(problems)
            if rollback_error:
                result.problems.extend(rollback_error)
            result.installed = []
            result.removed = []
            try:
                self.hooks.emit(
                    ROLLBACK,
                    HookContext(event=ROLLBACK, manager=self.manager, plan=plan),
                    error=exc,
                )
            except Exception:
                pass
            return result

    def _rollback(
        self,
        db_snapshot: dict[str, Any],
        command_snapshot: Any,
        path_snapshots: dict[str, Any],
    ) -> list[str]:
        problems: list[str] = []
        for path, snapshot in path_snapshots.items():
            try:
                self.backend.restore(path, snapshot)
            except Exception as exc:
                problems.append(f"rollback failed for {path}: {exc}")
        try:
            self.backend.restore_commands(command_snapshot)
        except Exception as exc:
            problems.append(f"rollback failed for commands: {exc}")
        try:
            self.database.load_dict(db_snapshot)
        except Exception as exc:
            problems.append(f"rollback failed for local database: {exc}")
            raise RollbackError("; ".join(problems)) from exc
        return problems
