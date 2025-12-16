"""Prompt inspector/debugger sidebar.

Provides visibility into the assembled prompt, RAG context,
and token usage for debugging and transparency.
"""

from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QTabWidget,
    QPushButton,
    QScrollArea,
    QFrame,
    QTreeWidget,
    QTreeWidgetItem,
)
from PySide6.QtCore import Qt, Signal

from ..config.themes import theme, fonts, metrics


class InspectorPanel(QWidget):
    """Prompt debugger sidebar panel.

    Shows the full assembled prompt, RAG context, token counts,
    and other debugging information. Toggle-able for power users.
    """

    closed = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize the inspector panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the inspector UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
            metrics.padding_medium,
        )
        layout.setSpacing(metrics.padding_medium)

        # Header with close button
        header = QHBoxLayout()
        title = QLabel("Prompt Inspector")
        title.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_primary};
                font-size: {metrics.font_medium}px;
                font-weight: 600;
                font-family: {fonts.ui};
            }}
        """)
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme.text_secondary};
                border: none;
                font-size: 20px;
                font-weight: bold;
                border-radius: {metrics.radius_small}px;
            }}
            QPushButton:hover {{
                color: {theme.text_primary};
                background-color: {theme.background_secondary};
            }}
        """)
        close_btn.clicked.connect(self.closed.emit)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Tab widget for different views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                background-color: {theme.background_secondary};
            }}
            QTabBar::tab {{
                background-color: {theme.background_tertiary};
                color: {theme.text_secondary};
                padding: {metrics.padding_small}px {metrics.padding_medium}px;
                border: 1px solid {theme.border};
                border-bottom: none;
                border-top-left-radius: {metrics.radius_small}px;
                border-top-right-radius: {metrics.radius_small}px;
                font-family: {fonts.ui};
                font-size: {metrics.font_small}px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme.background_secondary};
                color: {theme.text_primary};
            }}
            QTabBar::tab:hover {{
                color: {theme.text_primary};
            }}
        """)

        # Prompt tab
        self.prompt_view = QTextEdit()
        self.prompt_view.setReadOnly(True)
        self.prompt_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.background};
                color: {theme.text_primary};
                border: none;
                font-family: {fonts.mono};
                font-size: {metrics.font_small}px;
                padding: {metrics.padding_small}px;
                selection-background-color: {theme.accent};
            }}
        """)
        self.tabs.addTab(self.prompt_view, "Prompt")

        # RAG Context tab
        self.rag_view = QTextEdit()
        self.rag_view.setReadOnly(True)
        self.rag_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.background};
                color: {theme.text_primary};
                border: none;
                font-family: {fonts.mono};
                font-size: {metrics.font_small}px;
                padding: {metrics.padding_small}px;
                selection-background-color: {theme.accent};
            }}
        """)
        self.tabs.addTab(self.rag_view, "RAG Context")

        # Metadata tab with tree view
        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["Property", "Value"])
        self.metadata_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {theme.background};
                color: {theme.text_primary};
                border: none;
                font-family: {fonts.mono};
                font-size: {metrics.font_small}px;
            }}
            QTreeWidget::item {{
                padding: {metrics.padding_small}px;
            }}
            QTreeWidget::item:selected {{
                background-color: {theme.accent};
            }}
            QTreeWidget::item:hover {{
                background-color: {theme.background_tertiary};
            }}
            QHeaderView::section {{
                background-color: {theme.background_tertiary};
                color: {theme.text_secondary};
                padding: {metrics.padding_small}px;
                border: none;
                border-bottom: 1px solid {theme.border};
                font-family: {fonts.ui};
                font-size: {metrics.font_small}px;
                font-weight: 600;
            }}
        """)
        self.tabs.addTab(self.metadata_tree, "Metadata")

        layout.addWidget(self.tabs)

        # Token summary at bottom
        self.token_summary = QLabel("Tokens: --")
        self.token_summary.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: {metrics.font_small}px;
                font-family: {fonts.mono};
                padding: {metrics.padding_small}px;
                background-color: {theme.background_secondary};
                border-radius: {metrics.radius_small}px;
            }}
        """)
        layout.addWidget(self.token_summary)

        # Set width
        self.setFixedWidth(380)

        # Style
        self.setStyleSheet(f"""
            InspectorPanel {{
                background-color: {theme.background_tertiary};
                border-left: 1px solid {theme.border};
            }}
        """)

    def update_prompt(self, prompt_text: str) -> None:
        """Update the prompt view.

        Args:
            prompt_text: The full assembled prompt
        """
        self.prompt_view.setPlainText(prompt_text)

    def update_rag_context(
        self,
        chunks: List[Dict[str, Any]],
        query: str = "",
    ) -> None:
        """Update the RAG context view.

        Args:
            chunks: List of retrieved chunks with metadata
            query: The query used for retrieval
        """
        lines = []

        if query:
            lines.append(f"Query: {query}")
            lines.append("-" * 40)
            lines.append("")

        if not chunks:
            lines.append("No RAG context retrieved")
        else:
            for i, chunk in enumerate(chunks):
                lines.append(f"[Chunk {i + 1}]")
                lines.append(f"  Source: {chunk.get('source_file', 'unknown')}")
                lines.append(f"  Section: {chunk.get('page_or_section', '-')}")
                lines.append(f"  Score: {chunk.get('similarity_score', 0):.3f}")
                lines.append(f"  Content ({len(chunk.get('content', ''))} chars):")

                # Truncate long content
                content = chunk.get("content", "")
                if len(content) > 500:
                    content = content[:500] + "..."
                lines.append(f"    {content}")
                lines.append("")

        self.rag_view.setPlainText("\n".join(lines))

    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update the metadata tree view.

        Args:
            metadata: Dictionary of metadata to display
        """
        self.metadata_tree.clear()

        def add_items(parent: QTreeWidgetItem | None, data: Any, key: str = "") -> None:
            if isinstance(data, dict):
                if parent is None:
                    for k, v in data.items():
                        item = QTreeWidgetItem([str(k), ""])
                        self.metadata_tree.addTopLevelItem(item)
                        add_items(item, v, str(k))
                else:
                    for k, v in data.items():
                        item = QTreeWidgetItem([str(k), ""])
                        parent.addChild(item)
                        add_items(item, v, str(k))
            elif isinstance(data, list):
                if parent:
                    parent.setText(1, f"[{len(data)} items]")
                    for i, item_data in enumerate(data):
                        item = QTreeWidgetItem([f"[{i}]", ""])
                        parent.addChild(item)
                        add_items(item, item_data)
            else:
                if parent:
                    parent.setText(1, str(data))

        add_items(None, metadata)
        self.metadata_tree.expandAll()

    def update_token_summary(
        self,
        total: int,
        system: int = 0,
        history: int = 0,
        rag: int = 0,
        context_window: int = 0,
    ) -> None:
        """Update the token summary.

        Args:
            total: Total token count
            system: System prompt tokens
            history: Conversation history tokens
            rag: RAG context tokens
            context_window: Model's context window size
        """
        parts = [f"Total: {total:,}"]
        if system:
            parts.append(f"System: {system:,}")
        if history:
            parts.append(f"History: {history:,}")
        if rag:
            parts.append(f"RAG: {rag:,}")
        if context_window:
            usage = (total / context_window) * 100
            parts.append(f"Usage: {usage:.1f}%")

        self.token_summary.setText(" | ".join(parts))


class InspectorButton(QPushButton):
    """Toggle button for showing/hiding the inspector."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the inspector button.

        Args:
            parent: Parent widget
        """
        super().__init__("Inspector", parent)
        self._is_active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def set_active(self, active: bool) -> None:
        """Set the active state.

        Args:
            active: Whether inspector is visible
        """
        self._is_active = active
        self._update_style()

    def _update_style(self) -> None:
        """Update button style based on state."""
        if self._is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.accent};
                    color: white;
                    border: none;
                    border-radius: {metrics.radius_small}px;
                    padding: {metrics.padding_small}px {metrics.padding_medium}px;
                    font-size: {metrics.font_small}px;
                    font-family: {fonts.ui};
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {theme.accent_hover};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme.background_tertiary};
                    color: {theme.text_secondary};
                    border: 1px solid {theme.border};
                    border-radius: {metrics.radius_small}px;
                    padding: {metrics.padding_small}px {metrics.padding_medium}px;
                    font-size: {metrics.font_small}px;
                    font-family: {fonts.ui};
                }}
                QPushButton:hover {{
                    background-color: {theme.background_secondary};
                    color: {theme.text_primary};
                    border-color: {theme.accent};
                }}
            """)
