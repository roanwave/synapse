"""Chat panel for displaying conversation history - Premium styling."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QSizePolicy,
    QTextBrowser,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, QPoint
from PySide6.QtGui import QFont, QDesktopServices

from ..config.themes import theme, fonts, metrics
from ..utils.markdown_renderer import render_markdown


class TypingIndicator(QWidget):
    """Premium animated typing indicator (three pulsing dots with wave effect)."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the typing indicator.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._dots: list[QLabel] = []
        self._timers: list[QTimer] = []
        self._current_states: list[bool] = [False, False, False]
        self._animation_index = 0
        self._wave_timer: QTimer | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(6)

        # Create three dots with premium styling
        for i in range(3):
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"""
                QLabel {{
                    background-color: {theme.text_muted};
                    border-radius: 4px;
                }}
            """)
            self._dots.append(dot)
            layout.addWidget(dot)

        layout.addStretch()
        self.setFixedHeight(24)

    def start(self) -> None:
        """Start the wave animation."""
        self._animation_index = 0
        self._wave_timer = QTimer(self)
        self._wave_timer.timeout.connect(self._wave_step)
        self._wave_timer.start(150)  # Fast wave effect

    def stop(self) -> None:
        """Stop the animation."""
        if self._wave_timer:
            self._wave_timer.stop()
            self._wave_timer = None

        # Reset all dots to dim
        for dot in self._dots:
            dot.setStyleSheet(f"""
                QLabel {{
                    background-color: {theme.text_muted};
                    border-radius: 4px;
                }}
            """)

    def _wave_step(self) -> None:
        """Animate one step of the wave."""
        # Reset previous dot
        prev_index = (self._animation_index - 1) % 3
        self._dots[prev_index].setStyleSheet(f"""
            QLabel {{
                background-color: {theme.text_muted};
                border-radius: 4px;
            }}
        """)

        # Light up current dot with accent color
        self._dots[self._animation_index].setStyleSheet(f"""
            QLabel {{
                background-color: {theme.accent};
                border-radius: 4px;
            }}
        """)

        self._animation_index = (self._animation_index + 1) % 3


