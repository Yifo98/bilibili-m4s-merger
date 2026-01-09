#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并执行器
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable
from .models import MediaFile, FilePair, MergeResult, MergeTask
from .file_scanner import FileScanner
from .smart_matcher import SmartMatcher


class Merger:
    """合并执行器"""

    def __init__(self, ffmpeg_service, progress_callback: Optional[Callable] = None):
        """
        Args:
            ffmpeg_service: FFmpegService 实例
            progress_callback: 进度回调函数
        """
        self.ffmpeg = ffmpeg_service
        self.progress_callback = progress_callback

    def create_media_files(
        self,
        file_paths: List[Path],
        parallel_workers: int = 1
    ) -> List[MediaFile]:
        """创建媒体文件对象列表"""
        media_files = []

        workers = max(1, int(parallel_workers or 1))
        if workers > 1 and len(file_paths) > 1:
            workers = min(workers, len(file_paths))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for file_path, info in zip(file_paths, executor.map(self.ffmpeg.analyze_file, file_paths)):
                    if info:
                        media_files.append(self._build_media_file(file_path, info))
        else:
            for file_path in file_paths:
                info = self.ffmpeg.analyze_file(file_path)
                if info:
                    media_files.append(self._build_media_file(file_path, info))

        return media_files

    @staticmethod
    def _build_media_file(file_path: Path, info: dict) -> MediaFile:
        return MediaFile(
            path=file_path,
            name=file_path.name,
            base_name=FileScanner.extract_base_name(file_path.name),
            duration=info.get("duration", 0),
            has_video=info.get("has_video", False),
            has_audio=info.get("has_audio", False),
            width=info.get("width", 0),
            height=info.get("height", 0),
            size_mb=file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0
        )

    def categorize_files(self, files: List[MediaFile]) -> tuple[List[MediaFile], List[MediaFile]]:
        """分类文件为视频和音频"""
        videos = [f for f in files if f.is_video_only]
        audios = [f for f in files if f.is_audio_only]
        return videos, audios

    def prepare_task(
        self,
        input_folders: List[Path],
        extensions: List[str],
        output_dir: Path,
        delete_sources: bool = False,
        matcher_config: Optional[dict] = None,
        naming_format: str = "default",
        custom_template: Optional[str] = None,
        parallel_workers: int = 1,
        copy_codec: bool = True,
        retry_on_failure: bool = True,
        max_retries: int = 2
    ) -> Optional[MergeTask]:
        """
        准备合并任务

        Args:
            input_folders: 输入文件夹列表
            extensions: 文件扩展名列表
            output_dir: 输出目录
            delete_sources: 是否删除源文件
            matcher_config: 匹配器配置
            naming_format: 命名格式 (default/original/custom)
            custom_template: 自命名模板

        Returns:
            MergeTask 对象，失败返回 None
        """
        # 1. 扫描文件
        all_files = FileScanner.scan_multiple_folders(input_folders, extensions)
        if not all_files:
            return None

        # 2. 分析文件
        media_files = self.create_media_files(all_files, parallel_workers=parallel_workers)
        if not media_files:
            return None

        # 3. 分类
        videos, audios = self.categorize_files(media_files)
        if not videos or not audios:
            return None

        # 4. 匹配
        matcher_config = matcher_config or {}
        matcher = SmartMatcher(
            max_duration_diff=matcher_config.get("max_duration_diff", 5.0),
            confidence_threshold=matcher_config.get("confidence_threshold", 0.6),
            match_strategy=matcher_config.get("match_strategy", "smart")
        )
        pairs = matcher.match(videos, audios)

        if not pairs:
            return None

        # 5. 创建任务
        effective_retries = max(0, int(max_retries)) if retry_on_failure else 0
        task = MergeTask(
            pairs=pairs,
            output_dir=output_dir,
            delete_sources=delete_sources,
            naming_format=naming_format,
            custom_template=custom_template,
            copy_codec=copy_codec,
            max_retries=effective_retries
        )

        return task

    def execute_task(self, task: MergeTask) -> MergeTask:
        """
        执行合并任务

        Args:
            task: MergeTask 对象

        Returns:
            更新后的 MergeTask 对象
        """
        task.start_time = datetime.now()

        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y_%m_%d_%H.%M")
        seq = 1

        for idx, pair in enumerate(task.pairs, 1):
            # 生成输出文件名（根据命名格式）
            output_name = self._generate_output_name(
                pair=pair,
                seq=seq,
                timestamp=timestamp,
                naming_format=task.naming_format,
                custom_template=task.custom_template
            )
            output_path = self._ensure_unique_output_path(task.output_dir / output_name)

            # 执行合并
            result = self._merge_pair(pair, output_path, copy_codec=task.copy_codec)
            result.retry_count = 0

            # 重试逻辑
            if not result.success and task.max_retries > 0:
                for attempt in range(task.max_retries):
                    result = self._merge_pair(pair, output_path, copy_codec=task.copy_codec)
                    result.retry_count = attempt + 1
                    if result.success:
                        break

            result.end_time = datetime.now()
            task.add_result(result)

            # 删除源文件
            if result.success and task.delete_sources:
                try:
                    os.remove(pair.video.path)
                    os.remove(pair.audio.path)
                except Exception as e:
                    print(f"删除源文件失败: {e}")

            # 进度回调
            if self.progress_callback:
                self.progress_callback(idx, len(task.pairs), result)

            seq += 1

        task.end_time = datetime.now()
        return task

    def _generate_output_name(self, pair, seq: int, timestamp: datetime,
                             naming_format: str, custom_template: Optional[str] = None) -> str:
        """
        生成输出文件名

        Args:
            pair: FilePair 对象
            seq: 序号
            timestamp: 时间戳
            naming_format: 命名格式
            custom_template: 自定义模板

        Returns:
            输出文件名
        """
        # 获取视频文件的基础名称（不含扩展名）
        video_name = pair.video.base_name if pair.video.base_name else "video"
        timestamp_str = timestamp.strftime("%Y_%m_%d_%H.%M")

        if naming_format == "original":
            # 保持原视频文件名
            name = f"{video_name}.mp4"
        elif naming_format == "custom" and custom_template:
            # 自定义格式
            name_vars = {
                "{name}": video_name,
                "{date}": timestamp.strftime("%Y%m%d"),
                "{time}": timestamp.strftime("%H%M"),
                "{num}": f"{seq:03d}"
            }

            name = custom_template
            for var, value in name_vars.items():
                name = name.replace(var, value)

            # 确保以 .mp4 结尾
            if not name.lower().endswith(".mp4"):
                name += ".mp4"
        else:
            # 默认格式：序号_时间戳.mp4
            name = f"{seq}.ATM_{timestamp_str}.mp4"

        return name

    def _merge_pair(self, pair: FilePair, output_path: Path, copy_codec: bool = True) -> MergeResult:
        """合并单个文件对"""
        result = MergeResult(
            success=False,
            video_path=pair.video.path,
            audio_path=pair.audio.path,
            output_path=output_path,
            start_time=datetime.now()
        )

        try:
            success = self.ffmpeg.merge_media(
                pair.video.path,
                pair.audio.path,
                output_path,
                copy_codec=copy_codec
            )
            result.success = success

            if not success:
                result.error = "FFmpeg 合并失败"

        except Exception as e:
            result.error = str(e)

        result.end_time = datetime.now()
        return result

    @staticmethod
    def _ensure_unique_output_path(output_path: Path) -> Path:
        """避免输出路径冲突"""
        if not output_path.exists():
            return output_path

        stem = output_path.stem
        suffix = output_path.suffix
        counter = 1
        while True:
            candidate = output_path.with_name(f"{stem}_{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1
