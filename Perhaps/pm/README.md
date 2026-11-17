# 基于 Perhaps PM 写自己的包管理器

先说实话：`Perhaps/pm` 不是 pacman 的 Python 复刻版。它更像一套已经接好线的零件：包模型、仓库源、依赖解析、事务、回滚、持久化、CLI、钩子都在，你可以直接拿来用，也可以只取其中几块。

如果你准备在 HumanOS 里做一个 Memory Package Manager、模型/工具仓库、剧情 DLC 管理器，或者只是想要一个能装、卸、查的壳，这份文档就是给你（以及半年后的我自己）看的。

---

## 1. 先跑起来

最省事的方式是用虚拟文件系统，和游戏里的 `/usr`、`/var/lib/pm` 共用一个世界：

```python
from Perhaps import fileutil
from Perhaps.pm import default_manager

fileutil.InitBaseFileSystem()      # 如果你已经初始化过，就别重复调
pm = default_manager()             # 默认读写 /var/lib/pm，并自动 load
pm.register_commands("mpm")        # 把 mpm 命令注册进 Perhaps shell
```

`default_manager()` 默认使用 `VirtualFSBackend` + `VirtualFSStore`。它不会在 import 时注册任何命令，也不会偷偷启动什么东西；命令注册永远是你显式做的。

如果你只想做工具、测试或不想碰游戏文件系统，用内存版：

```python
from Perhaps.pm import PackageManager, MemoryBackend, MemoryStore

pm = PackageManager(backend=MemoryBackend(), store=MemoryStore())
```

注意：`PackageManager(backend=MemoryBackend())` 不传 `store` 时，构造器会自动配 `MemoryStore`；但 `default_manager(backend=MemoryBackend())` 默认还是 `VirtualFSStore`，因为它是“默认管理器”工厂。想完全脱离虚拟 FS，就用上面那种显式构造。

---

## 2. 一个包到底长什么样

最小包定义：

```python
from Perhaps.pm import Package

demo = Package.from_dict({
    "id": "demo",
    "name": "demo",
    "version": "1.0-1",
    "author": "BL.BlueLighting",
    "date": "2026/11/17",
    "description": "一个演示包",
    "depends": ["libdemo>=1.0"],
    "optdepends": ["demo-gui: 图形界面"],
    "conflicts": ["old-demo"],
    "provides": ["demo-api=1.0"],
    "replaces": ["demo-legacy"],
    "groups": ["utils"],
    "files": [
        {
            "path": "/usr/bin/demo",
            "content": "#!/bin/demo\nprint('demo')",
            "permissions": ["Readable", "Runnable"],
            "owner": "root",
        },
        {
            "path": "/usr/share/demo/data",
            "kind": "directory",
        },
        {
            "path": "/usr/lib/demo.so",
            "content": "<BINARY>",
        },
    ],
    "commands": ["demo"],
    "handlers": {"demo": lambda args: 0},
})
```

字段不用全填。真正常用的是：

- `id`：包的唯一键，也是 `install(["id"])` 用的名字。
- `name`：显示名；`id` 和 `name` 都可以被依赖/查询。
- `version`：pacman 风格 `[epoch:]version[-release]`，例如 `1.0-1`、`2:1.3-2`。
- `depends` / `optdepends`：依赖和可选依赖；`optdepends` 支持 `"foo: 说明"`。
- `conflicts` / `replaces` / `provides`：版本约束也支持，例如 `"old-demo<2.0"`。
- `files`：这个包实际写入虚拟 FS 的内容。
- `commands`：声明“这个包会提供哪些命令”，只用于查询、展示和 MPM 兼容层。
- `handlers`：真正的命令函数，`{命令名: callable}`；事务安装时只会注册这里的东西。

这里有个很容易踩的点：**`commands` 和 `handlers` 不是一回事。**

你在 `Story/chapters/first.py` 里看到的 `models`、`systemutil` 这类名字，很多只是剧情里的字符串，框架里根本没有对应命令。`Perhaps/pm` 不会因为 `commands` 里写了一个不存在的名字就报错，也不会替你伪造一个命令。要么在 `handlers` 里给真函数，要么就让它只作为元数据存在。

