"""
doas -su mylife.root
Saving System

A tiny JSON-backed key/value store used by fastutil for save slots and by
the virtual file system for its serialized state.

The store deliberately does **not** protect against save tampering: a local
player can always edit their own save file.  What it *does* guarantee is:

- missing attributes raise ``AttributeError`` (so typos are not silently
  turned into ``None``);
- values are checked to be JSON serializable before anything is written;
- writes go to a temporary file in the same directory and are then moved
  into place with ``os.replace`` (no truncated half-saves);
- paths must be relative and must not contain ``..``.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

_ENCODING = "utf-8"


def _check_relative_path(file: str) -> str:
    """Reject absolute paths and ``..`` components."""
    if not isinstance(file, (str, os.PathLike)):
        raise TypeError("save path must be a string or os.PathLike")
    path = os.fspath(file)
    if path == "":
        raise ValueError("save path must not be empty")
    if os.path.isabs(path):
        raise ValueError(f"save path must be relative: {path!r}")
    if ".." in Path(path).parts:
        raise ValueError(f"save path must not contain '..': {path!r}")
    return path


class Save:
    """A dict-like JSON save state.

    ``save.foo = 1`` stores the value under key ``foo``;
    ``save.foo`` reads it back.  ``Save.load`` / ``Save.save`` do file I/O.
    """

    def __init__(self) -> None:
        object.__setattr__(self, "statuses", {})

    # ------------------------------------------------------------------ dict
    def __setitem__(self, key: str, value: Any) -> None:
        self.statuses[key] = value

    def __getitem__(self, key: str) -> Any:
        try:
            return self.statuses[key]
        except KeyError:
            raise KeyError(key) from None

    def __delitem__(self, key: str) -> None:
        try:
            del self.statuses[key]
        except KeyError:
            raise KeyError(key) from None

    def __contains__(self, key: object) -> bool:
        return key in self.statuses

    def __iter__(self):
        return iter(self.statuses)

    def __len__(self) -> int:
        return len(self.statuses)

    # ------------------------------------------------------------- attribute
    def __getattr__(self, name: str) -> Any:
        # Only called when normal attribute lookup fails.  Never return None
        # here: that would make hasattr() useless and hide typos.
        try:
            statuses = object.__getattribute__(self, "statuses")
        except AttributeError:
            raise AttributeError(name) from None
        try:
            return statuses[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name: str, value: Any) -> None:
        object.__getattribute__(self, "statuses")[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del object.__getattribute__(self, "statuses")[name]
        except KeyError:
            raise AttributeError(name) from None

    def gotattr(self, name: str) -> bool:
        """Does the save state contain ``name``?"""
        return name in self.statuses

    def get(self, name: str, default: Any = None) -> Any:
        return self.statuses.get(name, default)

    # ------------------------------------------------------------------ json
    def to_json(self) -> str:
        """Serialize the state to a JSON string."""
        try:
            return json.dumps(self.statuses, ensure_ascii=False)
        except TypeError as exc:
            raise TypeError(f"save state is not JSON serializable: {exc}") from exc

    def load_json(self, dump: str) -> None:
        """Replace the state with JSON text."""
        try:
            data = json.loads(dump)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid save JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("save JSON must contain an object at the top level")
        object.__setattr__(self, "statuses", data)

    # ------------------------------------------------------------------- I/O
    def load(self, file: str | os.PathLike[str]) -> None:
        """Load state from *file*; missing file raises ``FileNotFoundError``."""
        path = _check_relative_path(file)
        with open(path, "r", encoding=_ENCODING) as fh:
            self.load_json(fh.read())

    def save(self, file: str | os.PathLike[str]) -> None:
        """Atomically write the state to *file*."""
        path = _check_relative_path(file)
        dump = self.to_json()
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".save-", dir=parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding=_ENCODING) as fh:
                fh.write(dump)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    # ------------------------------------------------------------- interface
    def __call__(self, file: str = "", act: str = "") -> str:
        """Compatibility interface.

        ``save(file, "r")`` loads *file*, ``save(file, "w")`` stores *file*,
        and ``save()`` returns the current state as JSON.
        """
        if file == "":
            if act not in ("", "r", "w"):
                raise ValueError(f"unknown save action: {act!r}")
            return self.to_json()
        if act == "r":
            self.load(file)
        elif act == "w":
            self.save(file)
        else:
            raise ValueError(f"unknown save action: {act!r}")
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()

    def __str__(self) -> str:
        return self.to_json()


#: Process-wide save state (fastutil and fileutil share this object).
save = Save()
