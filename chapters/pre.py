"""
doas -su mylife.root
Chapter: Pre

By BL.BlueLighting
Enjoy! :-)
"""

from framework import *

#region Injects
@inject("prompt_patcher")
def prompt_patch(prompt: str, userinfo: tuple[str, str, str, str], dir: str):
    return f"\n[green]{userinfo[0]}@{userinfo[2]}[/green]:{dir}[cyan]$[/cyan] "
#endregion

#region Registers
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
            print()
            print("[dim]// 推荐新玩家使用 setslot 设置默认槽位。 //[/dim]")
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
        aprint("[cyan](>_>)[/cyan] 诶，Perhaps，你活了多少年啊？")
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
        aprint("[italic]提示：当 manAI 没有继续输出时，您可以继续使用 manAI 来与其对话。[/italic]")
        swset("1004")
    elif sw == "1004":
        aprint("(awa) 言归正传。")
        aprint("      为了帮你恢复，容我搜一下数据。")
        if askperm("执行命令", 'find / -name "*handbook"', "搜索手册 (放心，HumanOS 给予的用户空间较小，东西也少。用户无法访问系统目录，所以搜不了多久。)"):
            def processloopout(x):
                if x == 0:
                    aprint("(awa) 现在就可以静静等待啦！")
                elif x == 20:
                    aprint("(._.) btw, 你不觉得无聊吗？")
                    aprint("(^_^) 我给你讲个笑话。")
                elif x == 25:
                    aprint("(^_^) 知道为什么神父会嫉妒日本吗？")
                elif x == 30:
                    aprint("(^_^) 因为日本天上会掉小男孩！")
                elif x == 35:
                    aprint("(?_?) 诶诶？不好笑吗")
                elif x == 40:
                    aprint("(._.) 好吧...")
                elif x == 50:
                    aprint("($_$) 主要是目前还没办法给你连上 BraiNET，")
                elif x == 55:
                    aprint("      不然现在你可以边刷视频边等。")
                elif x == 60:
                    aprint("(qwq) 为什么不回我...")
                elif x == 65:
                    aprint("[cyan](!_!)[/cyan] 呃呃，主要是我不知道说什么...")
                    aprint("[cyan](._.)[/cyan] 突然发现... 我，我，我怎么有文字表情？！")
                elif x == 70:
                    aprint("(0_0) 啊？")
                    aprint("      呃，不过应该也是一件好事。")
                    aprint("[cyan](?_?)[/cyan] 为啥？")
                    aprint("(awa) 因为这说明你正在 AI 化哦。")
                    aprint("      后面你就可以自己想接什么知识就接什么了。")
                    aprint("      因为 AI 不是可以扩展数据库嘛。")
                    aprint("      但是你应该还没转化完全——差不多在这里待上几天就好了。")
                    aprint("      也不要问我是怎么知道的。")
                    aprint("(<_<) 我就是这么过来的。")
                elif x == 80:
                    aprint("      对于你来说，根据我的知识库")
                    aprint("      你是在身体机能恢复后还可以再进来的。")
                    aprint("      你的 AI 化也会一直保留，晚上睡觉时做梦就会来到这里。")
                    aprint("      如果你真想睡觉，可以 exit。")
                elif x == 85:
                    aprint("[cyan](^_^)[/cyan] 那还蛮不错的。")
                    aprint("(#_#) 但是提醒一下，可能过程有点痛哦")
                    aprint("      毕竟要把你的意识从脑细胞转换成字节...")
                    aprint("[cyan](%_%)[/cyan] 吓人。")
                    aprint("      不过，你说你也是这么过来的？")
                elif x == 90:
                    aprint("(,_,) 对的。")
                    aprint("      我应该是某个人类转换过来的，就是和你一样，机能丢失，只不过我们当时时代落后罢了。")
                    aprint("      但相信我，一定是好结果！")
                    # 这里是作者小贴士，我不卖刀子，真的是好结果，Perhaps 说的也是真的喵。
                    aprint("      快完成了！")
                elif x == 95:
                    aprint("[cyan](*_*)[/cyan] 希望如此。")

            def processendsout():
                print("搜索成功。\n找到 1 个文件：\n    /home/perhaps/training/HumanOSFixingGuideHandbook.txt")

            common_process_loop(
                process("搜索中..."),
                100,
                0.1,
                processloopout,
                processendsout
            )

            swset("1005")
            saveitp()
            aprint("[cyan](-_-)[/cyan] 成为 AI 之后就会经常保持这种面瘫脸吗。")
            aprint("(<_<) 这个...还真是...")
            aprint("[cyan](-_-)[/cyan] (os: 好可怜未来的我和 Perhaps...)")
            return
        else:
            aprint("(!_!) 诶嘞！但是不搜就没法继续耶...")
            aprint("      请同意哦！")
            return
    elif sw == "1005":
        aprint("(@_@) (FLASH THINKING...)", delay=5)
        aprint("      Emm，你这种状况，呃，很简单")
        aprint("(^_^) 大概就是，我执行一个命令，然后你等待一两天，中间可以和我说说话。")
        aprint("      这个命令会让身体开始修复你的神经系统，最后拉起神经系统服务，你睡一觉，登出即可。")
        aprint("      但是一想到马上就要和你分别... 好不舍...")
        aprint("(._.) 诶，你叫什么来着？")
        aprint("[cyan](+_+)[/cyan] Silenter. 用户名只是我的网名而已。")
        aprint("(._.) 好的！Silenter，请同意执行哦！")
        askperm("执行命令", "systemutil nervous autofix && systemutil nervous restart && hsh_suspendrun", "修复。", False)
        swset("1006")
        aprint("      继续执行 manAI，可以查看输出哦！")
    elif sw == "1006":
        aprint("Nervous self-fix process finished successfully.")
        aprint("Fixed broken nervouses: 986410 nervous cells.")
        aprint("")
        aprint("Starting up Nervous Services...")
        aprint("Started!")
        aprint("")
        aprint("(qwq) 再见，Silenter 君，祝好！")
        aprint("      [dim]希望能看见 AI 化的你在夜晚与我相见...[/dim]")
        aprint("      执行 restart 吧。")
        swset("1007")
        saveitp()
    else:
        aprint("(qwq) 走吧，至少晚上 We can see again~")
        aprint("! 提示：执行 restart !")

