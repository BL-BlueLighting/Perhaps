"""
doas -su mylife.root
Chapter: 1 (first)

First chapter, Repent, then Recreate
What adventure more?
"""

from Perhaps import *
from Perhaps.fastcmdutil import *
from Perhaps.fileutil import *
from Perhaps.manAI import *
from Perhaps.fastdebugger import *
from Perhaps.pm import MPMManager as PerhapsMPMManager
from Perhaps.pm.cli import CLIController

enableDebugger = True

if not flags("defaultslot"):
    svslot(1)

fs = FileSystem({}, [])

def MakeFilesAndDirectories():
    global fs
    fs = InitBaseFileSystem()

    #region manAI
    CreateFile("WHEN_U_BACK.txt", file_content = [
        "Remember me! Use manAI!"
    ], file_parent="~")

    CreateDirectory("", "", "/home/perhaps/models")
    CreateDirectory("", "", "/home/perhaps/models/trainingDatas")
    CreateDirectory("", "", "/home/perhaps/models/teacherModel")
    CreateDirectory("", "", "/home/perhaps/models/teacherModel/deepseek-v4-flash")

    CreateFile("configuration.toml", file_content=[
        "[official_api]",
        "endpoint=https://api.deepseek.com/chat/completions",
        "method=openai_v1",
        "api_key=sk-kfcCrazyThursdayVme50NotRealkeys",
        "[eula]",
        "agree=true"
    ], file_parent="/home/perhaps/models/teacherModel/deepseek-v4-flash")

    CreateFile("configuration.toml", file_content=[
        "[settings]",
        "eula_agree=true",
        "model=deepseek-v4-flash/configuration.toml"
    ], file_parent="/home/perhaps/models/teacherModel")

    for i in range(10):
        CreateFile(f"data_{i}.gguf",
                   file_content=["<BINARY>"],
                   file_parent="/home/perhaps/models/trainingDatas",
                   file_owner="Perhaps",
                   file_permission=[PermEnum.Listable, PermEnum.Access_Denied, PermEnum.Unwritable])

    CreateFile(f"prehot.py", file_content=[
        "from HumanOSmanAI import *",
        "aiObject = manAI()",
        "aiObject.create('./*.gguf')",
        "aiObject.fill()",
        "aiObject.prehot()",
        "aiObject.initialize()"
    ],
        file_parent="/home/perhaps/models/trainingDatas/",
        file_owner="Perhaps",
        file_permission=[PermEnum.Listable, PermEnum.Runnable, PermEnum.Readable])

    CreateFile(f"server.py", file_content=[
        "from .prehot import *",
        "import huOSsocket as socket",
        "sock = socket.socket(socket.ApiSock, socket.PostSock)",
        "sock.server()",
        "sock.bind('/dev/manAI')",
        "sock.mainloop = manAISocket()",
        "sock.mainloop.start()",
        "sock.start()",
        "print('manAI service started.')"
    ],  file_parent="/home/perhaps/models/trainingDatas/",
        file_owner="Perhaps",
        file_permission=[PermEnum.Listable, PermEnum.Runnable, PermEnum.Readable])

    #endregion

    #region Stories

    #endregion

    #region Saving
    fs_writesave(fs)
    saveit()
    #endregion
    return fs

def pprint(content: str):
    aprint(f"[cyan]{content}[/cyan]")

if save.gotattr("fileSystem"):
    fs = fs_initialize(fs)
else:
    fs = MakeFilesAndDirectories()

@patcher("prompt_patcher")
def _ (prompt: str, userinfo: tuple, dire: str):
    if swget() == "1001":
        print("Fixing Help: systemutil, systemfixer")
        return f"[red]EmergencyShell[/red]# "
    return prompt_patch(prompt, userinfo, dire)