class MessageBubble(QFrame):
    """Premium message bubble with gradient backgrounds and shadows."""

    def __init__(self, role: str, content: str = "", parent: QWidget | None = None):
        """Initialize the message bubble.

        Args:
            role: "user" or "assistant"
            content: Initial message content
            parent: Parent widget
        """
        super().__init__(parent)
        self.role = role
        self._raw_content = content
        self._typing_indicator: TypingIndicator | None = None
        self._setup_ui(content)

    def _setup_ui(self, content: str) -> None:
        """Set up the bubble UI with premium styling."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Role label - subtle, premium
        role_text = "You" if self.role == "user" else "Synapse"
        role_label = QLabel(role_text)
        role_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: 11px;
                font-weight: 600;
                font-family: {fonts.ui};
                background: transparent;
                letter-spacing: 0.3px;
            }}
        """)
        layout.addWidget(role_label)

        # Content container for styling
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Content browser (supports HTML/markdown rendering)
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setOpenLinks(False)
        self.content_browser.anchorClicked.connect(self._on_link_clicked)

        # Remove all internal document margins
        self.content_browser.document().setDocumentMargin(0)

        # Premium styling based on role
        if self.role == "user":
            # User messages: Gradient background with shadow
            content_frame.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 {theme.user_bubble_start},
                        stop:1 {theme.user_bubble_end}
                    );
                    border-radius: {metrics.radius_large}px;
                    padding: {metrics.padding_medium}px {metrics.padding_large}px;
                }}
            """)
            self.content_browser.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: transparent;
                    border: none;
                    color: #ffffff;
                    font-size: {metrics.font_medium}px;
                    font-family: {fonts.chat};
                    selection-background-color: rgba(255, 255, 255, 0.3);
                    padding: 0;
                    margin: 0;
                }}
            """)
        else:
            # Assistant messages: Elevated surface with accent bar
            content_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme.assistant_bubble};
                    border: 1px solid {theme.border};
                    border-left: 3px solid {theme.accent};
                    border-radius: {metrics.radius_large}px;
                    padding: {metrics.padding_large}px 20px;
                }}
            """)
            self.content_browser.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: transparent;
                    border: none;
                    color: {theme.text_primary};
                    font-size: {metrics.font_medium}px;
                    font-family: {fonts.chat};
                    selection-background-color: {theme.selection};
                    padding: 0;
                    margin: 0;
                }}
            """)

        # Make it auto-resize to content
        self.content_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Set content
        if content:
            self._render_content(content)

        content_layout.addWidget(self.content_browser)
        layout.addWidget(content_frame)

        # Set max width based on role
        if self.role == "user":
            self.setMaximumWidth(800)  # 75% of typical width
        else:
            pass  # Assistant messages can be full width

        self.setStyleSheet("""
            MessageBubble {
                background-color: transparent;
                border: none;
            }
        """)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _render_content(self, content: str) -> None:
        """Render markdown content as HTML.

        Args:
            content: Markdown text to render
        """
        html = render_markdown(content, is_user=self.role == "user")
        self.content_browser.setHtml(html)

        # Adjust height to content
        self.content_browser.document().setTextWidth(self.content_browser.viewport().width())
        doc_height = self.content_browser.document().size().height()
        self.content_browser.setMinimumHeight(int(doc_height) + 4)

    def _on_link_clicked(self, url) -> None:
        """Handle link clicks by opening in external browser.

        Args:
            url: The clicked URL
        """
        QDesktopServices.openUrl(url)

    def set_content(self, content: str) -> None:
        """Update the bubble content.

        Args:
            content: New content text (markdown)
        """
        self._raw_content = content
        self._render_content(content)

    def append_content(self, text: str) -> None:
        """Append text to the bubble content.

        Args:
            text: Text to append (markdown)
        """
        self._raw_content += text
        self._render_content(self._raw_content)

    def get_raw_content(self) -> str:
        """Get the raw markdown content.

        Returns:
            Raw markdown text
        """
        return self._raw_content

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
    """Premium panel for displaying the conversation history."""

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
        """Set up the panel UI with premium styling."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area with premium styling
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
                background-color: {theme.background_secondary};
                border: none;
            }}
        """)

        # Container for messages
        self.messages_container = QWidget()
        self.messages_container.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.background_secondary};
            }}
        """)
        self.messages_layout = QVBoxLayout(self.messages_container)
        # Premium spacing
        self.messages_layout.setContentsMargins(24, 16, 24, 16)
        self.messages_layout.setSpacing(16)  # Good spacing between messages
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)

    def add_user_message(self, content: str) -> None:
        """Add a user message to the chat.

        Args:
            content: Message text
        """
        bubble = MessageBubble("user", content)
        self._add_bubble(bubble, align_right=True)

    def start_assistant_message(self) -> None:
        """Start a new assistant message for streaming."""
        bubble = MessageBubble("assistant", "")
        bubble.show_typing()
        self._current_assistant_bubble = bubble
        self._add_bubble(bubble)

    def append_to_assistant_message(self, text: str) -> None:
        """Append text to the current assistant message.

        Args:
            text: Text to append
        """
        if self._current_assistant_bubble:
            # Hide typing on first content
            if not self._current_assistant_bubble._raw_content:
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

        bubble = MessageBubble("assistant", f"**Error:** {error}")
        # Style with error color
        bubble.content_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                color: {theme.error};
                font-size: {metrics.font_medium}px;
                font-family: {fonts.chat};
                selection-background-color: {theme.selection};
                padding: 0;
                margin: 0;
            }}
        """)
        self._add_bubble(bubble)
        self._current_assistant_bubble = None

    def _add_bubble(self, bubble: MessageBubble, align_right: bool = False) -> None:
        """Add a bubble to the layout with optional alignment.

        Args:
            bubble: The message bubble to add
            align_right: Whether to align the bubble to the right (for user messages)
        """
        # Remove the stretch if this is the first message
        if not self._bubbles:
            item = self.messages_layout.takeAt(0)
            if item:
                del item

        self._bubbles.append(bubble)

        if align_right:
            # Create a container to align user messages to the right
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addStretch()
            container_layout.addWidget(bubble)
            self.messages_layout.addWidget(container)
        else:
            self.messages_layout.addWidget(bubble)

        # Add stretch after messages
        self.messages_layout.addStretch()

        # Scroll to bottom with smooth delay
        QTimer.singleShot(10, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        """Scroll the chat to the bottom."""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_system_message(self, content: str) -> None:
        """Add a system/info message to the chat.

        Args:
            content: Message text
        """
        bubble = MessageBubble("assistant", content)
        # Style as a system message - muted, subtle
        bubble.content_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                color: {theme.text_muted};
                font-size: {metrics.font_small}px;
                font-family: {fonts.chat};
                font-style: italic;
                selection-background-color: {theme.selection};
                padding: 0;
                margin: 0;
            }}
        """)
        self._add_bubble(bubble)

    def clear(self) -> None:
        """Clear all messages from the chat."""
        # Remove all widgets from layout
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._bubbles.clear()
        self._current_assistant_bubble = None

        # Re-add the stretch
        self.messages_layout.addStretch()
