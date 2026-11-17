# doas -su mylife.root
## FRAMEWORK Inject / Patcher API

### 常识

- 注入点用 `@inject("name")` 注册，可以注册**多个**回调；按注册顺序依次执行。
- 注入回调只允许返回：
  - `None`：无影响，框架继续默认行为；
  - `Handled()`：表示"这次由我处理"，跳过框架默认行为；
  - `Handled(callback)`：同上，并立即调用 `callback()`；
  - `Cancel()`：仅用于 `after_enter`，表示取消当前输入的命令解析。
  - 返回其它值会抛 `TypeError`，不再使用旧的 `(-1, Callable)` 魔术列表。
- 补丁点用 `@patcher("name")` 注册，与 Inject 分表，互不覆盖；多个补丁按注册顺序链式执行：
  - 回调签名 `func(current_value, *args) -> new_value | None`；
  - 返回 `None` 表示不修改，返回其它值会替换为下一次链的输入。
- `run_injects()` 返回 `InjectReport`（`values` / `executed` / `handled` / `cancelled`），不再靠返回值类型猜语义。

### 注入点

| 注入点 | 调用时机 | 参数 |
| --- | --- | --- |
| `before_setup` | `setup()` 开始时 | 无 |
| `before_load` | `init()` 打印开机文本前 | 无 |
| `before_shell_pre` | `init()` 打印欢迎信息前 | 无 |
| `while_head` | 主循环每轮开头 | 无 |
| `userinfo` | 主循环每轮，带账号信息 | `username, password_hash, hostname, salt` |
| `getdir` | 主循环每轮，带当前目录 | `directory: str` |
| `after_enter` | 用户敲下回车后，命令解析前 | `input: str` |
| `before_execute` | 命令解析完成、执行前 | `cmd: Command` |
| `after_execute` | 命令执行后 | `cmd: Command`, `returns: list[Arguments]` |
| `before_quit` | 主循环正常退出（`exit` / Ctrl-D / Ctrl-C）前 | 无 |

`before_setup` / `before_load` / `before_shell_pre` 返回 `Handled()` 可跳过框架默认逻辑；
`after_enter` 返回 `Cancel()` 会跳过命令解析。

### 补丁点

| 补丁点 | 调用时机 | 参数 | 返回 |
| --- | --- | --- | --- |
| `prompt_patcher` | 主循环显示提示符前 | `prompt: str`, `userinfo: tuple[str,str,str,str]`, `directory: str` | `str` 或 `None` |
| `directory_patcher` | `getdir` 注入后、显示提示符前 | `directory: str` | `str` 或 `None` |

示例：

```python
from Perhaps import *


@patcher("prompt_patcher")
def prompt(prompt: str, userinfo: tuple[str, str, str, str], directory: str) -> str:
    # 用户输入可能包含 rich 标记，拼接时务必 escape
    return f"[green]{escape(userinfo[0])}[/green]:{escape(directory)}[cyan]$[/cyan] "


@inject("after_enter")
def skip_debug(input: str):
    if input == "debug":
        print("debug command ignored")
        return Cancel()
    return None
```

## FRAMEWORK Chapter develop navigator

### register command

`register` 是装饰器，参数为命令的调用名。同名命令默认会抛 `ValueError`；如确实要覆盖（例如 Story 覆盖框架自带的 `ls`），传 `override=True`。

```python
from Perhaps import *


@register("helloWorld")
def _(args: Arguments):
    print("Hello, World!")
```

函数必须接收一个 `args: Arguments` 参数。用户名、密码等敏感输入不要直接拼进 rich 输出，使用 `escape()`。

### arg tunnel

`drom` 原生支持管道。管道下游通过 `args["TUNNEL"]` 拿到上游命令的返回值（`Arguments` 或 `None`），下游自己的参数不会被管道污染。

```python
from Perhaps import *


@register("tunnelecho")
def _(args: Arguments):
    return args[0]


@register("echo")
def _(args: Arguments):
    upstream = args["TUNNEL"]
    print(upstream[0] if upstream is not None else "")
```

