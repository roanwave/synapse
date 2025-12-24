"""Premium input panel for user message entry."""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QColor

from ..config.themes import theme, fonts, metrics


class MessageInput(QTextEdit):
    """Premium text input with focus states and smooth styling."""

    submit_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize the message input.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setPlaceholderText("Type your message... (Ctrl+Enter to send)")
        self.setAcceptRichText(False)
        self.setMinimumHeight(56)
        self.setMaximumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Premium styling with focus states
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_large}px;
                padding: {metrics.padding_medium}px {metrics.padding_large}px;
                font-family: {fonts.chat};
                font-size: {metrics.font_medium}px;
                selection-background-color: {theme.selection};
            }}
            QTextEdit:focus {{
                border: 2px solid {theme.border_focus};
                background-color: #1f1f28;
            }}
            QTextEdit:disabled {{
                background-color: {theme.background_tertiary};
                color: {theme.text_disabled};
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
    """Premium panel containing the message input and send button."""

    message_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        """Initialize the input panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the premium panel UI."""
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

        # Premium send button with hover effects
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumWidth(88)
        self.send_button.setMinimumHeight(48)
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self._on_submit)

        # Premium button styling with gradient-like effect
        self.send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_medium}px;
                font-weight: 600;
                font-size: {metrics.font_medium}px;
                font-family: {fonts.ui};
                padding: 0 {metrics.padding_xlarge}px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {theme.accent_pressed};
            }}
            QPushButton:disabled {{
                background-color: {theme.border};
                color: {theme.text_disabled};
            }}
        """)
        layout.addWidget(self.send_button, alignment=Qt.AlignmentFlag.AlignBottom)

        # Premium panel styling - elevated from background
        self.setStyleSheet(f"""
            InputPanel {{
                background-color: {theme.background_secondary};
                border-top: 1px solid {theme.border_subtle};
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
