"""Dialogs for Synapse.

Exit confirmation, artifact generation, help, and about dialogs.
"""

from typing import Optional, Tuple, List, TYPE_CHECKING
from enum import Enum

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QFrame,
    QWidget,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

if TYPE_CHECKING:
    from ..storage.conversation_store import ConversationStore
    from ..storage import SessionRecord

from ..config.themes import theme, fonts, metrics


class ExitAction(Enum):
    """Exit dialog action choices."""
    CANCEL = "cancel"
    JUST_EXIT = "just_exit"
    SUMMARIZE_EXIT = "summarize_exit"


class ExitDialog(QDialog):
    """Exit confirmation dialog with artifact generation options."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        default_outline: bool = True,
        default_decisions: bool = True,
        default_research: bool = False,
    ) -> None:
        """Initialize the exit dialog.

        Args:
            parent: Parent widget
            default_outline: Default state for outline checkbox
            default_decisions: Default state for decisions checkbox
            default_research: Default state for research checkbox
        """
        super().__init__(parent)
        self._action = ExitAction.CANCEL
        self._default_outline = default_outline
        self._default_decisions = default_decisions
        self._default_research = default_research
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("End Session")
        self.setFixedSize(400, 320)
        self.setModal(True)

        # Remove default window frame for custom styling
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main container with premium styling
        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_secondary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_large}px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_large,
        )
        layout.setSpacing(metrics.padding_medium)

        # Title
        title = QLabel("End Session")
        title.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_primary};
                font-size: 18px;
                font-weight: 600;
                font-family: {fonts.ui};
            }}
        """)
        layout.addWidget(title)

        # Message
        message = QLabel(
            "Do you want to save a summary of this conversation?"
        )
        message.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
            }}
        """)
        message.setWordWrap(True)
        layout.addWidget(message)

        # Artifact options
        options_label = QLabel("Generate artifacts:")
        options_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_small}px;
                font-family: {fonts.ui};
                margin-top: 8px;
            }}
        """)
        layout.addWidget(options_label)

        # Checkboxes
        self.outline_check = QCheckBox("Conversation Outline")
        self.outline_check.setChecked(self._default_outline)
        self.outline_check.setStyleSheet(self._checkbox_style())
        layout.addWidget(self.outline_check)

        self.decisions_check = QCheckBox("Decision Log")
        self.decisions_check.setChecked(self._default_decisions)
        self.decisions_check.setStyleSheet(self._checkbox_style())
        layout.addWidget(self.decisions_check)

        self.research_check = QCheckBox("Research Index")
        self.research_check.setChecked(self._default_research)
        self.research_check.setStyleSheet(self._checkbox_style())
        layout.addWidget(self.research_check)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(metrics.padding_small)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._secondary_button_style())
        cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(cancel_btn)

        just_exit_btn = QPushButton("Just Exit")
        just_exit_btn.setStyleSheet(self._secondary_button_style())
        just_exit_btn.clicked.connect(self._on_just_exit)
        button_layout.addWidget(just_exit_btn)

        summarize_btn = QPushButton("Summarize && Exit")
        summarize_btn.setStyleSheet(self._primary_button_style())
        summarize_btn.clicked.connect(self._on_summarize_exit)
        button_layout.addWidget(summarize_btn)

        layout.addLayout(button_layout)

    def _checkbox_style(self) -> str:
        """Get checkbox stylesheet."""
        return f"""
            QCheckBox {{
                color: {theme.text_primary};
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
                spacing: 8px;
                padding: 4px 0;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: {metrics.radius_small}px;
                border: 1px solid {theme.border};
                background-color: {theme.background_secondary};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme.accent};
                border-color: {theme.accent};
            }}
            QCheckBox::indicator:hover {{
                border-color: {theme.accent};
            }}
        """

    def _primary_button_style(self) -> str:
        """Get primary button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_medium}px;
                padding: 10px 16px;
                font-weight: 500;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {theme.accent_pressed};
            }}
        """

    def _secondary_button_style(self) -> str:
        """Get secondary button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: 10px 16px;
                font-weight: 500;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QPushButton:hover {{
                background-color: {theme.border_subtle};
                border-color: {theme.border};
            }}
            QPushButton:pressed {{
                background-color: {theme.background_tertiary};
            }}
        """

    def _on_cancel(self) -> None:
        """Handle cancel button."""
        self._action = ExitAction.CANCEL
        self.reject()

    def _on_just_exit(self) -> None:
        """Handle just exit button."""
        self._action = ExitAction.JUST_EXIT
        self.accept()

    def _on_summarize_exit(self) -> None:
        """Handle summarize and exit button."""
        self._action = ExitAction.SUMMARIZE_EXIT
        self.accept()

    def get_result(self) -> Tuple[ExitAction, bool, bool, bool]:
        """Get dialog result.

        Returns:
            Tuple of (action, outline, decisions, research)
        """
        return (
            self._action,
            self.outline_check.isChecked(),
            self.decisions_check.isChecked(),
            self.research_check.isChecked(),
        )


