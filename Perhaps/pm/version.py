"""
doas -su mylife.root
Package version helpers.

Pacman-ish version format: ``[epoch:]version[-release]``.

This is intentionally a *foundation*: the comparison below is close to
Arch's ``vercmp`` for ordinary numeric/alpha versions, but you can replace it
with your own callable through ``PackageManager(version_comparator=...)`` if
your story needs a different ordering.

You know, i love pacman.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import VersionError

_TOKEN_RE = re.compile(r"[0-9]+|[A-Za-z]+")


@dataclass(frozen=True)
class ParsedVersion:
    raw: str
    epoch: int
    version: str
    release: str

    @property
    def base(self) -> str:
        return f"{self.version}-{self.release}" if self.release else self.version


def parse_version(text: str) -> ParsedVersion:
    if not isinstance(text, str) or text.strip() == "":
        raise VersionError(f"invalid version: {text!r}")
    value = text.strip()
    epoch = 0
    if ":" in value:
        head, value = value.split(":", 1)
        if not head.isdigit():
            raise VersionError(f"invalid epoch in version: {text!r}")
        epoch = int(head)
    if "-" in value:
        version, release = value.rsplit("-", 1)
    else:
        version, release = value, ""
    if not version:
        raise VersionError(f"invalid version: {text!r}")
    return ParsedVersion(text.strip(), epoch, version, release)


def _cmp_tokens(left: str, right: str) -> int:
    """Compare two version chunks using numeric-aware segments."""
    left_tokens = _TOKEN_RE.findall(left)
    right_tokens = _TOKEN_RE.findall(right)
    for a, b in zip(left_tokens, right_tokens):
        a_num = a.isdigit()
        b_num = b.isdigit()
        if a_num and b_num:
            a_int, b_int = int(a), int(b)
            if a_int > b_int:
                return 1
            if a_int < b_int:
                return -1
            continue
        if a_num != b_num:
            # Numeric segments sort above alphabetic ones (rpmvercmp habit).
            return 1 if a_num else -1
        if a > b:
            return 1
        if a < b:
            return -1
    if len(left_tokens) > len(right_tokens):
        return 1
    if len(left_tokens) < len(right_tokens):
        return -1
    return 0


def compare_versions(left: str, right: str) -> int:
    """Return -1, 0 or 1 for ``left`` compared to ``right``."""
    a = parse_version(left)
    b = parse_version(right)
    if a.epoch != b.epoch:
        return 1 if a.epoch > b.epoch else -1
    result = _cmp_tokens(a.version, b.version)
    if result:
        return result
    return _cmp_tokens(a.release, b.release)


def versions_equal(left: str, right: str) -> bool:
    return compare_versions(left, right) == 0


def check_constraint(
    version: str,
    operator: str = "",
    required: str = "",
) -> bool:
    """Does ``version`` satisfy ``operator required``?"""
    if not operator:
        return True
    if operator not in ("=", "==", ">=", "<=", ">", "<", "!="):
        raise VersionError(f"unknown version operator: {operator!r}")
    if required == "":
        return True
    comparison = compare_versions(version, required)
    return {
        "=": comparison == 0,
        "==": comparison == 0,
        ">=": comparison >= 0,
        "<=": comparison <= 0,
        ">": comparison > 0,
        "<": comparison < 0,
        "!=": comparison != 0,
    }[operator]


def format_version(version: str) -> str:
    """Stable display helper; never raises for user-facing output."""
    try:
        parsed = parse_version(version)
    except VersionError:
        return str(version)
    if parsed.epoch:
        return f"{parsed.epoch}:{parsed.base}"
    return parsed.base
