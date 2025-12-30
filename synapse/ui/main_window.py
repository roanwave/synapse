"""Main application window."""

import asyncio
import traceback
from typing import Optional, List, Dict, Any, Set
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStatusBar,
    QLabel,
    QMenuBar,
    QMenu,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence, QAction

from .chat_panel import ChatPanel
from .input_panel import InputPanel
from .sidebar import Sidebar
from .inspector import InspectorPanel
from .side_panel import SidePanel
from .memory_panel import MemoryPanel
from .scratchpad_panel import ScratchpadPanel
from .dialogs import ExitDialog, ExitAction, HelpDialog, AboutDialog, SessionBrowserDialog, NotificationToast, SummaryViewerDialog, ConversationSearchDialog
from ..config.settings import settings
from ..config.models import MODELS, get_model, get_available_models
from ..config.themes import get_stylesheet, theme, fonts, metrics
from ..config.persistence import persistence
from ..orchestrator.prompt_builder import PromptBuilder
from ..orchestrator.context_manager import ContextManager, ContextState
from ..orchestrator.intent_tracker import IntentTracker
from ..orchestrator.waypoint_manager import WaypointManager
from ..orchestrator.toc_generator import TOCGenerator
from ..orchestrator.parallel_context import ParallelContextManager
from ..summarization.summary_generator import SummaryGenerator
from ..summarization.drift_detector import DriftDetector
from ..summarization.artifact_generator import ArtifactGenerator
from ..llm.base_adapter import LLMAdapter
from ..llm.anthropic_adapter import AnthropicAdapter
from ..llm.openai_adapter import OpenAIAdapter
from ..llm.openrouter_adapter import OpenRouterAdapter
from ..llm.gabai_adapter import GabAIAdapter
from ..utils.token_counter import TokenCounter
from ..utils.youtube_handler import (
    contains_youtube_url,
    extract_video_id,
    fetch_transcript,
    estimate_transcript_tokens,
)
from ..utils.export import export_to_markdown, generate_export_filename
from ..storage import SessionRecord
from ..storage.vector_store_client import FAISSVectorStore
from ..storage.bm25_client import BM25Client, reciprocal_rank_fusion
from ..storage.document_indexer import DocumentIndexer
from ..storage.retrieval_blacklist import RetrievalBlacklist
from ..storage.conversation_store import ConversationStore
from ..storage.conversation_indexer import ConversationIndexer
from ..storage.unified_memory import UnifiedMemory


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
        self._toc_generator = TOCGenerator()
        self._summary_generator = SummaryGenerator()
        self._drift_detector = DriftDetector()
        self._artifact_generator = ArtifactGenerator()
        self._is_streaming = False
        self._interrupt_requested = False
        self._summarization_in_progress = False
        self._focus_mode = False

        # Async task tracking and concurrency control
        self._active_tasks: Set[asyncio.Task] = set()
        self._streaming_lock = asyncio.Lock()
        self._summarization_lock = asyncio.Lock()
        self._indexing_lock = asyncio.Lock()

        # RAG components (initialized lazily when first document added)
        self._vector_store: Optional[FAISSVectorStore] = None
        self._bm25_client: Optional[BM25Client] = None
        self._document_indexer: Optional[DocumentIndexer] = None
        self._retrieval_blacklist: Optional[RetrievalBlacklist] = None
        self._rag_initialized = False

        # Inspector panel
        self._inspector_panel: Optional[InspectorPanel] = None

        # Side panel for quick questions
        self._side_panel: Optional[SidePanel] = None
        self._parallel_context = ParallelContextManager()
        self._side_streaming = False

        # Session tracking
        self._session_record = SessionRecord.create()
        self._conversation_store = ConversationStore(
            settings.conversations_dir / "sessions.jsonl"
        )

        # Unified memory (persistent facts)
        self._unified_memory = UnifiedMemory(
            settings.app_data_dir / "unified_memory.json"
        )
        self._loaded_session_summary: Optional[str] = None  # Summary from loaded session

        # Conversation indexer for semantic search
        self._conversation_indexer: Optional[ConversationIndexer] = None
        self._search_dialog: Optional[ConversationSearchDialog] = None

        # Crucible integration
        self._crucible_enabled = False
        self._crucible_router = "Auto"
        self._crucible_adapter = None  # Lazy initialization

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_default_model()
        self._setup_crucible_state()

    def _setup_ui(self) -> None:
        """Set up the main window UI."""
        # Window properties
        self.setWindowTitle(settings.window_title)
        self.setMinimumSize(600, 400)

        # Restore window state from preferences
        prefs = persistence.preferences
        self.move(prefs.window.x, prefs.window.y)
        self.resize(prefs.window.width, prefs.window.height)
        if prefs.window.maximized:
            self.showMaximized()

        # Restore focus mode state
        self._focus_mode = prefs.focus_mode

        # Apply stylesheet
        self.setStyleSheet(get_stylesheet())

        # Set up menu bar
        self._setup_menu_bar()

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
        self.sidebar.document_added.connect(self._on_document_added)
        self.sidebar.document_removed.connect(self._on_document_removed)
        self.sidebar.documents_cleared.connect(self._on_documents_cleared)
        self.sidebar.inspector_toggled.connect(self._on_inspector_toggled)
        self.sidebar.jump_to_message.connect(self._on_jump_to_message)
        self.sidebar.crucible_toggled.connect(self._on_crucible_toggled)
        self.sidebar.crucible_router_changed.connect(self._on_crucible_router_changed)
        main_layout.addWidget(self.sidebar)

        # Chat area
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Chat panel
        self.chat_panel = ChatPanel()
        self.chat_panel.fork_requested.connect(self._on_fork_requested)
        chat_layout.addWidget(self.chat_panel, stretch=1)

        # Premium divider
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {theme.border_subtle};")
        chat_layout.addWidget(divider)

        # Scratchpad panel (collapsible, above input)
        self._scratchpad_panel = ScratchpadPanel()
        self._scratchpad_panel.content_changed.connect(self._on_scratchpad_changed)
        chat_layout.addWidget(self._scratchpad_panel)

        # Input panel
        self.input_panel = InputPanel()
        self.input_panel.message_submitted.connect(self._on_message_submitted)
        chat_layout.addWidget(self.input_panel)

        main_layout.addWidget(chat_container, stretch=1)

        # Inspector panel (hidden by default)
        self._inspector_panel = InspectorPanel()
        self._inspector_panel.closed.connect(self._on_inspector_closed)
        self._inspector_panel.hide()
        main_layout.addWidget(self._inspector_panel)

        # Side panel for quick questions (hidden by default)
        self._side_panel = SidePanel()
        self._side_panel.closed.connect(self._on_side_panel_closed)
        self._side_panel.merge_requested.connect(self._on_side_panel_merge)
        self._side_panel.input_panel.message_submitted.connect(self._on_side_message_submitted)
        self._side_panel.hide()
        main_layout.addWidget(self._side_panel)

        # Premium status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {theme.background_tertiary};
                border-top: 1px solid {theme.border_subtle};
                font-family: {fonts.ui};
                font-size: {metrics.font_small}px;
                color: {theme.text_muted};
            }}
        """)
        self.setStatusBar(self.status_bar)

        # Token count label in status bar
        self.token_label = QLabel("Tokens: 0")
        self.token_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                padding: 4px {metrics.padding_medium}px;
                font-family: {fonts.mono};
                font-size: {metrics.font_small}px;
                font-weight: 500;
            }}
        """)
        self.status_bar.addPermanentWidget(self.token_label)

        # Model label in status bar
        self.model_label = QLabel("Model: -")
        self.model_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                padding: 4px {metrics.padding_medium}px;
                font-size: {metrics.font_small}px;
            }}
        """)
        self.status_bar.addPermanentWidget(self.model_label)

        # Intent label in status bar - with accent color
        self.intent_label = QLabel("Mode: exploration")
        self.intent_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.accent};
                padding: 4px {metrics.padding_medium}px;
                font-size: {metrics.font_small}px;
                font-weight: 500;
            }}
        """)
        self.status_bar.addPermanentWidget(self.intent_label)

        # Apply initial focus mode state (after all UI is created)
        if self._focus_mode:
            self.sidebar.hide()

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

        # Ctrl+I - Toggle inspector
        inspector_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        inspector_shortcut.activated.connect(self._on_toggle_inspector)

        # Ctrl+N - New conversation
        new_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_shortcut.activated.connect(self._on_new_conversation)

        # Ctrl+F - Toggle focus mode
        focus_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        focus_shortcut.activated.connect(self._on_toggle_focus_mode)

        # Escape - Close inspector or exit focus mode
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._on_escape_pressed)

        # F1 - Show help dialog
        help_shortcut = QShortcut(QKeySequence("F1"), self)
        help_shortcut.activated.connect(self._on_show_help)

        # Ctrl+S - Save session
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self._on_save_session)

        # Ctrl+Q - Toggle side panel for quick questions
        side_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        side_shortcut.activated.connect(self._on_toggle_side_panel)

        # ESC - Interrupt generation
        interrupt_shortcut = QShortcut(QKeySequence("Escape"), self)
        interrupt_shortcut.activated.connect(self._on_interrupt_generation)

        # Ctrl+Z - Rollback last exchange
        rollback_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        rollback_shortcut.activated.connect(self._on_rollback_last_exchange)

    def _setup_menu_bar(self) -> None:
        """Set up the premium main menu bar."""
        menu_bar = self.menuBar()

        # Premium menu bar styling
        menu_bar.setStyleSheet(f"""
            QMenuBar {{
                background-color: {theme.background_tertiary};
                color: {theme.text_primary};
                border-bottom: 1px solid {theme.border_subtle};
                padding: 2px 0;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QMenuBar::item {{
                padding: 6px 14px;
                background-color: transparent;
                border-radius: {metrics.radius_small}px;
                margin: 2px 2px;
            }}
            QMenuBar::item:selected {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
            }}
            QMenuBar::item:pressed {{
                background-color: {theme.accent};
                color: white;
            }}
            QMenu {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: {metrics.padding_small}px;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QMenu::item {{
                padding: {metrics.padding_small}px {metrics.padding_xlarge}px {metrics.padding_small}px {metrics.padding_medium}px;
                border-radius: {metrics.radius_small}px;
            }}
            QMenu::item:selected {{
                background-color: {theme.accent};
                color: white;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {theme.border_subtle};
                margin: {metrics.padding_small}px {metrics.padding_medium}px;
            }}
        """)

        # === File Menu ===
        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New Chat", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_conversation)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Session...", self)
        open_action.triggered.connect(self._on_open_session)
        file_menu.addAction(open_action)

        save_action = QAction("&Save Session", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save_session)
        file_menu.addAction(save_action)

        export_action = QAction("&Export Chat...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export_chat)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # === Edit Menu ===
        edit_menu = menu_bar.addMenu("&Edit")

        clear_docs_action = QAction("Clear &Documents", self)
        clear_docs_action.triggered.connect(self._on_menu_clear_documents)
        edit_menu.addAction(clear_docs_action)

        edit_menu.addSeparator()

        waypoint_action = QAction("Set &Waypoint", self)
        waypoint_action.setShortcut("Ctrl+M")
        waypoint_action.triggered.connect(self._on_set_waypoint)
        edit_menu.addAction(waypoint_action)

        regenerate_action = QAction("&Regenerate Response", self)
        regenerate_action.setShortcut("Ctrl+R")
        regenerate_action.triggered.connect(self._on_regenerate_requested)
        edit_menu.addAction(regenerate_action)

        edit_menu.addSeparator()

        search_action = QAction("&Search Conversations...", self)
        search_action.setShortcut("Ctrl+Shift+F")
        search_action.triggered.connect(self._on_search_conversations)
        edit_menu.addAction(search_action)

        edit_menu.addSeparator()

        rollback_action = QAction("&Rollback Last Exchange", self)
        rollback_action.setShortcut("Ctrl+Z")
        rollback_action.triggered.connect(self._on_rollback_last_exchange)
        edit_menu.addAction(rollback_action)

        # === View Menu ===
        view_menu = menu_bar.addMenu("&View")

        focus_action = QAction("&Focus Mode", self)
        focus_action.setShortcut("Ctrl+F")
        focus_action.triggered.connect(self._on_toggle_focus_mode)
        view_menu.addAction(focus_action)

        inspector_action = QAction("Prompt &Inspector", self)
        inspector_action.setShortcut("Ctrl+I")
        inspector_action.triggered.connect(self._on_toggle_inspector)
        view_menu.addAction(inspector_action)

        sidebar_action = QAction("Toggle &Sidebar", self)
        sidebar_action.triggered.connect(self._on_toggle_sidebar)
        view_menu.addAction(sidebar_action)

        side_action = QAction("Side &Question Panel", self)
        side_action.setShortcut("Ctrl+Q")
        side_action.triggered.connect(self._on_toggle_side_panel)
        view_menu.addAction(side_action)

        view_menu.addSeparator()

        summary_action = QAction("View Session &Summary", self)
        summary_action.triggered.connect(self._on_view_summary)
        view_menu.addAction(summary_action)

        memory_action = QAction("&Memory...", self)
        memory_action.setShortcut("Ctrl+M")
        memory_action.triggered.connect(self._on_view_memory)
        view_menu.addAction(memory_action)

        # === Help Menu ===
        help_menu = menu_bar.addMenu("&Help")

        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self._on_show_help)
        help_menu.addAction(shortcuts_action)

        about_action = QAction("&About Synapse", self)
        about_action.triggered.connect(self._on_show_about)
        help_menu.addAction(about_action)

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

        # Try to use persisted model, then default, then first available
        prefs = persistence.preferences
        default_id = prefs.last_model
        if not any(m.model_id == default_id for m in available):
            default_id = settings.default_model
        if not any(m.model_id == default_id for m in available):
            default_id = available[0].model_id

        self._switch_model(default_id)
        self.sidebar.set_model(default_id)

    # ==================== Task Management ====================

    def _create_task(self, coro, name: str = "") -> asyncio.Task:
        """Create a tracked async task with error handling.

        Args:
            coro: Coroutine to run
            name: Optional task name for debugging

        Returns:
            The created task
        """
        task = asyncio.create_task(coro)
        if name:
            task.set_name(name)
        self._active_tasks.add(task)
        task.add_done_callback(self._on_task_done)
        return task

    def _on_task_done(self, task: asyncio.Task) -> None:
        """Handle task completion and exceptions.

        Args:
            task: The completed task
        """
        # Remove from active set
        self._active_tasks.discard(task)

        # Check for exceptions (but not cancellation)
        if task.cancelled():
            return

        try:
            exc = task.exception()
            if exc:
                self._handle_task_exception(task, exc)
        except asyncio.InvalidStateError:
            pass  # Task not done yet

    def _handle_task_exception(self, task: asyncio.Task, exc: Exception) -> None:
        """Handle exception from a background task.

        Args:
            task: The task that raised the exception
            exc: The exception that was raised
        """
        task_name = task.get_name() if hasattr(task, 'get_name') else 'unknown'
        print(f"Background task '{task_name}' error: {exc}")
        traceback.print_exception(type(exc), exc, exc.__traceback__)

        # Show error to user
        error_msg = str(exc)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."

        self.status_bar.showMessage(f"Background error: {error_msg}", 5000)

    async def _cancel_all_tasks(self, timeout: float = None) -> None:
        """Cancel all active tasks and wait for them to finish.

        Args:
            timeout: Maximum time to wait for cancellation (uses settings default)
        """
        if timeout is None:
            timeout = settings.task_cancellation_timeout
        if not self._active_tasks:
            return

        # Cancel all tasks
        for task in self._active_tasks:
            task.cancel()

        # Wait for cancellation with timeout
        if self._active_tasks:
            try:
                await asyncio.wait(
                    self._active_tasks,
                    timeout=timeout,
                    return_when=asyncio.ALL_COMPLETED
                )
            except Exception:
                pass  # Ignore errors during cleanup

        self._active_tasks.clear()

    # ==================== Model Management ====================

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
            if self._switch_model(model_id):
                # Persist the model selection
                persistence.update_last_model(model_id)

                # Show notification toast
                model_config = get_model(model_id)
                if model_config:
                    self._show_model_notification(model_config.display_name)

    def _show_model_notification(self, model_name: str) -> None:
        """Show a notification toast for model switch.

        Args:
            model_name: Display name of the new model
        """
        toast = NotificationToast(
            f"Switched to {model_name}",
            self,
            duration_ms=2000,
        )
        # Position at top center of the window
        x = (self.width() - toast.width()) // 2
        y = 50
        toast.show_at(x, y)

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

        # Check for YouTube URLs - fetch async if found
        self._prompt_builder.clear_youtube_context()
        if contains_youtube_url(message):
            video_id = extract_video_id(message)
            if video_id:
                # Fetch transcript asynchronously to avoid blocking UI
                self.status_bar.showMessage("Fetching YouTube transcript...", 0)
                self.input_panel.set_enabled(False)
                self._create_task(
                    self._fetch_youtube_and_send(video_id, message),
                    name="youtube_fetch"
                )
                return

        # No YouTube URL - proceed normally
        self._continue_message_submission(message)

    async def _fetch_youtube_and_send(self, video_id: str, message: str) -> None:
        """Fetch YouTube transcript asynchronously and then send message.

        Args:
            video_id: YouTube video ID
            message: The user's message
        """
        try:
            # Run fetch in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            transcript, error = await loop.run_in_executor(
                None,
                fetch_transcript,
                video_id
            )

            if transcript:
                # Add transcript to context
                context_block = transcript.to_context_block()
                self._prompt_builder.set_youtube_context(context_block)
                token_estimate = estimate_transcript_tokens(transcript)
                self.status_bar.showMessage(
                    f"YouTube transcript loaded ({transcript.duration_formatted}, ~{token_estimate} tokens)",
                    3000
                )
            elif error:
                self.status_bar.showMessage(f"YouTube: {error}", 5000)

        except Exception as e:
            self.status_bar.showMessage(f"YouTube fetch error: {str(e)}", 5000)

        # Check if message is just the URL - if so, add default instruction
        import re
        url_patterns = [
            r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&\S*)?',
            r'https?://youtu\.be/[\w-]+(?:\?\S*)?',
            r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+',
        ]
        text_without_urls = message
        for pattern in url_patterns:
            text_without_urls = re.sub(pattern, '', text_without_urls)
        text_without_urls = text_without_urls.strip()

        if not text_without_urls:
            # User only pasted the link - add default instruction
            user_message = "Please provide a comprehensive summary of this YouTube video transcript."
        else:
            # User included instructions with the link
            user_message = message

        # Continue with message submission
        await self._continue_message_submission_async(user_message)

    def _continue_message_submission(self, message: str) -> None:
        """Continue message submission (sync entry point).

        Args:
            message: The user's message
        """
        # Schedule the async continuation
        self._create_task(
            self._continue_message_submission_async(message),
            name="message_submission"
        )

    async def _continue_message_submission_async(self, message: str) -> None:
        """Continue message submission after optional YouTube fetch (async).

        Args:
            message: The user's message
        """
        # Add user message to UI and history
        user_msg_index = self.chat_panel.add_user_message(message)
        self._prompt_builder.add_user_message(message)

        # Analyze message for TOC entry
        toc_entry = self._toc_generator.analyze_message(message, "user", user_msg_index)
        if toc_entry:
            self.sidebar.add_toc_entry(toc_entry)
        self.sidebar.set_toc_current_index(user_msg_index)

        # Update memory context (filter by current message for relevance)
        self._update_memory_context(message)

        # Update scratchpad context
        self._update_scratchpad_context()

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
        assistant_msg_index = self.chat_panel.start_assistant_message()

        # Route through Crucible or standard LLM
        if self._crucible_enabled and self._crucible_adapter:
            await self._stream_crucible_response(message, assistant_msg_index)
        else:
            # Await the streaming response with RAG
            await self._stream_response_with_rag(message, assistant_msg_index)

    async def _stream_response_with_rag(
        self,
        user_message: str,
        assistant_msg_index: int = -1
    ) -> None:
        """Stream a response with RAG retrieval.

        Args:
            user_message: The user's message for RAG query
            assistant_msg_index: Index of the assistant message for TOC
        """
        # Acquire streaming lock to prevent concurrent operations
        async with self._streaming_lock:
            # Check if summarization is in progress
            if self._summarization_lock.locked():
                self.status_bar.showMessage(
                    "Waiting for summarization to complete...", 2000
                )
                # Wait for summarization to finish
                async with self._summarization_lock:
                    pass

            await self._stream_response_with_rag_impl(user_message, assistant_msg_index)

    async def _stream_response_with_rag_impl(
        self,
        user_message: str,
        assistant_msg_index: int = -1
    ) -> None:
        """Implementation of RAG streaming (called with lock held).

        Args:
            user_message: The user's message for RAG query
            assistant_msg_index: Index of the assistant message for TOC
        """
        # Perform RAG retrieval if documents are indexed
        if self._rag_initialized and self._vector_store:
            doc_count = len(self._vector_store.get_all_doc_ids())
            if doc_count > 0:
                chunks = await self._perform_rag_retrieval(user_message)
                self._prompt_builder.set_rag_context(chunks, user_message)
            else:
                self._prompt_builder.clear_rag_context()
        else:
            self._prompt_builder.clear_rag_context()

        # Update inspector
        self._update_inspector()

        # Stream the response
        await self._stream_response(assistant_msg_index)

    async def _stream_response(self, assistant_msg_index: int = -1) -> None:
        """Stream a response from the LLM.

        Args:
            assistant_msg_index: Index of the assistant message for TOC
        """
        if not self._adapter:
            return

        full_response = ""

        try:
            messages = self._prompt_builder.build_messages()
            system = self._prompt_builder.get_system_prompt()

            async for chunk in self._adapter.stream(messages, system):
                # Check for interrupt request
                if self._interrupt_requested:
                    break

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

            # Check if we were interrupted
            if self._interrupt_requested:
                self._interrupt_requested = False
                # Handle partial response
                if full_response.strip():
                    # Keep partial response
                    self._prompt_builder.add_assistant_message(full_response)
                    self.chat_panel.finish_assistant_message()
                    self.status_bar.showMessage("Generation interrupted - partial response kept", 3000)
                else:
                    # Discard empty response
                    self.chat_panel.remove_last_assistant_message()
                    # Also remove the user message we just added
                    self._prompt_builder.history.remove_last_exchange()
                    self.chat_panel.remove_last_exchange()
                    self.status_bar.showMessage("Generation interrupted - no content", 3000)
            else:
                # Add complete response to history
                self._prompt_builder.add_assistant_message(full_response)
                self.chat_panel.finish_assistant_message()

                # Analyze completed response for TOC entry
                if assistant_msg_index >= 0:
                    toc_entry = self._toc_generator.analyze_message(
                        full_response, "assistant", assistant_msg_index
                    )
                    if toc_entry:
                        self.sidebar.add_toc_entry(toc_entry)
                    self.sidebar.set_toc_current_index(assistant_msg_index)

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
        # Allow regenerate if we have an adapter OR Crucible is enabled
        if self._is_streaming:
            return
        if not self._adapter and not (self._crucible_enabled and self._crucible_adapter):
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
        assistant_msg_index = self.chat_panel.start_assistant_message()

        self.status_bar.showMessage("Regenerating response...", 2000)

        # Route through Crucible or standard LLM
        if self._crucible_enabled and self._crucible_adapter:
            self._create_task(
                self._stream_crucible_response(last_user, assistant_msg_index),
                name="regenerate_crucible"
            )
        else:
            self._create_task(self._stream_response(), name="regenerate_stream")

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

        self._create_task(self._perform_summarization(), name="summarization")

    async def _perform_summarization(self) -> None:
        """Perform context summarization in the background."""
        if self._summarization_in_progress:
            return

        # Don't start if streaming is in progress
        if self._streaming_lock.locked():
            return

        async with self._summarization_lock:
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
        # Check that UI is initialized (showEvent can fire before _setup_ui completes)
        if hasattr(self, 'input_panel'):
            QTimer.singleShot(0, self.input_panel.focus_input)

    def _init_rag(self) -> bool:
        """Initialize RAG components lazily.

        Returns:
            True if initialization successful
        """
        if self._rag_initialized:
            return True

        try:
            # Initialize vector store WITHOUT persistence path
            # Each session starts fresh to prevent context contamination
            self._vector_store = FAISSVectorStore(
                dimension=settings.embedding_dimension,
                index_path=None,  # No persistence - fresh each session
            )

            # Initialize BM25 client
            self._bm25_client = BM25Client()

            # Initialize document indexer
            self._document_indexer = DocumentIndexer(
                vector_store=self._vector_store,
                bm25_client=self._bm25_client,
            )

            # Initialize retrieval blacklist
            blacklist_path = settings.app_data_dir / "blacklist.json"
            self._retrieval_blacklist = RetrievalBlacklist(blacklist_path)

            self._rag_initialized = True
            return True

        except Exception as e:
            self.status_bar.showMessage(f"RAG init failed: {e}", 5000)
            return False

    def _on_document_added(self, file_path: str) -> None:
        """Handle document added signal.

        Args:
            file_path: Path to the document file
        """
        if not self._init_rag():
            return

        # Index document asynchronously
        self._create_task(self._index_document(file_path), name="document_indexing")

    async def _index_document(self, file_path: str) -> None:
        """Index a document for RAG.

        Uses indexing lock to prevent concurrent FAISS operations.

        Args:
            file_path: Path to the document file
        """
        if not self._document_indexer:
            return

        async with self._indexing_lock:
            try:
                self.status_bar.showMessage(f"Indexing {Path(file_path).name}...")

                parent = await self._document_indexer.index_document(Path(file_path))

                # Add to sidebar
                self.sidebar.add_document(
                    doc_id=parent.doc_id,
                    name=parent.title,
                    path=file_path
                )

                self.status_bar.showMessage(
                    f"Indexed {parent.title} ({len(parent.chunk_ids)} chunks)", 3000
                )

            except Exception as e:
                self.chat_panel.add_error_message(f"Failed to index document: {e}")
                self.status_bar.showMessage(f"Index failed: {e}", 5000)

    def _on_document_removed(self, doc_id: str) -> None:
        """Handle document removed signal.

        Args:
            doc_id: Document ID to remove
        """
        if self._document_indexer:
            self._document_indexer.delete_document(doc_id)
            self.status_bar.showMessage("Document removed", 2000)

    def _on_documents_cleared(self) -> None:
        """Handle clear all documents signal."""
        if self._vector_store:
            self._vector_store.clear()
        if self._bm25_client:
            self._bm25_client.clear()
        self.status_bar.showMessage("All documents cleared", 2000)

    def _on_inspector_toggled(self, visible: bool) -> None:
        """Handle inspector toggle.

        Args:
            visible: Whether inspector should be visible
        """
        if self._inspector_panel:
            if visible:
                self._inspector_panel.show()
                self._update_inspector()
            else:
                self._inspector_panel.hide()

    def _on_inspector_closed(self) -> None:
        """Handle inspector close button."""
        if self._inspector_panel:
            self._inspector_panel.hide()
            self.sidebar.set_inspector_active(False)

    def _on_jump_to_message(self, message_index: int) -> None:
        """Handle TOC jump to message request.

        Args:
            message_index: Index of the message to scroll to
        """
        self.chat_panel.scroll_to_message(message_index)
        self.sidebar.set_toc_current_index(message_index)

    def _on_fork_requested(self, message_index: int) -> None:
        """Handle fork request from a message.

        Creates a new session with messages up to the fork point.

        Args:
            message_index: Index of the message to fork from
        """
        if self._is_streaming:
            return

        # Get messages up to and including the fork point
        all_messages = self._prompt_builder.history.messages
        if message_index >= len(all_messages):
            self.status_bar.showMessage("Cannot fork from this message", 3000)
            return

        # Messages to include in fork (up to and including fork point)
        fork_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in all_messages[: message_index + 1]
        ]

        if not fork_messages:
            self.status_bar.showMessage("No messages to fork", 3000)
            return

        # Save current session first
        current_session_id = self._session_record.session_id
        self._save_session_data()

        # Create forked session
        forked_session = SessionRecord.create_fork(
            source_session_id=current_session_id,
            fork_point_index=message_index,
            messages=fork_messages,
            models_used=[self._current_model_id] if self._current_model_id else [],
        )

        # Load the forked session
        self._load_forked_session(forked_session)

        self.status_bar.showMessage(
            f"Forked conversation at message {message_index + 1}", 3000
        )

    def _load_forked_session(self, session: SessionRecord) -> None:
        """Load a forked session as the active conversation.

        Args:
            session: The forked SessionRecord to load
        """
        # Clear current state
        self.chat_panel.clear()
        self.sidebar.clear_toc()
        self._scratchpad_panel.clear()
        self._prompt_builder = PromptBuilder()
        self._intent_tracker = IntentTracker()
        self._waypoint_manager = WaypointManager()
        self._toc_generator = TOCGenerator()
        self._drift_detector = DriftDetector()

        # Set the forked session as current
        self._session_record = session

        # Show fork header
        fork_msg = f"Forked from message {session.fork_point_index + 1}"
        self.chat_panel.add_system_message(f"🔀 {fork_msg}")

        # Load messages
        for msg in session.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                msg_index = self.chat_panel.add_user_message(content)
                self._prompt_builder.add_user_message(content)
                # Analyze for TOC entry
                toc_entry = self._toc_generator.analyze_message(content, "user", msg_index)
                if toc_entry:
                    self.sidebar.add_toc_entry(toc_entry)
            elif role == "assistant":
                msg_index = self.chat_panel.start_assistant_message()
                self.chat_panel.append_to_assistant_message(content)
                self.chat_panel.finish_assistant_message()
                self._prompt_builder.add_assistant_message(content)
                # Analyze for TOC entry
                toc_entry = self._toc_generator.analyze_message(content, "assistant", msg_index)
                if toc_entry:
                    self.sidebar.add_toc_entry(toc_entry)

        # Update context display
        self._update_token_count()

        # Enable regenerate if we have messages
        self.sidebar.set_regenerate_enabled(
            self._prompt_builder.get_message_count() > 0
        )

        # Focus input for continuation
        self.input_panel.focus_input()

    async def _perform_rag_retrieval(self, query: str) -> List[Dict[str, Any]]:
        """Perform hybrid RAG retrieval for a query.

        Uses indexing lock to prevent conflicts with document indexing.

        Args:
            query: The user's query

        Returns:
            List of retrieved chunks with metadata
        """
        if not self._rag_initialized or not self._document_indexer:
            return []

        if not self._vector_store or not self._bm25_client:
            return []

        async with self._indexing_lock:
            try:
                # Get query embedding
                query_embedding = await self._document_indexer.get_query_embedding(query)

                # Vector search
                vector_results = self._vector_store.query(
                    query_embedding, k=settings.rag_search_k
                )

                # BM25 search
                bm25_results = self._bm25_client.query(
                    query, k=settings.rag_search_k
                )

                # Reciprocal rank fusion
                chunks_dict = {c.chunk.chunk_id: c.chunk for c in vector_results}
                for r in bm25_results:
                    chunk = self._bm25_client.get_chunk(r.chunk_id)
                    if chunk:
                        chunks_dict[r.chunk_id] = chunk

                fused = reciprocal_rank_fusion(
                    vector_results, bm25_results, chunks_dict, k=60
                )

                # Apply blacklist filter
                results = []
                for chunk_id, score in fused[:settings.rag_retrieval_k]:
                    # Find the vector result for this chunk
                    vector_result = next(
                        (r for r in vector_results if r.chunk.chunk_id == chunk_id),
                        None
                    )

                    if vector_result:
                        # Check blacklist
                        filtered = self._retrieval_blacklist.filter_results([vector_result])
                        if filtered:
                            result = filtered[0]
                            results.append({
                                "chunk_id": result.chunk.chunk_id,
                                "content": result.chunk.content,
                                "source_file": result.chunk.source_file,
                                "page_or_section": result.chunk.page_or_section,
                                "similarity_score": result.similarity_score,
                                "combined_score": score,
                            })
                    else:
                        # Chunk only from BM25, get it directly
                        chunk = self._bm25_client.get_chunk(chunk_id)
                        if chunk:
                            results.append({
                                "chunk_id": chunk.chunk_id,
                                "content": chunk.content,
                                "source_file": chunk.source_file,
                                "page_or_section": chunk.page_or_section,
                                "similarity_score": 0.0,
                                "combined_score": score,
                            })

                return results

            except Exception as e:
                self.status_bar.showMessage(f"Retrieval error: {e}", 3000)
                return []

    def _update_inspector(self) -> None:
        """Update the inspector panel with current state."""
        if not self._inspector_panel or not self._inspector_panel.isVisible():
            return

        # Update prompt view
        system = self._prompt_builder.get_system_prompt()
        messages = self._prompt_builder.build_messages()
        prompt_text = f"=== SYSTEM PROMPT ===\n{system}\n\n"
        prompt_text += "=== MESSAGES ===\n"
        for msg in messages:
            prompt_text += f"[{msg['role'].upper()}]\n{msg['content']}\n\n"
        self._inspector_panel.update_prompt(prompt_text)

        # Update RAG context
        rag_chunks = self._prompt_builder.get_rag_chunks()
        self._inspector_panel.update_rag_context(rag_chunks)

        # Update metadata
        model_config = get_model(self._current_model_id)
        metadata = {
            "model": {
                "id": self._current_model_id,
                "provider": model_config.provider if model_config else "unknown",
                "context_window": model_config.context_window if model_config else 0,
            },
            "intent": {
                "mode": self._intent_tracker.current_mode.value,
            },
            "context": {
                "message_count": self._prompt_builder.get_message_count(),
                "active_messages": self._prompt_builder.get_active_message_count(),
                "rag_chunks": len(rag_chunks),
            },
        }
        self._inspector_panel.update_metadata(metadata)

        # Update token summary
        if self._token_counter and self._context_manager:
            total = self._token_counter.count_prompt(system, messages)
            self._inspector_panel.update_token_summary(
                total=total,
                context_window=self._context_manager.context_window,
            )

    def closeEvent(self, event) -> None:
        """Handle window close event - save session and window state."""
        # Cancel all active async tasks
        if self._active_tasks:
            # Cancel tasks synchronously
            for task in list(self._active_tasks):
                task.cancel()
            # Brief pause to let cancellations process
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()

        # Stop any streaming timers
        if hasattr(self, 'chat_panel') and hasattr(self.chat_panel, '_update_timer'):
            self.chat_panel._update_timer.stop()

        # Save window state
        self._save_window_state()

        # Only show exit dialog if there was actual conversation
        if self._prompt_builder.get_message_count() > 0:
            # Get default artifact options from preferences
            prefs = persistence.preferences

            dialog = ExitDialog(
                self,
                default_outline=prefs.generate_outline,
                default_decisions=prefs.generate_decisions,
                default_research=prefs.generate_research,
            )

            if dialog.exec() == 0:  # Dialog rejected (Cancel)
                event.ignore()
                return

            action, outline, decisions, research = dialog.get_result()

            if action == ExitAction.CANCEL:
                event.ignore()
                return

            # Save artifact preferences
            persistence.update_artifact_options(outline, decisions, research)

            if action == ExitAction.SUMMARIZE_EXIT:
                # Generate artifacts before exiting
                self._generate_exit_artifacts(outline, decisions, research)

            # Save session data
            self._save_session_data()

        super().closeEvent(event)

    def _save_window_state(self) -> None:
        """Save window position and size."""
        is_maximized = self.isMaximized()

        # Get geometry only if not maximized
        if not is_maximized:
            geometry = self.geometry()
            persistence.update_window_state(
                x=geometry.x(),
                y=geometry.y(),
                width=geometry.width(),
                height=geometry.height(),
                maximized=False,
            )
        else:
            # Just update maximized state, keep previous size
            prefs = persistence.preferences
            persistence.update_window_state(
                x=prefs.window.x,
                y=prefs.window.y,
                width=prefs.window.width,
                height=prefs.window.height,
                maximized=True,
            )

    def _save_session_data(self) -> None:
        """Save session data to conversation store."""
        if self._prompt_builder.get_message_count() == 0:
            return

        # Update session record with final data
        if self._current_model_id:
            if self._current_model_id not in self._session_record.models_used:
                self._session_record.models_used.append(self._current_model_id)

        # Get token count
        if self._token_counter:
            messages = self._prompt_builder.build_messages()
            system = self._prompt_builder.get_system_prompt()
            self._session_record.token_count = self._token_counter.count_prompt(
                system, messages
            )

        # Get summary if present
        if self._prompt_builder._summary_block:
            self._session_record.summary_xml = self._prompt_builder._summary_block

        # Get waypoints
        self._session_record.waypoints = self._waypoint_manager.get_waypoints_for_archive()

        # Save all conversation messages
        self._session_record.messages = [
            {"role": msg.role, "content": msg.content}
            for msg in self._prompt_builder.history.messages
        ]

        # Save to conversation store
        self._conversation_store.save_session(self._session_record)

    def _generate_exit_artifacts(
        self,
        outline: bool,
        decisions: bool,
        research: bool,
    ) -> None:
        """Generate artifacts before exiting.

        Uses QEventLoop for safe blocking in Qt context.

        Args:
            outline: Whether to generate conversation outline
            decisions: Whether to generate decision log
            research: Whether to generate research index
        """
        if not self._adapter:
            return

        if not any([outline, decisions, research]):
            return

        self.status_bar.showMessage("Generating artifacts...")

        # Get messages for artifact generation
        messages = []
        for msg in self._prompt_builder.history.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        # Use QEventLoop for Qt-safe blocking
        from PySide6.QtCore import QEventLoop

        loop = QEventLoop()
        result_holder = {"result": None, "error": None}

        async def generate():
            try:
                result_holder["result"] = await self._artifact_generator.generate_artifacts(
                    messages=messages,
                    adapter=self._adapter,
                    generate_outline=outline,
                    generate_decisions=decisions,
                    generate_research=research,
                )
            except Exception as e:
                result_holder["error"] = str(e)
            finally:
                loop.quit()

        # Schedule the async task
        task = asyncio.create_task(generate())

        # Run Qt event loop until task completes (with timeout)
        timeout_ms = settings.artifact_generation_timeout * 1000
        QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()

        # Cancel task if still running (timeout)
        if not task.done():
            task.cancel()
            self.status_bar.showMessage("Artifact generation timed out", 3000)
            return

        if result_holder["error"]:
            self.status_bar.showMessage(
                f"Artifact generation error: {result_holder['error']}", 3000
            )
            return

        result = result_holder["result"]
        if result and result.success:
            # Save artifacts
            saved = self._artifact_generator.save_artifacts(
                result,
                self._session_record.session_id,
                settings.artifacts_dir,
            )

            # Update session record
            for path in saved:
                artifact_type = path.stem.split("_")[-1]
                if artifact_type not in self._session_record.artifacts_generated:
                    self._session_record.artifacts_generated.append(artifact_type)

            self.status_bar.showMessage(
                f"Saved {len(saved)} artifact(s)", 2000
            )
        elif result:
            self.status_bar.showMessage(
                f"Artifact generation failed: {result.error}", 3000
            )

    def _on_toggle_inspector(self) -> None:
        """Toggle inspector panel visibility."""
        if self._inspector_panel:
            is_visible = self._inspector_panel.isVisible()
            if is_visible:
                self._inspector_panel.hide()
                self.sidebar.set_inspector_active(False)
            else:
                self._inspector_panel.show()
                self._update_inspector()
                self.sidebar.set_inspector_active(True)

            # Persist inspector state
            persistence.update_inspector_visible(not is_visible)

    def _on_new_conversation(self) -> None:
        """Start a new conversation, clearing the current one."""
        if self._is_streaming:
            return

        # Save current session if there's content
        if self._prompt_builder.get_message_count() > 0:
            self._save_session_data()

        # Clear UI
        self.chat_panel.clear()
        self.sidebar.clear_toc()
        self._scratchpad_panel.clear()

        # Reset conversation state
        self._prompt_builder = PromptBuilder()
        self._intent_tracker = IntentTracker()
        self._waypoint_manager = WaypointManager()
        self._toc_generator = TOCGenerator()
        self._drift_detector = DriftDetector()

        # Create new session record
        self._session_record = SessionRecord.create()

        # Update context display
        self._update_token_count()

        # Reset intent display
        self.intent_label.setText("Mode: exploration")

        # Disable regenerate button
        self.sidebar.set_regenerate_enabled(False)

        # Focus input
        self.input_panel.focus_input()

        self.status_bar.showMessage("New conversation started", 2000)

    def _on_toggle_focus_mode(self) -> None:
        """Toggle focus mode (hide/show sidebar)."""
        self._focus_mode = not self._focus_mode

        if self._focus_mode:
            self.sidebar.hide()
        else:
            self.sidebar.show()

        # Persist focus mode state
        persistence.update_focus_mode(self._focus_mode)

        # Focus input after toggle
        self.input_panel.focus_input()

    def _on_escape_pressed(self) -> None:
        """Handle Escape key - close inspector or exit focus mode."""
        # First, close inspector if visible
        if self._inspector_panel and self._inspector_panel.isVisible():
            self._inspector_panel.hide()
            self.sidebar.set_inspector_active(False)
            persistence.update_inspector_visible(False)
            return

        # Then, exit focus mode if active
        if self._focus_mode:
            self._focus_mode = False
            self.sidebar.show()
            persistence.update_focus_mode(False)
            self.input_panel.focus_input()

    def _on_show_help(self) -> None:
        """Show the help dialog with keyboard shortcuts."""
        dialog = HelpDialog(self)
        dialog.exec()

    def _on_show_about(self) -> None:
        """Show the about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def _on_save_session(self) -> None:
        """Save the current session immediately."""
        if self._prompt_builder.get_message_count() == 0:
            self.status_bar.showMessage("No conversation to save", 2000)
            return

        self._save_session_data()
        self.status_bar.showMessage("Session saved", 2000)

    def _on_export_chat(self) -> None:
        """Export the current conversation to a markdown file."""
        if self._prompt_builder.get_message_count() == 0:
            self.status_bar.showMessage("No conversation to export", 2000)
            return

        # Get all messages
        messages = self._prompt_builder.build_all_messages()

        # Estimate token count
        token_count = 0
        if self._token_counter:
            for msg in messages:
                token_count += self._token_counter.count(msg.get("content", ""))

        # Get models used
        models_used = [self._current_model_id] if self._current_model_id else []

        # Generate default filename
        default_filename = generate_export_filename()

        # Open save dialog
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Chat",
            default_filename,
            "Markdown Files (*.md);;All Files (*.*)"
        )

        if not filepath:
            return  # User cancelled

        # Ensure .md extension
        if not filepath.endswith(".md"):
            filepath += ".md"

        # Export
        try:
            markdown_content = export_to_markdown(
                messages=messages,
                models_used=models_used,
                token_count=token_count,
                session_id=self._session_record.session_id,
            )
            Path(filepath).write_text(markdown_content, encoding="utf-8")

            # Show confirmation
            filename = Path(filepath).name
            self.status_bar.showMessage(f"Chat exported to {filename}", 3000)
        except Exception as e:
            self.status_bar.showMessage(f"Export failed: {str(e)}", 5000)

    def _on_open_session(self) -> None:
        """Open the session browser dialog."""
        dialog = SessionBrowserDialog(self._conversation_store, self)
        if dialog.exec():
            session = dialog.get_selected_session()
            if session:
                self._load_session_replay(session)

    def _load_session_replay(self, session) -> None:
        """Load a session and restore conversation for continuation.

        Args:
            session: SessionRecord to load
        """
        # Save current session if there's content
        if self._prompt_builder.get_message_count() > 0:
            self._save_session_data()

        # Clear current state
        self.chat_panel.clear()
        self.sidebar.clear_toc()
        self._scratchpad_panel.clear()
        self._prompt_builder = PromptBuilder()
        self._intent_tracker = IntentTracker()
        self._waypoint_manager = WaypointManager()
        self._toc_generator = TOCGenerator()
        self._drift_detector = DriftDetector()

        # Create new session record (this is a continuation, new session ID)
        self._session_record = SessionRecord.create()

        # Show session header
        started = session.started_at.strftime("%Y-%m-%d %H:%M")
        models = ", ".join(session.models_used) if session.models_used else "unknown"
        msg_count = len(session.messages) if session.messages else 0

        # Check if this is an old session with summary but no messages
        has_messages = bool(session.messages)
        has_summary = bool(session.summary_xml)

        if has_messages:
            # Normal case: load full message history
            header = f"Loaded session from {started} | {msg_count} messages | Models: {models}"
            self.chat_panel.add_system_message(header)

            for msg in session.messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "user":
                    msg_index = self.chat_panel.add_user_message(content)
                    self._prompt_builder.add_user_message(content)
                    # Analyze for TOC entry
                    toc_entry = self._toc_generator.analyze_message(content, "user", msg_index)
                    if toc_entry:
                        self.sidebar.add_toc_entry(toc_entry)
                elif role == "assistant":
                    # Add assistant message directly (not through streaming)
                    msg_index = self.chat_panel.start_assistant_message()
                    self.chat_panel.append_to_assistant_message(content)
                    self.chat_panel.finish_assistant_message()
                    self._prompt_builder.add_assistant_message(content)
                    # Analyze for TOC entry
                    toc_entry = self._toc_generator.analyze_message(content, "assistant", msg_index)
                    if toc_entry:
                        self.sidebar.add_toc_entry(toc_entry)

            # Also restore summary if present (for summarized older messages)
            if has_summary:
                self._prompt_builder.set_summary(session.summary_xml)

            status_msg = f"Loaded session with {msg_count} messages - ready to continue"

        elif has_summary:
            # Old session with summary but no messages - inject summary as context
            header = f"Loaded session from {started} | Models: {models}"
            self.chat_panel.add_system_message(header)
            self.chat_panel.add_system_message(
                "[Session loaded from summary - original messages not available]"
            )

            # Inject summary into prompt builder as prior context
            self._prompt_builder.set_summary(session.summary_xml)

            status_msg = "Loaded session from summary - ready to continue"

        else:
            # Empty session - nothing to load
            header = f"Loaded empty session from {started} | Models: {models}"
            self.chat_panel.add_system_message(header)
            status_msg = "Loaded empty session"

        # Update context display
        self._update_token_count()

        # Enable regenerate if we have messages
        self.sidebar.set_regenerate_enabled(
            self._prompt_builder.get_message_count() > 0
        )

        # Focus input for continuation
        self.input_panel.focus_input()

        self.status_bar.showMessage(status_msg, 3000)

    def _on_menu_clear_documents(self) -> None:
        """Clear all indexed documents via menu."""
        # Trigger same action as sidebar "Clear All" button
        self._on_documents_cleared()
        self.sidebar.clear_documents()

    def _on_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility (same as focus mode)."""
        self._on_toggle_focus_mode()

    def _on_view_summary(self) -> None:
        """View the current session's XML summary."""
        # Check if we have a summary from prompt builder
        summary_xml = None

        # Check if current session has been summarized
        if hasattr(self._prompt_builder, '_summary_block') and self._prompt_builder._summary_block:
            # Extract just the XML part from the summary block
            summary_xml = self._prompt_builder._summary_block
        elif self._loaded_session_summary:
            # Use loaded session's summary
            summary_xml = self._loaded_session_summary

        if not summary_xml:
            self.status_bar.showMessage(
                "No summary available (context not yet compressed)",
                3000
            )
            return

        dialog = SummaryViewerDialog(
            summary_xml=summary_xml,
            session_id=self._session_record.session_id if self._session_record else "",
            parent=self
        )
        dialog.exec()

    def _on_search_conversations(self) -> None:
        """Open the conversation search dialog."""
        # Initialize conversation indexer if not already done
        if not self._conversation_indexer:
            try:
                self._conversation_indexer = ConversationIndexer(
                    index_path=settings.app_data_dir / "conversation_index",
                )
            except Exception as e:
                self.status_bar.showMessage(f"Search init failed: {e}", 5000)
                return

        # Create and show search dialog
        self._search_dialog = ConversationSearchDialog(self)
        self._search_dialog.search_requested.connect(self._on_search_requested)
        self._search_dialog.index_requested.connect(self._on_index_requested)
        self._search_dialog.session_selected.connect(self._on_search_session_selected)

        # Show index status
        msg_count = self._conversation_indexer.get_indexed_message_count()
        session_count = self._conversation_indexer.get_indexed_session_count()
        if msg_count > 0:
            self._search_dialog.status_label.setText(
                f"Index contains {session_count} session(s), {msg_count} message(s)"
            )

        self._search_dialog.exec()

    def _on_search_requested(self, query: str) -> None:
        """Handle search request from dialog.

        Args:
            query: The search query
        """
        if not self._conversation_indexer or not self._search_dialog:
            return

        self._create_task(
            self._perform_conversation_search(query),
            name="conversation_search"
        )

    async def _perform_conversation_search(self, query: str) -> None:
        """Perform semantic search across conversations.

        Args:
            query: The search query
        """
        if not self._conversation_indexer or not self._search_dialog:
            return

        try:
            results = await self._conversation_indexer.search(query, k=20)
            self._search_dialog.set_results(results, query)
        except Exception as e:
            self._search_dialog.status_label.setText(f"Search error: {str(e)}")

    def _on_index_requested(self) -> None:
        """Handle index all sessions request from dialog."""
        if not self._conversation_indexer or not self._search_dialog:
            return

        self._create_task(self._index_all_sessions(), name="index_sessions")

    async def _index_all_sessions(self) -> None:
        """Index all sessions for semantic search."""
        if not self._conversation_indexer or not self._search_dialog:
            return

        try:
            sessions = self._conversation_store.get_recent_sessions(limit=100)
            indexed_count = 0

            for session in sessions:
                # Skip if already indexed
                if self._conversation_indexer.is_session_indexed(session.session_id):
                    continue

                # Index session
                count = await self._conversation_indexer.index_session(session)
                if count > 0:
                    indexed_count += 1

            self._search_dialog.set_index_complete(indexed_count)

        except Exception as e:
            self._search_dialog.status_label.setText(f"Index error: {str(e)}")
            self._search_dialog.index_btn.setText("Index All Sessions")
            self._search_dialog.index_btn.setEnabled(True)

    def _on_search_session_selected(self, session_id: str) -> None:
        """Handle session selection from search results.

        Args:
            session_id: The selected session ID
        """
        # Find the session
        session = self._conversation_store.get_session(session_id)
        if session:
            self._load_session_replay(session)

    def _on_toggle_side_panel(self) -> None:
        """Toggle the side question panel."""
        if self._side_panel:
            if self._side_panel.isVisible():
                # Close and discard
                self._on_side_panel_closed()
            else:
                # Open side panel
                self._parallel_context.start_side_conversation()
                self._side_panel.clear()
                self._side_panel.show()
                self._side_panel.focus_input()
                self.status_bar.showMessage("Side panel opened - ask quick questions", 2000)

    def _on_side_panel_closed(self) -> None:
        """Handle side panel close."""
        if self._side_panel:
            self._side_panel.hide()
            self._parallel_context.end_side_conversation(merge=False)
            self.input_panel.focus_input()

    def _on_side_panel_merge(self) -> None:
        """Handle side panel merge request."""
        if not self._side_panel or not self._parallel_context.get_active_side():
            return

        # Get merge summary
        summary = self._parallel_context.end_side_conversation(merge=True)

        if summary:
            # Add as a system message in main conversation
            self.chat_panel.add_system_message(summary)
            self.status_bar.showMessage("Side discussion merged into conversation", 3000)

        # Close side panel
        self._side_panel.hide()
        self.input_panel.focus_input()

    def _on_side_message_submitted(self, message: str) -> None:
        """Handle message submitted in side panel.

        Args:
            message: The user's message
        """
        if not self._adapter or not self._side_panel or self._side_streaming:
            return

        # Add message to side panel and context
        self._side_panel.add_user_message(message)
        self._parallel_context.add_user_message(message)

        # Stream response
        self._side_streaming = True
        self._side_panel.set_input_enabled(False)
        self._create_task(self._stream_side_response(), name="side_response")

    async def _stream_side_response(self) -> None:
        """Stream a response for the side panel."""
        if not self._adapter or not self._side_panel:
            return

        active_side = self._parallel_context.get_active_side()
        if not active_side:
            return

        full_response = ""

        try:
            # Build messages for side conversation
            messages = active_side.build_messages()

            # Get summary of main conversation for context
            main_summary = None
            if self._prompt_builder.get_message_count() > 0:
                main_summary = f"Main conversation has {self._prompt_builder.get_message_count()} messages about: {self._intent_tracker.current_mode.value}"

            system = self._parallel_context.get_side_system_prompt(main_summary)

            async for chunk in self._adapter.stream(messages, system):
                if chunk.text:
                    full_response += chunk.text

            # Add complete response
            self._parallel_context.add_assistant_message(full_response)
            self._side_panel.finish_assistant_message(full_response)

        except Exception as e:
            error_msg = str(e)
            self._side_panel.add_assistant_message(f"Error: {error_msg}")
            self.status_bar.showMessage(f"Side panel error: {error_msg}", 5000)

        finally:
            self._side_streaming = False
            self._side_panel.set_input_enabled(True)
            self._side_panel.focus_input()

    def _on_view_memory(self) -> None:
        """Open the unified memory panel."""
        dialog = MemoryPanel(self._unified_memory, self)
        dialog.exec()

    def _update_memory_context(self, context: Optional[str] = None) -> None:
        """Update the memory context in the prompt builder.

        Args:
            context: Optional context for relevance filtering
        """
        memory_block = self._unified_memory.build_memory_prompt(context)
        self._prompt_builder.set_memory_context(memory_block)

    def _on_scratchpad_changed(self, content: str) -> None:
        """Handle scratchpad content changes.

        Args:
            content: New scratchpad content
        """
        self._prompt_builder.set_scratchpad(content)

    def _update_scratchpad_context(self) -> None:
        """Update the scratchpad context in the prompt builder."""
        content = self._scratchpad_panel.get_content()
        self._prompt_builder.set_scratchpad(content)

    def _on_interrupt_generation(self) -> None:
        """Handle interrupt request (ESC key)."""
        if self._is_streaming:
            self._interrupt_requested = True
            self.status_bar.showMessage("Interrupting generation...", 1000)
        elif self._side_streaming:
            # Also handle side panel streaming
            self._side_streaming = False
            if self._side_panel:
                self._side_panel.set_input_enabled(True)
            self.status_bar.showMessage("Side panel interrupted", 1000)

    def _on_rollback_last_exchange(self) -> None:
        """Handle rollback request (Ctrl+Z)."""
        if self._is_streaming:
            self.status_bar.showMessage("Cannot rollback during generation", 2000)
            return

        # Try to remove last exchange from history
        removed = self._prompt_builder.history.remove_last_exchange()
        if removed:
            # Remove from UI
            self.chat_panel.remove_last_exchange()
            self._update_token_count()
            self.status_bar.showMessage("Rolled back last exchange", 2000)

            # Update regenerate button state
            self.sidebar.set_regenerate_enabled(
                self._prompt_builder.get_message_count() > 0
            )
        else:
            self.status_bar.showMessage("Nothing to rollback", 2000)

    # ==================== Crucible Integration ====================

    def _setup_crucible_state(self) -> None:
        """Load Crucible settings from persistence and update UI."""
        prefs = persistence.preferences
        self._crucible_enabled = prefs.crucible_enabled
        self._crucible_router = prefs.crucible_router

        # Update sidebar UI
        self.sidebar.set_crucible_enabled(self._crucible_enabled)
        self.sidebar.set_crucible_router(self._crucible_router)

    def _on_crucible_toggled(self, enabled: bool) -> None:
        """Handle Crucible toggle state change.

        Args:
            enabled: Whether Crucible is enabled
        """
        self._crucible_enabled = enabled

        # Initialize Crucible adapter lazily if needed
        if enabled and self._crucible_adapter is None:
            try:
                from ..orchestrator.crucible_adapter import CrucibleAdapter

                self._crucible_adapter = CrucibleAdapter()
            except ImportError as e:
                self.status_bar.showMessage(
                    "Crucible not installed. Install with: pip install -e C:\\Users\\erick\\projects\\Crucible",
                    5000,
                )
                self._crucible_enabled = False
                self.sidebar.set_crucible_enabled(False)
                return
            except ValueError as e:
                self.status_bar.showMessage(str(e), 5000)
                self._crucible_enabled = False
                self.sidebar.set_crucible_enabled(False)
                return

        # Update status bar
        if enabled:
            self.status_bar.showMessage(
                f"Crucible enabled with {self._crucible_router} router", 3000
            )
            self.model_label.setText("Model: Crucible Council")
        else:
            self.status_bar.showMessage("Crucible disabled", 2000)
            # Restore model label
            model_config = get_model(self._current_model_id)
            if model_config:
                self.model_label.setText(f"Model: {model_config.display_name}")

        # Save preference
        persistence.update_crucible_settings(enabled, self._crucible_router)

    def _on_crucible_router_changed(self, router_mode: str) -> None:
        """Handle Crucible router mode change.

        Args:
            router_mode: Selected router mode
        """
        self._crucible_router = router_mode

        if self._crucible_enabled:
            self.status_bar.showMessage(f"Crucible router: {router_mode}", 2000)

        # Save preference
        persistence.update_crucible_settings(self._crucible_enabled, router_mode)

    async def _stream_crucible_response(self, user_message: str, assistant_msg_index: int = -1) -> None:
        """Stream a response through Crucible deliberation.

        Args:
            user_message: The user's message for Crucible query
            assistant_msg_index: Index of the assistant message for TOC
        """
        if not self._crucible_adapter:
            self.chat_panel.add_error_message("Crucible adapter not initialized")
            return

        try:
            self.status_bar.showMessage("Crucible deliberating...", 0)

            # Run Crucible deliberation
            response = await self._crucible_adapter.run(user_message, self._crucible_router)

            # Display the response (Crucible doesn't stream, so we display all at once)
            self.chat_panel.append_to_assistant_message(response)
            self.chat_panel.finish_assistant_message()

            # Add to history
            self._prompt_builder.add_assistant_message(response)

            # Analyze completed response for TOC entry
            if assistant_msg_index >= 0:
                toc_entry = self._toc_generator.analyze_message(
                    response, "assistant", assistant_msg_index
                )
                if toc_entry:
                    self.sidebar.add_toc_entry(toc_entry)
                self.sidebar.set_toc_current_index(assistant_msg_index)

            self.status_bar.showMessage("Crucible response complete", 3000)

        except Exception as e:
            error_msg = str(e)
            self.chat_panel.add_error_message(f"Crucible error: {error_msg}")
            self.status_bar.showMessage(f"Crucible error: {error_msg}", 5000)

        finally:
            self._is_streaming = False
            self.input_panel.set_enabled(True)
            self.sidebar.set_regenerate_enabled(
                self._prompt_builder.get_message_count() > 0
            )
            self.input_panel.focus_input()
            self._update_token_count()