class HelpDialog(QDialog):
    """Keyboard shortcuts help dialog."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the help dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Keyboard Shortcuts")
        self.setFixedSize(380, 400)
        self.setModal(True)

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_secondary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_large}px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_large,
        )
        layout.setSpacing(metrics.padding_medium)

        # Title
        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_primary};
                font-size: 18px;
                font-weight: 600;
                font-family: {fonts.ui};
            }}
        """)
        layout.addWidget(title)

        # Shortcuts list
        shortcuts = [
            ("Ctrl+Enter", "Send message"),
            ("Ctrl+N", "New conversation"),
            ("Ctrl+S", "Save session"),
            ("Ctrl+M", "Set waypoint"),
            ("Ctrl+R", "Regenerate response"),
            ("Ctrl+I", "Toggle inspector"),
            ("Ctrl+F", "Toggle focus mode"),
            ("Escape", "Close panel / Exit focus"),
            ("F1", "Show this help"),
        ]

        for key, description in shortcuts:
            row = QHBoxLayout()
            row.setSpacing(metrics.padding_medium)

            key_label = QLabel(key)
            key_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.text_primary};
                    font-size: {metrics.font_normal}px;
                    font-family: {fonts.mono};
                    background-color: {theme.background_secondary};
                    padding: 4px 8px;
                    border-radius: {metrics.radius_small}px;
                }}
            """)
            key_label.setFixedWidth(120)
            row.addWidget(key_label)

            desc_label = QLabel(description)
            desc_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.text_secondary};
                    font-size: {metrics.font_normal}px;
                    font-family: {fonts.ui};
                }}
            """)
            row.addWidget(desc_label, stretch=1)

            layout.addLayout(row)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_medium}px;
                padding: 10px 24px;
                font-weight: 500;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def keyPressEvent(self, event) -> None:
        """Handle key press - close on Escape or F1."""
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_F1):
            self.accept()
        else:
            super().keyPressEvent(event)


class AboutDialog(QDialog):
    """About dialog showing app info."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the about dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("About Synapse")
        self.setFixedSize(340, 280)
        self.setModal(True)

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_secondary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_large}px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_large,
        )
        layout.setSpacing(metrics.padding_small)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # App name
        name_label = QLabel("Synapse")
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_primary};
                font-size: 28px;
                font-weight: 700;
                font-family: {fonts.ui};
            }}
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # Version
        version_label = QLabel("Version 1.0.0")
        version_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
            }}
        """)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        layout.addSpacing(metrics.padding_medium)

        # Description
        desc_label = QLabel(
            "A private thinking environment.\n"
            "Multi-model chat with invisible context management,\n"
            "document-aware RAG, and flow-state-preserving UX."
        )
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_small}px;
                font-family: {fonts.ui};
                line-height: 1.5;
            }}
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_medium}px;
                padding: 10px 24px;
                font-weight: 500;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def keyPressEvent(self, event) -> None:
        """Handle key press - close on Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)


class NotificationToast(QLabel):
    """Transient notification toast for model switching etc."""

    def __init__(
        self,
        message: str,
        parent: Optional[QWidget] = None,
        duration_ms: int = 2000,
    ) -> None:
        """Initialize the notification.

        Args:
            message: Message to display
            parent: Parent widget
            duration_ms: How long to show (milliseconds)
        """
        super().__init__(message, parent)
        self._duration = duration_ms
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the premium toast UI."""
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
                font-weight: 500;
                padding: 10px 20px;
                border-radius: {metrics.radius_large}px;
                border: 1px solid {theme.border};
            }}
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.adjustSize()

    def show_at(self, x: int, y: int) -> None:
        """Show the toast at specified position.

        Args:
            x: X position
            y: Y position
        """
        from PySide6.QtCore import QTimer

        self.move(x, y)
        self.show()
        self.raise_()

        # Auto-hide after duration
        QTimer.singleShot(self._duration, self._fade_out)

    def _fade_out(self) -> None:
        """Fade out and hide."""
        # Simple hide for now (could add animation)
        self.hide()
        self.deleteLater()


