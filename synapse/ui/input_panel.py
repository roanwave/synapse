"""Input panel for user message entry."""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

from ..config.themes import theme, fonts, metrics


class MessageInput(QTextEdit):
    """Custom text edit that handles Ctrl+Enter for sending."""

    submit_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize the message input.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setPlaceholderText("Type your message... (Ctrl+Enter to send)")
        self.setAcceptRichText(False)
        self.setMinimumHeight(60)
        self.setMaximumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Apply styling - input field should be the brightest, most prominent
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: {metrics.padding_medium}px;
                font-family: {fonts.chat};
                font-size: {metrics.font_medium}px;
                selection-background-color: {theme.accent};
            }}
            QTextEdit:focus {{
                border-color: {theme.accent};
                background-color: #2A2A2A;
            }}
            QTextEdit:disabled {{
                background-color: {theme.background_tertiary};
                color: {theme.text_muted};
                border-color: {theme.border_subtle};
            }}
        """)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events.

        Args:
            event: The key event
        """
        # Check for Ctrl+Enter
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.submit_requested.emit()
            return

        super().keyPressEvent(event)


class InputPanel(QWidget):
    """Panel containing the message input and send button."""

    message_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        """Initialize the input panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            metrics.padding_xlarge,
            metrics.padding_medium,
            metrics.padding_xlarge,
            metrics.padding_large,
        )
        layout.setSpacing(metrics.padding_medium)

        # Message input
        self.input_field = MessageInput()
        self.input_field.submit_requested.connect(self._on_submit)
        layout.addWidget(self.input_field)

        # Send button - prominent accent color
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumWidth(80)
        self.send_button.setMinimumHeight(44)
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self._on_submit)
        self.send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_medium}px;
                font-weight: 600;
                font-size: {metrics.font_medium}px;
                font-family: {fonts.ui};
                padding: 0 {metrics.padding_large}px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {theme.accent_pressed};
            }}
            QPushButton:disabled {{
                background-color: {theme.border};
                color: {theme.text_muted};
            }}
        """)
        layout.addWidget(self.send_button, alignment=Qt.AlignmentFlag.AlignBottom)

        # Panel styling
        self.setStyleSheet(f"""
            InputPanel {{
                background-color: {theme.background};
            }}
        """)

    def _on_submit(self) -> None:
        """Handle message submission."""
        text = self.input_field.toPlainText().strip()
        if text:
            self.message_submitted.emit(text)
            self.input_field.clear()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the input.

        Args:
            enabled: Whether input should be enabled
        """
        self.input_field.setEnabled(enabled)
        self.send_button.setEnabled(enabled)

        # Update send button text during generation
        if enabled:
            self.send_button.setText("Send")
        else:
            self.send_button.setText("...")

    def focus_input(self) -> None:
        """Set focus to the input field."""
        self.input_field.setFocus()

    def get_text(self) -> str:
        """Get the current input text.

        Returns:
            The input text
        """
        return self.input_field.toPlainText()

    def clear(self) -> None:
        """Clear the input field."""
        self.input_field.clear()