`Package.from_dict` 兼容 MPM 的大写字段（`Name`、`Version`、`Author`、`Date`），所以从旧 `MPMManager` 的字典搬过来几乎不用改。

`files[].kind` 支持 `file`、`directory`、`symlink`。虚拟 FS 没有真正的符号链接，`symlink` 会写成一个带 `<PM_SYMLINK>` 标记的文件；如果你的世界观需要真链接，就在自己的 backend 里实现。

---

## 3. 仓库和源

一个仓库本质上就是 `Package` 的集合：

```python
from Perhaps.pm import Repository

repo = Repository("core", {demo.id: demo}, priority=10, server="brainet://...")
pm.repositories.add(repo)
```

真实接入时更推荐用源：

```python
from Perhaps.pm import DictSource, JsonTextSource, VirtualFSJsonSource

pm.add_source("core", DictSource("core", {"packages": [...]}), priority=10)

# 仓库 JSON 放在虚拟 FS 里
pm.add_source("brainet", VirtualFSJsonSource("brainet", "/var/lib/pm/remote/core.json"))

# 直接从 JSON 字符串
pm.add_source("extra", JsonTextSource("extra", json_text))
```

`add_source()` 默认会立刻 `load()` 一次并持久化仓库缓存；`refresh()` 可以手动重拉。源只要实现 `PackageSource.load() -> Repository` 就能接进来；`refresh()` 默认就是再 `load()` 一次，网络源可以覆盖它做真正的下载/缓存。

仓库 JSON 支持两种形状，随便挑：

```json
{
  "packages": [
    {"id": "foo", "name": "foo", "version": "1.0-1", "files": []}
  ]
}
```

或者直接一个 `包 id -> 包数据` 的映射。

`RepositorySet` 会自动按“仓库优先级 + 版本”挑候选；`provides` 也能参与匹配。你不需要自己写“从哪个仓库装”的逻辑，除非你想换策略。

---

## 4. 依赖、事务和回滚

```python
result = pm.install(["demo"])
if not result.success:
    for problem in result.problems:
        print(problem)
```

安装不是“直接写文件”。流程是：

1. `Resolver` 根据目标算出一份计划：先装哪些依赖、哪些要升级/替换、哪些旧包要移除，以及有没有冲突。
2. `Transaction` 按计划执行：先移除，再按依赖顺序安装。
3. 每个文件写之前检查归属；如果路径已被别的包占用，抛 `FileConflict`。
4. 任何一步抛异常，事务会拿文件快照、命令快照和 DB 快照回滚。

`TransactionResult` 里会告诉你 `success`、`installed`、`removed`、`problems`、`rolled_back`。别只看返回值是 `True`/`False`，出问题时 `problems` 通常比“失败”两个字有用。

升级和卸载：

```python
pm.upgrade()              # 升所有有更新候选的包
pm.remove(["demo"])       # 普通卸载
pm.remove(["base"], cascade=True)   # 删掉依赖它的包
pm.remove(["app"], recursive=True)  # 顺手清掉没人要的依赖
```

文件冲突策略：

- 默认：要装的路径已被本地 DB 里的其他包拥有 → 报错；路径存在于 FS 但没有主人 → 也报错（更接近 pacman）。
- 如果你做的系统允许包覆盖“系统自带文件”，构造时传 `allow_unowned_overwrite=True`，或者 `Transaction(...)` 这一层自己控制。

钩子：

```python
from Perhaps.pm import CallbackHook, PRE_INSTALL, POST_INSTALL

def log(ctx):
    print("installing", ctx.package.id if ctx.package else "?")

pm.hooks.add(CallbackHook("log", log, events=(PRE_INSTALL, POST_INSTALL)))
```

在 hook 里抛异常就会中止事务并触发回滚。适合做权限检查、剧情锁、审计日志；别在 hook 里偷偷改无关文件，回滚只负责事务碰过的路径。

如果你要更复杂的策略，直接继承：

```python
from Perhaps.pm import Resolver

class MyResolver(Resolver):
    def resolve_install(self, targets, **kwargs):
        plan = super().resolve_install(targets, **kwargs)
        # 比如禁止某类包、追加自己的冲突检查
        return plan

pm = PackageManager(..., resolver_class=MyResolver)
```

`PackageManager` 还接受 `transaction_class=`，所以事务层也能换。

---

