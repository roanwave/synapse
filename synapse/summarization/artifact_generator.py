"""Post-conversation artifact generation.

Generates structured artifacts from conversation history:
- Conversation outline (topics discussed)
- Decision log (conclusions reached)
- Research index (key terms, entities, sources)
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from ..llm.base_adapter import LLMAdapter


@dataclass
class ArtifactResult:
    """Result of artifact generation."""

    success: bool
    outline: Optional[str] = None
    decisions: Optional[str] = None
    research: Optional[str] = None
    error: Optional[str] = None


class ArtifactGenerator:
    """Generates post-conversation artifacts using the LLM."""

    OUTLINE_PROMPT = """Analyze this conversation and create a structured outline.

Format as markdown with:
- Main topics discussed (## headers)
- Key points under each topic (bullet points)
- Brief summary at the end

Be concise but comprehensive. Focus on substance, not meta-commentary.

CONVERSATION:
{conversation}

OUTPUT (markdown outline):"""

    DECISIONS_PROMPT = """Analyze this conversation and extract all decisions, conclusions, and action items.

Format as markdown with:
- Decisions made (explicit choices or conclusions)
- Recommendations given
- Action items or next steps mentioned
- Open questions remaining

If no clear decisions were made, state that briefly.

CONVERSATION:
{conversation}

OUTPUT (markdown decision log):"""

    RESEARCH_PROMPT = """Analyze this conversation and create a research index.

Format as markdown with:
- Key terms and concepts mentioned (with brief definitions if explained)
- Named entities (people, companies, products, technologies)
- Sources or references cited
- Technical terms or jargon used

Focus on indexable, searchable information.

CONVERSATION:
{conversation}

OUTPUT (markdown research index):"""

    def __init__(self) -> None:
        """Initialize the artifact generator."""
        pass

    async def generate_artifacts(
        self,
        messages: List[Dict[str, str]],
        adapter: LLMAdapter,
        generate_outline: bool = True,
        generate_decisions: bool = True,
        generate_research: bool = False,
    ) -> ArtifactResult:
        """Generate artifacts from conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            adapter: LLM adapter to use for generation
            generate_outline: Whether to generate conversation outline
            generate_decisions: Whether to generate decision log
            generate_research: Whether to generate research index

        Returns:
            ArtifactResult with generated content
        """
        try:
            # Format conversation for prompts
            conversation = self._format_conversation(messages)

            outline = None
            decisions = None
            research = None

            # Generate requested artifacts
            if generate_outline:
                outline = await self._generate_single(
                    self.OUTLINE_PROMPT.format(conversation=conversation),
                    adapter,
                )

            if generate_decisions:
                decisions = await self._generate_single(
                    self.DECISIONS_PROMPT.format(conversation=conversation),
                    adapter,
                )

            if generate_research:
                research = await self._generate_single(
                    self.RESEARCH_PROMPT.format(conversation=conversation),
                    adapter,
                )

            return ArtifactResult(
                success=True,
                outline=outline,
                decisions=decisions,
                research=research,
            )

        except Exception as e:
            return ArtifactResult(
                success=False,
                error=str(e),
            )

    async def _generate_single(
        self,
        prompt: str,
        adapter: LLMAdapter,
    ) -> str:
        """Generate a single artifact.

        Args:
            prompt: The generation prompt
            adapter: LLM adapter

        Returns:
            Generated content
        """
        messages = [{"role": "user", "content": prompt}]
        system = (
            "You are a precise assistant that generates structured summaries. "
            "Output only the requested format, no preamble or explanation."
        )

        response = await adapter.complete(messages, system, max_tokens=2000)
        return response.strip()

    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Format conversation messages for prompts.

        Args:
            messages: List of message dicts

        Returns:
            Formatted conversation string
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"[{role}]: {content}")
        return "\n\n".join(lines)

    def save_artifacts(
        self,
        result: ArtifactResult,
        session_id: str,
        output_dir: Path,
    ) -> List[Path]:
        """Save artifacts to disk.

        Args:
            result: ArtifactResult with generated content
            session_id: Session ID for filename
            output_dir: Directory to save to

        Returns:
            List of paths to saved files
        """
        saved = []
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if result.outline:
            path = output_dir / f"{session_id}_outline.md"
            self._save_markdown(
                path,
                "Conversation Outline",
                result.outline,
                timestamp,
            )
            saved.append(path)

        if result.decisions:
            path = output_dir / f"{session_id}_decisions.md"
            self._save_markdown(
                path,
                "Decision Log",
                result.decisions,
                timestamp,
            )
            saved.append(path)

        if result.research:
            path = output_dir / f"{session_id}_research.md"
            self._save_markdown(
                path,
                "Research Index",
                result.research,
                timestamp,
            )
            saved.append(path)

        return saved

    def _save_markdown(
        self,
        path: Path,
        title: str,
        content: str,
        timestamp: str,
    ) -> None:
        """Save a markdown file with header.

        Args:
            path: File path
            title: Document title
            content: Main content
            timestamp: Generation timestamp
        """
        header = f"""# {title}

*Generated: {timestamp}*

---

"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + content)
