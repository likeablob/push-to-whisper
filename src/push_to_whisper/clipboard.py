import shutil
import subprocess


def copy_to_clipboard(text: str):
    """Copy text to clipboard using wl-copy (assuming Wayland)"""
    if not text:
        return

    # Check if wl-copy exists
    wl_copy = shutil.which("wl-copy")
    if wl_copy:
        try:
            subprocess.run([wl_copy], input=text.encode("utf-8"), check=True)
            print("--- Text copied to clipboard via wl-copy ---")
            return
        except Exception as e:
            print(f"Failed to copy to clipboard via wl-copy: {e}")

    # Fallback for X11 environment (xsel / xclip)
    xsel = shutil.which("xsel")
    if xsel:
        try:
            subprocess.run([xsel, "-bi"], input=text.encode("utf-8"), check=True)
            print("--- Text copied to clipboard via xsel ---")
            return
        except Exception as e:
            print(f"Failed to copy to clipboard via xsel: {e}")

    print("Warning: No clipboard tool (wl-copy or xsel) found.")