## 5. 持久化

```python
pm.save()     # 本地 DB + 仓库缓存
pm.load()     # 反过来
```

默认路径是虚拟 FS 的 `/var/lib/pm`：

- `local.json`：已安装包、文件归属、命令归属
- `sync/<仓库名>.json`：同步下来的仓库缓存

不用虚拟 FS 时，可以换存储：

```python
from Perhaps.pm import HostJsonStore, MemoryStore

pm = PackageManager(backend=MemoryBackend(), store=MemoryStore())
# 或者
pm = PackageManager(backend=VirtualFSBackend(), store=HostJsonStore("pm-data"))
```

`PackageStore` 只有五个方法：`load_local`、`save_local`、`repository_names`、`load_repository`、`save_repository`。想接 JSON/TOML/数据库都行。

**一个必须知道的限制：** `Package.handlers` 是 Python callable，不会写进 JSON。仓库缓存重新加载后，包元数据和文件还在，但 `handlers` 没了。所以命令型包要这样做：

- 要么在启动时从源码/注册表重新构建仓库，再 install；
- 要么在运行时用 `pm.add_package(package)` 把带 handlers 的包塞回来；
- 要么把命令注册交给自己的 backend，而不是依赖持久化。

别指望 `load()` 之后一个纯 JSON 包还能自动拥有命令函数。

---

## 6. 接到 shell / CLI

```python
pm.register_commands("mpm")              # 注册，已存在会报错
pm.register_commands("mpm", override=True)  # 明确覆盖
```

已经实现的 pacman 风格操作：

```text
-Q  --query      查询已安装
-S  --sync       同步/安装/升级
-R  --remove     卸载
-U  --upgrade    从本地包文件安装
-T  --deptest    检查依赖
-D  --database   修改 reason / 自检
-F  --files      文件数据库查询
```

常用组合：

```text
mpm -S demo
mpm -Syu
mpm -Q
mpm -Qi demo
mpm -Ql demo
mpm -Qo /usr/bin/demo
mpm -Qs "demo"
mpm -Ss demo
mpm -Rns demo
mpm -T demo
mpm -D --asdeps demo
mpm -F -o /usr/bin/demo
mpm -U ./demo.json
```

自定义操作：

```python
from Perhaps.pm.cli import register_pm_command, CliRequest

ctrl = register_pm_command(pm, "mpm")

def export_handler(request: CliRequest) -> int:
    # request.action / request.options / request.targets
    print("custom -X", request.targets)
    return 0

ctrl.add_action("X", export_handler)
# 然后 mpm -X ...
```

自定义操作只支持单字母短操作（`-X`），因为 pacman 本身就是这个语法；长操作想加就改自己的 parser 或直接写一层自己的 CLI。CLI 只是薄壳，`PackageManager` 才是本体。

---

## 7. MPM 兼容层

如果你要做的是剧情里那个 MPM 的替代品：

```python
from Perhaps.pm import MPMManager

mpm = MPMManager.from_mpm(packages, registrys)
mpm.CheckRegistry()             # 默认宽松
mpm.check_registry()            # 返回缺失的命令名列表
mpm.CheckRegistry(strict=True)  # 只有这时才抛 UnregisteredCommand
```

`packages` 和 `registrys` 的属性形状跟旧 `MPMManager` 基本一致，方便剧情代码慢慢迁。

再次强调：**旧 MPM 的 registry 里那些 `models`、`systemutil`、`fakecmd` 是剧情演出，不是一定要存在的命令。** 默认宽松检查就是为了不拦这些名字；真正要注册命令，还是看 `Package.handlers`。

---

## 8. 如果你要做一个“新的包管理器”

不要一上来就重写全部。按这个顺序改，最省事：

1. **先换源**：写一个 `PackageSource`，把你们的包目录/数据库/远程 API 变成 `Repository`。
2. **再换存储**：如果 `/var/lib/pm` 不合适，写一个 `PackageStore`。
3. **再换策略**：冲突、版本、允许降级这些，继承 `Resolver` 覆盖对应方法。
4. **最后换执行**：只有确实需要新的文件系统/权限模型时，才写 `PackageBackend` 或 `Transaction`。

一个自定义管理器的骨架：

