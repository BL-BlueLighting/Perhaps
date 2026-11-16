"""
doas -su mylife.root
Fast baseutils

Base tools of DROM stories.
"""

import datetime
from framework.base import *  #type: ignore
from framework.saving import * #type: ignore
from framework.fileutil import *
from framework.fileutil import PermEnum, CreateFile, CreateDirectory, WriteFile
from typing import Any
import getpass

#region Functions / Variables
save = Save()
slot: int = 0
enableFastutilRegisters = True
"""if not os.path.exists("flags/0"):
    open("flags/0", "w").write("{}")
save("flags/0", "r")"""

def isdigit(x: Any):
    try:
        int(x)
    except ValueError:
        return False
    else:
        return True

def askinput(__prompt: str, wants_type: type | None = None, failure_retry: str = "输入格式错误，请重试。", validator: Callable[[str], bool] | None = None) -> str:  #type: ignore
    """
    Asking input

    :param __prompt: Input prompt.
    :param wants_type: Type you want user gives.
    :param failure_retry: Fail retry string.
    :param validator: Validating function.
        It needs a string, this is user's input.
        Return a bool value, user's value vaild state.
    :return str: User's input, if user input is not you want type, it will auto retry.
    """
    while True:
        try:
            ipt = console.input(__prompt)
            if wants_type == int:
                if isdigit(ipt):
                    return ipt
                else:
                    print(failure_retry)
                    continue
            elif wants_type == bool:
                bool(ipt)
            elif not validator is None:
                if validator(ipt):
                    return ipt
                else:
                    print(failure_retry)
                    continue
        except ValueError:
            print(failure_retry)
            continue
        except KeyboardInterrupt:
            print(failure_retry)
            continue
        else:
            return ipt

def askyn(__prompt: str = "确定吗？[Y/n]", default: str = "y") -> bool:
    """
    Ask user yes or not.

    :param __prompt: Input prompt.
    :param default: Default value. If user didn't write anything or write non-yes or non-not characters auto fallback.
    :return bool: Does user agree.
    """
    try:
        res = console.input(__prompt)
    except KeyboardInterrupt:
        return False
    else:
        if res.lower() != "y" and res.lower() != "n":
            return default == "y"
        return res.lower() == "y"

def svslot(x: int):
    """Set save slot"""
    global slot
    slot = x

def svreload():
    """Load now slot"""
    save(f"flags/{slot}", "r")

def svsslot():
    """Saving slot"""
    clear()
    print("doas -su mylife.root")
    print("保存存档 - Save archive / save")
    print("")
    for file in os.listdir("./flags"):
        if isdigit(file):
            print(f"[{file}] 槽位 {file}")
    islot = int(askinput("[dim]输入您所需要选择的槽位 >[/dim] ", int, "请输入正确的槽位数。请重试。"))

    if os.path.exists(f"./flags/{islot}"):
        if askyn(":: 检测到该槽位已有存档，仍要覆盖吗？", "n"):
            svslot(islot)
            saveitp()
            return True
        else:
            print(":: 已取消操作。")
            return False
    else:
        svslot(islot)
        saveitp()
        return True

def svoslot():
    """Loading slot"""
    clear()
    print("doas -su mylife.root")
    print("加载存档 - Load archive / save")
    print("")
    for file in os.listdir("./flags"):
        if isdigit(file):
            print(f"[{file}] 槽位 {file}")
    islot = int(askinput("[dim]输入您所需要选择的槽位 >[/dim] ", int, "请输入正确的槽位数。请重试。"))
    print(":: [red]请注意，您加载存档后，目前内存中的存档将被覆盖。[/red]")
    print("   继续吗？[Y/n]", end="")
    
    if askyn("") != "n":
        print(":: 稍等，正在加载...")
        svslot(islot)
        svreload()
        print(":: 存档加载成功。")
        console.input("[dim]Enter 继续游戏 >[/dim] ")
        return True
    else:
        if askyn(":: 是否要保存内存存档到新的槽位中继续？[Y/n]"):
            if svsslot():
                print(":: 正在加载槽位...")
                svslot(islot)
                svreload()
                print(":: 存档加载成功。")
                console.input("[dim]Enter 继续游戏 >[/dim] ")
                return True
            else:
                print(":: 取消保存存档，正在退出...")
                return False
        else:
            print(":: 取消保存存档，正在退出...")
            return False

def svdslot():
    clear()
    print("doas -su mylife.root")
    print("选择默认存档 - Select default archive / save")
    print("")
    for file in os.listdir("./flags"):
        if isdigit(file):
            print(f"[{file}] 槽位 {file}")

    def validator(s: str) -> bool:
        return os.path.exists(f"./flags/{s}")
    
    islot = int(askinput("[dim]输入您所需要选择的槽位 >[/dim] ", int, "请输入正确且存在的槽位数。请重试。", validator))

    print(":: 稍等，正在切换存档...")
    mkflag("defaultslot", str(islot))
    if askyn(":: 是否要立即加载该存档槽位？", "n"):
        svslot(islot)
        svreload()
        print(":: 存档加载成功。")
        console.input("[dim]Enter 继续游戏 >[/dim] ")
        return True
    else:
        return False


def swget() -> str:
    """Get storyWhere value."""
    if not save.gotattr("storyWhere"):
        save.storyWhere = "1000"
        return "1000"
    else:
        return save.storyWhere #type: ignore

def swset(sw: str):
    """Set storyWhere value."""
    save.storyWhere = sw