@aiReg("1000")
def _ ():
    aprint("(-_-) zzZ")
    aprint("(-_+) 干嘛... 谁啊？")
    aprint("(!_!) Silenter! 是你诶")
    aprint("[cyan](^_^) I'M[/cyan] BACK!")
    aprint("(-_-) 不过现在我们应该干啥🤔")
    aprint("[cyan](@_@)[/cyan] 我不到啊")
    aprint("(⇀‸↼) ...")
    aprint("(≧▽≦) 我有一计！")
    aprint("       不如看看你 AI 化到哪了！")
    aprint("[cyan](?_?) 何[/cyan]意味...")
    aprint("")
    if not askperm("执行命令", "models list", "列出所有模型"):
        aprint("(?_?) 诶嘞？不同意？")
        aprint("(qwq) 你不同意就不能继续了诶...")
        return
    else:
        aprint(":: Command Executing...")
        aprint("Executed. ErrCode=0, Result:")
        aprint("HumanOS AI System: Show model list.")
        aprint("   - manAI: 9182 billions data, training status: [TRAIN_SUCCESSFULLY]")
        aprint(f"   - {userinfo_get() [0]}: 5000+ billions data, training status: [MIGRATING_NERVOUS], arguments: 70%")
        aprint("   - (... use models initialize <ggufs> to add model)")
        aprint("(^_^) 70%!")
        aprint("[cyan](>﹏<)[/cyan] 痛！痛...嘶——哈——")
        aprint("(°□°;) 别吓我！")
        aprint("===== (你昏倒了过去)")

        sleep(2)

        emer = """███████╗███╗   ███╗███████╗██████╗  ██████╗ ███████╗███╗   ██╗ ██████╗██╗   ██╗    ███╗   ███╗ ██████╗ ██████╗ ███████╗
██╔════╝████╗ ████║██╔════╝██╔══██╗██╔════╝ ██╔════╝████╗  ██║██╔════╝╚██╗ ██╔╝    ████╗ ████║██╔═══██╗██╔══██╗██╔════╝
█████╗  ██╔████╔██║█████╗  ██████╔╝██║  ███╗█████╗  ██╔██╗ ██║██║      ╚████╔╝     ██╔████╔██║██║   ██║██║  ██║█████╗  
██╔══╝  ██║╚██╔╝██║██╔══╝  ██╔══██╗██║   ██║██╔══╝  ██║╚██╗██║██║       ╚██╔╝      ██║╚██╔╝██║██║   ██║██║  ██║██╔══╝  
███████╗██║ ╚═╝ ██║███████╗██║  ██║╚██████╔╝███████╗██║ ╚████║╚██████╗   ██║       ██║ ╚═╝ ██║╚██████╔╝██████╔╝███████╗
╚══════╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝   ╚═╝       ╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝
                                                                                                                       """

        print(f"[red]{emer}[/red]")
        print()
        print("[red]EMERGENCY MODE -- RECOVERY[/red]")
        print("[yellow][!][/yellow]")
        print("We have detected your body is now in emergency mode. To recovery your body, we have opened an emergency shell.")
        print("Emergency shell user is high permission user, please be careful.")
        print("Emergency shell will boot in 5 seconds.....")
        aprint("Emergency shell will boot in 4 seconds....", delay=1)
        aprint("Emergency shell will boot in 3 seconds...", delay=1)
        aprint("Emergency shell will boot in 2 seconds..", delay=1)
        aprint("Emergency shell will boot in 1 second.", delay=1)
        aprint("\nEmergency shell is opening now...", delay=0.5)

        return "1001"

