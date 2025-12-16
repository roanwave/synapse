"""Chat panel for displaying conversation history."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from ..config.themes import theme


class MessageBubble(QFrame):
    """A single message bubble in the chat."""

    def __init__(self, role: str, content: str = "", parent: QWidget | None = None):
        """Initialize the message bubble.

        Args:
            role: "user" or "assistant"
            content: Initial message content
            parent: Parent widget
        """
        super().__init__(parent)
        self.role = role
        self._setup_ui(content)

    def _setup_ui(self, content: str) -> None:
        """Set up the bubble UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # Role label
        role_label = QLabel("You" if self.role == "user" else "Assistant")
        role_label.setStyleSheet(f"""
            color: {theme.text_secondary};
            font-size: 12px;
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(role_label)

        # Content label
        self.content_label = QLabel(content)
        self.content_label.setWordWrap(True)
        self.content_label.setTextFormat(Qt.TextFormat.PlainText)
        self.content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.content_label.setStyleSheet(f"""
            color: {theme.text_primary};
            font-size: 14px;
            background: transparent;
            padding: 4px 0;
        """)
        layout.addWidget(self.content_label)

        # Style the bubble
        bubble_color = theme.user_bubble if self.role == "user" else theme.assistant_bubble
        self.setStyleSheet(f"""
            MessageBubble {{
                background-color: {bubble_color};
                border-radius: 12px;
                margin: 4px 0;
            }}
        """)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def set_content(self, content: str) -> None:
        """Update the bubble content.

        Args:
            content: New content text
        """
        self.content_label.setText(content)

    def append_content(self, text: str) -> None:
        """Append text to the bubble content.

        Args:
            text: Text to append
        """
        current = self.content_label.text()
        self.content_label.setText(current + text)


class ChatPanel(QWidget):
    """Panel for displaying the conversation history."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the chat panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._bubbles: list[MessageBubble] = []
        self._current_assistant_bubble: MessageBubble | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme.background};
                border: none;
            }}
        """)

        # Container for messages
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(16, 16, 16, 16)
        self.messages_layout.setSpacing(12)
        self.messages_layout.addStretch()  # Push messages to top initially

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)

    def add_user_message(self, content: str) -> None:
        """Add a user message to the chat.

        Args:
            content: Message text
        """
        bubble = MessageBubble("user", content)
        self._add_bubble(bubble)

    def start_assistant_message(self) -> None:
        """Start a new assistant message for streaming."""
        bubble = MessageBubble("assistant", "")
        self._current_assistant_bubble = bubble
        self._add_bubble(bubble)

    def append_to_assistant_message(self, text: str) -> None:
        """Append text to the current assistant message.

        Args:
            text: Text to append
        """
        if self._current_assistant_bubble:
            self._current_assistant_bubble.append_content(text)
            self._scroll_to_bottom()

    def finish_assistant_message(self) -> None:
        """Mark the current assistant message as complete."""
        self._current_assistant_bubble = None

    def add_error_message(self, error: str) -> None:
        """Add an error message to the chat.

        Args:
            error: Error text
        """
        bubble = MessageBubble("assistant", f"Error: {error}")
        bubble.content_label.setStyleSheet(f"""
            color: {theme.error};
            font-size: 14px;
            background: transparent;
            padding: 4px 0;
        """)
        self._add_bubble(bubble)
        self._current_assistant_bubble = None

    def _add_bubble(self, bubble: MessageBubble) -> None:
        """Add a bubble to the layout.

        Args:
            bubble: The message bubble to add
        """
        # Remove the stretch if this is the first message
        if not self._bubbles:
            # Remove the stretch item
            item = self.messages_layout.takeAt(0)
            if item:
                del item

        self._bubbles.append(bubble)
        self.messages_layout.addWidget(bubble)

        # Add stretch after messages to prevent them from expanding
        self.messages_layout.addStretch()

        # Scroll to bottom after a short delay to allow layout
        QTimer.singleShot(10, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        """Scroll the chat to the bottom."""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear(self) -> None:
        """Clear all messages from the chat."""
        for bubble in self._bubbles:
            self.messages_layout.removeWidget(bubble)
            bubble.deleteLater()
        self._bubbles.clear()
        self._current_assistant_bubble = None

        # Re-add the stretch
        self.messages_layout.addStretch()
