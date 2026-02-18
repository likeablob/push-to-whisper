from typing import Dict, Type

from push_to_whisper.pipeline.base import BaseStep
from push_to_whisper.pipeline.steps.llm import LLMInstructionStep, LLMRefineStep
from push_to_whisper.pipeline.steps.output import AppriseStep, CopyClipboardStep
from push_to_whisper.pipeline.steps.process import LLMPatchStep, TranscodeStep
from push_to_whisper.pipeline.steps.save_audio import SaveAudioStep
from push_to_whisper.pipeline.steps.save_file import SaveMarkdownStep
from push_to_whisper.pipeline.steps.transcribe import TranscribeStep

STEP_REGISTRY: Dict[str, Type[BaseStep]] = {
    "transcribe": TranscribeStep,
    "llm_refine": LLMRefineStep,
    "llm_instruction": LLMInstructionStep,
    "save_markdown": SaveMarkdownStep,
    "save_audio": SaveAudioStep,
    "transcode": TranscodeStep,
    "llm_patch": LLMPatchStep,
    "copy_clipboard": CopyClipboardStep,
    "apprise": AppriseStep,
}


def get_step_class(step_type: str) -> Type[BaseStep]:
    if step_type not in STEP_REGISTRY:
        raise ValueError(f"Unknown pipeline step type: {step_type}")
    return STEP_REGISTRY[step_type]
