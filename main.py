#!/usr/bin/env python3
"""
PulseWave Audio Visualizer & Video Studio
Native macOS Desktop Application
Packaged for PyInstaller (macOS .app bundle)
"""

import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk, ImageDraw

from audio_engine import AudioEngine
from video_renderer import VideoRenderer, VISUALIZER_STYLES

class PulseWaveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PulseWave - Audio Visualizer Studio")
        self.root.geometry("1100x750")
        self.root.minsize(950, 650)
        self.root.configure(bg="#0B0F19")

        # Application state
        self.audio_path = None
        self.audio_engine = AudioEngine()
        self.video_renderer = VideoRenderer()
        self.is_rendering = False
        self.preview_image = None
        
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
        left_frame = tk.Frame(main_paned, bg="#131B2E", padx=16, pady=16)
        main_paned.add(left_frame, minsize=380, width=420)

        # Right Column: Visualizer Preview & Timeline
        right_frame = tk.Frame(main_paned, bg="#0B0F19")
        main_paned.add(right_frame, minsize=500)

        self._build_left_controls(left_frame)
        self._build_right_preview(right_frame)

    def _build_left_controls(self, parent):
        # 1. Audio File Section
        file_box = tk.LabelFrame(
            parent,
            text=" 1. AUDIO SOURCE ",
            font=("Helvetica", 10, "bold"),
            fg="#38BDF8",
            bg="#131B2E",
            padx=10,
            pady=10
        )
        file_box.pack(fill="x", pady=(0, 12))

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

        btn_choose = tk.Button(
            btn_row,
            text="Choose Audio File...",
            command=self.open_audio_file,
            bg="#0284C7",
            fg="white",
            relief="flat",
            padx=12,
            pady=6,
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
            pady=10
        )
        style_box.pack(fill="x", pady=(0, 12))

        tk.Label(style_box, text="Preset Style:", fg="#E2E8F0", bg="#131B2E", font=("Helvetica", 9)).pack(anchor="w")
        cb_style = ttk.Combobox(
            style_box,
            textvariable=self.var_style,
            values=list(VISUALIZER_STYLES.keys()),
            state="readonly"
        )
        cb_style.pack(fill="x", pady=(2, 8))
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
        cb_theme.pack(fill="x", pady=(2, 8))
        cb_theme.bind("<<ComboboxSelected>>", lambda e: self.update_preview())

        aspect_row = tk.Frame(style_box, bg="#131B2E")
        aspect_row.pack(fill="x", pady=(2, 4))
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
            pady=10
        )
        text_box.pack(fill="x", pady=(0, 12))

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
        entry_title.pack(fill="x", pady=(2, 6))
        entry_title.bind("<KeyRelease>", lambda e: self.update_preview())

        tk.Label(text_box, text="Artist / Creator:", fg="#94A3B8", bg="#131B2E", font=("Helvetica", 9)).pack(anchor="w")
        entry_artist = tk.Entry(text_box, textvariable=self.var_artist, bg="#0B0F19", fg="white", insertbackground="white", bd=1)
        entry_artist.pack(fill="x", pady=(2, 6))
        entry_artist.bind("<KeyRelease>", lambda e: self.update_preview())

        # 4. Export Button & Status
        export_box = tk.Frame(parent, bg="#131B2E")
        export_box.pack(fill="x", side="bottom", pady=6)

        self.btn_export = tk.Button(
            export_box,
            text="Render & Export Video (.mp4)",
            command=self.start_video_export,
            bg="#10B981",
            fg="white",
            relief="flat",
            padx=14,
            pady=10,
            font=("Helvetica", 11, "bold"),
            cursor="hand2"
        )
        self.btn_export.pack(fill="x")

        self.progress_bar = ttk.Progressbar(export_box, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", pady=(8, 4))

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
        prev_head.pack(fill="x", pady=(0, 8))

        tk.Label(
            prev_head,
            text="Visualizer Real-Time Preview",
            font=("Helvetica", 12, "bold"),
            fg="#F8FAFC",
            bg="#0B0F19"
        ).pack(side="left")

        # Canvas for rendering preview frames
        self.canvas_preview = tk.Canvas(parent, bg="#000000", highlightthickness=1, highlightbackground="#1E293B")
        self.canvas_preview.pack(fill="both", expand=True)
        self.canvas_preview.bind("<Configure>", lambda e: self.update_preview())

        # Initial placeholder preview
        self.root.after(100, self.update_preview)

    def open_audio_file(self):
        filetypes = [
            ("Audio Files", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac"),
            ("All Files", "*.*")
        ]
        chosen = filedialog.askopenfilename(title="Select Audio File", filetypes=filetypes)
        if chosen:
            self.audio_path = chosen
            fname = os.path.basename(chosen)
            self.lbl_filename.config(text=fname)
            self.var_title.set(os.path.splitext(fname)[0])

            # Analyze audio in background thread
            threading.Thread(target=self._load_and_analyze_audio, daemon=True).start()

    def _load_and_analyze_audio(self):
        self.lbl_progress.config(text="Analyzing audio frequencies...")
        try:
            self.audio_engine.load_file(self.audio_path)
            dur = self.audio_engine.get_duration()
            mins = int(dur // 60)
            secs = int(dur % 60)
            self.lbl_duration.config(text=f"{mins:02d}:{secs:02d}")
            self.lbl_progress.config(text="Audio analysis complete. Ready to export.")
            self.update_preview()
        except Exception as e:
            messagebox.showerror("Audio Load Error", f"Failed to load audio: {str(e)}")
            self.lbl_progress.config(text="Audio load error.")

    def update_preview(self):
        width = self.canvas_preview.winfo_width()
        height = self.canvas_preview.winfo_height()
        if width <= 10 or height <= 10:
            width, height = 640, 360

        # Create simulated or real frame
        frame_time = 2.5 # Preview at 2.5s mark
        img = self.video_renderer.render_frame_pil(
            width=width,
            height=height,
            style=self.var_style.get(),
            theme=self.var_theme.get(),
            aspect=self.var_aspect.get(),
            title=self.var_title.get() if self.var_text_overlay.get() else "",
            artist=self.var_artist.get() if self.var_text_overlay.get() else "",
            audio_engine=self.audio_engine if self.audio_engine.is_loaded else None,
            timestamp=frame_time
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
                progress_fn=progress_callback
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
