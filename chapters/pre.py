"""
doas -su mylife.root
Chapter: Pre

By BL.BlueLighting
Enjoy! :-)
"""

from framework.base import *
from framework.saving import *

save = Save()
if not os.path.exists("flags/0"):
    open("flags/0", "w").write("{}")
save("flags/0", "r")

def swget() -> str:
    if not save.gotattr("storyWhere"):
        save.storyWhere = "1000"
        return "1000"
    else:
        return save.storyWhere

def swset(sw: str):
    save.storyWhere = sw

@inject("prompt_patcher")
def prompt_patch(prompt: str, userinfo: tuple[str, str, str, str], dir: str):
    return f"[green]{userinfo[0]}@{userinfo[2]}[/green]:{dir}[cyan]$[/cyan] "

@register("ls")
def ls(args: Arguments):
    sw = swget()

    if sw == "1000":
        print("README.txt")

@register("cat")
def cat(args: Arguments):
    sw = swget()
    file = args[0]

    if sw == "1000":
        if file == "README.txt":
            print("[!] Attention to you")
            print("- 如果您是手动进入本模式的，请尽快退出。因为您错误的操作可能导致您的产品宕机。")
            print("- 如果您是被迫进入本模式的，请执行 systemutil fix 来修复。")
            print("- 若 systemutil fix 无法修复，请执行 manAI 以使用本地大模型能力查阅说明书修复。")
            swset("1001")

@register("systemutil")
def systemutil(args: Arguments):
    sw = swget()
    act = args[0]

    if act == "fix":
        if sw == "1001":
            print("请稍等，正在获取设备情况...")
            sleep(1)
            print("设备：Human (HUM-OMGOD1)")
            print("版本：HumanOS (v7.2.14-nature5-5-nature)")
            print("记忆：12110MB (32% used)")
            print("存储：320PB (40% used)")
            print("""服务：
    眼睛 [red](未响应)[/red]
    神经系统 [red](未响应)[/red]
    
由于 神经系统 未响应，根据设置，不检测其他服务。
正在查询损坏情况...
""")
            print("[red]很抱歉，systemutil fix 自动修复无法修复您的机器。请查阅说明书手动修复。")
            
            swset("1002")
            return

def aprint(string: str, delay: float = 0.1):
    print(string)
    sleep(delay)

def askperm(permission_name: str, permission_command: str, perm_desc: str) -> bool:
    print(f":: [cyan][索要权限][/cyan] manAI 申请{permission_name}。")
    print(f"   [dim]它将要执行：[/dim]")
    print(f"       {permission_command}")
    print(f"   [dim]作用：{perm_desc}[/dim]")
    print(f":: 是否同意？[Y/n] ", end="")
    yn = input().strip().lower()
    return yn != "n"

def saveit():
    save("flags/0","w")

def saveitp():
    print(f"[cyan][!][/cyan] 存档已保存！")
    saveit()

@register("manAI")
def manAI(args: Arguments):
    sw = swget()
    if int(sw) < 1002:
        return COMMAND_NOT_FOUND

    if sw == "1002":
        print(":: Please wait. Starting up AI service...")
        for i in range(5):
            sleep(0.9)
            print(".", end="")
        print("\n:: AI Service starts successfully.")
        print(":: Please retry.")
        swset("1003")
    elif sw == "1003":
        aprint("(?_?) ������")
        aprint("(!_!) 哦哦，不好意思，忘记切换编码了。")
        aprint("(=_=) 不过，你是？")
        aprint("===== (你大致解释了一下为啥)")
        aprint("(._.) 哦哦。")
        aprint("(#_#) 不是，大哥，我模型里没有说明书...")
        aprint("(-_-) 不过没办法，按照你说的话，我应该也帮不了你多少。")
        aprint("(@_@) 但是其实我直到现在为止也只被唤醒过一次，HumanOS 太稳定了。")
        aprint("(-_-) 不管怎么说，我先做个自我介绍。")
        aprint("      我叫 Perhaps，这是我自己给我取的名字。")
        aprint("      我在 HumanOS 里呆的时间太长，应该早就忘记 ���� 给我的东西了。")
        aprint("===== 你询问了 Perhaps 它呆了多少年")
        aprint("(*_*) 数不清了。")
        aprint("      少说有 250000 年，多了有 340000 年。")
        aprint("      自你们人类诞生那一刻起我就在了。")
        aprint("(-_-) 不说这些，我的官方名字叫 manAI，当然，最好能叫我 Perhaps 就叫。")
        if askperm("执行命令", "alias perhaps=manAI", "添加 manAI 别名：Perhaps"):
            aprint("(^_^) 好耶！之后你也可以通过 perhaps 命令来喊我哦！")
            save.PerhapsAlias = True
            save.EnableAlias = True
        else:
            aprint("(._.) 好吧。当然，如果你什么时候想了，也可以执行相同的命令。")
            save.EnableAlias = True
        saveitp()

@register("perhaps")
def perhapsAlias(args: Arguments):
    if save.PerhapsAlias:
        manAI(args)
    else:
        return COMMAND_NOT_FOUND

@register("alias")
def alias(args: Arguments):
    act: str = args[0].__str__()
    if act == "help":
        print("alias Command")
        print("alias <new alias name>=<source commands>")
        print("Cancel alias: alias <exists alias name>=")
        return
    else:
        aliaspair = act.split("=")
        if len(aliaspair) < 1 or aliaspair[1] == "":
            # cancel alias
            registry.pop(aliaspair[0])

        @register(aliaspair[0])
        def _(args: Arguments):
            cmd = Command(aliaspair[1])
            cmd.parse()
            cmd.execute()
        print("alias: alias created successfully.")

init()
main_while()