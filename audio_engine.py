"""
Audio Analysis Engine for PulseWave
Extracts frequency spectra (FFT), waveform dynamics, and loudness envelope.
"""

import os
import wave
import numpy as np
from scipy.io import wavfile
import subprocess
import tempfile

class AudioEngine:
    def __init__(self):
        self.is_loaded = False
        self.sample_rate = 44100
        self.audio_data = None
        self.duration = 0.0
        self.fft_size = 2048

    def load_file(self, filepath):
        """Loads and decodes any audio file (MP3, WAV, FLAC, M4A) via ffmpeg or wave"""
        self.is_loaded = False
        ext = os.path.splitext(filepath)[1].lower()

        # If already uncompressed WAV
        if ext == ".wav":
            try:
                sr, data = wavfile.read(filepath)
                self._process_samples(sr, data)
                return
            except Exception:
                pass # Fall back to ffmpeg decode

        # Convert to temp 16-bit PCM WAV using ffmpeg (standard on macOS)
        temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()

        cmd = [
            "ffmpeg", "-y", "-i", filepath,
            "-ar", "44100", "-ac", "2", "-f", "wav",
            temp_wav_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            if os.path.exists(temp_wav_path):
                os.remove(temp_wav_path)
            raise RuntimeError(f"FFmpeg decoding failed: {res.stderr.decode('utf-8', errors='ignore')}")

        sr, data = wavfile.read(temp_wav_path)
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)

        self._process_samples(sr, data)

    def _process_samples(self, sr, data):
        self.sample_rate = sr
        # Normalize to float in [-1.0, 1.0]
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.uint8:
            data = (data.astype(np.float32) - 128) / 128.0

        # Downmix to mono for FFT analysis
        if len(data.shape) > 1 and data.shape[1] > 1:
            self.audio_data = np.mean(data, axis=1)
        else:
            self.audio_data = data.flatten()

        self.duration = len(self.audio_data) / self.sample_rate
        self.is_loaded = True

    def get_duration(self):
        return self.duration

    def get_spectrum_at(self, timestamp_seconds, num_bins=64):
        """Computes FFT frequency bin magnitudes at a specific timestamp"""
        if not self.is_loaded or self.audio_data is None:
            # Fallback simulated spectrum if no audio
            t = timestamp_seconds
            freqs = np.linspace(0.1, 1.0, num_bins)
            return np.abs(np.sin(freqs * 8 + t * 4)) * 0.6 + 0.1

        center_idx = int(timestamp_seconds * self.sample_rate)
        half_fft = self.fft_size // 2
        start_idx = max(0, center_idx - half_fft)
        end_idx = min(len(self.audio_data), center_idx + half_fft)

        chunk = self.audio_data[start_idx:end_idx]
        if len(chunk) < self.fft_size:
            chunk = np.pad(chunk, (0, self.fft_size - len(chunk)))

        # Hanning window
        windowed = chunk * np.hanning(len(chunk))
        fft_vals = np.abs(np.fft.rfft(windowed))

        # Logarithmic grouping into num_bins
        bins = np.zeros(num_bins, dtype=np.float32)
        fft_len = len(fft_vals)
        for i in range(num_bins):
            i_start = int(pow(i / num_bins, 1.4) * (fft_len * 0.65))
            i_end = int(pow((i + 1) / num_bins, 1.4) * (fft_len * 0.65)) + 1
            i_end = min(fft_len, max(i_start + 1, i_end))
            bins[i] = np.mean(fft_vals[i_start:i_end])

        # Normalize with soft ceiling
        max_val = np.max(bins) if np.max(bins) > 0 else 1.0
        bins = np.clip(bins / (max_val * 0.8 + 1e-5), 0.0, 1.0)
        return bins

    def get_bass_energy_at(self, timestamp_seconds):
        spec = self.get_spectrum_at(timestamp_seconds, num_bins=32)
        return float(np.mean(spec[:4]))
