"""
doas -su mylife.root
Transaction hooks.

Hooks are the free/open seam of the package manager: register a Python
callable for ``pre_install``, ``post_remove`` or a package-specific event, and
it runs inside the transaction.  Raising from a hook aborts the transaction
and triggers rollback.

oh my gosh! your hook hits me 😭
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .database import PackageDatabase, PackageRecord
from .package import Package

PRE_TRANSACTION = "pre_transaction"
POST_TRANSACTION = "post_transaction"
PRE_INSTALL = "pre_install"
POST_INSTALL = "post_install"
PRE_REMOVE = "pre_remove"
POST_REMOVE = "post_remove"
ROLLBACK = "rollback"


@dataclass
class HookContext:
    """Everything a hook may need, copied per event."""

    event: str
    package: Package | None = None
    record: PackageRecord | None = None
    database: PackageDatabase | None = None
    manager: Any = None
    plan: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


class Hook:
    """Base hook class; override :meth:`on_event`."""

    name: str = "hook"
    priority: int = 0
    events: tuple[str, ...] | None = None  # None = every event

    def on_event(self, context: HookContext) -> None:
        """Called for matching events.  Raise to abort the transaction."""

    def wants(self, event: str) -> bool:
        return self.events is None or event in self.events


class CallbackHook(Hook):
    """A hook built from a plain callable ``context -> None``."""

    def __init__(
        self,
        name: str,
        callback: Callable[[HookContext], None],
        events: tuple[str, ...] | None = None,
        priority: int = 0,
    ) -> None:
        self.name = name
        self.callback = callback
        self.events = events
        self.priority = priority

    def on_event(self, context: HookContext) -> None:
        self.callback(context)


class HookManager:
    def __init__(self, hooks: list[Hook] | None = None) -> None:
        self.hooks: list[Hook] = list(hooks or [])

    def add(self, hook: Hook) -> None:
        self.hooks.append(hook)
        self.hooks.sort(key=lambda item: item.priority, reverse=True)

    def register(self, hook: Hook) -> Hook:
        self.add(hook)
        return hook

    def remove(self, name: str) -> None:
        self.hooks = [hook for hook in self.hooks if hook.name != name]

    def emit(self, event: str, context: HookContext | None = None, **extra: Any) -> None:
        ctx = context or HookContext(event=event)
        ctx.event = event
        ctx.extra.update(extra)
        for hook in tuple(self.hooks):
            if hook.wants(event):
                hook.on_event(ctx)
