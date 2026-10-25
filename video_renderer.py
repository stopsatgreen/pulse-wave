"""
Video Rendering & Export Engine
Draws visualizer frames and encodes H.264 MP4 with synchronized audio.
"""

import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

VISUALIZER_STYLES = {
    "circular-spectrum": "Circular Radial Pulse",
    "neon-bars": "Neon Equalizer Bars",
    "waveform-osc": "Waveform Oscilloscope",
    "cyber-grid": "Cyber Horizon Synthwave",
    "galaxy-nebula": "Galaxy Particle Nebula",
    "minimal-ring": "Minimalist Apple Style Ring"
}

COLOR_THEMES = {
    "Cyber Neon (Cyan & Pink)": {
        "primary": (56, 189, 248),    # #38bdf8
        "secondary": (236, 72, 153),  # #ec4899
        "accent": (168, 85, 247),     # #a855f7
        "bg": (11, 15, 25)            # #0b0f19
    },
    "Sunset Glow (Violet & Gold)": {
        "primary": (245, 158, 11),
        "secondary": (239, 68, 68),
        "accent": (139, 92, 246),
        "bg": (15, 10, 26)
    },
    "Matrix Acid (Emerald & Lime)": {
        "primary": (16, 185, 129),
        "secondary": (132, 204, 22),
        "accent": (6, 182, 212),
        "bg": (6, 18, 12)
    },
    "Electric Blue & White": {
        "primary": (14, 165, 233),
        "secondary": (99, 102, 241),
        "accent": (255, 255, 255),
        "bg": (8, 12, 22)
    },
    "Monochrome Frost": {
        "primary": (226, 232, 240),
        "secondary": (148, 163, 184),
        "accent": (255, 255, 255),
        "bg": (15, 23, 42)
    }
}

