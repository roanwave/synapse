"""Retrieval blacklist for topic-based exclusion.

Allows users to exclude specific topics or document sections
from being retrieved, even if they match the query.
"""

import re
from typing import List, Set, Dict, Optional
from pathlib import Path
import json
from dataclasses import dataclass, field

from . import Chunk, RetrievalResult


@dataclass
class BlacklistRule:
    """A rule for blacklisting content from retrieval."""

    rule_id: str
    pattern: str  # Regex pattern or keyword
    is_regex: bool = False
    description: str = ""
    enabled: bool = True

    def matches(self, text: str) -> bool:
        """Check if the rule matches the given text.

        Args:
            text: Text to check

        Returns:
            True if the rule matches
        """
        if not self.enabled:
            return False

        if self.is_regex:
            try:
                return bool(re.search(self.pattern, text, re.IGNORECASE))
            except re.error:
                return False
        else:
            return self.pattern.lower() in text.lower()


class RetrievalBlacklist:
    """Manages blacklist rules for retrieval filtering.

    Blacklisted content will be excluded from RAG results,
    even if it scores highly on semantic similarity.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize the blacklist.

        Args:
            config_path: Optional path to persist blacklist config
        """
        self._config_path = config_path
        self._rules: Dict[str, BlacklistRule] = {}
        self._doc_blacklist: Set[str] = set()  # Blacklisted doc IDs

        if config_path and config_path.exists():
            self._load()

    def add_rule(
        self,
        pattern: str,
        is_regex: bool = False,
        description: str = "",
    ) -> BlacklistRule:
        """Add a blacklist rule.

        Args:
            pattern: The pattern to match (keyword or regex)
            is_regex: Whether the pattern is a regex
            description: Human-readable description

        Returns:
            The created BlacklistRule
        """
        import uuid
        rule_id = str(uuid.uuid4())[:8]

        rule = BlacklistRule(
            rule_id=rule_id,
            pattern=pattern,
            is_regex=is_regex,
            description=description,
        )

        self._rules[rule_id] = rule
        self._save()

        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a blacklist rule.

        Args:
            rule_id: The rule ID to remove

        Returns:
            True if removed, False if not found
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            self._save()
            return True
        return False

    def enable_rule(self, rule_id: str, enabled: bool = True) -> bool:
        """Enable or disable a rule.

        Args:
            rule_id: The rule ID
            enabled: Whether to enable the rule

        Returns:
            True if updated, False if not found
        """
        if rule_id in self._rules:
            self._rules[rule_id].enabled = enabled
            self._save()
            return True
        return False

    def blacklist_document(self, doc_id: str) -> None:
        """Blacklist an entire document.

        Args:
            doc_id: The document ID to blacklist
        """
        self._doc_blacklist.add(doc_id)
        self._save()

    def unblacklist_document(self, doc_id: str) -> None:
        """Remove a document from the blacklist.

        Args:
            doc_id: The document ID to unblacklist
        """
        self._doc_blacklist.discard(doc_id)
        self._save()

    def is_document_blacklisted(self, doc_id: str) -> bool:
        """Check if a document is blacklisted.

        Args:
            doc_id: The document ID

        Returns:
            True if blacklisted
        """
        return doc_id in self._doc_blacklist

    def filter_results(
        self, results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Filter retrieval results through the blacklist.

        Args:
            results: Results to filter

        Returns:
            Filtered results with blacklisted items removed
        """
        filtered = []

        for result in results:
            # Check document blacklist
            if result.chunk.parent_id in self._doc_blacklist:
                continue

            # Check rule matches
            matching_rules = self.get_matching_rules(result.chunk.content)
            if matching_rules:
                continue

            filtered.append(result)

        return filtered

    def get_matching_rules(self, text: str) -> List[BlacklistRule]:
        """Get all rules that match the given text.

        Args:
            text: Text to check

        Returns:
            List of matching rules
        """
        return [rule for rule in self._rules.values() if rule.matches(text)]

    def get_blacklisted_topics(self, text: str) -> List[str]:
        """Get list of blacklisted topic names that match text.

        Args:
            text: Text to check

        Returns:
            List of matching topic patterns
        """
        return [
            rule.pattern
            for rule in self._rules.values()
            if rule.matches(text)
        ]

    def get_all_rules(self) -> List[BlacklistRule]:
        """Get all blacklist rules.

        Returns:
            List of all rules
        """
        return list(self._rules.values())

    def get_blacklisted_docs(self) -> Set[str]:
        """Get all blacklisted document IDs.

        Returns:
            Set of blacklisted doc IDs
        """
        return self._doc_blacklist.copy()

    def clear(self) -> None:
        """Clear all blacklist rules and document blacklists."""
        self._rules.clear()
        self._doc_blacklist.clear()
        self._save()

    def _save(self) -> None:
        """Save blacklist configuration to disk."""
        if not self._config_path:
            return

        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "pattern": r.pattern,
                    "is_regex": r.is_regex,
                    "description": r.description,
                    "enabled": r.enabled,
                }
                for r in self._rules.values()
            ],
            "blacklisted_docs": list(self._doc_blacklist),
        }

        with open(self._config_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        """Load blacklist configuration from disk."""
        if not self._config_path or not self._config_path.exists():
            return

        try:
            with open(self._config_path, "r") as f:
                data = json.load(f)

            # Load rules
            for rule_data in data.get("rules", []):
                rule = BlacklistRule(
                    rule_id=rule_data["rule_id"],
                    pattern=rule_data["pattern"],
                    is_regex=rule_data.get("is_regex", False),
                    description=rule_data.get("description", ""),
                    enabled=rule_data.get("enabled", True),
                )
                self._rules[rule.rule_id] = rule

            # Load document blacklist
            self._doc_blacklist = set(data.get("blacklisted_docs", []))

        except (json.JSONDecodeError, KeyError):
            # If loading fails, start fresh
            pass
