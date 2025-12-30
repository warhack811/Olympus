"""
Beautiful Response Plugin - Markdown Enhancer

Parser'dan gelen blokları zenginleştirir ve temiz markdown üretir.
"""

import logging
import re

from app.plugins.beautiful_response.models.blocks import (
    BaseBlock,
    CitationBlock,
    CodeBlock,
    MathBlock,
    MermaidBlock,
    StructuredResponse,
    TableBlock,
    TaskBlock,
    TextBlock,
)

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "jsx",
    "tsx",
    "html",
    "css",
    "json",
    "yaml",
    "yml",
    "bash",
    "shell",
    "sh",
    "sql",
    "markdown",
    "md",
    "plaintext",
    "text",
    "java",
    "c",
    "cpp",
    "csharp",
    "cs",
    "go",
    "rust",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "scala",
    "mermaid",
    "latex",
    "tex",
}

LANGUAGE_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "sh": "bash",
    "shell": "bash",
    "yml": "yaml",
    "md": "markdown",
    "c++": "cpp",
    "c#": "csharp",
}


def enhance_response(structured: StructuredResponse) -> str:
    if not structured or not structured.blocks:
        return ""
    enhanced_parts: list[str] = []
    for block in structured.blocks:
        enhanced = _enhance_block(block)
        if enhanced:
            enhanced_parts.append(enhanced)
    result = "\n\n".join(enhanced_parts)
    result = _final_cleanup(result)
    return result


def _enhance_block(block: BaseBlock) -> str:
    if isinstance(block, CodeBlock):
        return _enhance_code_block(block)
    elif isinstance(block, TextBlock):
        return _enhance_text_block(block)
    elif isinstance(block, CitationBlock):
        return _enhance_citation_block(block)
    elif isinstance(block, TableBlock):
        return _enhance_table_block(block)
    elif isinstance(block, MermaidBlock):
        return _enhance_mermaid_block(block)
    elif isinstance(block, MathBlock):
        return _enhance_math_block(block)
    elif isinstance(block, TaskBlock):
        return _enhance_task_block(block)
    else:
        logger.warning(f"[Enhancer] Unknown block type: {type(block)}")
        return getattr(block, "content", "") or getattr(block, "text", "") or ""


def _enhance_code_block(block: CodeBlock) -> str:
    lang = block.language.lower().strip() if block.language else "plaintext"
    lang = LANGUAGE_ALIASES.get(lang, lang)
    if lang not in SUPPORTED_LANGUAGES:
        lang = "plaintext"
    code = block.content
    if code:
        code = code.strip("\n")
        code = code.replace("\t", "    ")
    return f"```{lang}\n{code}\n```"


def _enhance_text_block(block: TextBlock) -> str:
    text = block.content
    if not text or not text.strip():
        return ""
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _enhance_citation_block(block: CitationBlock) -> str:
    text = getattr(block, "text", "")
    if not text:
        return ""
    lines = text.strip().split("\n")
    quoted_lines = [f"> {line.strip()}" for line in lines]
    return "\n".join(quoted_lines)


def _enhance_table_block(block: TableBlock) -> str:
    if not block.headers or not block.rows:
        return ""
    header_str = "| " + " | ".join(block.headers) + " |"
    separators = []
    for i in range(len(block.headers)):
        align = block.alignments[i] if i < len(block.alignments) else "left"
        if align == "center":
            separators.append(":---:")
        elif align == "right":
            separators.append("---:")
        else:
            separators.append("---")
    separator_str = "| " + " | ".join(separators) + " |"
    row_strs = []
    for row in block.rows:
        cols = row[: len(block.headers)]
        while len(cols) < len(block.headers):
            cols.append("")
        row_str = "| " + " | ".join(cols) + " |"
        row_strs.append(row_str)
    return f'<div class="overflow-x-auto">\n\n{header_str}\n{separator_str}\n' + "\n".join(row_strs) + "\n\n</div>"


def _enhance_mermaid_block(block: MermaidBlock) -> str:
    """Mermaid bloklarını standart markdown olarak döndür (Frontend işleyecek)"""
    content = block.content.strip()

    # AUTOCORRECT: Fix common LLM syntax errors
    # 1. Fix invalid arrow syntax "-->|Label|>" -> "-->|Label|"
    #    The LLM often adds a trailing '>' which breaks the parser.
    content = re.sub(r"-->\|([^|]+)\|>", r"-->|\1|", content)

    # 2. Fix unquoted labels with parentheses "A[Text (Info)]" -> "A["Text (Info)"]"
    #    If it sees brackets containing parens without quotes, try to quote it?
    #    This is risky with regex alone. Better to rely on the arrow fix first.

    return f"```mermaid\n{content}\n```"


def _enhance_math_block(block: MathBlock) -> str:
    """Matematik bloklarını formatlar"""
    content = block.content.strip()
    if block.is_inline:
        return f"${content}$"
    else:
        # Block math
        return f"$$\n{content}\n$$"


def _enhance_task_block(block: TaskBlock) -> str:
    """Görev listesini HTML listesine çevirir (daha temiz görünüm için)"""
    lines = []
    lines.append('<ul class="task-list">')
    for item in block.items:
        checked_attr = "checked" if item.checked else ""
        # HTML checkbox disabled
        lines.append(f'  <li class="task-list-item"><input type="checkbox" disabled {checked_attr}> {item.text}</li>')
    lines.append("</ul>")
    return "\n".join(lines)


def _final_cleanup(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if text.count("```") % 2 != 0:
        logger.warning("[Enhancer] Unbalanced code blocks detected, adding closing")
        text += "\n```"
    return text