class VideoRenderer:
    def __init__(self):
        pass

    def render_frame_pil(self, width, height, style, theme, aspect, title="", artist="", audio_engine=None, timestamp=0.0):
        theme_colors = COLOR_THEMES.get(theme, COLOR_THEMES["Cyber Neon (Cyan & Pink)"])
        bg_color = theme_colors["bg"]
        primary = theme_colors["primary"]
        secondary = theme_colors["secondary"]
        accent = theme_colors["accent"]

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Get audio FFT bins if engine available
        num_bars = 64
        if audio_engine and audio_engine.is_loaded:
            spectrum = audio_engine.get_spectrum_at(timestamp, num_bars)
            bass = audio_engine.get_bass_energy_at(timestamp)
        else:
            # Synthetic preview animation
            t = timestamp
            spectrum = np.array([abs(math.sin(i * 0.2 + t * 3)) * 0.7 for i in range(num_bars)])
            bass = float(np.mean(spectrum[:4]))

        cx = width // 2
        cy = height // 2

        if style == "circular-spectrum":
            base_r = int(min(width, height) * 0.22 * (1.0 + bass * 0.15))
            # Center circle
            draw.ellipse([cx - base_r, cy - base_r, cx + base_r, cy + base_r], fill=(20, 25, 40), outline=primary, width=3)
            # Bars radiating
            angle_step = (2 * math.pi) / num_bars
            for i in range(num_bars):
                val = spectrum[i]
                bar_len = int(val * (min(width, height) * 0.25))
                ang = i * angle_step - math.pi / 2
                x1 = cx + math.cos(ang) * (base_r + 2)
                y1 = cy + math.sin(ang) * (base_r + 2)
                x2 = cx + math.cos(ang) * (base_r + 2 + bar_len)
                y2 = cy + math.sin(ang) * (base_r + 2 + bar_len)
                draw.line([(x1, y1), (x2, y2)], fill=accent if i % 2 == 0 else primary, width=3)

        elif style == "neon-bars":
            total_w = int(width * 0.85)
            start_x = (width - total_w) // 2
            bar_w = max(2, int((total_w / num_bars) * 0.75))
            slot_w = total_w / num_bars
            base_y = int(height * 0.7)

            for i in range(num_bars):
                bar_h = int(spectrum[i] * (height * 0.45))
                x = int(start_x + i * slot_w)
                y = base_y - bar_h
                draw.rectangle([x, y, x + bar_w, base_y], fill=primary)
                # Cap line
                draw.rectangle([x, y - 4, x + bar_w, y - 1], fill=accent)

            draw.line([(start_x, base_y), (start_x + total_w, base_y)], fill=secondary, width=2)

        elif style == "waveform-osc":
            pts = []
            total_w = int(width * 0.9)
            start_x = (width - total_w) // 2
            step = total_w / (num_bars - 1)
            base_y = int(height * 0.52)

            for i in range(num_bars):
                x = int(start_x + i * step)
                y_offset = (spectrum[i] - 0.5) * (height * 0.35)
                y = int(base_y + y_offset)
                pts.append((x, y))

            if len(pts) > 1:
                draw.line(pts, fill=primary, width=3)

        elif style == "cyber-grid":
            horizon = int(height * 0.55)
            # Glowing sun
            sun_r = int(min(width, height) * 0.16)
            draw.pieslice([cx - sun_r, horizon - sun_r, cx + sun_r, horizon + sun_r], 180, 360, fill=accent, outline=primary)
            draw.line([(0, horizon), (width, horizon)], fill=primary, width=2)
            # Mountain frequency peaks
            peaks = []
            step = width / num_bars
            for i in range(num_bars):
                h = int(spectrum[i] * (height * 0.25))
                peaks.append((int(i * step), horizon - h))
            if len(peaks) > 1:
                draw.line(peaks, fill=secondary, width=2)

        else: # minimal-ring or galaxy-nebula
            r = int(min(width, height) * 0.25)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=primary, width=2)
            step = (2 * math.pi) / num_bars
            for i in range(num_bars):
                l = int(spectrum[i] * 40)
                ang = i * step
                x1 = cx + math.cos(ang) * (r - 2)
                y1 = cy + math.sin(ang) * (r - 2)
                x2 = cx + math.cos(ang) * (r + l)
                y2 = cy + math.sin(ang) * (r + l)
                draw.line([(x1, y1), (x2, y2)], fill=accent, width=2)

        # Text Overlay
        if title:
            draw.text((cx, int(height * 0.15)), title, fill=(255, 255, 255), anchor="mm")
        if artist:
            draw.text((cx, int(height * 0.20)), artist, fill=(180, 190, 210), anchor="mm")

        return img

    def export_video(self, audio_path, output_path, audio_engine, style, theme, aspect, fps, title, artist, progress_fn=None):
        """Streams rendered frames directly to ffmpeg for fast, lossless MP4 video export"""
        # Determine resolution
        if aspect == "9:16":
            width, height = 1080, 1920
        elif aspect == "1:1":
            width, height = 1080, 1080
        else: # 16:9
            width, height = 1920, 1080

        duration = audio_engine.get_duration()
        total_frames = int(duration * fps)

        # Pipe raw RGB24 frames into ffmpeg process
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", str(fps),
            "-i", "-", # Stdin pipe
            "-i", audio_path, # Audio track
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "320k",
            "-shortest",
            output_path
        ]

        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

        for frame_idx in range(total_frames):
            timestamp = frame_idx / fps
            img = self.render_frame_pil(
                width=width,
                height=height,
                style=style,
                theme=theme,
                aspect=aspect,
                title=title,
                artist=artist,
                audio_engine=audio_engine,
                timestamp=timestamp
            )

            # Write raw bytes to ffmpeg pipe
            raw_bytes = img.tobytes()
            try:
                proc.stdin.write(raw_bytes)
            except BrokenPipeError:
                break

            if progress_fn and frame_idx % 15 == 0:
                pct = (frame_idx / total_frames) * 100
                progress_fn(pct, f"Rendering frame {frame_idx}/{total_frames}")

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            err = proc.stderr.read().decode('utf-8', errors='ignore')
            raise RuntimeError(f"FFmpeg render error: {err}")

        if progress_fn:
            progress_fn(100.0, "Export complete!")
