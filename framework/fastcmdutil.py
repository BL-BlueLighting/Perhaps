"""
doas -su mylife.root
Fast command utilities

Base command utilities for game.
"""

from framework.base import *
from framework.saving import *
from typing import Any

@register("clear")
def _clear(args: Arguments):
    clear()
    # hyw

@register("echo")
def _echo(args: Arguments):
    print(" ".join(args))
    return

# i am very angry my computer is very stuck when i am writing code
# fuck u logitech

