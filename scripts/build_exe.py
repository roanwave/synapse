"""Build Synapse as a standalone Windows executable.

Uses PyInstaller to create a single .exe file with embedded Python.

Requirements:
    pip install pyinstaller

Usage:
    python scripts/build_exe.py
    python scripts/build_exe.py --onefile  # Single file (slower startup)
    python scripts/build_exe.py --debug    # Include console for debugging
"""

import subprocess
import sys
from pathlib import Path


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def build_executable(onefile: bool = False, debug: bool = False):
    """Build the Synapse executable.

    Args:
        onefile: Create a single .exe file (slower startup)
        debug: Include console window for debugging
    """
    project_root = Path(__file__).parent.parent
    main_script = project_root / "synapse" / "main.py"
    icon_path = project_root / "synapse" / "assets" / "synapse.ico"
    dist_dir = project_root / "dist"

    # Verify paths
    if not main_script.exists():
        print(f"Error: Main script not found at {main_script}")
        sys.exit(1)

    if not icon_path.exists():
        print(f"Warning: Icon not found at {icon_path}")
        print("Run 'python scripts/generate_icon.py' first for custom icon.")
        icon_path = None

    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "Synapse",
        "--distpath", str(dist_dir),
        "--workpath", str(project_root / "build"),
        "--specpath", str(project_root),
        "--clean",
    ]

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    if not debug:
        cmd.append("--windowed")  # No console window
        cmd.append("--noconsole")

    if icon_path:
        cmd.extend(["--icon", str(icon_path)])

    # Add hidden imports for PySide6
    hidden_imports = [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Add data files
    cmd.extend([
        "--add-data", f"{project_root / 'synapse' / 'assets'};synapse/assets",
    ])

    # Main script
    cmd.append(str(main_script))

    print("Building Synapse executable...")
    print(f"Command: {' '.join(cmd)}")
    print()

    # Run PyInstaller
    result = subprocess.run(cmd)

    if result.returncode == 0:
        if onefile:
            exe_path = dist_dir / "Synapse.exe"
        else:
            exe_path = dist_dir / "Synapse" / "Synapse.exe"

        print()
        print("Build successful!")
        print(f"Executable: {exe_path}")
        print()
        print("You can now run Synapse by double-clicking the .exe file.")
    else:
        print()
        print("Build failed. Check the output above for errors.")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Build Synapse as a Windows executable"
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Create a single .exe file (slower startup, easier to distribute)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Include console window for debugging",
    )
    args = parser.parse_args()

    # Check for PyInstaller
    if not check_pyinstaller():
        print("PyInstaller is not installed.")
        print("Install it with: pip install pyinstaller")
        print()
        response = input("Install now? [y/N] ").strip().lower()
        if response == "y":
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print()
        else:
            sys.exit(1)

    build_executable(onefile=args.onefile, debug=args.debug)


if __name__ == "__main__":
    main()