@register("systemutil")
def _(args: Arguments):
    if swget() != "1001":
        print("HumanOS SystemUTIL")
        print(":: Undetected troubles. systemutils are not enabled.")
        return

    if len(args) < 1:
        print("HumanOS SystemUTIL")
        print("systemutil shell: Open system utils shell")
        print()
        print("(humansh cannot use advanced syntaxes.)")
        return

    elif args[0] == "shell":
        print("HumanOS SystemUTIL Shell")
        print(":: Initializing...")
        print()
        print("Type ':h' or 'help' to list all commands.")
        while True:
            try:
                ipt = input("> ")
            except KeyboardInterrupt:
                print(":: Shutting down...")
            else:
                head = ipt.split(" ")[0]
                params = None
                if len(ipt.split(" ")) > 1:
                    params = str(ipt.split(" ")[1:])

                if head.startswith("!"):
                    # command execute mode
                    try:
                        cmdi = Command(head[1:] + params)
                        cmdi.parse()
                        cmdi.execute()
                    except Exception:
                        print("Unexcepted exception.")

                if head == "help" or head == "h":
                    print("HumanOS SystemUTIL")
                    print(":h / :help / h / help - Help")
                    print(":s / :status - Show statuses")
                    print(":hmSocket / :hm / :hms - HumanOS HumanMod Socket connector middle component.")
                    print(":rec / :r / :recovery - Run auto recovery")
                elif head == ":s" or head == ":status":
                    print("HumanOS Body Statuses")
                    print()
                    print("""
- Vital Signs:
    :: Body Temperature - [red]Too Low[/red]: 10 C
    :: Heart Rate - [red]Too Low[/red]: 15 BPM
    :: Respiratory Rhythm - Unstable
    :: Blood Pressure - [red]Too High[/red]
    :: Oxygen Saturation - [red]Too Low[/red] - 56%
- Neurological and Sensory:
    :: Consciousness Level - [yellow]Low[/yellow]
    :: Vision - [dim]Unactive[/dim]
    :: Hearing - [dim]Unactive[/dim]
    :: Touch Sensation - [dim]Unactive[/dim]
    :: Balance - [dim]Active[/dim]
    :: Pain Sensation - [red]Brain, Breathe, Hand, Thinking, Brain Cell[/red]
- Musculoskeletal System:
    :: Muscle Strength - [yellow]Too Low[/yellow]
    :: Muscle Tone - Active
    :: Joint Range of Motion - Brisk
    :: Standing Balance - Active
    :: Gait - Brisk
- Respiratory and Circulatory:
    :: Pulmonary Ventilation - [yellow]Unstable[/yellow]
    :: Cardiac Pumping - [red]Too Slow[/red]
    :: Peripheral Circulation - Active
- Digestive and Metabolic:
    :: Appetite - Active
    :: Gastrointestinal Motility - Doing Something
    :: Urination - Nothing
    :: Defecation - Nothing
    :: Blood Glucose Regulation - Active
    :: Water and Electrolyte Balance - Active
- Endocrine and Immune:
    :: Thyroid Function - Active
    :: Adrenal Function - Active
    :: Immune Defense - Active
    :: Inflammatory Response - Nothing
- Skin and Thermoregulation:
    :: Skin Integrity - Active
    :: Sweating - [yellow]Too Much[/yellow]
    :: Thermoregulation - [bold red]UNCONTROLLABLE[/bold red]
- Sleep and Energy:
    :: Wakefulness - [dim]No response[/dim]
    :: Sleep Rhythm - Stable
    :: Physical Stamina - Active
    :: Fatigue Sensation - Nothing""")

                    print("\nOverall assessment: [bold red]Need to fix.[/bold red]")
                    print("For fix, you should initialize HumanMod.")
                    print("Execute '!modprobe hmos.HumanMod' to initialize.")
                    print("After initialize, run ':hmSocket connect'.")

                elif head == ":hmSocket" or head == ":hm" or head == ":hms":
                    if not save.HumanModProbe:
                        print("hmsocket: Cannot connect to HumanMod Service. Does it stopped?")
                        return

                    print("hmsocket: Connection established.")
                    print("hmsocket: HumanMod utils enabled.")

                    if params is None:
                        print("hmsocket: need arguments.")
                        print("          use :hm help / :hm h to list all HumanMod utils.")
                        return

                    if "h" in params or "help" in params:
                        print("hmsocket: HumanMod utils")
                        print("          :hm bpmReseter")
                        print("          :hm bpmTester")
                        print("          :hm breatheMixer")
                        print("          :hm oxygSlider")

                    elif "bpmReseter" in params:
                        print("hmsocket: Hang up...")
                        print("          HumanMod is executing. Please do not do anything.")
                        print("[ HumanMod Broadcast ]")
                        print(":: Heart rate detected: 15BPM")
                        print(":: 15BPM < Too Low Deadline...")
                        print("   BPM Correction is running")
                        print()
                        aprint("[ [green]SUCCESS[/green] ] Heart daemon respond, setting to normal state...", delay=3)
                        aprint("            Reset finished. Sending finish packet to socket...", delay=2)
                        print("HumanMod BPMReset Finished.")
                        print()
                        print("hmsocket: Finish packet received. ")
                        print("          BPMReset process finished successfully.")
                        save.hmSock_BPMreset = True
                        return

                    elif "bpmTester" in params:
                        print("hmsocket: Creating request...")
                        print("          Request received...")
                        print("          Establishing connection...")
                        print("          Connected!")
                        print()
                        testerList = []
                        def BeatRandomer() -> int:
                            return random.randint(15, 124)

                        for i in range(random.randint(1, 20)):
                            br = BeatRandomer()
                            print(f"{i+1} {br}") # fstring 神力
                            testerList.append(br)
                        deadline = BeatRandomer()
                        lowOrHigh = bool(random.randint(0, 1)) # true high false low
                        print("[ HumanMod BPM Tester ]")
                        print(f"Select out BPMs {"higher" if lowOrHigh else "lower"} than {deadline} (equals no)")
                        try:
                            bpmslist = input("Input number indexes, use space to split> ")
                            bpms = bpmslist.split(" ")
                        except ValueError:
                            print("Incorrect BPMs. Please try again.")
                            return
                        else:
                            if len(bpms) < len(testerList):
                                print("Incorrect BPMs. Please try again.")
                                return

                            solves = []
                            for i in testerList:
                                if lowOrHigh:
                                    solves.append(i if i > deadline else 0)
                                else:
                                    solves.append(i if i < deadline else 0)

                            solves.sort()
                            bpms.sort()

                            if bpms != solves:
                                print("Incorrect BPMs. Please try again.")
                                return
                            else:
                                print("BPM Trouble found!")
                                print("Reseting...")
                                print("hmsocket: Reset packet received. Task finished successfully.")
                                save.hmSock_BPMTrouble = True
                                return

                    else:
                        # 我懒了，不写
                        print("hmsocket: Access Denied.")
                        return

                elif head == ":r" or head == ":rec" or head == ":recovery":
                    print("HumanOS SystemUTIL Auto Recovery")
                    if not save.gotattr("hmSock_BPMTrouble") or not save.gotattr("hmSock_BPMreset"):
                        print(":: Detected unautomatic-recoverable troubles.")
                        print("   Please fix them first.")
                        return

                    print("Proceeding Auto Recovery...")
                    print("Don't force shutdown or do anything...")
                    for i in range(30):
                        print(".", end="")
                        sleep(i)
                    print()
                    print("Auto Recovery finished.")
                    # 草好潦草的结尾
                    swset(1002)
                    return

