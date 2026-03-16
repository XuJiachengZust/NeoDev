"""Graph types aligned with gitnexus/src/core/graph/types.ts and schema."""

from typing import TypedDict, Literal, Optional

# Node labels (single primary label per node)
NodeLabel = Literal[
    "Project", "Package", "Module", "Folder", "File",
    "Class", "Function", "Method", "Variable", "Interface", "Enum",
    "Decorator", "Import", "Type", "CodeElement", "Community", "Process",
    "Struct", "Macro", "Typedef", "Union", "Namespace", "Trait", "Impl",
    "TypeAlias", "Const", "Static", "Property", "Record", "Delegate",
    "Annotation", "Constructor", "Template",
]

# Relationship types
RelationshipType = Literal[
    "CONTAINS", "CALLS", "INHERITS", "OVERRIDES", "IMPORTS", "USES",
    "DEFINES", "DECORATES", "IMPLEMENTS", "EXTENDS", "MEMBER_OF", "STEP_IN_PROCESS",
]


class NodeProperties(TypedDict, total=False):
    branch: str
    project_id: Optional[int]
    name: str
    filePath: str
    sourceCode: Optional[str]
    content: Optional[str]
    startLine: int
    endLine: int
    language: Optional[str]
    isExported: bool
    description: Optional[str]
    heuristicLabel: Optional[str]
    cohesion: Optional[float]
    symbolCount: Optional[int]
    keywords: Optional[list[str]]
    enrichedBy: Optional[Literal["heuristic", "llm"]]
    processType: Optional[Literal["intra_community", "cross_community"]]
    stepCount: Optional[int]
    communities: Optional[list[str]]
    entryPointId: Optional[str]
    terminalId: Optional[str]
    entryPointScore: Optional[float]
    entryPointReason: Optional[str]


class GraphNode(TypedDict):
    id: str
    label: NodeLabel
    properties: NodeProperties


class GraphRelationship(TypedDict, total=False):
    id: str
    sourceId: str
    targetId: str
    type: RelationshipType
    confidence: float
    reason: str
    step: int
