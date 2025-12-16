"""Summary generator for context compression.

This module generates XML summaries of conversation history when triggered
by the orchestrator. It uses the active LLM to generate summaries.

The summary format follows CLAUDE.md's XML Summary Structure.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..llm.base_adapter import LLMAdapter
from ..orchestrator.intent_tracker import IntentMode


@dataclass
class SummaryResult:
    """Result of a summarization operation."""

    xml_summary: str
    messages_summarized: int
    success: bool
    error: Optional[str] = None


SUMMARY_PROMPT = """You are a context summarization assistant. Your task is to compress conversation history into a structured XML summary that preserves essential information for continuing the conversation.

Analyze the following conversation and create a summary in this exact XML format:

<ContextSummary>
    <GeneralSubject>The main topic or theme being discussed</GeneralSubject>
    <SpecificContext>
        <Subtopic>Specific areas or aspects being explored</Subtopic>
        <Entities>Key names, concepts, terms, or identifiers mentioned</Entities>
        <KeyPoints>Important facts, decisions, or conclusions reached</KeyPoints>
    </SpecificContext>
    <NextExpectedTopics>What the conversation seems to be heading toward</NextExpectedTopics>
    <UserIntent mode="{mode}">Brief description of user's apparent goal</UserIntent>
</ContextSummary>

Guidelines:
- Be concise but preserve all information needed to continue the conversation
- Include specific names, numbers, and technical terms
- Capture the user's apparent intent and goals
- Note any decisions made or preferences expressed
- The summary should allow seamless continuation without losing context

Conversation to summarize:
{conversation}

Generate only the XML summary, nothing else."""


class SummaryGenerator:
    """Generates XML summaries of conversation history.

    This class is called by the orchestrator when summarization is needed.
    It uses the provided LLM adapter to generate summaries.

    Does NOT:
    - Decide when to summarize (orchestrator's job)
    - Modify conversation history directly
    - Self-trigger
    """

    def __init__(self) -> None:
        """Initialize the summary generator."""
        pass

    async def generate_summary(
        self,
        messages: List[Dict[str, Any]],
        adapter: LLMAdapter,
        intent_mode: IntentMode = IntentMode.EXPLORATION,
        max_tokens: int = 1000,
    ) -> SummaryResult:
        """Generate an XML summary of the given messages.

        Args:
            messages: List of message dicts to summarize
            adapter: LLM adapter to use for generation
            intent_mode: Current user intent mode
            max_tokens: Maximum tokens for the summary

        Returns:
            SummaryResult with the generated summary
        """
        if not messages:
            return SummaryResult(
                xml_summary="",
                messages_summarized=0,
                success=False,
                error="No messages to summarize",
            )

        try:
            # Format conversation for the prompt
            conversation_text = self._format_conversation(messages)

            # Create the prompt with mode
            prompt = SUMMARY_PROMPT.format(
                mode=intent_mode.value,
                conversation=conversation_text,
            )

            # Generate summary using the adapter
            summary = await adapter.complete(
                messages=[{"role": "user", "content": prompt}],
                system="You are a precise summarization assistant. Output only valid XML.",
                max_tokens=max_tokens,
            )

            # Validate and clean the summary
            cleaned_summary = self._clean_summary(summary)

            if not self._validate_summary(cleaned_summary):
                return SummaryResult(
                    xml_summary=cleaned_summary,
                    messages_summarized=len(messages),
                    success=False,
                    error="Generated summary failed validation",
                )

            return SummaryResult(
                xml_summary=cleaned_summary,
                messages_summarized=len(messages),
                success=True,
            )

        except Exception as e:
            return SummaryResult(
                xml_summary="",
                messages_summarized=0,
                success=False,
                error=str(e),
            )

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into a readable conversation string.

        Args:
            messages: List of message dicts

        Returns:
            Formatted conversation string
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n\n".join(lines)

    def _clean_summary(self, summary: str) -> str:
        """Clean and extract XML from the summary response.

        Args:
            summary: Raw response from LLM

        Returns:
            Cleaned XML summary
        """
        # Try to extract just the XML if there's extra text
        summary = summary.strip()

        # Find XML start and end
        start_idx = summary.find("<ContextSummary>")
        end_idx = summary.find("</ContextSummary>")

        if start_idx != -1 and end_idx != -1:
            return summary[start_idx:end_idx + len("</ContextSummary>")]

        return summary

    def _validate_summary(self, summary: str) -> bool:
        """Validate that the summary has required XML structure.

        Args:
            summary: XML summary string

        Returns:
            True if valid
        """
        required_tags = [
            "<ContextSummary>",
            "</ContextSummary>",
            "<GeneralSubject>",
            "<SpecificContext>",
        ]

        return all(tag in summary for tag in required_tags)

    def format_for_prompt(self, xml_summary: str) -> str:
        """Format a summary for injection into the system prompt.

        Args:
            xml_summary: The XML summary

        Returns:
            Formatted string for prompt injection
        """
        return (
            "PREVIOUS CONTEXT HAS BEEN SUMMARIZED AS FOLLOWS:\n\n"
            f"{xml_summary}\n\n"
            "CONTINUE THE CONVERSATION SEAMLESSLY."
        )
