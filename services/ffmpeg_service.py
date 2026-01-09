#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg 服务封装
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any


class FFmpegService:
    """FFmpeg 服务类"""

    def __init__(self, ffmpeg_path: Optional[str] = None, ffprobe_path: Optional[str] = None):
        """
        Args:
            ffmpeg_path: ffmpeg 可执行文件路径
            ffprobe_path: ffprobe 可执行文件路径
        """
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg("ffmpeg")
        self.ffprobe_path = ffprobe_path or self._find_ffmpeg("ffprobe")
        self._probe_cache: Dict[tuple, Dict[str, Any]] = {}

        if not self.is_available():
            raise RuntimeError("FFmpeg 未安装或未找到")

    @staticmethod
    def _find_ffmpeg(name: str) -> str:
        """查找 ffmpeg 可执行文件"""
        # 1. 检查程序内置目录
        builtin_path = Path(__file__).parent.parent / "ffmpeg" / "bin" / f"{name}.exe"
        if builtin_path.exists():
            return str(builtin_path)

        # 2. 检查系统 PATH
        system_path = shutil.which(name)
        if system_path:
            return system_path

        # 3. 返回默认名称（可能在 PATH 中）
        return name

    def is_available(self) -> bool:
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except Exception:
            return False

    def analyze_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        分析媒体文件信息

        Args:
            file_path: 文件路径

        Returns:
            包含媒体信息的字典，失败返回 None
        """
        if not file_path.exists():
            return None
        try:
            stat_info = file_path.stat()
            cache_key = (file_path.resolve(), stat_info.st_mtime, stat_info.st_size)
            cached = self._probe_cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            cache_key = None

        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=15,
                encoding="utf-8",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if not result.stdout:
                return None

            data = json.loads(result.stdout)
            parsed = self._parse_ffprobe_data(data)
            if cache_key is not None:
                self._probe_cache[cache_key] = parsed
            return parsed

        except Exception as e:
            print(f"分析文件失败 {file_path}: {e}")
            return None

    def _parse_ffprobe_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析 ffprobe 输出"""
        fmt = data.get("format", {}) or {}
        streams = data.get("streams", []) or []

        duration = float(fmt.get("duration") or 0)

        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        width = 0
        height = 0
        if video_streams:
            width = int(video_streams[0].get("width") or 0)
            height = int(video_streams[0].get("height") or 0)

        return {
            "duration": duration,
            "has_video": bool(video_streams),
            "has_audio": bool(audio_streams),
            "width": width,
            "height": height,
        }

    def merge_media(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        copy_codec: bool = True
    ) -> bool:
        """
        合并音视频文件

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            copy_codec: 是否使用 copy 编码（不重新编码，速度快）

        Returns:
            是否成功
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path),
            "-i", str(audio_path),
        ]

        if copy_codec:
            cmd.extend(["-c", "copy"])

        cmd.extend(["-y", str(output_path)])

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,  # 5 分钟超时
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            return result.returncode == 0 and output_path.exists()

        except subprocess.TimeoutExpired:
            print(f"合并超时: {video_path.name} + {audio_path.name}")
            return False
        except Exception as e:
            print(f"合并失败: {e}")
            return False

    def get_version(self) -> Optional[str]:
        """获取 FFmpeg 版本"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                # 提取版本号
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower():
                        return line.strip()
                return result.stdout.split('\n')[0]
        except Exception:
            pass
        return None


# 导入 shutil
import shutil
