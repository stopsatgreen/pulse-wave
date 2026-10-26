#!/usr/bin/env python3
"""
PulseWave Audio Visualizer & Video Studio
Native macOS Desktop Application
Packaged for PyInstaller (macOS .app bundle)
"""

import sys
import os

# --- Add standard macOS binary directories to PATH ---
# macOS GUI bundles do not load the shell profile.
# This ensures Python and child processes can locate ffmpeg.
common_paths = [
    "/opt/homebrew/bin",  # Homebrew on Apple Silicon
    "/usr/local/bin",     # Homebrew on Intel
    os.path.expanduser("~/bin"),
    os.path.expanduser("~/.local/bin"),
]

current_path = os.environ.get("PATH", "")
paths_to_add = [p for p in common_paths if os.path.isdir(p) and p not in current_path]

if paths_to_add:
    os.environ["PATH"] = ":".join(paths_to_add) + ":" + current_path
# -----------------------------------------------------

import threading
import time
import subprocess
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk, ImageDraw

from audio_engine import AudioEngine
from video_renderer import VideoRenderer, VISUALIZER_STYLES

class ActionButton(tk.Label):
    """
    High-contrast, cross-platform interactive button built on tk.Label.
    Solves macOS Aqua Tkinter limitations where native NSButton ignores custom
    background colors and renders low-contrast white/silver boxes with faint text.
    """
    def __init__(
        self,
        master,
        text="",
        command=None,
        bg="#0284C7",
        fg="#FFFFFF",
        hover_bg=None,
        active_bg=None,
        disabled_bg="#1E293B",
        disabled_fg="#64748B",
        font=("Helvetica", 10, "bold"),
        padx=14,
        pady=8,
        cursor="hand2",
        **kwargs
    ):
        self.command = command
        self.default_bg = bg
        self.default_fg = fg
        self.hover_bg = hover_bg or bg
        self.active_bg = active_bg or hover_bg or bg
        self.disabled_bg = disabled_bg
        self.disabled_fg = disabled_fg
        self._state = "normal"
        self._pressed = False

        super().__init__(
            master,
            text=text,
            bg=bg,
            fg=fg,
            font=font,
            padx=padx,
            pady=pady,
            cursor=cursor,
            relief="flat",
            takefocus=True,
            **kwargs
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<KeyPress-Return>", self._on_key_press)
        self.bind("<KeyRelease-Return>", self._on_key_release)
        self.bind("<KeyPress-space>", self._on_key_press)
        self.bind("<KeyRelease-space>", self._on_key_release)

    def _on_enter(self, event):
        if self._state == "normal":
            super().configure(bg=self.active_bg if self._pressed else self.hover_bg)

    def _on_leave(self, event):
        if self._state == "normal":
            super().configure(bg=self.default_bg)

    def _on_press(self, event):
        if self._state == "normal":
            self._pressed = True
            super().configure(bg=self.active_bg)

    def _on_release(self, event):
        if self._state == "normal" and self._pressed:
            self._pressed = False
            if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
                super().configure(bg=self.hover_bg)
                if self.command:
                    self.command()
            else:
                super().configure(bg=self.default_bg)

    def _on_focus_in(self, event):
        if self._state == "normal":
            self.configure(highlightthickness=2, highlightbackground="#38BDF8", highlightcolor="#38BDF8")

    def _on_focus_out(self, event):
        self.configure(highlightthickness=0)

    def _on_key_press(self, event):
        if self._state == "normal":
            super().configure(bg=self.active_bg)

    def _on_key_release(self, event):
        if self._state == "normal":
            super().configure(bg=self.default_bg)
            if self.command:
                self.command()

    def configure(self, **kwargs):
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            if self._state == "disabled":
                self._pressed = False
                super().configure(
                    bg=self.disabled_bg,
                    fg=self.disabled_fg,
                    cursor="arrow",
                    highlightthickness=0
                )
            else:
                super().configure(
                    bg=self.default_bg,
                    fg=self.default_fg,
                    cursor="hand2"
                )
        if "hover_bg" in kwargs:
            self.hover_bg = kwargs.pop("hover_bg")
        if "active_bg" in kwargs:
            self.active_bg = kwargs.pop("active_bg")
        if "disabled_bg" in kwargs:
            self.disabled_bg = kwargs.pop("disabled_bg")
        if "disabled_fg" in kwargs:
            self.disabled_fg = kwargs.pop("disabled_fg")
        if "bg" in kwargs:
            self.default_bg = kwargs["bg"]
        if "background" in kwargs:
            self.default_bg = kwargs["background"]
        if "fg" in kwargs:
            self.default_fg = kwargs["fg"]
        if "foreground" in kwargs:
            self.default_fg = kwargs["foreground"]
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        super().configure(**kwargs)

    config = configure

    def cget(self, key):
        if key == "state":
            return self._state
        return super().cget(key)

    __getitem__ = cget

class AudioPlaybackController:
    """
    Handles real-time audio playback preview on macOS.
    Prefers ffplay for precise seeking support (-ss), with fallback to afplay.
    """
    def __init__(self):
        self.proc = None
        self.is_playing = False
        self.muted = False

    def play(self, audio_path, start_seconds=0.0):
        self.stop()
        if not audio_path or self.muted or not os.path.exists(audio_path):
            return

        # Prefer ffplay for accurate seeking (-ss) and silent/headless audio playback
        try:
            cmd = [
                "ffplay", "-nodisp", "-autoexit",
                "-ss", f"{max(0.0, start_seconds):.2f}",
                "-loglevel", "quiet",
                audio_path
            ]
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.is_playing = True
            return
        except Exception:
            pass

        # Fallback to macOS native afplay
        try:
            cmd = ["afplay", audio_path]
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.is_playing = True
        except Exception:
            pass

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=0.15)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
        self.is_playing = False

    def set_muted(self, muted, audio_path=None, current_time=0.0, playing=False):
        self.muted = muted
        if muted:
            self.stop()
        elif audio_path and playing:
            self.play(audio_path, current_time)

class PulseWaveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PulseWave - Audio Visualizer Studio")
        self.root.geometry("1150x800")
        self.root.minsize(1000, 720)
        self.root.configure(bg="#0B0F19")

        # Application state
        self.audio_path = None
        self.audio_engine = AudioEngine()
        self.video_renderer = VideoRenderer()
        self.is_rendering = False
        self.preview_image = None
        self.bg_image_path = None
        self.bg_image_pil = None
        self._preview_background_key = None
        self._preview_background = None
        self._audio_load_results = queue.Queue()
        self._audio_load_generation = 0

        # Real-time preview animation & playback state
        self.audio_player = AudioPlaybackController()
        self.is_playing = False
        self.is_scrubbing = False
        self.playback_start_clock = 0.0
        self.playback_start_offset = 0.0
        self.current_preview_timestamp = 0.0
        self.app_start_time = time.monotonic()
        self.var_seek = tk.DoubleVar(value=0.0)
        
        # Style variables
        self.var_style = tk.StringVar(value="circular-spectrum")
        self.var_aspect = tk.StringVar(value="16:9")
        self.var_title = tk.StringVar(value="My Audio Track")
        self.var_artist = tk.StringVar(value="PulseWave Artist")
        self.var_fps = tk.IntVar(value=30)
        self.var_bars = tk.IntVar(value=64)
        self.var_theme = tk.StringVar(value="Cyber Neon (Cyan & Pink)")
        self.var_particles = tk.BooleanVar(value=True)
        self.var_text_overlay = tk.BooleanVar(value=True)
        self.var_text_scale = tk.DoubleVar(value=1.0)
        self.var_use_bg_image = tk.BooleanVar(value=False)

        self._setup_ui()

    def _setup_ui(self):
        # Header / Top bar
        header = tk.Frame(self.root, bg="#111827", height=54)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        brand_lbl = tk.Label(
            header,
            text="PulseWave Audio Visualizer",
            font=("Helvetica", 16, "bold"),
            fg="#38BDF8",
            bg="#111827",
            padx=18
        )
        brand_lbl.pack(side="left")

        sub_lbl = tk.Label(
            header,
            text="macOS Video Exporter",
            font=("Helvetica", 11),
            fg="#94A3B8",
            bg="#111827"
        )
        sub_lbl.pack(side="left")

        # Main horizontal split container
        main_paned = tk.PanedWindow(self.root, orient="horizontal", bg="#0B0F19", bd=0, sashwidth=4)
        main_paned.pack(fill="both", expand=True, padx=14, pady=14)

        # Left Column: Controls & Configuration
        left_frame = tk.Frame(main_paned, bg="#131B2E", padx=14, pady=12)
        main_paned.add(left_frame, minsize=400, width=430)

        # Right Column: Visualizer Preview & Timeline
        right_frame = tk.Frame(main_paned, bg="#0B0F19")
        main_paned.add(right_frame, minsize=500)

        self._build_left_controls(left_frame)
        self._build_right_preview(right_frame)

        # Handle window close cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_left_controls(self, parent):
        # 1. Audio File Section
        file_box = tk.LabelFrame(
            parent,
            text=" 1. AUDIO SOURCE ",
            font=("Helvetica", 10, "bold"),
            fg="#38BDF8",
            bg="#131B2E",
            padx=10,
            pady=8
        )
        file_box.pack(fill="x", pady=(0, 8))

        self.lbl_filename = tk.Label(
            file_box,
            text="No audio file loaded (MP3, WAV, FLAC, M4A)",
            fg="#94A3B8",
            bg="#131B2E",
            anchor="w",
            font=("Helvetica", 10)
        )
        self.lbl_filename.pack(fill="x", pady=(0, 6))

        btn_row = tk.Frame(file_box, bg="#131B2E")
        btn_row.pack(fill="x")

        btn_choose = ActionButton(
            btn_row,
            text="Choose Audio File...",
            command=self.open_audio_file,
            bg="#0284C7",
            fg="#FFFFFF",
            hover_bg="#0369A1",
            active_bg="#075985",
            padx=14,
            pady=7,
            font=("Helvetica", 10, "bold"),
            cursor="hand2"
        )
        btn_choose.pack(side="left")

        self.lbl_duration = tk.Label(
            btn_row,
            text="",
            fg="#38BDF8",
            bg="#131B2E",
            font=("Helvetica", 9, "bold"),
            padx=10
        )
        self.lbl_duration.pack(side="left")

        # 2. Visualizer Style Section
        style_box = tk.LabelFrame(
            parent,
            text=" 2. VISUALIZER STYLE & ASPECT RATIO ",
            font=("Helvetica", 10, "bold"),
            fg="#38BDF8",
            bg="#131B2E",
            padx=10,
            pady=8
        )
        style_box.pack(fill="x", pady=(0, 8))

        tk.Label(style_box, text="Preset Style:", fg="#E2E8F0", bg="#131B2E", font=("Helvetica", 9)).pack(anchor="w")
        cb_style = ttk.Combobox(
            style_box,
            textvariable=self.var_style,
            values=list(VISUALIZER_STYLES.keys()),
            state="readonly"
        )
        cb_style.pack(fill="x", pady=(1, 4))
        cb_style.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        tk.Label(style_box, text="Color Theme:", fg="#E2E8F0", bg="#131B2E", font=("Helvetica", 9)).pack(anchor="w")
        cb_theme = ttk.Combobox(
            style_box,
            textvariable=self.var_theme,
            values=[
                "Cyber Neon (Cyan & Pink)",
                "Sunset Glow (Violet & Gold)",
                "Matrix Acid (Emerald & Lime)",
                "Electric Blue & White",
                "Monochrome Frost"
            ],
            state="readonly"
        )
        cb_theme.pack(fill="x", pady=(1, 4))
        cb_theme.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        aspect_row = tk.Frame(style_box, bg="#131B2E")
        aspect_row.pack(fill="x", pady=(1, 2))
        tk.Label(aspect_row, text="Aspect Ratio:", fg="#E2E8F0", bg="#131B2E", font=("Helvetica", 9)).pack(side="left")
        
        for asp in ["16:9 (Landscape)", "9:16 (Shorts/TikTok)", "1:1 (Square)"]:
            r = tk.Radiobutton(
                aspect_row,
                text=asp.split()[0],
                value=asp.split()[0],
                variable=self.var_aspect,
                fg="#E2E8F0",
                bg="#131B2E",
                selectcolor="#0B0F19",
                command=self.update_preview
            )
            r.pack(side="left", padx=4)

        # 3. Typography Overlays
        text_box = tk.LabelFrame(
            parent,
            text=" 3. TEXT & TITLE OVERLAYS ",
            font=("Helvetica", 10, "bold"),
            fg="#38BDF8",
            bg="#131B2E",
            padx=10,
            pady=8
        )
        text_box.pack(fill="x", pady=(0, 8))

        chk_text = tk.Checkbutton(
            text_box,
            text="Render Track Title & Artist Overlay",
            variable=self.var_text_overlay,
            fg="#E2E8F0",
            bg="#131B2E",
            selectcolor="#0B0F19",
            command=self.update_preview
        )
        chk_text.pack(anchor="w", pady=(0, 4))

        tk.Label(text_box, text="Track Title:", fg="#94A3B8", bg="#131B2E", font=("Helvetica", 9)).pack(anchor="w")
        entry_title = tk.Entry(text_box, textvariable=self.var_title, bg="#0B0F19", fg="white", insertbackground="white", bd=1)
        entry_title.pack(fill="x", pady=(2, 4))
        entry_title.bind("<KeyRelease>", lambda e: self.update_preview())

        tk.Label(text_box, text="Artist / Creator:", fg="#94A3B8", bg="#131B2E", font=("Helvetica", 9)).pack(anchor="w")
        entry_artist = tk.Entry(text_box, textvariable=self.var_artist, bg="#0B0F19", fg="white", insertbackground="white", bd=1)
        entry_artist.pack(fill="x", pady=(2, 4))
        entry_artist.bind("<KeyRelease>", lambda e: self.update_preview())

        # Scale text size slider
        scale_row = tk.Frame(text_box, bg="#131B2E")
        scale_row.pack(fill="x", pady=(4, 2))

        lbl_scale_title = tk.Label(
            scale_row,
            text="Scale text size:",
            fg="#94A3B8",
            bg="#131B2E",
            font=("Helvetica", 9)
        )
        lbl_scale_title.pack(side="left")

        self.lbl_scale_val = tk.Label(
            scale_row,
            text="1.0x",
            fg="#38BDF8",
            bg="#131B2E",
            font=("Helvetica", 9, "bold"),
            width=5
        )
        self.lbl_scale_val.pack(side="right")

        self.slider_text_scale = tk.Scale(
            scale_row,
            from_=1.0,
            to=3.5,
            resolution=0.1,
            orient="horizontal",
            variable=self.var_text_scale,
            showvalue=False,
            bg="#131B2E",
            fg="#E2E8F0",
            troughcolor="#0B0F19",
            activebackground="#38BDF8",
            highlightthickness=0,
            bd=0,
            command=self._on_scale_slider_change
        )
        self.slider_text_scale.pack(fill="x", expand=True, padx=6)

        # 4. Background Image Section
        bg_box = tk.LabelFrame(
            parent,
            text=" 4. BACKGROUND IMAGE ",
            font=("Helvetica", 10, "bold"),
            fg="#38BDF8",
            bg="#131B2E",
            padx=10,
            pady=8
        )
        bg_box.pack(fill="x", pady=(0, 8))

        chk_bg = tk.Checkbutton(
            bg_box,
            text="Use Background Image",
            variable=self.var_use_bg_image,
            fg="#E2E8F0",
            bg="#131B2E",
            selectcolor="#0B0F19",
            command=self._on_toggle_bg_image
        )
        chk_bg.pack(anchor="w", pady=(0, 4))

        bg_btn_row = tk.Frame(bg_box, bg="#131B2E")
        bg_btn_row.pack(fill="x")

        btn_choose_bg = ActionButton(
            bg_btn_row,
            text="Choose Image...",
            command=self.open_bg_image_file,
            bg="#0284C7",
            fg="#FFFFFF",
            hover_bg="#0369A1",
            active_bg="#075985",
            padx=10,
            pady=5,
            font=("Helvetica", 9, "bold"),
            cursor="hand2"
        )
        btn_choose_bg.pack(side="left")

        self.lbl_bg_filename = tk.Label(
            bg_btn_row,
            text="No image selected",
            fg="#94A3B8",
            bg="#131B2E",
            font=("Helvetica", 9),
            anchor="w",
            padx=8
        )
        self.lbl_bg_filename.pack(side="left", fill="x", expand=True)

        # 5. Export Button & Status
        export_box = tk.Frame(parent, bg="#131B2E")
        export_box.pack(fill="x", side="bottom", pady=4)

        self.btn_export = ActionButton(
            export_box,
            text="Render & Export Video (.mp4)",
            command=self.start_video_export,
            bg="#059669",
            fg="#FFFFFF",
            hover_bg="#047857",
            active_bg="#065F46",
            disabled_bg="#1E293B",
            disabled_fg="#94A3B8",
            padx=14,
            pady=8,
            font=("Helvetica", 11, "bold"),
            cursor="hand2"
        )
        self.btn_export.pack(fill="x")

        self.progress_bar = ttk.Progressbar(export_box, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", pady=(5, 3))

        self.lbl_progress = tk.Label(
            export_box,
            text="Ready to render",
            fg="#94A3B8",
            bg="#131B2E",
            font=("Helvetica", 9)
        )
        self.lbl_progress.pack(fill="x")

    def _build_right_preview(self, parent):
        # Preview Header
        prev_head = tk.Frame(parent, bg="#0B0F19")
        prev_head.pack(fill="x", pady=(0, 6))

        title_badge_frame = tk.Frame(prev_head, bg="#0B0F19")
        title_badge_frame.pack(side="left")

        tk.Label(
            title_badge_frame,
            text="Visualizer Real-Time Preview",
            font=("Helvetica", 12, "bold"),
            fg="#F8FAFC",
            bg="#0B0F19"
        ).pack(side="left")

        self.lbl_live_badge = tk.Label(
            title_badge_frame,
            text="● LIVE",
            font=("Helvetica", 8, "bold"),
            fg="#34D399",
            bg="#111827",
            padx=7,
            pady=2
        )
        self.lbl_live_badge.pack(side="left", padx=10)

        # Controls on the right of header
        btn_controls_frame = tk.Frame(prev_head, bg="#0B0F19")
        btn_controls_frame.pack(side="right")

        self.btn_mute = ActionButton(
            btn_controls_frame,
            text="🔊 Audio On",
            command=self.toggle_mute,
            bg="#1E293B",
            fg="#94A3B8",
            hover_bg="#334155",
            active_bg="#475569",
            padx=10,
            pady=4,
            font=("Helvetica", 9, "bold")
        )
        self.btn_mute.pack(side="left", padx=4)

        self.btn_play_pause = ActionButton(
            btn_controls_frame,
            text="⏸ Pause",
            command=self.toggle_play_pause,
            bg="#0284C7",
            fg="#FFFFFF",
            hover_bg="#0369A1",
            active_bg="#075985",
            padx=12,
            pady=4,
            font=("Helvetica", 9, "bold")
        )
        self.btn_play_pause.pack(side="left", padx=4)

        # Canvas for rendering preview frames
        self.canvas_preview = tk.Canvas(parent, bg="#000000", highlightthickness=1, highlightbackground="#1E293B")
        self.canvas_preview.pack(fill="both", expand=True)
        self.canvas_preview.bind("<Configure>", lambda e: self.render_current_frame())

        # Timeline Scrubber Bar below canvas
        timeline_bar = tk.Frame(parent, bg="#111827", padx=10, pady=4)
        timeline_bar.pack(fill="x", pady=(6, 0))

        btn_restart = ActionButton(
            timeline_bar,
            text="⏮",
            command=self.restart_playback,
            bg="#1E293B",
            fg="#E2E8F0",
            hover_bg="#334155",
            active_bg="#475569",
            padx=8,
            pady=2,
            font=("Helvetica", 9, "bold")
        )
        btn_restart.pack(side="left", padx=(0, 6))

        self.lbl_time_cur = tk.Label(
            timeline_bar,
            text="00:00",
            fg="#38BDF8",
            bg="#111827",
            font=("Helvetica", 9, "bold"),
            width=5
        )
        self.lbl_time_cur.pack(side="left")

        self.slider_seek = tk.Scale(
            timeline_bar,
            from_=0.0,
            to=30.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.var_seek,
            showvalue=False,
            bg="#111827",
            fg="#E2E8F0",
            troughcolor="#0B0F19",
            activebackground="#38BDF8",
            highlightthickness=0,
            bd=0
        )
        self.slider_seek.pack(side="left", fill="x", expand=True, padx=8)

        # Scrubbing events
        self.slider_seek.bind("<Button-1>", self._on_scrub_start)
        self.slider_seek.bind("<B1-Motion>", self._on_scrub_move)
        self.slider_seek.bind("<ButtonRelease-1>", self._on_scrub_end)

        self.lbl_time_total = tk.Label(
            timeline_bar,
            text="Demo",
            fg="#94A3B8",
            bg="#111827",
            font=("Helvetica", 9),
            width=5
        )
        self.lbl_time_total.pack(side="right")

        # Start live preview loop immediately
        self.is_playing = True
        self.playback_start_clock = time.monotonic()
        self.playback_start_offset = 0.0

        # Launch the live animation tick loop
        self.root.after(50, self._animation_tick)

    def _animation_tick(self):
        self._process_audio_load_results()
        try:
            if not self.is_rendering:
                if self.is_playing:
                    if self.audio_engine and self.audio_engine.is_loaded:
                        dur = self.audio_engine.get_duration()
                        elapsed = time.monotonic() - self.playback_start_clock
                        cur = self.playback_start_offset + elapsed

                        if cur >= dur:
                            # Seamless loop
                            cur = 0.0
                            self.playback_start_clock = time.monotonic()
                            self.playback_start_offset = 0.0
                            if self.audio_path:
                                self.audio_player.play(self.audio_path, 0.0)

                        if not self.is_scrubbing:
                            self.current_preview_timestamp = cur
                            self.var_seek.set(cur)
                            mins = int(cur // 60)
                            secs = int(cur % 60)
                            self.lbl_time_cur.config(text=f"{mins:02d}:{secs:02d}")

                        self.render_current_frame()

                    else:
                        # Demo synthetic animation
                        elapsed = time.monotonic() - self.playback_start_clock
                        cur = (self.playback_start_offset + elapsed) % 30.0
                        if not self.is_scrubbing:
                            self.current_preview_timestamp = cur
                            self.var_seek.set(cur)
                            secs = int(cur % 60)
                            self.lbl_time_cur.config(text=f"00:{secs:02d}")

                        self.render_current_frame()

        except Exception as exc:
            self.root.report_callback_exception(type(exc), exc, exc.__traceback__)

        # Schedule next frame (~30 FPS)
        self.root.after(33, self._animation_tick)

    def _on_scrub_start(self, event):
        self.is_scrubbing = True

    def _on_scrub_move(self, event):
        self.is_scrubbing = True
        seek_val = self.var_seek.get()
        self.current_preview_timestamp = seek_val
        mins = int(seek_val // 60)
        secs = int(seek_val % 60)
        self.lbl_time_cur.config(text=f"{mins:02d}:{secs:02d}")
        self.render_current_frame()

    def _on_scrub_end(self, event):
        self.is_scrubbing = False
        seek_val = self.var_seek.get()
        self.seek_to(seek_val)

    def seek_to(self, target_time):
        dur = self.audio_engine.get_duration() if self.audio_engine.is_loaded else 30.0
        target_time = max(0.0, min(target_time, dur))
        self.current_preview_timestamp = target_time
        self.var_seek.set(target_time)
        mins = int(target_time // 60)
        secs = int(target_time % 60)
        self.lbl_time_cur.config(text=f"{mins:02d}:{secs:02d}")

        if self.is_playing:
            self.playback_start_clock = time.monotonic()
            self.playback_start_offset = target_time
            if self.audio_path and self.audio_engine.is_loaded:
                self.audio_player.play(self.audio_path, target_time)
        self.render_current_frame()

    def toggle_play_pause(self):
        if self.is_playing:
            self.pause_preview()
        else:
            self.play_preview()

    def play_preview(self, seek_to=None):
        self.is_playing = True
        self.lbl_live_badge.config(text="● LIVE", fg="#34D399")
        self.btn_play_pause.config(text="⏸ Pause", bg="#0284C7", hover_bg="#0369A1")

        if seek_to is not None:
            self.current_preview_timestamp = seek_to
            self.playback_start_offset = seek_to
        else:
            self.playback_start_offset = self.current_preview_timestamp

        self.playback_start_clock = time.monotonic()

        if self.audio_path and self.audio_engine.is_loaded:
            self.audio_player.play(self.audio_path, self.playback_start_offset)

    def pause_preview(self):
        self.is_playing = False
        self.lbl_live_badge.config(text="❚❚ PAUSED", fg="#94A3B8")
        self.btn_play_pause.config(text="▶ Play", bg="#059669", hover_bg="#047857")
        self.audio_player.stop()

    def restart_playback(self):
        self.seek_to(0.0)
        if not self.is_playing:
            self.play_preview(seek_to=0.0)

    def toggle_mute(self):
        is_muted = not self.audio_player.muted
        self.audio_player.set_muted(is_muted, self.audio_path, self.current_preview_timestamp, self.is_playing)
        if is_muted:
            self.btn_mute.config(text="🔇 Muted", fg="#EF4444")
        else:
            self.btn_mute.config(text="🔊 Audio On", fg="#94A3B8")

    def open_audio_file(self):
        filetypes = [
            ("Audio Files", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac"),
            ("All Files", "*.*")
        ]
        chosen = filedialog.askopenfilename(title="Select Audio File", filetypes=filetypes)
        if chosen:
            self.audio_player.stop()
            self.audio_path = None
            self.audio_engine = AudioEngine()
            self._audio_load_generation += 1
            generation = self._audio_load_generation
            fname = os.path.basename(chosen)
            self.lbl_filename.config(text=fname)
            self.var_title.set(os.path.splitext(fname)[0])
            self.lbl_progress.config(text="Analyzing audio frequencies...")
            self.btn_export.config(state="disabled")

            # Analyze audio in background thread
            threading.Thread(target=self._load_and_analyze_audio, args=(chosen, generation), daemon=True).start()

    def _load_and_analyze_audio(self, path, generation):
        try:
            engine = AudioEngine()
            engine.load_file(path)
            self._audio_load_results.put((generation, path, engine, None))
        except Exception as e:
            self._audio_load_results.put((generation, path, None, str(e)))

    def _process_audio_load_results(self):
        while True:
            try:
                generation, path, engine, error = self._audio_load_results.get_nowait()
            except queue.Empty:
                return
            if generation != self._audio_load_generation:
                continue
            self.btn_export.config(state="normal")
            if error:
                self.lbl_progress.config(text="Audio load error.")
                messagebox.showerror("Audio Load Error", f"Failed to load audio: {error}")
                continue
            self.audio_path = path
            self.audio_engine = engine
            dur = engine.get_duration()
            mins, secs = int(dur // 60), int(dur % 60)
            self.lbl_duration.config(text=f"{mins:02d}:{secs:02d}")
            self.slider_seek.config(to=dur)
            self.lbl_time_total.config(text=f"{mins:02d}:{secs:02d}")
            self.lbl_progress.config(text="Audio analysis complete. Ready to export.")
            self.play_preview(seek_to=0.0)

    def _on_scale_slider_change(self, val):
        try:
            v = float(val)
            self.lbl_scale_val.config(text=f"{v:.1f}x")
        except Exception:
            pass
        self.render_current_frame()

    def _on_toggle_bg_image(self):
        if self.var_use_bg_image.get() and not self.bg_image_path:
            self.open_bg_image_file()
        else:
            self.render_current_frame()

    def open_bg_image_file(self):
        filetypes = [
            ("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff"),
            ("All Files", "*.*")
        ]
        chosen = filedialog.askopenfilename(title="Select Background Image", filetypes=filetypes)
        if chosen:
            self.bg_image_path = chosen
            try:
                self.bg_image_pil = Image.open(chosen).convert("RGB")
                fname = os.path.basename(chosen)
                self.lbl_bg_filename.config(text=fname)
                self.var_use_bg_image.set(True)
                self.render_current_frame()
            except Exception as e:
                messagebox.showerror("Image Load Error", f"Failed to load image: {str(e)}")

    def update_preview(self):
        self.render_current_frame()

    def render_current_frame(self):
        width = self.canvas_preview.winfo_width()
        height = self.canvas_preview.winfo_height()
        if width <= 10 or height <= 10:
            width, height = 640, 360

        # Match the selected output aspect ratio within the preview canvas.
        ratio = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1}.get(self.var_aspect.get(), 16 / 9)
        if width / height > ratio:
            frame_width, frame_height = max(1, int(height * ratio)), height
        else:
            frame_width, frame_height = width, max(1, int(width / ratio))

        background = None
        if self.var_use_bg_image.get() and self.bg_image_pil is not None:
            key = (id(self.bg_image_pil), frame_width, frame_height)
            if key != self._preview_background_key:
                self._preview_background = self.video_renderer.prepare_background_image(
                    self.bg_image_pil, frame_width, frame_height
                )
                self._preview_background_key = key
            background = self._preview_background

        img = self.video_renderer.render_frame_pil(
            width=frame_width,
            height=frame_height,
            style=self.var_style.get(),
            theme=self.var_theme.get(),
            aspect=self.var_aspect.get(),
            title=self.var_title.get() if self.var_text_overlay.get() else "",
            artist=self.var_artist.get() if self.var_text_overlay.get() else "",
            audio_engine=self.audio_engine if self.audio_engine.is_loaded else None,
            timestamp=self.current_preview_timestamp,
            text_scale=self.var_text_scale.get(),
            bg_image=background
        )

        self.preview_image = ImageTk.PhotoImage(img)
        self.canvas_preview.delete("all")
        self.canvas_preview.create_image(width // 2, height // 2, image=self.preview_image)

    def start_video_export(self):
        if not self.audio_path:
            messagebox.showwarning("No Audio", "Please choose an audio file first!")
            return
        if self.is_rendering:
            return

        out_path = filedialog.asksaveasfilename(
            title="Save Rendered Visualizer Video",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")]
        )
        if not out_path:
            return

        # Pause preview playback to dedicate full CPU to rendering
        if self.is_playing:
            self.pause_preview()

        self.is_rendering = True
        self.btn_export.config(state="disabled", text="Rendering Video...")
        self.progress_bar["value"] = 0

        # Launch export in background thread so GUI stays responsive
        thread = threading.Thread(
            target=self._run_export,
            args=(out_path,),
            daemon=True
        )
        thread.start()

    def _run_export(self, output_path):
        def progress_callback(pct, msg):
            self.root.after(0, lambda: self._update_progress(pct, msg))

        try:
            self.video_renderer.export_video(
                audio_path=self.audio_path,
                output_path=output_path,
                audio_engine=self.audio_engine,
                style=self.var_style.get(),
                theme=self.var_theme.get(),
                aspect=self.var_aspect.get(),
                fps=self.var_fps.get(),
                title=self.var_title.get() if self.var_text_overlay.get() else "",
                artist=self.var_artist.get() if self.var_text_overlay.get() else "",
                progress_fn=progress_callback,
                text_scale=self.var_text_scale.get(),
                bg_image=self.bg_image_pil if self.var_use_bg_image.get() else None
            )
            self.root.after(0, lambda: self._export_finished(output_path, None))
        except Exception as e:
            self.root.after(0, lambda: self._export_finished(output_path, str(e)))

    def _update_progress(self, pct, msg):
        self.progress_bar["value"] = pct
        self.lbl_progress.config(text=f"{pct:.1f}% - {msg}")

    def _export_finished(self, out_path, error):
        self.is_rendering = False
        self.btn_export.config(state="normal", text="Render & Export Video (.mp4)")
        if error:
            err_msg = "An error occurred during video render:\n" + str(error)
            messagebox.showerror("Export Failed", err_msg)
            self.lbl_progress.config(text="Render failed.")
        else:
            self.lbl_progress.config(text=f"Render complete! Saved to {os.path.basename(out_path)}")
            prompt_msg = "Video successfully rendered to:\n" + str(out_path) + "\n\nWould you like to open it in QuickTime/Finder?"
            res = messagebox.askyesno("Export Complete!", prompt_msg)
            if res and sys.platform == "darwin":
                os.system(f'open "{out_path}"')

    def on_close(self):
        try:
            self.audio_player.stop()
        except Exception:
            pass
        self.root.destroy()

def main():
    root = tk.Tk()
    # macOS styling improvements
    try:
        root.tk.call('tk', 'scaling', 2.0) # Retina support
    except Exception:
        pass
    app = PulseWaveApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
