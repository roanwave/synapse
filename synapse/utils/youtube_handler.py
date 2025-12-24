"""YouTube transcript fetching and processing.

Handles fetching transcripts from YouTube videos for summarization.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    # Import from top-level module (proper API usage)
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
        CouldNotRetrieveTranscript,
    )
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    # Define placeholder classes for type hints when module not installed
    YouTubeTranscriptApi = None
    TranscriptsDisabled = Exception
    NoTranscriptFound = Exception
    VideoUnavailable = Exception
    CouldNotRetrieveTranscript = Exception


# Regex patterns for YouTube URLs
YOUTUBE_PATTERNS = [
    r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
]


@dataclass
class YouTubeTranscript:
    """Container for YouTube transcript data."""
    video_id: str
    transcript_text: str
    duration_seconds: int
    language: str
    is_auto_generated: bool

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string."""
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def to_context_block(self) -> str:
        """Format transcript as a context block for the prompt.

        Returns:
            Formatted string for inclusion in LLM context
        """
        source_type = "auto-generated" if self.is_auto_generated else "manual"
        return f"""<youtube_transcript>
<video_id>{self.video_id}</video_id>
<duration>{self.duration_formatted}</duration>
<language>{self.language}</language>
<transcript_type>{source_type}</transcript_type>
<content>
{self.transcript_text}
</content>
</youtube_transcript>"""


def extract_video_id(text: str) -> Optional[str]:
    """Extract YouTube video ID from a URL or text containing a URL.

    Args:
        text: Text that may contain a YouTube URL

    Returns:
        Video ID if found, None otherwise
    """
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def contains_youtube_url(text: str) -> bool:
    """Check if text contains a YouTube URL.

    Args:
        text: Text to check

    Returns:
        True if YouTube URL found
    """
    return extract_video_id(text) is not None


def fetch_transcript(video_id: str) -> Tuple[Optional[YouTubeTranscript], Optional[str]]:
    """Fetch transcript for a YouTube video.

    Args:
        video_id: YouTube video ID

    Returns:
        Tuple of (YouTubeTranscript or None, error message or None)
    """
    if not YOUTUBE_API_AVAILABLE:
        return None, "YouTube transcript API not installed. Run: pip install youtube-transcript-api"

    try:
        # Create API instance and fetch transcript
        # api.fetch() returns a FetchedTranscript object (iterable)
        api = YouTubeTranscriptApi()
        fetched = api.fetch(
            video_id,
            languages=['en', 'en-US', 'en-GB'],
            preserve_formatting=False
        )

        # FetchedTranscript is iterable - each item is a FetchedTranscriptSnippet
        # with attributes: .text, .start, .duration
        text_parts = []
        total_duration = 0

        for snippet in fetched:
            text_parts.append(snippet.text)
            end_time = snippet.start + snippet.duration
            if end_time > total_duration:
                total_duration = end_time

        full_text = ' '.join(text_parts)

        return YouTubeTranscript(
            video_id=fetched.video_id,
            transcript_text=full_text,
            duration_seconds=int(total_duration),
            language=fetched.language_code,
            is_auto_generated=fetched.is_generated,
        ), None

    except TranscriptsDisabled:
        return None, "Transcripts are disabled for this video"
    except VideoUnavailable:
        return None, "Video is unavailable (private, deleted, or restricted)"
    except NoTranscriptFound:
        return None, "No English transcript available for this video"
    except CouldNotRetrieveTranscript as e:
        return None, f"Could not retrieve transcript: {str(e)}"
    except Exception as e:
        return None, f"Failed to fetch transcript: {str(e)}"


def estimate_transcript_tokens(transcript: YouTubeTranscript) -> int:
    """Estimate token count for a transcript.

    Rough estimate: ~0.75 tokens per word for English text.

    Args:
        transcript: The transcript to estimate

    Returns:
        Estimated token count
    """
    word_count = len(transcript.transcript_text.split())
    return int(word_count * 0.75)


def is_video_too_long(duration_seconds: int, max_hours: float = 2.0) -> bool:
    """Check if video exceeds maximum length for auto-fetching.

    Args:
        duration_seconds: Video duration in seconds
        max_hours: Maximum allowed hours

    Returns:
        True if video is too long
    """
    max_seconds = max_hours * 3600
    return duration_seconds > max_seconds
