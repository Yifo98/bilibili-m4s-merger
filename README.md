# B站M4S视频合并工具

<div align="center">

<img src="logo.png" width="200" alt="Logo">

**一键合并B站下载的M4S视频和音频文件**

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Upload-success.svg)](https://github.com)

</div>

---

## 简介

这是一个专门用于合并B站（Bilibili）下载视频的工具。当你使用IDM或其他工具下载B站视频时，会得到分离的`.m4s`视频文件和音频文件。本工具可以**自动识别、智能配对、一键合并**这些文件，生成完整的MP4视频。

## 功能特点

- **自动识别** - 自动扫描目录中的所有m4s文件，智能区分视频/音频
- **智能配对** - 基于时长和大小自动匹配对应的视频和音频文件
- **批量处理** - 一次性处理多组视频，无需手动逐个合并
- **自动清理** - 合并成功后自动删除源m4s文件（可配置）
- **零配置** - 无需修改配置，双击即可使用
- **简洁输出** - 清晰的进度显示，无冗余信息

## 适用场景

- 使用IDM下载B站视频后，需要合并视频和音频
- 使用其他下载工具得到的分离m4s文件
- 批量处理多个B站视频

## 环境要求

- Windows 7/10/11
- Python 3.6 或更高版本
- [FFmpeg](https://ffmpeg.org/download.html)（需要添加到系统PATH）

## 安装

### 1. 安装 FFmpeg

下载 [FFmpeg](https://ffmpeg.org/download.html) 并解压，将`bin`目录添加到系统环境变量PATH中。

验证安装：
```bash
ffmpeg -version
```

### 2. 下载本工具

**方式一：直接下载文件**

访问 [仓库首页](https://github.com/Yifo98/bilibili-m4s-merger)，下载以下两个文件：
- `合并B站视频.py`
- `合并B站视频.bat`

**方式二：克隆仓库**
```bash
git clone https://github.com/Yifo98/bilibili-m4s-merger.git
```

## 使用方法

### 方式一：双击运行（推荐）

1. 将 `合并B站视频.bat` 和 `合并B站视频.py` 复制到m4s文件所在目录
2. 双击 `合并B站视频.bat`
3. 等待合并完成

### 方式二：命令行运行

```bash
cd "你的m4s文件目录"
python 合并B站视频.py
```

## 输出示例

```
==================================================
      B站M4S视频音频自动合并工具
==================================================

工作目录: I:\B站视频下载

扫描到 6 个m4s文件...
  [音频] XXXXXXXXXXX_哔哩哔哩_bilibili.m4s (12.1MB)
  [视频] XXXXXXXXXXX_哔哩哔哩_bilibili_2.m4s (102.5MB, 4096x2048)
  [视频] XXXXXXXXXXX_哔哩哔哩_bilibili_2_2.m4s (109.4MB, 4096x2048)
  [音频] XXXXXXXXXXX_哔哩哔哩_bilibili_2_3.m4s (6.3MB)
  [音频] XXXXXXXXXXX_哔哩哔哩_bilibili_3.m4s (7.3MB)
  [视频] XXXXXXXXXXX_哔哩哔哩_bilibili_4.m4s (70.1MB, 4096x2048)

[匹配阶段] 正在匹配视频和音频...
找到 3 组匹配

[合并阶段] 正在合并文件...
[1/3] 合并: XXXXXXXXXXX_哔哩哔哩.mp4
         视频: XXXXXXXXXXX_哔哩哔哩_bilibili_2.m4s (4096x2048)
         音频: XXXXXXXXXXX_哔哩哔哩_bilibili_2_2.m4s
         [成功] XXXXXXXXXXX_哔哩哔哩.mp4
         已删除: XXXXXXXXXXX_哔哩哔哩_bilibili_2.m4s
         已删除: XXXXXXXXXXX_哔哩哔哩_bilibili_2_2.m4s

[2/3] 合并: 董北：XXXXXXXXXXX_哔哩哔哩_1.mp4
         视频: XXXXXXXXXXX_哔哩哔哩_bilibili.m4s (4096x2048)
         音频: XXXXXXXXXXX_哔哩哔哩_bilibili.m4s
         [成功] XXXXXXXXXXX_哔哩哔哩_1.mp4
         已删除: XXXXXXXXXXX_哔哩哔哩_bilibili.m4s
         已删除: XXXXXXXXXXX_哔哩哔哩_bilibili.m4s

[3/3] 合并: XXXXXXXXXXX_哔哩哔哩_2.mp4
         视频: XXXXXXXXXXX_哔哩哔哩_bilibili_4.m4s (4096x2048)
         音频: XXXXXXXXXXX_哔哩哔哩_bilibili_2_3.m4s
         [成功] XXXXXXXXXXX_哔哩哔哩_2.mp4
         已删除: XXXXXXXXXXX_哔哩哔哩_bilibili_4.m4s
         已删除: XXXXXXXXXXX_哔哩哔哩_bilibili_2_3.m4s

==================================================
合并完成! 成功: 3/3
已删除 6 个m4s源文件
==================================================
```

## 配置选项

打开 `合并B站视频.py`，可以修改以下配置：

```python
DELETE_SOURCE_AFTER_MERGE = True  # 合并成功后是否删除源文件
FFMPEG_PATH = "ffmpeg"            # FFmpeg路径（如果在PATH中可直接写"ffmpeg"）
```

## 文件说明

```
bilibili-m4s-merger/
├── 合并B站视频.py    # 主程序（Python脚本）
├── 合并B站视频.bat    # 启动器（双击运行）
├── logo.png          # 项目Logo
├── README.md         # 说明文档
└── LICENSE           # 许可证
```

## 常见问题

### Q: 提示找不到ffmpeg？

A: 请确保FFmpeg已安装并添加到系统PATH环境变量中。

### Q: 合并后视频没有声音？

A: 检查音频文件是否正确，确保音频和视频文件是一对匹配的。

### Q: 可以保留m4s源文件吗？

A: 可以，修改脚本中的 `DELETE_SOURCE_AFTER_MERGE = False`。

### Q: 支持哪些视频格式？

A: 输入为B站标准的m4s格式，输出为MP4格式。

## 技术实现

- 使用 `ffprobe` 检测文件类型（视频/音频）
- 使用 `ffmpeg` 进行无损合并（`-c copy`）
- 基于时长和文件大小进行智能配对

## 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0 (2024-12-23)
- 初始版本发布
- 支持自动识别和合并m4s文件
- 支持批量处理
- 支持自动删除源文件

---

<div align="center">

Made with ❤️ by [Your Name]

[⬆ Back to Top](#b站m4s视频合并工具)

</div>
