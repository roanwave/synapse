"""Markdown to HTML renderer for chat messages.

Converts markdown text to styled HTML that matches the app's dark theme.
"""

import re
from typing import Optional

try:
    import markdown
    from markdown.extensions.fenced_code import FencedCodeExtension
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.nl2br import Nl2BrExtension
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

from ..config.themes import theme, fonts, metrics


def get_markdown_css() -> str:
    """Get CSS styles for rendered markdown content.

    Returns:
        CSS stylesheet string
    """
    return f"""
        body {{
            color: {theme.text_primary};
            font-family: {fonts.chat};
            font-size: {metrics.font_medium}px;
            line-height: 1.3;
            margin: 0;
            padding: 0;
        }}

        /* Headings - minimal spacing */
        h1, h2, h3, h4, h5, h6 {{
            color: {theme.text_primary};
            font-family: {fonts.ui};
            margin-top: 4px;
            margin-bottom: 2px;
            font-weight: 600;
        }}
        h1 {{ font-size: 1.2em; }}
        h2 {{ font-size: 1.15em; }}
        h3 {{ font-size: 1.1em; }}
        h4, h5, h6 {{ font-size: 1em; }}

        /* Paragraphs - tight */
        p {{
            margin-top: 0;
            margin-bottom: 3px;
        }}

        /* Bold and italic */
        strong, b {{
            font-weight: 600;
            color: {theme.text_primary};
        }}
        em, i {{
            font-style: italic;
        }}

        /* Links */
        a {{
            color: {theme.accent};
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}

        /* Lists - very tight */
        ul, ol {{
            margin-top: 0;
            margin-bottom: 3px;
            padding-left: 18px;
        }}
        li {{
            margin-bottom: 0;
            padding-bottom: 0;
        }}
        li p {{
            margin-top: 1px;
            margin-bottom: 2px;
        }}

        /* Code - inline */
        code {{
            font-family: {fonts.mono};
            font-size: 0.9em;
            background-color: {theme.background_tertiary};
            padding: 1px 3px;
            border-radius: 2px;
            color: {theme.text_primary};
        }}

        /* Code blocks */
        pre {{
            font-family: {fonts.mono};
            font-size: 0.9em;
            background-color: {theme.background_tertiary};
            padding: 6px;
            border-radius: 3px;
            overflow-x: auto;
            margin: 3px 0;
            border: 1px solid {theme.border};
        }}
        pre code {{
            background: none;
            padding: 0;
            border-radius: 0;
        }}

        /* Blockquotes */
        blockquote {{
            margin: 3px 0;
            padding: 2px 8px;
            border-left: 2px solid {theme.accent};
            background-color: {theme.background_secondary};
            color: {theme.text_secondary};
        }}
        blockquote p {{
            margin: 0;
        }}

        /* Horizontal rule */
        hr {{
            border: none;
            border-top: 1px solid {theme.border};
            margin: 4px 0;
        }}

        /* Tables */
        table {{
            border-collapse: collapse;
            margin: 3px 0;
            width: 100%;
        }}
        th, td {{
            border: 1px solid {theme.border};
            padding: 2px 6px;
            text-align: left;
        }}
        th {{
            background-color: {theme.background_tertiary};
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: {theme.background_secondary};
        }}
    """


def render_markdown(text: str) -> str:
    """Convert markdown text to styled HTML.

    Args:
        text: Markdown formatted text

    Returns:
        HTML string with inline styles
    """
    if not text:
        return ""

    if MARKDOWN_AVAILABLE:
        # Use markdown library for full parsing
        md = markdown.Markdown(
            extensions=[
                'fenced_code',
                'tables',
                'nl2br',  # Convert newlines to <br>
            ]
        )
        html_content = md.convert(text)
    else:
        # Fallback: basic markdown conversion
        html_content = _basic_markdown_to_html(text)

    # Wrap in styled container
    css = get_markdown_css()
    html = f"""
    <html>
    <head>
    <style>
    {css}
    </style>
    </head>
    <body>
    {html_content}
    </body>
    </html>
    """

    return html


