"""Symbol table: file-scoped and global index for lookup_exact / lookup_fuzzy. Aligned with symbol-table.ts."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SymbolDefinition:
    nodeId: str
    filePath: str
    type: str  # 'Function', 'Class', etc.


class SymbolTable:
    """File index (filePath -> name -> nodeId) + global index (name -> list of SymbolDefinition)."""

    def __init__(self) -> None:
        self._file_index: dict[str, dict[str, str]] = {}
        self._global_index: dict[str, list[SymbolDefinition]] = {}

    def add(self, file_path: str, name: str, node_id: str, type: str) -> None:
        if file_path not in self._file_index:
            self._file_index[file_path] = {}
        self._file_index[file_path][name] = node_id
        if name not in self._global_index:
            self._global_index[name] = []
        self._global_index[name].append(SymbolDefinition(nodeId=node_id, filePath=file_path, type=type))

    def lookup_exact(self, file_path: str, name: str) -> Optional[str]:
        symbols = self._file_index.get(file_path)
        if not symbols:
            return None
        return symbols.get(name)

    def lookup_fuzzy(self, name: str) -> list[SymbolDefinition]:
        return self._global_index.get(name, []).copy()

    def get_stats(self) -> dict[str, int]:
        return {
            "fileCount": len(self._file_index),
            "globalSymbolCount": len(self._global_index),
        }

    def clear(self) -> None:
        self._file_index.clear()
        self._global_index.clear()


def create_symbol_table() -> SymbolTable:
    return SymbolTable()
