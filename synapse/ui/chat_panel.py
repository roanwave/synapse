"""Chat panel for displaying conversation history - Premium styling."""

from datetime import datetime
from typing import Optional

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
    QPushButton,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QDesktopServices

from ..config.themes import theme, fonts, metrics
from ..utils.markdown_renderer import render_markdown, strip_markdown


def format_timestamp(dt: datetime) -> str:
    """Format a datetime for display.

    Returns:
        - "2:34 PM" for today
        - "Dec 23, 2:34 PM" for this year
        - "Dec 23 2024, 2:34 PM" for older
    """
    now = datetime.now()
    # Use %I and strip leading zero manually (cross-platform)
    time_str = dt.strftime("%I:%M %p").lstrip("0")

    if dt.date() == now.date():
        return time_str
    elif dt.year == now.year:
        return dt.strftime("%b %d, ") + time_str
    else:
        return dt.strftime("%b %d %Y, ") + time_str


class CopyButton(QPushButton):
    """Subtle copy button with hover effects and visual feedback."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the copy button.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._is_copied = False
        self._reset_timer: QTimer | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the button UI."""
        self.setText("Copy")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(24)
        self._apply_normal_style()

    def _apply_normal_style(self) -> None:
        """Apply normal (not copied) style."""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.text_muted};
                border: none;
                font-size: 11px;
                font-family: {fonts.ui};
                font-weight: 500;
                padding: 4px 8px;
                opacity: 0.5;
            }}
            QPushButton:hover {{
                color: {theme.text_primary};
                background-color: {theme.background_elevated};
                border-radius: 4px;
            }}
        """)

    def _apply_copied_style(self) -> None:
        """Apply copied feedback style."""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.success};
                color: white;
                border: none;
                font-size: 11px;
                font-family: {fonts.ui};
                font-weight: 500;
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)

    def show_copied_feedback(self) -> None:
        """Show copied visual feedback for 1.5 seconds."""
        self._is_copied = True
        self.setText("Copied!")
        self._apply_copied_style()

        # Reset after 1.5 seconds
        if self._reset_timer:
            self._reset_timer.stop()
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_state)
        self._reset_timer.start(1500)

    def _reset_state(self) -> None:
        """Reset to normal state."""
        self._is_copied = False
        self.setText("Copy")
        self._apply_normal_style()


class ForkButton(QPushButton):
    """Fork button that appears on hover to create conversation branches."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the fork button.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the button UI."""
        self.setText("Fork")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(24)
        self.setToolTip("Create a new conversation branch from this point")
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.text_muted};
                border: none;
                font-size: 11px;
                font-family: {fonts.ui};
                font-weight: 500;
                padding: 4px 8px;
                opacity: 0.5;
            }}
            QPushButton:hover {{
                color: {theme.accent};
                background-color: {theme.background_elevated};
                border-radius: 4px;
            }}
        """)


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

    # Signal emitted when fork button is clicked
    fork_requested = Signal()

    def __init__(
        self,
        role: str,
        content: str = "",
        timestamp: Optional[datetime] = None,
        parent: QWidget | None = None
    ):
        """Initialize the message bubble.

        Args:
            role: "user" or "assistant"
            content: Initial message content
            timestamp: Message timestamp (defaults to now)
            parent: Parent widget
        """
        super().__init__(parent)
        self.role = role
        self._raw_content = content
        self._timestamp = timestamp or datetime.now()
        self._typing_indicator: TypingIndicator | None = None
        self._copy_button: CopyButton | None = None
        self._fork_button: ForkButton | None = None
        self._setup_ui(content)

    def _setup_ui(self, content: str) -> None:
        """Set up the bubble UI with premium styling."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header row with role label, timestamp, and copy button
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

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
        header_row.addWidget(role_label)

        # Timestamp label
        timestamp_text = format_timestamp(self._timestamp)
        self._timestamp_label = QLabel(timestamp_text)
        self._timestamp_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_disabled};
                font-size: 11px;
                font-family: {fonts.ui};
                background: transparent;
            }}
        """)
        header_row.addWidget(self._timestamp_label)

        header_row.addStretch()

        # Fork button
        self._fork_button = ForkButton()
        self._fork_button.clicked.connect(self._on_fork_clicked)
        header_row.addWidget(self._fork_button)

        # Copy button
        self._copy_button = CopyButton()
        self._copy_button.clicked.connect(self._on_copy_clicked)
        header_row.addWidget(self._copy_button)

        layout.addLayout(header_row)

        # Content container for styling
        self._content_frame = QFrame()
        content_layout = QVBoxLayout(self._content_frame)
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
            self._content_frame.setStyleSheet(f"""
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
            self._content_frame.setStyleSheet(f"""
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
        layout.addWidget(self._content_frame)

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

    def _on_copy_clicked(self) -> None:
        """Handle copy button click."""
        # Get plain text content (strip markdown)
        plain_text = strip_markdown(self._raw_content)

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(plain_text)

        # Show feedback
        if self._copy_button:
            self._copy_button.show_copied_feedback()

    def _on_fork_clicked(self) -> None:
        """Handle fork button click."""
        self.fork_requested.emit()

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


class ScrollToBottomButton(QPushButton):
    """Button that appears when user scrolls up during generation."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the scroll button.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        """Set up the button UI."""
        self.setText("↓ New content")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_medium}px;
                font-size: 12px;
                font-family: {fonts.ui};
                font-weight: 500;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        self.adjustSize()


class ChatPanel(QWidget):
    """Premium panel for displaying the conversation history."""

    # Signal emitted when current visible message changes (for TOC)
    visible_message_changed = Signal(int)  # message_index
    # Signal emitted when fork is requested from a message
    fork_requested = Signal(int)  # message_index

    def __init__(self, parent: QWidget | None = None):
        """Initialize the chat panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._bubbles: list[MessageBubble] = []
        self._message_indices: dict[MessageBubble, int] = {}  # Bubble -> message index
        self._current_assistant_bubble: MessageBubble | None = None
        self._user_scrolled_up = False
        self._is_generating = False
        self._next_message_index = 0
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

        # Connect scroll events for scroll lock
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.valueChanged.connect(self._on_scroll_changed)

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

        # Scroll to bottom button (initially hidden)
        self._scroll_button = ScrollToBottomButton(self)
        self._scroll_button.clicked.connect(self._on_scroll_button_clicked)

    def resizeEvent(self, event) -> None:
        """Handle resize to position scroll button."""
        super().resizeEvent(event)
        self._position_scroll_button()

    def _position_scroll_button(self) -> None:
        """Position the scroll button at bottom center."""
        if self._scroll_button:
            btn_width = self._scroll_button.width()
            x = (self.width() - btn_width) // 2
            y = self.height() - 60
            self._scroll_button.move(x, y)

    def _on_scroll_changed(self, value: int) -> None:
        """Handle scroll position changes."""
        scrollbar = self.scroll_area.verticalScrollBar()
        at_bottom = (scrollbar.maximum() - value) < 50  # Within 50px of bottom

        if self._is_generating:
            if at_bottom:
                self._user_scrolled_up = False
                self._scroll_button.hide()
            else:
                self._user_scrolled_up = True
                self._scroll_button.show()
                self._position_scroll_button()

    def _on_scroll_button_clicked(self) -> None:
        """Handle scroll button click."""
        self._user_scrolled_up = False
        self._scroll_button.hide()
        self._scroll_to_bottom()

    def add_user_message(
        self,
        content: str,
        timestamp: Optional[datetime] = None
    ) -> int:
        """Add a user message to the chat.

        Args:
            content: Message text
            timestamp: Message timestamp (defaults to now)

        Returns:
            Message index
        """
        bubble = MessageBubble("user", content, timestamp=timestamp)
        message_index = self._next_message_index
        self._message_indices[bubble] = message_index
        self._next_message_index += 1

        # Connect fork signal
        bubble.fork_requested.connect(
            lambda idx=message_index: self.fork_requested.emit(idx)
        )

        self._add_bubble(bubble, align_right=True)
        return message_index

    def start_assistant_message(
        self,
        timestamp: Optional[datetime] = None
    ) -> int:
        """Start a new assistant message for streaming.

        Args:
            timestamp: Message timestamp (defaults to now)

        Returns:
            Message index
        """
        self._is_generating = True
        self._user_scrolled_up = False
        bubble = MessageBubble("assistant", "", timestamp=timestamp)
        bubble.show_typing()
        self._current_assistant_bubble = bubble
        message_index = self._next_message_index
        self._message_indices[bubble] = message_index
        self._next_message_index += 1

        # Connect fork signal
        bubble.fork_requested.connect(
            lambda idx=message_index: self.fork_requested.emit(idx)
        )

        self._add_bubble(bubble)
        return message_index

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

            # Only auto-scroll if user hasn't scrolled up
            if not self._user_scrolled_up:
                self._scroll_to_bottom()

    def finish_assistant_message(self) -> None:
        """Mark the current assistant message as complete."""
        self._is_generating = False
        self._user_scrolled_up = False
        self._scroll_button.hide()
        if self._current_assistant_bubble:
            self._current_assistant_bubble.hide_typing()
        self._current_assistant_bubble = None

    def add_error_message(self, error: str) -> None:
        """Add an error message to the chat.

        Args:
            error: Error text
        """
        self._is_generating = False
        self._scroll_button.hide()

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
        self._message_indices.clear()
        self._next_message_index = 0
        self._current_assistant_bubble = None
        self._is_generating = False
        self._user_scrolled_up = False
        self._scroll_button.hide()

        # Re-add the stretch
        self.messages_layout.addStretch()

    def scroll_to_message(self, message_index: int) -> None:
        """Scroll to a specific message by its index.

        Args:
            message_index: The index of the message to scroll to
        """
        # Find the bubble with this index
        for bubble, idx in self._message_indices.items():
            if idx == message_index:
                # Scroll to show this bubble
                self.scroll_area.ensureWidgetVisible(bubble, 0, 50)
                return

    def get_message_count(self) -> int:
        """Get the total number of messages.

        Returns:
            Number of messages
        """
        return self._next_message_index

    def remove_last_assistant_message(self) -> Optional[str]:
        """Remove the last assistant message bubble.

        Returns:
            The content of the removed message, or None if no message found
        """
        # Find and remove the last assistant bubble
        for bubble in reversed(self._bubbles):
            if bubble.role == "assistant":
                try:
                    content = bubble._raw_content
                except RuntimeError:
                    # Widget already deleted
                    content = ""

                # Clear current bubble reference if this is it
                if bubble is self._current_assistant_bubble:
                    self._current_assistant_bubble = None

                # Remove from tracking
                self._bubbles.remove(bubble)
                if bubble in self._message_indices:
                    del self._message_indices[bubble]

                # Safely delete widget
                try:
                    bubble.setParent(None)
                    bubble.deleteLater()
                except RuntimeError:
                    pass  # Already deleted

                return content
        return None

    def remove_last_exchange(self) -> bool:
        """Remove the last user-assistant message exchange.

        Returns:
            True if exchange was removed, False otherwise
        """
        # Find last assistant
        assistant_bubble = None
        user_bubble = None

        for bubble in reversed(self._bubbles):
            try:
                role = bubble.role
            except RuntimeError:
                continue  # Skip deleted widgets

            if role == "assistant" and assistant_bubble is None:
                assistant_bubble = bubble
            elif role == "user" and assistant_bubble is not None:
                user_bubble = bubble
                break

        if assistant_bubble and user_bubble:
            # Clear current bubble reference if applicable
            if assistant_bubble is self._current_assistant_bubble:
                self._current_assistant_bubble = None

            # Remove from tracking lists first
            if assistant_bubble in self._bubbles:
                self._bubbles.remove(assistant_bubble)
            if user_bubble in self._bubbles:
                self._bubbles.remove(user_bubble)
            if assistant_bubble in self._message_indices:
                del self._message_indices[assistant_bubble]
            if user_bubble in self._message_indices:
                del self._message_indices[user_bubble]

            # Safely delete widgets
            for bubble in [assistant_bubble, user_bubble]:
                try:
                    bubble.setParent(None)
                    bubble.deleteLater()
                except RuntimeError:
                    pass  # Already deleted

            return True

        return False

    def get_current_assistant_content(self) -> Optional[str]:
        """Get the content of the currently streaming assistant message.

        Returns:
            Current content or None if not streaming
        """
        if self._current_assistant_bubble:
            return self._current_assistant_bubble._raw_content
        return None
