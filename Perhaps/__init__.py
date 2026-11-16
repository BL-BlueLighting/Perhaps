"""
doas -su mylife.root
Framework Library File

Import this will import all scripts under.
"""

"""
Because fast command utils and file utils will have
feature repeats or conflicts, __init__.py will not
auto import them.
If you need, you can import it by yourself.
"""

from .base import *
from .fastutil import *
from .membertable import *
from .saving import *