"""
doas -su mylife.root
Base Framework - Perhaps

Usage:
>>> python base.py
- For example

```
import base

base.init()
base.main_while()
```

Import this file to initialize all framework of DROM.
Fork / develop based on this.

---

Base Framework is Injectable.
If you didn't need to edit Inject system, you can direct use Inject system, or direct create new hook in `base.py`.

~~(maybe you can use it in your script?)~~
"""

import rich
import rich.console as ricon
from time import sleep
from builtins import print as rprint
import os
import enlighten
from typing import Callable
import getpass
import hashlib
import random
import shlex

console = ricon.Console()
elgnmgr = enlighten.get_manager()
print = console.print
registry: dict[str, Callable[["Arguments"], "Arguments"]] = {}

COMMAND_NOT_FOUND = "CNF-1"

#region Injector
injects: dict[str, Callable] = {}

def inject(inject_point: str):
    """
    :param inject_point: 注入点名称
    """
    def decorator(func: Callable) -> Callable:
        injects[inject_point] = func
        return func

    return decorator


def run_injects(inject_point_name: str, *args, **kwargs):
    callback = injects.get(inject_point_name)
    if callback is None:
        return (Arguments(["0"]))
    ret = callback(*args, **kwargs)
    if type(ret) == tuple or type(ret) == list:
        # break actions now
        if ret[0] == -1:
            # execute
            retnd = ret[1](ret)
            return (retnd, ret)
        else:
            return (-1, ret)
    return (ret)

def run_patcher(inject_point_name: str, *args, **kwargs):
    callback = injects.get(inject_point_name)
    if callback == None:
        return ("stable_no_change")
    ret = callback(*args, **kwargs)
    return ret

#endregion

#region Command Creator
def register(command: str):
    """
    :param command: 命令的执行名称
    """
    def decorator(func: Callable) -> Callable:
        registry[command] = func
        return func
    
    return decorator


#endregion

#region Functions
def mkflag(flag_name: str, writeln: str = ""):
    if not os.path.exists("./flags"):
        os.mkdir("./flags")
    open(f"./flags/{flag_name}", "w").write(writeln)

def clear():
    """Clear console"""
    console.clear()

def flags(flag_name: str):
    """Detect flags"""
    if os.path.exists("./flags") and os.path.isdir("./flags"):
        if flag_name in os.listdir("./flags"):
            return True
        else:
            return False

def rdflag(flag_name: str) -> str:
    """Read flag content"""
    if not flags(flag_name):
        return ""
    else:
        return open(f"./flags/{flag_name}", "r").read()

def process(desc: str, total: int = 100, unit: str = "items"):
    """Create enlighten process"""
    pbar = elgnmgr.counter(total=total, desc=desc, unit=unit)
    return pbar

