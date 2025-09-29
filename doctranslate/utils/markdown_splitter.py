# SPDX-FileCopyrightText: 2025 RealTimeX
# SPDX-License-Identifier: MPL-2.0
import re
from typing import List




class MarkdownBlockSplitter:
    def __init__(self, max_block_size: int = 5000):
        """
        Initialize Markdown block splitter

        Parameters:
            max_block_size: Maximum number of bytes per block
        """
        self.max_block_size = max_block_size

    @staticmethod
    def _get_bytes(text: str) -> int:
        return len(text.encode('utf-8'))

    def split_markdown(self, markdown_text: str) -> List[str]:
        """
        Split Markdown text into blocks of specified size
        Ensure original text can be reconstructed through simple concatenation (except for split code blocks)
        Try to keep headings with their corresponding content in the same block
        """
        # 1. Split text into logical blocks
        logical_blocks = self._split_into_logical_blocks(markdown_text)

        # 2. Merge logical blocks, ensuring they don't exceed max_block_size
        chunks = []
        current_chunk_parts = []
        current_size = 0

        for block in logical_blocks:
            block_size = self._get_bytes(block)

            # Case 1: The block itself is too large
            if block_size > self.max_block_size:
                # First output the currently accumulated blocks
                if current_chunk_parts:
                    chunks.append("".join(current_chunk_parts))
                    current_chunk_parts = []
                    current_size = 0

                # Split this oversized block and add it directly to results
                chunks.extend(self._split_large_block(block))
                continue

            # Case 2: Adding this block to current chunk would exceed limit
            if current_size + block_size > self.max_block_size:
                if current_chunk_parts:
                    chunks.append("".join(current_chunk_parts))

                current_chunk_parts = [block]
                current_size = block_size
            # Case 3: Normal addition
            else:
                current_chunk_parts.append(block)
                current_size += block_size

        # Add the last remaining chunk
        if current_chunk_parts:
            chunks.append("".join(current_chunk_parts))

        return chunks

    def _split_into_logical_blocks(self, markdown_text: str) -> List[str]:
        """
        Split Markdown text into logical blocks (headings, paragraphs, code blocks, empty line separators, etc.)
        """
        # Normalize line breaks
        text = markdown_text.replace('\r\n', '\n')

        # Split code blocks from other content
        code_block_pattern = r'(```[\s\S]*?```|~~~[\s\S]*?~~~)'
        parts = re.split(code_block_pattern, text)

        blocks = []
        for i, part in enumerate(parts):
            if not part:
                continue

            if i % 2 == 1:  # This is a code block
                blocks.append(part)
            else:  # This is regular Markdown content
                # Split by one or more empty lines, preserving separators
                # This effectively separates paragraphs, lists, headings, etc., while preserving empty lines between them
                sub_parts = re.split(r'(\n{2,})', part)
                # Filter out empty strings that re.split may produce
                blocks.extend([p for p in sub_parts if p])

        return blocks

    def _split_large_block(self, block: str) -> List[str]:
        """
        Split a single large block that exceeds max_block_size
        """
        # Prioritize handling code blocks
        if block.startswith(('```', '~~~')):
            fence = '```' if block.startswith('```') else '~~~'
            lines = block.split('\n')
            header = lines[0]
            footer = lines[-1]
            content_lines = lines[1:-1]

            chunks = []
            current_chunk_lines = [header]
            current_size = self._get_bytes(header) + 1

            for line in content_lines:
                line_size = self._get_bytes(line) + 1
                if current_size + line_size + self._get_bytes(footer) > self.max_block_size:
                    current_chunk_lines.append(footer)
                    chunks.append('\n'.join(current_chunk_lines))
                    current_chunk_lines = [header, line]
                    current_size = self._get_bytes(header) + 1 + line_size
                else:
                    current_chunk_lines.append(line)
                    current_size += line_size

            if len(current_chunk_lines) > 1:
                current_chunk_lines.append(footer)
                chunks.append('\n'.join(current_chunk_lines))
            return chunks

        # Split regular large text by lines
        lines = block.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        for line in lines:
            line_size = self._get_bytes(line) + 1
            if current_size + line_size > self.max_block_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size - 1  # -1 because the first line doesn't have a leading '\n'
            else:
                current_chunk.append(line)
                current_size += line_size

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks


def split_markdown_text(markdown_text: str, max_block_size=5000) -> List[str]:
    """
    Split Markdown string into blocks not exceeding max_block_size
    """
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    chunks = splitter.split_markdown(markdown_text)
    # Filter out blocks consisting only of whitespace characters
    return [chunk for chunk in chunks if chunk.strip()]


def _needs_single_newline_join(prev_chunk: str, next_chunk: str) -> bool:
    """
    Determine whether two blocks should be joined with a single newline
    This usually occurs between consecutive lines of lists, tables, and quote blocks
    """
    if not prev_chunk.strip() or not next_chunk.strip():
        return False

    last_line_prev = prev_chunk.rstrip().split('\n')[-1].lstrip()
    first_line_next = next_chunk.lstrip().split('\n')[0].lstrip()

    # Tables
    if last_line_prev.startswith('|') and last_line_prev.endswith('|') and \
            first_line_next.startswith('|') and first_line_next.endswith('|'):
        return True

    # Lists (unordered and ordered)
    list_markers = r'^\s*([-*+]|\d+\.)\s+'
    if re.match(list_markers, last_line_prev) and re.match(list_markers, first_line_next):
        return True

    # Quotes
    if last_line_prev.startswith('>') and first_line_next.startswith('>'):
        return True

    return False


def join_markdown_texts(markdown_texts: List[str]) -> str:
    """
    Intelligently join a list of Markdown blocks
    """
    if not markdown_texts:
        return ""

    joined_text = markdown_texts[0]
    for i in range(1, len(markdown_texts)):
        prev_chunk = markdown_texts[i - 1]
        current_chunk = markdown_texts[i]

        # Determine whether to use single or double newline
        if _needs_single_newline_join(prev_chunk, current_chunk):
            separator = "\n"
        else:
            # Default to using double newlines to separate different blocks
            separator = "\n\n"

        joined_text += separator + current_chunk

    return joined_text


if __name__ == '__main__':
    from pathlib import Path
    from doctranslate.utils.markdown_utils import clean_markdown_math_block
    content=Path(r"C:\Users\jxgm\Desktop\3a8d8999-3e9d-4f32-a32c-5b0830bb4320\full.md").read_text()
    content=split_markdown_text(content)
    content=join_markdown_texts(content)

