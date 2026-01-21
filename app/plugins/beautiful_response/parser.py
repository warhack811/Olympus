"""
Beautiful Response Plugin - Markdown Parser
"""

import logging
import re
import uuid

from app.plugins.beautiful_response.models.blocks import (
    BaseBlock,
    CitationBlock,
    CodeBlock,
    MathBlock,
    MermaidBlock,
    StructuredResponse,
    TableBlock,
    TaskBlock,
    TaskItem,
    TextBlock,
)

logger = logging.getLogger(__name__)


def generate_block_id(prefix: str = "block") -> str:
    """Unique block ID üretir"""
    return f"{prefix}-{str(uuid.uuid4())[:8]}"


def parse_response(text: str) -> StructuredResponse:
    if not text:
        return StructuredResponse(blocks=[])

    try:
        # (start_index, end_index, Block)
        extracted_blocks: list[tuple[int, int, BaseBlock]] = []

        # 1. Code Blocks (includes Mermaid candidates)
        extracted_blocks.extend(_extract_code_blocks(text))

        # 2. Math Blocks ($$ ... $$)
        math_blocks = _extract_math_blocks(text)

        # 3. Tables
        table_blocks = _extract_tables(text)

        # 4. Task Lists
        task_blocks = _extract_task_lists(text)

        # 5. Citations
        citation_blocks = _extract_citations(text)

        # MERGE STRATEGY: Priority to Code > Math > Table > Task > Citation
        # We process lists in priority order and add only if they don't overlap with existing blocks

        # Helper to check overlap
        def is_overlapping(start, end, existing_list):
            for ex_start, ex_end, _ in existing_list:
                if start < ex_end and end > ex_start:
                    return True
            return False

        # Math
        for start, end, block in math_blocks:
            if not is_overlapping(start, end, extracted_blocks):
                extracted_blocks.append((start, end, block))

        # Tables
        for start, end, block in table_blocks:
            if not is_overlapping(start, end, extracted_blocks):
                extracted_blocks.append((start, end, block))

        # Task Lists
        for start, end, block in task_blocks:
            if not is_overlapping(start, end, extracted_blocks):
                extracted_blocks.append((start, end, block))

        # Citations
        for start, end, block in citation_blocks:
            if not is_overlapping(start, end, extracted_blocks):
                extracted_blocks.append((start, end, block))

        # Sort all blocks by position
        extracted_blocks.sort(key=lambda x: x[0])

        # Convert CodeBlocks with language='mermaid' to MermaidBlock
        final_extracted: list[tuple[int, int, BaseBlock]] = []
        for start, end, block in extracted_blocks:
            if isinstance(block, CodeBlock) and block.language == "mermaid":
                mermaid_block = MermaidBlock(block_type="mermaid", content=block.content)
                final_extracted.append((start, end, mermaid_block))
            else:
                final_extracted.append((start, end, block))

        # FILL GAPS with TextBlocks
        all_blocks: list[BaseBlock] = []
        current_idx = 0

        for start, end, block in final_extracted:
            if start > current_idx:
                gap_text = text[current_idx:start]
                if gap_text.strip():
                    # Check for inline math in text blocks?
                    # For now, simplistic approach: text is text.
                    # Inline math ($...$) handling could be here but might be too aggressive if not careful.
                    # We will treat text as markdown, so frontend renders inline math if it supports it.
                    all_blocks.append(TextBlock(content=gap_text, block_type="text"))

            all_blocks.append(block)
            current_idx = end

        if current_idx < len(text):
            tail_text = text[current_idx:]
            if tail_text.strip():
                all_blocks.append(TextBlock(content=tail_text, block_type="text"))

        return StructuredResponse(blocks=all_blocks)

    except Exception as e:
        logger.error(f"[BeautifulResponse] Parse error: {e}")
        return StructuredResponse(blocks=[TextBlock(content=text, block_type="text")])


def _extract_code_blocks(text: str) -> list[tuple[int, int, CodeBlock]]:
    blocks = []
    pattern = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)

    for match in pattern.finditer(text):
        start, end = match.span()
        raw_lang = match.group(1)
        code_content = match.group(2)
        lang = raw_lang.strip().lower() or "plaintext"

        if code_content.endswith("\n"):
            code_content = code_content[:-1]

        blocks.append((start, end, CodeBlock(block_type="code", content=code_content, language=lang)))
    return blocks


def _extract_math_blocks(text: str) -> list[tuple[int, int, MathBlock]]:
    """$$...$$ bloklarını ayıklar"""
    blocks = []
    # Block math: $$ ... $$
    pattern = re.compile(r"\$\$([\s\S]+?)\$\$")

    for match in pattern.finditer(text):
        start, end = match.span()
        content = match.group(1).strip()
        blocks.append((start, end, MathBlock(block_type="math", content=content, is_inline=False)))

    # Inline math is tricky to separate from text blocks without partial parsing.
    # For now, we rely on Block Math extraction.
    # Inline math will stay inside TextBlocks and be rendered by Markdown renderer supports it.
    return blocks


