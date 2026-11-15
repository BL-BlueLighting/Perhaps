# doas -su mylife.root
## FRAMEWORK Inject points

### 常识
- 当 Inject 函数返回 `tuple` 或 `list` 时，`run_injects` 自动检查 (在可返回处使用 `LISTRET` 表明) 其的第一项，判断是否需要执行后方（第二项）中提供的函数。
- **注意：** 当 `ret[0]` (即函数返回值) 为 -1 时，`run_injects` 会执行 `ret[1]`
- Inject 分为 `Patcher`s 和 `Inject`s，使用同一个函数定义，几乎没有区别。但 `Patcher` 会将返回的值直接替换为 `Patcher` 函数返回的值。

### `before_setup`
注入点为 `base.py:L227`，在 setup 函数开始时执行。

参数：`None`

可返回：
`LISTRET(-1,Callable)` 来执行 Callable.

### `before_load`
注入点为 `base.py:L293`，在显示主程序加载日志前执行。

参数：`None`

可返回：
- `LISTRET(-1,Callable)` 来执行 Callable.

### `before_shell_pre`
注入点为 `base.py:L315`，在显示 Shell 提示执行。

参数：`None`

可返回：
- `LISTRET(-1,Callable)` 来执行 Callable.

### `while_head`
注入点为 `base.py:L347`，在主循环 while 头部执行。

参数：`None`

可返回：`None`

### `userinfo`
注入点为 `base.py:L348`，在 `while_head` 后方执行。

参数：
- `username: str`
- `password_hash: str`
- `hostname: str`
- `salt: str`
*(`password_hash` 使用 md5, `salt` 为 6 位数字。)*

可返回：`None`

### `getdir`
注入点为 `base.py:L349`，在 `userinfo` 后方执行。

参数：
- `directory: str`
*(`directory` 代表主循环中的 `directory` 变量的值)*

可返回：`None`

### `after_enter`
注入点为 `base.py:L356`，在用户输入命令敲下回车后执行，此时暂未开始命令解析。

参数：
- `input: str`
*(`input` 为用户输入)*

可返回：
- `LISTRET(-1,Callable)` 来执行 Callable，同时**会取消命令处理**。

### `before_execute`
注入点为 `base.py:L364`，在用户输入命令敲下回车后执行，此时命令解析完成，开始执行。

参数：
- `cmd: Command`
*(`cmd` 为 `Command` 类，详情参考其定义)*

可返回：`None`

### `after_execute`
注入点为 `base.py:L366`，在用户输入命令敲下回车后执行，此时命令执行完毕。

参数：
- `cmd: Command`
- `returns: Arguments`
*(`cmd` 为 `Command` 类，详情参考其定义; `returns` 为 `Arguments` 类，为命令执行结果。)*

### `prompt_patcher` (`PATCHER`)
修补点为 `base.py:L360`，在 `getdir` (`INJECT`) 执行后开始修补。

参数：
- `prompt: str`
- `userinfo_tuple: tuple[str, str, str, str]`
- `directory: str`
*(`prompt` 为旧 `prompt`，`userinfo_tuple` 和 `userinfo (PATCHER)` 传参一样。)*

返回：
- `str`

此时将应用修补。

### `dir_patcher` (`PATCHER`)
修补点为 `base.py:L403`, 在 `prompt_patcher` PATCH 前开始修补。

参数：
- `directory: str`

返回：
- `str`

此时将应用修补。

## FRAMEWORK Chapter develop navigator

### register command
register 使用 `base.py:register`，是一个 decorator。

decorator 传参为 command 的名称，即调用名。

示例：
```python
from framework.base import *

@register("helloWorld")
def _ (args: Arguments):
    print("Hello, World!")
```

注意：函数的参数无论要不要，都要提供 args 作为参数空位。

### arg tunnel
drom 框架是原生支持 tunnel (管道) 的，在函数获得 `args` 之后使用 `args["TUNNEL"]` 即可获得上级管道输出。

示例：
```python
from framework.base import *

@register("tunnelecho")
def _ (args: Arguments):
    return args[0]

@register("echo")
def _ (args: Arguments):
    print(args["TUNNEL"])
```