"""
Video Rendering & Export Engine
Draws visualizer frames and encodes H.264 MP4 with synchronized audio.
"""

import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

def get_system_font(size):
    """
    Loads the default system font (San Francisco or Helvetica on macOS) at the given size.
    Falls back gracefully if specific font files are unavailable.
    """
    candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/SFNSText.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "Helvetica.ttc",
        "Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

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

    def prepare_background_image(self, bg_image, width, height):
        """
        Scales and center-crops a PIL image to fill width x height without distortion.
        Applies a subtle dimming overlay to ensure neon visualizers and text stand out.
        """
        if bg_image is None:
            return None
        iw, ih = bg_image.size
        if iw == width and ih == height:
            cropped = bg_image.copy()
        else:
            scale = max(width / iw, height / ih)
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))
            resample = Image.Resampling.BILINEAR if max(width, height) <= 800 else Image.Resampling.LANCZOS
            resized = bg_image.resize((new_w, new_h), resample)
            crop_x = (new_w - width) // 2
            crop_y = (new_h - height) // 2
            cropped = resized.crop((crop_x, crop_y, crop_x + width, crop_y + height)).convert("RGB")

        # Subtle dimming (0.78 brightness) ensures glowing visualizers and text are crisp and high-contrast
        enhancer = ImageEnhance.Brightness(cropped)
        return enhancer.enhance(0.78)

    def render_frame_pil(self, width, height, style, theme, aspect, title="", artist="", audio_engine=None, timestamp=0.0, text_scale=1.0, bg_image=None):
        theme_colors = COLOR_THEMES.get(theme, COLOR_THEMES["Cyber Neon (Cyan & Pink)"])
        bg_color = theme_colors["bg"]
        primary = theme_colors["primary"]
        secondary = theme_colors["secondary"]
        accent = theme_colors["accent"]

        if bg_image is not None:
            if isinstance(bg_image, str):
                try:
                    loaded = Image.open(bg_image)
                    img = self.prepare_background_image(loaded, width, height)
                except Exception:
                    img = Image.new("RGB", (width, height), bg_color)
            elif isinstance(bg_image, Image.Image):
                if bg_image.size == (width, height):
                    img = bg_image.copy()
                else:
                    img = self.prepare_background_image(bg_image, width, height)
            else:
                img = Image.new("RGB", (width, height), bg_color)
            draw = ImageDraw.Draw(img)
        else:
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
        if title or artist:
            # Baseline font sizes (minimum size at scale 1.0)
            base_title_size = max(11, int(height * 0.024))
            base_artist_size = max(10, int(base_title_size * 0.75))

            eff_scale = max(1.0, float(text_scale))
            title_size = max(10, int(base_title_size * eff_scale))
            artist_size = max(9, int(base_artist_size * eff_scale))

            title_font = get_system_font(title_size)
            artist_font = get_system_font(artist_size)

            top_y = max(int(height * 0.07), int(title_size * 0.75))
            if title and artist:
                title_y = top_y
                gap = int(title_size * 0.5 + artist_size * 0.5 + 4)
                artist_y = title_y + gap
            elif title:
                title_y = top_y
            elif artist:
                artist_y = top_y

            # Draw with subtle drop shadow for maximum legibility over background images
            if title:
                draw.text((cx + 1, title_y + 1), title, font=title_font, fill=(0, 0, 0, 200), anchor="mm")
                draw.text((cx, title_y), title, font=title_font, fill=(255, 255, 255), anchor="mm")
            if artist:
                draw.text((cx + 1, artist_y + 1), artist, font=artist_font, fill=(0, 0, 0, 180), anchor="mm")
                draw.text((cx, artist_y), artist, font=artist_font, fill=(180, 190, 210), anchor="mm")

        return img

    def export_video(self, audio_path, output_path, audio_engine, style, theme, aspect, fps, title, artist, progress_fn=None, text_scale=1.0, bg_image=None):
        """Streams rendered frames directly to ffmpeg for fast, lossless MP4 video export"""
        # Determine resolution
        if aspect == "9:16":
            width, height = 1080, 1920
        elif aspect == "1:1":
            width, height = 1080, 1080
        else: # 16:9
            width, height = 1920, 1080

        # Pre-prepare background image once if provided for high-speed frame rendering
        prepared_bg = None
        if bg_image is not None:
            if isinstance(bg_image, str):
                try:
                    loaded = Image.open(bg_image)
                    prepared_bg = self.prepare_background_image(loaded, width, height)
                except Exception:
                    pass
            elif isinstance(bg_image, Image.Image):
                prepared_bg = self.prepare_background_image(bg_image, width, height)

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
                timestamp=timestamp,
                text_scale=text_scale,
                bg_image=prepared_bg
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