`|` 必须能被 shell 解析：带引号的 `"|"` 会作为普通参数；多级管道（`a | b | c`）也支持。

`Arguments` 缺少位置参数时抛 `MissingArgument`（`IndexError` 子类），主循环会显示"arguments not enough"，不会再吞掉命令内部的真实 `IndexError`。

### 会话与账号

- `setup()` 会把 `scrypt` 密码哈希、随机盐、用户名、主机名写入 `flags/userinfo`，创建 `flags/login_required`，然后提示重启并退出进程；首次启动必须重新运行游戏。
- `read_userinfo()` 是纯读取函数，不会触发 setup；`init()`、`main_while()` 和 `InitBaseFileSystem()` 会先调用 `ensure_initialized()`，缺账号时自动进入 setup。
- 主循环在 `flags/login_required` 存在时调用 `base.askpass()` 要求密码；老存档没有该 flag 时保持直接进入。
- `base.askpass(userinfo=None, requirer="sudo", attempts=3, prompt=None)` 是底层密码询问/校验函数，`base.login` 是它的别名。
- `fastutil.login(userinfo=None, ifs=None, requirer="sudo", max_attempts=5, prompt=None, lock_duration=60)` 是完整登录后端，传入 `ifs` 时使用虚拟文件系统 `/etc/faillocks/faillock` 做锁定；`fastutil.askpass(userinfo=None, ifs=None)` 是省略参数的简化包装；`fastutil.passwd_checker` 是 `login` 的兼容别名。
- 登录提示不再包含多余的 `f` 前缀；`requirer=""` / `requirer="[No Requirer]"` 输出 `<username>'s password: `。

### manAI 返回值

`aiReg` 注册的回调返回：

- `None`：什么都不做；
- `str`：视为新的 `storyWhere`，推进剧情；
- `[storyWhere, text]`：推进到 `storyWhere` 并显示一行 `! text !`。

其它类型会抛 `TypeError`。

### 存档 / 虚拟文件系统

- `Perhaps/config.py` 提供存档流程开关（默认全开）：`SAVE_PATCH_ENABLED`、`AUTO_LOAD_ON_START`、`AUTO_LOAD_ON_SLOT_SELECT`、`AUTO_SAVE_ON_EXIT`、`DEFAULT_SLOT`。
- 默认行为：导入 fastutil 时加载当前槽位；`svslot(n)` 选中后立即读取槽位 `n`；主循环正常退出时通过 `before_quit` 自动保存当前完整 `save.statuses`（含 `storyWhere`、别名等）。
- 需要自己控制存档流程时，可在启动前修改 `Perhaps.config` 或注册自己的 `before_quit` 注入；`svsslot` / `svoslot` / `svdslot` 内部使用 `svslot(..., load=False)`，不会在写档前误读旧档。
- `Save` 的 `load/save` 只接受相对路径，拒绝 `..`/绝对路径；写入使用临时文件 + `os.replace`，不会产生半截 JSON。
- `fs_writesave(fs)` 保存的是 JSON，`fs_fromsave()` 返回重建后的 `FileSystem`，`fs_initialize(fs)` 会真正把存档加载进传入的文件系统并切换全局文件系统。
- `FileSystem.DumpToFile()` / `LoadFromFile()` 使用带版本号的 JSON，正文里出现 `;`、`]`、`}`、逗号、数字串都能正确往返。
- 权限统一由 `ProtectedList` / `_require()` 检查：读需要 `Readable`，写需要 `Writable`，列目录需要可列；`Access_Denied` 优先拒绝。系统内部可显式传 `access="system"`。
- `CreateFile` / `CreateDirectory` / `WriteFile` 支持 `target=` 指定文件系统，`access="system"` 绕过用户权限；`file_owner` 可以是字符串。
- `InitBaseFileSystem()` 可重复调用（会重置全局文件系统）；用户名含 `/` 等分隔符会被拒绝。

## 环境

- Python 3.10+
- `pip install -r requirements.txt`
- 从仓库根目录运行 `python -m Story`；`Story/__main__.py` 会自动切到 `Story/` 目录并补齐 `sys.path`，因此不再需要手动设置 `PYTHONPATH`。
