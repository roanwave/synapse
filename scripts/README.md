# Synapse Build Scripts

This directory contains scripts for building and deploying Synapse.

## Desktop Launcher (Recommended)

The simplest way to launch Synapse from your desktop:

### 1. Generate the Icon (first time only)

```bash
python scripts/generate_icon.py
```

This creates `synapse/assets/synapse.ico` with a neural network motif.

### 2. Create Desktop Shortcut

```bash
python scripts/create_shortcut.py
```

Options:
- `--start-menu` - Also add to Windows Start Menu
- `--no-desktop` - Skip desktop shortcut

The shortcut uses `pythonw.exe` to run `launch_synapse.pyw` without showing a console window.

## Standalone Executable (Optional)

For a true standalone .exe that doesn't require Python installed:

### Requirements

```bash
pip install pyinstaller
```

### Build

```bash
python scripts/build_exe.py
```

Options:
- `--onefile` - Single .exe file (slower startup, ~100MB)
- `--debug` - Include console window for troubleshooting

Output: `dist/Synapse/Synapse.exe` or `dist/Synapse.exe` (with --onefile)

## Files

| File | Description |
|------|-------------|
| `generate_icon.py` | Creates the application icon (synapse.ico) |
| `create_shortcut.py` | Creates Windows desktop/Start Menu shortcuts |
| `build_exe.py` | Builds standalone executable with PyInstaller |

## Direct Launch

You can also run Synapse directly:

```bash
# With console (for debugging)
python synapse/main.py

# Without console
pythonw.exe launch_synapse.pyw
```
