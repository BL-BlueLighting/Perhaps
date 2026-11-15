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
- Chapter: Pre
- Chapter: 1
- Chapter: 2

正在逐步迁移剧情，重置剧情等。

## 技术架构 / Technology Arch.

doas -su mylife.root 基于 Python 和 Rich.
```
Framework --------------------
             rich            |
            shlex            |
base.py  -----|              |
    |- Base Shell            |
    |- Command Analzying     | 
    |- Inject Points         |
    |- I/O Control           |
    |- Flags Controlling     |
    -------------|           |
                 |           |
saving.py -------|           |
    |- Base Saving System    |
            -----|           |
                 |           |
fastutil.py -----|           |
    |- Saving system extend  |
    |- Quick tools           |
------------------------------
```