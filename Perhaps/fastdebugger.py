"""
doas -su mylife.root
Fast Debugger
"""

from . import *
from rich import print_json
import sys

enableDebugger = False

@register("debugger")
def debugger(args: Arguments):
    print("Perhaps Common Debugger")
    if not save.gotattr("DebugSwitch"):
        print("> You haven't enable debugger. Please enable debugger in your game.")
        return

    print("> Pausing...")

    def GetSW(anyth: None):
        """Get storyWhere"""
        return swget()

    def SetSW(param: str):
        """Set storyWhere"""
        swset(param)
        return f"storyWhere set to {param} successfully."

    def ShowArchive(anyth: None):
        """Show archive's JSON with rich pretty view"""
        print_json(save.to_json(4))
        return ""

    def EditArchive(param: str):
        """Edit archive"""
        key, value = param.split(" ")
        save.__setattr__(key, value)
        return f"Archive's {key} has been set to {value}."

    def fallback(param: str):
        return "This debugger command is not defined."

    dbgcmd: dict[str, Callable[[Any], str]] = {
        "sw": GetSW,
        "ssw": SetSW,
        "sa": ShowArchive,
        "ea": EditArchive
    }

    while True:
        ipt = input("\n> ")
        if ipt == "e": return
        if ipt == "h":
            for scmd, cmd in dbgcmd.items():
                print("Help")
                print(f"{scmd}: {cmd.__doc__}")

        params = None
        head = ipt.split(" ") [0]
        if len(ipt.replace("head", "")) > 0:
            params = " ".join(ipt.split(" ") [1:])

        print("\n" + dbgcmd.get(head, fallback)(params))
        continue
