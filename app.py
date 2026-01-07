#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI tool to merge split audio/video tracks for Bilibili/Douyin downloads.
Supports selecting file types and output folder, with optional source cleanup.
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


APP_TITLE = "分离音视频合成工具"
DEFAULT_EXTENSIONS = [
    "m4s",
    "mp4",
    "m4a",
    "aac",
    "flv",
    "f4v",
    "ts",
    "mkv",
    "webm",
    "mov",
    "avi",
    "mp3",
    "wav",
    "ogg",
    "opus",
]


def _candidate_base_dirs() -> List[Path]:
    bases: List[Path] = []
    if getattr(sys, "frozen", False):
        bases.append(Path(sys.executable).parent)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bases.append(Path(meipass))
    bases.append(Path(__file__).parent.resolve())
    return bases


def resolve_ffmpeg_bins() -> Tuple[str, str]:
    for base in _candidate_base_dirs():
        ffmpeg = base / "ffmpeg" / "bin" / "ffmpeg.exe"
        ffprobe = base / "ffmpeg" / "bin" / "ffprobe.exe"
        if ffmpeg.is_file() and ffprobe.is_file():
            return str(ffmpeg), str(ffprobe)
    return "ffmpeg", "ffprobe"


FFMPEG_BIN, FFPROBE_BIN = resolve_ffmpeg_bins()
CONFIG_PATH = Path(__file__).parent / "settings.json"


def _ffmpeg_ready() -> bool:
    if FFMPEG_BIN.lower().endswith("ffmpeg.exe"):
        return Path(FFMPEG_BIN).is_file() and Path(FFPROBE_BIN).is_file()
    return shutil.which(FFMPEG_BIN) is not None and shutil.which(FFPROBE_BIN) is not None