class SessionBrowserDialog(QDialog):
    """Dialog for browsing and selecting past sessions."""

    def __init__(
        self,
        conversation_store: "ConversationStore",
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the session browser dialog.

        Args:
            conversation_store: The conversation store to browse
            parent: Parent widget
        """
        super().__init__(parent)
        self._conversation_store = conversation_store
        self._sessions: List = []
        self._selected_session = None
        self._setup_ui()
        self._load_sessions()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Open Session")
        self.setFixedSize(500, 400)
        self.setModal(True)

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_secondary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_large}px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_large,
        )
        layout.setSpacing(metrics.padding_medium)

        # Title
        title = QLabel("Open Session")
        title.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_primary};
                font-size: 18px;
                font-weight: 600;
                font-family: {fonts.ui};
            }}
        """)
        layout.addWidget(title)

        # Description
        desc = QLabel("Select a previous session to view:")
        desc.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
            }}
        """)
        layout.addWidget(desc)

        # Session list
        self.session_list = QListWidget()
        self.session_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
                padding: {metrics.padding_small}px;
            }}
            QListWidget::item {{
                padding: {metrics.padding_medium}px;
                border-radius: {metrics.radius_small}px;
                margin: 2px 0;
            }}
            QListWidget::item:selected {{
                background-color: {theme.accent};
            }}
            QListWidget::item:hover {{
                background-color: {theme.background_tertiary};
            }}
        """)
        self.session_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.session_list, stretch=1)

        # Info label for selected session
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: {metrics.font_small}px;
                font-family: {fonts.mono};
            }}
        """)
        self.info_label.setWordWrap(True)
        self.session_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.info_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(metrics.padding_small)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._secondary_button_style())
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()

        open_btn = QPushButton("Open")
        open_btn.setStyleSheet(self._primary_button_style())
        open_btn.clicked.connect(self._on_open_clicked)
        button_layout.addWidget(open_btn)

        layout.addLayout(button_layout)

    def _load_sessions(self) -> None:
        """Load sessions from the conversation store."""
        self._sessions = self._conversation_store.get_recent_sessions(limit=50)

        if not self._sessions:
            self.session_list.addItem("No saved sessions found")
            self.session_list.item(0).setFlags(Qt.ItemFlag.NoItemFlags)
            return

        for session in self._sessions:
            started = session.started_at.strftime("%Y-%m-%d %H:%M")
            models = ", ".join(session.models_used[:2]) if session.models_used else "unknown"
            if len(session.models_used) > 2:
                models += f" +{len(session.models_used) - 2}"

            item_text = f"{started} | {models} | {session.token_count:,} tokens"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, session.session_id)
            self.session_list.addItem(item)

    def _on_selection_changed(self) -> None:
        """Handle session selection change."""
        items = self.session_list.selectedItems()
        if not items:
            self.info_label.setText("")
            return

        session_id = items[0].data(Qt.ItemDataRole.UserRole)
        session = next((s for s in self._sessions if s.session_id == session_id), None)

        if session:
            ended = session.ended_at.strftime("%H:%M") if session.ended_at else "?"
            info = f"Session ID: {session.session_id[:8]}...\n"
            info += f"Duration: {session.started_at.strftime('%H:%M')} - {ended}\n"
            info += f"Drift events: {session.drift_events}"
            if session.artifacts_generated:
                info += f" | Artifacts: {', '.join(session.artifacts_generated)}"
            self.info_label.setText(info)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on item."""
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id:
            self._selected_session = next(
                (s for s in self._sessions if s.session_id == session_id), None
            )
            self.accept()

    def _on_open_clicked(self) -> None:
        """Handle open button click."""
        items = self.session_list.selectedItems()
        if items:
            session_id = items[0].data(Qt.ItemDataRole.UserRole)
            if session_id:
                self._selected_session = next(
                    (s for s in self._sessions if s.session_id == session_id), None
                )
                self.accept()

    def get_selected_session(self):
        """Get the selected session.

        Returns:
            SessionRecord if selected, None otherwise
        """
        return self._selected_session

    def _primary_button_style(self) -> str:
        """Get primary button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_medium}px;
                padding: 10px 24px;
                font-weight: 500;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {theme.accent_pressed};
            }}
        """

    def _secondary_button_style(self) -> str:
        """Get secondary button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: 10px 24px;
                font-weight: 500;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QPushButton:hover {{
                background-color: {theme.border_subtle};
                border-color: {theme.border};
            }}
            QPushButton:pressed {{
                background-color: {theme.background_tertiary};
            }}
        """

    def keyPressEvent(self, event) -> None:
        """Handle key press - close on Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)


class SummaryViewerDialog(QDialog):
    """Dialog for viewing XML session summaries."""

    def __init__(
        self,
        summary_xml: str,
        session_id: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the summary viewer dialog.

        Args:
            summary_xml: The XML summary content
            session_id: Optional session ID for display
            parent: Parent widget
        """
        super().__init__(parent)
        self._summary_xml = summary_xml
        self._session_id = session_id
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Session Summary")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_secondary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_large}px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_xlarge,
            metrics.padding_large,
        )
        layout.setSpacing(metrics.padding_medium)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(metrics.padding_medium)

        title = QLabel("Session Summary")
        title.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_primary};
                font-size: 18px;
                font-weight: 600;
                font-family: {fonts.ui};
            }}
        """)
        header_layout.addWidget(title)

        if self._session_id:
            session_label = QLabel(f"({self._session_id[:8]}...)")
            session_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.text_muted};
                    font-size: {metrics.font_small}px;
                    font-family: {fonts.mono};
                }}
            """)
            header_layout.addWidget(session_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # XML content display
        from PySide6.QtWidgets import QTextEdit
        self.content_display = QTextEdit()
        self.content_display.setReadOnly(True)
        self.content_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.code_bg};
                color: {theme.text_primary};
                border: 1px solid {theme.code_border};
                border-radius: {metrics.radius_medium}px;
                padding: {metrics.padding_medium}px;
                font-family: {fonts.mono};
                font-size: 13px;
            }}
        """)

        # Format and display the XML with syntax highlighting
        formatted_xml = self._format_xml(self._summary_xml)
        self.content_display.setHtml(formatted_xml)
        layout.addWidget(self.content_display, stretch=1)

        # Copy button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setStyleSheet(self._secondary_button_style())
        copy_btn.clicked.connect(self._on_copy)
        button_layout.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(self._primary_button_style())
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _format_xml(self, xml_text: str) -> str:
        """Format XML with syntax highlighting.

        Args:
            xml_text: Raw XML text

        Returns:
            HTML with syntax highlighting
        """
        import html

        # Escape HTML entities first
        escaped = html.escape(xml_text)

        # Add colors for XML elements
        # Tags in accent color
        import re
        highlighted = re.sub(
            r'(&lt;/?)([\w]+)',
            f'<span style="color: {theme.accent};">\\1\\2</span>',
            escaped
        )
        # Close tags
        highlighted = re.sub(
            r'(&gt;)',
            f'<span style="color: {theme.accent};">\\1</span>',
            highlighted
        )

        return f"""
        <pre style="
            font-family: {fonts.mono};
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        ">{highlighted}</pre>
        """

    def _on_copy(self) -> None:
        """Copy XML to clipboard."""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self._summary_xml)

        # Brief feedback
        sender = self.sender()
        if sender:
            original_text = sender.text()
            sender.setText("Copied!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: sender.setText(original_text))

    def _primary_button_style(self) -> str:
        """Get primary button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_medium}px;
                padding: 10px 24px;
                font-weight: 500;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {theme.accent_pressed};
            }}
        """

    def _secondary_button_style(self) -> str:
        """Get secondary button stylesheet."""
        return f"""
            QPushButton {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: 10px 24px;
                font-weight: 500;
                font-family: {fonts.ui};
                font-size: {metrics.font_normal}px;
            }}
            QPushButton:hover {{
                background-color: {theme.border_subtle};
                border-color: {theme.border};
            }}
            QPushButton:pressed {{
                background-color: {theme.background_tertiary};
            }}
        """

    def keyPressEvent(self, event) -> None:
        """Handle key press - close on Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)