# FAQ♂

@register("modprobe")
def modprobe(args: Arguments):
    def humanMod():
        print("HumanMod Service Initialized.")
        print("Socket service listening on /dev/hmsocket:*")
        print("Waiting devices...")
        save.HumanModProbe = True
        saveit()

    def fallback():
        print("modprobe: mod not found")

    initializable_mods = {
        "hmos.HumanMod": humanMod
    }

    if len(args) <= 0:
        print("modprobe: need mod name")
        return

    initializable_mods.get(args[0], fallback)()
    return

# btw say real DROM is linear storying
@aiReg("1002")
def _():
    #print("FAQ♂")
    aprint("(   ) Only feels like nothing could be better when I am with you...")
    aprint("      When I am with you...")
    aprint("      Dance dance all night weaving we together")
    aprint("      It's a breakthrough, it's a breakthrough...")
    print()
    aprint("[cyan](?_?) 何意味... 为什么要唱 Xterfusion...[/cyan]")
    aprint("(-_-) zzZ")
    aprint("[cyan](@_@) (⚡ Flash Thinking...)[/cyan]")
    aprint("      好何意味。")
    aprint("      感觉不是唱的... 不是大哥你睡觉听 Xterfusion?")
    print()
    aprint("(-_+) 有人？")
    aprint("(^_^) yay! 是 Silenter")
    aprint("      给你带个好消息：在你昏迷的这段时间，HumanOS Modeler 加快了 AI 化进程，现在应该已经完成了！")
    if not askperm("执行命令", "models list", "列出所有模型"):
        aprint("(?_?) 诶嘞？不同意？")
        aprint("(qwq) 你不同意就不能继续了诶...")
        return
    else:
        aprint(":: Command Executing...", delay=2)
        print("Executed. ErrCode=0, Result:")
        print("HumanOS AI System: Show model list.")
        print("   - manAI: 9182 billions data, training status: [TRAIN_SUCCESSFULLY]")
        print(f"   - {userinfo_get()[0]}: 11225 billions data, training status: [MIGRATED], arguments: 100%")
        print("   - (... use models initialize <ggufs> to add model)")
        # it's sudden......
        if not askperm("执行命令", "models add-util mpm --model 1", "添加 Memory Package Manager 到你的 utils 里"):
            aprint(":: Command Executing...", delay=4)
            print("Executed. ErrCode=0, Result:")
            print("HumanOS AI System: Add Util")
            print("    - Fetching remote resource /dev/enp2s1:brainet://huosai.humanos.com/api/models/add-util/util-fetch?name=mpm...")
            print("    - Fetched remote resource: Memory Package Manager (mpm) by Holy Selbrights")
            print("    - Downloading...")
            print("      ———————————————————————— 19.8MiB/19.8MiB 2.5MiB/s")
            print("    - Verifying remote resource hashes...")
            print("    = mpm.tar.gz SHA256:94c250f507a97d5e5fd1926157a766111d92f71b95397eee2850de43394202a5")
            print("    = mpm.sh SHA256:SKIP MD5:SKIP B64:TVBN")
            print("    - Creating soft-links...")
            print("    - Registering utils table...")
            print("    - Restarting AI model...")
            print("    - Failed to restart: Device or resources are busy")
            aprint("(O_O) Emm... 看起来似乎你得，呃，手动重启？")
            save.NeedReboot = True
            saveit()
            return "1003"