def md5(text: str):
    """Calc MD5"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def random_num() -> int:
    """Return 6 numbers (?)"""
    return random.randint(100000,999999)

def common_process_loop(
        pbar: enlighten.Counter, 
        tries: int = 100, 
        delay: float = 0.09, 
        while_do: Callable[[int], None] | None = None, 
        callback: Callable | None = None
    ):
    """
    Run Process Loop

    :param pbar: Process function created process object.
    :param tries: Total in process.
    :param delay: Process more delay time.
    :param while_do: Function do after delay.
    :param callback: Function do after process finished.
    """
    for i in range(tries):
        sleep(delay)
        if type(while_do) != None:
            while_do(i) #type: ignore
        pbar.update()

    if type(callback) != None:
        callback() #type: ignore

    elgnmgr.stop()

class Command:
    """
    Parse and execute Command
    """
    def __init__(self, command: str | list):
        """
        Initialize Command.

        :param command: Command string or splited list.
        """
        self.cmd: str = "".join(command)
        self.data = []

        self.head = ""
        self.args = []
        self.tunnel: Command | None = None # storages commands

    def parse(self):
        """
        Parse command.

        This function will use shlex to automatic split and recursive parse tunnels.
        """
        try:
            self.data = shlex.split(self.cmd)
        except:
            print("humansh: your command has syntax errors. please check then try again.")
            self.data = ["SYNTAX_ERROR_SYNTAX_ERROR"]
        
        self.head = self.data [0]
        tunnel: bool = False
        subcmd: list[str] = []

        del self.data[0]

        for arg in self.data:
            if arg == "|": # tunnel
                tunnel = True
                # why do not continue interpret tunnel?
                # because next command will interpret tunnel too, recursive interpret is greater than repeat write.
                continue
            else:
                self.args.append(arg)

            if tunnel:
                subcmd.append(arg)

            

        if subcmd != []:
            self.tunnel = Command(subcmd)

        

    def __call__(self, tunnel_ret: Arguments | None = None):
        return self.execute(tunnel_ret)

    def execute(self, tunnel_ret: Arguments | None = None):
        returns: list[Arguments] = []
        # find registry
        if not self.head in registry:
            print("humansh: command not found: " + self.head)

        for cmd, func in registry.items():
            if self.head == cmd:
                ret = func(Arguments(self.args, tunnel_ret))
                if ret == None:
                    ret = Arguments([0])
                if ret [0] == COMMAND_NOT_FOUND:
                    print("humansh: command not found: " + self.head)
                if self.tunnel != None:
                    self.tunnel(Arguments(ret.__getargs__(), ret))
                returns.append(ret)
        
        return returns
                    

class Arguments:
    """
    Arguments give to Commands and command Returns.
    """
    def __init__(self, args: list, tunnel_ret: "Arguments | None" = None):
        self.args = args
        self.tunnel_ret = tunnel_ret
    
    def __getitem__(self, key):
        if key == "TUNNEL":
            return self.tunnel_ret
        return self.args[key]

    def __setitem__(self, key, value):
        self.args[key] = value

    def __delitem__(self, key):
        del self.args[key]

    def __getargs__(self):
        return self.args

    def __len__(self):
        return len(self.args)

    def __iter__(self):
        return iter(self.args)
    
#endregion

#region Parts
def setup():
    """
    Example setup command.
    """
    ret = run_injects("before_setup")
    if type(ret) == tuple:
        # do not run example setup.

        return

    def setup_phase2(i: int):
        if i == 20:
            clear()
            print("\n[cyan]Second[/cyan], setup your hardwares.")
            print("Eyes Service: [gray]<disabled>[/gray]")
            print("Nervous Service: [gray]<disabled>[/gray]")
            print("No services need to setup.")
        elif i == 50:
            clear()
            print("\n[cyan]Third[/cyan], recovery from backups.")
            print("Backups     | Time | Recoverable | Select")
            print("<No backups>")
            print("")
            print("No backups found or recoverable.")
        elif i == 70:
            clear()
            print("\n[cyan]Fourth[/cyan], write configuration.")
            print("Please hold on.")
        elif i == 99:
            clear()
  

    def setup_phase3():
        clear()
        print("\n[cyan]Fifth[/cyan], set your personal informations.")
        print("Please input them.")
        username = input("Your username: ")
        password = getpass.getpass("Password (Hidden): ")
        hostname = input("Your hostname: ")
        salt = random_num().__str__()

        if not os.path.exists("./flags"):
            os.mkdir("./flags")
        open("./flags/setuped", "w").write("success")
        open("./flags/userinfo", "w").writelines([username+"\n", md5(password+salt)+"\n", hostname+"\n", salt+"\n"]) # what motherfuckin function

        sleep(2)
        print("\n🎉 All configuration completed!")
        print("- File writed.")
        print("- Discover more things in HumanOS.")
        print()

    clear()
    print("\n[green]Welcome to HumanOS![/green]")
    print("This is a setup for you to initialize this system.")
    print("Thank you for your choose.")
    print()
    print("[cyan]First[/cyan], let's setup your machine.")
    print("")
    print("Detected hard / memory drives")
    print("    - /dev/sda1 1024PB used 369PB (B)")
    print("    - /dev/sda2 2048PB used 0PB   (X)")
    print("[italic](B) Bootable Flag; (X) Selecting; ( ) Unselected[/italic]")
    print("")
    common_process_loop(process("Auto Config..."), while_do=setup_phase2, callback=setup_phase3)
#endregion

#region Pre-init texts

if not flags("skipload"):
    ret = run_injects("before_load")
    if type(ret) == tuple:
        # do not run init pre-comment
        pass
    else:
        initpre = open("./texts/initpre.txt", "r").readlines()

        for line in initpre:
            rich.print(f"[green]{line.strip()}[/green]", flush=True)
            sleep(0.04)

        sleep(1)
        rprint(".")
        sleep(1)
        rprint(".")
        sleep(2)

#endregion

#region Shell Pre
def init():
    """Welcome information"""
    clear()
    ret = run_injects("before_shell_pre")
    if type(ret) == tuple:
        # do not output normal shell precomment

        return

    print("[green]Welcome to HumanOS [/green]([cyan]v7.2.14-nature5-5-nature[/cyan]) !")
    print()
    print("[yellow][!][/yellow] [red]Warnings to you[/red]")
    print("    - This mode is for [bold]EMERGENCY[/bold] use. If you entered this mode as yourself, please quit ASAP.\n    - If you entered this mode without your any actions, please read recovery documents.")
    print()
    print("Type 'help' for all commands.")
    print()

    if not flags("skipsetup") and not flags("setuped"):
        setup()
#endregion

#region Main While
def main_while():
    """Run doas -su mylife.root Perhaps main loop"""
    username, password_hash, hostname, salt = open('./flags/userinfo', 'r').readlines()

    username = username.strip()
    password_hash = password_hash.strip()
    hostname = hostname.strip()
    salt = salt.strip()

    # faq

    directory = "~"
    prompt = "{username}@{hostname}:{directory}$ "

    while True:
        run_injects("while_head")
        run_injects("userinfo", username, password_hash, hostname, salt)
        run_injects("getdir", directory)

        dir_patch = run_patcher("directory_patcher", directory)
        prompt_patch = run_patcher("prompt_patcher", prompt, (username, password_hash, hostname, salt), directory)

        if prompt_patch != "stable_no_change":
            prompt = prompt_patch

        if dir_patch != "stable_no_change":
            directory = dir_patch

        try:
            ipt = console.input(prompt)
            if ipt.strip() == "":
                continue

            if ipt == "exit":
                raise KeyboardInterrupt
        except KeyboardInterrupt or EOFError:
            print("\nLogging out...")
            exit(0)
        else:
            ret = run_injects("after_enter", ipt)
            if ret[0] == -1:
                # interrupt command parse
                # control by ret auto use
                continue
            
            cmd = Command(ipt)
            cmd.parse()
            run_injects("before_execute", cmd)
            try:
                returns = cmd.execute()
            except IndexError:
                print(f"{cmd.head}: arguments not enough. May you can use `{cmd.head} help` for information")
                continue
            run_injects("after_execute", cmd, returns)
#endregion

if __name__ == "__main__":
    init()
    print(">>> [cyan]Notice:[/cyan] This is Framework file! Please execute Chapter files or Menu file.")
    main_while()