"""Export utilities for Synapse.

Handles exporting conversation history to various formats.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


def export_to_markdown(
    messages: List[Dict[str, str]],
    models_used: Optional[List[str]] = None,
    token_count: Optional[int] = None,
    session_id: Optional[str] = None,
) -> str:
    """Export conversation messages to markdown format.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        models_used: Optional list of model IDs used in the conversation
        token_count: Optional total token count
        session_id: Optional session ID

    Returns:
        Formatted markdown string
    """
    lines = []

    # Header with metadata
    lines.append("# Synapse Conversation Export")
    lines.append("")
    lines.append(f"**Exported:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")

    if session_id:
        lines.append(f"**Session ID:** {session_id[:8]}...")

    if models_used:
        models_str = ", ".join(models_used[:3])
        if len(models_used) > 3:
            models_str += f" (+{len(models_used) - 3} more)"
        lines.append(f"**Models Used:** {models_str}")

    if token_count:
        lines.append(f"**Total Tokens:** {token_count:,}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Messages
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")

        # Role header
        if role == "user":
            header = "## User"
        elif role == "assistant":
            header = "## Assistant"
        else:
            header = f"## {role.capitalize()}"

        if timestamp:
            header += f" ({timestamp})"

        lines.append(header)
        lines.append("")
        lines.append(content)
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Exported from [Synapse](https://github.com/roanwave/synapse)*")

    return "\n".join(lines)


def generate_export_filename(prefix: str = "synapse_export") -> str:
    """Generate a timestamped export filename.

    Args:
        prefix: Filename prefix

    Returns:
        Filename string with timestamp
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"{prefix}_{timestamp}.md"


def save_markdown_export(
    filepath: Path,
    messages: List[Dict[str, str]],
    models_used: Optional[List[str]] = None,
    token_count: Optional[int] = None,
    session_id: Optional[str] = None,
) -> None:
    """Save conversation to a markdown file.

    Args:
        filepath: Path to save the file
        messages: List of message dicts
        models_used: Optional list of model IDs
        token_count: Optional total token count
        session_id: Optional session ID
    """
    content = export_to_markdown(
        messages=messages,
        models_used=models_used,
        token_count=token_count,
        session_id=session_id,
    )

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
