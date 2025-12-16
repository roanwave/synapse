"""Chat panel for displaying conversation history."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont

from ..config.themes import theme, fonts, metrics


class TypingIndicator(QWidget):
    """Animated typing indicator (three pulsing dots)."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the typing indicator.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._dots: list[QLabel] = []
        self._timers: list[QTimer] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Create three dots
        for i in range(3):
            dot = QLabel()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"""
                QLabel {{
                    background-color: {theme.text_muted};
                    border-radius: 3px;
                }}
            """)
            self._dots.append(dot)
            layout.addWidget(dot)

        layout.addStretch()
        self.setFixedHeight(20)

    def start(self) -> None:
        """Start the animation."""
        # Stagger the animations
        for i, dot in enumerate(self._dots):
            timer = QTimer(self)
            timer.timeout.connect(lambda d=dot: self._pulse_dot(d))
            timer.start(600)  # Pulse interval
            # Offset each dot
            QTimer.singleShot(i * 200, timer.start)
            self._timers.append(timer)

    def stop(self) -> None:
        """Stop the animation."""
        for timer in self._timers:
            timer.stop()
        self._timers.clear()

        # Reset dots
        for dot in self._dots:
            dot.setStyleSheet(f"""
                QLabel {{
                    background-color: {theme.text_muted};
                    border-radius: 3px;
                }}
            """)

    def _pulse_dot(self, dot: QLabel) -> None:
        """Pulse a single dot."""
        # Simple toggle between bright and dim
        current = dot.styleSheet()
        if theme.text_muted in current:
            dot.setStyleSheet(f"""
                QLabel {{
                    background-color: {theme.accent};
                    border-radius: 3px;
                }}
            """)
        else:
            dot.setStyleSheet(f"""
                QLabel {{
                    background-color: {theme.text_muted};
                    border-radius: 3px;
                }}
            """)


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
        self._typing_indicator: TypingIndicator | None = None
        self._setup_ui(content)

    def _setup_ui(self, content: str) -> None:
        """Set up the bubble UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            metrics.padding_large,
            metrics.padding_medium,
            metrics.padding_large,
            metrics.padding_medium,
        )
        layout.setSpacing(4)

        # Role label
        role_text = "You" if self.role == "user" else "Assistant"
        role_label = QLabel(role_text)
        role_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_small}px;
                font-weight: 600;
                font-family: {fonts.ui};
                background: transparent;
            }}
        """)
        layout.addWidget(role_label)

        # Content label
        self.content_label = QLabel(content)
        self.content_label.setWordWrap(True)
        self.content_label.setTextFormat(Qt.TextFormat.PlainText)
        self.content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.content_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_primary};
                font-size: {metrics.font_medium}px;
                font-family: {fonts.chat};
                background: transparent;
                line-height: 1.5;
            }}
        """)
        layout.addWidget(self.content_label)

        # Style the bubble
        if self.role == "user":
            bubble_color = theme.user_bubble
        else:
            bubble_color = theme.assistant_bubble

        self.setStyleSheet(f"""
            MessageBubble {{
                background-color: {bubble_color};
                border-radius: {metrics.radius_medium}px;
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

    def show_typing(self) -> None:
        """Show typing indicator."""
        if self._typing_indicator is None:
            self._typing_indicator = TypingIndicator(self)
            self.layout().addWidget(self._typing_indicator)
        self._typing_indicator.start()
        self._typing_indicator.show()

    def hide_typing(self) -> None:
        """Hide typing indicator."""
        if self._typing_indicator:
            self._typing_indicator.stop()
            self._typing_indicator.hide()


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
        self.messages_container.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.background};
            }}
        """)
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(
            metrics.padding_xlarge,
            metrics.padding_large,
            metrics.padding_xlarge,
            metrics.padding_large,
        )
        self.messages_layout.setSpacing(metrics.padding_medium)
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
        bubble.show_typing()  # Show typing indicator
        self._current_assistant_bubble = bubble
        self._add_bubble(bubble)

    def append_to_assistant_message(self, text: str) -> None:
        """Append text to the current assistant message.

        Args:
            text: Text to append
        """
        if self._current_assistant_bubble:
            # Hide typing on first content
            if not self._current_assistant_bubble.content_label.text():
                self._current_assistant_bubble.hide_typing()
            self._current_assistant_bubble.append_content(text)
            self._scroll_to_bottom()

    def finish_assistant_message(self) -> None:
        """Mark the current assistant message as complete."""
        if self._current_assistant_bubble:
            self._current_assistant_bubble.hide_typing()
        self._current_assistant_bubble = None

    def add_error_message(self, error: str) -> None:
        """Add an error message to the chat.

        Args:
            error: Error text
        """
        # Hide typing if showing
        if self._current_assistant_bubble:
            self._current_assistant_bubble.hide_typing()

        bubble = MessageBubble("assistant", f"Error: {error}")
        bubble.content_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.error};
                font-size: {metrics.font_medium}px;
                font-family: {fonts.chat};
                background: transparent;
            }}
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
