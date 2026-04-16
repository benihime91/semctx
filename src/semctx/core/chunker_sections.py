"""Chunker section helpers."""

import re

from beartype import beartype


@beartype
def build_markdown_sections(
    lines: list[str], heading_pattern: re.Pattern[str]
) -> list[tuple[int, int]]:
    """Build markdown section ranges from heading lines."""
    heading_lines = [
        line_number
        for line_number, line in enumerate(lines, start=1)
        if heading_pattern.match(line.strip())
    ]
    if not heading_lines:
        return []
    sections: list[tuple[int, int]] = []
    first_heading = heading_lines[0]
    if first_heading > 1 and any(line.strip() for line in lines[: first_heading - 1]):
        sections.append((1, first_heading - 1))
    for index, start_line in enumerate(heading_lines):
        end_line = (
            heading_lines[index + 1] - 1
            if index + 1 < len(heading_lines)
            else len(lines)
        )
        sections.append((start_line, max(start_line, end_line)))
    return sections


@beartype
def build_paragraphs(lines: list[str], max_chars: int) -> list[tuple[int, int, str]]:
    """Split file lines into bounded paragraph chunks."""
    paragraphs: list[tuple[int, int, str]] = []
    start_line = 0
    current_lines: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        if line.strip():
            if start_line == 0:
                start_line = line_number
            current_lines.append(line)
            continue
        if current_lines:
            paragraphs.extend(
                split_paragraph_lines(start_line, current_lines, max_chars)
            )
            start_line = 0
            current_lines = []
    if current_lines:
        paragraphs.extend(split_paragraph_lines(start_line, current_lines, max_chars))
    return paragraphs


@beartype
def split_paragraph_lines(
    start_line: int,
    lines: list[str],
    max_chars: int,
) -> list[tuple[int, int, str]]:
    """Split one paragraph into bounded text chunks."""
    chunks: list[tuple[int, int, str]] = []
    current_start = start_line
    current_lines: list[str] = []
    for line_number, line in enumerate(lines, start=start_line):
        proposed_content = "\n".join([*current_lines, line]).strip()
        if current_lines and len(proposed_content) > max_chars:
            chunks.append(
                (current_start, line_number - 1, "\n".join(current_lines).strip())
            )
            current_start = line_number
            current_lines = [line]
            continue
        if not current_lines:
            current_start = line_number
        current_lines.append(line)
    if current_lines:
        chunks.append(
            (
                current_start,
                start_line + len(lines) - 1,
                "\n".join(current_lines).strip(),
            )
        )
    return chunks
