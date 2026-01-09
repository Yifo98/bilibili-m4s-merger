#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能匹配引擎
"""

from collections import defaultdict
from typing import List, Tuple, Optional, Dict
from difflib import SequenceMatcher
from .models import MediaFile, FilePair
from .file_scanner import FileScanner


class SmartMatcher:
    """智能文件匹配器"""

    def __init__(
        self,
        max_duration_diff: float = 5.0,
        confidence_threshold: float = 0.6,
        match_strategy: str = "smart"
    ):
        """
        Args:
            max_duration_diff: 最大时长差异（秒）
            confidence_threshold: 匹配置信度阈值
        """
        self.max_duration_diff = max_duration_diff
        self.confidence_threshold = confidence_threshold
        self.match_strategy = (match_strategy or "smart").lower()

    def match(
        self,
        videos: List[MediaFile],
        audios: List[MediaFile]
    ) -> List[FilePair]:
        """
        智能匹配音视频文件

        Args:
            videos: 视频文件列表
            audios: 音频文件列表

        Returns:
            匹配的文件对列表
        """
        pairs = []
        used_audios = set()

        audios_by_base: Dict[str, List[MediaFile]] = defaultdict(list)
        for audio in audios:
            audios_by_base[audio.base_name].append(audio)

        # 按时长排序（长的优先）
        videos_sorted = sorted(videos, key=lambda x: x.duration, reverse=True)
        audios_sorted = sorted(audios, key=lambda x: x.duration, reverse=True)

        for video in videos_sorted:
            if not audios_sorted:
                break

            if self.match_strategy == "duration":
                candidates = [
                    a for a in audios_sorted
                    if a.path not in used_audios
                ]
            else:
                # 优先查找文件名相同的
                name_matches = [
                    a for a in audios_by_base.get(video.base_name, [])
                    if a.path not in used_audios
                ]

                candidates = name_matches if name_matches else [
                    a for a in audios_sorted
                    if a.path not in used_audios
                ]

            if not candidates:
                continue

            # 找到最佳匹配
            best_audio = None
            best_score = 0.0

            for audio in candidates:
                score = self._calculate_match_score(video, audio)
                if score > best_score:
                    best_score = score
                    best_audio = audio

            # 检查置信度
            if best_audio and best_score >= self.confidence_threshold:
                pairs.append(FilePair(video, best_audio, best_score))
                used_audios.add(best_audio.path)

        return pairs

    def _calculate_match_score(
        self,
        video: MediaFile,
        audio: MediaFile
    ) -> float:
        """
        计算匹配分数（0-1）

        考虑因素：
        1. 文件名相似度 (40%)
        2. 时长差异 (30%)
        3. 分辨率/文件大小 (20%)
        4. 文件扩展名 (10%)
        """
        score = 0.0

        if self.match_strategy == "duration":
            if video.duration > 0 and audio.duration > 0:
                duration_diff = abs(video.duration - audio.duration)
                if self.max_duration_diff > 0:
                    return max(0, 1 - duration_diff / self.max_duration_diff)
                return 1.0 if duration_diff == 0 else 0.0
            if video.size_mb > 0 and audio.size_mb > 0:
                return min(video.size_mb, audio.size_mb) / max(video.size_mb, audio.size_mb)
            return 0.0

        if self.match_strategy == "filename":
            name_similarity = SequenceMatcher(
                None,
                video.base_name.lower(),
                audio.base_name.lower()
            ).ratio()
            return name_similarity

        # 1. 文件名相似度 (40%)
        name_similarity = SequenceMatcher(
            None,
            video.base_name.lower(),
            audio.base_name.lower()
        ).ratio()
        score += name_similarity * 0.4

        # 2. 时长差异 (30%)
        if video.duration > 0 and audio.duration > 0:
            duration_diff = abs(video.duration - audio.duration)
            # 时长差异越小，分数越高
            if self.max_duration_diff > 0:
                duration_score = max(0, 1 - duration_diff / self.max_duration_diff)
            else:
                duration_score = 1.0 if duration_diff == 0 else 0.0
            score += duration_score * 0.3
        else:
            # 无法获取时长，使用文件大小对比
            size_diff = abs(video.size_mb - audio.size_mb)
            max_size = max(video.size_mb, audio.size_mb)
            if max_size > 0:
                size_score = max(0, 1 - size_diff / max_size)
                score += size_score * 0.3

        # 3. 文件大小相似度 (20%)
        if video.size_mb > 0 and audio.size_mb > 0:
            size_ratio = min(video.size_mb, audio.size_mb) / max(video.size_mb, audio.size_mb)
            score += size_ratio * 0.2

        # 4. 扩展名匹配 (10%)
        # 常见的音视频配对
        common_pairs = {
            ("m4s", "m4s"),
            ("mp4", "m4a"),
            ("mp4", "aac"),
            ("mkv", "aac"),
            ("webm", "opus"),
        }
        video_ext = video.path.suffix.lower().lstrip('.')
        audio_ext = audio.path.suffix.lower().lstrip('.')
        if (video_ext, audio_ext) in common_pairs:
            score += 0.1

        return min(score, 1.0)  # 确保不超过 1.0

    def find_unmatched(
        self,
        videos: List[MediaFile],
        audios: List[MediaFile],
        pairs: List[FilePair]
    ) -> Tuple[List[MediaFile], List[MediaFile]]:
        """
        找出未匹配的文件

        Args:
            videos: 所有视频文件
            audios: 所有音频文件
            pairs: 已匹配的文件对

        Returns:
            (未匹配的视频, 未匹配的音频)
        """
        matched_videos = {p.video.path for p in pairs}
        matched_audios = {p.audio.path for p in pairs}

        unmatched_videos = [v for v in videos if v.path not in matched_videos]
        unmatched_audios = [a for a in audios if a.path not in matched_audios]

        return unmatched_videos, unmatched_audios
