"""Markdown document chunking for document-level ingestion."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


DEFAULT_TARGET_TOKENS = 800
DEFAULT_MAX_TOKENS = 1200
DEFAULT_OVERLAP_TOKENS = 120


def chunk_markdown(
    text: str,
    *,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[dict]:
    blocks = _structural_blocks(text)
    chunks: list[dict] = []
    for heading_path, block_text in blocks:
        token_count = estimate_tokens(block_text)
        if token_count > max_tokens:
            parts = _semantic_split_block(
                block_text,
                target_tokens=target_tokens,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
            )
            for part in parts:
                chunks.append(_chunk_payload(len(chunks), heading_path, part, "semantic"))
            continue
        chunks.append(_chunk_payload(len(chunks), heading_path, block_text, "structural"))
    return [chunk for chunk in chunks if chunk["text"].strip()]


def estimate_tokens(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text or "")))


def _chunk_payload(index: int, heading_path: str, text: str, strategy: str) -> dict:
    normalized = text.strip()
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return {
        "chunk_index": index,
        "heading_path": heading_path,
        "text": normalized,
        "token_count": estimate_tokens(normalized),
        "content_hash": content_hash,
        "split_strategy": strategy,
    }


def _structural_blocks(text: str) -> list[tuple[str, str]]:
    current_headings: dict[int, str] = {}
    current_path = ""
    current_lines: list[str] = []
    blocks: list[tuple[str, str]] = []
    in_code = False

    def flush() -> None:
        nonlocal current_lines
        block = "\n".join(current_lines).strip()
        if block:
            blocks.append((current_path, block))
        current_lines = []

    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            current_lines.append(line)
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match and not in_code:
            flush()
            level = len(match.group(1))
            current_headings = {
                existing_level: heading
                for existing_level, heading in current_headings.items()
                if existing_level < level
            }
            current_headings[level] = match.group(2).strip()
            current_path = " > ".join(
                current_headings[key] for key in sorted(current_headings)
            )
            continue
        current_lines.append(line)
    flush()
    return blocks or [("", text or "")]


def _semantic_split_block(
    block: str,
    *,
    target_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", block) if part.strip()]
    if not paragraphs:
        return [block]
    if len(paragraphs) == 1:
        return _split_long_paragraph(
            paragraphs[0],
            target_tokens=target_tokens,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )

    similarities = [
        _token_cosine_similarity(paragraphs[index - 1], paragraphs[index])
        for index in range(1, len(paragraphs))
    ]
    threshold = _median(similarities)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for index, paragraph in enumerate(paragraphs):
        paragraph_tokens = estimate_tokens(paragraph)
        would_exceed_target = current_tokens + paragraph_tokens > target_tokens
        would_exceed_max = current_tokens + paragraph_tokens > max_tokens
        semantic_boundary = (
            index > 0
            and similarities[index - 1] <= threshold
            and current_tokens >= max(1, target_tokens // 2)
        )
        if current and (would_exceed_max or (would_exceed_target and semantic_boundary)):
            chunks.append("\n\n".join(current))
            current = _overlap_tail(current, overlap_tokens)
            current_tokens = estimate_tokens("\n\n".join(current)) if current else 0
        current.append(paragraph)
        current_tokens += paragraph_tokens
        if current_tokens >= max_tokens:
            chunks.append("\n\n".join(current))
            current = []
            current_tokens = 0
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _split_long_paragraph(
    paragraph: str,
    *,
    target_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", paragraph) if part.strip()]
    units = sentences if len(sentences) > 1 else _word_windows(paragraph, max_tokens)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for unit in units:
        unit_tokens = estimate_tokens(unit)
        if current and current_tokens + unit_tokens > target_tokens:
            chunks.append(" ".join(current))
            current = _overlap_tail(current, overlap_tokens)
            current_tokens = estimate_tokens(" ".join(current)) if current else 0
        current.append(unit)
        current_tokens += unit_tokens
    if current:
        chunks.append(" ".join(current))
    return chunks


def _word_windows(text: str, max_tokens: int) -> list[str]:
    words = re.findall(r"\S+", text or "")
    if not words:
        return [text]
    return [" ".join(words[index : index + max_tokens]) for index in range(0, len(words), max_tokens)]


def _overlap_tail(paragraphs: list[str], overlap_tokens: int) -> list[str]:
    if overlap_tokens <= 0:
        return []
    selected: list[str] = []
    total = 0
    for paragraph in reversed(paragraphs):
        total += estimate_tokens(paragraph)
        selected.insert(0, paragraph)
        if total >= overlap_tokens:
            break
    return selected


def _token_cosine_similarity(left: str, right: str) -> float:
    left_counts = Counter(_semantic_tokens(left))
    right_counts = Counter(_semantic_tokens(right))
    if not left_counts or not right_counts:
        return 0.0
    shared = set(left_counts) & set(right_counts)
    dot = sum(left_counts[token] * right_counts[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _semantic_tokens(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", text or "")]


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2