def aprint(string: str, delay: float = 0.4):
    """manAI print, or slow print."""
    print(string)
    sleep(delay)

def askperm(permission_name: str, permission_command: str, perm_desc: str, rejectable: bool = True, who: str = "manAI") -> bool:
    """
    manAI / something permission asking.
    
    :param permission_name: What permission does {who} wants.
    :param permission_command: What command does {who} wants to run.
    :param perm_desc: Permission's description.
    :param rejectable: Does user can cancel.
    :param who: Who wants to do it.
    :return bool: Does user accept.
    """
    print(f":: [cyan][索要权限][/cyan] {who} 申请{permission_name}。")
    print(f"   [dim]它将要执行：[/dim]")
    print(f"       {permission_command}")
    print(f"   [dim]作用：{perm_desc}[/dim]")
    if not rejectable:
        print(f":: 无法取消，已经过 Unrejectable Command 审查。")
        return True
    print(f":: 是否同意？[Y/n] ", end="")
    yn = input().strip().lower()
    return yn != "n"

def saveit():
    """Save user save without prompting."""
    save(f"flags/{slot}","w")

def saveitp():
    """Save user save."""
    print(f"[cyan][!][/cyan] 存档已保存！")
    saveit()

def mkachieve(achieve_name: str, achieve_desc: str, achieve_id: str):
    """
    Make achieve.

    :param achieve_name: Achievement's name.
    :param achieve_desc: Description.
    :param achieve_id: Achievement's ID, storage name.
    """
    if flags(achieve_id): return
    print(f"[cyan][!][/cyan] 获得成就：{achieve_name}")
    print(f"    [dim]{achieve_desc}[/dim]")
    mkflag(achieve_id, f":: 成就：{achieve_name}\n    - {achieve_desc}")

def fs_writesave(ifs: FileSystem):
    save.fileSystem = ifs.__str__()

def fs_fromsave() -> FileSystem:
    ifs = FileSystem({}, [])
    ifs.LoadFromFile(save.fileSystem)
    return ifs

def fs_initialize(ifs: FileSystem):
    if save.gotattr("fileSystem"):
        fs_fromsave()
    else:
        fs_writesave(ifs)

def userinfo_get() -> list[str]:
    # get userinfo from flag.
    if not flags("userinfo"):
        raise FileNotFoundError("You can't read an uninitialized userinfo.")

    userinfo = rdflag("userinfo")
    return userinfo.split("\n")

def passwd_faillock(userinfo: list[str], ifs: FileSystem) -> bool:  #type: ignore
    fileContent: list[str] = ifs.ReadFile("/etc/faillocks/faillock", list[str], "system") #type: ignore
    for line in fileContent.split("\n"): #type: ignore
        columns = line.split("|")
        if userinfo[0] != columns [0]:
            continue

        itime = datetime.datetime.fromisoformat(columns[3])
        now = datetime.datetime.now()
        itime = itime + datetime.timedelta(seconds=60)
        if itime > now:
            filec = fileContent.split("\n")  #type: ignore
            filec.remove(line)
            WriteFile("/etc/faillocks", "faillock", file_content=filec)
            return False
        else:
            return True
    return False


def passwd_checker(userinfo: list[str], ifs: FileSystem, requirer: str = "sudo") -> bool: #type: ignore
    wrong_times = 0
    while True:
        try:
            pwd = getpass.getpass(f"{requirer}: f{userinfo[0]} 's password: ")
        except KeyboardInterrupt or EOFError:
            print(f"{requirer}: need password")
        else:
            if md5(pwd + userinfo[3]) == userinfo[2] and not passwd_faillock(userinfo, ifs):
                return True
            else:
                if wrong_times >= 4:
                    print(f"{requirer}: {wrong_times} times incorrect password try.")
                    print(f"{requirer}: please wait 60 seconds then try again.")
                    if not "faillock" in ifs.ListDirectory("/etc/faillocks"):
                        CreateFile("faillock", file_permission=[PermEnum.Access_Denied, PermEnum.Listable], file_content=[
                            f"{userinfo[0]}|{requirer}|faillock|{datetime.datetime.now()}|60"
                        ], file_owner="root")
                    else:
                        WriteFile("/etc/faillocks", "faillock", file_content=[
                            f"{userinfo[0]}|{requirer}|faillock|{datetime.datetime.now()}|60"
                        ], access="system")
                print(f"{requirer}: incorrect password. please try again.")
                wrong_times += 1
                continue

@register("setslot")
def setslot(args: Arguments):  #type: ignore
    svdslot()
    return

@register("openslot")
def openslot(args: Arguments): #type: ignore
    svoslot()
    return

@register("loadslot")
def loadslot(args: Arguments): #type: ignore
    if askyn(":: [yellow][ ! 警告 ][/yellow] 加载当前槽位存档后，内存中存档信息将会丢失。继续吗？[y/N]", "n"):
        print(":: 稍等，存档加载中...")
        svreload()
        print(":: 存档加载完毕。")
        return
    else:
        print(":: 用户拒绝，正在退出...")
        return

@register("resaveslot")
def resaveslot(args: Arguments): #type: ignore

    svsslot()
    return

@register("saveslot")
def saveslot(args: Arguments): #type: ignore

    if askyn(":: [yellow][ ! 警告 ][/yellow] 保存当前槽位存档后，文件中存档信息将会丢失。继续吗？[y/N]", "n"):
        saveitp()
        return
    else:
        print(":: 用户拒绝，正在退出...")
        return

if flags("defaultslot"):
    slot = int(rdflag("defaultslot"))
    svreload()

#endregion