def _basic_markdown_to_html(text: str) -> str:
    """Basic markdown to HTML conversion without external libraries.

    Handles common markdown patterns:
    - Headers (# ## ###)
    - Bold (**text** or __text__)
    - Italic (*text* or _text_)
    - Code (`code` and ```code blocks```)
    - Lists (- item or * item or 1. item)
    - Links [text](url)
    - Blockquotes (> text)

    Args:
        text: Markdown text

    Returns:
        HTML string
    """
    lines = text.split('\n')
    html_lines = []
    in_code_block = False
    in_list = False
    list_type = None

    for line in lines:
        # Code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                html_lines.append('</code></pre>')
                in_code_block = False
            else:
                lang = line.strip()[3:].strip()
                html_lines.append(f'<pre><code class="language-{lang}">')
                in_code_block = True
            continue

        if in_code_block:
            # Escape HTML in code blocks
            escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_lines.append(escaped)
            continue

        # Close list if line doesn't continue it
        if in_list and not re.match(r'^(\s*[-*]|\s*\d+\.)\s', line) and line.strip():
            html_lines.append(f'</{list_type}>')
            in_list = False
            list_type = None

        # Headers
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            content = _inline_markdown(header_match.group(2))
            html_lines.append(f'<h{level}>{content}</h{level}>')
            continue

        # Unordered lists
        ul_match = re.match(r'^(\s*)[-*]\s+(.+)$', line)
        if ul_match:
            if not in_list or list_type != 'ul':
                if in_list:
                    html_lines.append(f'</{list_type}>')
                html_lines.append('<ul>')
                in_list = True
                list_type = 'ul'
            content = _inline_markdown(ul_match.group(2))
            html_lines.append(f'<li>{content}</li>')
            continue

        # Ordered lists
        ol_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
        if ol_match:
            if not in_list or list_type != 'ol':
                if in_list:
                    html_lines.append(f'</{list_type}>')
                html_lines.append('<ol>')
                in_list = True
                list_type = 'ol'
            content = _inline_markdown(ol_match.group(2))
            html_lines.append(f'<li>{content}</li>')
            continue

        # Blockquotes
        if line.startswith('>'):
            content = _inline_markdown(line[1:].strip())
            html_lines.append(f'<blockquote><p>{content}</p></blockquote>')
            continue

        # Horizontal rule
        if re.match(r'^[-*_]{3,}\s*$', line):
            html_lines.append('<hr>')
            continue

        # Empty line = paragraph break
        if not line.strip():
            if in_list:
                html_lines.append(f'</{list_type}>')
                in_list = False
                list_type = None
            html_lines.append('<br>')
            continue

        # Regular paragraph
        content = _inline_markdown(line)
        html_lines.append(f'<p>{content}</p>')

    # Close any open list
    if in_list:
        html_lines.append(f'</{list_type}>')

    return '\n'.join(html_lines)


def _inline_markdown(text: str) -> str:
    """Convert inline markdown elements.

    Args:
        text: Text with inline markdown

    Returns:
        HTML string
    """
    # Escape HTML first (but preserve our conversions)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Code (inline) - must be before bold/italic to avoid conflicts
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Bold (** or __)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)

    # Italic (* or _) - be careful not to match inside words
    text = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'<em>\1</em>', text)

    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # Strikethrough ~~text~~
    text = re.sub(r'~~([^~]+)~~', r'<s>\1</s>', text)

    return text


def strip_markdown(text: str) -> str:
    """Remove markdown formatting from text.

    Useful for getting plain text from markdown.

    Args:
        text: Markdown formatted text

    Returns:
        Plain text without markdown syntax
    """
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Remove inline code
    text = re.sub(r'`[^`]+`', '', text)

    # Remove headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)

    # Remove links, keep text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Remove list markers
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove blockquote markers
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)

    return text.strip()
