"""Create Windows desktop shortcut for Synapse.

Creates a .lnk shortcut file on the user's desktop that launches
Synapse without showing a console window.

Usage:
    python scripts/create_shortcut.py
    python scripts/create_shortcut.py --start-menu  # Also add to Start Menu
"""

import sys
import os
import subprocess
from pathlib import Path


def get_pythonw_path() -> Path:
    """Get the path to pythonw.exe.

    Returns:
        Path to pythonw.exe
    """
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"

    if pythonw.exists():
        return pythonw

    # Try Scripts directory for virtual environments
    scripts_pythonw = python_dir / "Scripts" / "pythonw.exe"
    if scripts_pythonw.exists():
        return scripts_pythonw

    # Fallback to python.exe location with w suffix
    return Path(sys.executable.replace("python.exe", "pythonw.exe"))


def create_shortcut_powershell(
    shortcut_path: Path,
    target_path: Path,
    working_dir: Path,
    icon_path: Path,
    description: str = "Synapse - Private Thinking Environment",
) -> bool:
    """Create a shortcut using PowerShell (fallback method).

    Args:
        shortcut_path: Where to create the .lnk file
        target_path: What the shortcut points to
        working_dir: Working directory for the target
        icon_path: Path to the .ico file
        description: Shortcut description

    Returns:
        True if successful
    """
    pythonw = get_pythonw_path()
    launcher = working_dir / "launch_synapse.pyw"

    # PowerShell script to create shortcut
    ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{pythonw}"
$Shortcut.Arguments = '"{launcher}"'
$Shortcut.WorkingDirectory = "{working_dir}"
$Shortcut.IconLocation = "{icon_path}, 0"
$Shortcut.Description = "{description}"
$Shortcut.Save()
'''

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"PowerShell error: {e}")
        return False


def create_shortcut_win32(
    shortcut_path: Path,
    target_path: Path,
    working_dir: Path,
    icon_path: Path,
    description: str = "Synapse - Private Thinking Environment",
) -> bool:
    """Create a shortcut using win32com (preferred method).

    Args:
        shortcut_path: Where to create the .lnk file
        target_path: What the shortcut points to
        working_dir: Working directory for the target
        icon_path: Path to the .ico file
        description: Shortcut description

    Returns:
        True if successful
    """
    try:
        import win32com.client
    except ImportError:
        return False

    pythonw = get_pythonw_path()
    launcher = working_dir / "launch_synapse.pyw"

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = str(pythonw)
        shortcut.Arguments = f'"{launcher}"'
        shortcut.WorkingDirectory = str(working_dir)
        shortcut.IconLocation = f"{icon_path}, 0"
        shortcut.Description = description
        shortcut.save()
        return True
    except Exception as e:
        print(f"win32com error: {e}")
        return False


def get_desktop_path() -> Path:
    """Get the user's desktop path.

    Returns:
        Path to Desktop folder
    """
    # Try standard Windows approach
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop

    # Try OneDrive Desktop
    onedrive_desktop = Path.home() / "OneDrive" / "Desktop"
    if onedrive_desktop.exists():
        return onedrive_desktop

    # Fallback to USERPROFILE
    userprofile = os.environ.get("USERPROFILE", "")
    if userprofile:
        desktop = Path(userprofile) / "Desktop"
        if desktop.exists():
            return desktop

    raise RuntimeError("Could not find Desktop folder")


def get_start_menu_path() -> Path:
    """Get the user's Start Menu Programs path.

    Returns:
        Path to Start Menu Programs folder
    """
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        start_menu = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        if start_menu.exists():
            return start_menu

    raise RuntimeError("Could not find Start Menu folder")


def main():
    """Create the desktop shortcut."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create Windows shortcut for Synapse"
    )
    parser.add_argument(
        "--start-menu",
        action="store_true",
        help="Also create Start Menu shortcut",
    )
    parser.add_argument(
        "--no-desktop",
        action="store_true",
        help="Skip desktop shortcut",
    )
    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).parent.parent
    icon_path = project_root / "synapse" / "assets" / "synapse.ico"
    launcher_path = project_root / "launch_synapse.pyw"

    # Verify required files exist
    if not icon_path.exists():
        print(f"Error: Icon not found at {icon_path}")
        print("Run 'python scripts/generate_icon.py' first.")
        sys.exit(1)

    if not launcher_path.exists():
        print(f"Error: Launcher not found at {launcher_path}")
        sys.exit(1)

    # Try win32com first, fall back to PowerShell
    try:
        import win32com.client
        create_shortcut = create_shortcut_win32
        print("Using win32com for shortcut creation...")
    except ImportError:
        create_shortcut = create_shortcut_powershell
        print("Using PowerShell for shortcut creation...")

    shortcuts_created = []

    # Create desktop shortcut
    if not args.no_desktop:
        try:
            desktop = get_desktop_path()
            shortcut_path = desktop / "Synapse.lnk"

            print(f"Creating desktop shortcut: {shortcut_path}")
            if create_shortcut(
                shortcut_path=shortcut_path,
                target_path=launcher_path,
                working_dir=project_root,
                icon_path=icon_path,
            ):
                shortcuts_created.append(shortcut_path)
                print(f"  Created: {shortcut_path}")
            else:
                print("  Failed to create desktop shortcut")
        except Exception as e:
            print(f"  Error creating desktop shortcut: {e}")

    # Create Start Menu shortcut
    if args.start_menu:
        try:
            start_menu = get_start_menu_path()
            shortcut_path = start_menu / "Synapse.lnk"

            print(f"Creating Start Menu shortcut: {shortcut_path}")
            if create_shortcut(
                shortcut_path=shortcut_path,
                target_path=launcher_path,
                working_dir=project_root,
                icon_path=icon_path,
            ):
                shortcuts_created.append(shortcut_path)
                print(f"  Created: {shortcut_path}")
            else:
                print("  Failed to create Start Menu shortcut")
        except Exception as e:
            print(f"  Error creating Start Menu shortcut: {e}")

    # Summary
    if shortcuts_created:
        print(f"\nSuccessfully created {len(shortcuts_created)} shortcut(s):")
        for path in shortcuts_created:
            print(f"  - {path}")
        print("\nYou can now launch Synapse by double-clicking the shortcut!")
    else:
        print("\nNo shortcuts were created.")
        sys.exit(1)


if __name__ == "__main__":
    main()
