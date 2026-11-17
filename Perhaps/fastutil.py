"""
doas -su mylife.root
Fast baseutils

Save slots, password verification, achievement helpers and convenience
wrappers around the virtual file system.
"""

from __future__ import annotations

import datetime
import getpass
import os
from typing import Any

from Perhaps import config
from Perhaps.base import *
from Perhaps.base import ask_password_once as _base_ask_password_once
from Perhaps.fileutil import *
from Perhaps.fileutil import PermEnum, CreateFile, CreateDirectory, WriteFile
from Perhaps.saving import *

slot: int = config.DEFAULT_SLOT


# region Functions / Variables
def isdigit(x: Any) -> bool:
    try:
        int(x)
    except (TypeError, ValueError):
        return False
    return True


def askinput(
    __prompt: str,
    wants_type: type | None = None,
    failure_retry: str = "输入格式错误，请重试。",
    validator: Callable[[str], bool] | None = None,
) -> str:
    """Ask for input and retry until it matches the requested type/validator."""
    while True:
        try:
            ipt = console.input(__prompt)
        except (KeyboardInterrupt, EOFError):
            print()
            raise
        if wants_type is int:
            try:
                int(ipt)
            except ValueError:
                print(failure_retry)
                continue
        elif wants_type is bool:
            low = ipt.strip().lower()
            if low in ("y", "yes", "true", "1"):
                ipt = "True"
            elif low in ("n", "no", "false", "0"):
                ipt = "False"
            else:
                print(failure_retry)
                continue
        elif wants_type is not None and wants_type is not str:
            raise TypeError(f"unsupported wants_type: {wants_type!r}")
        if validator is not None and not validator(ipt):
            print(failure_retry)
            continue
        return ipt


def askyn(__prompt: str = "确定吗？[Y/n]", default: str = "y") -> bool:
    """Ask a yes/no question.  Empty input uses *default*."""
    try:
        res = console.input(__prompt).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return False
    if res == "":
        return default.strip().lower() == "y"
    if res in ("y", "yes"):
        return True
    if res in ("n", "no"):
        return False
    return default.strip().lower() == "y"


def svslot(x: int, load: bool | None = None) -> None:
    """Set the active save slot.

    :param load: ``None`` follows ``config.AUTO_LOAD_ON_SLOT_SELECT``; pass
        ``False`` for callers that are about to write the slot instead
        (``svsslot`` / ``svoslot`` / ``svdslot``).
    """
    global slot
    if not isinstance(x, int) or isinstance(x, bool) or x < 0:
        raise ValueError("save slot must be a non-negative integer")
    slot = x
    if load is None:
        load = config.SAVE_PATCH_ENABLED and config.AUTO_LOAD_ON_SLOT_SELECT
    if load:
        svreload()


def _slot_file(x: int | None = None) -> str:
    return os.path.join("flags", str(slot if x is None else x))


def svreload() -> None:
    """Load the active save slot.  A missing slot starts from an empty save."""
    try:
        save.load(_slot_file())
    except FileNotFoundError:
        object.__setattr__(save, "statuses", {})
    except (OSError, ValueError) as exc:
        print(f":: [yellow]存档无法读取，已从空存档开始：{escape(str(exc))}[/yellow]")
        object.__setattr__(save, "statuses", {})


def _list_slots() -> list[int]:
    try:
        entries = os.listdir("flags")
    except FileNotFoundError:
        return []
    slots = []
    for entry in entries:
        if entry.isdigit():
            try:
                slots.append(int(entry))
            except ValueError:
                continue
    return sorted(slots)


def _choose_slot(prompt_text: str, validator: Callable[[str], bool] | None = None) -> int:
    os.makedirs("flags", exist_ok=True)
    for entry in _list_slots():
        print(f"[{entry}] 槽位 {entry}")
    raw = askinput(prompt_text, int, "请输入正确的槽位数。请重试。", validator)
    return int(raw)


def svsslot() -> bool:
    """Save the current in-memory state to a slot."""
    clear()
    print("doas -su mylife.root")
    print("保存存档 - Save archive / save")
    print("")
    chosen = _choose_slot("[dim]输入您所需要选择的槽位 >[/dim] ")
    if os.path.exists(_slot_file(chosen)):
        if not askyn(":: 检测到该槽位已有存档，仍要覆盖吗？[Y/n]", "n"):
            print(":: 已取消操作。")
            return False
    svslot(chosen, load=False)
    saveitp()
    return True


