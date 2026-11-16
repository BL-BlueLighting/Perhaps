"""
doas -su mylife.root
Framework Library File

Importing this package brings in the shell, save state, save-slot helpers and
the virtual file system, plus the tiny ``clear``/``echo`` built-ins from
``fastcmdutil``.  ``manAI`` is *not* imported automatically: it adds a
dialogue command and should be imported explicitly by the story that uses it.
"""

from .base import *
from .saving import *
from .fastutil import *
from .membertable import *

# Register the small built-in commands (clear / echo).  They do not collide
# with the file-system commands, so importing them here is safe.
from . import fastcmdutil  # noqa: F401  (imported for its registration side effect)
