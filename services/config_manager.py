#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理服务
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass
class AppConfig:
    """应用配置"""
    # UI 设置
    theme: str = "light"
    language: str = "zh-CN"
    window_width: int = 1200
    window_height: int = 760
    remember_position: bool = True

    # 合并设置
    max_duration_diff: float = 5.0
    match_strategy: str = "smart"  # filename, duration, smart
    output_naming: str = "sequential"  # sequential, preserve, custom
    filename_template: str = "{idx}.ATM_{timestamp}.mp4"

    # FFmpeg 设置
    ffmpeg_threads: int = 0  # 0 = auto
    copy_codec: bool = True
    resolve_safe_mode: bool = True

    # 行为设置
    delete_sources: bool = False
    remember_dirs: bool = True
    last_input_dir: str = ""
    last_output_dir: str = ""

    # 高级设置
    parallel_workers: int = 4
    retry_on_failure: bool = True
    max_retries: int = 2
    generate_log: bool = True


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: 配置文件路径，默认为 settings.json
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "settings.json"

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> AppConfig:
        """加载配置"""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                return AppConfig(**data)
            except Exception as e:
                print(f"加载配置失败，使用默认配置: {e}")

        return AppConfig()

    def save_config(self) -> bool:
        """保存配置"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(asdict(self.config), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            return self.save_config()
        return False

    def update(self, **kwargs) -> bool:
        """批量更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        return self.save_config()

    @property
    def input_dir(self) -> str:
        """获取输入目录"""
        if self.config.remember_dirs:
            return self.config.last_input_dir
        return ""

    @property
    def output_dir(self) -> str:
        """获取输出目录"""
        if self.config.remember_dirs:
            return self.config.last_output_dir
        return ""

    def update_dirs(self, input_dir: str, output_dir: str) -> bool:
        """更新目录配置"""
        self.config.last_input_dir = input_dir
        self.config.last_output_dir = output_dir
        return self.save_config()

    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        self.config = AppConfig()
        return self.save_config()

    def export_config(self, export_path: Path) -> bool:
        """导出配置"""
        try:
            export_path.parent.mkdir(parents=True, exist_ok=True)
            export_path.write_text(
                json.dumps(asdict(self.config), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False

    def import_config(self, import_path: Path) -> bool:
        """导入配置"""
        try:
            if import_path.exists():
                data = json.loads(import_path.read_text(encoding="utf-8"))
                self.config = AppConfig(**data)
                return self.save_config()
        except Exception as e:
            print(f"导入配置失败: {e}")
        return False
