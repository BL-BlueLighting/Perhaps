"""
doas -su mylife.root
Fast command utilities

Base command utilities for the game shell.
"""

from Perhaps.base import *


@register("clear")
def _clear(args: Arguments) -> None:
    clear()


@register("echo")
def _echo(args: Arguments) -> None:
    # Never let user input be interpreted as rich markup: ``echo '[/]'``
    # used to raise MarkupError and kill the shell.
    print(" ".join(str(arg) for arg in args), markup=False, emoji=False)
