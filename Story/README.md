<div align="center">
    <img src="./README.logo.png" style="width: 100px;">
    <h1>doas -su mylife.root</h1>
    <i>An adventure game, about a Silenter and an AI.</i>
    <br/>
    <div style="margin-top: 12px">
        <img src="https://img.shields.io/badge/Using-Python-blue">
        <img src="https://img.shields.io/badge/Version-v1.0.1-yellow">
    </div>
    (By BL.BlueLighting)
</div>

## 简述
- Chapter: Pre = Unexpected Corruptions: 未知差错
- Chapter: 1 = Repent, then Recreate: 回头，重建。
- Chapter: 2 = ???? ????

正在逐步迁移剧情，重置剧情等。

## 运行

```bash
# 在仓库根目录
pip install -r requirements.txt
python -m Story
```

`Story/__main__.py` 会自动切换到 `Story/` 目录并补齐 `sys.path`；菜单需要真实 TTY（终端交互）。

## 技术架构 / Technology Arch.

doas -su mylife.root 基于 Python 和 Perhaps Framework.