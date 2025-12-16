"""Main application window."""

import asyncio
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStatusBar,
    QLabel,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence

from .chat_panel import ChatPanel
from .input_panel import InputPanel
from .sidebar import Sidebar
from ..config.settings import settings
from ..config.models import MODELS, get_model, get_available_models
from ..config.themes import get_stylesheet, theme
from ..orchestrator.prompt_builder import PromptBuilder
from ..orchestrator.context_manager import ContextManager, ContextState
from ..orchestrator.intent_tracker import IntentTracker
from ..orchestrator.waypoint_manager import WaypointManager
from ..summarization.summary_generator import SummaryGenerator
from ..summarization.drift_detector import DriftDetector
from ..llm.base_adapter import LLMAdapter
from ..llm.anthropic_adapter import AnthropicAdapter
from ..llm.openai_adapter import OpenAIAdapter
from ..llm.openrouter_adapter import OpenRouterAdapter
from ..llm.gabai_adapter import GabAIAdapter
from ..utils.token_counter import TokenCounter


class MainWindow(QMainWindow):
    """Main application window for Synapse."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self._adapter: Optional[LLMAdapter] = None
        self._current_model_id: str = ""
        self._prompt_builder = PromptBuilder()
        self._token_counter: Optional[TokenCounter] = None
        self._context_manager: Optional[ContextManager] = None
        self._intent_tracker = IntentTracker()
        self._waypoint_manager = WaypointManager()
        self._summary_generator = SummaryGenerator()
        self._drift_detector = DriftDetector()
        self._is_streaming = False
        self._summarization_in_progress = False

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_default_model()

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

        # Main horizontal layout (sidebar + chat)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.model_changed.connect(self._on_model_changed)
        self.sidebar.regenerate_requested.connect(self._on_regenerate_requested)
        main_layout.addWidget(self.sidebar)

        # Chat area
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Chat panel
        self.chat_panel = ChatPanel()
        chat_layout.addWidget(self.chat_panel, stretch=1)

        # Divider
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {theme.border};")
        chat_layout.addWidget(divider)

        # Input panel
        self.input_panel = InputPanel()
        self.input_panel.message_submitted.connect(self._on_message_submitted)
        chat_layout.addWidget(self.input_panel)

        main_layout.addWidget(chat_container, stretch=1)

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
        self.model_label = QLabel("Model: -")
        self.model_label.setStyleSheet(f"""
            color: {theme.text_secondary};
            padding: 2px 8px;
        """)
        self.status_bar.addPermanentWidget(self.model_label)

        # Intent label in status bar
        self.intent_label = QLabel("Mode: exploration")
        self.intent_label.setStyleSheet(f"""
            color: {theme.text_muted};
            padding: 2px 8px;
        """)
        self.status_bar.addPermanentWidget(self.intent_label)

        # Focus input field after window is shown
        QTimer.singleShot(100, self.input_panel.focus_input)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Ctrl+M - Set waypoint
        waypoint_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        waypoint_shortcut.activated.connect(self._on_set_waypoint)

        # Ctrl+R - Regenerate
        regenerate_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        regenerate_shortcut.activated.connect(self._on_regenerate_requested)

    def _setup_default_model(self) -> None:
        """Set up the default model."""
        available = get_available_models()
        if not available:
            self.status_bar.showMessage("No API keys configured")
            self.chat_panel.add_error_message(
                "No API keys configured. Please set ANTHROPIC_API_KEY, "
                "OPENAI_API_KEY, OPENROUTER_KEY, or GABAI_KEY environment variable."
            )
            self.input_panel.set_enabled(False)
            return

        # Try to use default model, or first available
        default_id = settings.default_model
        if not any(m.model_id == default_id for m in available):
            default_id = available[0].model_id

        self._switch_model(default_id)
        self.sidebar.set_model(default_id)

    def _switch_model(self, model_id: str) -> bool:
        """Switch to a different model.

        Args:
            model_id: The model ID to switch to

        Returns:
            True if switch was successful
        """
        model_config = get_model(model_id)
        if not model_config:
            self.status_bar.showMessage(f"Unknown model: {model_id}", 3000)
            return False

        try:
            # Create appropriate adapter
            if model_config.provider == "anthropic":
                self._adapter = AnthropicAdapter(model_id)
            elif model_config.provider == "openai":
                self._adapter = OpenAIAdapter(model_id)
            elif model_config.provider == "openrouter":
                self._adapter = OpenRouterAdapter(model_id)
            elif model_config.provider == "gabai":
                self._adapter = GabAIAdapter(model_id)
            else:
                raise ValueError(f"Unknown provider: {model_config.provider}")

            # Update token counter
            self._token_counter = TokenCounter(model_id)

            # Update context manager
            self._context_manager = ContextManager(
                context_window=model_config.context_window,
                threshold=0.80,
            )
            self._context_manager.on_summarize(self._on_summarization_needed)

            # Update current model
            self._current_model_id = model_id

            # Update UI
            self.model_label.setText(f"Model: {model_config.display_name}")
            self.status_bar.showMessage(
                f"Switched to {model_config.display_name}", 3000
            )

            # Update context display
            self._update_token_count()

            self.input_panel.set_enabled(True)
            return True

        except ValueError as e:
            self.status_bar.showMessage(str(e), 5000)
            return False

    def _on_model_changed(self, model_id: str) -> None:
        """Handle model selection change.

        Args:
            model_id: The new model ID
        """
        if model_id != self._current_model_id:
            self._switch_model(model_id)

    def _on_message_submitted(self, message: str) -> None:
        """Handle a submitted message.

        Args:
            message: The user's message
        """
        if self._is_streaming or not self._adapter:
            return

        # Update intent based on message
        intent_signal = self._intent_tracker.update(message)
        self._prompt_builder.set_intent_hint(self._intent_tracker.get_prompt_hint())
        self.intent_label.setText(f"Mode: {self._intent_tracker.current_mode.value}")

        # Check for drift
        drift_result = self._drift_detector.analyze_message(message)
        if drift_result.is_drift and self._context_manager:
            self._context_manager.signal_drift_detected()

        # Add user message to UI and history
        self.chat_panel.add_user_message(message)
        self._prompt_builder.add_user_message(message)

        # Update context manager with message count
        if self._context_manager:
            self._context_manager.update_message_counts(
                self._prompt_builder.get_message_count(),
                len(self._prompt_builder.history.get_summarized_messages())
            )

        # Update token count (this may trigger summarization)
        self._update_token_count()

        # Start streaming response
        self._is_streaming = True
        self.input_panel.set_enabled(False)
        self.sidebar.set_regenerate_enabled(False)
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
            self.sidebar.set_regenerate_enabled(
                self._prompt_builder.get_message_count() > 0
            )
            self.input_panel.focus_input()
            self._update_token_count()

    def _on_regenerate_requested(self) -> None:
        """Handle regenerate request."""
        if self._is_streaming or not self._adapter:
            return

        # Get last user message before removing
        last_user = self._prompt_builder.get_last_user_message()
        if not last_user:
            self.status_bar.showMessage("No message to regenerate", 3000)
            return

        # Remove last assistant response from history
        removed = self._prompt_builder.remove_last_assistant_message()
        if not removed:
            self.status_bar.showMessage("No response to regenerate", 3000)
            return

        # Remove from UI (remove last two bubbles - user and assistant)
        # Actually we just re-use the existing UI display
        # The prompt builder already has the user message re-added

        # Start streaming new response
        self._is_streaming = True
        self.input_panel.set_enabled(False)
        self.sidebar.set_regenerate_enabled(False)
        self.chat_panel.start_assistant_message()

        self.status_bar.showMessage("Regenerating response...", 2000)

        # Run the async stream
        asyncio.ensure_future(self._stream_response())

    def _on_set_waypoint(self) -> None:
        """Handle waypoint set request."""
        message_count = self._prompt_builder.get_message_count()
        if message_count == 0:
            return

        # Set waypoint at current position
        current_index = message_count - 1
        waypoint = self._waypoint_manager.add_waypoint(current_index)

        # Show brief confirmation
        self.status_bar.showMessage(
            f"Waypoint set at message {current_index + 1}", 2000
        )

    def _on_summarization_needed(self) -> None:
        """Handle summarization trigger from context manager."""
        if self._summarization_in_progress or not self._adapter:
            return

        asyncio.ensure_future(self._perform_summarization())

    async def _perform_summarization(self) -> None:
        """Perform context summarization in the background."""
        if self._summarization_in_progress:
            return

        self._summarization_in_progress = True

        try:
            # Get waypoint boundary if any
            boundary = self._waypoint_manager.get_summarization_boundary(
                self._prompt_builder.get_message_count()
            )

            # Get messages to summarize
            messages = self._prompt_builder.get_messages_for_summarization(boundary)
            if not messages:
                return

            # Get the highest index being summarized
            highest_index = self._prompt_builder.get_highest_summarizable_index(boundary)
            if highest_index < 0:
                return

            # Generate summary
            result = await self._summary_generator.generate_summary(
                messages=messages,
                adapter=self._adapter,
                intent_mode=self._intent_tracker.current_mode,
            )

            if result.success:
                # Set summary in prompt builder
                self._prompt_builder.set_summary(result.xml_summary)

                # Mark messages as summarized
                self._prompt_builder.mark_messages_summarized(highest_index)

                # Update context manager
                if self._context_manager:
                    self._context_manager.mark_messages_summarized(
                        len(self._prompt_builder.history.get_summarized_messages())
                    )
                    self._context_manager.clear_drift_signal()

                # Clear waypoints that were summarized past
                self._waypoint_manager.clear_summarized_waypoints(highest_index)

                # Reset drift detector with remaining messages
                active_messages = self._prompt_builder.history.get_active_messages()
                self._drift_detector.force_recalculate_centroid(
                    [m.content for m in active_messages]
                )

                # Update token count
                self._update_token_count()

                # Silent - user should not see interruption

        except Exception as e:
            # Log error but don't interrupt user
            self.status_bar.showMessage(f"Summarization failed: {e}", 3000)

        finally:
            self._summarization_in_progress = False

    def _update_token_count(self) -> None:
        """Update the token count display and check thresholds."""
        if not self._token_counter or not self._context_manager:
            return

        # Count tokens for active messages only
        messages = self._prompt_builder.build_messages()
        system = self._prompt_builder.get_system_prompt()
        total_tokens = self._token_counter.count_prompt(system, messages)

        # Update displays
        self.token_label.setText(f"Tokens: {total_tokens:,}")

        # Update context manager (may trigger summarization)
        self._context_manager.update_token_count(total_tokens)

        # Update sidebar indicator
        self.sidebar.update_context(
            total_tokens,
            self._context_manager.context_window
        )

    def showEvent(self, event) -> None:
        """Handle window show event."""
        super().showEvent(event)
        # Ensure input has focus when window is shown
        QTimer.singleShot(0, self.input_panel.focus_input)
