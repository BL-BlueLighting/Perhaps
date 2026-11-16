"""
doas -su mylife.root
manAI utils
"""

from __future__ import annotations

from typing import Callable

from .base import *
from .fastutil import *

#: storyWhere value -> list of callables for the manAI dialog.
manAI_talks: dict[str, list[Callable[[], Any]]] = {}


@register("manAI")
def manAI(args: Arguments) -> None:
    story_where = swget()
    callables = manAI_talks.get(story_where, [])
    if not callables:
        print("(._.) To be continued...")
        return
    for call in callables:
        result = call()
        if result is None:
            continue
        if isinstance(result, str):
            # Text-only response: do not touch storyWhere.
            print(f"[dim]! {escape(result)} ![/dim]")
            continue
        if (
            isinstance(result, (tuple, list))
            and len(result) == 2
            and all(isinstance(item, str) for item in result)
        ):
            swset(result[0])
            print(f"[dim]! {escape(result[1])} ![/dim]")
            continue
        raise TypeError(
            "manAI talk callables must return None, a string, or "
            f"(next_story_where, text); got {result!r}"
        )


def aiReg(storyWhere: str):
    """Register a manAI dialog function for a storyWhere value."""

    def decorator(func: Callable[[], Any]) -> Callable[[], Any]:
        manAI_talks.setdefault(storyWhere, []).append(func)
        return func

    return decorator
