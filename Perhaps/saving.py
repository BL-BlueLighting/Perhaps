"""
doas -su mylife.root
Saving System
"""

import json, os
from typing import Any

# 友情提醒，本套存档系统不对存档进行防修改篡改保护，不存在绝对可以保护存档的算法。
# 同时，本套存档系统实现较为简单，推荐自己实现。

class Save:
    def __init__(self):
        object.__setattr__(self, "statuses", {})

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return json.dumps(self.statuses)

    def __setitem__(self, key, value):
        self.statuses[key] = value

    def __getitem__(self, key):
        return self.statuses[key]

    def __delitem__(self, key):
        del self.statuses[key]
        return

    def __getattr__(self, name):
        try:
            statuses = object.__getattribute__(self, "statuses")
        except AttributeError:
            # statuses not yet set (unpickling, early init, copy, …)
            raise AttributeError(name) from None
        try:
            return statuses[name]
        except KeyError:
            return None

    def __call__(self, file: str = "", act: str = ""):
        if file != "" and act == "r":
            if os.path.exists(file):
                self.statuses = json.load(open(file, "r"))
            else:
                self.statuses = json.loads(file)

        if file != "" and act == "w":
            open(file, "w").write(self.__str__())

        return self.__str__()

    def __setattr__(self, name, value):
        super().__getattribute__("statuses")[name] = value

    def __setattribute__(self, name: str, value: str) -> Any:
        super().__getattribute__("statuses")[name] = value

    def gotattr(self, attr: str) -> bool:
        return attr in self.statuses
    
    # 我在写什么
    # 为什么一大堆魔术