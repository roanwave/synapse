"""Memory panel for viewing and editing unified memory facts."""

from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QComboBox,
    QLineEdit,
    QMenu,
    QSplitter,
)
from PySide6.QtCore import Qt, Signal

from ..config.themes import theme, fonts, metrics
from ..storage.unified_memory import UnifiedMemory, MemoryFact


class MemoryFactWidget(QFrame):
    """Widget displaying a single memory fact."""

    edit_requested = Signal(str)  # fact_id
    delete_requested = Signal(str)  # fact_id

    def __init__(
        self,
        fact: MemoryFact,
        parent: QWidget | None = None
    ):
        """Initialize the fact widget.

        Args:
            fact: The memory fact to display
            parent: Parent widget
        """
        super().__init__(parent)
        self._fact = fact
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            metrics.padding_medium,
            metrics.padding_small,
            metrics.padding_medium,
            metrics.padding_small,
        )
        layout.setSpacing(4)

        # Header row with category badge
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        # Category badge
        category_colors = {
            "preference": theme.accent,
            "fact": theme.text_muted,
            "person": theme.success,
            "project": theme.warning,
            "custom": theme.text_secondary,
        }
        color = category_colors.get(self._fact.category, theme.text_muted)

        category_label = QLabel(self._fact.category.upper())
        category_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 9px;
                font-weight: 600;
                letter-spacing: 0.5px;
                font-family: {fonts.ui};
                background-color: {theme.background_elevated};
                padding: 2px 6px;
                border-radius: 3px;
            }}
        """)
        header_row.addWidget(category_label)

        # Date
        date_str = self._fact.created_at.strftime("%Y-%m-%d")
        date_label = QLabel(date_str)
        date_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_disabled};
                font-size: 10px;
                font-family: {fonts.ui};
            }}
        """)
        header_row.addWidget(date_label)
        header_row.addStretch()

        layout.addLayout(header_row)

        # Content
        content_label = QLabel(self._fact.content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_primary};
                font-size: {metrics.font_normal}px;
                font-family: {fonts.chat};
            }}
        """)
        layout.addWidget(content_label)

        # Frame styling
        self.setStyleSheet(f"""
            MemoryFactWidget {{
                background-color: {theme.background_elevated};
                border: 1px solid {theme.border_subtle};
                border-radius: {metrics.radius_medium}px;
            }}
            MemoryFactWidget:hover {{
                border-color: {theme.border};
            }}
        """)

        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos) -> None:
        """Show context menu for fact actions."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: {metrics.padding_small}px;
                font-family: {fonts.ui};
            }}
            QMenu::item {{
                padding: {metrics.padding_small}px {metrics.padding_large}px;
                border-radius: {metrics.radius_small}px;
            }}
            QMenu::item:selected {{
                background-color: {theme.accent};
                color: white;
            }}
        """)

        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == edit_action:
            self.edit_requested.emit(self._fact.fact_id)
        elif action == delete_action:
            self.delete_requested.emit(self._fact.fact_id)


class AddFactDialog(QDialog):
    """Dialog for adding a new memory fact."""

    def __init__(self, parent: QWidget | None = None):
        """Initialize the dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Add Memory")
        self.setMinimumWidth(400)
        self.setStyleSheet(f"background-color: {theme.background_secondary};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            metrics.padding_large,
            metrics.padding_large,
            metrics.padding_large,
            metrics.padding_large,
        )
        layout.setSpacing(metrics.padding_medium)

        # Category selector
        category_layout = QHBoxLayout()
        category_label = QLabel("Category:")
        category_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
            }}
        """)
        category_layout.addWidget(category_label)

        self._category_combo = QComboBox()
        self._category_combo.addItems(["fact", "preference", "person", "project", "custom"])
        self._category_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                padding: 6px 12px;
                font-family: {fonts.ui};
                min-width: 120px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                selection-background-color: {theme.accent};
            }}
        """)
        category_layout.addWidget(self._category_combo)
        category_layout.addStretch()
        layout.addLayout(category_layout)

        # Content input
        content_label = QLabel("What should I remember?")
        content_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_secondary};
                font-size: {metrics.font_normal}px;
                font-family: {fonts.ui};
            }}
        """)
        layout.addWidget(content_label)

        self._content_input = QTextEdit()
        self._content_input.setPlaceholderText("Enter a fact, preference, or context to remember...")
        self._content_input.setMaximumHeight(100)
        self._content_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_medium}px;
                padding: {metrics.padding_small}px;
                font-size: {metrics.font_normal}px;
                font-family: {fonts.chat};
            }}
            QTextEdit:focus {{
                border-color: {theme.accent};
            }}
        """)
        layout.addWidget(self._content_input)

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.text_secondary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                padding: 8px 16px;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                background-color: {theme.background_elevated};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_small}px;
                padding: 8px 16px;
                font-family: {fonts.ui};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        save_btn.clicked.connect(self.accept)
        button_row.addWidget(save_btn)

        layout.addLayout(button_row)

    def get_fact_data(self) -> tuple[str, str]:
        """Get the entered fact data.

        Returns:
            Tuple of (content, category)
        """
        return (
            self._content_input.toPlainText().strip(),
            self._category_combo.currentText()
        )


