"""Synapse Desktop Launcher.

This script launches Synapse without showing a console window.
Use this script with pythonw.exe or associate .pyw files with it.

Usage:
    pythonw.exe launch_synapse.pyw
    OR
    Double-click launch_synapse.pyw (if .pyw is associated with pythonw)
"""

import sys
import os
from pathlib import Path

# Ensure the project root is in the Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Change to project directory to ensure relative paths work
os.chdir(project_root)


def main():
    """Launch the Synapse application."""
    try:
        # Import and run the main application
        from synapse.main import main as run_synapse
        run_synapse()
    except Exception as e:
        # If there's an error, show it in a message box
        # (since we don't have a console)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Failed to start Synapse:\n\n{str(e)}",
                "Synapse Error",
                0x10  # MB_ICONERROR
            )
        except Exception:
            # Last resort: write to a log file
            log_path = project_root / "synapse_error.log"
            with open(log_path, "w") as f:
                f.write(f"Error starting Synapse:\n{str(e)}")


if __name__ == "__main__":
    main()
