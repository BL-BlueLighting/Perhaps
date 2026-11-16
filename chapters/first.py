"""
doas -su mylife.root
Chapter: 1 (first)

First chapter, Repent, then Recreate
What adventure more?
"""

from framework import *
from framework.fastcmdutil import *
from framework.fileutil import *
from framework.manAI import *

def MakeFilesAndDirectories():
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
    ])
    #endregion

    #region Stories

    #endregion

    #region Saving
    fs_writesave(fs)
    saveit()
    #endregion

fs_initialize(fs)

@aiReg("1000")
def _ ():
    print("(-_-) zzZ")
    print("(-_+) 干嘛... 谁啊？")
    print("(!_!) Silenter! 是你诶")
    print("[cyan](^_^)[/cyan] I'M BACK!")
    print()


init()
mkachieve("Chapter 1: Repent, then Recreate", "游玩 Chapter 1。", "chapter1_played")
main_while()