class MemoryPanel(QDialog):
    """Dialog for viewing and managing unified memory."""

    def __init__(
        self,
        memory: UnifiedMemory,
        parent: QWidget | None = None
    ):
        """Initialize the memory panel.

        Args:
            memory: UnifiedMemory instance
            parent: Parent widget
        """
        super().__init__(parent)
        self._memory = memory
        self._fact_widgets: List[MemoryFactWidget] = []
        self._setup_ui()
        self._refresh_facts()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Memory")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(f"background-color: {theme.background_secondary};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_tertiary};
                border-bottom: 1px solid {theme.border_subtle};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(
            metrics.padding_large,
            metrics.padding_medium,
            metrics.padding_large,
            metrics.padding_medium,
        )

        title = QLabel("UNIFIED MEMORY")
        title.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_muted};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                font-family: {fonts.ui};
            }}
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Fact count
        self._count_label = QLabel("0 facts")
        self._count_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.text_disabled};
                font-size: 11px;
                font-family: {fonts.ui};
            }}
        """)
        header_layout.addWidget(self._count_label)

        layout.addWidget(header)

        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_tertiary};
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(
            metrics.padding_large,
            metrics.padding_small,
            metrics.padding_large,
            metrics.padding_small,
        )

        # Category filter
        self._filter_combo = QComboBox()
        self._filter_combo.addItem("All Categories", "all")
        for cat in UnifiedMemory.CATEGORIES:
            self._filter_combo.addItem(cat.capitalize(), cat)
        self._filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                padding: 4px 12px;
                font-size: 12px;
                font-family: {fonts.ui};
                min-width: 120px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        self._filter_combo.currentIndexChanged.connect(self._refresh_facts)
        toolbar_layout.addWidget(self._filter_combo)

        toolbar_layout.addStretch()

        # Add button
        add_btn = QPushButton("+ Add Memory")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: {metrics.radius_small}px;
                padding: 6px 12px;
                font-size: 12px;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
        """)
        add_btn.clicked.connect(self._on_add_fact)
        toolbar_layout.addWidget(add_btn)

        layout.addWidget(toolbar)

        # Facts list
        self._facts_container = QWidget()
        self._facts_container.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.background_secondary};
            }}
        """)
        self._facts_layout = QVBoxLayout(self._facts_container)
        self._facts_layout.setContentsMargins(
            metrics.padding_large,
            metrics.padding_medium,
            metrics.padding_large,
            metrics.padding_medium,
        )
        self._facts_layout.setSpacing(metrics.padding_small)
        self._facts_layout.addStretch()

        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme.background_secondary};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {theme.background_secondary};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.border};
                border-radius: 4px;
            }}
        """)
        scroll.setWidget(self._facts_container)
        layout.addWidget(scroll, stretch=1)

        # Footer
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.background_tertiary};
                border-top: 1px solid {theme.border_subtle};
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(
            metrics.padding_large,
            metrics.padding_medium,
            metrics.padding_large,
            metrics.padding_medium,
        )

        clear_btn = QPushButton("Clear All")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme.text_disabled};
                border: none;
                font-size: 12px;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                color: {theme.error};
            }}
        """)
        clear_btn.clicked.connect(self._on_clear_all)
        footer_layout.addWidget(clear_btn)

        footer_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.background_elevated};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: {metrics.radius_small}px;
                padding: 8px 24px;
                font-family: {fonts.ui};
            }}
            QPushButton:hover {{
                border-color: {theme.accent};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)

        layout.addWidget(footer)

    def _refresh_facts(self) -> None:
        """Refresh the facts list."""
        # Clear existing widgets
        for widget in self._fact_widgets:
            widget.deleteLater()
        self._fact_widgets.clear()

        # Get filtered facts
        category = self._filter_combo.currentData()
        if category == "all":
            facts = self._memory.get_all_facts()
        else:
            facts = self._memory.get_facts_by_category(category)

        # Sort by date descending
        facts.sort(key=lambda f: f.created_at, reverse=True)

        # Update count
        self._count_label.setText(f"{len(facts)} fact{'s' if len(facts) != 1 else ''}")

        # Remove stretch
        if self._facts_layout.count() > 0:
            self._facts_layout.takeAt(self._facts_layout.count() - 1)

        # Add fact widgets
        for fact in facts:
            widget = MemoryFactWidget(fact)
            widget.edit_requested.connect(self._on_edit_fact)
            widget.delete_requested.connect(self._on_delete_fact)
            self._facts_layout.addWidget(widget)
            self._fact_widgets.append(widget)

        # Re-add stretch
        self._facts_layout.addStretch()

    def _on_add_fact(self) -> None:
        """Handle add fact button click."""
        dialog = AddFactDialog(self)
        if dialog.exec():
            content, category = dialog.get_fact_data()
            if content:
                self._memory.add_fact(content, category)
                self._refresh_facts()

    def _on_edit_fact(self, fact_id: str) -> None:
        """Handle fact edit request.

        Args:
            fact_id: ID of fact to edit
        """
        # Find the fact
        facts = self._memory.get_all_facts()
        fact = next((f for f in facts if f.fact_id == fact_id), None)
        if not fact:
            return

        # Show edit dialog (reuse add dialog)
        dialog = AddFactDialog(self)
        dialog.setWindowTitle("Edit Memory")
        dialog._content_input.setText(fact.content)
        dialog._category_combo.setCurrentText(fact.category)

        if dialog.exec():
            content, _ = dialog.get_fact_data()
            if content:
                self._memory.update_fact(fact_id, content)
                self._refresh_facts()

    def _on_delete_fact(self, fact_id: str) -> None:
        """Handle fact delete request.

        Args:
            fact_id: ID of fact to delete
        """
        self._memory.remove_fact(fact_id)
        self._refresh_facts()

    def _on_clear_all(self) -> None:
        """Handle clear all button click."""
        if self._memory.get_fact_count() > 0:
            self._memory.clear()
            self._refresh_facts()