@aiReg("1003")
def _():
    if save.NeedReboot:
        aprint("(?_?) 啊嘞？不重启就想要加载 MPM 吗？")
        return "1003"

    aprint("(^_^) yay!")
    aprint("      现在来试试 mpm!")
    save.MPMActivated = True

    return "1004"

# Memory Package Manager 的包世界数据。commands 里有些名字只是剧情演出，
# 不一定有真正注册的 handler；Perhaps PM 默认不拿这种假命令报错。
MPM_PACKAGES: dict[str, dict[str, str | int | list]] = {
    "mpm": {
        "Name": "Memory Package Manager",
        "Version": "6.0.0.3106",
        "Author": "Holy Selbrights / BL.BlueLighting",
        "Date": "2026/11/17 15:56:53"
    },
    "perhaps-framework": {
        "Name": "Perhaps Framework",
        "Version": "1.0.1",
        "Author": "BL.BlueLighting",
        "Date": "2026/11/17 15:57:53"
    }
}
MPM_REGISTRYS: dict[str, list[str]] = {
    "mpm": [
        "mpm"
    ],
    "perhaps-framework": [
        "reboot",
        "ls",
        "cd",
        "cat",
        "manAI",
        "models",
        "clear",
        # and a lot, much, many!! i don't want to list it. LET'S DESTROY WORLDDDDDDD!
    ]
}


