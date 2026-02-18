import datetime
import logging
import queue
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Tuple

from push_to_whisper.config import Settings
from push_to_whisper.input import get_default_input_adapter
from push_to_whisper.llm_client import LLMClient
from push_to_whisper.notifier import Notifier
from push_to_whisper.pipeline.registry import get_step_class
from push_to_whisper.pipeline.state import PipelineState
from push_to_whisper.recorder import Recorder
from push_to_whisper.whisper.base import BaseWhisperClient
from push_to_whisper.whisper.factory import get_whisper_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class DaemonContext:
    settings: Settings
    whisper: BaseWhisperClient
    notifier: Notifier
    llm: LLMClient
    recorder: Recorder
    task_queue: queue.Queue = field(default_factory=queue.Queue)

    def get_output_paths(self) -> Tuple[Path, Path]:
        """Generate paths based on template in settings."""
        from jinja2 import DebugUndefined, Environment

        now = datetime.datetime.now()
        template_vars = {
            "date_iso": now.isoformat(),
            "date": now.strftime("%Y%m%d"),
            "time": now.strftime("%H%M%S"),
            "start_time": now,
        }

        template_str = self.settings.storage.filename_template
        env = Environment(undefined=DebugUndefined)

        try:
            template = env.from_string(template_str)
            rel_path = template.render(**template_vars)
        except Exception as e:
            logger.error(f"Filename template rendering failed: {e}")
            rel_path = now.strftime("%Y%m%d/%Y%m%d-%H%M%S")

        base_dir = Path(self.settings.storage.base_dir).expanduser()
        base_path = base_dir / rel_path
        return base_path.with_suffix(".wav"), base_path.with_suffix(".md")


def worker(ctx: DaemonContext) -> None:
    logger.info("Worker thread started.")
    while True:
        task = ctx.task_queue.get()
        if task is None:
            break
        try:
            audio_data = task.get("audio_data")
            audio_path = task["audio_path"]

            # Heavy processing (resampling, I/O) is executed in the worker thread
            if audio_data is not None:
                ctx.recorder.save_processed(audio_data, audio_path)

            execute_pipeline(
                ctx, task["pipeline"], audio_path, task.get("whisper_text")
            )
        except Exception as e:
            logger.error(f"Error in worker processing: {e}")
        finally:
            ctx.task_queue.task_done()


def execute_pipeline(
    ctx: DaemonContext,
    pipeline: Any,
    audio_path: Path,
    whisper_text_override: Optional[str] = None,
) -> None:
    """Pipeline execution engine (Strategy Pattern)."""
    logger.info(f"Executing pipeline: {pipeline.id}")

    state = PipelineState(audio_path=audio_path, pipeline_id=pipeline.id)
    if whisper_text_override:
        state.whisper_text = whisper_text_override

    if audio_path and audio_path.exists():
        state.audio_duration = audio_path.stat().st_size / (16000 * 2)

    try:
        for step_config in pipeline.steps:
            logger.info(f"Step: {step_config.type}")

            try:
                # Get class from Registry and execute
                step_class = get_step_class(step_config.type)
                step_instance = step_class()

                default_options = getattr(ctx.settings.defaults, step_config.type, {})
                options = {**default_options, **step_config.options}

                step_instance.execute(ctx, state, options)
            except ValueError as e:
                logger.warning(f"Skipping unknown step: {e}")
                continue

        logger.info(f"Pipeline {pipeline.id} finished successfully.")

        # --- Strategy for full cleanup of temporary files ---
        tmp_dir = Path(ctx.settings.storage.base_dir).expanduser() / ".tmp"
        if tmp_dir.exists():
            for f in tmp_dir.glob("tmp_*"):
                try:
                    f.unlink()
                except Exception as e:
                    logger.debug(f"Failed to cleanup residual tmp file {f}: {e}")

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        ctx.notifier.notify(title="Pipeline Failed", body=str(e))


class DaemonApp:
    def __init__(self, settings: Settings):
        self.ctx = DaemonContext(
            settings=settings,
            whisper=get_whisper_client(settings),
            notifier=Notifier(settings),
            llm=LLMClient(settings),
            recorder=Recorder(),
        )
        self.app_id = "com.github.likeablob.push-to-whisper"
        self.input_adapter = get_default_input_adapter(self.app_id)

    def on_pressed(self, shortcut_id: str):
        logger.info(f"Shortcut Pressed: {shortcut_id}")
        self.ctx.recorder.start()

    def on_released(self, shortcut_id: str):
        logger.info(f"Shortcut Released: {shortcut_id}. Stopping recorder...")
        audio_data = self.ctx.recorder.stop()

        # Find the pipeline corresponding to the shortcut_id
        pipeline = next(
            (p for p in self.ctx.settings.pipelines if p.id == shortcut_id),
            self.ctx.settings.pipelines[0],
        )

        if audio_data is not None and audio_data.size > 0:
            tmp_dir = Path(self.ctx.settings.storage.base_dir).expanduser() / ".tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            audio_path = tmp_dir / f"tmp_{uuid.uuid4().hex[:8]}.wav"

            logger.info(
                f"Queuing pipeline task: {audio_path.name} for pipeline {pipeline.id}"
            )
            self.ctx.task_queue.put(
                {
                    "pipeline": pipeline,
                    "audio_path": audio_path,
                    "audio_data": audio_data,
                }
            )
        else:
            logger.warning("No audio data captured (too short?). Pipeline skipped.")

    def run(self):
        # Configure logging level from settings
        logging.getLogger().setLevel(self.ctx.settings.log_level.upper())
        logger.info(f"Logging level set to: {self.ctx.settings.log_level.upper()}")

        # Start worker thread
        threading.Thread(target=worker, args=(self.ctx,), daemon=True).start()

        try:
            # Start input adapter
            # This will now start a dedicated thread for GLib MainLoop
            self.input_adapter.start(
                on_pressed=self.on_pressed,
                on_released=self.on_released,
                pipelines=self.ctx.settings.pipelines,
            )

            # Keep the main thread alive to handle signals and worker coordination
            logger.info(
                "Daemon is running. Press the global shortcut to record. (Ctrl+C to stop)"
            )
            import time

            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Daemon error: {e}")
        finally:
            # Ensure cleanup happens even on errors
            self.input_adapter.stop()
            self.ctx.task_queue.put(None)
            self.ctx.recorder.close()
            logger.info("Daemon stopped.")


def start_daemon(settings_obj: Settings) -> None:
    """Main entry point to start the daemon."""
    app = DaemonApp(settings_obj)
    app.run()
