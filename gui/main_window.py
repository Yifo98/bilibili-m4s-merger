#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口 - 柔和米灰主题
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
from pathlib import Path
from typing import Optional
import threading
import time

from core import Merger, FileScanner
from services import FFmpegService, ConfigManager


class MainWindow(ctk.CTk):
    """主窗口 - 柔和米灰主题"""

    def _update_splash(self, text: str, progress: int):
        """Update splash screen (packaged builds only)."""
        if getattr(self, "_splash_window", None):
            try:
                if self._splash_label:
                    self._splash_label.configure(text=text)
                if self._splash_progress:
                    if hasattr(self._splash_progress, "set"):
                        self._splash_progress.set(max(0.0, min(1.0, progress / 100.0)))
                    else:
                        self._splash_progress["value"] = max(0, min(100, int(progress)))
                self._splash_window.update_idletasks()
            except Exception:
                pass
        try:
            import pyi_splash  # type: ignore
            pyi_splash.update_text("\u6b63\u5728\u542f\u52a8\uff0c\u8bf7\u7a0d\u5019...")
            pyi_splash.update_progress(progress)
        except Exception:
            pass

    def _close_splash(self):
        """Close splash screen (packaged builds only)."""
        try:
            import pyi_splash  # type: ignore
            pyi_splash.close()
        except Exception:
            pass
        if getattr(self, "_splash_window", None):
            try:
                self._splash_window.destroy()
            except Exception:
                pass
            self._splash_window = None
            self._splash_label = None
            self._splash_progress = None
        if self.state() == "withdrawn":
            self._show_main_window()

    def _create_custom_splash(self):
        if getattr(self, "_splash_window", None):
            return

        bg = "#F2ECE3"
        muted = "#6F6257"

        splash = ctk.CTkToplevel(self)
        splash.title("\u542f\u52a8\u4e2d")
        splash.resizable(False, False)
        splash.configure(fg_color=bg)
        splash.geometry("420x260")
        splash.attributes("-topmost", False)

        container = ctk.CTkFrame(splash, fg_color=bg, corner_radius=0)
        container.pack(fill="both", expand=True)

        img_path = self._resource_path(os.path.join("assets", "splash.png"))
        self._splash_image = None
        if os.path.exists(img_path):
            try:
                self._splash_image = tk.PhotoImage(file=img_path)
                img_label = ctk.CTkLabel(container, image=self._splash_image, text="")
                img_label.pack(padx=8, pady=(8, 0))
            except Exception:
                pass

        self._splash_label = ctk.CTkLabel(
            container,
            text="\u6b63\u5728\u542f\u52a8\uff0c\u8bf7\u7a0d\u5019...",
            text_color=muted,
            font=ctk.CTkFont(size=12)
        )
        self._splash_label.pack(pady=(6, 4))

        self._splash_progress = ctk.CTkProgressBar(
            container,
            height=8,
            fg_color="#E8DFD3",
            progress_color="#3E5868"
        )
        self._splash_progress.pack(fill="x", padx=12, pady=(0, 12))
        self._splash_progress.set(0)

        def start_move(event):
            splash._drag_x = event.x
            splash._drag_y = event.y

        def on_move(event):
            x = splash.winfo_x() + event.x - getattr(splash, "_drag_x", 0)
            y = splash.winfo_y() + event.y - getattr(splash, "_drag_y", 0)
            splash.geometry(f"+{x}+{y}")

        splash.bind("<ButtonPress-1>", start_move)
        splash.bind("<B1-Motion>", on_move)

        splash.update_idletasks()
        width = max(360, splash.winfo_reqwidth())
        height = max(200, splash.winfo_reqheight())
        x = (splash.winfo_screenwidth() - width) // 2
        y = (splash.winfo_screenheight() - height) // 2
        splash.geometry(f"{width}x{height}+{x}+{y}")
        splash.update()

        self._splash_window = splash

    def _show_main_window(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def __init__(self):
        super().__init__()

        self._create_custom_splash()

        self._update_splash("\u542f\u52a8\u521d\u59cb\u5316", 5)

        # 初始化服务
        self.config = ConfigManager()
        try:
            self._update_splash("\u68c0\u6d4b FFmpeg", 20)
            self.ffmpeg = FFmpegService()
            self._update_splash("\u521d\u59cb\u5316\u5408\u5e76\u5f15\u64ce", 35)
            self.merger = Merger(self.ffmpeg, self._on_progress)
        except RuntimeError as e:
            self._close_splash()
            messagebox.showerror("错误", f"FFmpeg 初始化失败: {e}\n\n请确保FFmpeg已安装。")
            self.destroy()
            return

        self.current_task = None
        self.worker = None
        self.selected_formats = {"m4s", "mp4", "m4a", "aac"}
        self._last_progress_log = 0.0
        self._merge_start_time = 0.0

        # 设置主题
        self._update_splash("\u52a0\u8f7d\u4e3b\u9898", 50)
        self._setup_theme()
        self._show_main_window()
        self._update_splash("\u6784\u5efa\u754c\u9762", 70)
        self._build_ui()
        self._update_splash("\u52a0\u8f7d\u914d\u7f6e", 85)
        self._load_settings()
        self._update_splash("\u51c6\u5907\u5b8c\u6210", 100)
        self._show_main_window()
        self._close_splash()

    def _setup_theme(self):
        """设置主题"""
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("AV Track Merger v2.0")
        self.geometry("1020x880")
        self.minsize(960, 800)
        self._set_window_icon()

        # 窗口居中
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 1020) // 2
        y = (screen_height - 880) // 2
        self.geometry(f"1020x880+{x}+{y}")

        # 配色方案（米白 + 高级冷灰蓝）
        self.colors = {
            "bg": "#F2ECE3",           # 米白背景
            "panel": "#FAF6F0",        # 卡片背景
            "panel_2": "#E8DFD3",      # 标题栏背景
            "border": "#D7CBBE",       # 边框颜色
            "highlight": "#EFE7DB",    # 高光线（已移除）
            "muted": "#6F6257",        # 次要文字
            "text": "#2B2622",         # 主要文字
            "accent": "#A6907C",       # 强调色（米金）
            "accent_2": "#3E5868",     # 辅助色（冷灰蓝）
            "button": "#A6907C",       # 按钮颜色
            "button_hover": "#9A846F", # 按钮悬停
        }

    def _resource_path(self, relative_path: str) -> str:
        base_dir = getattr(sys, "_MEIPASS", str(Path(__file__).resolve().parent.parent))
        return str(Path(base_dir) / relative_path)

    def _set_window_icon(self):
        icon_path = self._resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(icon_path):
            try:
                self._icon_image = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, self._icon_image)
            except Exception:
                pass

    def _build_ui(self):
        """构建 UI"""
        # 主容器
        main_container = ctk.CTkFrame(self, fg_color=self.colors["bg"], corner_radius=0)
        main_container.pack(fill="both", expand=True)

        # 顶部标题栏
        self._build_header(main_container)

        # 内容容器
        content = ctk.CTkFrame(main_container, fg_color=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=(12, 16))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=0)
        content.grid_rowconfigure(1, weight=0)
        content.grid_rowconfigure(2, weight=0)
        content.grid_rowconfigure(3, weight=1)

        top_stack = ctk.CTkFrame(content, fg_color="transparent")
        top_stack.grid(row=0, column=0, sticky="ew")

        self._build_path_card(top_stack)
        self._build_format_card(top_stack)
        self._build_naming_action_card(top_stack)

        bottom_row = ctk.CTkFrame(content, fg_color="transparent")
        bottom_row.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        bottom_row.grid_columnconfigure(0, weight=1)
        bottom_row.grid_columnconfigure(1, weight=1)
        bottom_row.grid_rowconfigure(0, weight=1)

        matched_slot = ctk.CTkFrame(bottom_row, fg_color="transparent")
        matched_slot.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._build_matched_card(matched_slot)

        log_slot = ctk.CTkFrame(bottom_row, fg_color="transparent")
        log_slot.grid(row=0, column=1, sticky="nsew")
        self._build_log_card(log_slot)

    def _build_header(self, parent):
        """构建顶部标题栏"""
        header = ctk.CTkFrame(
            parent,
            fg_color=self.colors["panel_2"],
            height=70,
            corner_radius=0
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x", padx=22, pady=(12, 6))

        ctk.CTkLabel(
            title_row,
            text="AV Track Merger",
            font=ctk.CTkFont(size=21, weight="bold"),
            text_color=self.colors["text"]
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="Modern batch merger for split audio/video tracks",
            font=ctk.CTkFont(size=10),
            text_color=self.colors["muted"]
        ).pack(anchor="w", padx=22, pady=(0, 6))

    def _glass_card(self, parent):
        """创建卡片效果"""
        card = ctk.CTkFrame(
            parent,
            fg_color=self.colors["panel"],
            corner_radius=20,
            border_width=1,
            border_color=self.colors["border"]
        )
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True)
        return card, body

    def _build_path_card(self, parent):
        """构建路径设置卡片"""
        path_card, path_body = self._glass_card(parent)
        path_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            path_body,
            text="路径设置",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text"]
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))

        path_body.grid_columnconfigure(0, weight=1)
        path_body.grid_columnconfigure(1, weight=1)

        input_block = ctk.CTkFrame(path_body, fg_color="transparent")
        input_block.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=6)
        input_block.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            input_block,
            text="输入目录",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["muted"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._input_placeholder = "选择包含媒体文件的文件夹..."
        self.input_var = ctk.StringVar(value=self._input_placeholder)
        input_row = ctk.CTkFrame(input_block, fg_color="transparent")
        input_row.grid(row=1, column=0, sticky="ew")
        input_row.grid_columnconfigure(0, weight=1)

        input_box = ctk.CTkFrame(
            input_row,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=1,
            border_color=self.colors["border"]
        )
        input_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.input_label = ctk.CTkLabel(
            input_box,
            textvariable=self.input_var,
            font=ctk.CTkFont(size=13),
            text_color=self.colors["muted"],
            fg_color="transparent",
            height=28,
            anchor="w"
        )
        self.input_label.pack(fill="x", padx=10, pady=4)

        ctk.CTkButton(
            input_row,
            text="浏览...",
            command=self._choose_input,
            width=96,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.colors["button"],
            hover_color=self.colors["button_hover"],
            text_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color=self.colors["border"]
        ).grid(row=0, column=1)

        output_block = ctk.CTkFrame(path_body, fg_color="transparent")
        output_block.grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=6)
        output_block.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            output_block,
            text="输出目录",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["muted"]
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._output_placeholder = "选择合并后文件的保存位置..."
        self.output_var = ctk.StringVar(value=self._output_placeholder)
        output_row = ctk.CTkFrame(output_block, fg_color="transparent")
        output_row.grid(row=1, column=0, sticky="ew")
        output_row.grid_columnconfigure(0, weight=1)

        output_box = ctk.CTkFrame(
            output_row,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=1,
            border_color=self.colors["border"]
        )
        output_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.output_label = ctk.CTkLabel(
            output_box,
            textvariable=self.output_var,
            font=ctk.CTkFont(size=13),
            text_color=self.colors["muted"],
            fg_color="transparent",
            height=28,
            anchor="w"
        )
        self.output_label.pack(fill="x", padx=10, pady=4)

        ctk.CTkButton(
            output_row,
            text="浏览...",
            command=self._choose_output,
            width=96,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.colors["button"],
            hover_color=self.colors["button_hover"],
            text_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color=self.colors["border"]
        ).grid(row=0, column=1)

    def _build_format_card(self, parent):
        """构建格式选择卡片"""
        format_card, format_body = self._glass_card(parent)
        format_card.pack(fill="x", pady=(0, 10))

        # 标题
        ctk.CTkLabel(
            format_body,
            text="文件格式",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text"]
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 6))

        # 格式网格
        format_grid = ctk.CTkFrame(format_body, fg_color="transparent")
        format_grid.grid(row=1, column=0, columnspan=4, sticky="w", padx=16)

        self.format_buttons = {}
        formats = ["m4s", "mp4", "m4a", "aac", "flv", "ts", "mkv", "webm", "mov", "avi", "mp3", "wav", "ogg", "opus"]

        for idx, fmt in enumerate(formats):
            col = idx % 7
            row = idx // 7
            var = ctk.BooleanVar(value=fmt in self.selected_formats)

            cb = ctk.CTkCheckBox(
                format_grid,
                text=fmt.upper(),
                variable=var,
                font=ctk.CTkFont(size=12, weight="bold"),
                checkbox_width=18,
                checkbox_height=18,
                corner_radius=5,
                fg_color=self.colors["accent"],
                border_color=self.colors["border"],
                hover_color=self.colors["button_hover"],
                checkmark_color="#FFFFFF",
                text_color=self.colors["text"],
                command=lambda f=fmt, v=var: self._toggle_format(f, v)
            )
            cb.grid(row=row, column=col, padx=(0, 14), pady=2, sticky="w")
            self.format_buttons[fmt] = (cb, var)

        # 按钮
        btns = ctk.CTkFrame(format_body, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="w", padx=16, pady=(6, 10))

        ctk.CTkButton(
            btns,
            text="全选",
            command=self._select_all_formats,
            width=90,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.colors["button"],
            hover_color=self.colors["button_hover"],
            text_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color=self.colors["border"]
        ).pack(side="left")

        ctk.CTkButton(
            btns,
            text="清空",
            command=self._clear_all_formats,
            width=90,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.colors["button"],
            hover_color=self.colors["button_hover"],
            text_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color=self.colors["border"]
        ).pack(side="left", padx=8)

    def _build_naming_action_card(self, parent):
        """构建命名和操作合并卡片"""
        card, body = self._glass_card(parent)
        card.pack(fill="x")

        ctk.CTkLabel(
            body,
            text="输出设置",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=16, pady=(12, 6))

        main_frame = ctk.CTkFrame(body, fg_color="transparent")
        main_frame.pack(fill="x", padx=16, pady=(0, 6))
        main_frame.grid_columnconfigure(0, weight=3)
        main_frame.grid_columnconfigure(1, weight=2)

        naming_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        naming_frame.grid(row=0, column=0, sticky="nw", padx=(0, 12))

        ctk.CTkLabel(
            naming_frame,
            text="命名方式",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["muted"]
        ).pack(anchor="w", pady=(0, 2))

        self.naming_format = ctk.StringVar(value="default")

        default_container = ctk.CTkFrame(naming_frame, fg_color="transparent")
        default_container.pack(anchor="w", pady=2, fill="x")

        ctk.CTkRadioButton(
            default_container,
            text="默认（如 1.ATM_2026_01_08_11.39）",
            variable=self.naming_format,
            value="default",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text"]
        ).pack(anchor="w")

        ctk.CTkRadioButton(
            naming_frame,
            text="保持原视频文件名",
            variable=self.naming_format,
            value="original",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=2)

        action_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        action_frame.grid(row=0, column=1, sticky="ne")

        options_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        options_row.pack(anchor="e", pady=(0, 6))

        self.delete_check = ctk.CTkCheckBox(
            options_row,
            text="合并后删除源文件",
            font=ctk.CTkFont(size=12),
            checkbox_width=16,
            checkbox_height=16,
            corner_radius=4,
            fg_color=self.colors["accent"],
            hover_color=self.colors["button_hover"],
            checkmark_color="#FFFFFF",
            text_color=self.colors["muted"],
            variable=ctk.BooleanVar(value=self.config.get("delete_sources", False)),
            onvalue=True,
            offvalue=False
        )
        self.delete_check.pack(side="left", padx=(0, 14))

        self.remember_check = ctk.CTkCheckBox(
            options_row,
            text="记住目录",
            font=ctk.CTkFont(size=12),
            checkbox_width=16,
            checkbox_height=16,
            corner_radius=4,
            fg_color=self.colors["accent"],
            hover_color=self.colors["button_hover"],
            checkmark_color="#FFFFFF",
            text_color=self.colors["muted"],
            variable=ctk.BooleanVar(value=self.config.get("remember_dirs", True)),
            onvalue=True,
            offvalue=False
        )
        self.remember_check.pack(side="left")

        self.start_btn = ctk.CTkButton(
            action_frame,
            text="开始合并",
            command=self._start_merge,
            fg_color=self.colors["accent_2"],
            hover_color="#34505F",
            width=120,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FFFFFF",
            corner_radius=10
        )
        self.start_btn.pack(anchor="e", pady=(0, 6))

    def _toggle_custom_input(self):
        """切换自定义输入框显示（已禁用）"""
        pass

    def _build_bottom_section(self, parent):
        """构建底部区域"""
        # 已拆分为 _build_matched_card 和 _build_log_card
        pass

    def _build_matched_card(self, parent):
        """构建已匹配文件卡片"""
        file_card, file_body = self._glass_card(parent)
        file_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            file_body,
            text="已匹配的文件",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=16, pady=(12, 4))

        self.file_text = ctk.CTkTextbox(
            file_body,
            font=ctk.CTkFont(size=13, family="Microsoft YaHei UI"),
            fg_color="#FFFFFF",
            border_color=self.colors["border"],
            border_width=1,
            corner_radius=12,
            text_color=self.colors["text"]
        )
        self.file_text.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.file_text.configure(state="disabled")

    def _build_log_card(self, parent):
        """构建日志输出卡片"""
        log_card, log_body = self._glass_card(parent)
        log_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            log_body,
            text="日志输出",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=16, pady=(12, 4))

        progress_row = ctk.CTkFrame(log_body, fg_color="transparent")
        progress_row.pack(fill="x", padx=16, pady=(0, 6))

        self.status_label = ctk.CTkLabel(
            progress_row,
            text="就绪",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["muted"]
        )
        self.status_label.pack(anchor="w")

        self.progress_bar = ctk.CTkProgressBar(
            progress_row,
            fg_color=self.colors["panel_2"],
            progress_color=self.colors["accent_2"]
        )
        self.progress_bar.pack(fill="x", pady=(4, 0))
        self.progress_bar.set(0)

        self.log_text = ctk.CTkTextbox(
            log_body,
            font=ctk.CTkFont(size=13, family="Consolas"),
            fg_color="#FFFFFF",
            border_color=self.colors["border"],
            border_width=1,
            corner_radius=12,
            text_color="#5B5C57"
        )
        self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 14))

    def _choose_input(self):
        """选择输入目录"""
        dir_path = self._browse_folder(
            title="选择输入目录",
            initial_dir=self.input_var.get(),
            preview_formats=list(self.selected_formats)
        )
        if dir_path:
            self._set_path_label(self.input_var, self._input_placeholder, dir_path, self.input_label)
            self._save_settings()
            self._refresh_file_list()
            self._log(f"输入目录: {dir_path}")

    def _choose_output(self):
        """选择输出目录"""
        dir_path = self._browse_folder(
            title="选择输出目录",
            initial_dir=self.output_var.get(),
            preview_formats=None
        )
        if dir_path:
            self._set_path_label(self.output_var, self._output_placeholder, dir_path, self.output_label)
            self._save_settings()
            self._log(f"输出目录: {dir_path}")

    def _browse_folder(self, title: str, initial_dir: str, preview_formats=None) -> Optional[str]:
        """自定义文件夹选择器（含文件预览）"""
        dialog = ctk.CTkToplevel(self)
        if hasattr(self, "_icon_image"):
            try:
                dialog.iconphoto(True, self._icon_image)
            except Exception:
                pass
        dialog.title(title)
        dialog.geometry("880x560")
        dialog.minsize(760, 480)
        dialog.transient(self)
        dialog.grab_set()

        header = ctk.CTkFrame(dialog, fg_color=self.colors["panel_2"], corner_radius=0, height=58)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(10, 0))
        ctk.CTkLabel(
            title_row,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.colors["text"]
        ).pack(side="left")

        path_var = ctk.StringVar(value="")
        path_label = ctk.CTkLabel(
            header,
            textvariable=path_var,
            font=ctk.CTkFont(size=11),
            text_color=self.colors["muted"]
        )
        path_label.pack(anchor="w", padx=16, pady=(0, 8))

        body = ctk.CTkFrame(dialog, fg_color=self.colors["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.grid_columnconfigure(0, weight=5)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        tree_frame = tk.Frame(body, bg=self.colors["bg"])
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        preview_frame = ctk.CTkFrame(body, fg_color=self.colors["panel"])
        preview_frame.grid(row=0, column=1, sticky="nsew")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        tree = ttk.Treeview(tree_frame, show="tree", yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=tree.yview)
        tree_scroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        style = ttk.Style(tree_frame)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=self.colors["panel"],
            fieldbackground=self.colors["panel"],
            foreground=self.colors["text"],
            font=("Microsoft YaHei UI", 12),
            rowheight=26
        )
        style.map("Treeview", background=[("selected", self.colors["panel_2"])])

        ctk.CTkLabel(
            preview_frame,
            text="文件预览",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", padx=12, pady=(10, 6))

        preview_info = ctk.CTkLabel(
            preview_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.colors["muted"]
        )
        preview_info.pack(anchor="w", padx=12, pady=(0, 8))

        preview_box = ctk.CTkTextbox(
            preview_frame,
            font=ctk.CTkFont(size=12, family="Consolas"),
            fg_color="#FFFFFF",
            border_color=self.colors["border"],
            border_width=1,
            corner_radius=10,
            text_color=self.colors["text"]
        )
        preview_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        def has_subdirs(path: str) -> bool:
            try:
                for entry in os.scandir(path):
                    if entry.is_dir():
                        return True
            except Exception:
                return False
            return False

        def insert_node(parent, path: str):
            name = os.path.basename(path.rstrip("\\/")) or path
            node = tree.insert(parent, "end", text=name, values=[path])
            if has_subdirs(path):
                tree.insert(node, "end", text="")

        def populate_children(node):
            path = tree.item(node, "values")[0]
            children = tree.get_children(node)
            if len(children) == 1 and tree.item(children[0], "text") == "":
                tree.delete(children[0])
            try:
                for entry in sorted(os.scandir(path), key=lambda e: e.name.lower()):
                    if entry.is_dir():
                        insert_node(node, entry.path)
            except Exception:
                return

        def on_open(event):
            node = tree.focus()
            if node:
                populate_children(node)

        def list_files(path: str):
            try:
                folder = Path(path)
                if preview_formats:
                    files = FileScanner.scan_folder(folder, preview_formats)
                else:
                    files = [p for p in folder.iterdir() if p.is_file()]
                names = [p.name for p in files]
                preview_box.configure(state="normal")
                preview_box.delete("1.0", "end")
                preview_box.insert("end", "\n".join(names) if names else "未找到匹配的媒体文件")
                preview_box.configure(state="disabled")
                preview_info.configure(text=f"找到 {len(names)} 个文件")
            except Exception:
                preview_box.configure(state="normal")
                preview_box.delete("1.0", "end")
                preview_box.insert("end", "无法读取目录")
                preview_box.configure(state="disabled")
                preview_info.configure(text="")

        def on_select(_event=None):
            selected = tree.selection()
            if not selected:
                return
            values = tree.item(selected[0], "values")
            path = values[0] if values else ""
            if not path or not os.path.isdir(path):
                return
            path_var.set(path)
            list_files(path)

        tree.bind("<<TreeviewOpen>>", on_open)
        tree.bind("<<TreeviewSelect>>", on_select)

        def add_quick_links():
            home = os.path.expanduser("~")
            quick_paths = set()

            def add_quick_access():
                try:
                    import win32com.client  # type: ignore
                    shell = win32com.client.Dispatch("Shell.Application")
                    qa = shell.NameSpace("shell:::{679F85CB-0220-4080-B29B-5540CC05AAB6}")
                    if not qa:
                        return
                    parent = tree.insert("", "end", text="快速访问", values=[""])
                    for item in qa.Items():
                        try:
                            path = item.Path
                            if not path or not os.path.isdir(path):
                                continue
                            quick_paths.add(os.path.abspath(path))
                            node = tree.insert(parent, "end", text=item.Name, values=[path])
                            if has_subdirs(path):
                                tree.insert(node, "end", text="")
                        except Exception:
                            continue
                    tree.item(parent, open=True)
                except Exception:
                    return

            add_quick_access()

            one_drive_root = None
            try:
                for entry in os.listdir(home):
                    if entry.lower().startswith("onedrive"):
                        candidate = os.path.join(home, entry)
                        if os.path.isdir(candidate):
                            one_drive_root = candidate
                            break
            except Exception:
                one_drive_root = None

            quick = [
                ("桌面", os.path.join(home, "Desktop")),
                ("下载", os.path.join(home, "Downloads")),
                ("文档", os.path.join(home, "Documents")),
                ("音乐", os.path.join(home, "Music")),
                ("视频", os.path.join(home, "Videos")),
            ]
            if one_drive_root:
                quick.extend([
                    ("OneDrive 桌面", os.path.join(one_drive_root, "Desktop")),
                    ("OneDrive 文档", os.path.join(one_drive_root, "Documents")),
                ])
            for name, path in quick:
                if os.path.exists(path):
                    norm_path = os.path.abspath(path)
                    if norm_path in quick_paths:
                        continue
                    node = tree.insert("", "end", text=name, values=[path])
                    if has_subdirs(path):
                        tree.insert(node, "end", text="")

        def add_roots():
            add_quick_links()
            if os.name == "nt":
                for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        insert_node("", drive)
            else:
                insert_node("", "/")

        add_roots()

        def select_path(target: str):
            if not target:
                return
            target = os.path.abspath(target)
            parts = []
            if os.name == "nt":
                drive, rest = os.path.splitdrive(target)
                current = drive + "\\"
                parts.append(current)
                rest = rest.strip("\\")
                if rest:
                    parts.extend(rest.split("\\"))
            else:
                parts.append("/")
                rest = target.strip("/")
                if rest:
                    parts.extend(rest.split("/"))

            node = ""
            for idx, part in enumerate(parts):
                children = tree.get_children(node)
                next_node = None
                for child in children:
                    if tree.item(child, "text") == part or tree.item(child, "values")[0] == part:
                        next_node = child
                        break
                if next_node is None:
                    break
                node = next_node
                if idx < len(parts) - 1:
                    populate_children(node)
                    tree.item(node, open=True)
            if node:
                tree.selection_set(node)
                tree.see(node)
                on_select()

        if initial_dir and initial_dir not in (self._input_placeholder, self._output_placeholder):
            select_path(initial_dir)

        footer = ctk.CTkFrame(dialog, fg_color=self.colors["bg"])
        footer.pack(fill="x", padx=16, pady=(0, 16))

        result = {"path": None}

        def confirm():
            selected = tree.selection()
            if selected:
                result["path"] = tree.item(selected[0], "values")[0]
            dialog.destroy()

        def cancel():
            dialog.destroy()

        ctk.CTkButton(
            footer,
            text="使用此目录",
            command=confirm,
            width=120,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.colors["accent_2"],
            hover_color="#34505F",
            text_color="#FFFFFF",
            corner_radius=9
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            footer,
            text="取消",
            command=cancel,
            width=120,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.colors["button"],
            hover_color=self.colors["button_hover"],
            text_color="#FFFFFF",
            corner_radius=9
        ).pack(side="right")

        dialog.wait_window()
        return result["path"]

    def _toggle_format(self, fmt: str, var):
        """切换格式选择"""
        if var.get():
            self.selected_formats.add(fmt)
        else:
            self.selected_formats.discard(fmt)
        self._refresh_file_list()

    def _select_all_formats(self):
        """全选格式"""
        formats = ["m4s", "mp4", "m4a", "aac", "flv", "ts", "mkv", "webm", "mov", "avi", "mp3", "wav", "ogg", "opus"]
        self.selected_formats.clear()
        for fmt in formats:
            self.selected_formats.add(fmt)
        for fmt, (checkbox, var) in self.format_buttons.items():
            var.set(True)
        self._refresh_file_list()

    def _clear_all_formats(self):
        """全不选格式"""
        self.selected_formats.clear()
        for fmt, (checkbox, var) in self.format_buttons.items():
            var.set(False)
        self._refresh_file_list()

    def _refresh_file_list(self):
        """刷新文件列表"""
        input_dir = self.input_var.get().strip()
        if input_dir == self._input_placeholder:
            input_dir = ""
        if not input_dir:
            self._set_file_text("")
            return

        if not self.selected_formats:
            self._set_file_text("请先勾选文件格式")
            return

        folder = Path(input_dir)
        if not folder.exists():
            self._set_file_text("输入目录不存在")
            return

        try:
            from core import FileScanner
            scanner = FileScanner()
            files = scanner.scan_folder(folder, list(self.selected_formats))

            if not files:
                self._set_file_text("未找到匹配的文件")
                return

            file_list = "\n".join([f.name for f in files])
            self._set_file_text(file_list)
        except Exception as e:
            self._set_file_text(f"扫描失败: {e}")

    def _set_file_text(self, content):
        """设置文件列表文本"""
        self.file_text.configure(state="normal")
        self.file_text.delete("1.0", "end")
        self.file_text.insert("end", content)
        self.file_text.configure(state="disabled")

    def _start_merge(self):
        """开始合并"""
        input_dir = self.input_var.get().strip()
        output_dir = self.output_var.get().strip()
        if input_dir == self._input_placeholder:
            input_dir = ""
        if output_dir == self._output_placeholder:
            output_dir = ""

        if not input_dir:
            messagebox.showwarning("提示", "请选择输入目录")
            return

        if not output_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return

        if not self.selected_formats:
            messagebox.showwarning("提示", "请至少选择一种文件格式")
            return

        # 获取命名格式
        naming_format = self.naming_format.get()
        custom_template = None
        if naming_format == "custom":
            custom_template = self.custom_format_entry.get().strip()
            if not custom_template:
                messagebox.showwarning("提示", "请输入自定义命名格式")
                return

        # 立即显示开始日志
        self._log("\n" + "="*60)
        self._log("开始准备合并任务...")
        self._log(f"输入目录: {input_dir}")
        self._log(f"输出目录: {output_dir}")
        self._log(f"文件格式: {', '.join(sorted(self.selected_formats))}")

        # 禁用按钮，显示处理中
        self.start_btn.configure(state="disabled", text="扫描中...")
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.configure(text="正在扫描文件...")
        if hasattr(self, "progress_bar") and self.progress_bar:
            try:
                self.progress_bar.configure(mode="determinate")
            except Exception:
                pass
            self.progress_bar.set(0)

        # 在后台线程中准备和执行任务
        self.worker = threading.Thread(
            target=self._run_prepare_and_merge,
            args=(input_dir, output_dir, naming_format, custom_template),
            daemon=True
        )
        self.worker.start()

    def _run_prepare_and_merge(self, input_dir, output_dir, naming_format, custom_template):
        """在后台线程中准备并执行合并"""
        try:
            # 准备任务
            matcher_config = {
                "max_duration_diff": self.config.get("max_duration_diff", 5.0),
                "confidence_threshold": self.config.get("confidence_threshold", 0.6),
                "match_strategy": "duration"
            }
            self.current_task = self.merger.prepare_task(
                input_folders=[Path(input_dir)],
                extensions=list(self.selected_formats),
                output_dir=Path(output_dir),
                delete_sources=self.delete_check.get(),
                matcher_config=matcher_config,
                naming_format=naming_format,
                custom_template=custom_template,
                parallel_workers=self.config.get("parallel_workers", 1),
                copy_codec=self.config.get("copy_codec", True),
                resolve_safe_mode=self.config.get("resolve_safe_mode", True),
                retry_on_failure=self.config.get("retry_on_failure", True),
                max_retries=self.config.get("max_retries", 2)
            )

            if not self.current_task or not self.current_task.pairs:
                self.after(0, lambda: messagebox.showwarning("提示", "未找到可匹配的音视频文件"))
                self.after(0, lambda: self._on_error("未找到可匹配的音视频文件"))
                return

            # 显示匹配结果
            self.after(0, lambda: self._log(f"找到 {len(self.current_task.pairs)} 组文件："))
            for pair in self.current_task.pairs:
                self.after(0, lambda p=pair: self._log(f"  {p.video.name} + {p.audio.name}"))

            self.after(0, lambda: self._log("="*60 + "\n"))
            self.after(0, lambda: self.status_label.configure(text="开始合并..."))
            self.after(0, lambda: self.start_btn.configure(text="合并中..."))
            if hasattr(self, "progress_bar") and self.progress_bar:
                try:
                    self.progress_bar.configure(mode="indeterminate")
                    self.progress_bar.start()
                except Exception:
                    pass

            # 执行合并
            result_task = self.merger.execute_task(self.current_task)
            self.after(0, lambda: self._on_completed(result_task))

        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _format_time_ms(self, ms: int) -> str:
        if not ms or ms <= 0:
            return ""
        seconds = ms / 1000.0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"
        return f"{minutes:02d}:{secs:05.2f}"

    def _on_progress(self, current: int, total: int, result):
        """Progress callback"""
        label_merging = "\u5408\u5e76\u4e2d"
        label_speed = "\u901f\u5ea6"
        label_progress = "\u8fdb\u5ea6"
        label_overall_duration = "\u5a92\u4f53\u65f6\u957f"
        label_elapsed = "\u5b9e\u8017"
        log_interval = 3.0

        if isinstance(result, dict):
            phase = result.get("phase")
            speed = result.get("speed")
            status = result.get("progress")
            overall_out_time_ms = result.get("overall_out_time_ms")
            overall_total_ms = result.get("overall_total_ms")

            if phase == "start":
                if hasattr(self, "status_label") and self.status_label:
                    text = f"{label_merging} {current}/{total}"
                    overall_time_str = self._format_time_ms(int(overall_out_time_ms or 0))
                    overall_total_str = self._format_time_ms(int(overall_total_ms or 0))
                    if overall_time_str and overall_total_str:
                        text += f" {label_overall_duration} {overall_time_str}/{overall_total_str}"
                    self.after(0, lambda t=text: self.status_label.configure(text=t))
                return

            overall_time_str = self._format_time_ms(int(overall_out_time_ms or 0))
            overall_total_str = self._format_time_ms(int(overall_total_ms or 0))
            if hasattr(self, "status_label") and self.status_label:
                text = f"{label_merging} {current}/{total}"
                if overall_time_str and overall_total_str:
                    text += f" {label_overall_duration} {overall_time_str}/{overall_total_str}"
                if speed:
                    text += f" {label_speed} {speed}"
                if self._merge_start_time:
                    elapsed = time.time() - self._merge_start_time
                    text += f" {label_elapsed} {self._format_time_ms(int(elapsed * 1000))}"
                self.after(0, lambda t=text: self.status_label.configure(text=t))

            now = time.time()
            if now - self._last_progress_log >= log_interval or status == "end":
                log_parts = [f"{label_progress} {current}/{total}"]
                if overall_time_str and overall_total_str:
                    log_parts.append(f"{label_overall_duration} {overall_time_str}/{overall_total_str}")
                if speed:
                    log_parts.append(f"{label_speed} {speed}")
                if self._merge_start_time:
                    elapsed = time.time() - self._merge_start_time
                    log_parts.append(f"{label_elapsed} {self._format_time_ms(int(elapsed * 1000))}")
                log_msg = " ".join(log_parts)
                self.after(0, lambda m=log_msg: self._log(m))
                self._last_progress_log = now
            return

        if hasattr(self, "status_label") and self.status_label:
            self.after(0, lambda: self.status_label.configure(
                text=f"{label_merging} {current}/{total}"
            ))

        if result.success:
            self.after(0, lambda: self._log(f"[{current}/{total}] {result.output_path.name}"))
        else:
            self.after(0, lambda: self._log(f"[{current}/{total}] {result.error}"))


    def _on_completed(self, task):
        """完成回调"""
        self.start_btn.configure(state="normal", text="开始合并")
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.configure(text=f"完成: {task.success_count}/{task.total_count}")
        if hasattr(self, "progress_bar") and self.progress_bar:
            try:
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
            except Exception:
                pass
            self.progress_bar.set(1)

        success = task.success_count
        failed = task.failed_count
        total = task.total_count

        self._log(f"\n{'='*60}")
        self._log("合并完成！")
        self._log(f"成功: {success}/{total}")
        if failed > 0:
            self._log(f"失败: {failed}")
        self._log(f"耗时: {task.duration:.2f} 秒")
        self._log(f"{'='*60}\n")

        if hasattr(self, "status_label") and self.status_label:
            self.status_label.configure(text=f"完成: {success}/{total}")
        self._refresh_file_list()

        messagebox.showinfo(
            "完成",
            f"合并完成！\n\n成功: {success}/{total}\n失败: {failed}\n耗时: {task.duration:.2f} 秒"
        )

    def _on_error(self, error: str):
        """错误回调"""
        self.start_btn.configure(state="normal", text="开始合并")
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.configure(text="发生错误")
        if hasattr(self, "progress_bar") and self.progress_bar:
            try:
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
            except Exception:
                pass
            self.progress_bar.set(0)
        self._log(f"错误: {error}")
        self._log(f"{'='*60}\n")
        messagebox.showerror("错误", error)

    def _log(self, message: str):
        """输出日志"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def _load_settings(self):
        """加载设置"""
        if self.config.get('remember_dirs', True):
            self._set_path_label(self.input_var, self._input_placeholder, self.config.input_dir, self.input_label)
            self._set_path_label(self.output_var, self._output_placeholder, self.config.output_dir, self.output_label)

    def _set_path_label(self, var, placeholder: str, value: str, label):
        """路径展示标签赋值"""
        if value:
            var.set(value)
            label.configure(text_color=self.colors["text"])
        else:
            var.set(placeholder)
            label.configure(text_color=self.colors["muted"])

    def _save_settings(self):
        """保存设置"""
        input_dir = self.input_var.get()
        output_dir = self.output_var.get()
        if input_dir == self._input_placeholder:
            input_dir = ""
        if output_dir == self._output_placeholder:
            output_dir = ""
        self.config.update_dirs(input_dir, output_dir)

        self.config.update(
            delete_sources=self.delete_check.get(),
            remember_dirs=self.remember_check.get(),
            match_strategy="duration"
        )


def main():
    """主函数"""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
