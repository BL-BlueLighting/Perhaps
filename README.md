<div align="center">
    <img src="./README.Logo.png" style="width: 640px;">
    <h1>Perhaps Framework</h1>
    <i>A virtual system game / terminal emulator framework</i>
    <br/>
    <div style="margin-top: 12px">
        <img src="https://img.shields.io/badge/Using-Python-blue">
        <img src="https://img.shields.io/badge/Version-v1.0.1-yellow">
    </div>
    (By BL.BlueLighting)
</div>

## 如何使用？
Perhaps Framework 使用方法极其简单（Python 3.10+，依赖见 `requirements.txt`）：

将本项目的 Perhaps 文件夹挪到您项目的文件夹下，随后进行测试：

```python
import Perhaps as fm
import Perhaps.fileutil as fsu
fs = fsu.InitBaseFileSystem()

@register("helloworld")
def helloWorld(args: Arguments):
    print("Hello World!")
    print(args[0])

fm.init()
fm.main_while()
```

即可获得一个开箱即用的 Shell 环境。

具体开发文档，参见 [DEVELOPMENT.md](DEVELOPMENT.md)。

说明：
- 导入 `Perhaps` 不再需要 `texts/initpre.txt`；`init()` 在文件缺失时会跳过开机文本。
- 首次运行如果缺少 `flags/userinfo`，会自动进入 `setup()` 设置账号；设置完成后会创建 `flags/login_required`，之后启动需要密码。
- 老存档没有 `flags/login_required` 时保持免密进入。
- `flags/` 下的文件名会做路径校验，不能包含 `/`、`..` 等。

## 提示
如果您在寻找 doas -su mylife.root 游戏，参见本项目目录下 `Story` 文件夹，或者点此->[Story/README.md](Story/README.md)。