def _extract_task_lists(text: str) -> list[tuple[int, int, TaskBlock]]:
    """- [ ] veya - [x] listelerini ayıklar"""
    blocks = []
    # Pattern to find a chunk of lines that look like task items
    # (?:^|\n) - [ ] ...
    lines = text.split("\n")
    current_items: list[TaskItem] = []
    in_list = False

    i = 0
    line_start_idx = 0
    list_start_idx = 0

    while i < len(lines):
        line = lines[i]
        line_len = len(line) + 1

        clean_line = line.strip()
        is_task = clean_line.startswith("- [ ]") or clean_line.startswith("- [x]") or clean_line.startswith("- [X]")

        if is_task:
            if not in_list:
                in_list = True
                list_start_idx = line_start_idx
                current_items = []

            checked = clean_line.lower().startswith("- [x]")
            # Remove "- [ ] " or "- [x] " (5 chars + space? or just 5)
            # Find first closing bracket ]
            bracket_idx = clean_line.find("]")
            item_text = clean_line[bracket_idx + 1 :].strip()

            current_items.append(TaskItem(text=item_text, checked=checked))

        else:
            if in_list:
                # List ended
                # But wait, could be a continuation line or sub-task?
                # For simplicity, if line is empty or doesn't look like task, end list.
                if not clean_line:
                    pass  # Empty line within list? Usually breaks list in MD
                else:
                    # End list
                    blocks.append(
                        (list_start_idx, line_start_idx, TaskBlock(block_type="task_list", items=current_items))
                    )
                    in_list = False
                    current_items = []

        line_start_idx += line_len
        i += 1

    if in_list and current_items:
        blocks.append((list_start_idx, line_start_idx, TaskBlock(block_type="task_list", items=current_items)))

    return blocks


def _extract_citations(text: str) -> list[tuple[int, int, CitationBlock]]:
    blocks = []
    pattern = re.compile(r"(?:^|\n)((?:>[^\n]*\n?)+)", re.MULTILINE)

    for match in pattern.finditer(text):
        start = match.start(1)
        end = match.end(1)
        content_group = match.group(1)
        cleaned_lines = [re.sub(r"^>\s?", "", line) for line in content_group.splitlines()]
        blocks.append(
            (
                start,
                end,
                CitationBlock(
                    block_type="citation", source_id=generate_block_id("cite"), text="\n".join(cleaned_lines).strip()
                ),
            )
        )
    return blocks


def _extract_tables(text: str) -> list[tuple[int, int, TableBlock]]:
    blocks = []
    lines = text.split("\n")
    current_table_lines = []
    current_line_start = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        line_len = len(line) + 1

        if "|" in line:
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if "|" in next_line and set(next_line.strip()) <= set("| -:") and next_line.count("-") >= 3:
                    table_start = current_line_start
                    current_table_lines.append(line)
                    i += 1
                    current_line_start += line_len
                    current_table_lines.append(lines[i])
                    line_len = len(lines[i]) + 1
                    i += 1
                    current_line_start += line_len

                    while i < len(lines):
                        body_line = lines[i]
                        if not body_line.strip() or "|" not in body_line:
                            break
                        current_table_lines.append(body_line)
                        current_line_start += len(body_line) + 1
                        i += 1

                    try:
                        table = _parse_markdown_table(current_table_lines)
                        if table:
                            table_text = "\n".join(current_table_lines)  # Approximation of length
                            blocks.append((table_start, table_start + len(table_text) + 1, table))  # +1 fuzziness
                    except Exception:
                        pass
                    current_table_lines = []
                    continue
        current_line_start += line_len
        i += 1
    return blocks


def _parse_markdown_table(lines: list[str]) -> TableBlock | None:
    if len(lines) < 2:
        return None
    h_row = lines[0].strip().strip("|")
    headers = [h.strip() for h in h_row.split("|")]

    s_row = lines[1].strip().strip("|")
    alignments = []
    for col in s_row.split("|"):
        col = col.strip()
        if col.startswith(":") and col.endswith(":"):
            alignments.append("center")
        elif col.endswith(":"):
            alignments.append("right")
        else:
            alignments.append("left")
    while len(alignments) < len(headers):
        alignments.append("left")

    rows = []
    for line in lines[2:]:
        r_row = line.strip().strip("|")
        if not r_row:
            continue
        cols = [c.strip() for c in r_row.split("|")]
        while len(cols) < len(headers):
            cols.append("")
        rows.append(cols)
    return TableBlock(headers=headers, rows=rows, alignments=alignments)
