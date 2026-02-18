import subprocess

import pytest


def test_cli_help():
    """Verify that --help works correctly (detect import errors)"""
    result = subprocess.run(
        ["uv", "run", "push-to-whisper", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "usage: push-to-whisper" in result.stdout


def test_cli_init_smoke():
    """Verify that the init command works correctly"""
    result = subprocess.run(
        ["uv", "run", "push-to-whisper", "init"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "storage:" in result.stdout
    assert "whisper:" in result.stdout


def test_cli_serve_import_smoke():
    """Check for issues with imports (main_daemon, etc.) when running serve by importing the module directly"""
    # Instead of running a subcommand, import the actual module to verify
    # that all transitive dependencies (patch_ng, etc.) can be resolved.
    try:
        from push_to_whisper.main_daemon import start_daemon

        assert start_daemon is not None
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")
    except Exception as e:
        # Depending on GUI/D-Bus, an error might occur during import in some environments,
        # but the primary goal is to check the import itself (ModuleNotFoundError).
        print(f"Imported but failed with other error (expected in some CI): {e}")