```python
from Perhaps.pm import (
    PackageManager, MemoryBackend, MemoryStore,
    PackageSource, Repository, Package,
)

class ModelSource(PackageSource):
    def load(self) -> Repository:
        # 从自己的剧情/模型目录里读出包
        return Repository(self.name, {
            "deepseek-v4-flash": Package.from_dict({
                "id": "deepseek-v4-flash",
                "name": "deepseek-v4-flash",
                "version": "4.0.0",
                "files": [
                    {"path": "/home/perhaps/models/v4/config.toml",
                     "content": ["[model]", "name=deepseek-v4-flash"]},
                ],
            }),
        })

class ModelManager(PackageManager):
    def install_model(self, model_id: str):
        return self.install([model_id])

pm = ModelManager(backend=MemoryBackend(), store=MemoryStore())
pm.add_source("models", ModelSource("models"), priority=100)
pm.register_commands("models")
```

你也可以把 `PackageManager` 继续往上包：它不关心“包”到底是软件、模型、剧情章节还是技能卡，只要有 id、version、files、depends 就能跑。

---

## 9. 一些真实会踩的坑

- **`commands` 只是声明。** 真正注册的是 `handlers`。`commands` 用来查询和 MPM 兼容，不要靠它“自动出现命令”。
- **handler 不会持久化。** 详见第 5 节。
- **默认 `default_manager()` 会吞掉 load 错误。** 它想让你在干净世界也能启动；如果你在调试存档，传 `strict=True`，别让错误静默消失。
- **未托管文件默认拒绝覆盖。** 这是有意的 pacman 行为；如果你的包要盖系统文件，显式 `allow_unowned_overwrite=True`，别把开关当默认。
- **虚拟 FS 路径要绝对。** 包文件路径会被规范化成 `/...`；相对路径虽然会被补成绝对，但别依赖这个行为。
- **`PackageManager.save()` 不会自动被所有外部修改触发。** 直接改 `pm.database` 之后记得自己 `save()`；`install/remove/upgrade` 默认会存。
- **一个进程里一般只用一个 manager 后端。** `VirtualFSBackend` 和 `MemoryBackend` 各自有命令/文件状态，混用两个 manager 容易互相看不见。
- **注册命令可能撞名。** 用 `register_commands(..., override=True)` 前想清楚；CLI 注册名和业务命令名也一样。
- **事务回滚不是魔法。** 它只恢复事务碰过的文件路径、命令快照和本地 DB；hook 里的外部副作用（发网络请求、写别的文件）它管不了。
- **版本比较是“够用”级别。** 普通数字/字母版本没问题；如果你们的版本体系很怪，继承 `Resolver` 或在包数据里统一格式，别在业务层到处手写字符串比较。

---

## 10. 文件地图

```text
Perhaps/pm/
    __init__.py      导出面、default_manager()
    package.py       Package / PackageFile / Dependency
    version.py       版本解析与比较
    database.py      本地 DB / Repository / RepositorySet
    resolver.py      依赖、冲突、升级/移除计划
    transaction.py   安装/卸载、快照、回滚
    hooks.py         pre/post hooks
    backends.py      VirtualFSBackend / MemoryBackend
    store.py         VirtualFSStore / MemoryStore / HostJsonStore
    sources.py       Dict / JSON / VirtualFS / Host / Callback source
    manager.py       PackageManager 总装
    compat.py        MPMManager 剧情兼容层
    cli.py           pacman 风格 CLI
    errors.py        异常树
```

---

## 11. 最小验收清单

每次改完，我至少会跑一遍这些：

1. `from Perhaps.pm import *` 能导入，且没有自动注册任何命令。
2. 一个只有文件、没有依赖的包能安装、文件能从虚拟 FS 读出来、卸载后文件消失。
3. 一个有依赖的包会先把依赖装进来，`required_by`/reason 正确。
4. 两个包抢同一个文件时，后一个失败且事务回滚，前一个文件没丢。
5. `pm.save(); pm.load()` 后本地 DB 和仓库缓存还在。
6. `mpm -S` / `-Q` / `-Qo` / `-Rns` / `-U` 至少各跑一次。
7. 在 hook 里抛个异常，确认 `rolled_back=True` 且文件/DB 恢复。

这七条过了，基本就不会在剧情里突然把一个存档写坏。