class MPMController(CLIController):
    """Memory Package Manager CLI，底层换成 Perhaps PM。"""

    def print_version(self) -> None:
        # 雷霆大汉堡，来自 asciiart.website, by Ric Hotchkiss
        print("""
                    _____________
           ._===~~~\\~' .K!.r  .L,~~~~==__
        _=~'  j-!+  =-  /-:L _  _ .=  =- ~\\=_
     .=~.= !+_   -f_ ~\\_   ./.=`\\r       ~X  ~\\
    :'j-    ` .  ~~'+' -=/'`~ __ ._ !@:, `' +, \\
   .@      ~' ~) -r-  L  /f.L  j  ._`  ',  :    \\
   |          `   ~-  `  \\  :L ! ,'`- :!'-= '   `;
  .d,                        /=  ~-    '         \\
/~L+t_                                         _=+\\_
D~.j/\\f=\\__                                ._=*~~Z~t\\;
b/VGf\\qr===MMmm____                  .__=q/V*5\\_Z=\\d,)
b !, | !r==| \\ ~~G+*#P~Zrqm=====q=fT7'    \\NL,\\`*mL_~
 ~\\+LGW#W_  |d  .Df~.t/ W\\/;    `@~K4;      bZ8   .!
 -b`tL    \\+P/\\=f~\\=d   #+7|     b4' `\\    .*/M; /'
 |#P\\=*Gmr_d +__    t__4d)G#qmmmm'!_, `\\__q)K/K#~
  #bd /  `~~~~~~~*@*+~P#@|| Tf \\==q==+*****T~/|##b
  VN(5N\\__,       |.__b*!`~=d_d__|        |_bW5t5
   b\\TqNLL(T5T5T5T5\\=_,        `~T855T5T5X#N5\\*/
   |\\L\\\\T5NqNqNLLLLLXK=,     .(bLLGqN5T\\L)/' |
   |  Y+LL\\\\\\\\\\\\\\5T\r~~Vt5\\\\LL+=f~'   :'
   \\     `~~\\=+\\LLLLLLLLLLLb .+=+=~~'         :'
    t-\_                   !_/            _=.='
     \\ ~~==\\__             '         /==T/='
       ~~===__,~~~~~\\========/~~~~~ .__=~'
              `~~======\\____======~~'
              
    Memory Package Manager - What delicious!
    Version 6.0.0.3106 - by Holy Selbrights
    
    (c) Copyright 2023~2025 BL.BlueLighting
    (c) Copyright 2025~now Holy Selbrights
    
    This program can redistribute under MIT License.
    """)


_mpm_manager = None
_mpm_controller: MPMController | None = None


def _mpm_get_controller() -> MPMController:
    global _mpm_manager, _mpm_controller
    if _mpm_controller is None:
        _mpm_manager = PerhapsMPMManager.from_mpm(MPM_PACKAGES, MPM_REGISTRYS)
        _mpm_controller = MPMController(_mpm_manager, name="mpm")
    return _mpm_controller


@register("mpm")
def mpm(args: Arguments):
    if not save.gotattr("MPMActivated") or not save.MPMActivated:
        return COMMAND_NOT_FOUND
    return _mpm_get_controller().run([str(arg) for arg in args])


@register("reboot")
def reboot(args: Arguments):
    save.NeedReboot = False
    saveit()
    py = sys.executable
    os.execv(py, (py, *sys.argv))
    # what great reboot way!
    return

init()
mkachieve("Chapter 1: Repent, then Recreate", "游玩 Chapter 1。", "chapter1_played")
main_while()
