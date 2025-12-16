"""Main application window."""

import asyncio
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QStatusBar,
    QLabel,
)
from PySide6.QtCore import Qt, QTimer

from .chat_panel import ChatPanel
from .input_panel import InputPanel
from ..config.settings import settings, MODELS
from ..config.themes import get_stylesheet, theme
from ..orchestrator.prompt_builder import PromptBuilder
from ..llm.anthropic_adapter import AnthropicAdapter
from ..llm.base_adapter import LLMAdapter
from ..utils.token_counter import TokenCounter


class MainWindow(QMainWindow):
    """Main application window for Synapse."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self._adapter: Optional[LLMAdapter] = None
        self._prompt_builder = PromptBuilder()
        self._token_counter = TokenCounter(settings.default_model)
        self._is_streaming = False

        self._setup_ui()
        self._setup_adapter()

    def _setup_ui(self) -> None:
        """Set up the main window UI."""
        # Window properties
        self.setWindowTitle(settings.window_title)
        self.resize(settings.window_width, settings.window_height)
        self.setMinimumSize(600, 400)

        # Apply stylesheet
        self.setStyleSheet(get_stylesheet())

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Chat panel
        self.chat_panel = ChatPanel()
        layout.addWidget(self.chat_panel, stretch=1)

        # Divider
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {theme.border};")
        layout.addWidget(divider)

        # Input panel
        self.input_panel = InputPanel()
        self.input_panel.message_submitted.connect(self._on_message_submitted)
        layout.addWidget(self.input_panel)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Token count label in status bar
        self.token_label = QLabel("Tokens: 0")
        self.token_label.setStyleSheet(f"""
            color: {theme.text_secondary};
            padding: 2px 8px;
        """)
        self.status_bar.addPermanentWidget(self.token_label)

        # Model label in status bar
        model_config = MODELS.get(settings.default_model)
        model_name = model_config.display_name if model_config else settings.default_model
        self.model_label = QLabel(f"Model: {model_name}")
        self.model_label.setStyleSheet(f"""
            color: {theme.text_secondary};
            padding: 2px 8px;
        """)
        self.status_bar.addPermanentWidget(self.model_label)

        # Focus input field after window is shown
        QTimer.singleShot(100, self.input_panel.focus_input)

    def _setup_adapter(self) -> None:
        """Set up the LLM adapter."""
        try:
            self._adapter = AnthropicAdapter(settings.default_model)
            self.status_bar.showMessage("Ready", 3000)
        except ValueError as e:
            self.status_bar.showMessage(str(e))
            self.chat_panel.add_error_message(str(e))
            self.input_panel.set_enabled(False)

    def _on_message_submitted(self, message: str) -> None:
        """Handle a submitted message.

        Args:
            message: The user's message
        """
        if self._is_streaming or not self._adapter:
            return

        # Add user message to UI and history
        self.chat_panel.add_user_message(message)
        self._prompt_builder.add_user_message(message)

        # Update token count
        self._update_token_count()

        # Start streaming response
        self._is_streaming = True
        self.input_panel.set_enabled(False)
        self.chat_panel.start_assistant_message()

        # Run the async stream in the event loop
        asyncio.ensure_future(self._stream_response())

    async def _stream_response(self) -> None:
        """Stream a response from the LLM."""
        if not self._adapter:
            return

        full_response = ""

        try:
            messages = self._prompt_builder.build_messages()
            system = self._prompt_builder.get_system_prompt()

            async for chunk in self._adapter.stream(messages, system):
                if chunk.text:
                    full_response += chunk.text
                    self.chat_panel.append_to_assistant_message(chunk.text)

                if chunk.is_final and chunk.usage:
                    # Update status with actual usage
                    self.status_bar.showMessage(
                        f"Input: {chunk.usage['input_tokens']} | "
                        f"Output: {chunk.usage['output_tokens']} tokens",
                        5000
                    )

            # Add complete response to history
            self._prompt_builder.add_assistant_message(full_response)
            self.chat_panel.finish_assistant_message()

        except Exception as e:
            error_msg = str(e)
            self.chat_panel.add_error_message(error_msg)
            self.status_bar.showMessage(f"Error: {error_msg}", 5000)

        finally:
            self._is_streaming = False
            self.input_panel.set_enabled(True)
            self.input_panel.focus_input()
            self._update_token_count()

    def _update_token_count(self) -> None:
        """Update the token count display."""
        messages = self._prompt_builder.build_messages()
        system = self._prompt_builder.get_system_prompt()
        total_tokens = self._token_counter.count_prompt(system, messages)
        self.token_label.setText(f"Tokens: {total_tokens:,}")

    def showEvent(self, event) -> None:
        """Handle window show event."""
        super().showEvent(event)
        # Ensure input has focus when window is shown
        QTimer.singleShot(0, self.input_panel.focus_input)
