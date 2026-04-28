from service.services import doc_chunk_service


def test_chunk_markdown_preserves_heading_path_and_code_block():
    text = """# Overview

Intro paragraph for the product.

## API

```python
def login():
    return True
```

After code.
"""

    chunks = doc_chunk_service.chunk_markdown(text, target_tokens=40, max_tokens=80)

    assert [chunk["heading_path"] for chunk in chunks] == ["Overview", "Overview > API"]
    assert "Intro paragraph" in chunks[0]["text"]
    assert "```python" in chunks[1]["text"]
    assert "After code." in chunks[1]["text"]


def test_chunk_markdown_semantic_splits_oversized_structural_chunk(monkeypatch):
    calls = []

    def fake_similarity_split(block: str, *, target_tokens: int, max_tokens: int, overlap_tokens: int):
        calls.append((block, target_tokens, max_tokens, overlap_tokens))
        return ["part one", "part two"]

    monkeypatch.setattr(doc_chunk_service, "_semantic_split_block", fake_similarity_split)

    chunks = doc_chunk_service.chunk_markdown(
        "# Long\n\n" + "word " * 80,
        target_tokens=10,
        max_tokens=20,
        overlap_tokens=2,
    )

    assert calls
    assert [chunk["text"] for chunk in chunks] == ["part one", "part two"]
    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1]
    assert all(chunk["split_strategy"] == "semantic" for chunk in chunks)