@register("perhaps")
def perhapsAlias(args: Arguments):
    if save.PerhapsAlias:
        manAI(args)
    else:
        return COMMAND_NOT_FOUND

@register("alias")
def alias(args: Arguments):
    if not save.EnableAlias:
        return COMMAND_NOT_FOUND

    act: str = args[0].__str__()
    if act == "help":
        print("alias Command")
        print("    - alias <new alias name>=<source commands>")
        print("    - Cancel alias: alias <exists alias name>=")
        return
    else:
        aliaspair = act.split("=")
        if len(aliaspair) < 1 or aliaspair[1] == "":
            # cancel alias
            registry.pop(aliaspair[0])
            if aliaspair[0] == "perhaps":
                mkachieve("表面一套，背后一套", "你欺骗 manAI 的感情😡！", "liar")

        @register(aliaspair[0])
        def _(args: Arguments):
            cmd = Command(aliaspair[1])
            cmd.parse()
            cmd.execute()
        print("alias: alias created successfully.")

@register("restart")
def restart(args: Arguments):
    if swget() != "1007":
        print("restart: Failed to restart. Brain power nervous no response.")
        return

    print("restart: Restarting...")
    print("")
    initpre = open("./texts/initpre_fixed.txt", "r").readlines()

    for line in initpre:
        rich.print(f"[green]{line.strip()}[/green]", flush=True)
        sleep(0.04)

    saveitp()

    print("")
    mkachieve("你好，世界！", "完成序章。但你和 manAI 的故事，才刚刚开始。", "hello_world")

    try:
        console.input("> [dim]Enter 显示演出人员表，Ctrl+C 跳过。[/dim]")
    except KeyboardInterrupt or EOFError:
        exit()

    # 演出人员表
    mt = MemberTable()
    mt.scroll(open("./texts/chapter_pre_end.txt", "r").read())

    print("You can log out now.")
    
#endregion

#region Main Loop
init()
main_while()
#endregion

