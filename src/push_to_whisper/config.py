from pathlib import Path
from typing import Any, Dict, List, Optional

from platformdirs import user_config_dir
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class StorageConfig(BaseModel):
    base_dir: str = Field(
        default_factory=lambda: str(Path.home() / "obsidian/myvault/ptw")
    )
    filename_template: str = "{{ date }}/{{ date }}-{{ time }}"
    markdown_template: str = """---
date: {{ date_iso }}
audio_file: "[[{{ audio_file_name }}]]"
tags: [whisper, voice-memo]
---

![[{{ audio_file_name }}]]

{% if refined_text %}
## Refined Text

{{ refined_text }}
{% endif %}

## Full Text (Original)

{{ full_text }}"""


class WhisperCppConfig(BaseModel):
    """
    Configuration for whisper.cpp server.
    Ref: https://github.com/ggerganov/whisper.cpp/blob/master/examples/server/README.md
    """

    enabled: bool = True
    base_url: str = "http://localhost:8080"
    language: str = "ja"  # Note: Also needs to be supported by the server (-l)


class WhisperOpenAIConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[str] = "sk-..."
    base_url: str = "https://api.openai.com/v1"
    model: str = "whisper-1"
    language: Optional[str] = "ja"


class WhisperConfig(BaseModel):
    """
    Configuration for multiple Whisper providers.
    At least one provider must be enabled.

    Recommended model (2026): whisper-v3-turbo for high speed and accuracy.
    For Linux/NVIDIA: Speaches (OpenAI compatible) is recommended.
    For macOS: whisper.cpp or MLX-based engines are recommended.
    """

    whisper_cpp: WhisperCppConfig = Field(default_factory=WhisperCppConfig)
    openai: WhisperOpenAIConfig = Field(default_factory=WhisperOpenAIConfig)


class LLMConfig(BaseModel):
    """LLM connection settings."""

    model: str = "gemini/gemini-2.5-flash"
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class PipelineStep(BaseModel):
    type: str
    options: Dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    id: str
    preferred_trigger: str
    description: str = ""
    steps: List[PipelineStep] = Field(default_factory=list)


class DefaultsConfig(BaseModel):
    """Default settings for each step type."""

    transcode: Dict[str, Any] = Field(
        default_factory=lambda: {
            "format": "ogg",
            "bitrate": "64k",
            "remove_original": True,
        }
    )
    llm_refine: Dict[str, Any] = Field(
        default_factory=lambda: {
            "system_prompt_template": "You are a professional writing assistant. Please refine the provided transcription into a clear and readable text while maintaining the original context. Output only the refined text without any explanations.",
            "input_template": "{{ full_text }}",
        }
    )
    apprise: Dict[str, Any] = Field(
        default_factory=lambda: {
            "urls": [],
            "title_template": "Transcription Complete",
            "body_template": "File: {{ markdown_file_name }}\nText: {{ final_text | truncate(100) }}",
        }
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
    )

    log_level: str = "INFO"
    storage: StorageConfig = Field(default_factory=StorageConfig)
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)

    # Pipelines define the workflows triggered by shortcuts.
    # Note on 'preferred_trigger' format (Freedesktop Shortcuts Spec):
    # - Modifiers (UPPERCASE): CTRL, ALT, SHIFT, NUM, LOGO (for Meta/Super/Win)
    # - Key identifiers: Case-sensitive, typically lowercase (e.g., 'x', 'c', 'Return')
    # - Join with '+': e.g., 'ALT+SHIFT+x', 'LOGO+v'
    pipelines: List[PipelineConfig] = Field(
        default_factory=lambda: [
            PipelineConfig(
                id="push_to_whisper_main",
                preferred_trigger="ALT+SHIFT+x",
                description="Transcription to Markdown",
                steps=[
                    PipelineStep(type="transcribe"),
                    PipelineStep(type="transcode"),
                    PipelineStep(type="save_audio"),
                    PipelineStep(type="save_markdown"),
                    PipelineStep(type="apprise"),
                ],
            ),
            PipelineConfig(
                id="push_to_whisper_clipboard",
                preferred_trigger="ALT+SHIFT+c",
                description="Transcription to Clipboard",
                steps=[
                    PipelineStep(type="transcribe"),
                    PipelineStep(type="transcode"),
                    PipelineStep(type="copy_clipboard"),
                    PipelineStep(type="apprise"),
                ],
            ),
        ]
    )

    @classmethod
    def load(
        cls, config_path: Optional[Path] = None, ignore_config: bool = False
    ) -> "Settings":
        if ignore_config:
            return cls(_ignore_config=True)  # type: ignore

        if config_path:
            return cls(_yaml_file=config_path)  # type: ignore

        return cls()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        if init_settings.init_kwargs.get("_ignore_config"):
            return (init_settings, env_settings)

        default_yaml = Path(user_config_dir("push-to-whisper")) / "config.yaml"
        yaml_file = init_settings.init_kwargs.get("_yaml_file") or default_yaml

        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file),
        )


settings = Settings()
