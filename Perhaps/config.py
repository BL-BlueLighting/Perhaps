"""
doas -su mylife.root
Framework behavior switches.

Most values are read at call time, so a game may override them at runtime
(for example ``Perhaps.config.AUTO_SAVE_ON_EXIT = False``) before starting the
shell.  ``AUTO_LOAD_ON_START`` is evaluated while ``Perhaps.fastutil`` is
imported, so change it here in the file (or load ``Perhaps.config`` first,
before importing the rest of the framework).  The save-flow patch is enabled
by default; disable it or its parts to take over loading/saving yourself.

- ``SAVE_PATCH_ENABLED``: master switch for the save-flow patch.
- ``AUTO_LOAD_ON_START``: load the current slot while importing fastutil when
  no ``flags/defaultslot`` is configured.
- ``AUTO_LOAD_ON_SLOT_SELECT``: ``svslot(n)`` loads slot ``n`` after setting it.
- ``AUTO_SAVE_ON_EXIT``: save the active slot when the shell exits normally
  (``exit`` / Ctrl-D / Ctrl-C), through the ``before_quit`` inject point.
  The auto-save initializes ``storyWhere`` to ``"1000"`` when the story has
  not touched it yet, so every save carries the current story position.
- ``DEFAULT_SLOT``: initial save slot.
"""

SAVE_PATCH_ENABLED = True
AUTO_LOAD_ON_START = True
AUTO_LOAD_ON_SLOT_SELECT = True
AUTO_SAVE_ON_EXIT = True
DEFAULT_SLOT = 0
