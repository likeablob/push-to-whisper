import logging
import queue
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from scipy.signal import resample

logger = logging.getLogger(__name__)


class Recorder:
    def __init__(self, target_sample_rate=16000, channels=1):
        self.target_sample_rate = target_sample_rate
        self.channels = channels
        self._recording_event = threading.Event()
        self.audio_queue = queue.Queue()

        # Get native sample rate of the device
        try:
            self.device_sample_rate = int(
                sd.query_devices(kind="input")["default_samplerate"]
            )
        except Exception as e:
            logger.warning(
                f"Failed to query default input device sample rate, falling back to 44100Hz: {e}"
            )
            self.device_sample_rate = 44100

        logger.info(f"Recorder initialized (Native: {self.device_sample_rate}Hz)")

        # Initialize sounddevice stream (do not start yet)
        self.stream = sd.InputStream(
            samplerate=self.device_sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
            dtype="float32",
            blocksize=0,
            latency="low",
        )

    def _audio_callback(self, indata, frames, time, status):
        """Audio thread with high priority"""
        if status:
            logger.warning(f"Audio status warning: {status}")

        # Put data into the queue (continuously collected while stream is running)
        self.audio_queue.put(indata.copy())

    def start(self):
        """Start the stream and set it to recording state"""
        if self._recording_event.is_set():
            return

        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        self._recording_event.set()
        self.stream.start()
        logger.debug("Recording started (Stream opened)")

    def stop(self) -> np.ndarray:
        """Stop recording, close the stream, and return raw data (no heavy processing)"""
        if not self._recording_event.is_set():
            return np.array([], dtype="float32")

        self._recording_event.clear()
        self.stream.stop()
        logger.debug("Recording stopped (Stream closed)")

        # Collect all chunks from the queue
        data_list = []
        while not self.audio_queue.empty():
            try:
                data_list.append(self.audio_queue.get_nowait())
            except queue.Empty:
                break

        if not data_list:
            return np.array([], dtype="float32")

        # Concatenate chunks into a flat array
        audio_data = np.concatenate(data_list, axis=0).flatten()
        return np.clip(audio_data, -1.0, 1.0)

    def save_processed(self, audio_data: np.ndarray, output_path: Path):
        """Data preservation process (resampling, int16 conversion, I/O)"""
        if audio_data.size == 0:
            logger.warning("No audio data to save.")
            return

        # Resample on save (to 16kHz for Whisper)
        if self.device_sample_rate != self.target_sample_rate:
            num_samples = int(
                len(audio_data) * self.target_sample_rate / self.device_sample_rate
            )
            audio_data = resample(audio_data, num_samples)

        # float32 -> int16 conversion
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save using scipy
        wavfile.write(str(output_path), self.target_sample_rate, audio_int16)

        duration = len(audio_int16) / self.target_sample_rate
        logger.info(f"Saved: {output_path} ({duration:.1f}s)")

    def close(self):
        """Stop the stream"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None


if __name__ == "__main__":
    import time

    rec = Recorder()
    time.sleep(1)
    rec.start()
    time.sleep(3)
    # stop() no longer takes arguments
    data = rec.stop()
    if data.size > 0:
        rec.save_processed(data, Path("tmp/test_final.wav"))
    rec.close()
