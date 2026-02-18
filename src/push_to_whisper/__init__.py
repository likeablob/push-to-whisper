try:
    import importlib.metadata as metadata
except ImportError:
    # Python < 3.8 fallback
    import importlib_metadata as metadata

try:
    __version__ = metadata.version("push-to-whisper")
except metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"
