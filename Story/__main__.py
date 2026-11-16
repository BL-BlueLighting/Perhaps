"""
doas -su mylife.root
Menu File
"""

import os
import runpy

import rich.console
from builtins import print as rprint
from rich import print as iprint

# EasyCliMenu 库开发者出来挨打！
# 示例和文档写的不一样！
# 文档里的导入名是 `cli_menu`，实际安装后是 `climenu`。
from climenu import CliMenu

chapters = {
    "pre": {
        "Name": "序章 - 意外而来",
        "Description": "你从昏迷中醒来，发现自己处于 Emergency Mode (应急恢复模式，又称 CLI Mode)，与 manAI 一起拯救你自己。"
    }
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

console = rich.console.Console()
console.clear()
print = console.print

LOGO = open("texts/logo.txt", "r").read()

print("[white]" + LOGO + "[/white]", justify="center")
print()

print("doas -su mylife.root", justify="center")
print("Version 1.0.0", justify="center")
print("[italic]Python Version[/italic]", justify="center")
print()

# EasyCliMenu 每次重绘都会清屏，把 Logo 放进标题里才能一直显示。
MENU_HEADER = LOGO.rstrip("\n") + "\n\ndoas -su mylife.root  |  Version 1.0.0  |  Python Version"


def choose_chapter() -> str | None:
    """
    显示章节选择菜单。

    :return: 选中的章节 key；若用户选择退出菜单则返回 None。
    """
    items = list(chapters.items())
    options = [chapter["Name"] for _, chapter in items] + ["退出菜单"]

    menu = CliMenu(
        options=options,
        title=MENU_HEADER,
        description="↑/↓ 选择章节，←/→ 翻页，Enter 确认，q / Esc 退出",
        page_size=10,
    )
    choice = menu.show()

    if choice is None or choice == len(items):
        return None
    return items[choice][0] #type: ignore


def run_chapter(chapter_key: str):
    """
    执行 `chapters/<chapter_key>.py`，执行完毕后返回主菜单。
    """
    chapter = chapters[chapter_key]
    chapter_file = os.path.join(BASE_DIR, "chapters", f"{chapter_key}.py")

    console.clear()
    print(f"[bold cyan]{chapter['Name']}[/bold cyan]")
    print(f"[dim]{chapter['Description']}[/dim]")
    print()

    console.input("[dim]按 Enter 开始游戏[/dim]")

    if not os.path.isfile(chapter_file):
        print(f"[red][!][/red] 章节文件不存在：{chapter_file}")
    else:
        try:
            runpy.run_path(chapter_file, run_name="__main__")
        except SystemExit:
            pass
        except (KeyboardInterrupt, EOFError):
            print("\n[yellow]章节已中断。[/yellow]")
        except Exception:
            console.print_exception()

    exit()


def main():
    """菜单主循环。"""
    while True:
        chapter_key = choose_chapter()
        if chapter_key is None:
            console.clear()
            print("正在退出游戏 ...")
            return
        run_chapter(chapter_key)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        console.clear()
        print("\n正在退出游戏 ...")

