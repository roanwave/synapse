"""Premium markdown to HTML renderer for chat messages.

Converts markdown text to styled HTML with premium dark theme aesthetics.
Inspired by Linear, Raycast, and high-end SaaS applications.
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


def get_markdown_css(is_user: bool = False) -> str:
    """Get premium CSS styles for rendered markdown content.

    Args:
        is_user: Whether this is for a user message (affects colors)

    Returns:
        CSS stylesheet string
    """
    # Text color based on message type
    text_color = "#ffffff" if is_user else theme.text_primary
    text_secondary = "rgba(255, 255, 255, 0.85)" if is_user else theme.text_secondary
    link_color = "#a5b4fc" if is_user else theme.accent_hover
    link_hover = "#c4b5fd" if is_user else "#a5b4fc"
    code_bg = "rgba(0, 0, 0, 0.2)" if is_user else theme.code_bg
    code_border = "rgba(255, 255, 255, 0.1)" if is_user else theme.code_border
    blockquote_border = "rgba(255, 255, 255, 0.4)" if is_user else theme.accent
    blockquote_bg = "rgba(0, 0, 0, 0.15)" if is_user else theme.background_elevated
    table_border = "rgba(255, 255, 255, 0.2)" if is_user else theme.border
    table_header_bg = "rgba(0, 0, 0, 0.2)" if is_user else theme.background_tertiary
    table_alt_bg = "rgba(0, 0, 0, 0.1)" if is_user else theme.background_secondary

    return f"""
        body {{
            color: {text_color};
            font-family: {fonts.chat};
            font-size: {metrics.font_medium}px;
            line-height: 1.5;
            margin: 0;
            padding: 0;
        }}

        /* Headings - Premium typography */
        h1, h2, h3, h4, h5, h6 {{
            color: {text_color};
            font-family: {fonts.ui};
            margin-top: 12px;
            margin-bottom: 6px;
            font-weight: 600;
            letter-spacing: -0.01em;
        }}
        h1 {{ font-size: 1.3em; }}
        h2 {{ font-size: 1.2em; }}
        h3 {{ font-size: 1.1em; }}
        h4, h5, h6 {{ font-size: 1em; }}

        /* Paragraphs */
        p {{
            margin-top: 0;
            margin-bottom: 8px;
        }}

        /* Bold and italic */
        strong, b {{
            font-weight: 600;
            color: {text_color};
        }}
        em, i {{
            font-style: italic;
        }}

        /* Links - Premium styling */
        a {{
            color: {link_color};
            text-decoration: none;
            transition: color 150ms ease;
        }}
        a:hover {{
            color: {link_hover};
            text-decoration: underline;
        }}

        /* Lists */
        ul, ol {{
            margin-top: 0;
            margin-bottom: 8px;
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 4px;
            line-height: 1.5;
        }}
        li p {{
            margin: 0;
        }}

        /* Inline code - Premium styling */
        code {{
            font-family: {fonts.mono};
            font-size: 0.9em;
            background-color: {code_bg};
            padding: 2px 6px;
            border-radius: 4px;
            color: {text_color};
        }}

        /* Code blocks - GitHub dark inspired */
        pre {{
            font-family: {fonts.mono};
            font-size: 13px;
            background-color: {code_bg};
            padding: 12px 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 8px 0;
            border: 1px solid {code_border};
            line-height: 1.45;
        }}
        pre code {{
            background: none;
            padding: 0;
            border-radius: 0;
            font-size: inherit;
        }}

        /* Blockquotes - Premium accent */
        blockquote {{
            margin: 8px 0;
            padding: 8px 16px;
            border-left: 3px solid {blockquote_border};
            background-color: {blockquote_bg};
            border-radius: 0 6px 6px 0;
            color: {text_secondary};
        }}
        blockquote p {{
            margin: 0;
        }}

        /* Horizontal rule */
        hr {{
            border: none;
            border-top: 1px solid {table_border};
            margin: 16px 0;
        }}

        /* Tables - Premium styling */
        table {{
            border-collapse: collapse;
            margin: 8px 0;
            width: 100%;
            border-radius: 6px;
            overflow: hidden;
        }}
        th, td {{
            border: 1px solid {table_border};
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: {table_header_bg};
            font-weight: 600;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        tr:nth-child(even) {{
            background-color: {table_alt_bg};
        }}

        /* Selection */
        ::selection {{
            background-color: {theme.selection if not is_user else "rgba(255, 255, 255, 0.3)"};
        }}
    """


def render_markdown(text: str, is_user: bool = False) -> str:
    """Convert markdown text to premium styled HTML.

    Args:
        text: Markdown formatted text
        is_user: Whether this is a user message (affects styling)

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
                'nl2br',
            ]
        )
        html_content = md.convert(text)
    else:
        # Fallback: basic markdown conversion
        html_content = _basic_markdown_to_html(text)

    # Wrap in styled container
    css = get_markdown_css(is_user)
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
