import yaml

from push_to_whisper.config import Settings


def test_settings_default_values():
    """Verify that default values are set correctly."""
    # Use ignore_config=True to avoid loading local user config during tests
    s = Settings.load(ignore_config=True)
    assert s.whisper.whisper_cpp.enabled is True
    assert s.storage.filename_template == "{{ date }}/{{ date }}-{{ time }}"


def test_settings_yaml_load(tmp_path):
    """Verify loading settings from a YAML file."""
    config_file = tmp_path / "config.yaml"

    config_data = {
        "whisper": {"openai": {"model": "medium", "language": "en"}},
        "storage": {"base_dir": "/tmp/ptw_test"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    # Explicitly specify the file using Settings.load()
    s = Settings.load(config_file)
    assert s.whisper.openai.model == "medium"
    assert s.whisper.openai.language == "en"
    assert s.storage.base_dir == "/tmp/ptw_test"


def test_settings_env_override(monkeypatch):
    """Verify environment variable overrides."""
    monkeypatch.setenv("WHISPER__OPENAI__MODEL", "large")
    monkeypatch.setenv("STORAGE__BASE_DIR", "/env/override")

    s = Settings.load(ignore_config=True)
    assert s.whisper.openai.model == "large"
    assert s.storage.base_dir == "/env/override"


def test_settings_load_method(tmp_path):
    """Verify the behavior of the load class method."""
    # 1. No path specified (default)
    s_default = Settings.load()
    assert isinstance(s_default, Settings)

    # 2. Path specified
    cfg = tmp_path / "custom.yaml"
    with open(cfg, "w") as f:
        yaml.dump({"whisper": {"openai": {"model": "custom-model"}}}, f)

    s_custom = Settings.load(cfg)
    assert s_custom.whisper.openai.model == "custom-model"
