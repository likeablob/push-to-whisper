import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def transcode_audio(input_path: Path, options: Dict[str, Any]) -> Optional[Path]:
    """Transcode audio file using ffmpeg."""
    if not input_path.exists():
        logger.error(f"Input file not found for transcoding: {input_path}")
        return None

    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe:
        logger.error("ffmpeg command not found. Please install ffmpeg.")
        return None

    output_format = options.get("format", "ogg")
    bitrate = options.get("bitrate", "64k")

    # Note: Original file is not deleted here; cleanup is handled by the daemon.

    # Create output file in the same directory
    output_path = input_path.with_suffix(f".{output_format}")
    if input_path == output_path:
        # Avoid overwriting if extension is the same (e.g., wav to wav)
        output_path = input_path.with_name(f"transcoded_{input_path.name}").with_suffix(
            f".{output_format}"
        )

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i",
        str(input_path),
        "-ab",
        bitrate,
        str(output_path),
    ]

    try:
        logger.info(f"Transcoding {input_path.name} to {output_path.name}...")
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg error: {e.stderr.decode().strip()}")
        return None
    except Exception as e:
        logger.error(f"Transcoding failed: {e}")
        return None