def _run_ffprobe(path: Path) -> Optional[dict]:
    cmd = [
        FFPROBE_BIN,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        if not result.stdout:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def _stream_info(path: Path) -> dict:
    data = _run_ffprobe(path)
    if not data:
        size_mb = path.stat().st_size / (1024 * 1024)
        return {
            "duration": 0.0,
            "has_video": size_mb > 50,
            "has_audio": size_mb <= 50,
            "width": 0,
            "height": 0,
        }

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


def _base_key(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"_bilibili(_\d+(_\d+)?)?$", "", stem, flags=re.I)
    stem = re.sub(r"(_audio|_video|_aud|_vid|_track\d+|_a\d+|_v\d+)$", "", stem, flags=re.I)
    return stem.strip() or stem


def _discover_files(folder: Path, extensions: Iterable[str]) -> List[Path]:
    exts = {f".{ext.lower().lstrip('.')}" for ext in extensions if ext.strip()}
    results: List[Path] = []
    for entry in folder.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() in exts:
            results.append(entry)
    return results


def _categorize_files(files: List[Path], logger) -> Tuple[List[dict], List[dict]]:
    videos: List[dict] = []
    audios: List[dict] = []
    for f in files:
        info = _stream_info(f)
        size_mb = f.stat().st_size / (1024 * 1024)
        item = {
            "path": f,
            "name": f.name,
            "base": _base_key(f.name),
            "duration": info["duration"],
            "width": info["width"],
            "height": info["height"],
            "size_mb": size_mb,
            "has_video": info["has_video"],
            "has_audio": info["has_audio"],
        }
        if info["has_video"] and not info["has_audio"]:
            videos.append(item)
            logger(f"[视频] {f.name} ({size_mb:.1f}MB, {info['width']}x{info['height']})")
        elif info["has_audio"] and not info["has_video"]:
            audios.append(item)
            logger(f"[音频] {f.name} ({size_mb:.1f}MB)")
        elif info["has_video"] and info["has_audio"]:
            logger(f"[跳过] 已包含音视频: {f.name}")
        else:
            logger(f"[跳过] 无法识别: {f.name}")
    return videos, audios


def _match_pairs(videos: List[dict], audios: List[dict], max_diff: float = 5.0) -> List[Tuple[dict, dict]]:
    matches: List[Tuple[dict, dict]] = []
    used_audio = set()

    videos_sorted = sorted(videos, key=lambda x: x.get("duration", 0), reverse=True)
    audios_sorted = sorted(audios, key=lambda x: x.get("duration", 0), reverse=True)

    for v in videos_sorted:
        if not audios_sorted:
            break

        base_matches = [a for a in audios_sorted if a["base"] == v["base"] and a["path"] not in used_audio]
        candidates = base_matches if base_matches else [a for a in audios_sorted if a["path"] not in used_audio]

        best_audio = None
        best_diff = None
        for a in candidates:
            if v["duration"] and a["duration"]:
                diff = abs(v["duration"] - a["duration"])
            else:
                diff = abs(v["size_mb"] - a["size_mb"])
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_audio = a

        if best_audio is None:
            continue

        if v["duration"] and best_audio["duration"] and best_diff is not None and best_diff > max_diff:
            continue

        matches.append((v, best_audio))
        used_audio.add(best_audio["path"])

    return matches


def _merge(video_path: Path, audio_path: Path, output_path: Path) -> bool:
    cmd = [FFMPEG_BIN, "-i", str(video_path), "-i", str(audio_path), "-c", "copy", "-y", str(output_path)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return result.returncode == 0 and output_path.exists()


class MergerApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("900x620")
        self.root.minsize(820, 560)

        self.queue: "queue.Queue[str]" = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.input_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value="")
        self.delete_var = tk.BooleanVar(value=True)
        self.remember_var = tk.BooleanVar(value=True)
        self.ext_vars = {ext: tk.BooleanVar(value=ext in ("m4s", "mp4", "m4a", "aac")) for ext in DEFAULT_EXTENSIONS}

        self._build_ui()
        self._load_settings()
        self.root.after(120, self._poll_queue)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(top, text=APP_TITLE, font=("Segoe UI", 16, "bold"))
        title.pack(anchor=tk.W, pady=(0, 8))

        path_frame = ttk.LabelFrame(top, text="路径设置", padding=10)
        path_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(path_frame, text="输入目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6), pady=4)
        ttk.Entry(path_frame, textvariable=self.input_var, width=60).grid(row=0, column=1, sticky=tk.W, padx=(0, 6))
        ttk.Button(path_frame, text="浏览...", command=self._choose_input).grid(row=0, column=2, sticky=tk.W)

        ttk.Label(path_frame, text="输出目录:").grid(row=1, column=0, sticky=tk.W, padx=(0, 6), pady=4)
        ttk.Entry(path_frame, textvariable=self.output_var, width=60).grid(row=1, column=1, sticky=tk.W, padx=(0, 6))
        ttk.Button(path_frame, text="浏览...", command=self._choose_output).grid(row=1, column=2, sticky=tk.W)

        options_frame = ttk.LabelFrame(top, text="文件格式", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))

        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X)

        for idx, ext in enumerate(DEFAULT_EXTENSIONS):
            col = idx % 8
            row = idx // 8
            cb = ttk.Checkbutton(
                format_frame,
                text=ext.upper(),
                variable=self.ext_vars[ext],
                command=self._refresh_file_list,
            )
            cb.grid(row=row, column=col, sticky=tk.W, padx=(0, 10), pady=2)

        btn_frame = ttk.Frame(options_frame)
        btn_frame.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btn_frame, text="全选", command=self._select_all).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="全不选", command=self._clear_all).pack(side=tk.LEFT, padx=(8, 0))

        action_frame = ttk.Frame(top)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(action_frame, text="合并成功后删除源文件", variable=self.delete_var).pack(side=tk.LEFT)
        ttk.Checkbutton(action_frame, text="记住输入/输出目录", variable=self.remember_var).pack(
            side=tk.LEFT, padx=(12, 0)
        )
        self.start_btn = ttk.Button(action_frame, text="开始合并", command=self._start_merge)
        self.start_btn.pack(side=tk.RIGHT)

        file_frame = ttk.LabelFrame(top, text="已匹配的文件", padding=10)
        file_frame.pack(fill=tk.BOTH, expand=False)
        self.file_list = tk.Listbox(file_frame, height=6)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_scroll = ttk.Scrollbar(file_frame, command=self.file_list.yview)
        file_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.configure(yscrollcommand=file_scroll.set)

        log_frame = ttk.LabelFrame(top, text="日志输出", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.log_text = tk.Text(log_frame, height=18, wrap="word")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)

    def _choose_input(self) -> None:
        if not self._collect_extensions():
            messagebox.showwarning("提示", "请先勾选文件格式。")
            return
        extensions = self._collect_extensions()
        patterns = [f"*.{ext.lower().lstrip('.')}" for ext in extensions]
        filetypes = [("媒体文件", ";".join(patterns)), ("所有文件", "*.*")]
        files = filedialog.askopenfilenames(title="选择输入目录（可多选，任意目标文件）", filetypes=filetypes)
        if files:
            folders = {Path(p).parent for p in files}
            folder = next(iter(folders))
            if len(folders) > 1:
                messagebox.showwarning("提示", "请选择同一目录下的文件。")
                return
            self.input_var.set(str(folder))
            self._refresh_file_list()
            self._save_settings()

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_var.set(path)
            self._save_settings()

    def _select_all(self) -> None:
        for var in self.ext_vars.values():
            var.set(True)
        self._refresh_file_list()

    def _clear_all(self) -> None:
        for var in self.ext_vars.values():
            var.set(False)
        self._refresh_file_list()

    def _refresh_file_list(self) -> None:
        self.file_list.delete(0, tk.END)
        input_dir = self.input_var.get().strip()
        if not input_dir:
            return
        extensions = self._collect_extensions()
        if not extensions:
            self.file_list.insert(tk.END, "请先勾选文件格式")
            return
        folder = Path(input_dir)
        if not folder.exists():
            self.file_list.insert(tk.END, "输入目录不存在")
            return
        files = _discover_files(folder, extensions)
        if not files:
            self.file_list.insert(tk.END, "未找到匹配的文件")
            return
        for f in files:
            self.file_list.insert(tk.END, f.name)

    def _log(self, message: str) -> None:
        self.queue.put(message)

    def _poll_queue(self) -> None:
        while not self.queue.empty():
            msg = self.queue.get_nowait()
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
        self.root.after(120, self._poll_queue)

    def _collect_extensions(self) -> List[str]:
        return [ext for ext, var in self.ext_vars.items() if var.get()]

    def _start_merge(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("提示", "任务正在进行中，请稍候。")
            return

        input_dir = self.input_var.get().strip()
        output_dir = self.output_var.get().strip()
        extensions = self._collect_extensions()
        if not input_dir:
            messagebox.showwarning("提示", "请选择输入目录。")
            return
        if not extensions:
            messagebox.showwarning("提示", "请先勾选文件格式。")
            return
        if not output_dir:
            messagebox.showwarning("提示", "请选择输出目录。")
            return
        if not extensions:
            messagebox.showwarning("提示", "请选择至少一种文件格式。")
            return

        self.log_text.delete("1.0", tk.END)
        self.start_btn.configure(state=tk.DISABLED)
        self._save_settings()
        self.worker = threading.Thread(
            target=self._run_merge,
            args=(Path(input_dir), Path(output_dir), extensions, self.delete_var.get()),
            daemon=True,
        )
        self.worker.start()

    def _set_start_state(self, enabled: bool) -> None:
        def _apply() -> None:
            state = tk.NORMAL if enabled else tk.DISABLED
            self.start_btn.configure(state=state)

        self.root.after(0, _apply)

    def _run_merge(self, input_dir: Path, output_dir: Path, extensions: List[str], delete_sources: bool) -> None:
        try:
            if not _ffmpeg_ready():
                self._log("未找到 ffmpeg/ffprobe，请确保 ffmpeg 已放在 ffmpeg/bin 或已加入 PATH。")
                return
            output_dir.mkdir(parents=True, exist_ok=True)

            if not input_dir.exists():
                self._log(f"输入目录不存在: {input_dir}")
                return
            self._log(f"输入目录: {input_dir}")
            self._log(f"输出目录: {output_dir}")
            self._log(f"文件格式: {', '.join(sorted(set(extensions)))}")
            self._log("")

            files = _discover_files(input_dir, extensions)
            if not files:
                self._log("未找到符合格式的文件。")
                return

            self._log(f"扫描到 {len(files)} 个文件，开始识别...")
            videos, audios = _categorize_files(files, self._log)

            if not videos:
                self._log("未找到视频文件，结束。")
                return
            if not audios:
                self._log("未找到音频文件，结束。")
                return

            self._log("")
            self._log("开始匹配音视频...")
            matches = _match_pairs(videos, audios)
            self._log(f"匹配到 {len(matches)} 组。")
            self._log("")

            if not matches:
                return

            success = 0
            deleted = 0
            for idx, (video, audio) in enumerate(matches, 1):
                base_name = video["base"] or Path(video["name"]).stem
                output_path = output_dir / f"{base_name}.mp4"
                counter = 1
                while output_path.exists():
                    output_path = output_dir / f"{base_name}_{counter}.mp4"
                    counter += 1

                self._log(f"[{idx}/{len(matches)}] 合并: {output_path.name}")
                self._log(f"  视频: {video['name']}")
                self._log(f"  音频: {audio['name']}")

                if _merge(video["path"], audio["path"], output_path):
                    success += 1
                    self._log("  成功")
                    if delete_sources:
                        try:
                            os.remove(video["path"])
                            os.remove(audio["path"])
                            deleted += 2
                            self._log("  已删除源文件")
                        except Exception as exc:
                            self._log(f"  删除失败: {exc}")
                else:
                    self._log("  失败")
                self._log("")

            self._log("=" * 40)
            self._log(f"完成: {success}/{len(matches)} 成功")
            if delete_sources and deleted:
                self._log(f"已删除源文件: {deleted} 个")
            self._log("=" * 40)
        finally:
            self._set_start_state(True)

    def run(self) -> None:
        self.root.mainloop()

    def _load_settings(self) -> None:
        try:
            if not CONFIG_PATH.exists():
                return
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            self.remember_var.set(bool(data.get("remember", True)))
            if self.remember_var.get():
                self.input_var.set(data.get("input_dir", ""))
                self.output_var.set(data.get("output_dir", ""))
            self.delete_var.set(bool(data.get("delete_sources", True)))
        except Exception:
            pass

    def _save_settings(self) -> None:
        if not self.remember_var.get():
            data = {"remember": False, "delete_sources": self.delete_var.get()}
        else:
            data = {
                "remember": True,
                "input_dir": self.input_var.get().strip(),
                "output_dir": self.output_var.get().strip(),
                "delete_sources": self.delete_var.get(),
            }
        try:
            CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


def main() -> None:
    MergerApp().run()


if __name__ == "__main__":
    main()