def svoslot() -> bool:
    """Load a save slot."""
    clear()
    print("doas -su mylife.root")
    print("加载存档 - Load archive / save")
    print("")
    chosen = _choose_slot("[dim]输入您所需要选择的槽位 >[/dim] ")
    print(":: [red]请注意，您加载存档后，目前内存中的存档将被覆盖。[/red]")
    if askyn(":: 继续吗？[Y/n] ", "y"):
        print(":: 稍等，正在加载...")
        svslot(chosen, load=False)
        svreload()
        print(":: 存档加载成功。")
        console.input("[dim]Enter 继续游戏 >[/dim] ")
        return True
    if askyn(":: 是否要保存内存存档到新的槽位中继续？[Y/n]", "y"):
        if svsslot():
            print(":: 正在加载槽位...")
            svslot(chosen, load=False)
            svreload()
            print(":: 存档加载成功。")
            console.input("[dim]Enter 继续游戏 >[/dim] ")
            return True
    print(":: 取消保存存档，正在退出...")
    return False


def svdslot() -> bool:
    """Choose the default save slot."""
    clear()
    print("doas -su mylife.root")
    print("选择默认存档 - Select default archive / save")
    print("")

    def validator(s: str) -> bool:
        return s.isdigit() and os.path.exists(_slot_file(int(s)))

    chosen = _choose_slot(
        "[dim]输入您所需要选择的槽位 >[/dim] ",
        validator,
    )
    print(":: 稍等，正在切换存档...")
    mkflag("defaultslot", str(chosen))
    if askyn(":: 是否要立即加载该存档槽位？[Y/n]", "n"):
        svslot(chosen, load=False)
        svreload()
        print(":: 存档加载成功。")
        console.input("[dim]Enter 继续游戏 >[/dim] ")
        return True
    return False


def swget() -> str:
    """Read ``storyWhere``."""
    value = save.get("storyWhere")
    if not isinstance(value, str):
        save.storyWhere = "1000"
        return "1000"
    return value


def swset(sw: str) -> None:
    """Write ``storyWhere``."""
    if not isinstance(sw, str):
        raise TypeError("storyWhere must be a string")
    save.storyWhere = sw


def aprint(string: str, delay: float = 0.4) -> None:
    """Print and wait (manAI style)."""
    print(string)
    sleep(delay)


def askperm(
    permission_name: str,
    permission_command: str,
    perm_desc: str,
    rejectable: bool = True,
    who: str = "manAI",
) -> bool:
    """Ask the user for a permission."""
    print(f":: [cyan][索要权限][/cyan] {who} 申请{escape(permission_name)}。")
    print("   [dim]它将要执行：[/dim]")
    print(f"       {escape(permission_command)}")
    print(f"   [dim]作用：{escape(perm_desc)}[/dim]")
    if not rejectable:
        print(":: 无法取消，已经过 Unrejectable Command 审查。")
        return True
    print(":: 是否同意？[Y/n] ", end="")
    try:
        yn = input().strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return False
    if yn == "":
        return True
    return yn in ("y", "yes")


def saveit() -> None:
    """Save the active slot without extra output."""
    os.makedirs("flags", exist_ok=True)
    save.save(_slot_file())


def saveitp() -> None:
    """Save the active slot and announce it."""
    print("[cyan][!][/cyan] 存档已保存！")
    saveit()


def mkachieve(achieve_name: str, achieve_desc: str, achieve_id: str) -> None:
    """Unlock an achievement once."""
    if flags(achieve_id):
        return
    print(f"[cyan][!][/cyan] 获得成就：{achieve_name}")
    print(f"    [dim]{achieve_desc}[/dim]")
    mkflag(achieve_id, f":: 成就：{achieve_name}\n    - {achieve_desc}")


def fs_writesave(ifs: FileSystem) -> None:
    """Store *ifs* in the in-memory save state."""
    save.fileSystem = ifs.DumpToFile()


