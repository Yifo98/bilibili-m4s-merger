#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型定义
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
from datetime import datetime


@dataclass
class MediaFile:
    """媒体文件模型"""
    path: Path
    name: str
    base_name: str  # 用于匹配的基础名称
    duration: float  # 秒
    has_video: bool
    has_audio: bool
    width: int = 0
    height: int = 0
    size_mb: float = 0.0

    def __post_init__(self):
        if not self.path.exists():
            raise FileNotFoundError(f"文件不存在: {self.path}")

    @property
    def is_video_only(self) -> bool:
        """是否为纯视频文件"""
        return self.has_video and not self.has_audio

    @property
    def is_audio_only(self) -> bool:
        """是否为纯音频文件"""
        return self.has_audio and not self.has_video

    @property
    def resolution(self) -> str:
        """分辨率字符串"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "未知"

    def __str__(self) -> str:
        type_str = "视频" if self.is_video_only else "音频" if self.is_audio_only else "混合"
        return f"{self.name} ({type_str}, {self.duration:.1f}s)"


@dataclass
class FilePair:
    """音视频文件对"""
    video: MediaFile
    audio: MediaFile
    confidence: float = 1.0  # 匹配置信度 0-1

    @property
    def duration_diff(self) -> float:
        """时长差异"""
        return abs(self.video.duration - self.audio.duration)

    def __str__(self) -> str:
        return f"{self.video.name} + {self.audio.name}"


@dataclass
class MergeResult:
    """合并结果"""
    success: bool
    video_path: Path
    audio_path: Path
    output_path: Path
    error: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    retry_count: int = 0

    @property
    def duration(self) -> float:
        """耗时（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def __str__(self) -> str:
        if self.success:
            return f"✓ {self.output_path.name} ({self.duration:.2f}s)"
        else:
            return f"✗ 失败: {self.error}"


@dataclass
class MergeTask:
    """合并任务"""
    pairs: List[FilePair]
    output_dir: Path
    delete_sources: bool = False
    naming_format: str = "default"  # 命名格式: default/original/custom
    custom_template: Optional[str] = None  # 自定义命名模板
    copy_codec: bool = True
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[MergeResult] = field(default_factory=list)
    max_retries: int = 2
    retry_count: int = 0

    def __post_init__(self):
        self.total_count = len(self.pairs)

    @property
    def progress(self) -> float:
        """进度百分比"""
        if self.total_count == 0:
            return 0.0
        return (self.success_count + self.failed_count) / self.total_count * 100

    @property
    def is_completed(self) -> bool:
        """是否完成"""
        return (self.success_count + self.failed_count) >= self.total_count

    @property
    def duration(self) -> float:
        """总耗时（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0

    def add_result(self, result: MergeResult):
        """添加结果"""
        self.results.append(result)
        if result.success:
            self.success_count += 1
        else:
            self.failed_count += 1
