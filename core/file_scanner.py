#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件扫描引擎
"""

import re
from pathlib import Path
from typing import List, Set, Iterable, Optional


class FileScanner:
    """文件扫描器"""

    _BILIBILI_SUFFIX_RE = re.compile(r"_bilibili(_\d+(_\d+)?)?$", re.IGNORECASE)
    _MEDIA_SUFFIX_RE = re.compile(
        r"(_audio|_video|_aud|_vid|_track\d+|_a\d+|_v\d+)$",
        re.IGNORECASE
    )

    # 默认支持的文件格式
    DEFAULT_EXTENSIONS = {
        "m4s", "mp4", "m4a", "aac", "flv", "f4v",
        "ts", "mkv", "webm", "mov", "avi",
        "mp3", "wav", "ogg", "opus"
    }

    @classmethod
    def extract_base_name(cls, filename: str) -> str:
        """
        提取用于匹配的基础名称

        移除常见后缀：
        - _bilibili, _bilibili_1, _bilibili_1_1
        - _audio, _video, _aud, _vid
        - _track1, _track2
        - _a1, _v1
        """
        stem = Path(filename).stem

        # 移除 B 站下载后缀
        stem = cls._BILIBILI_SUFFIX_RE.sub("", stem)

        # 移除音视频标识后缀
        stem = cls._MEDIA_SUFFIX_RE.sub("", stem)

        return stem.strip()

    @classmethod
    def scan_folder(
        cls,
        folder: Path,
        extensions: Optional[Iterable[str]] = None
    ) -> List[Path]:
        """
        扫描文件夹中的媒体文件

        Args:
            folder: 文件夹路径
            extensions: 文件扩展名列表，默认使用 DEFAULT_EXTENSIONS

        Returns:
            文件路径列表
        """
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"无效的文件夹路径: {folder}")

        # 使用指定的扩展名或默认扩展名
        if extensions is None:
            extensions = cls.DEFAULT_EXTENSIONS

        ext_set = {f".{ext.lower().lstrip('.')}" for ext in extensions if ext.strip()}

        files = []
        for entry in folder.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() in ext_set:
                files.append(entry)

        return sorted(files)

    @classmethod
    def scan_multiple_folders(
        cls,
        folders: List[Path],
        extensions: Optional[Iterable[str]] = None
    ) -> List[Path]:
        """
        扫描多个文件夹

        Args:
            folders: 文件夹路径列表
            extensions: 文件扩展名列表

        Returns:
            所有文件路径列表（去重）
        """
        all_files = []
        seen_paths: Set[Path] = set()

        for folder in folders:
            try:
                files = cls.scan_folder(folder, extensions)
                for file in files:
                    # 使用绝对路径去重
                    abs_path = file.resolve()
                    if abs_path not in seen_paths:
                        seen_paths.add(abs_path)
                        all_files.append(file)
            except Exception as e:
                print(f"扫描文件夹 {folder} 时出错: {e}")

        return all_files
