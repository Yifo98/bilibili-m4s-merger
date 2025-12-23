#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站M4S视频音频自动合并工具
自动识别视频和音频文件并智能配对合并
合并成功后自动删除m4s源文件

使用方法：将此脚本放到m4s文件所在目录，直接运行即可
"""

import os
import subprocess
import json
import re
import sys
from pathlib import Path

# 自动获取脚本所在目录
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent.resolve()

INPUT_DIR = SCRIPT_DIR
OUTPUT_DIR = SCRIPT_DIR
FFMPEG_PATH = "ffmpeg"

DELETE_SOURCE_AFTER_MERGE = True  # 合并成功后是否删除源文件

# 屏蔽stderr警告
DEVNULL = subprocess.DEVNULL


def get_file_type(filepath):
    """使用ffprobe检测文件是视频还是音频"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=DEVNULL,
                                text=True, timeout=10, encoding='utf-8', errors='ignore')
        if "video" in result.stdout.lower():
            return "video"
        else:
            return "audio"
    except:
        size = os.path.getsize(filepath) / (1024 * 1024)
        return "video" if size > 50 else "audio"


def get_file_info(filepath):
    """获取文件的详细信息"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=DEVNULL,
                                text=True, timeout=10, encoding='utf-8', errors='ignore')
        data = json.loads(result.stdout)

        duration = float(data.get("format", {}).get("duration", 0))
        streams = data.get("streams", [])

        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        info = {
            "duration": duration,
            "has_video": len(video_streams) > 0,
            "has_audio": len(audio_streams) > 0,
            "width": video_streams[0].get("width") if video_streams else 0,
            "height": video_streams[0].get("height") if video_streams else 0,
        }
        return info
    except Exception:
        return {"duration": 0, "has_video": False, "has_audio": False, "width": 0, "height": 0}


def extract_base_name(filename):
    """提取基础名称（去掉_bilibili和后缀）"""
    name = filename.replace(".m4s", "")
    name = re.sub(r'_bilibili(_\d+(_\d+)?)?$', '', name)
    return name


def categorize_files(files_dir):
    """扫描并分类视频和音频文件"""
    files = list(Path(files_dir).glob("*.m4s"))

    videos = []
    audios = []

    if not files:
        print(f"未找到m4s文件")
        return videos, audios

    print(f"扫描到 {len(files)} 个m4s文件...")

    for f in files:
        file_type = get_file_type(str(f))
        info = get_file_info(str(f))
        base_name = extract_base_name(f.name)

        file_info = {
            "path": f,
            "name": f.name,
            "base_name": base_name,
            "size_mb": f.stat().st_size / (1024 * 1024),
            "duration": info.get("duration", 0),
            "width": info.get("width"),
            "height": info.get("height"),
        }

        if file_type == "video":
            videos.append(file_info)
            print(f"  [视频] {f.name} ({file_info['size_mb']:.1f}MB, {file_info['width']}x{file_info['height']})")
        else:
            audios.append(file_info)
            print(f"  [音频] {f.name} ({file_info['size_mb']:.1f}MB)")

    return videos, audios


def match_files(videos, audios):
    """智能匹配视频和音频"""
    matches = []

    videos_sorted = sorted(videos, key=lambda x: x["size_mb"], reverse=True)
    audios_sorted = sorted(audios, key=lambda x: x["size_mb"], reverse=True)

    used_videos = set()
    used_audios = set()

    # 按时长匹配
    for v in videos_sorted:
        if v["path"] in used_videos:
            continue

        best_audio = None
        best_diff = float('inf')

        for a in audios_sorted:
            if a["path"] in used_audios:
                continue

            duration_diff = abs(v["duration"] - a["duration"])
            if duration_diff < 5 and duration_diff < best_diff:
                best_diff = duration_diff
                best_audio = a

        if best_audio:
            matches.append((v, best_audio))
            used_videos.add(v["path"])
            used_audios.add(best_audio["path"])

    # 处理未匹配的文件
    unmatched_videos = [v for v in videos if v["path"] not in used_videos]
    unmatched_audios = [a for a in audios if a["path"] not in used_audios]

    for i, v in enumerate(unmatched_videos):
        if i < len(unmatched_audios):
            matches.append((v, unmatched_audios[i]))

    return matches


def merge_video_audio(video_path, audio_path, output_path):
    """使用ffmpeg合并视频和音频"""
    cmd = [
        FFMPEG_PATH,
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c", "copy",
        "-y",
        str(output_path)
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=DEVNULL, text=True)
    return result.returncode == 0


def get_quality_label(video_info):
    """根据分辨率生成质量标签"""
    width = video_info.get("width", 0) or 0
    height = video_info.get("height", 0) or 0

    if width >= 3840:
        return "4K"
    elif width >= 2560:
        return "2K"
    elif width >= 1920:
        return "1080p"
    elif width >= 1280:
        return "720p"
    elif width >= 854:
        return "480p"
    else:
        return "360p"


def delete_files(paths):
    """删除指定的文件"""
    for path in paths:
        try:
            os.remove(path)
            print(f"         已删除: {Path(path).name}")
        except Exception as e:
            print(f"         删除失败: {Path(path).name} ({e})")


def main():
    print("=" * 50)
    print("      B站M4S视频音频自动合并工具")
    print("=" * 50)
    print()
    print(f"工作目录: {INPUT_DIR}")
    print()

    # 扫描文件
    videos, audios = categorize_files(INPUT_DIR)

    if not videos:
        print("未找到视频文件，退出")
        return

    if not audios:
        print("未找到音频文件，退出")
        return

    print()
    print("[匹配阶段] 正在匹配视频和音频...")
    matches = match_files(videos, audios)

    print(f"找到 {len(matches)} 组匹配")
    print()

    # 合并文件
    print("[合并阶段] 正在合并文件...")
    success_count = 0
    deleted_files = set()

    for i, (video, audio) in enumerate(matches, 1):
        output_name = f"{video['base_name']}.mp4"
        output_path = Path(OUTPUT_DIR) / output_name

        # 避免文件名冲突
        counter = 1
        while output_path.exists():
            output_name = f"{video['base_name']}_{counter}.mp4"
            output_path = Path(OUTPUT_DIR) / output_name
            counter += 1

        print(f"[{i}/{len(matches)}] 合并: {output_name}")
        print(f"         视频: {video['name']} ({video['width']}x{video['height']})")
        print(f"         音频: {audio['name']}")

        if merge_video_audio(video["path"], audio["path"], output_path):
            print(f"         [成功] {output_name}")
            success_count += 1

            # 删除源文件
            if DELETE_SOURCE_AFTER_MERGE:
                delete_files([video["path"], audio["path"]])
                deleted_files.add(video["path"])
                deleted_files.add(audio["path"])
        else:
            print(f"         [失败]")
        print()

    print("=" * 50)
    print(f"合并完成! 成功: {success_count}/{len(matches)}")
    if DELETE_SOURCE_AFTER_MERGE and deleted_files:
        print(f"已删除 {len(deleted_files)} 个m4s源文件")
    print("=" * 50)


if __name__ == "__main__":
    main()