def fs_fromsave() -> FileSystem:
    """Rebuild a file system from the in-memory save state."""
    dump = save.get("fileSystem")
    if not isinstance(dump, str) or not dump:
        raise ValueError("save state has no serialized file system")
    ifs = FileSystem({}, [])
    ifs.LoadFromFile(dump)
    return ifs


def fs_initialize(ifs: FileSystem) -> FileSystem:
    """Load saved file system state into *ifs* (or save *ifs* when empty)."""
    if save.gotattr("fileSystem"):
        try:
            loaded = fs_fromsave()
        except (OSError, ValueError, TypeError) as exc:
            print(f":: [yellow]文件系统存档损坏，已重新初始化：{escape(str(exc))}[/yellow]")
            fs_writesave(ifs)
        else:
            ifs.files.clear()
            ifs.files.update(loaded.files)
            ifs.directories.clear()
            ifs.directories.extend(loaded.directories)
    else:
        fs_writesave(ifs)
    use_filesystem(ifs)
    return ifs


def userinfo_get() -> list[str]:
    """Read the four userinfo fields as a list."""
    return list(read_userinfo())


def passwd_faillock(
    userinfo: list[str] | tuple[str, ...],
    ifs: FileSystem,
) -> bool:
    """Return ``True`` when *userinfo*'s user is currently locked out."""
    try:
        content = ifs.ReadFile("/etc/faillocks/faillock", str, "system")
    except (DirectoryNotExists, FileNotFoundError, AccessDenied):
        return False
    username = userinfo[0]
    lines = [line for line in content.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        columns = line.split("|")
        if len(columns) < 5 or columns[0] != username:
            continue
        try:
            locked_at = datetime.datetime.fromisoformat(columns[3])
            duration = int(columns[4])
        except ValueError:
            continue
        if locked_at + datetime.timedelta(seconds=duration) > datetime.datetime.now():
            return True
        lines.pop(index)
        remaining = lines if lines else [""]
        WriteFile(
            "/etc/faillocks",
            "faillock",
            file_content=remaining,
            access="system",
            target=ifs,
        )
        return False
    return False


def _add_lock(
    userinfo: list[str] | tuple[str, ...],
    ifs: FileSystem,
    requirer: str,
    duration: int = 60,
) -> None:
    lock_line = "|".join(
        [
            userinfo[0],
            requirer,
            "faillock",
            datetime.datetime.now().isoformat(),
            str(duration),
        ]
    )
    try:
        existing = ifs.ReadFile("/etc/faillocks/faillock", str, "system")
    except (DirectoryNotExists, FileNotFoundError, AccessDenied):
        existing = ""
    lines = [
        line
        for line in existing.splitlines()
        if line.strip() and line.split("|")[0:1] != [userinfo[0]]
    ]
    lines.append(lock_line)
    permissions = [PermEnum.Access_Denied, PermEnum.Listable]
    try:
        if "faillock" not in ifs.ListDirectory("/etc/faillocks", access="system"):
            CreateFile(
                "faillock",
                file_permission=permissions,
                file_content=lines,
                file_owner=["root"],
                file_parent="/etc/faillocks",
                target=ifs,
                access="system",
            )
        else:
            WriteFile(
                "/etc/faillocks",
                "faillock",
                file_content=lines,
                access="system",
                target=ifs,
            )
    except DirectoryNotExists:
        CreateDirectory(
            "",
            "/etc",
            full_path="/etc/faillocks",
            target=ifs,
            access="system",
        )
        CreateFile(
            "faillock",
            file_permission=permissions,
            file_content=lines,
            file_owner=["root"],
            file_parent="/etc/faillocks",
            target=ifs,
            access="system",
        )


def login(
    userinfo: list[str] | tuple[str, ...] | None = None,
    ifs: FileSystem | None = None,
    requirer: str | None = "sudo",
    max_attempts: int = 5,
    prompt: str | Callable[[str], str] | None = None,
    lock_duration: int = 60,
) -> bool:
    """Full-featured login backend.

    This is the configurable counterpart of :func:`askpass` (similar to how
    ``FileSystem.AddFile`` is the explicit counterpart of ``CreateFile``).
    It optionally applies the virtual file system's faillock record.

    :param userinfo: ``(username, password_hash, hostname, salt)``; read from
        ``flags/userinfo`` when omitted.
    :param ifs: virtual file system used for the lockout record.  ``None``
        disables lockout storage.
    :param requirer: prefix used in prompts/messages, e.g. ``"sudo"``.
    :param max_attempts: attempts before writing a lockout record.
    :param prompt: custom prompt string or callable ``username -> str``.
    :param lock_duration: lockout duration in seconds.
    """
    if userinfo is None:
        userinfo = tuple(userinfo_get())
    if len(userinfo) < 4:
        raise ValueError("userinfo must contain username, hash, hostname and salt")
    if ifs is not None and passwd_faillock(userinfo, ifs):
        print(f"{requirer or ''}: account is locked, please wait.")
        return False

    prefix = f"{requirer}: " if requirer and requirer != "[No Requirer]" else ""
    password_hash = userinfo[1]
    salt = userinfo[3]
    for _ in range(max(1, max_attempts)):
        password = _base_ask_password_once(
            tuple(userinfo),
            requirer=requirer,
            prompt=prompt,
        )
        if password is None:
            # Ctrl-C / EOF is a cancellation, not a failed attempt.
            return False
        if verify_password(password, password_hash, salt):
            return True
        print(f"{prefix}incorrect password. please try again.")

    if ifs is not None:
        _add_lock(userinfo, ifs, requirer or "sudo", duration=lock_duration)
        print(
            f"{prefix}too many incorrect password attempts; "
            f"locked for {lock_duration} seconds."
        )
    return False


def askpass(
    userinfo: list[str] | tuple[str, ...] | None = None,
    ifs: FileSystem | None = None,
) -> bool:
    """Simplified login: default requirer/attempts/prompt, optional lockout."""
    return login(userinfo=userinfo, ifs=ifs)


#: Backwards-compatible alias for the old ``passwd_checker`` name.
passwd_checker = login


# endregion

# region Commands
@register("setslot")
def setslot(args: Arguments) -> None:
    svdslot()


@register("openslot")
def openslot(args: Arguments) -> None:
    svoslot()


@register("loadslot")
def loadslot(args: Arguments) -> None:
    if askyn(
        ":: [yellow][ ! 警告 ][/yellow] 加载当前槽位存档后，内存中存档信息将会丢失。继续吗？[y/N]",
        "n",
    ):
        print(":: 稍等，存档加载中...")
        svreload()
        print(":: 存档加载完毕。")
    else:
        print(":: 用户拒绝，正在退出...")


@register("resaveslot")
def resaveslot(args: Arguments) -> None:
    svsslot()


@register("saveslot")
def saveslot(args: Arguments) -> None:
    if askyn(
        ":: [yellow][ ! 警告 ][/yellow] 保存当前槽位存档后，文件中存档信息将会丢失。继续吗？[y/N]",
        "n",
    ):
        saveitp()
    else:
        print(":: 用户拒绝，正在退出...")


# endregion

# region Default slot
def load_default_slot() -> bool:
    """Load ``flags/defaultslot`` if it exists and points at a valid slot."""
    if not flags("defaultslot"):
        return False
    try:
        chosen = int(rdflag("defaultslot").strip())
        svslot(chosen, load=False)
        svreload()
        return True
    except (TypeError, ValueError, OSError) as exc:
        print(f":: [yellow]默认存档槽位无效，已忽略：{escape(str(exc))}[/yellow]")
        return False


@inject("before_quit")
def _auto_save_on_exit() -> None:
    """Save the active slot when the shell exits normally."""
    if not (config.SAVE_PATCH_ENABLED and config.AUTO_SAVE_ON_EXIT):
        return
    # storyWhere is a core save key; initialize it even when the story has
    # not touched it yet, so every save carries the current story position.
    if not save.gotattr("storyWhere"):
        save.storyWhere = "1000"
    try:
        saveit()
    except (OSError, TypeError, ValueError) as exc:
        print(f":: [yellow]自动存档失败：{escape(str(exc))}[/yellow]")


# The historical behaviour was "load the default slot while importing
# Perhaps.fastutil".  Keep it, but never let a broken slot crash the import.
if not load_default_slot():
    if (
        config.SAVE_PATCH_ENABLED
        and config.AUTO_LOAD_ON_START
        and os.path.isfile(_slot_file())
    ):
        svreload()
# endregion
